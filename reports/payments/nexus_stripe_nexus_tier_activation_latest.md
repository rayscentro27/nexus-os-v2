# Nexus Stripe — Nexus Tier Activation

**Generated**: 2026-07-05
**Phase**: H

## Status: STRIPE_TIER_1_VERIFIED_TIER_2_CREATED

## Tier Mapping

| Tier | Product ID | Price ID | Amount | Interval | Status |
|------|------------|----------|--------|----------|--------|
| Nexus Readiness Portal | prod_Tn99pBvgTeJ9dx (renamed from Gold) | price_1SpYrL2MIMiohBBFTqGJqb0b | $100/month | Monthly | VERIFIED |
| Nexus Funding Builder Plus | prod_UpeRRU4DGE1AvS (NEW) | price_1Tpz922MIMiohBBFuzM642Hu | $197/month | Monthly | CREATED |

## What Was Done

1. Renamed existing Gold product → "Nexus Readiness Portal"
2. Created new product "Nexus Funding Builder Plus" at $197/month
3. Both products in test mode (livemode=false)
4. No live charges created
5. No secrets exposed

## Compliance Positioning

- Education, readiness, organization, advisory review
- Business bankability workflow
- No guaranteed credit repair
- No promised funding approval
- Test mode only

## Frontend Integration

- `src/config/goclearPaymentOfferContract.ts` — needs product/price ID update
- Tier 1 placeholder: `prod_Tn99pBvgTeJ9dx` / `price_1SpYrL2MIMiohBBFTqGJqb0b`
- Tier 2 placeholder: `prod_UpeRRU4DGE1AvS` / `price_1Tpz922MIMiohBBFuzM642Hu`

## All Existing Products (Test Mode)

| Product | Price | Interval |
|---------|-------|----------|
| Nexus Readiness Portal | $100/month | Monthly |
| Nexus Funding Builder Plus | $197/month | Monthly |
| Silver | $50/month | Monthly |
| Bronze | $10/month | Monthly |
| myproduct (test) | $15 | One-time |
| myproduct (test) | $15 | One-time |
