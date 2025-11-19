# ============================================================================
# INTEGRATION TESTS
# ============================================================================
import pytest
from unittest.mock import Mock, patch
import json

# Import the classes from the agent system
import sys
sys.path.append('..')

from healthcare_agents import (
    ClinicalDocumentationAgent,
    CareCoordinatorAgent,
    PatientCommunicationAgent,
    OrchestratorAgent
)

from workflow_models import(
    ConsultationInput

)

from execution_models import (
    ExecutionStatus
)

from executor_engine import (
    HealthcareExecutionEngine
    
)

class TestIntegration:
    """Integration tests for complete workflows"""
    
    @pytest.mark.asyncio
    async def test_end_to_end_workflow(self, mock_llm):
        """Test complete end-to-end workflow"""
        # This would test the entire flow from consultation input to execution
        # For brevity, outline the test structure:
        
        # 1. Create consultation input
        consultation = ConsultationInput(
            patient_name="Integration Test Patient",
            patient_id="PT-INT-001",
            date_of_visit="2025-11-18",
            consultation_notes="""
Patient presents with chest pain and shortness of breath.
BP: 145/90, HR: 95, RR: 22, O2 Sat: 96%
Pain started 2 hours ago, radiating to left arm.
Assessment: Possible acute coronary syndrome
Plan: Immediate EKG, cardiac enzymes, chest X-ray, cardiology consult
""",
            physician_id="DR001"
        )
        
        # 2. Mock LLM responses for all agents
        clinical_response = Mock()
        clinical_response.content = json.dumps({
            "chief_complaint": "Chest pain with shortness of breath",
            "history_of_present_illness": "Chest pain started 2 hours ago, radiating to left arm",
            "vital_signs": "BP: 145/90, HR: 95, RR: 22, O2 Sat: 96%",
            "physical_exam_findings": [
                {"body_part": "Chest", "finding": "No visible trauma"}
            ],
            "assessments": [
                {"diagnosis": "Acute coronary syndrome, suspected", "icd_code": "I24.9", "severity": "severe"}
            ],
            "icd_codes": ["I24.9"],
            "additional_notes": "Emergency evaluation required"
        })
        
        care_response = Mock()
        care_response.content = json.dumps([
            {
                "action_type": "diagnostic",
                "description": "Immediate EKG",
                "priority": "high",
                "timeline": "STAT",
                "requires_scheduling": False
            },
            {
                "action_type": "lab",
                "description": "Cardiac enzymes (Troponin, CK-MB)",
                "priority": "high",
                "timeline": "STAT",
                "requires_scheduling": False
            },
            {
                "action_type": "referral",
                "description": "Emergency cardiology consult",
                "priority": "high",
                "timeline": "immediate",
                "requires_scheduling": True
            }
        ])
        
        comm_response = Mock()
        comm_response.content = json.dumps({
            "subject": "Important: Your Emergency Visit Summary",
            "greeting": "Dear Integration Test Patient,",
            "summary": "You were evaluated for chest pain today.",
            "treatment_plan": "We are conducting urgent tests to evaluate your heart.",
            "instructions": ["Remain in the emergency department", "Do not eat or drink"],
            "warning_signs": ["Worsening chest pain", "Difficulty breathing"],
            "next_steps": "Cardiology will see you within the hour",
            "closing": "We are monitoring you closely."
        })
        
        # Configure mock to return different responses
        mock_llm.invoke.side_effect = [clinical_response, care_response, comm_response]
        
        # 3. Initialize execution engine
        engine = HealthcareExecutionEngine(mock_llm)
        
        # 4. Create initial state
        from workflow.healthcare_workflow import create_healthcare_workflow
        
        initial_state = {
            "consultation": consultation,
            "clinical_summary": None,
            "next_steps": None,
            "patient_email": None,
            "status": "initiated",
            "current_agent": "OrchestratorAgent",
            "errors": [],
            "physician_approval_required": False,
            "physician_approved": False,
            "messages": [],
            "executed_actions": []
        }
        
        # 5. Run agents
        clinical_agent = ClinicalDocumentationAgent(mock_llm)
        state_after_clinical = clinical_agent.process(initial_state)
        
        assert state_after_clinical["clinical_summary"] is not None
        assert "I24.9" in state_after_clinical["clinical_summary"].icd_codes
        
        care_agent = CareCoordinatorAgent(mock_llm)
        state_after_care = care_agent.process(state_after_clinical)
        
        assert state_after_care["next_steps"] is not None
        assert len(state_after_care["next_steps"]) == 3
        assert state_after_care["physician_approval_required"] == True
        
        comm_agent = PatientCommunicationAgent(mock_llm)
        state_after_comm = comm_agent.process(state_after_care)
        
        assert state_after_comm["patient_email"] is not None
        
        # 6. Execute workflow
        with patch('asyncio.create_task'):
            workflow = await engine.execute_workflow(state_after_comm, auto_approve=True)
        
        assert workflow.status == ExecutionStatus.COMPLETED
        assert len(workflow.actions) == 3
        assert all(a.status == ExecutionStatus.COMPLETED for a in workflow.actions)
    
    @pytest.mark.asyncio
    async def test_error_recovery_workflow(self, mock_llm):
        """Test workflow error recovery"""
        engine = HealthcareExecutionEngine(mock_llm)
        
        from workflow_models.models import ClinicalSummary, NextStepAction
        
        workflow_state = {
            "consultation": ConsultationInput(
                patient_name="Error Test Patient",
                patient_id="PT-ERR-001",
                date_of_visit="2025-11-18",
                consultation_notes="Test error handling",
                physician_id="DR001"
            ),
            "clinical_summary": ClinicalSummary(
                patient_name="Error Test Patient",
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
                    description="Test lab order",
                    priority="medium",
                    timeline="48 hours"
                )
            ],
            "patient_email": None
        }
        
        # Mock a failure in one executor
        with patch.object(engine.executor, 'execute_lab_order', side_effect=Exception("Lab system unavailable")):
            with patch('asyncio.create_task'):
                workflow = await engine.execute_workflow(workflow_state, auto_approve=True)
        
        # Workflow should complete even if one action fails
        assert workflow.workflow_id is not None
        assert workflow.actions[0].status == ExecutionStatus.FAILED
        assert workflow.actions[0].error == "Lab system unavailable"