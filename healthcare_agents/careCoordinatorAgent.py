# ============================================================================
# CARE COORDINATOR AGENT
# ============================================================================

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from workflow_models.models import AgentState, WorkflowStatus, NextStepAction


class CareCoordinatorAgent:
    """
    Agent responsible for managing next steps, follow-ups, lab orders,
    referrals, and ongoing patient care coordination.
    """
    
    def __init__(self, llm: ChatOpenAI):
        self.llm = llm
        self.name = "CareCoordinatorAgent"
        
    def process(self, state: AgentState) -> AgentState:
        """Generate action items and coordinate care"""
        
        print(f"\n{'='*60}")
        print(f"📋 {self.name} - Coordinating Care & Next Steps")
        print(f"{'='*60}")
        
        consultation = state["consultation"]
        clinical_summary = state.get("clinical_summary")
        
        if not clinical_summary:
            return {
                **state,
                "errors": [f"{self.name}: No clinical summary available"],
                "status": WorkflowStatus.ERROR.value
            }
        
        system_prompt = """You are an expert healthcare care coordinator.
Analyze the clinical summary and consultation notes to determine necessary next steps.

Consider:
1. Lab Work: What tests are needed based on diagnoses?
2. Imaging: Are X-rays, MRIs, CT scans required?
3. Referrals: Should patient see a specialist?
4. Medications: What prescriptions are needed?
5. Follow-up: When should patient return?
6. Patient Education: What should patient know?

For each action, determine:
- Action type (lab, imaging, referral, medication, follow-up, education)
- Detailed description
- Priority (high, medium, low)
- Timeline (immediate, 24-48 hours, 1 week, 2 weeks, etc.)
- Whether it requires scheduling

Format as JSON array:
[
  {
    "action_type": "lab",
    "description": "Complete Blood Count (CBC) to check for anemia",
    "priority": "high",
    "timeline": "within 48 hours",
    "requires_scheduling": true
  }
]

Be thorough and prioritize patient safety."""

        user_prompt = f"""Clinical Summary:
Chief Complaint: {clinical_summary.chief_complaint}
Assessments: {', '.join([a['diagnosis'] for a in clinical_summary.assessments])}
ICD Codes: {', '.join(clinical_summary.icd_codes)}

Full Notes:
{consultation.consultation_notes}

Generate comprehensive next steps and action items."""

        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]
            
            response = self.llm.invoke(messages)
            
            # Parse JSON response
            import json
            actions_data = json.loads(response.content)
            
            # Create action objects
            next_steps = [
                NextStepAction(
                    action_type=action["action_type"],
                    description=action["description"],
                    priority=action["priority"],
                    timeline=action["timeline"],
                    requires_scheduling=action.get("requires_scheduling", False)
                )
                for action in actions_data
            ]
            
            print(f"✅ Generated {len(next_steps)} action items:")
            for action in next_steps:
                print(f"   - [{action.priority.upper()}] {action.action_type}: {action.description}")
            
            # Check if any high-priority items need physician approval
            has_high_priority = any(a.priority == "high" for a in next_steps)
            
            return {
                **state,
                "next_steps": next_steps,
                "physician_approval_required": has_high_priority,
                "messages": [f"{self.name}: Generated {len(next_steps)} action items"],
                "current_agent": "PatientCommunicationAgent"
            }
            
        except Exception as e:
            error_msg = f"{self.name}: Error generating next steps - {str(e)}"
            print(f"❌ {error_msg}")
            return {
                **state,
                "errors": [error_msg],
                "status": WorkflowStatus.ERROR.value
            }