# Alpha-to-Nexus Payment and Subscription Handoff Plan

Alpha may research demand, define an offer hypothesis, draft price tests, landing copy, CTA, campaign, and Ray Review proposal. Alpha cannot create checkout sessions, confirm payment, charge/refund, create subscriptions, store customer/payment data, track referrals, or trigger onboarding.

After Ray approves the exact offer, Nexus owns: legal/compliance copy, checkout/payment provider, verified payment event, customer identity/consent, subscription state, onboarding, fulfillment, support, refund/cancellation, referral attribution, and financial reporting.

Early clients use a separately approved manual payment path. Nexus records nothing as paid unless Ray verifies it through the approved system. The manual checklist must separate “offer accepted,” “payment requested,” “payment verified,” and “delivery approved.”

Production Stripe comes later after test-mode contract/webhook/idempotency/security verification and explicit Ray approval. Subscription and referral tracking come after the one-time journey is proven, with cancellation, retry, disclosure, data retention, and reconciliation controls.

No Alpha artifact may contain a live checkout URL or activate a payment path. The bridge payload contains only offer ID/version, approved copy, proposed price, audience, evidence, experiment limits, and Ray Review receipt.
