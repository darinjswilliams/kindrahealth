import pytest
from pydantic import ValidationError
from data_models.consultation import (
    ConsultationRequest,
    ConsultationSummaryResponse,
)
from datetime import date

def test_consultation_request_valid():
    data = {
        "patient_name": "DARIN JESSIE WILLIAMS",
        "visit_date": date(2025, 11, 15),
        "consultation_notes": "Patient reports mild headache for 2 days.",
        "symptoms": ["headache", "fatigue"],
        "patient_id": "12345"
    }

    req = ConsultationRequest(**data)
    assert req.patient_name == "DARIN JESSIE WILLIAMS"
    assert req.visit_date == date(2025, 11, 15)
    assert "headache" in req.consultation_notes

def test_consultation_request_invalid_missing_field():
    data = {
        # missing patient_id
        "symptoms": ["headache"],
        "notes": "Incomplete request"
    }
    with pytest.raises(ValidationError):
        ConsultationRequest(**data)

def test_consultation_summary_response_valid():
    data = {
        "clinical_summary": {
            "patient_name": "DARIN JESSIE WILLIAMS",
            "visit_date": "2025-11-15",
            "chief_complaint": "Headache",
            "history_of_present_illness": "Patient reports headache.",
            "vital_signs": None,
            "physical_exam_findings": [
                {"body_part": "Head", "finding": "Tenderness"}
            ],
            "assessments": [
                {"diagnosis": "Tension headache", "icd_code": "G44.2", "severity": "Mild"}
            ],
            "additional_notes": "Recommend acetaminophen."
        },
        "next_steps": {
            "actions": [
                {"action_type": "Medication", "description": "Take acetaminophen", "timeline": "As needed", "priority": "High"}
            ],
            "follow_up_appointment": "2025-11-20",
            "red_flags": ["Severe headache", "Vision changes"]
        },
        "patient_email": {
            "greeting": "Hello Darin,",
            "summary_of_findings": "We found signs of tension headache.",
            "treatment_plan": "Use acetaminophen as needed.",
            "patient_instructions": [
                {"category": "medication", "instruction": "Take acetaminophen when headache occurs"}
            ],
            "warning_signs": ["Sudden severe headache"],
            "next_steps_timeline": "Follow up in 5 days",
            "closing": "Best regards,",
            "physician_signature": "Dr. Smith"
        },
         "generation_timestamp": "2025-11-15T17:00:00Z"
    }
    resp = ConsultationSummaryResponse(**data)
    assert resp.clinical_summary.patient_name == "DARIN JESSIE WILLIAMS"
    assert resp.next_steps.actions[0].action_type == "Medication"
    assert resp.patient_email.greeting.startswith("Hello")

def test_consultation_summary_response_invalid():
    data = {
        "clinical_summary": {
            "patient_name": "DARIN",
            "visit_date": "invalid-date",  # invalid format
            "chief_complaint": "Headache",
            "history_of_present_illness": "Patient reports headache.",
            "vital_signs": None,
            "physical_exam_findings": [],
            "assessments": [],
            "additional_notes": None
        },
        "next_steps": {
            "actions": [],
            "follow_up_appointment": None,
            "red_flags": []
        },
        "patient_email": {
            "greeting": "Hi",
            "summary_of_findings": "Summary",
            "treatment_plan": "Plan",
            "patient_instructions": [],
            "warning_signs": [],
            "next_steps_timeline": "Soon",
            "closing": "Bye",
            "physician_signature": "Dr. X"
        }
       
    }
    with pytest.raises(ValidationError):
        ConsultationSummaryResponse(**data)
