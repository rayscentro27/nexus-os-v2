# Stripe Config Status

**Generated:** 2026-07-07

## Environment

| Key | Status | File |
|-----|--------|------|
| VITE_STRIPE_PUBLISHABLE_KEY | FOUND | .env.nexus.recovered.local |
| VITE_STRIPE_PRICE_ID | MISSING | - |
| VITE_STRIPE_PRODUCT_ID | MISSING | - |
| STRIPE_SECRET_KEY | FOUND | .env.nexus.recovered.local |
| STRIPE_WEBHOOK_SECRET | MISSING | - |

## Status

- **Frontend publishable key:** Available (in recovered env)
- **Backend secret key:** Available (in recovered env)
- **Product/Price IDs:** NOT configured
- **Webhook secret:** NOT configured
- **Checkout:** Not yet wired
- **Payment status display:** Demo only

## What's Needed Before Subscriptions

1. Create Stripe product and price in Stripe Dashboard
2. Add `VITE_STRIPE_PRODUCT_ID` to .env
3. Add `VITE_STRIPE_PRICE_ID` to .env
4. Add `STRIPE_WEBHOOK_SECRET` to .env
5. Wire checkout flow in frontend
6. Test with Stripe test mode

## Safety

- No charges created ✓
- No live checkout activated ✓
- Demo mode only ✓

## Blockers

- Missing Stripe product/price IDs
- Missing webhook secret
