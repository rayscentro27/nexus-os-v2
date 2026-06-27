/**
 * Nexus OS v2 — Client Workflow models (GoClear / Apex).
 *
 * The backend operating brain for moving a client from signup to funding-ready. Pure /
 * deterministic config + types. No I/O, no external AI, no client-facing output.
 *
 * Core principle: Nexus can work internally; it cannot leave the building without approval.
 * Final client-facing recommendations are NEVER exposed until Ray-approved.
 */
import type { AutomationLevelId } from './nexusAutomationLevels';

// ---- Workflow stages --------------------------------------------------------

export type ClientWorkflowStage =
  | 'signup_started'
  | 'profile_created'
  | 'credit_report_source_needed'
  | 'credit_report_pending'
  | 'credit_report_received'
  | 'credit_analysis_ready'
  | 'business_setup_needed'
  | 'business_setup_in_progress'
  | 'business_analysis_ready'
  | 'letters_needed'
  | 'letters_ready'
  | 'mailing_needed'
  | 'funding_readiness_pending'
  | 'ray_review_needed'
  | 'approved_client_plan_ready'
  | 'client_plan_visible'
  | 'funding_ready';

/** Ordered stages → drives progress_percentage. */
export const CLIENT_WORKFLOW_STAGES: ClientWorkflowStage[] = [
  'signup_started',
  'profile_created',
  'credit_report_source_needed',
  'credit_report_pending',
  'credit_report_received',
  'credit_analysis_ready',
  'business_setup_needed',
  'business_setup_in_progress',
  'business_analysis_ready',
  'letters_needed',
  'letters_ready',
  'mailing_needed',
  'funding_readiness_pending',
  'ray_review_needed',
  'approved_client_plan_ready',
  'client_plan_visible',
  'funding_ready',
];

export type RevenueRiskLevel = 'low' | 'medium' | 'high' | 'critical';
export type RayReviewStatus = 'not_needed' | 'pending_review' | 'approved' | 'changes_requested';

/** What the CLIENT may see for a stage — never the internal recommendation until approved. */
export const CLIENT_VISIBLE_STAGE_LABEL: Record<ClientWorkflowStage, string> = {
  signup_started: 'Welcome — let’s get started',
  profile_created: 'Profile created',
  credit_report_source_needed: 'Choose your credit report source',
  credit_report_pending: 'Waiting for your credit report',
  credit_report_received: 'Credit report received',
  credit_analysis_ready: 'We’re reviewing your credit',
  business_setup_needed: 'Let’s set up your business foundation',
  business_setup_in_progress: 'Building your business foundation',
  business_analysis_ready: 'Reviewing your business setup',
  letters_needed: 'Preparing your letters',
  letters_ready: 'Your letters are ready to review',
  mailing_needed: 'Choose how to mail your letters',
  funding_readiness_pending: 'Checking your funding readiness',
  ray_review_needed: 'Final review in progress',
  approved_client_plan_ready: 'Your plan is being finalized',
  client_plan_visible: 'Your action plan is ready',
  funding_ready: 'You’re funding-ready',
};

/** Default next required action per stage (internal). */
export const STAGE_NEXT_ACTION: Record<ClientWorkflowStage, string> = {
  signup_started: 'Complete client profile.',
  profile_created: 'Choose a credit report source.',
  credit_report_source_needed: 'Select SmartCredit (recommended) or AnnualCreditReport.com (free).',
  credit_report_pending: 'Upload or import the credit report.',
  credit_report_received: 'Run internal credit analysis.',
  credit_analysis_ready: 'Begin business setup review.',
  business_setup_needed: 'Confirm business entity and core setup items.',
  business_setup_in_progress: 'Upload remaining business setup proofs.',
  business_analysis_ready: 'Prepare dispute/repair letters.',
  letters_needed: 'Generate letter drafts.',
  letters_ready: 'Approve letters, then choose mailing method.',
  mailing_needed: 'Choose DocuPost or USPS certified mail; upload mailing proof.',
  funding_readiness_pending: 'Complete funding readiness review.',
  ray_review_needed: 'Ray reviews the full client-facing action plan.',
  approved_client_plan_ready: 'Publish approved plan to client portal.',
  client_plan_visible: 'Client follows the approved action plan.',
  funding_ready: 'Route to recommended funding path (approval-gated).',
};

// ---- Credit report source ---------------------------------------------------

export type CreditReportSource = 'smartcredit' | 'annualcreditreport' | 'manual_upload' | 'other';
export type ScoreSource = 'smartcredit' | 'manual_entry' | 'imported_report' | 'unavailable';
export type ReportStatus = 'not_started' | 'pending' | 'received' | 'failed';

