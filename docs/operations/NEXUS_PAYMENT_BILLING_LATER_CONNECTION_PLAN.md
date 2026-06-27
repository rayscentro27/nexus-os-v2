# Nexus Payment / Billing — Later Connection Plan

Billing is **contract + placeholders only** in the current work. There is no Stripe connection, no
live payment links, no charges, and no active subscriptions. Source:
`src/config/goclearPaymentOfferContract.ts`.

## Status (by design)

- `stripe_connected: false`
- `live_payment_links: false`
- `charges_enabled: false`
- `subscriptions_active: false`
- `activation_status: not_connected`

Each offer carries placeholders (`stripe_product_id_placeholder`, `stripe_price_id_placeholder`,
`payment_link_placeholder`) so billing can be wired later without changing callers.

## Preconditions before connecting billing

1. Ray approves the offers, pricing language, and disclosures (via the Ray Review launch cards).
2. Partner offers are validated/configured where revenue depends on them.
3. A dedicated, secret-stored Stripe key is provisioned (never committed, never in `.env` in git).

## Connection steps (future, separately approved)

1. Create Stripe products/prices matching the approved offers.
2. Replace placeholders with real product/price ids + payment links.
3. Flip `activation_status` to connected behind an explicit approved flag.
4. Enable charges only after a successful test-mode validation in a staging tenant.

## Hard rules (now)

- No Stripe connection, no live payment links, no charges, no subscription activation.
- Pricing figures remain internal estimates to validate, not live offers.
- Client-facing offers/copy remain approval-gated.
