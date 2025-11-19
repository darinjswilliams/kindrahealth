# ============================================================================
# CLINICAL DOCUMENTATION AGENT TESTS
# ============================================================================
from healthcare_agents import ClinicalDocumentationAgent
from unittest.mock import Mock, patch
from workflow_models.models import WorkflowStatus

import json

class TestClinicalDocumentationAgent:
    """Test suite for Clinical Documentation Agent"""
    
    def test_initialization(self, mock_llm):
        """Test agent initializes correctly"""
        agent = ClinicalDocumentationAgent(mock_llm)
        assert agent.name == "ClinicalDocumentationAgent"
        assert agent.llm == mock_llm
    
    def test_process_valid_notes(self, mock_llm, sample_agent_state):
        """Test processing valid consultation notes"""
        agent = ClinicalDocumentationAgent(mock_llm)
        
        # Mock LLM response
        mock_response = Mock()
        mock_response.content = json.dumps({
            "chief_complaint": "Headache and elevated blood pressure",
            "history_of_present_illness": "Headaches started 1 week ago, progressively worsening",
            "vital_signs": "BP: 160/95, HR: 82, Temp: 98.6°F",
            "physical_exam_findings": [
                {"body_part": "Head", "finding": "No tenderness"}
            ],
            "assessments": [
                {"diagnosis": "Hypertension, uncontrolled", "icd_code": "I10", "severity": "moderate"}
            ],
            "icd_codes": ["I10"],
            "additional_notes": "Patient cooperative"
        })
        mock_llm.invoke.return_value = mock_response
        
        # Process
        result = agent.process(sample_agent_state)
        
        # Assertions
        assert result["clinical_summary"] is not None
        assert result["clinical_summary"].chief_complaint == "Headache and elevated blood pressure"
        assert result["clinical_summary"].icd_codes == ["I10"]
        assert len(result["messages"]) > 0
        assert "Successfully generated clinical summary" in result["messages"][0]
    
    def test_process_invalid_json(self, mock_llm, sample_agent_state):
        """Test handling of invalid JSON from LLM"""
        agent = ClinicalDocumentationAgent(mock_llm)
        
        # Mock invalid JSON response
        mock_response = Mock()
        mock_response.content = "This is not valid JSON"
        mock_llm.invoke.return_value = mock_response
        
        # Process
        result = agent.process(sample_agent_state)
        
        # Assertions
        assert result["status"] == WorkflowStatus.ERROR.value
        assert len(result["errors"]) > 0
        assert "Error processing clinical documentation" in result["errors"][0]
    
    def test_process_missing_required_fields(self, mock_llm, sample_agent_state):
        """Test handling of missing required fields in LLM response"""
        agent = ClinicalDocumentationAgent(mock_llm)
        
        # Mock incomplete response
        mock_response = Mock()
        mock_response.content = json.dumps({
            "chief_complaint": "Headache",
            # Missing required fields
        })
        mock_llm.invoke.return_value = mock_response
        
        # Process
        result = agent.process(sample_agent_state)
        
        # Should handle gracefully
        assert result["status"] == WorkflowStatus.ERROR.value