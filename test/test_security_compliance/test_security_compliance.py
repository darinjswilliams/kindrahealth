# ============================================================================
# SECURITY AND COMPLIANCE TESTS
# ============================================================================
from healthcare_agents import ClinicalDocumentationAgent
from workflow_models.models import ConsultationInput
from executor_engine import HealthcareExecutionEngine
from unittest.mock import Mock, patch

import json
import asyncio

class TestSecurityCompliance:
    """Test security and HIPAA compliance features"""
    
    def test_phi_not_in_logs(self, mock_llm, capsys):
        """Test that PHI is not exposed in logs"""
        agent = ClinicalDocumentationAgent(mock_llm)
        
        consultation = ConsultationInput(
            patient_name="Sensitive Patient Name",
            patient_id="SSN-123-45-6789",  # Should never appear in logs
            date_of_visit="2025-11-18",
            consultation_notes="Patient has HIV and diabetes",
            physician_id="DR001"
        )
        
        state = {
            "consultation": consultation,
            "clinical_summary": None,
            "next_steps": None,
            "patient_email": None,
            "status": "initiated",
            "current_agent": "ClinicalDocumentationAgent",
            "errors": [],
            "physician_approval_required": False,
            "physician_approved": False,
            "messages": [],
            "executed_actions": []
        }
        
        mock_response = Mock()
        mock_response.content = json.dumps({
            "chief_complaint": "Medical conditions",
            "history_of_present_illness": "Ongoing treatment",
            "vital_signs": None,
            "physical_exam_findings": [],
            "assessments": [{"diagnosis": "Multiple conditions", "icd_code": "E11.9", "severity": "moderate"}],
            "icd_codes": ["E11.9"],
            "additional_notes": None
        })
        mock_llm.invoke.return_value = mock_response
        
        result = agent.process(state)
        
        # Capture output
        captured = capsys.readouterr()
        
        # SSN should not appear in logs
        assert "SSN-123-45-6789" not in captured.out
    
    def test_audit_trail_completeness(self, mock_llm):
        """Test that all actions are auditable"""
        from workflow_models.models import ClinicalSummary, NextStepAction
        
        engine = HealthcareExecutionEngine(mock_llm)
        
        workflow_state = {
            "consultation": ConsultationInput(
                patient_name="Audit Test Patient",
                patient_id="PT-AUDIT-001",
                date_of_visit="2025-11-18",
                consultation_notes="Audit trail test",
                physician_id="DR001"
            ),
            "clinical_summary": ClinicalSummary(
                patient_name="Audit Test Patient",
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
                    description="Audit test",
                    priority="low",
                    timeline="1 week"
                )
            ],
            "patient_email": None
        }
        
        # Execute
        async def run_test():
            with patch('asyncio.create_task'):
                workflow = await engine.execute_workflow(workflow_state, auto_approve=True)
            return workflow
        
        workflow = asyncio.run(run_test())
        
        # Check audit trail
        assert workflow.started_at is not None
        assert workflow.completed_at is not None
        for action in workflow.actions:
            assert action.executed_time is not None
            assert action.result is not None