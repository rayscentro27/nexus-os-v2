/**
 * Nexus OS v2 — Client Workflow reminder / stuck-client model.
 * Pure / deterministic. Reminder DRAFTS are Level 1 (internal). Sending external reminders is
 * Level 2 (approval-gated, requires client opt-in). No auto-send in v1.
 */
import type { RevenueRiskLevel } from './clientWorkflow';

export type ReminderWorkflowArea = 'credit' | 'business' | 'funding';
export type ReminderStatus = 'pending' | 'sent_internal' | 'completed' | 'escalated' | 'snoozed';
export type EscalationStatus = 'none' | 'hermes' | 'ray';

export interface ReminderTaskTemplate {
  task_key: string;
  workflow_area: ReminderWorkflowArea;
  task_title: string;
  task_description: string;
}

export const REMINDER_TASK_TEMPLATES: ReminderTaskTemplate[] = [
  // Credit
  { task_key: 'choose_credit_report_source', workflow_area: 'credit', task_title: 'Choose your credit report source', task_description: 'Pick SmartCredit (recommended) or AnnualCreditReport.com (free).' },
  { task_key: 'connect_smartcredit_or_upload_report', workflow_area: 'credit', task_title: 'Connect SmartCredit or upload your report', task_description: 'Sign up via the recommended link or upload your report.' },
  { task_key: 'upload_credit_report', workflow_area: 'credit', task_title: 'Upload your credit report', task_description: 'Upload your most recent credit report.' },
  { task_key: 'enter_credit_scores_if_missing', workflow_area: 'credit', task_title: 'Enter your credit scores (if missing)', task_description: 'If your report has no scores, enter them manually.' },
  { task_key: 'review_credit_analysis', workflow_area: 'credit', task_title: 'Review your credit analysis', task_description: 'Review your readiness analysis once approved.' },
  { task_key: 'approve_dispute_letters', workflow_area: 'credit', task_title: 'Approve your dispute letters', task_description: 'Review and approve prepared letters before mailing.' },
  { task_key: 'choose_mailing_method', workflow_area: 'credit', task_title: 'Choose your mailing method', task_description: 'Select DocuPost or USPS certified mail.' },
  { task_key: 'upload_mailing_receipt', workflow_area: 'credit', task_title: 'Upload your mailing receipt', task_description: 'Upload the certified mail / tracking proof.' },
  { task_key: 'upload_updated_report', workflow_area: 'credit', task_title: 'Upload your updated report', task_description: 'Upload a refreshed report after the response window.' },
  // Business
  { task_key: 'confirm_business_entity', workflow_area: 'business', task_title: 'Confirm your business entity', task_description: 'Confirm your LLC/entity details.' },
  { task_key: 'upload_llc_proof', workflow_area: 'business', task_title: 'Upload LLC proof', task_description: 'Upload your formation documents.' },
  { task_key: 'add_ein', workflow_area: 'business', task_title: 'Add your EIN', task_description: 'Provide your EIN (free from IRS.gov).' },
  { task_key: 'add_business_address', workflow_area: 'business', task_title: 'Add a business address', task_description: 'Add a real commercial business address.' },
  { task_key: 'add_business_phone', workflow_area: 'business', task_title: 'Add a business phone', task_description: 'Add a dedicated business phone number.' },
  { task_key: 'add_website', workflow_area: 'business', task_title: 'Add a website', task_description: 'Register a domain and publish a basic site.' },
  { task_key: 'add_business_email', workflow_area: 'business', task_title: 'Add a business email', task_description: 'Create a professional email at your domain.' },
  { task_key: 'add_duns_profile', workflow_area: 'business', task_title: 'Add a DUNS profile', task_description: 'Request a free DUNS number from D&B.' },
  { task_key: 'add_business_bank_account', workflow_area: 'business', task_title: 'Add a business bank account', task_description: 'Open a dedicated business checking account.' },
  { task_key: 'add_vendor_accounts', workflow_area: 'business', task_title: 'Add vendor accounts', task_description: 'Open starter net-30 vendor accounts.' },
  { task_key: 'upload_bank_statements', workflow_area: 'business', task_title: 'Upload bank statements', task_description: 'Upload 3-6 months of business bank statements.' },
  // Funding
  { task_key: 'complete_funding_readiness_review', workflow_area: 'funding', task_title: 'Complete funding readiness review', task_description: 'Finish the funding readiness checklist.' },
  { task_key: 'upload_required_documents', workflow_area: 'funding', task_title: 'Upload required documents', task_description: 'Upload documents needed for funding readiness.' },
  { task_key: 'review_recommended_funding_path', workflow_area: 'funding', task_title: 'Review recommended funding path', task_description: 'Review your approved funding path (after Ray approval).' },
  { task_key: 'book_funding_strategy_call', workflow_area: 'funding', task_title: 'Book a funding strategy call', task_description: 'Schedule a call to plan your funding.' },
];

/** Reminder timing thresholds in days. */
export const REMINDER_TIMINGS = {
  urgent_blocker_hours: 24,
  incomplete_setup_days: 3,
  stuck_task_days: 7,
  escalation_days: 14,
} as const;

export interface ClientReminder {
  client_id: string;
  tenant_id: string;
  workflow_area: ReminderWorkflowArea;
  task_key: string;
  task_title: string;
  task_description: string;
  due_at: string | null;
  completed_at: string | null;
  completion_proof_path: string | null;
  reminder_status: ReminderStatus;
  reminder_count: number;
  last_reminder_at: string | null;
  next_reminder_at: string | null;
  escalation_status: EscalationStatus;
  revenue_risk_level: RevenueRiskLevel;
}

/** Deterministic escalation given how many days a task has been stuck. */
export function escalationForDaysStuck(daysStuck: number): EscalationStatus {
  if (daysStuck >= REMINDER_TIMINGS.escalation_days) return 'ray';
  if (daysStuck >= REMINDER_TIMINGS.stuck_task_days) return 'hermes';
  return 'none';
}

/** Revenue risk increases the longer a paying client is stuck. */
export function revenueRiskForDaysStuck(daysStuck: number): RevenueRiskLevel {
  if (daysStuck >= REMINDER_TIMINGS.escalation_days) return 'critical';
  if (daysStuck >= REMINDER_TIMINGS.stuck_task_days) return 'high';
  if (daysStuck >= REMINDER_TIMINGS.incomplete_setup_days) return 'medium';
  return 'low';
}
