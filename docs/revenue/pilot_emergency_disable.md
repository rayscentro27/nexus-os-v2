# Pilot Emergency Disable

## Overview

The emergency disable feature allows administrators to instantly block all new checkout sessions across the system.

## When to Use

- Suspected unauthorized payment activity
- Security incident
- Unexpected behavior in live payment mode
- Need to pause all purchasing immediately

## How It Works

1. Admin navigates to `/admin#tester-invitations`
2. Scrolls to "Payment Controls" section
3. Clicks "Emergency Disable Checkout"
4. Confirms the action
5. `emergency_checkout_disabled` set to `true` in `payment_pilot_controls`
6. All checkout edge functions check this flag
7. New checkout sessions are rejected
8. Admin clicks "Re-enable Test Checkout" to restore

## Impact

| Feature | When Disabled |
|---------|---------------|
| New checkout sessions | Blocked |
| Existing orders | Remain readable |
| Verified webhooks | Still reconcile |
| Delivery history | Remains intact |
| Refunds | Still possible for admins |
| Public pages | Show "unavailable" message |

## Technical Details

- Stored in `payment_pilot_controls.emergency_checkout_disabled`
- Checked in `create-stripe-checkout` and `create-invited-checkout`
- Admin-only toggle (no client/tester access)
- Audit-logged via `invitation_events`

## Rollback

To re-enable:
1. Navigate to Payment Controls
2. Click "Re-enable Test Checkout"
3. Confirm the action
4. Checkout sessions resume normally
