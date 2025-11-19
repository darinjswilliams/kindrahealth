# ============================================================================
# ORCHESTRATOR AGENT TESTS
# ============================================================================

from healthcare_agents import OrchestratorAgent
from workflow_models.models import WorkflowStatus

class TestOrchestratorAgent:
    """Test suite for Orchestrator Agent"""
    
    def test_initialization(self):
        """Test orchestrator initializes correctly"""
        orchestrator = OrchestratorAgent()
        assert orchestrator.name == "OrchestratorAgent"
    
    def test_initiate_workflow(self, sample_agent_state):
        """Test workflow initiation"""
        orchestrator = OrchestratorAgent()
        
        result = orchestrator.initiate_workflow(sample_agent_state)
        
        assert result["status"] == WorkflowStatus.PROCESSING.value
        assert result["current_agent"] == "ClinicalDocumentationAgent"
        assert len(result["messages"]) > 0
    
    def test_check_completion_error(self, sample_agent_state):
        """Test completion check with errors"""
        orchestrator = OrchestratorAgent()
        
        sample_agent_state["status"] = WorkflowStatus.ERROR.value
        sample_agent_state["errors"] = ["Test error"]
        
        result = orchestrator.check_completion(sample_agent_state)
        
        assert result == "error"
    
    def test_check_completion_awaiting_approval(self, sample_agent_state):
        """Test completion check when awaiting approval"""
        orchestrator = OrchestratorAgent()
        
        sample_agent_state["status"] = WorkflowStatus.AWAITING_APPROVAL.value
        
        result = orchestrator.check_completion(sample_agent_state)
        
        assert result == "awaiting_approval"
    
    def test_check_completion_completed(self, sample_agent_state):
        """Test completion check when completed"""
        orchestrator = OrchestratorAgent()
        
        sample_agent_state["status"] = WorkflowStatus.COMPLETED.value
        
        result = orchestrator.check_completion(sample_agent_state)
        
        assert result == "completed"