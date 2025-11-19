# ============================================================================
# HEALTHCARE EXECUTION ENGINE TESTS
# ============================================================================
from workflow_models.models import ConsultationInput
from execution_models import ExecutionStatus, WorkflowExecution
from executor_engine import HealthcareExecutionEngine
from unittest.mock import Mock, patch

import pytest
from datetime import datetime


class TestHealthcareExecutionEngine:
    """Test suite for Healthcare Execution Engine"""
    
    def test_initialization(self, mock_llm):
        """Test execution engine initializes correctly"""
        engine = HealthcareExecutionEngine(mock_llm)
        
        assert engine.llm == mock_llm
        assert engine.executor is not None
        assert engine.monitor is not None
        assert engine.approval_handler is not None
        assert len(engine.workflows) == 0
    
    @pytest.mark.asyncio
    async def test_execute_workflow_auto_approve(self, mock_llm):
        """Test workflow execution with auto-approval"""
        engine = HealthcareExecutionEngine(mock_llm)
        
        from workflow_models.models import ClinicalSummary, NextStepAction
        
        workflow_state = {
            "consultation": ConsultationInput(
                patient_name="Test Patient",
                patient_id="PT999",
                date_of_visit="2025-11-18",
                consultation_notes="Test notes",
                physician_id="DR001"
            ),
            "clinical_summary": ClinicalSummary(
                patient_name="Test Patient",
                visit_date="2025-11-18",
                chief_complaint="Test",
                history_of_present_illness="Test",
                physical_exam_findings=[],
                assessments=[{"diagnosis": "Test", "icd_code": "Z00.0", "severity": "mild"}],
                icd_codes=["Z00.0"]
            ),
            "next_steps": [
                NextStepAction(
                    action_type="lab",
                    description="Order CBC",
                    priority="medium",
                    timeline="48 hours"
                )
            ],
            "patient_email": None
        }
        
        # Execute with auto-approve
        with patch('asyncio.create_task'):  # Prevent actual monitoring tasks
            workflow = await engine.execute_workflow(workflow_state, auto_approve=True)
        
        assert workflow.status == ExecutionStatus.COMPLETED
        assert len(workflow.actions) == 1
        assert workflow.actions[0].status == ExecutionStatus.COMPLETED
    
    @pytest.mark.asyncio
    async def test_execute_workflow_requires_approval(self, mock_llm):
        """Test workflow execution requiring approval"""
        engine = HealthcareExecutionEngine(mock_llm)
        
        from workflow_models.models import ClinicalSummary, NextStepAction
        
        workflow_state = {
            "consultation": ConsultationInput(
                patient_name="Test Patient",
                patient_id="PT999",
                date_of_visit="2025-11-18",
                consultation_notes="Test notes",
                physician_id="DR001"
            ),
            "clinical_summary": ClinicalSummary(
                patient_name="Test Patient",
                visit_date="2025-11-18",
                chief_complaint="Test",
                history_of_present_illness="Test",
                physical_exam_findings=[],
                assessments=[{"diagnosis": "Test", "icd_code": "Z00.0", "severity": "mild"}],
                icd_codes=["Z00.0"]
            ),
            "next_steps": [
                NextStepAction(
                    action_type="medication",
                    description="High-dose medication",
                    priority="high",  # Requires approval
                    timeline="immediate"
                )
            ],
            "patient_email": None
        }
        
        # Execute without auto-approve
        workflow = await engine.execute_workflow(workflow_state, auto_approve=False)
        
        assert workflow.status == ExecutionStatus.REQUIRES_APPROVAL
        assert "WF-" in workflow.workflow_id
        assert workflow.actions[0].requires_physician_approval == True
    
    @pytest.mark.asyncio
    async def test_resume_after_approval(self, mock_llm):
        """Test resuming workflow after approval"""
        engine = HealthcareExecutionEngine(mock_llm)
        
        from workflow_models.models import ClinicalSummary, NextStepAction
        
        workflow_state = {
            "consultation": ConsultationInput(
                patient_name="Test Patient",
                patient_id="PT999",
                date_of_visit="2025-11-18",
                consultation_notes="Test notes",
                physician_id="DR001"
            ),
            "clinical_summary": ClinicalSummary(
                patient_name="Test Patient",
                visit_date="2025-11-18",
                chief_complaint="Test",
                history_of_present_illness="Test",
                physical_exam_findings=[],
                assessments=[{"diagnosis": "Test", "icd_code": "Z00.0", "severity": "mild"}],
                icd_codes=["Z00.0"]
            ),
            "next_steps": [
                NextStepAction(
                    action_type="medication",
                    description="Prescription",
                    priority="high",
                    timeline="immediate"
                )
            ],
            "patient_email": None
        }
        
        # Create workflow requiring approval
        workflow = await engine.execute_workflow(workflow_state, auto_approve=False)
        workflow_id = workflow.workflow_id
        
        # Resume after approval
        with patch('asyncio.create_task'):
            await engine.resume_after_approval(workflow_id, "DR_SMITH")
        
        assert engine.workflows[workflow_id].status == ExecutionStatus.COMPLETED
    
    def test_get_physician_dashboard(self, mock_llm):
        """Test generating physician dashboard data"""
        engine = HealthcareExecutionEngine(mock_llm)
        
        # Add some workflows
        workflow1 = WorkflowExecution(
            workflow_id="WF-001",
            patient_id="PT123",
            patient_name="John Doe",
            consultation_id="CONS-001",
            started_at=datetime.now(),
            status=ExecutionStatus.IN_PROGRESS
        )
        engine.workflows["WF-001"] = workflow1
        
        dashboard = engine.get_physician_dashboard()
        
        assert "active_workflows" in dashboard
        assert "pending_approvals" in dashboard
        assert "total_alerts" in dashboard
        assert dashboard["active_workflows"] == 1