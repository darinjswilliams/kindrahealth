# ============================================================================
# PATIENT COMMUNICATION AGENT
# ============================================================================
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from workflow_models.models import AgentState, WorkflowStatus, PatientEmail

class PatientCommunicationAgent:
    """
    Agent responsible for generating patient-friendly communications,
    educational content, and managing all patient-facing interactions.
    """
    
    def __init__(self, llm: ChatOpenAI):
        self.llm = llm
        self.name = "PatientCommunicationAgent"
        
    def process(self, state: AgentState) -> AgentState:
        """Generate patient-friendly email communication"""
        
        print(f"\n{'='*60}")
        print(f"📧 {self.name} - Drafting Patient Communication")
        print(f"{'='*60}")
        
        consultation = state["consultation"]
        clinical_summary = state.get("clinical_summary")
        next_steps = state.get("next_steps", [])
        
        if not clinical_summary:
            return {
                **state,
                "errors": [f"{self.name}: No clinical summary available"],
                "status": WorkflowStatus.ERROR.value
            }
        
        system_prompt = """You are an expert at translating medical information into patient-friendly language.

Create a warm, empathetic email that:
1. Summarizes the visit in simple terms
2. Explains the diagnosis clearly (avoid jargon)
3. Outlines the treatment plan step-by-step
4. Provides clear instructions
5. Lists warning signs to watch for
6. Explains next steps and timeline

Tone: Professional yet warm, empathetic, clear, and reassuring.
Reading Level: 8th grade or below
Avoid: Medical jargon, complex terminology

Format as JSON:
{
  "subject": "Summary of Your Visit on [date]",
  "greeting": "Dear [name],",
  "summary": "Brief visit summary in plain language",
  "treatment_plan": "What we're doing to help you",
  "instructions": ["Step 1", "Step 2"],
  "warning_signs": ["When to call us immediately"],
  "next_steps": "What happens next",
  "closing": "Closing message"
}"""

        # Simplify next steps for patient
        next_steps_text = "\n".join([
            f"- {action.description} ({action.timeline})"
            for action in next_steps
        ])
        
        user_prompt = f"""Patient: {consultation.patient_name}
Visit Date: {consultation.date_of_visit}

Chief Complaint: {clinical_summary.chief_complaint}
Diagnosis: {', '.join([a['diagnosis'] for a in clinical_summary.assessments])}

Next Steps:
{next_steps_text}

Create a patient-friendly email summarizing this visit."""

        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]
            
            response = self.llm.invoke(messages)
            
            # Parse JSON response
            import json
            email_data = json.loads(response.content)
            
            # Create email object
            patient_email = PatientEmail(
                subject=email_data["subject"],
                greeting=email_data["greeting"],
                summary=email_data["summary"],
                treatment_plan=email_data["treatment_plan"],
                instructions=email_data["instructions"],
                warning_signs=email_data["warning_signs"],
                next_steps=email_data["next_steps"],
                closing=email_data["closing"]
            )
            
            print(f"✅ Generated patient email")
            print(f"   - Subject: {patient_email.subject}")
            print(f"   - Instructions: {len(patient_email.instructions)} items")
            print(f"   - Warning signs: {len(patient_email.warning_signs)} listed")
            
            return {
                **state,
                "patient_email": patient_email,
                "messages": [f"{self.name}: Generated patient communication"],
                "current_agent": "OrchestratorAgent",
                "status": WorkflowStatus.AWAITING_APPROVAL.value if state.get("physician_approval_required") else WorkflowStatus.COMPLETED.value
            }
            
        except Exception as e:
            error_msg = f"{self.name}: Error generating patient communication - {str(e)}"
            print(f"❌ {error_msg}")
            return {
                **state,
                "errors": [error_msg],
                "status": WorkflowStatus.ERROR.value
            }