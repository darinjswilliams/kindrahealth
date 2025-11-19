# ============================================================================
# ORCHESTRATOR AGENT
# ============================================================================
from workflow_models.models import AgentState, WorkflowStatus


class OrchestratorAgent:
    """
    Master coordinator that manages workflow, routes between agents,
    handles physician approvals, and ensures proper sequencing.
    """
    
    def __init__(self):
        self.name = "OrchestratorAgent"
        
    def initiate_workflow(self, state: AgentState) -> AgentState:
        """Initialize the workflow"""
        print(f"\n{'='*60}")
        print(f"🎯 {self.name} - Initiating Workflow")
        print(f"{'='*60}")
        print(f"Patient: {state['consultation'].patient_name}")
        print(f"Date: {state['consultation'].date_of_visit}")
        print(f"{'='*60}\n")
        
        return {
            **state,
            "status": WorkflowStatus.PROCESSING.value,
            "current_agent": "ClinicalDocumentationAgent",
            "messages": [f"{self.name}: Workflow initiated"]
        }
    
    def check_completion(self, state: AgentState) -> str:
        """Determine next step in workflow"""
        
        status = state.get("status")
        
        # Check for errors
        if status == WorkflowStatus.ERROR.value:
            print(f"\n❌ Workflow failed with errors:")
            for error in state.get("errors", []):
                print(f"   - {error}")
            return "error"
        
        # Check if awaiting physician approval
        if status == WorkflowStatus.AWAITING_APPROVAL.value:
            print(f"\n⏸️  Workflow paused - awaiting physician approval")
            return "awaiting_approval"
        
        # Check if completed
        if status == WorkflowStatus.COMPLETED.value:
            print(f"\n✅ Workflow completed successfully")
            self.print_summary(state)
            return "completed"
        
        # Continue processing
        return "continue"
    
    def print_summary(self, state: AgentState):
        """Print final workflow summary"""
        print(f"\n{'='*60}")
        print(f"📊 WORKFLOW SUMMARY")
        print(f"{'='*60}")
        
        clinical = state.get("clinical_summary")
        if clinical:
            print(f"\n🏥 Clinical Summary:")
            print(f"   Chief Complaint: {clinical.chief_complaint}")
            print(f"   Diagnoses: {len(clinical.assessments)}")
            print(f"   ICD Codes: {', '.join(clinical.icd_codes)}")
        
        next_steps = state.get("next_steps", [])
        if next_steps:
            print(f"\n📋 Next Steps ({len(next_steps)} actions):")
            for action in next_steps:
                print(f"   - [{action.priority}] {action.action_type}: {action.description}")
        
        email = state.get("patient_email")
        if email:
            print(f"\n📧 Patient Email:")
            print(f"   Subject: {email.subject}")
            print(f"   Instructions: {len(email.instructions)}")
        
        print(f"\n{'='*60}\n")