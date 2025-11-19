import pytest
from fastapi.testclient import TestClient
from api.server import app, clerk_guard
from fastapi_clerk_auth import HTTPAuthorizationCredentials

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
from typing import Dict, List

# Import the classes from the agent system
import sys
sys.path.append('..')

from healthcare_agents import (
    ClinicalDocumentationAgent,
    CareCoordinatorAgent,
    PatientCommunicationAgent,
    OrchestratorAgent  
)

from workflow_models import (
    ConsultationInput,
    WorkflowStatus,
    AgentState
)

from executor_engine import (
    ActionExecutor,
    MonitoringAgent,
    PhysicianApprovalHandler,
    HealthcareExecutionEngine
)

from execution_models import (
    ActionExecution,
    WorkflowExecution,
    ExecutionStatus
)

class MockCredentials:
    """Mock credentials with decoded claims"""
    def __init__(self):
        self.scheme = "Bearer"
        self.credentials = "test-token"
        self.decoded = {"sub": "test-user-id"}

@pytest.fixture(scope="session")
def client():
    """Test client with mocked authentication"""
    
    # Override Clerk dependency to bypass auth
    app.dependency_overrides[clerk_guard] = lambda: MockCredentials()
    
    yield TestClient(app)
    
    # Cleanup
    app.dependency_overrides.clear()


@pytest.fixture
def mock_llm():
    """Mock LLM for testing"""
    llm = Mock()
    llm.invoke = Mock()
    return llm


@pytest.fixture
def sample_consultation():
    """Sample consultation input"""
    return ConsultationInput(
        patient_name="John Doe",
        patient_id="PT12345",
        date_of_visit="2025-11-18",
        consultation_notes="""
Patient presents with persistent headache and elevated blood pressure.
BP: 160/95, HR: 82, Temp: 98.6°F
History: Headaches started 1 week ago, worsening.
Assessment: Hypertension, uncontrolled
Plan: Start antihypertensive, order labs (CBC, BMP), follow-up in 2 weeks
""",
        physician_id="DR001"
    )


@pytest.fixture
def sample_agent_state(sample_consultation):
    """Sample agent state"""
    return {
        "consultation": sample_consultation,
        "clinical_summary": None,
        "next_steps": None,
        "patient_email": None,
        "status": WorkflowStatus.INITIATED.value,
        "current_agent": "OrchestratorAgent",
        "errors": [],
        "physician_approval_required": False,
        "physician_approved": False,
        "messages": [],
        "executed_actions": []
    }


@pytest.fixture
def sample_action_execution():
    """Sample action execution"""
    return ActionExecution(
        action_id="ACT-001",
        action_type="lab",
        description="Order Complete Blood Count (CBC)",
        status=ExecutionStatus.PENDING,
        requires_physician_approval=False
    )