# ============================================================================
# PHYSICIAN APPROVAL HANDLER TESTS
# ============================================================================
from executor_engine import PhysicianApprovalHandler
from execution_models import WorkflowExecution, ActionExecution, ExecutionStatus

from datetime import datetime


class TestPhysicianApprovalHandler:
    """Test suite for Physician Approval Handler"""
    
    def test_initialization(self):
        """Test approval handler initializes correctly"""
        handler = PhysicianApprovalHandler()
        
        assert len(handler.pending_approvals) == 0
    
    def test_request_approval(self):
        """Test requesting physician approval"""
        handler = PhysicianApprovalHandler()
        
        workflow = WorkflowExecution(
            workflow_id="WF-004",
            patient_id="PT123",
            patient_name="Jane Smith",
            consultation_id="CONS-004",
            started_at=datetime.now()
        )
        
        # Add actions requiring approval
        workflow.actions.append(ActionExecution(
            action_id="ACT-001",
            action_type="medication",
            description="Start high-dose steroid",
            status=ExecutionStatus.PENDING,
            requires_physician_approval=True
        ))
        
        approval_request = handler.request_approval(workflow)
        
        assert "WF-004" in handler.pending_approvals
        assert approval_request["status"] == "pending_approval"
        assert len(approval_request["requires_approval_for"]) == 1
    
    def test_approve_workflow(self):
        """Test approving workflow"""
        handler = PhysicianApprovalHandler()
        
        workflow = WorkflowExecution(
            workflow_id="WF-005",
            patient_id="PT123",
            patient_name="Jane Smith",
            consultation_id="CONS-005",
            started_at=datetime.now()
        )
        
        action = ActionExecution(
            action_id="ACT-001",
            action_type="medication",
            description="Prescription",
            status=ExecutionStatus.PENDING,
            requires_physician_approval=True
        )
        workflow.actions.append(action)
        
        handler.request_approval(workflow)
        
        # Approve
        result = handler.approve_workflow("WF-005", "DR_SMITH")
        
        assert result == True
        assert "WF-005" not in handler.pending_approvals
        assert action.approved_by == "DR_SMITH"
        assert action.approved_at is not None
    
    def test_approve_nonexistent_workflow(self):
        """Test approving workflow that doesn't exist"""
        handler = PhysicianApprovalHandler()
        
        result = handler.approve_workflow("WF-NONEXISTENT", "DR_SMITH")
        
        assert result == False