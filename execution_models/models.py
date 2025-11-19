from typing import Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum


class ExecutionStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    REQUIRES_APPROVAL = "requires_approval"


@dataclass
class ActionExecution:
    """Track execution of individual actions"""
    action_id: str
    action_type: str
    description: str
    status: ExecutionStatus
    scheduled_time: Optional[datetime] = None
    executed_time: Optional[datetime] = None
    result: Optional[Dict] = None
    error: Optional[str] = None
    requires_physician_approval: bool = False
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None


@dataclass
class WorkflowExecution:
    """Track entire workflow execution"""
    workflow_id: str
    patient_id: str
    patient_name: str
    consultation_id: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: ExecutionStatus = ExecutionStatus.PENDING
    
    # Agent execution results
    clinical_summary_id: Optional[str] = None
    actions: List[ActionExecution] = field(default_factory=list)
    patient_email_sent: bool = False
    
    # Monitoring data
    alerts: List[Dict] = field(default_factory=list)
    physician_notifications: List[Dict] = field(default_factory=list)