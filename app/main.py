import os
import json
import sqlite3
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

load_dotenv()
from app.core.engine import claims_pipeline
from app.core.agents import run_extractor_agent

conn = sqlite3.connect("claims_memory.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS submitted_claims (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        member_id TEXT,
        treatment_date TEXT,
        decision TEXT
    )
''')
conn.commit()

app = FastAPI(title="Plum Health Insurance Claims Processor")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class VerifyRequest(BaseModel):
    member_id: str
    policy_id: str

@app.post("/api/v1/verify-policy")
async def verify_policy(payload: VerifyRequest):
    try:
        with open("data/policy_terms.json", "r") as f:
            policy = json.load(f)
        member = next((m for m in policy.get("members", []) if m["member_id"] == payload.member_id), None)
        if not member:
            raise HTTPException(status_code=404, detail=f"Member ID '{payload.member_id}' not found in the system.")
        if member.get("status", "ACTIVE") != "ACTIVE":
            raise HTTPException(status_code=403, detail=f"Member '{payload.member_id}' has an inactive policy.")
        return {"status": "success", "message": f"Welcome, {member['name']}! Policy verified."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class TestCasePayload(BaseModel):
    member_id: str
    policy_id: str
    claim_category: str
    treatment_date: str
    claimed_amount: float
    documents: List[Dict[str, Any]]
    claims_history: Optional[List[Dict[str, Any]]] = []
    simulate_component_failure: Optional[bool] = False

@app.post("/api/v1/evaluate-test-cases")
async def evaluate_test_case(payload: TestCasePayload):
    try:
        initial_state = payload.model_dump()
        initial_state["audit_trace"] = []
        initial_state["validation_errors"] = []
        initial_state["fraud_flags"] = []
        initial_state["stop_pipeline"] = False
        return claims_pipeline.invoke(initial_state)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/process-claim")
async def process_live_claim(
    member_id: str = Form(...),
    policy_id: str = Form(...),
    claim_category: str = Form(...),
    treatment_date: str = Form(...),
    claimed_amount: float = Form(...),
    files: List[UploadFile] = File(...)
):
    allowed_types = ["image/jpeg", "image/png", "application/pdf"]
    for file in files:
        if file.content_type not in allowed_types:
            raise HTTPException(status_code=400, detail=f"Invalid file type: {file.filename}")

    document_payloads = []
    simulate_failure = False 
    
    for file in files:
        file_bytes = await file.read()
        try:
            # FIX: Pass claim_category to the extractor agent loop explicitly
            extracted_pydantic = run_extractor_agent(file_bytes, file.content_type, claim_category=claim_category)
            doc_payload = {
                "file_id": file.filename,
                "file_name": file.filename,
                "actual_type": extracted_pydantic.actual_type.value,
                "quality": extracted_pydantic.quality_flag.value,
                "patient_name_on_doc": extracted_pydantic.patient_name_on_doc,
                "content": extracted_pydantic.model_dump() 
            }
        except Exception as e:
            print(f"AI Vision Failed for {file.filename}: {str(e)}")
            simulate_failure = True
            doc_payload = {
                "file_id": file.filename,
                "file_name": file.filename,
                "actual_type": "UNKNOWN",
                "quality": "UNREADABLE",
                "patient_name_on_doc": None,
                "content": {}
            }
        document_payloads.append(doc_payload)

    cursor.execute("SELECT id, treatment_date FROM submitted_claims WHERE member_id = ?", (member_id,))
    db_history = cursor.fetchall()
    claims_history = [{"claim_id": f"DB_{row[0]}", "date": row[1]} for row in db_history]

    live_state = {
        "member_id": member_id,
        "policy_id": policy_id,
        "claim_category": claim_category,
        "treatment_date": treatment_date,
        "claimed_amount": claimed_amount,
        "documents": document_payloads,
        "claims_history": claims_history,
        "simulate_component_failure": simulate_failure, 
        "audit_trace": [],
        "validation_errors": [],
        "fraud_flags": [],
        "stop_pipeline": False,
        "confidence_score": 1.0
    }

    try:
        result = claims_pipeline.invoke(live_state)
        cursor.execute(
            "INSERT INTO submitted_claims (member_id, treatment_date, decision) VALUES (?, ?, ?)",
            (member_id, treatment_date, result.get("decision", "UNKNOWN"))
        )
        conn.commit()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))