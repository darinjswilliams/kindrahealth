from workflow_models.models import AgentState, WorkflowStatus
from typing import Dict, List
from data_models import ApprovalRequest
from workflow_models.models import ConsultationInput
from execution_models import (
    WorkflowExecution,
    ExecutionStatus,
    ActionExecution
)

from datetime import datetime

from executor_engine import PhysicianApprovalHandler


async def request_approval(
    workflow: WorkflowExecution,
    approval_handler: PhysicianApprovalHandler,
    agent_state: Dict
) -> ApprovalRequest:
    """
    Pause workflow and create approval request for physician
    
    Args:
        workflow: The WorkflowExecution object to pause
        approval_handler: Handler that manages pending approvals
        agent_state: The AgentState dict from LangGraph (contains clinical_summary, next_steps)
    
    Returns:
        ApprovalRequest: Structured approval request for physician dashboard
    
    Raises:
        ValueError: If workflow not in correct state for approval
        RuntimeError: If approval handler fails to register request
    
    PEAS Mapping:
        Performance Measure: <30 seconds to create and route approval request
        Environment: Physician approval queue, workflow state store
        Actuators: This function (pauses workflow, creates request)
        Sensors: Reads workflow state, reads agent outputs
    """
    
    # ========================================================================
    # STEP 1: VALIDATE WORKFLOW STATE
    # ========================================================================
    
    if workflow.status == ExecutionStatus.REQUIRES_APPROVAL:
        raise ValueError(
            f"Workflow {workflow.workflow_id} already awaiting approval"
        )
    
    if workflow.status == ExecutionStatus.COMPLETED:
        raise ValueError(
            f"Workflow {workflow.workflow_id} already completed - cannot request approval"
        )
    
    # ========================================================================
    # STEP 2: EXTRACT CLINICAL CONTEXT FROM AGENT STATE
    # ========================================================================
    
    clinical_summary = agent_state.get("clinical_summary")
    if not clinical_summary:
        raise ValueError(
            f"Cannot request approval - no clinical summary available for workflow {workflow.workflow_id}"
        )
    
    # Extract key clinical information for physician context
    chief_complaint = clinical_summary.chief_complaint
    diagnoses = [assessment["diagnosis"] for assessment in clinical_summary.assessments]
    icd_codes = clinical_summary.icd_codes
    
    # ========================================================================
    # STEP 3: IDENTIFY ACTIONS REQUIRING APPROVAL
    # ========================================================================
    
    actions_needing_approval = []
    
    for action in workflow.actions:
        if action.requires_physician_approval:
            actions_needing_approval.append({
                "action_id": action.action_id,
                "action_type": action.action_type,
                "description": action.description,
                "priority": "high" if action.requires_physician_approval else "normal",
                "timeline": getattr(action, 'timeline', 'Not specified'),
                "reason_for_approval": _determine_approval_reason(action)
            })
    
    if not actions_needing_approval:
        raise ValueError(
            f"No actions require approval in workflow {workflow.workflow_id}"
        )
    
    # ========================================================================
    # STEP 4: DETERMINE OVERALL PRIORITY
    # ========================================================================
    
    # Priority based on action types and clinical context
    priority = _calculate_request_priority(
        actions_needing_approval,
        diagnoses,
        clinical_summary
    )
    
    # ========================================================================
    # STEP 5: CREATE APPROVAL REQUEST
    # ========================================================================
    
    approval_request = ApprovalRequest(
        workflow_id=workflow.workflow_id,
        patient_id=workflow.patient_id,
        patient_name=workflow.patient_name,
        consultation_id=workflow.consultation_id,
        
        # Clinical context
        chief_complaint=chief_complaint,
        diagnoses=diagnoses,
        icd_codes=icd_codes,
        
        # Actions
        actions_requiring_approval=actions_needing_approval,
        total_actions=len(workflow.actions),
        
        # Metadata
        status="pending_approval",
        requested_at=datetime.now(),
        priority=priority,
        
        # Additional context
        clinical_summary_id=f"CS-{workflow.workflow_id}",
        physician_notes=None  # Will be filled when physician reviews
    )
    
    # ========================================================================
    # STEP 6: UPDATE WORKFLOW STATUS
    # ========================================================================
    
    workflow.status = ExecutionStatus.REQUIRES_APPROVAL
    
    # Add notification to workflow
    workflow.alerts.append({
        "type": "Approval Required",
        "message": f"{len(actions_needing_approval)} action(s) require physician approval",
        "priority": priority,
        "timestamp": datetime.now().isoformat()
    })
    
    # ========================================================================
    # STEP 7: REGISTER WITH APPROVAL HANDLER
    # ========================================================================
    
    try:
        # Register workflow in pending approval queue
        registered = approval_handler.request_approval(workflow)
        
        if not registered:
            raise RuntimeError(
                f"Failed to register workflow {workflow.workflow_id} with approval handler"
            )
        
    except Exception as e:
        # Rollback workflow status on failure
        workflow.status = ExecutionStatus.IN_PROGRESS
        workflow.alerts.pop()  # Remove the approval required alert
        
        raise RuntimeError(
            f"Error registering approval request: {str(e)}"
        ) from e
    
    # ========================================================================
    # STEP 8: LOG APPROVAL REQUEST
    # ========================================================================
    
    _log_approval_request(approval_request)
    
    # ========================================================================
    # STEP 9: NOTIFY PHYSICIAN (Optional - could be async)
    # ========================================================================
    
    # In production, you might send immediate notifications:
    # await notify_physician_urgent(approval_request) if priority == "high"
    # await send_dashboard_notification(approval_request)
    
    print(f"✅ Approval request created for workflow {workflow.workflow_id}")
    print(f"   Priority: {priority}")
    print(f"   Actions: {len(actions_needing_approval)}")
    print(f"   Patient: {workflow.patient_name}")
    
    return approval_request

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _determine_approval_reason(action: ActionExecution) -> str:
    """
    Determine why this action requires approval
    
    Args:
        action: The action requiring approval
    
    Returns:
        Human-readable reason string
    """
    reasons = []
    
    # High-risk action types
    high_risk_types = {
        "medication": "High-dose or controlled substance",
        "referral": "Specialist consultation recommended",
        "imaging": "Advanced imaging (MRI, CT) required",
        "procedure": "Invasive procedure recommended"
    }
    
    if action.action_type in high_risk_types:
        reasons.append(high_risk_types[action.action_type])
    
    # Check description for keywords
    if "STAT" in action.description.upper() or "URGENT" in action.description.upper():
        reasons.append("Urgent/STAT order")
    
    if "emergency" in action.description.lower():
        reasons.append("Emergency intervention")
    
    # Default reason
    if not reasons:
        reasons.append("High-priority clinical action")
    
    return "; ".join(reasons)


