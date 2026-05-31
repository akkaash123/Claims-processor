import json
import base64
import sys
from typing import List, Dict, Any
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
from app.core.schemas import ExtractedClaimData

# Load global definitions
try:
    with open("data/policy_terms.json", "r") as f:
        policy_data = json.load(f)
        
        exclusions_dict = policy_data.get("exclusions", {})
        dynamic_exclusions = (
            exclusions_dict.get("conditions", []) + 
            exclusions_dict.get("dental_exclusions", []) + 
            exclusions_dict.get("vision_exclusions", [])
        )
        waiting_conditions = list(policy_data.get("waiting_periods", {}).get("specific_conditions", {}).keys())
        pre_auth_tests = policy_data.get("pre_authorization", {}).get("required_for", [])
        opd_categories = policy_data.get("opd_categories", {})

except Exception as e:
    print(f"CRITICAL ERROR: Could not load data/policy_terms.json. Error: {e}")
    sys.exit(1)

exclusions_string = ", ".join(dynamic_exclusions)
waiting_string = ", ".join(waiting_conditions)
pre_auth_string = ", ".join(pre_auth_tests)

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0.0,
    max_retries=3
)
extractor_llm = llm.with_structured_output(ExtractedClaimData)

def encode_image(file_bytes: bytes) -> str:
    return base64.b64encode(file_bytes).decode("utf-8")

# ---------------------------------------------------------
# THE FIX: Context-Aware AI Extraction
# ---------------------------------------------------------
def run_extractor_agent(file_bytes: bytes, mime_type: str = "image/jpeg", claim_category: str = "CONSULTATION") -> ExtractedClaimData:
    base64_data = encode_image(file_bytes)
    
    # Extract category-specific constraints dynamically from the JSON
    cat_config = opd_categories.get(claim_category.lower(), {})
    allowed_items = cat_config.get("covered_procedures", []) + cat_config.get("covered_items", []) + cat_config.get("covered_systems", [])
    
    category_scope_instruction = ""
    if allowed_items:
        category_scope_instruction = (
            f"6. CATEGORY SCOPE VIOLATION: The user is claiming under the category '{claim_category}'. "
            f"This category ONLY covers the following explicit services: {', '.join(allowed_items)}. "
            "If any line item on this document does not semantically fall under this list of allowed services, "
            "YOU MUST mark 'is_policy_excluded' as True for that item and set the 'exclusion_reason' to 'CATEGORY_MISMATCH'."
        )
    else:
        # Fallback for general categories like Consultation/Pharmacy
        category_scope_instruction = (
            f"6. CATEGORY SCOPE: Ensure the services extracted reasonably correspond to a '{claim_category}' claim. "
            "If there is an undeniable category breakdown, flag it."
        )

    prompt_instructions = (
        "You are an elite medical document parser for Plum Health Insurance. "
        "Extract the requested fields accurately. "
        "CRITICAL RULES: "
        "1. Expand all medical shorthands (e.g., 'HTN' becomes 'Hypertension'). "
        "2. If a rubber stamp obscures text or the image is blurry, set quality_flag to 'LOW_CONFIDENCE'. "
        "3. If amounts are crossed out or tampered with, set alteration_detected to true. "
        "4. Convert all dates to YYYY-MM-DD. "
        f"5. GLOBAL EXCLUSIONS: Evaluate against this list: {exclusions_string}. If matched, set exclusion flags to true.\n"
        f"{category_scope_instruction}\n"
        f"7. WAITING PERIODS: If the treatment matches any of these: {waiting_string}, set 'matched_waiting_period_category' to the exact matching word.\n"
        f"8. PRE-AUTH: If any line item matches these tests: {pre_auth_string}, set 'requires_pre_auth' to true."
    )
    
    message = HumanMessage(
        content=[
            {"type": "text", "text": prompt_instructions},
            {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{base64_data}"}}
        ]
    )
    try:
        return extractor_llm.invoke([message])
    except Exception as e:
        print(f"Extraction Pipeline Failure: {str(e)}")
        raise e

def run_semantic_evaluator_agent(raw_content: Dict[str, Any], claim_category: str = "CONSULTATION") -> ExtractedClaimData:
    cat_config = opd_categories.get(claim_category.lower(), {})
    allowed_items = cat_config.get("covered_procedures", []) + cat_config.get("covered_items", []) + cat_config.get("covered_systems", [])
    
    category_scope_instruction = ""
    if allowed_items:
        category_scope_instruction = (
            f"CATEGORY SCOPE VIOLATION: The user is claiming under the category '{claim_category}'. "
            f"This category ONLY covers: {', '.join(allowed_items)}. "
            "If any line item on this document does not semantically match this list, "
            "YOU MUST mark 'is_policy_excluded' as True and set the 'exclusion_reason' to 'CATEGORY_MISMATCH'."
        )

    prompt_instructions = (
        "You are an elite medical document parser. Map this data strictly to the schema.\n"
        f"GLOBAL EXCLUSIONS: {exclusions_string}\n"
        f"{category_scope_instruction}\n"
        f"WAITING PERIODS: {waiting_string}\n"
        f"PRE-AUTH: {pre_auth_string}"
    )
    message = HumanMessage(
        content=[{"type": "text", "text": prompt_instructions + f"\n\nRAW DATA:\n{str(raw_content)}"}]
    )
    return extractor_llm.invoke([message])