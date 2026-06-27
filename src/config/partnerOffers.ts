/**
 * Nexus OS v2 — Partner Offers registry (central, approval-ready, report-only).
 *
 * Mirrors the existing `partner_offers` table shape and the affiliate categories from
 * clientWorkflowAffiliate.ts / onlineBusinessBankAffiliates.ts. URLs are placeholders to configure;
 * nothing here activates an affiliate link, charges, or contacts. Pure / deterministic.
 */

export type PartnerRevenueType = 'affiliate' | 'referral' | 'service_fee' | 'free_official' | 'commission';
export type PartnerActivationStatus = 'proposed' | 'approved' | 'active' | 'disabled';
export type PartnerConfigStatus = 'configured' | 'needs_config';
export type PartnerRiskLevel = 'low' | 'medium' | 'high';

export interface PartnerOffer {
  partner_offer_id: string;
  category: string;
  partner_name: string;
  offer_name: string;
  affiliate_url: string | null;
  referral_url: string | null;
  application_url: string | null;
  diy_option_name: string | null;
  diy_option_url: string | null;
  disclosure_text: string;
  recommended_reason: string;
  client_trigger: string;
  target_client_stage: string;
  revenue_type: PartnerRevenueType;
  estimated_revenue: string;
  approval_required: boolean;
  activation_status: PartnerActivationStatus;
  configuration_status: PartnerConfigStatus;
  risk_level: PartnerRiskLevel;
  compliance_notes: string;
  last_validated_at: string | null;
  next_validation_due_at: string | null;
}

const DISCLOSURE = 'Recommended partner; we may earn a commission/referral if you sign up. Optional — a free/DIY option is always available.';
const NO_GUARANTEE = 'Educational/planning only. No guarantee of approval, deletion, score increase, or funding.';

function offer(p: Partial<PartnerOffer> & {
  partner_offer_id: string; category: string; partner_name: string; offer_name: string;
  client_trigger: string; target_client_stage: string; revenue_type: PartnerRevenueType; estimated_revenue: string;
}): PartnerOffer {
  const isFree = p.revenue_type === 'free_official';
  return {
    affiliate_url: null,
    referral_url: null,
    application_url: null,
    diy_option_name: null,
    diy_option_url: null,
    disclosure_text: isFree ? 'Free official option — no affiliate relationship.' : DISCLOSURE,
    recommended_reason: '',
    approval_required: !isFree,
    activation_status: 'proposed',
    configuration_status: 'needs_config',
    risk_level: 'low',
    compliance_notes: NO_GUARANTEE,
    last_validated_at: null,
    next_validation_due_at: null,
    ...p,
  };
}

