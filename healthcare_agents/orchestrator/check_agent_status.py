# ============================================================================
# IMPLEMENTATION
# ============================================================================
from data_models.agent_models import AgentHealthCheck, AgentStatus
from typing import Dict, Optional
from datetime import datetime

def check_status(agent_state: Dict, agent_name: str) -> AgentHealthCheck:
    """
    Check if agent is available and responsive
    
    Args:
        agent_state: The AgentState dict from LangGraph containing:
            - status: Overall workflow status
            - current_agent: Which agent is currently active
            - errors: List of error messages
            - messages: Agent execution log
            - clinical_summary: Output from Clinical Agent
            - next_steps: Output from Care Coordinator Agent
            - patient_email: Output from Patient Communication Agent
        
        agent_name: Name of agent to check. Valid values:
            - "ClinicalDocumentationAgent"
            - "CareCoordinatorAgent"
            - "PatientCommunicationAgent"
            - "OrchestratorAgent"
    
    Returns:
        AgentHealthCheck: Detailed status information
    
    PEAS Mapping:
        Performance Measure: <100ms to check agent status
        Environment: AgentState dict, agent execution log
        Actuators: None (this is a sensor/read-only function)
        Sensors: Reads agent_state fields (status, current_agent, errors, outputs)
    
    Example:
        >>> state = {"current_agent": "ClinicalDocumentationAgent", "status": "processing"}
        >>> health = check_agent_status(state, "ClinicalDocumentationAgent")
        >>> print(health.status)
        AgentStatus.BUSY
    """
    
    # ========================================================================
    # STEP 1: VALIDATE INPUT
    # ========================================================================
    
    valid_agents = [
        "ClinicalDocumentationAgent",
        "CareCoordinatorAgent", 
        "PatientCommunicationAgent",
        "OrchestratorAgent"
    ]
    
    if agent_name not in valid_agents:
        raise ValueError(
            f"Invalid agent name: {agent_name}. Must be one of {valid_agents}"
        )
    
    # ========================================================================
    # STEP 2: READ AGENT STATE
    # ========================================================================
    
    current_agent = agent_state.get("current_agent", "")
    workflow_status = agent_state.get("status", "")
    errors = agent_state.get("errors", [])
    messages = agent_state.get("messages", [])
    
    # ========================================================================
    # STEP 3: DETERMINE AGENT STATUS
    # ========================================================================
    
    status = _determine_agent_status(
        agent_name=agent_name,
        current_agent=current_agent,
        workflow_status=workflow_status,
        agent_state=agent_state
    )
    
    # ========================================================================
    # STEP 4: CHECK FOR ERRORS
    # ========================================================================
    
    agent_errors = [
        error for error in errors 
        if agent_name in error or _is_agent_error(error, agent_name)
    ]
    
    has_errors = len(agent_errors) > 0
    
    # ========================================================================
    # STEP 5: CALCULATE PROCESSING TIME (if available)
    # ========================================================================
    
    processing_time = _calculate_processing_time(agent_name, messages)
    
    # ========================================================================
    # STEP 6: CHECK RESPONSIVENESS
    # ========================================================================
    
    is_responsive = _check_responsiveness(
        agent_name=agent_name,
        status=status,
        has_errors=has_errors,
        processing_time=processing_time
    )
    
    # ========================================================================
    # STEP 7: CREATE HEALTH CHECK RESULT
    # ========================================================================
    
    health_check = AgentHealthCheck(
        agent_name=agent_name,
        status=status,
        current_step=current_agent,
        has_errors=has_errors,
        error_messages=agent_errors,
        last_update=datetime.now(),
        is_responsive=is_responsive,
        processing_time_seconds=processing_time
    )
    
    return health_check


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _determine_agent_status(
    agent_name: str,
    current_agent: str,
    workflow_status: str,
    agent_state: Dict
) -> AgentStatus:
    """
    Determine the current status of an agent based on state
    
    Logic:
    1. If current_agent == agent_name → BUSY
    2. If agent has produced output → COMPLETED
    3. If workflow has errors mentioning agent → ERROR
    4. If workflow_status == "error" → ERROR
    5. If agent hasn't run yet → NOT_STARTED
    6. If agent waiting for another agent → WAITING
    """
    
    # Check if this agent is currently active
    if current_agent == agent_name:
        return AgentStatus.BUSY
    
    # Check if agent has completed by looking for its output
    agent_outputs = {
        "ClinicalDocumentationAgent": "clinical_summary",
        "CareCoordinatorAgent": "next_steps",
        "PatientCommunicationAgent": "patient_email"
    }
    
    if agent_name in agent_outputs:
        output_field = agent_outputs[agent_name]
        if agent_state.get(output_field) is not None:
            return AgentStatus.COMPLETED
    
    # Check for errors
    errors = agent_state.get("errors", [])
    if any(agent_name in error for error in errors):
        return AgentStatus.ERROR
    
    if workflow_status == "error":
        return AgentStatus.ERROR
    
    # Check execution order to determine if agent is waiting
    agent_order = [
        "OrchestratorAgent",
        "ClinicalDocumentationAgent",
        "CareCoordinatorAgent",
        "PatientCommunicationAgent"
    ]
    
    try:
        current_index = agent_order.index(current_agent) if current_agent in agent_order else 0
        agent_index = agent_order.index(agent_name)
        
        # If agent comes after current agent, it's waiting
        if agent_index > current_index:
            return AgentStatus.WAITING
        
        # If agent comes before current agent but has no output, it's an error
        if agent_index < current_index and agent_state.get(agent_outputs.get(agent_name)) is None:
            return AgentStatus.ERROR
        
    except (ValueError, KeyError):
        pass
    
    # Default: not started
    return AgentStatus.NOT_STARTED


