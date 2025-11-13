from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional
from datetime import date

# ===== INPUT MODELS =====

class ConsultationRequest(BaseModel):
    """Request model for generating consultation summary"""
    patient_name: str = Field(..., min_length=1, description="Patient's full name")
    visit_date: date = Field(..., description="Date of the consultation visit")
    consultation_notes: str = Field(..., min_length=10, description="Raw consultation notes from physician")
    physician_name: Optional[str] = Field(None, description="Name of the attending physician")
    patient_email: Optional[EmailStr] = Field(None, description="Patient's email address for follow-up")

    class Config:
        json_schema_extra = {
            "example": {
                "patient_name": "John Doe",
                "visit_date": "2025-11-09",
                "consultation_notes": "Patient presents with lower back pain radiating to both feet. Pain began 2 weeks ago.",
                "physician_name": "Dr. Smith",
                "patient_email": "john.doe@example.com"
            }
        }


# ===== OUTPUT MODELS =====

class PhysicalExamFinding(BaseModel):
    """Individual physical examination finding"""
    body_part: str = Field(..., description="Body part or system examined")
    finding: str = Field(..., description="Observation or finding")

    class Config:
        json_schema_extra = {
            "example": {
                "body_part": "Back",
                "finding": "Tenderness in L4-L5 region, reduced range of motion"
            }
        }


class Assessment(BaseModel):
    """Clinical assessment/diagnosis"""
    diagnosis: str = Field(..., description="Primary diagnosis or assessment")
    icd_code: Optional[str] = Field(None, description="ICD-10 code if applicable")
    severity: Optional[str] = Field(None, description="Severity level (mild, moderate, severe)")

    class Config:
        json_schema_extra = {
            "example": {
                "diagnosis": "Lower back pain, likely musculoskeletal origin",
                "icd_code": "M54.5",
                "severity": "moderate"
            }
        }


class ClinicalSummary(BaseModel):
    """Structured clinical summary for doctor's records"""
    patient_name: str
    visit_date: date
    chief_complaint: str = Field(..., description="Primary reason for visit")
    history_of_present_illness: str = Field(..., description="Detailed history of current condition")
    vital_signs: Optional[str] = Field(None, description="Vital signs if recorded")
    physical_exam_findings: List[PhysicalExamFinding] = Field(default_factory=list, description="Physical examination findings")
    assessments: List[Assessment] = Field(..., min_items=1, description="Clinical assessments/diagnoses")
    additional_notes: Optional[str] = Field(None, description="Any additional clinical notes")

    class Config:
        json_schema_extra = {
            "example": {
                "patient_name": "John Doe",
                "visit_date": "2025-11-09",
                "chief_complaint": "Back pain and bilateral foot pain",
                "history_of_present_illness": "Patient presents with complaints of lower back pain radiating to both feet. Pain began approximately 2 weeks ago, rated 6/10 in severity.",
                "vital_signs": "BP: 120/80, HR: 72, Temp: 98.6°F",
                "physical_exam_findings": [
                    {
                        "body_part": "Back",
                        "finding": "Tenderness in L4-L5 region, reduced range of motion"
                    }
                ],
                "assessments": [
                    {
                        "diagnosis": "Lower back pain, likely musculoskeletal origin",
                        "icd_code": "M54.5",
                        "severity": "moderate"
                    }
                ]
            }
        }


class NextStepAction(BaseModel):
    """Individual action item for next steps"""
    action_type: str = Field(..., description="Type of action (diagnostic, treatment, referral, follow-up, education)")
    description: str = Field(..., description="Detailed description of the action")
    priority: Optional[str] = Field(None, description="Priority level (high, medium, low)")
    timeline: Optional[str] = Field(None, description="When this should be completed")

    class Config:
        json_schema_extra = {
            "example": {
                "action_type": "diagnostic",
                "description": "Order lumbar spine X-ray to rule out structural abnormalities",
                "priority": "high",
                "timeline": "within 48 hours"
            }
        }


class NextSteps(BaseModel):
    """Structured next steps for physician follow-up"""
    actions: List[NextStepAction] = Field(..., min_items=1, description="List of action items")
    follow_up_appointment: Optional[str] = Field(None, description="Follow-up appointment details")
    red_flags: Optional[List[str]] = Field(default_factory=list, description="Warning signs to watch for")

    class Config:
        json_schema_extra = {
            "example": {
                "actions": [
                    {
                        "action_type": "diagnostic",
                        "description": "Order lumbar spine X-ray",
                        "priority": "high",
                        "timeline": "within 48 hours"
                    },
                    {
                        "action_type": "treatment",
                        "description": "Prescribe NSAIDs (Ibuprofen 400mg TID)",
                        "priority": "high",
                        "timeline": "immediate"
                    }
                ],
                "follow_up_appointment": "2 weeks",
                "red_flags": ["Severe or worsening pain", "Numbness or weakness in legs"]
            }
        }


class PatientInstruction(BaseModel):
    """Individual instruction for patient"""
    category: str = Field(..., description="Category (medication, activity, self-care, warning)")
    instruction: str = Field(..., description="Patient-friendly instruction")

    class Config:
        json_schema_extra = {
            "example": {
                "category": "medication",
                "instruction": "Take ibuprofen 400mg three times daily with food"
            }
        }


