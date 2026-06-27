/**
 * Nexus OS v2 — Online business bank account affiliate research model.
 *
 * Internal research/report only — partner fit notes are estimates to validate, not live offers.
 * Pure / deterministic. Nexus never opens accounts or submits applications. No guarantee of approval.
 */

export interface OnlineBankPartner {
  partner_name: string;
  fits: string[];
  no_monthly_fee: boolean;
  invoicing: boolean;
  ach_wire: boolean;
  statements_for_funding: boolean;
  referral_program_likely: boolean;
  notes: string;
}

/** Candidate partners to research/validate (no affiliate URL activated here). */
export const ONLINE_BANK_PARTNERS: OnlineBankPartner[] = [
  { partner_name: 'Bluevine', fits: ['startup', 'llc_owner', 'funding_readiness'], no_monthly_fee: true, invoicing: true, ach_wire: true, statements_for_funding: true, referral_program_likely: true, notes: 'Business checking + interest; strong for funding readiness statements.' },
  { partner_name: 'Mercury', fits: ['startup', 'llc_owner', 'business_credit_building'], no_monthly_fee: true, invoicing: false, ach_wire: true, statements_for_funding: true, referral_program_likely: true, notes: 'Popular with startups; clean statements.' },
  { partner_name: 'Relay', fits: ['llc_owner', 'bookkeeping', 'business_credit_building'], no_monthly_fee: true, invoicing: false, ach_wire: true, statements_for_funding: true, referral_program_likely: true, notes: 'Multiple accounts; accountant-friendly.' },
  { partner_name: 'Novo', fits: ['startup', 'llc_owner', 'invoicing'], no_monthly_fee: true, invoicing: true, ach_wire: true, statements_for_funding: true, referral_program_likely: true, notes: 'Simple business checking + invoicing.' },
  { partner_name: 'Found', fits: ['solopreneur', 'startup'], no_monthly_fee: true, invoicing: true, ach_wire: true, statements_for_funding: true, referral_program_likely: true, notes: 'Banking + bookkeeping + taxes for solo owners.' },
  { partner_name: 'North One', fits: ['small_business', 'llc_owner'], no_monthly_fee: false, invoicing: false, ach_wire: true, statements_for_funding: true, referral_program_likely: true, notes: 'Budgeting envelopes; small monthly fee.' },
  { partner_name: 'Lili', fits: ['solopreneur', 'startup'], no_monthly_fee: true, invoicing: true, ach_wire: true, statements_for_funding: true, referral_program_likely: true, notes: 'Solo-focused; tax tools.' },
];

/** Recommended primary + backups (to validate against live referral terms). */
export const ONLINE_BANK_RECOMMENDATION = {
  primary: 'Bluevine',
  backups: ['Mercury', 'Relay'],
  reason: 'No monthly fee, ACH/wire, invoicing, and clean statements for funding readiness; likely referral program.',
} as const;

export const ONLINE_BANK_DIY_OPTION = {
  diy_option_name: 'Client’s own bank / local credit union',
  steps: ['Open a dedicated business checking account at any bank or credit union', 'Upload business bank proof / statements'],
  note: 'DIY is always available; the partner option is optional.',
} as const;

export const ONLINE_BANK_COMPLIANCE_NOTE =
  'Nexus does not open accounts automatically and does not submit applications. No guarantee of approval. Affiliate/referral relationships are disclosed; a DIY/own-bank option is always offered.';
