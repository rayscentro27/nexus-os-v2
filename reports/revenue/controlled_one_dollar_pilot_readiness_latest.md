# Controlled $1 Pilot Readiness Decision

**Generated:** 2026-07-15
**Phase:** 7 — Hidden $1 Controlled-Live Pilot Foundation

## Decision: READY FOR SEPARATE ACTIVATION SPRINT

## Required Verification Checklist

- [x] Hidden offer exists — `real-payment-pilot-1` in catalog
- [x] Public visibility disabled — `publicly_visible: false`
- [x] Controlled live pilot disabled — `controlled_live_pilot_enabled: false`
- [x] Allowlist enforced — `payment_pilot_allowlist` table with RLS
- [x] One-purchase limit enforced — server-side check in checkout
- [x] Emergency disable works — admin toggle, server-enforced
- [x] Refund foundation works — test-mode path ready
- [x] Live/test guards pass — mode check in all checkout functions
- [x] No live key used in this sprint — `sk_test_` enforced
- [x] No real charge executed — foundation only

## Evidence

### Hidden Offer
- `real-payment-pilot-1` exists in `HIDDEN_PILOT_OFFERS`
- `active: false` — not available for checkout
- `publicly_visible: false` — not shown on pricing
- `requires_invitation: true` — invitation required
- `requires_allowlist: true` — allowlist required
- `max_orders_per_invitation: 1` — one-purchase limit

### Payment Controls
- `controlled_live_pilot_enabled: false` — disabled
- `public_live_enabled: false` — disabled
- `emergency_checkout_disabled: false` — available
- `mode: test` — test mode default

### Allowlist
- `payment_pilot_allowlist` table created
- Admin-only writes via RLS
- Email/Auth match required
- Offer restriction required
- Expiration required
- Revocation supported

### Guards
- Checkout functions check `emergency_checkout_disabled`
- Checkout functions check `test_mode_purchases_enabled`
- Checkout functions reject `public_live` mode
- Stripe key prefix validated (`sk_test_`)

### Refund Foundation
- Test-mode refund path certified
- Real live refund must not execute
- Admin-only, one refund maximum
- Audit logged

## What Requires Separate Activation Sprint

1. Setting `controlled_live_pilot_enabled = true`
2. Configuring live Stripe keys (`sk_live_`)
3. Populating allowlist with approved emails
4. Finalizing pilot disclosure version
5. Certifying refund process with real Stripe
6. Recording explicit Ray approval
7. Setting `active = true` on the offer
8. Enabling public-facing checkout path

## Recommendation

**READY FOR SEPARATE ACTIVATION SPRINT** — Foundation is complete. All safety guards are in place. Real payment is disabled. No live Stripe keys are used. A separate sprint with explicit Ray approval is required before activation.
