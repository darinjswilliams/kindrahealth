import {
  ConsultationSummaryResponseSchema,
  AssessmentSchema,
} from "../schemas/consultationSummaryResponseSchema";

describe("Zod Schema Validation", () => {
  it("valid ConsultationSummaryResponse passes", () => {
    const data = {
      clinical_summary: {
        patient_name: "DARIN JESSIE WILLIAMS",
        visit_date: "2025-11-15",
        chief_complaint: "Headache",
        history_of_present_illness: "Patient reports headache.",
        vital_signs: null,
        physical_exam_findings: [
          { body_part: "Head", finding: "Tenderness" }
        ],
        assessments: [
          { diagnosis: "Tension headache", icd_code: "G44.2", severity: "mild" }
        ],
        additional_notes: "Recommend acetaminophen."
      },
      next_steps: {
        actions: [
          { action_type: "treatment", description: "Take acetaminophen", priority: "high", timeline: "As needed" }
        ],
        follow_up_appointment: "2025-11-20",
        red_flags: ["Severe headache", "Vision changes"]
      },
      patient_email: {
        greeting: "Hello Darin,",
        summary_of_findings: "Signs of tension headache",
        treatment_plan: "Use acetaminophen as needed",
        patient_instructions: [
          { instruction: "Take acetaminophen when headache occurs", category: "medication" }
        ],
        warning_signs: ["Sudden severe headache"],
        next_steps_timeline: "Follow up in 5 days",
        closing: "Best regards,",
        physician_signature: "Dr. Smith"
      },
      generation_timestamp: "2025-11-15T12:00:00Z"
    };

    const result = ConsultationSummaryResponseSchema.safeParse(data);
    expect(result.success).toBe(true);
  });

  it("invalid ConsultationSummaryResponse fails when missing required fields", () => {
    const badData = {
      clinical_summary: {}, // missing required fields
      next_steps: {},
      patient_email: {},
      generation_timestamp: "2025-11-15T12:00:00Z"
    };

    const result = ConsultationSummaryResponseSchema.safeParse(badData);
    expect(result.success).toBe(false);
  });

  it("rejects invalid enum values", () => {
    const badAssessment = {
      diagnosis: "Migraine",
      severity: "Mild" // ❌ should be lowercase "mild"
    };
    const result = AssessmentSchema.safeParse(badAssessment);
    expect(result.success).toBe(false);
  });
});