export interface CreditReportSourceOption {
  source: CreditReportSource;
  name: string;
  recommended: boolean;
  is_affiliate: boolean;
  provides_scores: boolean;
  disclosure: string | null;
  description: string;
}

export const CREDIT_REPORT_SOURCES: CreditReportSourceOption[] = [
  {
    source: 'smartcredit',
    name: 'SmartCredit (Recommended)',
    recommended: true,
    is_affiliate: true,
    provides_scores: true,
    disclosure: 'SmartCredit is a recommended partner; we may earn a commission if you sign up. It is not required.',
    description: 'Recommended because it supports credit score visibility, monitoring, tracking, and smoother Nexus analysis.',
  },
  {
    source: 'annualcreditreport',
    name: 'AnnualCreditReport.com (Free)',
    recommended: false,
    is_affiliate: false,
    provides_scores: false,
    disclosure: null,
    description: 'The free official credit report option. May provide reports only, not scores. Upload your report and enter a score manually if you have one from another source.',
  },
  {
    source: 'manual_upload',
    name: 'Manual upload (other source)',
    recommended: false,
    is_affiliate: false,
    provides_scores: false,
    disclosure: null,
    description: 'Upload a credit report you already have from another source.',
  },
];

// ---- SmartCredit connector shell (NO password/scrape/login) ------------------

export type SmartCreditConnectorStatus =
  | 'not_configured'
  | 'affiliate_link_only'
  | 'partner_signup_ready'
  | 'api_connected'
  | 'report_import_ready'
  | 'disabled';

export interface SmartCreditConnectorShell {
  status: SmartCreditConnectorStatus;
  affiliate_url: string | null;
  partner_id: string | null;
  callback_status: string | null;
  customer_token: null; // never stored client-side; placeholder only
  account_token: null; // never stored client-side; placeholder only
  external_customer_reference: string | null;
  report_download_status: 'requires_partner_api_confirmation' | 'unavailable';
  notes: string;
}

/** Default shell — affiliate-link-only, no credentials, no scrape, no automated login. */
export const SMARTCREDIT_CONNECTOR_DEFAULT: SmartCreditConnectorShell = {
  status: 'not_configured',
  affiliate_url: null,
  partner_id: null,
  callback_status: null,
  customer_token: null,
  account_token: null,
  external_customer_reference: null,
  report_download_status: 'requires_partner_api_confirmation',
  notes: 'No password storage, no scraping, no automated login. Report download requires a verified SmartCredit partner/API endpoint to be confirmed in project config/docs.',
};

// ---- Credit score model -----------------------------------------------------

export type CreditBureau = 'equifax' | 'experian' | 'transunion' | 'unknown';

export interface CreditScoreEntry {
  client_id: string;
  tenant_id: string;
  bureau: CreditBureau;
  score: number | null;
  score_model: string | null; // e.g. VantageScore 3.0, FICO 8
  score_source: ScoreSource;
  reported_at: string;
  imported_from: string | null;
  notes: string | null;
}

export const SCORE_DISCLAIMER =
  'Scores may vary by model, bureau, lender, and timing. Scores and readiness analysis are for education/planning and are not a guarantee of approval, deletion, score increase, or funding.';

// ---- Business setup items ---------------------------------------------------

export type BusinessSetupPath = 'partner' | 'diy' | 'already_completed' | 'not_applicable';
export type CompletionStatus = 'not_started' | 'in_progress' | 'completed' | 'verified';

export interface BusinessSetupItemDef {
  setup_item_key: string;
  setup_item_name: string;
  required_for_bankability: boolean;
  recommended_partner_name: string | null;
  diy_official_option_name: string | null;
  diy_instruction_text: string;
  proof_required: boolean;
  bankability_score_impact: number; // 0-100 contribution weight
  funding_readiness_score_impact: number;
}

