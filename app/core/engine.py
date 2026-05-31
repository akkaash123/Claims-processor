from typing import TypedDict, List, Dict, Any, Optional
from langgraph.graph import StateGraph, END
from app.core.schemas import ExtractedClaimData
from app.core.policy_math import PolicyRulesEngine
from app.core.agents import run_semantic_evaluator_agent

rules_engine = PolicyRulesEngine(policy_path="data/policy_terms.json")

class ClaimState(TypedDict):
    member_id: str
    policy_id: str
    claim_category: str
    treatment_date: str
    claimed_amount: float
    documents: List[Dict[str, Any]]
    claims_history: List[Dict[str, Any]]
    simulate_component_failure: bool
    stop_pipeline: bool
    validation_errors: List[str]
    extracted_data: Any 
    fraud_flags: List[str]
    approved_amount: float
    itemized_breakdown: List[Dict[str, Any]]
    decision: Optional[str] 
    rejection_reasons: List[str]
    notes: str
    confidence_score: float
    audit_trace: List[Dict[str, Any]]

def bouncer_node(state: ClaimState) -> Dict[str, Any]:
    if state.get("simulate_component_failure"):
        return {"audit_trace": state.get("audit_trace", []) + [{"node": "bouncer", "status": "BYPASSED_DUE_TO_FAILURE"}]}
        
    docs = state.get("documents", [])
    category = state.get("claim_category", "").upper()
    
    # ---------------------------------------------------------
    # THE FIX: Legibility Before Logic.
    # Check for blurry/unreadable documents BEFORE matching names.
    # ---------------------------------------------------------
    for doc in docs:
        if doc.get("quality") in ["UNREADABLE", "LOW_CONFIDENCE"]:
            errors = [f"The document {doc.get('file_name')} is blurry or unreadable. Please re-upload."]
            return {
                "decision": "REJECTED",
                "validation_errors": errors,
                "stop_pipeline": True,
                "notes": errors[0],
                "audit_trace": state.get("audit_trace", []) + [{"node": "bouncer", "status": "FAILED"}]
            }

    # 1. Check Missing Documents
    reqs = rules_engine.policy.get("document_requirements", {}).get(category, {})
    required_types = set(reqs.get("required", []))
    uploaded_types = set([d.get("actual_type") for d in docs])
    
    missing_docs = required_types - uploaded_types
    if missing_docs:
        missing_str = ", ".join(missing_docs)
        uploaded_str = ", ".join(uploaded_types) if uploaded_types else "None"
        errors = [f"Missing required document: {missing_str}. You uploaded: {uploaded_str}."]
        return {
            "decision": "REJECTED",
            "validation_errors": errors,
            "stop_pipeline": True,
            "notes": " | ".join(errors),
            "audit_trace": state.get("audit_trace", []) + [{"node": "bouncer", "status": "FAILED"}]
        }
        
    # 2. Check Name Mismatches
    names = set([d.get("patient_name_on_doc") for d in docs if d.get("patient_name_on_doc")])
    if len(names) > 1:
        errors = [f"Documents belong to different patients: {', '.join(names)}."]
        return {
            "decision": "REJECTED",
            "validation_errors": errors,
            "stop_pipeline": True,
            "notes": " | ".join(errors),
            "audit_trace": state.get("audit_trace", []) + [{"node": "bouncer", "status": "FAILED"}]
        }
        
    return {"audit_trace": state.get("audit_trace", []) + [{"node": "bouncer", "status": "PASSED"}]}

def fraud_node(state: ClaimState) -> Dict[str, Any]:
    history = state.get("claims_history", [])
    today_claims = [c for c in history if c.get("date") == state.get("treatment_date")]
    if len(today_claims) >= 2:
        return {
            "fraud_flags": ["HIGH_VELOCITY_SAME_DAY"],
            "stop_pipeline": True,
            "decision": "MANUAL_REVIEW",
            "notes": "Unusual same-day claim pattern detected.",
            "audit_trace": state.get("audit_trace", []) + [{"node": "fraud", "status": "FLAGGED"}]
        }
    return {"audit_trace": state.get("audit_trace", []) + [{"node": "fraud", "status": "CLEAN"}]}

