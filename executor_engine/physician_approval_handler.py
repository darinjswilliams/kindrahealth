# ============================================================================
# PHYSICIAN APPROVAL HANDLER
# ============================================================================
from typing import Dict, Optional
from datetime import datetime
from execution_models.models import WorkflowExecution

class PhysicianApprovalHandler:
    """
    Manages physician review and approval workflows.
    Pauses execution until physician approves critical actions.
    """
    
    def __init__(self):
        self.pending_approvals: Dict[str, WorkflowExecution] = {}
    
    def request_approval(self, workflow: WorkflowExecution) -> Dict:
        """Request physician approval for workflow"""
        
        self.pending_approvals[workflow.workflow_id] = workflow
        
        approval_request = {
            "workflow_id": workflow.workflow_id,
            "patient_name": workflow.patient_name,
            "status": "pending_approval",
            "clinical_summary": workflow.clinical_summary_id,
            "actions": [
                {
                    "action_id": action.action_id,
                    "type": action.action_type,
                    "description": action.description,
                    "priority": "high" if action.requires_physician_approval else "normal"
                }
                for action in workflow.actions
            ],
            "requires_approval_for": [
                action.description
                for action in workflow.actions
                if action.requires_physician_approval
            ]
        }
        
        print(f"\n⏸️  Workflow {workflow.workflow_id} paused for physician approval")
        print(f"   Patient: {workflow.patient_name}")
        print(f"   Actions requiring approval: {len(approval_request['requires_approval_for'])}")
        
        return approval_request
    
    def approve_workflow(self, workflow_id: str, physician_id: str, modifications: Optional[Dict] = None) -> bool:
        """Physician approves workflow (with optional modifications)"""
        
        workflow = self.pending_approvals.get(workflow_id)
        if not workflow:
            return False
        
        print(f"\n✅ Workflow {workflow_id} approved by {physician_id}")
        
        # Apply any modifications
        if modifications:
            print(f"   📝 Modifications applied:")
            for key, value in modifications.items():
                print(f"      - {key}: {value}")
        
        # Mark actions as approved
        for action in workflow.actions:
            if action.requires_physician_approval:
                action.approved_by = physician_id
                action.approved_at = datetime.now()
        
        # Remove from pending
        del self.pending_approvals[workflow_id]
        
        return True