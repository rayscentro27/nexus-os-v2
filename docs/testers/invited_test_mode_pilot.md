# Invited Test-Mode Pilot

## Overview

The invited test-mode pilot allows real human testers to verify the Stripe payment and onboarding flow using test cards. No real money is charged.

## Prerequisites

- Valid accepted invitation with `invited_test_mode` level
- Authenticated tester account
- Stripe test mode enabled (`STRIPE_MODE=test`)

## Flow

1. Tester signs in to their account
2. Navigates to `/tester/tasks`
3. Starts testing session
4. Clicks "Test Payment" (when checklist includes payment)
5. `create-invited-checkout` edge function validates:
   - Valid invitation
   - Email matches
   - No prior completed purchase
   - Stripe test mode
   - Emergency disable not active
6. Stripe Checkout Session created with test price
7. Tester enters test card number
8. Webhook processes payment
9. Order and fulfillment created
10. Tester sees confirmation

## Test Card Numbers

| Card | Result |
|------|--------|
| `4242 4242 4242 4242` | Success |
| `4000 0000 0000 0002` | Declined |
| `4000 0025 0000 3155` | Requires 3D Secure |

## One-Order Enforcement

- One active order per invitation
- Duplicate checkout blocked server-side
- Paid orders cannot be re-purchased
- Existing open orders reused

## Security

- Invitation token required
- Auth user must match invitation
- Server-side price authoritative
- No live Stripe keys
- No card data stored
- Emergency disable blocks checkout
