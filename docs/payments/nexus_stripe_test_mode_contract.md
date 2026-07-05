# Nexus Stripe Test-Mode Paywall — Contract

**Generated**: 2026-07-05

---

## Rules

- Stripe test mode only
- No real charges
- No live billing
- No secrets exposed
- No `.env` commits
- Tester/referral/admin bypass required

---

## Expected Environment Variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `STRIPE_SECRET_KEY` | YES | Stripe API key (test mode) |
| `STRIPE_WEBHOOK_SECRET` | YES | Webhook signature verification |
| `VITE_STRIPE_PUBLISHABLE_KEY` | YES | Frontend Stripe.js |
| `STRIPR_PRICE_ID_MONTHLY` | OPTIONAL | Monthly subscription price |
| `STRIPE_TEST_MODE` | YES | Must be `true` |

---

## Access Types

| Type | Description |
|------|-------------|
| `paid_client` | Active paid subscription |
| `trial_client` | Free trial period |
| `referral_tester` | Referred tester access |
| `comped_client` | Complimentary access |
| `admin_invited` | Admin invited access |
| `internal_test_client` | Internal testing |
| `inactive` | No active subscription |
| `past_due` | Payment past due |
| `canceled` | Subscription canceled |

---

## Current Status

| Check | Status |
|-------|--------|
| STRIPE_SECRET_KEY | **MISSING from .env** |
| STRIPE_WEBHOOK_SECRET | **MISSING from .env** |
| VITE_STRIPE_PUBLISHABLE_KEY | **MISSING from .env** |
| STRIPE_TEST_MODE | **MISSING from .env** |
| Classification | **STRIPE_TEST_MODE_ENV_MISSING_READY** |

---

## What Exists

- Stripe keys present in `.env.nexus.recovered.local` (not active)
- Paywall access model designed (8 types)
- Subscription value researched ($97/mo core tier)
- No live Stripe integration code

---

## Next Step

Add to `.env`:
```
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
VITE_STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_TEST_MODE=true
```