def _calculate_request_priority(
    actions: List[Dict],
    diagnoses: List[str],
    clinical_summary
) -> str:
    """
    Calculate overall priority of approval request
    
    Args:
        actions: List of actions requiring approval
        diagnoses: List of diagnosis strings
        clinical_summary: Clinical summary object
    
    Returns:
        Priority level: "high", "medium", or "low"
    """
    
    # HIGH PRIORITY CONDITIONS
    
    # 1. Check for emergency keywords in diagnoses
    # 2. For future reference retrieve from Database or Api that has a list of emergency keywords
    emergency_keywords = [
        "acute", "emergency", "critical", "severe", "life-threatening",
        "myocardial infarction", "stroke", "sepsis", "hemorrhage"
    ]
    
    for diagnosis in diagnoses:
        if any(keyword in diagnosis.lower() for keyword in emergency_keywords):
            return "high"
    
    # 2. Check for STAT or urgent actions
    for action in actions:
        desc_upper = action["description"].upper()
        if "STAT" in desc_upper or "URGENT" in desc_upper or "EMERGENCY" in desc_upper:
            return "high"
    
    # 3. Check for multiple high-risk actions
    if len(actions) >= 3:
        return "high"
    
    # MEDIUM PRIORITY CONDITIONS
    
    # 1. Referrals to specialists
    if any(action["action_type"] == "referral" for action in actions):
        return "medium"
    
    # 2. Advanced imaging
    if any(action["action_type"] == "imaging" for action in actions):
        return "medium"
    
    # 3. Multiple actions
    if len(actions) >= 2:
        return "medium"
    
    # DEFAULT: LOW PRIORITY
    return "low"


