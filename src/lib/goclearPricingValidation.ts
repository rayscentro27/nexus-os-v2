/**
 * Nexus OS v2 — GoClear pricing validation.
 *
 * Validates each proposed offer price against the internal market-research bands. Report-only;
 * never charges. Deterministic. No I/O.
 */
import { ALL_GOCLEAR_OFFERS, type GoClearOffer } from '../config/goclearSubscriptionOffers';
import { MARKET_PRICE_BANDS } from '../config/goclearSubscriptionTiers';

export interface PricingValidation {
  offer_id: string;
  offer_name: string;
  price: number;
  billing_cycle: string;
  within_market_band: boolean;
  reference_band: string;
  verdict: 'in_range' | 'below_range' | 'above_range' | 'one_time';
  note: string;
}

/** Map each offer to a reference market band for a sanity check. */
function referenceBand(offer: GoClearOffer): { low: number; high: number; label: string } {
  if (offer.billing_cycle === 'one_time') return { low: 97, high: 199, label: 'Business funding readiness/coaching' };
  if (offer.offer_id === 'credit_action_plan') {
    const b = MARKET_PRICE_BANDS.find((x) => x.category.startsWith('Credit repair'))!;
    return { low: b.low_monthly, high: b.high_monthly, label: b.category };
  }
  if (offer.offer_id === 'credit_plus_business_setup') {
    const b = MARKET_PRICE_BANDS.find((x) => x.category.startsWith('Business credit builder'))!;
    return { low: b.low_monthly, high: b.high_monthly, label: b.category };
  }
  const b = MARKET_PRICE_BANDS.find((x) => x.category.startsWith('Business funding'))!;
  return { low: b.low_monthly, high: b.high_monthly, label: b.category };
}

export function validateOfferPricing(offer: GoClearOffer): PricingValidation {
  const band = referenceBand(offer);
  if (offer.billing_cycle === 'one_time') {
    return {
      offer_id: offer.offer_id, offer_name: offer.offer_name, price: offer.price, billing_cycle: 'one_time',
      within_market_band: true, reference_band: `${band.label} ($${band.low}-$${band.high})`,
      verdict: 'one_time', note: '$97 readiness review is a common front-end price point; validate against local market.',
    };
  }
  const inRange = offer.price >= band.low && offer.price <= band.high;
  const verdict = inRange ? 'in_range' : offer.price < band.low ? 'below_range' : 'above_range';
  return {
    offer_id: offer.offer_id, offer_name: offer.offer_name, price: offer.price, billing_cycle: 'monthly',
    within_market_band: inRange, reference_band: `${band.label} ($${band.low}-$${band.high})`,
    verdict,
    note: inRange ? 'Price sits within the market band.' : verdict === 'below_range' ? 'Below band — room to raise after validation.' : 'Above band — confirm value justifies premium.',
  };
}

export function validateAllOfferPricing(): PricingValidation[] {
  return ALL_GOCLEAR_OFFERS.map(validateOfferPricing);
}

export function pricingValidationSummary() {
  const v = validateAllOfferPricing();
  return {
    offers: v.length,
    in_range: v.filter((x) => x.verdict === 'in_range' || x.verdict === 'one_time').length,
    out_of_range: v.filter((x) => x.verdict === 'below_range' || x.verdict === 'above_range').length,
  };
}
