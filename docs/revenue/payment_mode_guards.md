# Payment Mode Guards

## Overview

Server-controlled payment modes ensure safe separation between test and live environments.

## Modes

| Mode | Description |
|------|-------------|
| `test` | Stripe test keys, test cards, no real charges |
| `controlled_live_pilot` | Live Stripe keys, hidden $1 offer, invitation required |
| `public_live` | Public live payments, requires separate launch process |

## Default

**`test`** — All environments default to test mode.

## Guard Rules

### Test Mode
- Stripe test keys only (`sk_test_` prefix)
- Public commercial routes operate per existing settings
- Invited testers use test cards
- No real charge

### Controlled Live Pilot
- Live Stripe keys required server-side
- Hidden $1 offer only
- Valid accepted invitation required
- Allowlisted email required
- One purchase limit
- Maximum global pilot order count
- Ray activation record required
- Public $97/$297/$497 live checkout disabled

### Public Live
- Must remain disabled
- No code path may enable it automatically
- Requires separate future launch process
- Requires explicit Ray approval

## Enforcement Points

1. **Checkout Edge Function** — Rejects non-test mode, checks pilot controls
2. **Webhook Edge Function** — Verifies Stripe mode
3. **Admin UI** — Shows current mode, requires confirmation for changes
4. **Payment Controls** — Singleton row with all mode flags

## Mixed Key Rejection

- Server rejects mixed test/live key configurations
- `STRIPE_MODE` must match `STRIPE_SECRET_KEY` prefix
- Webhook secret must match mode

## Browser-Supplied Mode Rejection

- Payment mode never accepted from browser
- Server determines mode from controls table
- Client cannot override server-side checks
