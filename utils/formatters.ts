import { ClinicalSummary, NextSteps, PatientFollowUpEmail } from "../schemas"; 
// adjust the import path to wherever your interfaces/types live

export function formatClinicalSummary(summary: ClinicalSummary): string {
  let output = `Patient: ${summary.patient_name}
Date: ${summary.visit_date}

Chief Complaint: ${summary.chief_complaint}

History of Present Illness:
${summary.history_of_present_illness}
`;

  if (summary.vital_signs) {
    output += `\nVital Signs:\n${summary.vital_signs}\n`;
  }

  if (summary.physical_exam_findings.length > 0) {
    output += "\nPhysical Examination:\n";
    summary.physical_exam_findings.forEach((finding) => {
      output += `- ${finding.body_part}: ${finding.finding}\n`;
    });
  }

  output += "\nAssessment:\n";
  summary.assessments.forEach((assessment, i) => {
    output += `${i + 1}. ${assessment.diagnosis}`;
    if (assessment.icd_code) {
      output += ` (ICD-10: ${assessment.icd_code})`;
    }
    if (assessment.severity) {
      output += ` - Severity: ${assessment.severity}`;
    }
    output += "\n";
  });

  if (summary.additional_notes) {
    output += `\nAdditional Notes:\n${summary.additional_notes}\n`;
  }

  return output;
}

export function formatNextSteps(nextSteps: NextSteps): string {
  let output = "";

  nextSteps.actions.forEach((action, i) => {
    output += `${i + 1}. [${action.action_type.toUpperCase()}] ${action.description}`;
    if (action.timeline) {
      output += ` (Timeline: ${action.timeline})`;
    }
    if (action.priority) {
      output += ` [Priority: ${action.priority}]`;
    }
    output += "\n";
  });

  if (nextSteps.follow_up_appointment) {
    output += `\nFollow-up Appointment: ${nextSteps.follow_up_appointment}\n`;
  }

  if (nextSteps.red_flags && nextSteps.red_flags.length > 0) {
    output += "\n⚠️ Red Flags - Call immediately if:\n";
    nextSteps.red_flags.forEach((flag) => {
      output += `- ${flag}\n`;
    });
  }

  return output;
}

export function formatPatientEmail(email: PatientFollowUpEmail): string {
  let output = `${email.greeting}

${email.summary_of_findings}

What we're doing next:
${email.treatment_plan}

What you should do:
`;

  email.patient_instructions.forEach((instruction) => {
    // assuming PatientInstruction has a `category` field
    output += `• [${instruction.category.charAt(0).toUpperCase() + instruction.category.slice(1)}] ${instruction.instruction}\n`;
  });

  if (email.warning_signs.length > 0) {
    output += "\n⚠️ Call us immediately if you experience:\n";
    email.warning_signs.forEach((warning) => {
      output += `• ${warning}\n`;
    });
  }

  output += `\nNext Steps:\n${email.next_steps_timeline}\n`;
  output += `\n${email.closing}\n\n${email.physician_signature}`;

  return output;
}
