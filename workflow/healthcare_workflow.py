# ============================================================================
# WORKFLOW GRAPH DEFINITION
# ============================================================================
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from datetime import datetime

from healthcare_agents import (OrchestratorAgent,
                      ClinicalDocumentationAgent,
                      CareCoordinatorAgent,
                      PatientCommunicationAgent)

from workflow_models.models import AgentState, WorkflowStatus, ConsultationInput

def create_healthcare_workflow(llm: ChatOpenAI) -> StateGraph:
    """Create the LangGraph workflow with all agents"""
    
    # Initialize agents
    orchestrator = OrchestratorAgent()
    clinical_agent = ClinicalDocumentationAgent(llm)
    care_coordinator_agent = CareCoordinatorAgent(llm)
    patient_comm_agent = PatientCommunicationAgent(llm)
    
    # Create the graph
    workflow = StateGraph(AgentState)
    
    # Add nodes (agents)
    workflow.add_node("orchestrator_init", orchestrator.initiate_workflow)
    workflow.add_node("clinical_agent", clinical_agent.process)
    workflow.add_node("care_coordinator_agent", care_coordinator_agent.process)
    workflow.add_node("patient_comm_agent", patient_comm_agent.process)
    workflow.add_node("orchestrator_check", lambda state: state)  # Checkpoint
    
    # Define edges (workflow flow)
    workflow.set_entry_point("orchestrator_init")
    
    workflow.add_edge("orchestrator_init", "clinical_agent")
    workflow.add_edge("clinical_agent", "care_coordinator_agent")
    workflow.add_edge("care_coordinator_agent", "patient_comm_agent")
    workflow.add_edge("patient_comm_agent", "orchestrator_check")
    
    # Conditional edge from orchestrator_check
    def route_from_orchestrator(state: AgentState) -> str:
        status = state.get("status")
        if status == WorkflowStatus.ERROR.value:
            return "error"
        elif status == WorkflowStatus.AWAITING_APPROVAL.value:
            return "awaiting_approval"
        elif status == WorkflowStatus.COMPLETED.value:
            return "end"
        return "end"
    
    workflow.add_conditional_edges(
        "orchestrator_check",
        route_from_orchestrator,
        {
            "error": END,
            "awaiting_approval": END,
            "end": END
        }
    )
    
    return workflow.compile()


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def run_consultation_workflow(consultation_notes: str, patient_name: str, patient_id: str):
    """
    Main function to execute the healthcare consultation workflow
    """
    
    # Initialize LLM
    llm = ChatOpenAI(
        model="gpt-4o",
        temperature=0.2  # Lower temperature for more consistent medical outputs
    )
    
    # Create consultation input
    consultation = ConsultationInput(
        patient_name=patient_name,
        patient_id=patient_id,
        date_of_visit=datetime.now().strftime("%Y-%m-%d"),
        consultation_notes=consultation_notes,
        physician_id="DR001"
    )
    
    # Initialize state
    initial_state: AgentState = {
        "consultation": consultation,
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
    
    # Create and run workflow
    workflow = create_healthcare_workflow(llm)
    
    print("\n" + "="*60)
    print("🚀 STARTING HEALTHCARE CONSULTATION WORKFLOW")
    print("="*60)
    
    # Execute workflow
    final_state = workflow.invoke(initial_state)
    
    return final_state


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    # Example consultation notes
    sample_notes = """
Patient presents with complaints of persistent lower back pain radiating to both legs.
Pain started approximately 2 weeks ago after lifting heavy boxes at work.
Pain is rated 7/10, worse in the morning and after prolonged sitting.

Vital Signs: BP 128/82, HR 76, Temp 98.4°F, RR 16

Physical Examination:
- Back: Tenderness in L4-L5 region, reduced range of motion
- Neurological: Intact sensation bilaterally, 5/5 strength in lower extremities
- Straight leg raise test: Positive on right at 45 degrees

Assessment:
1. Acute lumbar radiculopathy, likely L4-L5 disc herniation
2. Muscle strain, lower back

Plan:
- Order lumbar spine MRI to evaluate disc herniation
- Start NSAIDs (Ibuprofen 600mg TID with food)
- Physical therapy referral
- Avoid heavy lifting
- Follow-up in 2 weeks or sooner if symptoms worsen
- Red flags: Loss of bowel/bladder control, progressive weakness
"""
    
    # Run workflow
    result = run_consultation_workflow(
        consultation_notes=sample_notes,
        patient_name="John Doe",
        patient_id="PT12345"
    )
    
    # Access results
    print("\n" + "="*60)
    print("📋 FINAL RESULTS")
    print("="*60)
    
    if result.get("clinical_summary"):
        print(f"\n✅ Clinical Summary Generated")
        print(f"   ICD Codes: {', '.join(result['clinical_summary'].icd_codes)}")
    
    if result.get("next_steps"):
        print(f"\n✅ Next Steps Generated: {len(result['next_steps'])} actions")
    
    if result.get("patient_email"):
        print(f"\n✅ Patient Email Generated")
        print(f"   Subject: {result['patient_email'].subject}")
    
    print("\n" + "="*60)