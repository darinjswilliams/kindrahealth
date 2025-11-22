from healthcare_agents import CareCoordinatorAgent
from workflow_models.models import AgentState

async def route_to_care_coordinator(self, state: AgentState) -> AgentState:
        """
        Route to Care Coordinator Agent - called after Clinical Agent
        """
        
        print(f"\n{'='*60}")
        print(f"🔵 ORCHESTRATOR: Routing to Care Coordinator Agent")
        print(f"{'='*60}")
        
        state["current_agent"] = "CareCoordinatorAgent"
        
        try:
            care_agent = CareCoordinatorAgent(self.llm)
            updated_state = care_agent.process(state)
            
            updated_state["current_agent"] = "PatientCommunicationAgent"
            print(f"✅ Care Coordinator complete, routing to Patient Communication")
            
            return updated_state
            
        except Exception as e:
            return {
                **state,
                "status": "error",
                "errors": [f"Care Coordinator failed: {str(e)}"]
            }