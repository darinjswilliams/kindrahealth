# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from dataclasses import dataclass


class ConsultationCreateRequest(BaseModel):
    """Request to create a new consultation and trigger workflow"""
    patient_name: str = Field(..., min_length=1, max_length=200)
    patient_id: str = Field(..., min_length=1, max_length=50)
    date_of_visit: str = Field(..., description="ISO format date: YYYY-MM-DD")
    consultation_notes: str = Field(..., min_length=10)
    physician_id: str = Field(..., min_length=1, max_length=50)
    auto_approve: bool = Field(False, description="Auto-approve high-priority actions")
    
    @field_validator('date_of_visit')
    def validate_date(cls, v):
        try:
            datetime.fromisoformat(v)
            return v
        except ValueError:
            raise ValueError("date_of_visit must be in YYYY-MM-DD format")
    
    class Config:
        json_schema_extra = {
            "example": {
                "patient_name": "John Doe",
                "patient_id": "PT12345",
                "date_of_visit": "2025-11-18",
                "consultation_notes": "Patient presents with hypertension...",
                "physician_id": "DR001",
                "auto_approve": False
            }
        }


class WorkflowStatusEnum(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    AWAITING_APPROVAL = "awaiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"


class ActionResponse(BaseModel):
    """Action execution details"""
    action_id: str
    action_type: str
    description: str
    status: str
    priority: Optional[str] = None
    executed_time: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class ClinicalSummaryResponse(BaseModel):
    """Clinical summary from agent"""
    patient_name: str
    visit_date: str
    chief_complaint: str
    history_of_present_illness: str
    vital_signs: Optional[str] = None
    assessments: List[Dict[str, Any]]
    icd_codes: List[str]


class PatientEmailResponse(BaseModel):
    """Patient email details"""
    subject: str
    greeting: str
    summary: str
    treatment_plan: str
    instructions: List[str]
    warning_signs: List[str]
    next_steps: str


class WorkflowResponse(BaseModel):
    """Complete workflow response"""
    workflow_id: str
    patient_id: str
    patient_name: str
    consultation_id: str
    status: WorkflowStatusEnum
    started_at: datetime
    completed_at: Optional[datetime] = None
    clinical_summary: Optional[ClinicalSummaryResponse] = None
    actions: List[ActionResponse]
    patient_email_sent: bool
    requires_approval: bool
    
    class Config:
        json_schema_extra = {
            "example": {
                "workflow_id": "WF-12345",
                "patient_id": "PT12345",
                "patient_name": "John Doe",
                "consultation_id": "CONS-12345",
                "status": "completed",
                "started_at": "2025-11-18T10:00:00Z",
                "completed_at": "2025-11-18T10:05:00Z",
                "actions": [],
                "patient_email_sent": True,
                "requires_approval": False
            }
        }


class ApprovalRequest(BaseModel):
    """Physician approval request"""
    workflow_id: str
    physician_id: str
    approved: bool
    modifications: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None


class DashboardResponse(BaseModel):
    """Physician dashboard data"""
    active_workflows: int
    pending_approvals: int
    total_alerts: int
    high_priority_alerts: int
    workflows: List[Dict[str, Any]]
    alerts: List[Dict[str, Any]]
    pending_approvals_list: List[Dict[str, Any]]


class HealthCheckResponse(BaseModel):
    """Health check response"""
    status: str
    timestamp: datetime
    version: str
    llm_available: bool

# ============================================================================
# DATA MODELS
# ============================================================================

class AgentStatus(Enum):
    """
    Status of an agent in the workflow
    """
    READY = "ready"              # Agent ready to process
    BUSY = "busy"                # Agent currently processing
    COMPLETED = "completed"      # Agent finished successfully
    ERROR = "error"              # Agent encountered error
    NOT_STARTED = "not_started"  # Agent hasn't been invoked yet
    WAITING = "waiting"          # Agent waiting for dependencies


@dataclass
class AgentHealthCheck:
    """
    Detailed health check result for an agent
    """
    agent_name: str
    status: AgentStatus
    current_step: str
    has_errors: bool
    error_messages: list
    last_update: Optional[datetime]
    is_responsive: bool
    processing_time_seconds: Optional[float]