# Hidden $1 Pilot Foundation — Latest Report

**Generated:** 2026-07-15
**Phase:** 7 — Hidden $1 Controlled-Live Pilot Foundation

## Overview

Foundation created for a future hidden, invite-only $1 real payment pilot. This offer exists in the catalog but is **not active** and **not publicly visible**. Real payment is **disabled**.

## Pilot Offer: `real-payment-pilot-1`

| Field | Value |
|-------|-------|
| Price | $1.00 (100 cents) |
| Publicly Visible | false |
| Requires Invitation | true |
| Requires Allowlist | true |
| Max Orders Per Client | 1 |
| Max Orders Per Invitation | 1 |
| Active | false |
| Live Activation Status | disabled |
| Payment Mode Required | controlled_live_pilot |
| Refund Supported | true |
| Maximum Total Pilot Orders | 10 |

## Safety Guards

1. **Public visibility disabled** — Offer not shown on pricing page
2. **Controlled live pilot disabled** — Payment mode guard blocks live charges
3. **Allowlist required** — Only allowlisted emails can purchase
4. **One-purchase limit** — Enforced server-side
5. **Emergency disable** — Admin can block all checkouts instantly
6. **Ray approval required** — Separate activation sprint needed
7. **No live keys used** — Test mode enforced in this sprint

## Activation Requirements (Future Sprint)

- [ ] Admin enables `controlled_live_pilot` in payment controls
- [ ] Live Stripe keys configured server-side
- [ ] Allowlist populated with approved tester emails
- [ ] Pilot disclosure version finalized
- [ ] Refund process certified
- [ ] Emergency disable tested
- [ ] Explicit Ray approval recorded
- [ ] Audit log entry created

## Pilot Disclosure

> "This is a limited paid product-testing program. It is not the full $97 Credit & Funding Readiness Review. The $1 charge is used to test the real payment, onboarding, portal, review, delivery, and refund experience. Testing participation and feedback are part of this pilot. No funding, credit, deletion, approval, timeline, or outcome is guaranteed."

## Refund Foundation

- Admin-only refund capability
- Provider payment ID required
- One full refund maximum
- Reason required
- Audit logged
- Order status updated after provider confirmation

## Emergency Disable

- Server-enforced checkout block
- No new checkout sessions when enabled
- Existing orders remain readable
- Admin UI toggle available
- No client/tester access to toggle

## What Is NOT Done (Future)

- Real $1 charge is NOT executed
- Live Stripe mode is NOT enabled
- Public $97/$297/$497 live checkout is NOT enabled
- No public users are invited
- No automatic email without admin approval
- No DocuPost submission

## Decision

**READY FOR SEPARATE ACTIVATION SPRINT** — Foundation complete, all safety guards in place, real payment disabled.
