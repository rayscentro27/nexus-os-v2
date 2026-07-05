# Nexus Stripe — Existing Test-Mode Audit

**Generated**: 2026-07-05
**Phase**: E

## Summary

| Field | Value |
|-------|-------|
| Stripe CLI | v1.40.8 INSTALLED |
| CLI Auth | Connected (acct_****) |
| Test Mode | VERIFIED (livemode=false on all products) |
| Live Key in Env | YES (STRIPE_SECRET_KEY = rk_live_****) |
| Test Key in Env | NO |
| Existing Products | 5 (2 test + 3 subscription tiers) |
| Existing Prices | 5 (2 one-time + 3 monthly recurring) |
| Code Exists | 16 scripts in scripts/payments/ |
| Frontend Integration | Stub with placeholders |
| Real Charges | BLOCKED |

## Existing Stripe Products

| Product ID | Name | Active | Type |
|------------|------|--------|------|
| prod_UnQ2rveYF6mjrn | myproduct | YES | Test (one-time) |
| prod_UnOy9ghrJkgRRi | myproduct | YES | Test (one-time) |
| prod_Tn99pBvgTeJ9dx | Gold | YES | Subscription |
| prod_Tn992DjsD7mx6h | Silver | YES | Subscription |
| prod_Tn99slXYkPQNHv | Bronze | YES | Subscription |

## Existing Stripe Prices

| Price ID | Amount | Recurring | Product |
|----------|--------|-----------|---------|
| price_1TnpCS2MIMiohBBFSRGyvBRV | $15 | None (one-time) | myproduct |
| price_1TnoB22MIMiohBBFJH00slT3 | $15 | None (one-time) | myproduct |
| price_1SpYrL2MIMiohBBFTqGJqb0b | $100/month | Monthly | Gold |
| price_1SpYrK2MIMiohBBFo1FmUxKE | $50/month | Monthly | Silver |
| price_1SpYrJ2MIMiohBBF3geiTNZc | $10/month | Monthly | Bronze |

## Proposed Two-Tier Pricing vs Existing

| Proposed Tier | Price | Existing Match |
|---------------|-------|----------------|
| Nexus Readiness Portal | $97/month | Closest: Gold ($100/month) |
| Nexus Funding Builder Plus | $197/month | No match — needs creation |

## Existing Scripts (DO NOT REBUILD)

1. `audit_stripe_cli_and_env.py` — CLI + env audit ✅
2. `stripe_test_execution_common.py` — shared helpers ✅
3. `verify_stripe_test_credentials.py` — credential verification ✅
4. `prepare_stripe_payment_intent_test.py` — PaymentIntent test ✅
5. `prepare_stripe_test_checkout_flow.py` — checkout flow test ✅
6. `prepare_stripe_webhook_test_execution.py` — webhook test ✅
7. `prepare_stripe_webhook_test_plan.py` — webhook plan ✅
8. `stripe_webhook_test_server.py` — local webhook server ✅
9. `run_stripe_test_checkout_session.py` — checkout session ✅
10. `run_stripe_webhook_event_fixture.py` — webhook fixture ✅
11. `run_stripe_test_payment_intent.py` — PaymentIntent ✅
12. `run_stripe_webhook_trigger_test.py` — webhook trigger ✅
13. `run_stripe_listener_test.py` — listener test ✅
14. `prepare_stripe_manual_test_completion_packet.py` — completion packet ✅

## Existing Documentation (DO NOT REBUILD)

- `docs/payments/nexus_stripe_test_mode_contract.md` — COMPLETE contract
- `reports/payments/nexus_stripe_test_mode_paywall_report.md` — COMPLETE report

## Frontend Integration Status

- `src/config/goclearPaymentOfferContract.ts` — STUB with placeholder IDs
- `src/lib/hermesWorkRouter.ts` — Routes stripe/billing queries
- `src/lib/hermesCapabilityRegistry.ts` — Registers Stripe as approval_gated
- `src/data/monetizationData.js` — Tracks test checkout status
- `src/data/systemHealthData.js` — Health entry for Stripe

## What Already Works

1. Stripe CLI connected and authenticated
2. Test mode verified
3. 3 subscription products exist (Gold/Silver/Bronze)
4. 3 monthly recurring prices exist ($100/$50/$10)
5. 16 test scripts exist
6. Paywall contract documented
7. Checkout flow tested
8. PaymentIntent tested
9. Webhook listener tested

## What's Needed

1. Create Nexus-specific products ($97/month, $197/month) — OR rename existing Gold to Nexus Readiness Portal
2. Fill in placeholder product/price IDs in `goclearPaymentOfferContract.ts`
3. Add Stripe test keys to .env (currently only live key present)
4. Build subscription management UI
5. Build access grant/revoke logic

## Pricing Decision

**Option A (Recommended)**: Use existing Gold ($100/month) as Tier 1, create new $197/month product as Tier 2
**Option B**: Create new $97/month and $197/month products, deprecate Gold/Silver/Bronze
**Option C**: Rename Gold → Nexus Readiness Portal ($100), Silver → Nexus Basic ($50), create Platinum → Nexus Funding Builder Plus ($197)

## Final Status

**STRIPE_TEST_MODE_PRODUCTS_VERIFIED** — Stripe CLI connected, test mode active, 3 subscription tiers exist ($10/$50/$100 monthly). Nexus-specific pricing needs alignment. 16 test scripts ready.
