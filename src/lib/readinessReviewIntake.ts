/**
 * Nexus OS v2 — Readiness Review Intake Config.
 *
 * Structured intake data model for the $97 Credit & Funding Readiness Review.
 * Pure config — no I/O, no external calls. Hermes reads this to validate intake
 * completeness and guide the review process.
 */

export interface IntakeSection {
  id: string;
  label: string;
  description: string;
  required: boolean;
  fields: IntakeField[];
}

export interface IntakeField {
  key: string;
  label: string;
  type: 'text' | 'select' | 'number' | 'boolean' | 'checklist';
  options?: string[];
  required: boolean;
  helpText?: string;
}

export const INTAKE_SECTIONS: IntakeSection[] = [
  {
    id: 'personal_credit',
    label: 'Personal Credit Readiness',
    description: 'Baseline credit profile information.',
    required: true,
    fields: [
      { key: 'credit_score_range', label: 'Approximate credit score range', type: 'select', options: ['300-500', '500-600', '600-700', '700+'], required: true },
      { key: 'bureaus_to_check', label: 'Which bureaus to check', type: 'select', options: ['Equifax', 'TransUnion', 'Experian', 'All three'], required: true },
      { key: 'report_access', label: 'Access to credit reports', type: 'select', options: ['AnnualCreditReport.com', 'SmartCredit', 'Credit monitoring service', 'No access'], required: true },
      { key: 'last_check_date', label: 'When did you last check your credit report', type: 'text', required: false },
    ],
  },
  {
    id: 'credit_report_availability',
    label: 'Credit Report Availability',
    description: 'Whether the client can provide their credit report.',
    required: true,
    fields: [
      { key: 'can_provide_report', label: 'Can you provide your credit report or scores?', type: 'select', options: ['Yes, I have it', 'Yes, I can get it', 'No, I need help'], required: true },
      { key: 'share_method', label: 'How would you prefer to share it?', type: 'select', options: ['Upload', 'Screenshot', 'Verbal', 'I will get it'], required: false },
      { key: 'monitoring_service', label: 'Credit monitoring service', type: 'select', options: ['SmartCredit', 'Credit Karma', 'Experian', 'None'], required: false },
    ],
  },
  {
    id: 'negative_items',
    label: 'Negative Items',
    description: 'Late payments, collections, charge-offs, judgments, bankruptcies.',
    required: true,
    fields: [
      { key: 'late_payments', label: 'Late payments', type: 'select', options: ['None', '1-3', '4+', 'Not sure'], required: true },
      { key: 'collections', label: 'Collection accounts', type: 'select', options: ['None', '1-2', '3+', 'Not sure'], required: true },
      { key: 'chargeoffs', label: 'Charge-offs', type: 'select', options: ['None', '1-2', '3+', 'Not sure'], required: true },
      { key: 'judgments_liens', label: 'Judgments or liens', type: 'select', options: ['None', '1-2', 'Not sure'], required: true },
      { key: 'bankruptcies', label: 'Bankruptcies', type: 'select', options: ['None', 'Chapter 7', 'Chapter 13', 'Not sure'], required: true },
      { key: 'inaccurate_items', label: 'Items believed inaccurate', type: 'text', required: false, helpText: 'Describe any items you believe are wrong.' },
    ],
  },
  {
    id: 'credit_utilization',
    label: 'Credit Utilization',
    description: 'Current credit card balances vs limits.',
    required: true,
    fields: [
      { key: 'total_balances', label: 'Approximate total credit card balances', type: 'text', required: true },
      { key: 'total_limits', label: 'Approximate total credit card limits', type: 'text', required: true },
      { key: 'utilization_percent', label: 'Utilization percentage (if known)', type: 'number', required: false },
      { key: 'maxed_out_cards', label: 'Any maxed-out cards', type: 'text', required: false },
    ],
  },
  {
    id: 'inquiries',
    label: 'Inquiries',
    description: 'Recent hard inquiries.',
    required: true,
    fields: [
      { key: 'hard_inquiries_12mo', label: 'Hard inquiries in last 12 months', type: 'select', options: ['0-2', '3-5', '6+', 'Not sure'], required: true },
      { key: 'recent_applications', label: 'Recent credit applications', type: 'text', required: false, helpText: 'What type and when.' },
    ],
  },
  {
    id: 'collections_chargeoffs',
    label: 'Collections / Charge-Offs',
    description: 'Detailed collection and charge-off status.',
    required: true,
    fields: [
      { key: 'collection_accounts', label: 'Accounts in collections (count and amounts)', type: 'text', required: true },
      { key: 'chargeoff_accounts', label: 'Charged-off accounts (count and amounts)', type: 'text', required: true },
      { key: 'negotiation_attempts', label: 'Pay-for-delete or settlement attempts', type: 'text', required: false },
    ],
  },
  {
    id: 'credit_goals',
    label: 'Credit Goals',
    description: 'What the client wants to achieve.',
    required: true,
    fields: [
      { key: 'primary_goal', label: 'Primary credit goal', type: 'select', options: ['Improve score', 'Remove negatives', 'Qualify for loan', 'Qualify for business funding', 'General improvement'], required: true },
      { key: 'target_score', label: 'Target credit score', type: 'text', required: false },
      { key: 'timeline', label: 'Timeline', type: 'select', options: ['1-3 months', '3-6 months', '6-12 months', '12+ months'], required: true },
    ],
  },
  {
    id: 'business_entity',
    label: 'Business Entity Status',
    description: 'LLC, corporation, sole proprietorship status.',
    required: true,
    fields: [
      { key: 'entity_type', label: 'Business entity type', type: 'select', options: ['LLC', 'Corporation', 'Sole Proprietor', 'None', 'In Progress'], required: true },
      { key: 'registration_state', label: 'State of registration', type: 'text', required: false },
      { key: 'good_standing', label: 'In good standing with SOS?', type: 'select', options: ['Yes', 'No', 'Not sure'], required: true },
      { key: 'formation_date', label: 'Formation date', type: 'text', required: false },
    ],
  },
  {
    id: 'ein_duns_sos_naics',
    label: 'EIN / DUNS / SOS / NAICS',
    description: 'Federal and business identifiers.',
    required: true,
    fields: [
      { key: 'ein_status', label: 'EIN status', type: 'select', options: ['Yes, I know it', 'Yes, need to find it', 'No, need to get one'], required: true },
      { key: 'duns_status', label: 'DUNS number status', type: 'select', options: ['Yes', 'In progress', 'No, need one', 'Not sure what this is'], required: true },
      { key: 'naics_code', label: 'NAICS code', type: 'text', required: false },
      { key: 'sam_gov', label: 'Registered with SAM.gov?', type: 'select', options: ['Yes', 'No', 'Not sure what this is'], required: false },
    ],
  },
  {
    id: 'business_contact',
    label: 'Business Address / Phone / Email / Website',
    description: 'Business contact information consistency.',
    required: true,
    fields: [
      { key: 'business_address', label: 'Dedicated business address', type: 'select', options: ['Yes, physical', 'Yes, virtual', 'No, using home'], required: true },
      { key: 'business_phone', label: 'Dedicated business phone', type: 'select', options: ['Yes, VoIP', 'Yes, mobile', 'No'], required: true },
      { key: 'business_email', label: 'Professional business email', type: 'select', options: ['Yes, domain-based', 'Yes, Gmail/free', 'No'], required: true },
      { key: 'business_website', label: 'Business website', type: 'select', options: ['Yes, live', 'Yes, in progress', 'No'], required: true },
      { key: 'info_consistent', label: 'Business info consistent across platforms?', type: 'select', options: ['Yes', 'No', 'Not sure'], required: true },
    ],
  },
  {
    id: 'business_bank',
    label: 'Business Bank Account',
    description: 'Dedicated business banking.',
    required: true,
    fields: [
      { key: 'has_business_bank', label: 'Dedicated business bank account?', type: 'select', options: ['Yes, traditional', 'Yes, online', 'No'], required: true },
      { key: 'bank_name', label: 'Bank name', type: 'text', required: false },
      { key: 'account_age', label: 'How long has the account been open?', type: 'select', options: ['Less than 3 months', '3-6 months', '6-12 months', '12+ months'], required: true },
      { key: 'has_business_credit_card', label: 'Business credit card?', type: 'select', options: ['Yes', 'No'], required: true },
    ],
  },
  {
    id: 'business_credit',
    label: 'Business Credit Monitoring',
    description: 'D&B profile, PAYDEX, vendor tradelines.',
    required: true,
    fields: [
      { key: 'has_dnb_profile', label: 'Dun & Bradstreet credit profile?', type: 'select', options: ['Yes', 'No', 'Not sure'], required: true },
      { key: 'paydex_score', label: 'PAYDEX score (if known)', type: 'text', required: false },
      { key: 'monitors_business_credit', label: 'Monitors business credit?', type: 'select', options: ['Yes', 'No'], required: true },
      { key: 'vendor_tradelines', label: 'Vendor tradeline accounts (count)', type: 'text', required: false },
    ],
  },
  {
    id: 'funding_goal',
    label: 'Funding Goal',
    description: 'Type and amount of funding desired.',
    required: true,
    fields: [
      { key: 'funding_type', label: 'Type of funding', type: 'select', options: ['Business credit card', 'Line of credit', 'SBA loan', 'Equipment financing', 'Working capital', 'Grant', 'Not sure yet'], required: true },
      { key: 'funding_amount', label: 'Amount needed', type: 'text', required: true },
      { key: 'funding_purpose', label: 'Purpose of funding', type: 'text', required: true },
      { key: 'funding_timeline', label: 'Timeline for funding', type: 'select', options: ['1-3 months', '3-6 months', '6-12 months'], required: true },
    ],
  },
  {
    id: 'timeline',
    label: 'Timeline & Constraints',
    description: 'Client readiness to act.',
    required: true,
    fields: [
      { key: 'start_timeline', label: 'When to start?', type: 'select', options: ['Immediately', 'Within 2 weeks', 'Within 1 month', 'Just exploring'], required: true },
      { key: 'willing_to_act', label: 'Willing to complete action items within 30 days?', type: 'select', options: ['Yes', 'No', 'Maybe'], required: true },
      { key: 'biggest_constraint', label: 'Biggest constraint', type: 'select', options: ['Time', 'Money', 'Knowledge', 'Motivation'], required: true },
    ],
  },
  {
    id: 'documents_available',
    label: 'Documents Available',
    description: 'Checklist of documents the client already has.',
    required: true,
    fields: [
      { key: 'govt_id', label: 'Government ID', type: 'boolean', required: false },
      { key: 'proof_of_address', label: 'Proof of address', type: 'boolean', required: false },
      { key: 'formation_docs', label: 'Business formation documents', type: 'boolean', required: false },
      { key: 'ein_confirmation', label: 'EIN confirmation letter', type: 'boolean', required: false },
      { key: 'personal_bank_statements', label: 'Personal bank statements', type: 'boolean', required: false },
      { key: 'business_bank_statements', label: 'Business bank statements', type: 'boolean', required: false },
      { key: 'credit_report_printout', label: 'Credit report printout', type: 'boolean', required: false },
      { key: 'tax_returns', label: 'Tax returns', type: 'boolean', required: false },
      { key: 'revenue_summary', label: 'Revenue summary / P&L', type: 'boolean', required: false },
      { key: 'business_license', label: 'Business license', type: 'boolean', required: false },
    ],
  },
];