def _is_agent_error(error_message: str, agent_name: str) -> bool:
    """
    Check if error message is related to specific agent
    
    Args:
        error_message: Error message string
        agent_name: Name of agent to check
    
    Returns:
        True if error is related to this agent
    """
    
    # Extract short name (e.g., "Clinical" from "ClinicalDocumentationAgent")
    short_names = {
        "ClinicalDocumentationAgent": ["clinical", "documentation"],
        "CareCoordinatorAgent": ["care", "coordinator"],
        "PatientCommunicationAgent": ["patient", "communication", "email"],
        "OrchestratorAgent": ["orchestrator", "workflow"]
    }
    
    keywords = short_names.get(agent_name, [])
    error_lower = error_message.lower()
    
    return any(keyword in error_lower for keyword in keywords)


def _calculate_processing_time(agent_name: str, messages: list) -> Optional[float]:
    """
    Calculate how long agent has been processing (if currently busy)
    
    Args:
        agent_name: Name of agent
        messages: List of agent messages from state
    
    Returns:
        Processing time in seconds, or None if not applicable
    """
    
    # Look for start message
    start_message = None
    for msg in messages:
        if agent_name in msg and ("started" in msg.lower() or "processing" in msg.lower()):
            start_message = msg
            break
    
    if start_message:
        # In production, you'd extract timestamp from message
        # For now, return None as we don't have timestamps in messages
        return None
    
    return None


def _check_responsiveness(
    agent_name: str,
    status: AgentStatus,
    has_errors: bool,
    processing_time: Optional[float]
) -> bool:
    """
    Determine if agent is responsive
    
    An agent is considered responsive if:
    1. It's not in ERROR state
    2. If BUSY, processing time is within acceptable limits
    3. It's progressing through the workflow
    
    Args:
        agent_name: Name of agent
        status: Current agent status
        has_errors: Whether agent has errors
        processing_time: How long agent has been processing
    
    Returns:
        True if agent is responsive, False otherwise
    """
    
    # Agent with errors is not responsive
    if has_errors or status == AgentStatus.ERROR:
        return False
    
    # Completed agents are responsive
    if status == AgentStatus.COMPLETED:
        return True
    
    # Check processing time for busy agents
    if status == AgentStatus.BUSY:
        if processing_time is not None:
            # Define timeout thresholds per agent
            timeouts = {
                "ClinicalDocumentationAgent": 10.0,  # 10 seconds
                "CareCoordinatorAgent": 15.0,        # 15 seconds
                "PatientCommunicationAgent": 10.0,   # 10 seconds
                "OrchestratorAgent": 5.0             # 5 seconds
            }
            
            timeout = timeouts.get(agent_name, 30.0)
            
            # If processing time exceeds timeout, not responsive
            if processing_time > timeout:
                return False
        
        # If no timing info, assume responsive
        return True
    
    # Waiting and not-started agents are responsive (not their turn yet)
    if status in [AgentStatus.WAITING, AgentStatus.NOT_STARTED]:
        return True
    
    # Default: responsive
    return True


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def check_all_agents(agent_state: Dict) -> Dict[str, AgentHealthCheck]:
    """
    Check status of all agents in the workflow
    
    Args:
        agent_state: The AgentState dict
    
    Returns:
        Dictionary mapping agent names to their health checks
    """
    
    agents = [
        "ClinicalDocumentationAgent",
        "CareCoordinatorAgent",
        "PatientCommunicationAgent",
        "OrchestratorAgent"
    ]
    
    health_checks = {}
    for agent in agents:
        health_checks[agent] = check_status(agent_state, agent)
    
    return health_checks


def is_workflow_healthy(agent_state: Dict) -> bool:
    """
    Check if entire workflow is healthy (all agents responsive, no errors)
    
    Args:
        agent_state: The AgentState dict
    
    Returns:
        True if workflow is healthy, False otherwise
    """
    
    health_checks = check_all_agents(agent_state)
    
    for agent_name, health in health_checks.items():
        if health.has_errors or not health.is_responsive:
            return False
    
    return True


