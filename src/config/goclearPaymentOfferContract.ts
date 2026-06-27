/**
 * Nexus OS v2 — GoClear payment/billing readiness CONTRACT ONLY.
 *
 * No Stripe connection, no live payment links, no charges, no subscription activation. This defines
 * future payment offer objects + placeholders so billing can be wired later behind explicit approval.
 * Pure / deterministic. No I/O.
 */
import { ALL_GOCLEAR_OFFERS } from './goclearSubscriptionOffers';

export type PaymentActivationStatus = 'not_connected';

export interface PaymentOffer {
  offer_id: string;
  offer_name: string;
  price: number;
  billing_cycle: 'one_time' | 'monthly';
  stripe_product_id_placeholder: string;
  stripe_price_id_placeholder: string;
  payment_link_placeholder: string;
  activation_status: PaymentActivationStatus;
  approval_required: true;
}

export const PAYMENT_OFFERS: PaymentOffer[] = ALL_GOCLEAR_OFFERS.map((o) => ({
  offer_id: o.offer_id,
  offer_name: o.offer_name,
  price: o.price,
  billing_cycle: o.billing_cycle,
  stripe_product_id_placeholder: `prod_PLACEHOLDER_${o.offer_id}`,
  stripe_price_id_placeholder: `price_PLACEHOLDER_${o.offer_id}`,
  payment_link_placeholder: `https://PLACEHOLDER.invalid/pay/${o.offer_id}`,
  activation_status: 'not_connected',
  approval_required: true,
}));

export const PAYMENT_CONTRACT_META = {
  stripe_connected: false,
  live_payment_links: false,
  charges_enabled: false,
  subscriptions_active: false,
  activation_status: 'not_connected' as PaymentActivationStatus,
  note: 'Contract + placeholders only. Billing is wired later via a separate, explicitly approved step with no auto-charge.',
} as const;
