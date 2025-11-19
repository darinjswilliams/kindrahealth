# ============================================================================
# EDGE CASE TESTS
# ============================================================================
from healthcare_agents import ClinicalDocumentationAgent
from workflow_models.models import ConsultationInput
from execution_models.models import ExecutionStatus, WorkflowExecution
from executor_engine import HealthcareExecutionEngine
from unittest.mock import Mock, patch

import json
import asyncio
import pytest

class TestEdgeCases:
    """Test edge cases and boundary conditions"""
    
    def test_empty_consultation_notes(self, mock_llm):
        """Test handling of empty consultation notes"""
        agent = ClinicalDocumentationAgent(mock_llm)
        
        consultation = ConsultationInput(
            patient_name="Test Patient",
            patient_id="PT001",
            date_of_visit="2025-11-18",
            consultation_notes="",  # Empty notes
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
        
        # Mock minimal response
        mock_response = Mock()
        mock_response.content = json.dumps({
            "chief_complaint": "Not specified",
            "history_of_present_illness": "No information provided",
            "vital_signs": None,
            "physical_exam_findings": [],
            "assessments": [{"diagnosis": "Incomplete evaluation", "icd_code": "Z00.0", "severity": "mild"}],
            "icd_codes": ["Z00.0"],
            "additional_notes": "Insufficient information"
        })
        mock_llm.invoke.return_value = mock_response
        
        result = agent.process(state)
        
        assert result["clinical_summary"] is not None
        assert result["clinical_summary"].chief_complaint == "Not specified"
    
    def test_very_long_consultation_notes(self, mock_llm):
        """Test handling of very long consultation notes"""
        agent = ClinicalDocumentationAgent(mock_llm)
        
        # Create very long notes
        long_notes = "Patient presents with multiple complaints. " * 1000
        
        consultation = ConsultationInput(
            patient_name="Test Patient",
            patient_id="PT001",
            date_of_visit="2025-11-18",
            consultation_notes=long_notes,
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
            "chief_complaint": "Multiple complaints",
            "history_of_present_illness": "Complex history",
            "vital_signs": None,
            "physical_exam_findings": [],
            "assessments": [{"diagnosis": "Multiple conditions", "icd_code": "Z00.0", "severity": "mild"}],
            "icd_codes": ["Z00.0"],
            "additional_notes": "Extensive evaluation required"
        })
        mock_llm.invoke.return_value = mock_response
        
        result = agent.process(state)
        
        assert result["clinical_summary"] is not None
    
    @pytest.mark.asyncio
    async def test_concurrent_workflow_execution(self, mock_llm):
        """Test executing multiple workflows concurrently"""
        engine = HealthcareExecutionEngine(mock_llm)
        
        from workflow_models.models import ClinicalSummary, NextStepAction
        
        # Create multiple workflows
        workflows = []
        for i in range(5):
            workflow_state = {
                "consultation": ConsultationInput(
                    patient_name=f"Patient {i}",
                    patient_id=f"PT-{i:03d}",
                    date_of_visit="2025-11-18",
                    consultation_notes="Test concurrent execution",
                    physician_id="DR001"
                ),
                "clinical_summary": ClinicalSummary(
                    patient_name=f"Patient {i}",
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
                        description="Test lab",
                        priority="low",
                        timeline="1 week"
                    )
                ],
                "patient_email": None
            }
            workflows.append(workflow_state)
        
        # Execute concurrently
        with patch('asyncio.create_task'):
            results = await asyncio.gather(*[
                engine.execute_workflow(w, auto_approve=True) 
                for w in workflows
            ])
        
        assert len(results) == 5
        assert all(r.status == ExecutionStatus.COMPLETED for r in results)
        assert len(set(r.workflow_id for r in results)) == 5  # All unique IDs
    
    def test_special_characters_in_patient_name(self, mock_llm):
        """Test handling of special characters in patient data"""
        agent = ClinicalDocumentationAgent(mock_llm)
        
        consultation = ConsultationInput(
            patient_name="O'Brien-Smith, José María",
            patient_id="PT001",
            date_of_visit="2025-11-18",
            consultation_notes="Routine checkup",
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
            "chief_complaint": "Routine checkup",
            "history_of_present_illness": "No acute complaints",
            "vital_signs": None,
            "physical_exam_findings": [],
            "assessments": [{"diagnosis": "Healthy", "icd_code": "Z00.0", "severity": "mild"}],
            "icd_codes": ["Z00.0"],
            "additional_notes": None
        })
        mock_llm.invoke.return_value = mock_response
        
        result = agent.process(state)
        
        assert result["clinical_summary"] is not None
        assert result["clinical_summary"].patient_name == "O'Brien-Smith, José María"