def extractor_node(state: ClaimState) -> Dict[str, Any]:
    if state.get("simulate_component_failure"):
        return {
            "confidence_score": 0.40,
            "notes": "Extractor component failed. Proceeding with degraded state.",
            "audit_trace": state.get("audit_trace", []) + [{"node": "extractor", "status": "DEGRADED"}],
            "extracted_data": ExtractedClaimData(actual_type="UNKNOWN", quality_flag="GOOD"),
            "decision": "MANUAL_REVIEW",
            "stop_pipeline": True
        }
        
    docs = state.get("documents", [])
    category = state.get("claim_category", "CONSULTATION")
    extracted_content = {}
    
    # We removed the UNREADABLE check from here because Bouncer handles it now!
    for doc in docs:
        if "content" in doc: 
            extracted_content.update(doc["content"])
            
    if extracted_content:
        ai_extracted_data = run_semantic_evaluator_agent(extracted_content, claim_category=category)
    else:
        ai_extracted_data = ExtractedClaimData(actual_type="UNKNOWN", quality_flag="GOOD")
            
    return {
        "extracted_data": ai_extracted_data,
        "confidence_score": 0.95,
        "audit_trace": state.get("audit_trace", []) + [{"node": "extractor", "status": "COMPLETED"}]
    }

def policy_math_node(state: ClaimState) -> Dict[str, Any]:
    ai_data = state.get("extracted_data")
    math_result = rules_engine.calculate_payout(state, ai_data)
    return {
        "decision": math_result.get("decision"),
        "approved_amount": math_result.get("approved_amount", 0.0),
        "rejection_reasons": math_result.get("rejection_reasons", []),
        "itemized_breakdown": math_result.get("itemized_breakdown", []),
        "notes": math_result.get("notes", ""),
        "audit_trace": state.get("audit_trace", []) + [{"node": "policy_math", "status": "COMPLETED", "result": math_result.get("decision")}]
    }

def synthesizer_node(state: ClaimState) -> Dict[str, Any]:
    decision = state.get("decision")
    audit_trace = state.get("audit_trace", [])
    current_notes = state.get("notes", "")
    confidence = state.get("confidence_score", 0.95)
    
    if confidence < 0.5:
        decision = "MANUAL_REVIEW"
        new_note = "Routed to manual review due to incomplete AI extraction (System Degraded)."
        if new_note not in current_notes:
            current_notes = f"{current_notes} {new_note}".strip()

    if not decision:
        if state.get("stop_pipeline"):
            decision = "REJECTED"
        else:
            decision = "APPROVED" 
        
    return {"decision": decision, "notes": current_notes, "confidence_score": confidence, "audit_trace": audit_trace + [{"node": "synthesizer", "status": "FINALIZED"}]}

def router_after_bouncer(state: ClaimState) -> str:
    if state.get("stop_pipeline"): return "synthesizer"
    return "fraud" 

def router_after_fraud(state: ClaimState) -> str:
    if state.get("stop_pipeline"): return "synthesizer"
    return "extractor" 

def router_after_extractor(state: ClaimState) -> str:
    if state.get("stop_pipeline"): return "synthesizer"
    return "policy_math"

workflow = StateGraph(ClaimState)
workflow.add_node("bouncer", bouncer_node)
workflow.add_node("fraud", fraud_node)
workflow.add_node("extractor", extractor_node)
workflow.add_node("policy_math", policy_math_node)
workflow.add_node("synthesizer", synthesizer_node)

workflow.set_entry_point("bouncer")
workflow.add_conditional_edges("bouncer", router_after_bouncer)
workflow.add_conditional_edges("fraud", router_after_fraud)
workflow.add_conditional_edges("extractor", router_after_extractor)
workflow.add_edge("policy_math", "synthesizer")
workflow.add_edge("synthesizer", END)

claims_pipeline = workflow.compile()