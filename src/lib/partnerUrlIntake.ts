/**
 * Nexus OS v2 — Partner URL Intake.
 *
 * Safely intakes approved partner URLs (affiliate/referral/application), validates them, verifies a
 * disclosure + DIY option are present, and computes the resulting partner offer configuration status.
 *
 * This NEVER navigates to, activates, or fetches a URL — it only validates the string and records it
 * for later Ray-approved placement. Deterministic. No I/O. Fails closed on unsafe input.
 */
import { getPartnerOffer, type PartnerOffer } from '../config/partnerOffers';
import { checkPartnerConfig, type PartnerConfigCheck } from './partnerOfferStatus';

export interface PartnerUrlIntake {
  partner_offer_id: string;
  affiliate_url?: string | null;
  referral_url?: string | null;
  application_url?: string | null;
  disclosure_text?: string | null;
  diy_option_name?: string | null;
  submitted_by?: string;
  submitted_at?: string;
}

export interface UrlValidation {
  field: string;
  value: string;
  valid: boolean;
  reason: string;
}

const ALLOWED_PROTOCOLS = new Set(['https:']);
const UNSAFE_PATTERN = /(javascript:|data:|vbscript:|\s|<|>|")/i;

/** Validate a single URL string. HTTPS-only, no unsafe schemes/characters, must have a host. */
export function validateUrl(field: string, value: string): UrlValidation {
  const v = (value ?? '').trim();
  if (!v) return { field, value: v, valid: false, reason: 'empty' };
  if (UNSAFE_PATTERN.test(v)) return { field, value: v, valid: false, reason: 'unsafe characters or scheme' };
  let url: URL;
  try {
    url = new URL(v);
  } catch {
    return { field, value: v, valid: false, reason: 'not a valid URL' };
  }
  if (!ALLOWED_PROTOCOLS.has(url.protocol)) return { field, value: v, valid: false, reason: 'must be https' };
  if (!url.hostname || !url.hostname.includes('.')) return { field, value: v, valid: false, reason: 'missing/invalid host' };
  if (/placeholder\.invalid$/i.test(url.hostname)) return { field, value: v, valid: false, reason: 'placeholder host — not a real URL yet' };
  return { field, value: v, valid: true, reason: 'ok' };
}

export interface IntakeResult {
  partner_offer_id: string;
  partner_name: string;
  accepted: boolean;
  validations: UrlValidation[];
  has_disclosure: boolean;
  has_diy_option: boolean;
  resulting_config_status: 'configured' | 'needs_config';
  errors: string[];
  next_action: string;
}

/**
 * Validate an intake against its partner offer. Returns a DERIVED result (never mutates the source
 * registry). `accepted` is true only when at least one valid URL, a disclosure, and a DIY option
 * exist. Real persistence/placement happens later behind Ray approval.
 */
export function intakePartnerUrls(intake: PartnerUrlIntake): IntakeResult {
  const offer = getPartnerOffer(intake.partner_offer_id);
  const errors: string[] = [];
  if (!offer) {
    return {
      partner_offer_id: intake.partner_offer_id,
      partner_name: 'unknown',
      accepted: false,
      validations: [],
      has_disclosure: false,
      has_diy_option: false,
      resulting_config_status: 'needs_config',
      errors: [`unknown partner_offer_id: ${intake.partner_offer_id}`],
      next_action: 'Use a valid partner_offer_id from the registry.',
    };
  }

  const validations: UrlValidation[] = [];
  for (const [field, val] of [
    ['affiliate_url', intake.affiliate_url],
    ['referral_url', intake.referral_url],
    ['application_url', intake.application_url],
  ] as const) {
    if (val != null && val !== '') validations.push(validateUrl(field, val));
  }
  const anyValidUrl = validations.some((v) => v.valid);
  if (validations.length === 0) errors.push('no URL provided');
  else if (!anyValidUrl) errors.push('no valid URL among the provided fields');

  const has_disclosure = Boolean((intake.disclosure_text ?? offer.disclosure_text)?.trim());
  const has_diy_option = Boolean((intake.diy_option_name ?? offer.diy_option_name)?.trim());
  if (!has_disclosure) errors.push('missing affiliate disclosure text');
  if (!has_diy_option) errors.push('missing DIY/free option');

  const accepted = anyValidUrl && has_disclosure && has_diy_option;
  return {
    partner_offer_id: offer.partner_offer_id,
    partner_name: offer.partner_name,
    accepted,
    validations,
    has_disclosure,
    has_diy_option,
    resulting_config_status: accepted ? 'configured' : 'needs_config',
    errors,
    next_action: accepted
      ? 'URLs valid — request Ray approval to place this offer.'
      : `Fix: ${errors.join('; ')}.`,
  };
}

/**
 * Re-derive a partner's config check after applying an intake (immutably). Used by reports to show
 * what config status WOULD be once approved URLs are intaken.
 */
export function projectedConfig(offer: PartnerOffer, intake?: PartnerUrlIntake): PartnerConfigCheck {
  if (!intake) return checkPartnerConfig(offer);
  const merged: PartnerOffer = {
    ...offer,
    affiliate_url: intake.affiliate_url ?? offer.affiliate_url,
    referral_url: intake.referral_url ?? offer.referral_url,
    application_url: intake.application_url ?? offer.application_url,
    disclosure_text: intake.disclosure_text ?? offer.disclosure_text,
    diy_option_name: intake.diy_option_name ?? offer.diy_option_name,
  };
  return checkPartnerConfig(merged);
}