export const INTAKE_CONSENT_LANGUAGE = `By providing this information, I understand that:

1. This is a readiness review, not legal or financial advice.
2. GoClear/Nexus does not guarantee credit score improvements, funding approvals, or dispute outcomes.
3. No information shared will be used to submit applications, dispute items, or contact creditors/bureaus without my explicit written approval.
4. All recommendations are advisory and require my approval before any action is taken.
5. I may be offered additional services ($297 Credit Assistant Plan, Monthly Readiness Subscription) after the review, but there is no obligation.
6. My information will be kept confidential and used only for the purpose of this review.`;

export function getIntakeSection(sectionId: string): IntakeSection | undefined {
  return INTAKE_SECTIONS.find(s => s.id === sectionId);
}

export function getRequiredSections(): IntakeSection[] {
  return INTAKE_SECTIONS.filter(s => s.required);
}

export function calculateIntakeCompleteness(answers: Record<string, unknown>): { total: number; answered: number; requiredAnswered: number; requiredTotal: number; complete: boolean } {
  let total = 0;
  let answered = 0;
  let requiredAnswered = 0;
  let requiredTotal = 0;
  for (const section of INTAKE_SECTIONS) {
    for (const field of section.fields) {
      total++;
      const val = answers[field.key];
      if (val !== undefined && val !== null && val !== '') answered++;
      if (field.required) {
        requiredTotal++;
        if (val !== undefined && val !== null && val !== '') requiredAnswered++;
      }
    }
  }
  return { total, answered, requiredAnswered, requiredTotal, complete: requiredAnswered >= requiredTotal };
}
