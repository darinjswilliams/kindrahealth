import {
    formatClinicalSummary,
    formatNextSteps,
    formatPatientEmail,
  } from "../utils/formatters";
  
  describe("Formatter functions", () => {
    test("formatClinicalSummary produces expected output", () => {
      const summary = {
        patient_name: "John Doe",
        visit_date: "2025-11-15",
        chief_complaint: "Headache",
        history_of_present_illness: "Patient reports headache.",
        vital_signs: "BP 120/80",
        physical_exam_findings: [{ body_part: "Head", finding: "Tenderness" }],
        assessments: [
          { diagnosis: "Tension headache", icd_code: "G44.2", severity: "mild" },
        ],
        additional_notes: "Recommend acetaminophen.",
      };
  
      const result = formatClinicalSummary(summary);
      expect(result).toContain("Patient: John Doe");
      expect(result).toContain("Chief Complaint: Headache");
      expect(result).toContain("ICD-10: G44.2");
      expect(result).toContain("Severity: mild");
    });
  
    test("formatNextSteps produces expected output", () => {
      const nextSteps = {
        actions: [
          {
            action_type: "treatment",
            description: "Take acetaminophen",
            priority: "high",
            timeline: "As needed",
          },
        ],
        follow_up_appointment: "2025-11-20",
        red_flags: ["Severe headache", "Vision changes"],
      };
  
      const result = formatNextSteps(nextSteps);
      expect(result).toContain("[TREATMENT] Take acetaminophen");
      expect(result).toContain("Timeline: As needed");
      expect(result).toContain("Priority: high");
      expect(result).toContain("Follow-up Appointment: 2025-11-20");
      expect(result).toContain("Red Flags");
    });
  
    test("formatPatientEmail produces expected output", () => {
      const email = {
        greeting: "Hi John,",
        summary_of_findings: "Signs of tension headache",
        treatment_plan: "Use acetaminophen as needed",
        patient_instructions: [
          {
            instruction: "Take acetaminophen when headache occurs",
            category: "medication",
          },
        ],
        warning_signs: ["Sudden severe headache"],
        next_steps_timeline: "Follow up in 5 days",
        closing: "Best regards,",
        physician_signature: "Dr. Smith",
      };
  
      const result = formatPatientEmail(email);
      expect(result).toContain("Hi John,");
      expect(result).toContain("Signs of tension headache");
      expect(result).toContain("Use acetaminophen as needed");
      expect(result).toContain("[Medication] Take acetaminophen when headache occurs");
      expect(result).toContain("Sudden severe headache");
      expect(result).toContain("Dr. Smith");
    });
  });
  