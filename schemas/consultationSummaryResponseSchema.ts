import { z } from "zod";

// Physical Exam Finding
const PhysicalExamFindingSchema = z.object({
  body_part: z.string(),
  finding: z.string(),
});

// Assessment
export const AssessmentSchema = z.object({
  diagnosis: z.string(),
  icd_code: z.string().optional().nullable(),
  severity: z.enum(["mild", "moderate", "severe"]).optional().nullable(),
});

// Clinical Summary
const ClinicalSummarySchema = z.object({
  patient_name: z.string(),
  visit_date: z.string(), // ISO date string
  chief_complaint: z.string(),
  history_of_present_illness: z.string(),
  vital_signs: z.string().optional().nullable(),
  physical_exam_findings: z.array(PhysicalExamFindingSchema),
  assessments: z.array(AssessmentSchema),
  additional_notes: z.string().optional().nullable(),
});

// Patient Instruction
const PatientInstructionSchema = z.object({
  instruction: z.string(),
  category: z.string(),
});

// Patient Follow-Up Email
const PatientFollowUpEmailSchema = z.object({
  greeting: z.string(),
  summary_of_findings: z.string(),
  treatment_plan: z.string(),
  patient_instructions: z.array(PatientInstructionSchema),
  warning_signs: z.array(z.string()),
  next_steps_timeline: z.string(),
  closing: z.string(),
  physician_signature: z.string(),
});

// Next Step Action
const NextStepActionSchema = z.object({
  action_type: z.enum([
    "diagnostic",
    "treatment",
    "referral",
    "follow-up",
    "education",
  ]),
  description: z.string(),
  priority: z.enum(["high", "medium", "low"]).optional().nullable(),
  timeline: z.string().optional().nullable(),
});

// Next Steps
const NextStepsSchema = z.object({
  actions: z.array(NextStepActionSchema),
  follow_up_appointment: z.string().optional().nullable(),
  red_flags: z.array(z.string()).optional().nullable(),
});

// Consultation Summary Response
export const ConsultationSummaryResponseSchema = z.object({
  clinical_summary: ClinicalSummarySchema,
  next_steps: NextStepsSchema,
  patient_email: PatientFollowUpEmailSchema,
  generation_timestamp: z.string(), // ISO timestamp
  model_version: z.string().optional().nullable(),
});

// Export TypeScript types from schemas
export type ClinicalSummary = z.infer<typeof ClinicalSummarySchema>;
export type NextSteps = z.infer<typeof NextStepsSchema>;
export type PatientFollowUpEmail = z.infer<typeof PatientFollowUpEmailSchema>;
export type ConsultationSummaryResponse = z.infer<typeof ConsultationSummaryResponseSchema>;