# ============================================================================
# USAGE EXAMPLES
# ============================================================================

def example_usage():
    """Examples of using check_agent_status()"""
    
    # Example 1: Agent currently processing
    state_busy = {
        "current_agent": "ClinicalDocumentationAgent",
        "status": "processing",
        "errors": [],
        "messages": ["ClinicalDocumentationAgent: Processing consultation notes"],
        "clinical_summary": None,
        "next_steps": None,
        "patient_email": None
    }
    
    health = check_status(state_busy, "ClinicalDocumentationAgent")
    print(f"Example 1 - Busy Agent:")
    print(f"  Status: {health.status.value}")
    print(f"  Responsive: {health.is_responsive}")
    print(f"  Errors: {health.has_errors}\n")
    
    # Example 2: Agent completed
    state_completed = {
        "current_agent": "CareCoordinatorAgent",
        "status": "processing",
        "errors": [],
        "messages": ["ClinicalDocumentationAgent: Successfully generated clinical summary"],
        "clinical_summary": {"patient_name": "John Doe", "chief_complaint": "Headache"},
        "next_steps": None,
        "patient_email": None
    }
    
    health = check_status(state_completed, "ClinicalDocumentationAgent")
    print(f"Example 2 - Completed Agent:")
    print(f"  Status: {health.status.value}")
    print(f"  Responsive: {health.is_responsive}")
    print(f"  Errors: {health.has_errors}\n")
    
    # Example 3: Agent with error
    state_error = {
        "current_agent": "ClinicalDocumentationAgent",
        "status": "error",
        "errors": ["ClinicalDocumentationAgent: Error processing clinical documentation - Invalid JSON"],
        "messages": [],
        "clinical_summary": None,
        "next_steps": None,
        "patient_email": None
    }
    
    health = check_status(state_error, "ClinicalDocumentationAgent")
    print(f"Example 3 - Agent with Error:")
    print(f"  Status: {health.status.value}")
    print(f"  Responsive: {health.is_responsive}")
    print(f"  Errors: {health.has_errors}")
    print(f"  Error Messages: {health.error_messages}\n")
    
    # Example 4: Agent waiting
    state_waiting = {
        "current_agent": "ClinicalDocumentationAgent",
        "status": "processing",
        "errors": [],
        "messages": [],
        "clinical_summary": None,
        "next_steps": None,
        "patient_email": None
    }
    
    health = check_status(state_waiting, "CareCoordinatorAgent")
    print(f"Example 4 - Waiting Agent:")
    print(f"  Status: {health.status.value}")
    print(f"  Responsive: {health.is_responsive}")
    print(f"  Errors: {health.has_errors}\n")
    
    # Example 5: Check all agents
    print("Example 5 - Check All Agents:")
    all_health = check_all_agents(state_completed)
    for agent_name, health in all_health.items():
        print(f"  {agent_name}: {health.status.value}")
    
    print(f"\n  Workflow Healthy: {is_workflow_healthy(state_completed)}")


# ============================================================================
# TESTING
# ============================================================================

def test_check_agent_status():
    """Unit tests for check_agent_status()"""
    
    print("Running check_agent_status() tests...\n")
    
    # Test 1: Busy agent
    state = {"current_agent": "ClinicalDocumentationAgent", "status": "processing", "errors": []}
    health = check_status(state, "ClinicalDocumentationAgent")
    assert health.status == AgentStatus.BUSY
    print("✅ Test 1 passed: Busy agent detected")
    
    # Test 2: Completed agent
    state = {
        "current_agent": "CareCoordinatorAgent",
        "clinical_summary": {"patient_name": "Test"},
        "errors": []
    }
    health = check_status(state, "ClinicalDocumentationAgent")
    assert health.status == AgentStatus.COMPLETED
    print("✅ Test 2 passed: Completed agent detected")
    
    # Test 3: Error agent
    state = {
        "current_agent": "ClinicalDocumentationAgent",
        "status": "error",
        "errors": ["ClinicalDocumentationAgent: Error"]
    }
    health = check_status(state, "ClinicalDocumentationAgent")
    assert health.status == AgentStatus.ERROR
    assert health.has_errors == True
    print("✅ Test 3 passed: Error agent detected")
    
    # Test 4: Invalid agent name
    try:
        check_status(state, "InvalidAgent")
        assert False, "Should have raised ValueError"
    except ValueError:
        print("✅ Test 4 passed: Invalid agent name rejected")
    
    print("\n✅ All tests passed!")


if __name__ == "__main__":
    print("="*60)
    print("USAGE EXAMPLES")
    print("="*60 + "\n")
    example_usage()
    
    print("\n" + "="*60)
    print("UNIT TESTS")
    print("="*60 + "\n")
    test_check_agent_status()