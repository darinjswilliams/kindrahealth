# ============================================================================
# ORCHESTRATOR IMPLEMENTATION
# ============================================================================
from workflow_models.models import AgentState
from healthcare_agents import ClinicalDocumentationAgent
from langchain_openai import ChatOpenAI
from datetime import datetime


async def route_to_clinical(state: AgentState, llm: ChatOpenAI) -> AgentState:
    """
    Delegate clinical documentation task to Clinical Agent
    
    This function:
    1. Validates that workflow is ready for clinical agent
    2. Instantiates Clinical Documentation Agent
    3. Passes consultation notes to the agent
    4. Receives structured clinical summary back
    5. Updates AgentState with results
    6. Routes to next agent (Care Coordinator)
    
    Args:
        state: Current AgentState containing consultation input
        llm: Language model for Clinical Agent to use
    
    Returns:
        Updated AgentState with clinical_summary populated
    
    PEAS Mapping:
        Performance Measure: <5 seconds to route and receive response
        Environment: Clinical Agent instance, AgentState
        Actuators: Instantiate agent, invoke agent.process(), update state
        Sensors: Read state.consultation, read agent response
    
    Workflow Position:
        Orchestrator.initiate_workflow() 
            → THIS FUNCTION (route_to_clinical)
            → Orchestrator.route_to_care_coordinator()
    """
    
    # ========================================================================
    # STEP 1: VALIDATE STATE
    # ========================================================================
    
    print(f"\n{'='*60}")
    print(f"🔵 ORCHESTRATOR: Routing to Clinical Documentation Agent")
    print(f"{'='*60}")
    
    # Check that consultation input exists
    if not state.get("consultation"):
        error_msg = "Cannot route to clinical agent - no consultation input"
        print(f"❌ {error_msg}")
        return {
            **state,
            "status": "error",
            "errors": [error_msg],
            "messages": [f"Orchestrator: {error_msg}"]
        }
    
    consultation = state["consultation"]
    
    # Log routing action
    print(f"📋 Patient: {consultation.patient_name}")
    print(f"📋 Patient ID: {consultation.patient_id}")
    print(f"📋 Date: {consultation.date_of_visit}")
    print(f"📋 Notes Length: {len(consultation.consultation_notes)} characters")
    
    # ========================================================================
    # STEP 2: UPDATE STATE - MARK CLINICAL AGENT AS ACTIVE
    # ========================================================================
    
    state["current_agent"] = "ClinicalDocumentationAgent"
    state["status"] = "processing"
    state["messages"].append(
        f"Orchestrator: Routing to Clinical Agent at {datetime.now().isoformat()}"
    )
    
    # ========================================================================
    # STEP 3: INSTANTIATE CLINICAL AGENT
    # ========================================================================
    
    try:
        clinical_agent = ClinicalDocumentationAgent(llm)
        print(f"✅ Clinical Agent instantiated")
        
    except Exception as e:
        error_msg = f"Failed to instantiate Clinical Agent: {str(e)}"
        print(f"❌ {error_msg}")
        return {
            **state,
            "status": "error",
            "current_agent": "OrchestratorAgent",
            "errors": [error_msg],
            "messages": [f"Orchestrator: {error_msg}"]
        }
    
    # ========================================================================
    # STEP 4: INVOKE CLINICAL AGENT
    # ========================================================================
    
    print(f"⚙️  Invoking Clinical Agent to process notes...")
    
    try:
        # Call the Clinical Agent's process method
        # This is THE KEY INTERACTION - Orchestrator delegates to agent
        updated_state = clinical_agent.process(state)
        
        print(f"✅ Clinical Agent processing complete")
        
    except Exception as e:
        error_msg = f"Clinical Agent failed: {str(e)}"
        print(f"❌ {error_msg}")
        return {
            **state,
            "status": "error",
            "current_agent": "OrchestratorAgent",
            "errors": [error_msg],
            "messages": [f"Orchestrator: {error_msg}"]
        }
    
    # ========================================================================
    # STEP 5: VALIDATE CLINICAL AGENT OUTPUT
    # ========================================================================
    
    if not updated_state.get("clinical_summary"):
        error_msg = "Clinical Agent did not produce a clinical summary"
        print(f"❌ {error_msg}")
        return {
            **updated_state,
            "status": "error",
            "current_agent": "OrchestratorAgent",
            "errors": updated_state.get("errors", []) + [error_msg],
            "messages": updated_state.get("messages", []) + [f"Orchestrator: {error_msg}"]
        }
    
    clinical_summary = updated_state["clinical_summary"]
    
    # Log what was received
    print(f"\n📊 Clinical Summary Received:")
    print(f"   Chief Complaint: {clinical_summary.chief_complaint}")
    print(f"   Diagnoses: {len(clinical_summary.assessments)}")
    print(f"   ICD Codes: {', '.join(clinical_summary.icd_codes)}")
    
    # ========================================================================
    # STEP 6: UPDATE STATE FOR NEXT AGENT
    # ========================================================================
    
    updated_state["current_agent"] = "CareCoordinatorAgent"
    updated_state["messages"].append(
        f"Orchestrator: Clinical Agent completed successfully, routing to Care Coordinator"
    )
    
    print(f"\n✅ Routing to Care Coordinator Agent next")
    print(f"{'='*60}\n")
    
    return updated_state