def _log_approval_request(approval_request: ApprovalRequest) -> None:
    """
    Log approval request for audit trail
    
    Args:
        approval_request: The approval request to log
    
    This satisfies HIPAA audit requirements by logging:
    - Who needs to approve (implicit - physician)
    - What needs approval (actions)
    - When request was made (timestamp)
    - Why approval needed (action details)
    """
    
    import logging
    logger = logging.getLogger("orchestrator.approval")
    
    logger.info(
        f"APPROVAL_REQUEST_CREATED",
        extra={
            "workflow_id": approval_request.workflow_id,
            "patient_id": approval_request.patient_id,
            "consultation_id": approval_request.consultation_id,
            "actions_count": len(approval_request.actions_requiring_approval),
            "priority": approval_request.priority,
            "timestamp": approval_request.requested_at.isoformat(),
            "diagnoses": approval_request.diagnoses,
            "icd_codes": approval_request.icd_codes
        }
    )

# ============================================================================
# USAGE EXAMPLE
# ============================================================================

async def example_usage():
    """
    Example of how request_approval() is called by the Orchestrator
    """
    from executor_engine import (
        HealthcareExecutionEngine,
    )

    from execution_models import (
        WorkflowExecution,
        ExecutionStatus,
        ActionExecution
    )   
    from langchain_openai import ChatOpenAI
    
    # Initialize
    llm = ChatOpenAI(model="gpt-4o", temperature=0.2)
    engine = HealthcareExecutionEngine(llm)
    
    # Simulate a workflow with high-priority actions
    workflow = WorkflowExecution(
        workflow_id="WF-12345",
        patient_id="PT-67890",
        patient_name="Jane Smith",
        consultation_id="CONS-12345",
        started_at=datetime.now(),
        status=ExecutionStatus.IN_PROGRESS
    )
    
    # Add high-priority action
    workflow.actions.append(
        ActionExecution(
            action_id="ACT-001",
            action_type="medication",
            description="Start high-dose steroid therapy",
            status=ExecutionStatus.PENDING,
            requires_physician_approval=True  # This triggers approval
        )
    )
    
    # Simulate agent state from LangGraph
    agent_state = {
        "clinical_summary": type('obj', (object,), {
            'chief_complaint': 'Severe asthma exacerbation',
            'assessments': [
                {'diagnosis': 'Acute severe asthma', 'icd_code': 'J45.51', 'severity': 'severe'}
            ],
            'icd_codes': ['J45.51']
        })(),
        "next_steps": workflow.actions
    }
    
    # Request approval
    approval_request = await approval(
        workflow=workflow,
        approval_handler=engine.approval_handler,
        agent_state=agent_state
    )
    
    print(f"\n✅ Approval Request Created:")
    print(f"   Workflow ID: {approval_request.workflow_id}")
    print(f"   Priority: {approval_request.priority}")
    print(f"   Actions: {len(approval_request.actions_requiring_approval)}")
    print(f"   Status: {workflow.status.value}")
    
    return approval_request


# ============================================================================
# TESTING
# ============================================================================

def test_request_approval():
    """Unit test for request_approval()"""
    import asyncio
    
    print("Running request_approval() test...")
    result = asyncio.run(example_usage())
    
    assert result.status == "pending_approval"
    assert result.priority in ["high", "medium", "low"]
    assert len(result.actions_requiring_approval) > 0
    
    print("\n✅ All tests passed!")


if __name__ == "__main__":
    test_request_approval()