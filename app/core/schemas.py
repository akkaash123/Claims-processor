from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum

class QualityFlag(str, Enum):
    GOOD = "GOOD"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    UNREADABLE = "UNREADABLE"

class DocumentType(str, Enum):
    PRESCRIPTION = "PRESCRIPTION"
    HOSPITAL_BILL = "HOSPITAL_BILL"
    LAB_REPORT = "LAB_REPORT"
    PHARMACY_BILL = "PHARMACY_BILL"
    DISCHARGE_SUMMARY = "DISCHARGE_SUMMARY"
    DENTAL_REPORT = "DENTAL_REPORT"
    PRE_AUTHORIZATION_LETTER = "PRE_AUTHORIZATION_LETTER" 
    UNKNOWN = "UNKNOWN"

class LineItem(BaseModel):
    description: str = Field(..., description="Exact description of the service, test, or medicine")
    amount: float = Field(..., description="Numerical amount charged.")
    
    is_policy_excluded: bool = Field(
        default=False, 
        description="Semantically evaluate the description. Is this a universally excluded treatment?"
    )
    exclusion_reason: Optional[str] = Field(None)

class ExtractedClaimData(BaseModel):
    actual_type: DocumentType = Field(..., description="Classify the type of medical document.")
    patient_name_on_doc: Optional[str] = None
    doctor_name: Optional[str] = None
    doctor_registration: Optional[str] = None
    
    diagnosis: Optional[str] = Field(None, description="Expand shorthands.")
    
    is_diagnosis_excluded: bool = Field(default=False)
    matched_waiting_period_category: Optional[str] = Field(
        None, 
        description="If the diagnosis/treatment requires a waiting period, output the EXACT category name from the provided policy list."
    )
    requires_pre_auth: bool = Field(
        default=False, 
        description="True if any test/procedure semantically requires pre-authorization based on the provided policy list."
    )
    
    hospital_name: Optional[str] = None
    treatment_date: Optional[str] = Field(None, description="YYYY-MM-DD")
    line_items: List[LineItem] = Field(default_factory=list)
    total_amount: Optional[float] = None
    
    quality_flag: QualityFlag = Field(..., description="Assess visual readability.")
    alteration_detected: bool = Field(default=False, description="True if tampered with.")