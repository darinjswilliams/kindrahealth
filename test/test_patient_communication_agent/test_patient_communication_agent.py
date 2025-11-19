# ============================================================================
# PATIENT COMMUNICATION AGENT TESTS
# ============================================================================
from healthcare_agents import PatientCommunicationAgent
from workflow_models.models import WorkflowStatus
from unittest.mock import Mock


import json

class TestPatientCommunicationAgent:
    """Test suite for Patient Communication Agent"""
    
    def test_initialization(self, mock_llm):
        """Test agent initializes correctly"""
        agent = PatientCommunicationAgent(mock_llm)
        assert agent.name == "PatientCommunicationAgent"
    
    def test_generate_patient_email(self, mock_llm, sample_agent_state):
        """Test generating patient-friendly email"""
        agent = PatientCommunicationAgent(mock_llm)
        
        # Add clinical summary and next steps
        from workflow_models.models import ClinicalSummary, NextStepAction
        sample_agent_state["clinical_summary"] = ClinicalSummary(
            patient_name="John Doe",
            visit_date="2025-11-18",
            chief_complaint="Headache",
            history_of_present_illness="Headaches for 1 week",
            physical_exam_findings=[],
            assessments=[{"diagnosis": "Hypertension", "icd_code": "I10", "severity": "moderate"}],
            icd_codes=["I10"]
        )
        sample_agent_state["next_steps"] = [
            NextStepAction(
                action_type="medication",
                description="Start blood pressure medication",
                priority="high",
                timeline="immediate"
            )
        ]
        
        # Mock LLM response
        mock_response = Mock()
        mock_response.content = json.dumps({
            "subject": "Summary of Your Visit on 2025-11-18",
            "greeting": "Dear John,",
            "summary": "We discussed your headaches and blood pressure.",
            "treatment_plan": "We're starting you on medication to help control your blood pressure.",
            "instructions": ["Take medication daily", "Monitor blood pressure at home"],
            "warning_signs": ["Severe headache", "Vision changes"],
            "next_steps": "Follow-up in 2 weeks",
            "closing": "Please call if you have any questions."
        })
        mock_llm.invoke.return_value = mock_response
        
        # Process
        result = agent.process(sample_agent_state)
        
        # Assertions
        assert result["patient_email"] is not None
        assert result["patient_email"].subject == "Summary of Your Visit on 2025-11-18"
        assert len(result["patient_email"].instructions) == 2
        assert result["status"] == WorkflowStatus.AWAITING_APPROVAL.value or result["status"] == WorkflowStatus.COMPLETED.value
    
    def test_no_clinical_summary(self, mock_llm, sample_agent_state):
        """Test handling when clinical summary is missing"""
        agent = PatientCommunicationAgent(mock_llm)
        
        result = agent.process(sample_agent_state)
        
        assert result["status"] == WorkflowStatus.ERROR.value
        assert "No clinical summary available" in result["errors"][0]