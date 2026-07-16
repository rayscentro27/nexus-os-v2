# Pilot Refund Process

## Overview

The refund foundation supports controlled refunds for pilot orders. In this sprint, only test-mode refunds are certified.

## Requirements

- Admin-only initiation
- Order must be paid
- Provider payment ID required
- One full refund maximum
- Reason required
- Audit log required
- Provider response sanitized
- Order status updates only after provider confirmation

## Process

1. Admin identifies order to refund
2. Verifies order status is "paid"
3. Initiates refund with reason
4. System calls Stripe refund API (test mode)
5. Provider confirms refund
6. Order status updated to "refunded"
7. `refunded_at` timestamp recorded
8. Audit log entry created in `invitation_events`

## Constraints

- **One full refund maximum** per order (unless partial refunds intentionally supported)
- **Admin-only** — no client/tester self-service
- **Test mode only** in this sprint
- **Real live refund** must not execute until activated

## Refund Fields

| Field | Description |
|-------|-------------|
| `order_id` | Order to refund |
| `provider_payment_intent_id` | Stripe payment intent |
| `reason` | Required reason for refund |
| `admin_id` | Admin initiating refund |
| `provider_response` | Sanitized Stripe response |
| `status` | pending → confirmed → failed |

## Audit Logging

Every refund creates an entry in `invitation_events`:
- `event_type: "refund_processed"`
- `metadata: { order_id, reason, amount_cents }`
- `actor_admin_id`: Admin who initiated

## Safety

- No automatic refunds from client UI
- No webhook-triggered refunds
- Provider confirmation required before status update
- Fulfillment state reviewed before refund
- Delivered packet remains historically linked