class PatientFollowUpEmail(BaseModel):
    """Structured patient-friendly follow-up email"""
    greeting: str = Field(..., description="Personalized greeting")
    summary_of_findings: str = Field(..., description="Patient-friendly explanation of findings")
    treatment_plan: str = Field(..., description="What treatments/actions are being taken")
    patient_instructions: List[PatientInstruction] = Field(default_factory=list, description="What patient should do")
    warning_signs: List[str] = Field(default_factory=list, description="When to call doctor immediately")
    next_steps_timeline: str = Field(..., description="What happens next and when")
    closing: str = Field(..., description="Closing statement")
    physician_signature: str = Field(..., description="Physician name and credentials")

    class Config:
        json_schema_extra = {
            "example": {
                "greeting": "Dear John,",
                "summary_of_findings": "Your back pain appears to be related to muscle and joint strain in your lower back area.",
                "treatment_plan": "We'll take some X-rays and prescribe pain medication to help with discomfort.",
                "patient_instructions": [
                    {
                        "category": "medication",
                        "instruction": "Take ibuprofen as directed with food"
                    }
                ],
                "warning_signs": ["Severe pain", "Numbness in legs"],
                "next_steps_timeline": "We'll contact you within 48 hours with X-ray appointment details.",
                "closing": "Take care and don't hesitate to call if you have concerns.",
                "physician_signature": "Dr. Sarah Smith, MD"
            }
        }


# ===== COMPLETE RESPONSE MODEL =====

class ConsultationSummaryResponse(BaseModel):
    """Complete response containing all generated summaries"""
    clinical_summary: ClinicalSummary
    next_steps: NextSteps
    patient_email: PatientFollowUpEmail
    generation_timestamp: str = Field(..., description="ISO timestamp of when this was generated")
    model_version: Optional[str] = Field(None, description="LLM model version used")

    class Config:
        json_schema_extra = {
            "example": {
                "clinical_summary": {
                    "patient_name": "John Doe",
                    "visit_date": "2025-11-09",
                    "chief_complaint": "Back pain and bilateral foot pain",
                    "history_of_present_illness": "Patient presents with lower back pain...",
                    "physical_exam_findings": [],
                    "assessments": []
                },
                "next_steps": {
                    "actions": [],
                    "follow_up_appointment": "2 weeks"
                },
                "patient_email": {
                    "greeting": "Dear John,",
                    "summary_of_findings": "...",
                    "treatment_plan": "...",
                    "patient_instructions": [],
                    "warning_signs": [],
                    "next_steps_timeline": "...",
                    "closing": "...",
                    "physician_signature": "Dr. Smith"
                },
                "generation_timestamp": "2025-11-09T10:30:00Z",
                "model_version": "gpt-4"
            }
        }


# ===== HELPER FUNCTIONS FOR FORMATTING =====

def format_clinical_summary_for_display(summary: ClinicalSummary) -> str:
    """Format clinical summary as readable text for display"""
    output = f"""Patient: {summary.patient_name}
Date: {summary.visit_date}

Chief Complaint: {summary.chief_complaint}

History of Present Illness:
{summary.history_of_present_illness}
"""
    
    if summary.vital_signs:
        output += f"\nVital Signs:\n{summary.vital_signs}\n"
    
    if summary.physical_exam_findings:
        output += "\nPhysical Examination:\n"
        for finding in summary.physical_exam_findings:
            output += f"- {finding.body_part}: {finding.finding}\n"
    
    output += "\nAssessment:\n"
    for i, assessment in enumerate(summary.assessments, 1):
        output += f"{i}. {assessment.diagnosis}"
        if assessment.icd_code:
            output += f" (ICD-10: {assessment.icd_code})"
        if assessment.severity:
            output += f" - Severity: {assessment.severity}"
        output += "\n"
    
    if summary.additional_notes:
        output += f"\nAdditional Notes:\n{summary.additional_notes}\n"
    
    return output


def format_next_steps_for_display(next_steps: NextSteps) -> str:
    """Format next steps as readable text for display"""
    output = ""
    
    for i, action in enumerate(next_steps.actions, 1):
        output += f"{i}. [{action.action_type.upper()}] {action.description}"
        if action.timeline:
            output += f" (Timeline: {action.timeline})"
        if action.priority:
            output += f" [Priority: {action.priority}]"
        output += "\n"
    
    if next_steps.follow_up_appointment:
        output += f"\nFollow-up Appointment: {next_steps.follow_up_appointment}\n"
    
    if next_steps.red_flags:
        output += "\n⚠️ Red Flags - Call immediately if:\n"
        for flag in next_steps.red_flags:
            output += f"- {flag}\n"
    
    return output


def format_patient_email_for_display(email: PatientFollowUpEmail) -> str:
    """Format patient email as readable text for display"""
    output = f"""{email.greeting}

{email.summary_of_findings}

What we're doing next:
{email.treatment_plan}

What you should do:
"""
    
    for instruction in email.patient_instructions:
        output += f"• [{instruction.category.title()}] {instruction.instruction}\n"
    
    if email.warning_signs:
        output += "\n⚠️ Call us immediately if you experience:\n"
        for warning in email.warning_signs:
            output += f"• {warning}\n"
    
    output += f"\nNext Steps:\n{email.next_steps_timeline}\n"
    output += f"\n{email.closing}\n\n{email.physician_signature}"
    
    return output