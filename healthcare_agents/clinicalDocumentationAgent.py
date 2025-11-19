# ============================================================================
# CLINICAL DOCUMENTATION AGENT
# ============================================================================

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from workflow_models.models import AgentState, WorkflowStatus, ClinicalSummary

class ClinicalDocumentationAgent:
    """
    Agent responsible for generating structured clinical summaries,
    extracting diagnoses, suggesting ICD codes, and maintaining medical records.
    """
    
    def __init__(self, llm: ChatOpenAI):
        self.llm = llm
        self.name = "ClinicalDocumentationAgent"
        
    def process(self, state: AgentState) -> AgentState:
        """Process consultation notes into structured clinical summary"""
        
        print(f"\n{'='*60}")
        print(f"🏥 {self.name} - Processing Clinical Documentation")
        print(f"{'='*60}")
        
        consultation = state["consultation"]
        
        # Create prompt for structured extraction
        system_prompt = """You are an expert medical documentation specialist.
Your task is to analyze consultation notes and create a structured clinical summary.

Extract and organize the following information:
1. Chief Complaint: Primary reason for visit
2. History of Present Illness: Detailed narrative of current condition
3. Vital Signs: If mentioned (BP, HR, Temp, etc.)
4. Physical Exam Findings: Structured list of examination results
5. Assessments/Diagnoses: Clinical impressions with severity
6. ICD-10 Codes: Suggest appropriate billing codes
7. Additional Notes: Any other relevant clinical information

Format your response as valid JSON matching this structure:
{
  "chief_complaint": "string",
  "history_of_present_illness": "string",
  "vital_signs": "string or null",
  "physical_exam_findings": [
    {"body_part": "string", "finding": "string"}
  ],
  "assessments": [
    {"diagnosis": "string", "icd_code": "string", "severity": "mild|moderate|severe"}
  ],
  "icd_codes": ["string"],
  "additional_notes": "string or null"
}

Be thorough, accurate, and maintain medical terminology standards."""

        user_prompt = f"""Patient: {consultation.patient_name}
Date: {consultation.date_of_visit}

Consultation Notes:
{consultation.consultation_notes}

Generate a structured clinical summary from these notes."""

        try:
            # Call LLM to extract structured data
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]
            
            response = self.llm.invoke(messages)
            
            # Parse JSON response
            import json
            clinical_data = json.loads(response.content)
            
            # Create structured summary
            summary = ClinicalSummary(
                patient_name=consultation.patient_name,
                visit_date=consultation.date_of_visit,
                chief_complaint=clinical_data["chief_complaint"],
                history_of_present_illness=clinical_data["history_of_present_illness"],
                vital_signs=clinical_data.get("vital_signs"),
                physical_exam_findings=clinical_data["physical_exam_findings"],
                assessments=clinical_data["assessments"],
                icd_codes=clinical_data["icd_codes"],
                additional_notes=clinical_data.get("additional_notes")
            )
            
            print(f"✅ Generated clinical summary")
            print(f"   - Chief Complaint: {summary.chief_complaint}")
            print(f"   - Assessments: {len(summary.assessments)}")
            print(f"   - ICD Codes: {', '.join(summary.icd_codes)}")
            
            return {
                **state,
                "clinical_summary": summary,
                "messages": [f"{self.name}: Successfully generated clinical summary"],
                "current_agent": "CareCoordinatorAgent"
            }
            
        except Exception as e:
            error_msg = f"{self.name}: Error processing clinical documentation - {str(e)}"
            print(f"❌ {error_msg}")
            return {
                **state,
                "errors": [error_msg],
                "status": WorkflowStatus.ERROR.value
            }