export const BUSINESS_SETUP_ITEMS: BusinessSetupItemDef[] = [
  { setup_item_key: 'llc_entity', setup_item_name: 'LLC / Entity Formation', required_for_bankability: true, recommended_partner_name: 'Formation partner', diy_official_option_name: 'State Secretary of State filing', diy_instruction_text: 'File articles of organization with your state.', proof_required: true, bankability_score_impact: 15, funding_readiness_score_impact: 15 },
  { setup_item_key: 'ein', setup_item_name: 'EIN', required_for_bankability: true, recommended_partner_name: 'Formation partner', diy_official_option_name: 'IRS EIN application (free)', diy_instruction_text: 'Apply for an EIN free at IRS.gov.', proof_required: true, bankability_score_impact: 12, funding_readiness_score_impact: 12 },
  { setup_item_key: 'registered_agent', setup_item_name: 'Registered Agent', required_for_bankability: false, recommended_partner_name: 'Registered agent partner', diy_official_option_name: 'Self/official agent', diy_instruction_text: 'Designate a registered agent in your state.', proof_required: false, bankability_score_impact: 4, funding_readiness_score_impact: 3 },
  { setup_item_key: 'business_address', setup_item_name: 'Business Address', required_for_bankability: true, recommended_partner_name: 'Virtual address partner', diy_official_option_name: 'Commercial address', diy_instruction_text: 'Use a real commercial/business address (not a PO box where avoidable).', proof_required: true, bankability_score_impact: 8, funding_readiness_score_impact: 8 },
  { setup_item_key: 'business_phone', setup_item_name: 'Business Phone', required_for_bankability: true, recommended_partner_name: 'VoIP partner', diy_official_option_name: 'Business phone line', diy_instruction_text: 'Set up a dedicated business phone number and list it.', proof_required: false, bankability_score_impact: 6, funding_readiness_score_impact: 6 },
  { setup_item_key: 'website_domain', setup_item_name: 'Website / Domain', required_for_bankability: true, recommended_partner_name: 'Website/domain partner', diy_official_option_name: 'Self-built site', diy_instruction_text: 'Register a domain and publish a basic business website.', proof_required: false, bankability_score_impact: 6, funding_readiness_score_impact: 5 },
  { setup_item_key: 'business_email', setup_item_name: 'Business Email', required_for_bankability: true, recommended_partner_name: 'Email partner', diy_official_option_name: 'Domain email', diy_instruction_text: 'Create a professional email at your domain.', proof_required: false, bankability_score_impact: 4, funding_readiness_score_impact: 4 },
  { setup_item_key: 'duns_profile', setup_item_name: 'DUNS / Business Credit Profile', required_for_bankability: true, recommended_partner_name: 'Business credit tool', diy_official_option_name: 'D&B DUNS request (free)', diy_instruction_text: 'Request a free DUNS number from Dun & Bradstreet.', proof_required: true, bankability_score_impact: 10, funding_readiness_score_impact: 12 },
  { setup_item_key: 'business_bank_account', setup_item_name: 'Business Bank Account', required_for_bankability: true, recommended_partner_name: 'Business banking partner', diy_official_option_name: 'Any business bank', diy_instruction_text: 'Open a dedicated business checking account.', proof_required: true, bankability_score_impact: 12, funding_readiness_score_impact: 14 },
  { setup_item_key: 'bookkeeping', setup_item_name: 'Bookkeeping / Accounting', required_for_bankability: false, recommended_partner_name: 'Bookkeeping partner', diy_official_option_name: 'Spreadsheet/DIY', diy_instruction_text: 'Track income and expenses from day one.', proof_required: false, bankability_score_impact: 4, funding_readiness_score_impact: 5 },
  { setup_item_key: 'vendor_accounts', setup_item_name: 'Vendor Credit Accounts', required_for_bankability: true, recommended_partner_name: 'Vendor credit partner', diy_official_option_name: 'Net-30 vendors', diy_instruction_text: 'Open starter net-30 vendor accounts that report to business bureaus.', proof_required: true, bankability_score_impact: 8, funding_readiness_score_impact: 10 },
  { setup_item_key: 'licenses_permits', setup_item_name: 'Licenses / Permits', required_for_bankability: false, recommended_partner_name: null, diy_official_option_name: 'State/local licensing', diy_instruction_text: 'Obtain any licenses/permits your industry requires.', proof_required: true, bankability_score_impact: 4, funding_readiness_score_impact: 4 },
  { setup_item_key: 'bank_statements', setup_item_name: 'Business Bank Statements', required_for_bankability: true, recommended_partner_name: null, diy_official_option_name: 'From your bank', diy_instruction_text: 'Maintain 3-6 months of healthy business bank statements.', proof_required: true, bankability_score_impact: 7, funding_readiness_score_impact: 12 },
];

// ---- Credit repair letters + mailing ----------------------------------------

export type LetterType =
  | 'bureau_dispute'
  | 'creditor_dispute'
  | 'collector_validation'
  | 'follow_up'
  | 'method_of_verification'
  | 'goodwill'
  | 'pay_for_delete_request';

export type LetterRecipientType = 'bureau' | 'creditor' | 'collector' | 'lender' | 'other';
export type LetterApprovalStatus = 'draft' | 'pending_approval' | 'approved' | 'changes_requested';

