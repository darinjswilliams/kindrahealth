# ============================================================================
# CARE COORDINATOR AGENT TESTS
# ============================================================================
from healthcare_agents import CareCoordinatorAgent
from unittest.mock import Mock, patch
from workflow_models.models import WorkflowStatus

import json

class TestCareCoordinatorAgent:
    """Test suite for Care Coordinator Agent"""
    
    def test_initialization(self, mock_llm):
        """Test agent initializes correctly"""
        agent = CareCoordinatorAgent(mock_llm)
        assert agent.name == "CareCoordinatorAgent"
        assert agent.llm == mock_llm
    
    def test_process_generates_actions(self, mock_llm, sample_agent_state):
        """Test generating action items from consultation"""
        agent = CareCoordinatorAgent(mock_llm)
        
        # Add clinical summary to state
        from workflow_models.models import ClinicalSummary
        sample_agent_state["clinical_summary"] = ClinicalSummary(
            patient_name="John Doe",
            visit_date="2025-11-18",
            chief_complaint="Headache",
            history_of_present_illness="Headaches for 1 week",
            physical_exam_findings=[],
            assessments=[{"diagnosis": "Hypertension", "icd_code": "I10", "severity": "moderate"}],
            icd_codes=["I10"]
        )
        
        # Mock LLM response
        mock_response = Mock()
        mock_response.content = json.dumps([
            {
                "action_type": "lab",
                "description": "Order Complete Blood Count (CBC)",
                "priority": "high",
                "timeline": "within 48 hours",
                "requires_scheduling": True
            },
            {
                "action_type": "medication",
                "description": "Start Lisinopril 10mg daily",
                "priority": "high",
                "timeline": "immediate",
                "requires_scheduling": False
            },
            {
                "action_type": "follow-up",
                "description": "Follow-up appointment in 2 weeks",
                "priority": "medium",
                "timeline": "2 weeks",
                "requires_scheduling": True
            }
        ])
        mock_llm.invoke.return_value = mock_response
        
        # Process
        result = agent.process(sample_agent_state)
        
        # Assertions
        assert result["next_steps"] is not None
        assert len(result["next_steps"]) == 3
        assert result["next_steps"][0].action_type == "lab"
        assert result["next_steps"][1].action_type == "medication"
        assert result["physician_approval_required"] == True  # Has high priority items
    
    def test_process_no_clinical_summary(self, mock_llm, sample_agent_state):
        """Test handling when clinical summary is missing"""
        agent = CareCoordinatorAgent(mock_llm)
        
        # Process without clinical summary
        result = agent.process(sample_agent_state)
        
        # Assertions
        assert result["status"] == WorkflowStatus.ERROR.value
        assert "No clinical summary available" in result["errors"][0]
    
    def test_prioritization_logic(self, mock_llm, sample_agent_state):
        """Test that high-priority actions require approval"""
        agent = CareCoordinatorAgent(mock_llm)
        
        from workflow_models.models import ClinicalSummary
        sample_agent_state["clinical_summary"] = ClinicalSummary(
            patient_name="John Doe",
            visit_date="2025-11-18",
            chief_complaint="Test",
            history_of_present_illness="Test",
            physical_exam_findings=[],
            assessments=[{"diagnosis": "Test", "icd_code": "Z00.0", "severity": "mild"}],
            icd_codes=["Z00.0"]
        )
        
        # Mock with low priority actions
        mock_response = Mock()
        mock_response.content = json.dumps([
            {
                "action_type": "education",
                "description": "Provide educational materials",
                "priority": "low",
                "timeline": "1 week",
                "requires_scheduling": False
            }
        ])
        mock_llm.invoke.return_value = mock_response
        
        result = agent.process(sample_agent_state)
        
        # Should not require approval for low priority
        assert result["physician_approval_required"] == False