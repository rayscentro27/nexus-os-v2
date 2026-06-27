/**
 * Nexus OS v2 — Partner offer status helpers.
 * Deterministic. No I/O. Reports config readiness; never activates anything.
 */
import { PARTNER_OFFERS, type PartnerOffer } from '../config/partnerOffers';

export interface PartnerConfigCheck {
  partner_offer_id: string;
  partner_name: string;
  category: string;
  configured: boolean;
  missing: string[];
  needs_config: boolean;
  next_action: string;
  approval_required: boolean;
  activation_status: PartnerOffer['activation_status'];
}

/** A partner is "configured" when it has at least one usable URL (or is a free/official option). */
export function checkPartnerConfig(offer: PartnerOffer): PartnerConfigCheck {
  const isFree = offer.revenue_type === 'free_official';
  const missing: string[] = [];
  if (!isFree) {
    const hasUrl = Boolean(offer.affiliate_url || offer.referral_url || offer.application_url);
    if (!hasUrl) missing.push('affiliate/referral/application URL');
    if (!offer.disclosure_text) missing.push('disclosure text');
  }
  const configured = missing.length === 0;
  return {
    partner_offer_id: offer.partner_offer_id,
    partner_name: offer.partner_name,
    category: offer.category,
    configured,
    missing,
    needs_config: !configured,
    next_action: configured
      ? 'Validate live terms, then request Ray approval to activate.'
      : `Add ${missing.join(' + ')} from the partner program, then re-validate.`,
    approval_required: offer.approval_required,
    activation_status: offer.activation_status,
  };
}

export function allPartnerConfigChecks(): PartnerConfigCheck[] {
  return PARTNER_OFFERS.map(checkPartnerConfig);
}

export function partnerOfferCounts() {
  const checks = allPartnerConfigChecks();
  return {
    total: checks.length,
    configured: checks.filter((c) => c.configured).length,
    needs_config: checks.filter((c) => c.needs_config).length,
    approval_required: checks.filter((c) => c.approval_required).length,
    active: PARTNER_OFFERS.filter((o) => o.activation_status === 'active').length,
    proposed: PARTNER_OFFERS.filter((o) => o.activation_status === 'proposed').length,
  };
}
