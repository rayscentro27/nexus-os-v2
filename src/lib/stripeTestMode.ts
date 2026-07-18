/** Pure payment-boundary helpers shared by certification and review tooling. */
export type StripeRuntimeMode = 'test' | 'live';

export function isStripeSecretForMode(value: unknown, mode: StripeRuntimeMode): boolean {
  return typeof value === 'string' && value.startsWith(mode === 'live' ? 'sk_live_' : 'sk_test_');
}

export function isStripeTestSecret(value: unknown): boolean {
  return isStripeSecretForMode(value, 'test');
}

export function isStripeLiveSecret(value: unknown): boolean {
  return isStripeSecretForMode(value, 'live');
}

export function isStripeWebhookSecret(value: unknown): boolean {
  return typeof value === 'string' && value.startsWith('whsec_');
}

export const isStripeTestWebhookSecret = isStripeWebhookSecret;

export function isCheckoutSessionForMode(value: unknown, mode: StripeRuntimeMode): boolean {
  return typeof value === 'string' && value.startsWith(mode === 'live' ? 'cs_live_' : 'cs_test_');
}

export function stripeEventMatchesRuntime(livemode: unknown, mode: StripeRuntimeMode): boolean {
  return Boolean(livemode) === (mode === 'live');
}

export function parseStripeSignatureHeader(value: string): { timestamp: number; signatures: string[] } | null {
  const entries = value.split(',').map(part => part.split('=', 2)).filter(pair => pair.length === 2);
  const timestamp = Number(entries.find(([key]) => key === 't')?.[1] || 0);
  const signatures = entries.filter(([key]) => key === 'v1').map(([, signature]) => signature).filter(Boolean);
  return timestamp > 0 && signatures.length ? { timestamp, signatures } : null;
}

export async function verifyStripeTestSignature(rawBody: string, signatureHeader: string, webhookSecret: string, nowSeconds = Math.floor(Date.now() / 1000), toleranceSeconds = 300): Promise<boolean> {
  if (!isStripeWebhookSecret(webhookSecret)) return false;
  const parsed = parseStripeSignatureHeader(signatureHeader);
  if (!parsed || Math.abs(nowSeconds - parsed.timestamp) > toleranceSeconds) return false;
  const key = await crypto.subtle.importKey('raw', new TextEncoder().encode(webhookSecret), { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']);
  const digest = await crypto.subtle.sign('HMAC', key, new TextEncoder().encode(`${parsed.timestamp}.${rawBody}`));
  const expected = Array.from(new Uint8Array(digest), byte => byte.toString(16).padStart(2, '0')).join('');
  return parsed.signatures.some(candidate => candidate.length === expected.length && candidate.split('').every((char, index) => char === expected[index]));
}

export function reconcileVerifiedPaymentEvent(eventType: string, currentStatus: string): { orderStatus: string; paymentStatus: string } | null {
  if (eventType === 'checkout.session.completed' || eventType === 'payment_intent.succeeded') return { orderStatus: 'paid', paymentStatus: 'verified_paid' };
  if (eventType === 'payment_intent.payment_failed') return { orderStatus: 'payment_failed', paymentStatus: 'failed' };
  if (eventType === 'checkout.session.expired') return { orderStatus: 'expired', paymentStatus: 'expired' };
  if (eventType === 'charge.refunded' && currentStatus === 'paid') return { orderStatus: 'refunded', paymentStatus: 'refunded' };
  if (eventType === 'charge.dispute.created' && currentStatus === 'paid') return { orderStatus: 'disputed', paymentStatus: 'disputed' };
  return null;
}

export function shouldCreateFulfillment(existingCount: number): boolean {
  return existingCount === 0;
}
