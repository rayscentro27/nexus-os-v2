/**
 * Nexus OS v2 — Affiliate Approval Waiting Room.
 *
 * Tracks the approval lifecycle for each (non-free) partner program from the partnerOffers registry.
 * This is a STATUS layer only — it does not apply, contact partners, or activate anything.
 * Approved partner URLs arrive via the partner URL intake (src/lib/partnerUrlIntake.ts).
 *
 * Pure / deterministic. No I/O.
 */
import { PARTNER_OFFERS } from './partnerOffers';

export type AffiliateApprovalStatus =
  | 'not_applied'
  | 'application_submitted'
  | 'pending_review'
  | 'approved'
  | 'rejected'
  | 'on_hold';

export type UrlIntakeStatus = 'awaiting_urls' | 'urls_received' | 'urls_validated';

export interface AffiliateApprovalRecord {
  partner_offer_id: string;
  partner_name: string;
  category: string;
  program_name: string;
  application_status: AffiliateApprovalStatus;
  applied_at: string | null;
  decision_at: string | null;
  url_intake_status: UrlIntakeStatus;
  notes: string;
  next_action: string;
}

/** Order in which Ray should pursue approvals — highest leverage / lowest risk first. */
export const APPROVAL_PRIORITY: string[] = [
  'smartcredit',
  'bluevine',
  'docupost',
  'business_formation',
  'mercury',
  'relay',
  'registered_agent',
  'business_address',
  'business_phone',
  'website_domain_email',
  'bookkeeping',
  'vendor_credit',
  'funding_readiness_service',
];

function nextActionFor(status: AffiliateApprovalStatus): string {
  switch (status) {
    case 'not_applied': return 'Apply to the partner/affiliate program.';
    case 'application_submitted': return 'Wait for the partner to review; check back per their timeline.';
    case 'pending_review': return 'Pending partner decision; no action needed yet.';
    case 'approved': return 'Intake the approved affiliate/referral URL via partner URL intake.';
    case 'rejected': return 'Mark offer as DIY-only or find an alternate partner.';
    case 'on_hold': return 'Revisit when the program reopens or terms change.';
  }
}

/**
 * Default waiting-room records: every non-free partner starts `not_applied` / `awaiting_urls`.
 * Free/official offers (e.g. AnnualCreditReport.com) are excluded — they need no approval.
 */
export const AFFILIATE_APPROVAL_RECORDS: AffiliateApprovalRecord[] = PARTNER_OFFERS
  .filter((o) => o.revenue_type !== 'free_official')
  .map((o) => ({
    partner_offer_id: o.partner_offer_id,
    partner_name: o.partner_name,
    category: o.category,
    program_name: `${o.partner_name} affiliate/referral program`,
    application_status: 'not_applied' as AffiliateApprovalStatus,
    applied_at: null,
    decision_at: null,
    url_intake_status: 'awaiting_urls' as UrlIntakeStatus,
    notes: 'Default state — no application submitted yet.',
    next_action: nextActionFor('not_applied'),
  }));

export function getApprovalRecord(id: string): AffiliateApprovalRecord | undefined {
  return AFFILIATE_APPROVAL_RECORDS.find((r) => r.partner_offer_id === id);
}

export function approvalPriorityRank(id: string): number {
  const i = APPROVAL_PRIORITY.indexOf(id);
  return i === -1 ? APPROVAL_PRIORITY.length : i;
}

export function affiliateApprovalCounts(records = AFFILIATE_APPROVAL_RECORDS) {
  const by = (s: AffiliateApprovalStatus) => records.filter((r) => r.application_status === s).length;
  return {
    total: records.length,
    not_applied: by('not_applied'),
    application_submitted: by('application_submitted'),
    pending_review: by('pending_review'),
    approved: by('approved'),
    rejected: by('rejected'),
    on_hold: by('on_hold'),
    awaiting_urls: records.filter((r) => r.url_intake_status === 'awaiting_urls').length,
  };
}
