# Controlled $1 Pilot

## Overview

The controlled $1 pilot is a future, hidden, invite-only real payment offer. It tests the complete payment lifecycle with a $1 charge.

## Current Status

**FOUNDATION ONLY — NOT ACTIVE**

- Offer exists in catalog (`real-payment-pilot-1`)
- `active = false`
- `publicly_visible = false`
- `controlled_live_pilot_enabled = false`
- No real payment processed
- No live Stripe keys configured

## Activation Requirements

1. Admin enables `controlled_live_pilot` in payment controls
2. Live Stripe keys configured server-side
3. Allowlist populated with approved tester emails
4. Pilot disclosure version finalized
5. Refund process certified
6. Emergency disable tested
7. Explicit Ray approval recorded

## Safety Guards

- Public visibility disabled
- Allowlist required
- One-purchase limit enforced
- Emergency disable available
- Maximum total pilot orders (10)
- Pilot start/end dates
- Admin-only activation

## Offer Details

| Field | Value |
|-------|-------|
| Price | $1.00 |
| Max Orders Per Client | 1 |
| Max Orders Per Invitation | 1 |
| Refund Supported | true |
| Payment Mode | controlled_live_pilot |

## Refund Process

1. Admin initiates refund
2. Provider payment ID required
3. Reason required
4. One full refund maximum
5. Provider confirms refund
6. Order status updated to "refunded"
7. Audit log entry created
