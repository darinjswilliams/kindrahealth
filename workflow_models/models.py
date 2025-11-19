from typing import TypedDict, Annotated, List, Dict, Any, Optional
from datetime import datetime, timedelta
import operator
from enum import Enum
from pydantic import BaseModel

class WorkflowStatus(str, Enum):
    INITIATED = "initiated"
    PROCESSING = "processing"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    EXECUTING = "executing"
    COMPLETED = "completed"
    ERROR = "error"


class ConsultationInput(BaseModel):
    """Input from physician"""
    patient_name: str
    patient_id: str
    date_of_visit: str
    consultation_notes: str
    physician_id: str


class ClinicalSummary(BaseModel):
    """Structured clinical summary"""
    patient_name: str
    visit_date: str
    chief_complaint: str
    history_of_present_illness: str
    vital_signs: Optional[str] = None
    physical_exam_findings: List[Dict[str, str]]
    assessments: List[Dict[str, str]]
    icd_codes: List[str]
    additional_notes: Optional[str] = None


class NextStepAction(BaseModel):
    """Individual action item"""
    action_type: str  # lab, imaging, referral, medication, follow-up
    description: str
    priority: str  # high, medium, low
    timeline: str
    requires_scheduling: bool = False


class PatientEmail(BaseModel):
    """Patient-friendly email"""
    subject: str
    greeting: str
    summary: str
    treatment_plan: str
    instructions: List[str]
    warning_signs: List[str]
    next_steps: str
    closing: str


class AgentState(TypedDict):
    """State shared across all agents"""
    # Input
    consultation: ConsultationInput
    
    # Agent outputs
    clinical_summary: Optional[ClinicalSummary]
    next_steps: Optional[List[NextStepAction]]
    patient_email: Optional[PatientEmail]
    
    # Workflow control
    status: str
    current_agent: str
    errors: Annotated[List[str], operator.add]
    physician_approval_required: bool
    physician_approved: bool
    
    # Agent messages (for debugging/audit)
    messages: Annotated[List[str], operator.add]
    
    # Execution tracking
    executed_actions: Annotated[List[Dict], operator.add]