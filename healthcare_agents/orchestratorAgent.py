# ============================================================================
# ORCHESTRATOR AGENT
# ============================================================================
from healthcare_agents import (
    ClinicalDocumentationAgent as clinicalDocumentationAgent,
    PatientCommunicationAgent as patientCommunicationAgent,
    CareCoordinatorAgent as careCoordinatorAgent
)

from healthcare_agents.orchestrator import route_to_care_coordinator
from workflow_models.models import AgentState, WorkflowStatus
from typing import Dict, List
from data_models import ApprovalRequest, AgentHealthCheck
from workflow_models.models import ConsultationInput

from executor_engine import PhysicianApprovalHandler

from execution_models import (
    WorkflowExecution,
    ExecutionStatus,
    ActionExecution
)

from orchestrator.request_approval import request_approval
from orchestrator.check_agent_status import check_status
from orchestrator.route_to_clinical import route_to_clinical
from orchestrator.route_to_care_coordinator import route_to_care_coordinator
from orchestrator.route_to_patient_com import route_to_patient_comm



class OrchestratorAgent:
    """
    Master coordinator that manages workflow, routes between agents,
    handles physician approvals, and ensures proper sequencing.
    """
    
    def __init__(self):
        self.name = "OrchestratorAgent"
        
    async def initiate_workflow(self, state: AgentState) -> AgentState:
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
    
    async def check_completion(self, state: AgentState) -> str:
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


    async def route_to_clinical(self, state: AgentState) -> None:
        ''' 
        Purpose: Delegate clinical documentation task
        Triggers: New workflow initiated
        Output: Task queued for Clinical Agent
        Interactions:

        Clinical Agent → Receives consultation notes
        Clinical Agent → Returns structured summary
        '''
    
        return await route_to_clinical(state, self.llm)

    async def route_to_care_coordinator(state: AgentState) -> None:
        '''
        Purpose: Delegate action planning task
        Triggers: Clinical summary completed
        Output: Task queued for Care Coordinator
        Interactions:

        Care Coordinator Agent → Receives clinical summary
        Care Coordinator Agent → Returns action items
        Sets physician_approval_required flag if high-priority actions detected
        '''
        return await route_to_care_coordinator(state)


    async def route_to_patient_comm(state: AgentState) -> None:
        '''
        Purpose: Delegate patient communication task
        Triggers: Care coordination completed
        Output: Task queued for Patient Communication Agent
        Interactions:

        Patient Comm Agent → Receives clinical summary + action items
        Patient Comm Agent → Returns patient-friendly email draft
        '''
        return await route_to_patient_comm(state)
        

    async def request_approval(
        workflow: WorkflowExecution,
        approval_handler: PhysicianApprovalHandler,
        agent_state: Dict) -> ApprovalRequest:
        '''
        Purpose: Pause workflow and notify physician for approval
        Triggers: High-priority actions detected OR physician_approval_required = True
        Output: Approval request in physician dashboard
        Interactions:

        Physician Dashboard → Displays pending approval
        Workflow Status → Set to "AWAITING_APPROVAL"
        Approval Handler → Registers workflow in pending queue
        '''
        return await request_approval(workflow, approval_handler, agent_state)
        

    async def resume_workflow(workflow_id: str, approved: bool, modifications: Dict) -> None:
        '''
        Purpose: Continue workflow execution after physician decision
        Triggers: Physician approves/rejects workflow
        Output: Workflow continues or terminates
        Interactions:

        If approved: Route to Action Executor Agent
        If approved: Apply any physician modifications
        If approved: Start Monitoring Agent
        If rejected: Mark workflow as FAILED
        '''
        pass

    async def route_to_executor(workflow_id: str, actions: List[Action]) -> None:
        '''
        Purpose: Delegate action execution to executor
        Triggers: Workflow approved or auto-approved
        Output: Actions queued for execution
        Interactions:

        Action Executor Agent → Executes each action
        Action Executor Agent → Returns execution results
        Updates workflow with execution status
        '''
        pass

    async def handle_failure(agent: str, workflow_id: str, error: Exception) -> None:
        '''
        Purpose: Recover from agent failures
        Triggers: Any agent raises exception
        Output: Error logged, workflow marked for retry or manual review
        Interactions:

        Logs error to audit system
        Attempts retry with exponential backoff (up to 3 times)
        If retry fails: Alert physician and mark workflow as FAILED
        If critical failure: Trigger incident alert
        '''
        pass

    async def update_state(state: AgentState, updates: Dict) -> None:
        '''
        Purpose: Maintain workflow state consistency
        Triggers: After every agent action
        Output: Updated state in state store
        Interactions:

        State Store → Persists updates
        Dashboard → Receives state change notification
        Audit Log → Records state transition
        '''
        pass

    async def complete_workflow(workflow_id: str) -> None:
        '''
        Purpose: Finalize completed workflow
        Triggers: All actions executed and monitoring started
        Output: Workflow marked as COMPLETED
        Interactions:

        Sets completed_at timestamp
        Sends completion notification to physician
        Archives workflow state
        Triggers billing agent (if implemented)
        '''
        pass

    async def generate_report(workflow_id: str) -> WorkflowReport:
        '''
        Purpose: Create comprehensive workflow status report
        Triggers: Physician requests workflow details
        Output: Detailed report with all agent actions and results
        Interactions:

        Queries all agent outputs
        Aggregates execution metrics
        Returns formatted report to dashboard
        '''
        pass

####################################################################################
#   Sensors                                                                        #
####################################################################################

    def read_consultation(consultation_id: str) -> ConsultationInput:
        '''
        Purpose: Receive physician consultation data
        Source: API endpoint /api/v1/consultations
        Data: Patient info, notes, physician ID
        '''
        pass

    def check_agent_status(agent_state: Dict, agent_name: str) -> AgentHealthCheck:
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
        return  check_status(agent_state, agent_name)
       

    def get_workflow_state(workflow_id: str) -> WorkflowState:
        '''
        Purpose: Retrieve current workflow state
        Source: State store (Redis/Database)
        Data: Complete workflow state object
        '''
        pass

    def check_approval(workflow_id: str) -> Optional[ApprovalDecision]:
        '''
        Purpose: Determine if workflow has been approved/rejected
        Source: Approval handler
        Data: Approved/rejected flag, physician ID, modifications
        '''
        pass

    def get_queue_depth() -> Dict[str, int]:
        '''
        Purpose: Check workload across agents
        Source: Internal queue metrics
        Data: Number of pending tasks per agent
        '''
        pass

    def get_physician_preferences(physician_id: str) -> PhysicianPreferences
        '''
        Purpose: Get physician-specific workflow settings
        Source: User preferences database
        Data: Auto-approve settings, notification preferences
        '''
        pass