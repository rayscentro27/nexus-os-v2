# Stripe Test Checkout Lane

**Status**: STRIPE_TEST_CHECKOUT_READY

## Workflow

1. Request checkout (Nexus creates approval packet)
2. Ray Review (via Telegram /review)
3. Approve (via Telegram /approve STRIPE-XXX)
4. Create Stripe checkout session (test mode only)
5. Write receipt
6. Log access state

## Tiers

| Tier | Product | Price | Amount |
|------|---------|-------|--------|
| Tier 1 | Nexus Readiness Portal | price_1SpYrL2MIMiohBBFTqGJqb0b | $100/month |
| Tier 2 | Nexus Funding Builder Plus | price_1Tpz922MIMiohBBFuzM642Hu | $197/month |

## Commands

```bash
# Request checkout
python3 scripts/approval_lanes/nexus_stripe_test_checkout_lane.py request <tier1|tier2> [email]

# Approve and create session
python3 scripts/approval_lanes/nexus_stripe_test_checkout_lane.py approve <item_id>

# Check status
python3 scripts/approval_lanes/nexus_stripe_test_checkout_lane.py status <item_id>
```

## Safety

- Test mode only (livemode=false)
- No live charges
- No real customer billing
- RESEND_API_KEY required for live sending
