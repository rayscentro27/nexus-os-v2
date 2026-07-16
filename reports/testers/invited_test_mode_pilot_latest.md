# Invited Test-Mode Pilot — Latest Report

**Generated:** 2026-07-15
**Phase:** 7 — Invited Stripe Test-Mode Pilot

## Overview

Invited human testers may use Stripe test mode to verify the payment and onboarding flow after accepting a validated invitation.

## Flow

1. Admin creates invitation → generates unique token
2. Invitation email sent via Resend
3. Tester clicks acceptance link → validates token
4. Tester creates password → Auth user created
5. Tester signs in → sees assigned checklist
6. Tester initiates test checkout → `create-invited-checkout` edge function
7. Stripe test checkout session created
8. Webhook processes test payment
9. Order and fulfillment created
10. Tester completes checklist and submits feedback

## Required Checks (Server-Side)

- Valid accepted invitation
- Email matches authenticated user
- Invitation not expired/revoked/completed
- No prior completed test purchase for that invitation
- Stripe test mode only (`sk_test_` prefix)
- Server-side price authoritative
- Emergency disable check
- Pilot controls check

## Test Offer

- **Slug:** `invited-readiness-test`
- **Amount:** $1.00 (test mode)
- **Active:** false (must be enabled via admin)
- **Publicly visible:** false

## Test Cards

Use Stripe test card numbers:
- `4242 4242 4242 4242` — Success
- `4000 0000 0000 0002` — Declined
- `4000 0025 0000 3155` — Requires authentication

## One-Order Enforcement

- One active order per invitation
- Duplicate checkout blocked
- Paid orders cannot be re-purchased

## Current Status

- **Test mode checkout:** Ready for invited testers
- **Webhook verification:** Signed, HMAC-SHA256
- **Fulfillment:** Created on successful payment
- **Feedback:** Linked to invitation and order

## Security

- No real money charged
- No live Stripe keys used
- No card data stored
- No public checkout route for test offer
- Invitation token required for checkout