export const PARTNER_OFFERS: PartnerOffer[] = [
  offer({
    partner_offer_id: 'smartcredit', category: 'credit_monitoring', partner_name: 'SmartCredit',
    offer_name: 'SmartCredit credit monitoring + score tracking',
    recommended_reason: 'Score visibility, monitoring, progress tracking, and smoother Nexus analysis.',
    client_trigger: 'Client needs a credit report/score source.', target_client_stage: 'credit_report_source_needed',
    revenue_type: 'affiliate', estimated_revenue: '$ per signup (validate)',
    diy_option_name: 'AnnualCreditReport.com (free)', risk_level: 'low',
    compliance_notes: 'No password storage, no scraping, no automated login. ' + NO_GUARANTEE,
  }),
  offer({
    partner_offer_id: 'annualcreditreport', category: 'credit_report_free', partner_name: 'AnnualCreditReport.com',
    offer_name: 'Free official credit report', recommended_reason: 'Free official credit report (reports only; score may not be included).',
    client_trigger: 'Client wants the free official report.', target_client_stage: 'credit_report_source_needed',
    revenue_type: 'free_official', estimated_revenue: '$0 (no affiliate)', approval_required: false,
    diy_option_name: 'Self-request at annualcreditreport.com', risk_level: 'low',
  }),
  offer({
    partner_offer_id: 'bluevine', category: 'online_business_bank_account', partner_name: 'Bluevine',
    offer_name: 'Bluevine business checking (primary)', recommended_reason: 'No monthly fee, ACH/wire, invoicing, clean statements for funding readiness.',
    client_trigger: 'Client needs a business bank account.', target_client_stage: 'business_setup_in_progress',
    revenue_type: 'referral', estimated_revenue: '$ per funded account (validate)',
    diy_option_name: 'Client’s own bank/credit union', risk_level: 'medium',
    compliance_notes: 'Nexus does not open accounts or submit applications. ' + NO_GUARANTEE,
  }),
  offer({
    partner_offer_id: 'mercury', category: 'online_business_bank_account', partner_name: 'Mercury',
    offer_name: 'Mercury business banking (backup)', recommended_reason: 'Startup-friendly with clean statements.',
    client_trigger: 'Client needs a business bank account (alt).', target_client_stage: 'business_setup_in_progress',
    revenue_type: 'referral', estimated_revenue: '$ per funded account (validate)',
    diy_option_name: 'Client’s own bank/credit union', risk_level: 'medium',
    compliance_notes: 'Nexus does not open accounts or submit applications. ' + NO_GUARANTEE,
  }),
  offer({
    partner_offer_id: 'relay', category: 'online_business_bank_account', partner_name: 'Relay',
    offer_name: 'Relay business banking (backup)', recommended_reason: 'Multiple accounts, accountant-friendly.',
    client_trigger: 'Client needs a business bank account (alt).', target_client_stage: 'business_setup_in_progress',
    revenue_type: 'referral', estimated_revenue: '$ per funded account (validate)',
    diy_option_name: 'Client’s own bank/credit union', risk_level: 'medium',
    compliance_notes: 'Nexus does not open accounts or submit applications. ' + NO_GUARANTEE,
  }),
  offer({
    partner_offer_id: 'docupost', category: 'online_mailing', partner_name: 'DocuPost',
    offer_name: 'DocuPost online certified mailing (shell)', recommended_reason: 'Mail certified letters online without a Post Office trip.',
    client_trigger: 'Client has approved letters to mail.', target_client_stage: 'mailing_needed',
    revenue_type: 'affiliate', estimated_revenue: '$ per mailing (validate)',
    diy_option_name: 'USPS Certified Mail (DIY)', risk_level: 'medium',
    compliance_notes: 'Connector shell only — no API sending, no postage spend in v1. ' + NO_GUARANTEE,
  }),
  offer({
    partner_offer_id: 'business_formation', category: 'business_formation', partner_name: 'Formation partner (placeholder)',
    offer_name: 'LLC/entity formation', recommended_reason: 'Faster, guided LLC/EIN setup.',
    client_trigger: 'Client needs LLC/entity.', target_client_stage: 'business_setup_needed',
    revenue_type: 'affiliate', estimated_revenue: '$ per formation (validate)',
    diy_option_name: 'State SoS + IRS.gov (free EIN)', risk_level: 'low',
    compliance_notes: 'Nexus does not file documents automatically. ' + NO_GUARANTEE,
  }),
  offer({
    partner_offer_id: 'registered_agent', category: 'registered_agent', partner_name: 'Registered agent partner (placeholder)',
    offer_name: 'Registered agent service', recommended_reason: 'Keeps address private and compliant.',
    client_trigger: 'Client needs a registered agent.', target_client_stage: 'business_setup_needed',
    revenue_type: 'affiliate', estimated_revenue: '$ per signup (validate)',
    diy_option_name: 'Act as your own agent', risk_level: 'low',
  }),
  offer({
    partner_offer_id: 'business_address', category: 'business_address', partner_name: 'Virtual address partner (placeholder)',
    offer_name: 'Business address / virtual office', recommended_reason: 'Real commercial address improves bankability.',
    client_trigger: 'Client needs a business address.', target_client_stage: 'business_setup_needed',
    revenue_type: 'affiliate', estimated_revenue: '$ per signup (validate)',
    diy_option_name: 'Existing commercial address', risk_level: 'low',
  }),
  offer({
    partner_offer_id: 'business_phone', category: 'business_phone', partner_name: 'VoIP partner (placeholder)',
    offer_name: 'Business phone line', recommended_reason: 'Listed business phone improves bankability.',
    client_trigger: 'Client needs a business phone.', target_client_stage: 'business_setup_needed',
    revenue_type: 'affiliate', estimated_revenue: '$ per signup (validate)',
    diy_option_name: 'Any business phone line', risk_level: 'low',
  }),
  offer({
    partner_offer_id: 'website_domain_email', category: 'website_domain_email', partner_name: 'Website/domain partner (placeholder)',
    offer_name: 'Website / domain / business email', recommended_reason: 'Web presence + domain email build legitimacy.',
    client_trigger: 'Client needs a website/domain/email.', target_client_stage: 'business_setup_needed',
    revenue_type: 'affiliate', estimated_revenue: '$ per signup (validate)',
    diy_option_name: 'Self-built site + domain email', risk_level: 'low',
  }),
  offer({
    partner_offer_id: 'bookkeeping', category: 'bookkeeping_accounting', partner_name: 'Bookkeeping partner (placeholder)',
    offer_name: 'Bookkeeping / accounting', recommended_reason: 'Clean books strengthen funding readiness.',
    client_trigger: 'Client needs bookkeeping.', target_client_stage: 'business_analysis_ready',
    revenue_type: 'affiliate', estimated_revenue: '$ per signup (validate)',
    diy_option_name: 'DIY spreadsheet/accounting', risk_level: 'low',
  }),
  offer({
    partner_offer_id: 'vendor_credit', category: 'vendor_credit_accounts', partner_name: 'Vendor credit partner (placeholder)',
    offer_name: 'Vendor credit accounts', recommended_reason: 'Reporting net-30 vendors build business credit.',
    client_trigger: 'Client is building business credit.', target_client_stage: 'business_analysis_ready',
    revenue_type: 'affiliate', estimated_revenue: '$ per signup (validate)',
    diy_option_name: 'Open net-30 vendors directly', risk_level: 'low',
  }),
  offer({
    partner_offer_id: 'funding_readiness_service', category: 'funding_readiness_services', partner_name: 'Funding readiness service',
    offer_name: 'Funding readiness service offer', recommended_reason: 'Guided help matching clients to funding paths.',
    client_trigger: 'Client is approaching funding-ready.', target_client_stage: 'funding_readiness_pending',
    revenue_type: 'service_fee', estimated_revenue: 'service fee / commission (validate)',
    diy_option_name: 'Internal funding readiness checklist', risk_level: 'medium',
    compliance_notes: 'Funding applications are never automated; Ray approves the path. ' + NO_GUARANTEE,
  }),
];

export function getPartnerOffer(id: string): PartnerOffer | undefined {
  return PARTNER_OFFERS.find((o) => o.partner_offer_id === id);
}
