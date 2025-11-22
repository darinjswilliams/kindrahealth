from workflow_models.models import AgentState
from healthcare_agents import PatientCommunicationAgent

async def route_to_patient_comm(self, state: AgentState) -> AgentState:
        """
        Route to Patient Communication Agent - called after Care Coordinator
        """
  
        print(f"\n{'='*60}")
        print(f"🔵 ORCHESTRATOR: Routing to Patient Communication Agent")
        print(f"{'='*60}")
        
        state["current_agent"] = "PatientCommunicationAgent"
        
        try:
            comm_agent = PatientCommunicationAgent(self.llm)
            updated_state = comm_agent.process(state)
            
            updated_state["current_agent"] = "OrchestratorAgent"
            updated_state["status"] = "completed"
            print(f"✅ Patient Communication complete, workflow finished")
            
            return updated_state
            
        except Exception as e:
            return {
                **state,
                "status": "error",
                "errors": [f"Patient Communication failed: {str(e)}"]
            }