export const LETTER_TYPES: { type: LetterType; label: string; recipient_type: LetterRecipientType }[] = [
  { type: 'bureau_dispute', label: 'Bureau Dispute', recipient_type: 'bureau' },
  { type: 'creditor_dispute', label: 'Creditor Dispute', recipient_type: 'creditor' },
  { type: 'collector_validation', label: 'Collector Validation', recipient_type: 'collector' },
  { type: 'follow_up', label: 'Follow-up Letter', recipient_type: 'other' },
  { type: 'method_of_verification', label: 'Method of Verification', recipient_type: 'bureau' },
  { type: 'goodwill', label: 'Goodwill Letter', recipient_type: 'creditor' },
  { type: 'pay_for_delete_request', label: 'Pay-for-Delete Request (draft)', recipient_type: 'collector' },
];

export type MailingMethod = 'docupost' | 'usps_certified' | 'manual_other';
export type MailingStatus =
  | 'not_started'
  | 'method_selected'
  | 'awaiting_proof'
  | 'mailed'
  | 'response_window_open'
  | 'follow_up_due'
  | 'completed';

export interface MailingMethodOption {
  method: MailingMethod;
  name: string;
  recommended: boolean;
  is_affiliate: boolean;
  connector_required: boolean;
  description: string;
  disclosure: string | null;
}

export const MAILING_METHODS: MailingMethodOption[] = [
  {
    method: 'docupost',
    name: 'DocuPost (online mailing)',
    recommended: true,
    is_affiliate: true,
    connector_required: true,
    description: 'Online certified mailing partner. Connector shell only in v1 — Nexus does not send letters or spend postage automatically.',
    disclosure: 'DocuPost may be a referral/affiliate partner; we may earn a commission. It is optional.',
  },
  {
    method: 'usps_certified',
    name: 'Print + USPS Certified Mail (DIY)',
    recommended: false,
    is_affiliate: false,
    connector_required: false,
    description: 'Download the PDF, print it, and mail it Certified Mail at your local Post Office. Upload your receipt/tracking proof so Nexus can track deadlines.',
    disclosure: null,
  },
];

// ---- Client profile (workflow status) ---------------------------------------

export interface ClientWorkflowProfile {
  client_id: string;
  tenant_id: string;
  client_label: string;
  current_stage: ClientWorkflowStage;
  next_required_action: string;
  due_at: string | null;
  days_stuck: number;
  progress_percentage: number;
  funding_readiness_impact: number;
  revenue_risk_level: RevenueRiskLevel;
  ray_review_status: RayReviewStatus;
  client_visible_status: string;
  selected_credit_report_source: CreditReportSource | null;
  source_selected_at: string | null;
  affiliate_partner_id: string | null;
  affiliate_url: string | null;
  affiliate_disclosure_accepted: boolean;
  client_consent_accepted: boolean;
  score_available: boolean;
  score_source: ScoreSource;
  report_upload_status: ReportStatus;
  report_import_status: ReportStatus;
  updated_at: string;
}

/** Automation level applied to each workflow action type. */
export const CLIENT_WORKFLOW_ACTION_LEVELS: Record<string, AutomationLevelId> = {
  // Level 1 — autonomous internal
  workflow_status_update: 'autonomous_internal',
  credit_analysis: 'autonomous_internal',
  business_bankability_scoring: 'autonomous_internal',
  funding_readiness_scoring: 'autonomous_internal',
  reminder_draft_generation: 'autonomous_internal',
  stuck_client_detection: 'autonomous_internal',
  hermes_prep_brief: 'autonomous_internal',
  affiliate_opportunity_scoring: 'autonomous_internal',
  // Level 2 — approval-gated
  send_client_message: 'approval_gated',
  contact_client_or_lead: 'approval_gated',
  publish_client_plan: 'approval_gated',
  activate_connector: 'approval_gated',
  activate_scheduler: 'approval_gated',
  mail_letters: 'approval_gated',
  submit_dispute: 'approval_gated',
  apply_for_funding: 'approval_gated',
  expose_client_recommendation: 'approval_gated',
  // Level 3 — blocked / high-risk
  store_smartcredit_password: 'blocked_high_risk',
  scrape_smartcredit: 'blocked_high_risk',
  auto_submit_disputes: 'blocked_high_risk',
  auto_mail_letters: 'blocked_high_risk',
  auto_contact_bureaus_creditors: 'blocked_high_risk',
  auto_file_llc_ein_state: 'blocked_high_risk',
  auto_open_accounts: 'blocked_high_risk',
  auto_apply_funding: 'blocked_high_risk',
  external_ai_on_client_credit_data: 'blocked_high_risk',
};
