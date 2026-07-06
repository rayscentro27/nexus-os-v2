# Nexus Approval-Gated Model — Away Mode Check

**Generated**: 2026-07-05
**Phase**: I

## Status: APPROVAL_GATED_LIVE_READY

## Model Verification

| Action | Status | Classification |
|--------|--------|---------------|
| Customer emails | APPROVAL_GATED_LIVE_READY | Draft → approve → send → receipt |
| Social publishing | APPROVAL_GATED_LIVE_READY | Create → approve → publish → receipt |
| Stripe live billing | APPROVAL_GATED_LIVE_PENDING_ENV | Test → verify → approve → charge |
| Credit disputes | APPROVAL_GATED_LIVE_PENDING_RUNNER | Prepare → compliance → approve → submit |
| Grant/funding submissions | APPROVAL_GATED_LIVE_PENDING_RUNNER | Prepare → verify → approve → submit |
| Trading | APPROVAL_GATED_LIVE_PENDING_GUARD | Paper → proof → risk → approve → live |
| Data export | APPROVAL_GATED_LIVE_PENDING_GUARD | Request → privacy → approve → export |
| SMS | APPROVAL_GATED_LIVE_PENDING_ENV | Draft → approve → send → receipt |
| Phone calls | APPROVAL_GATED_LIVE_PENDING_ENV | Script → approve → call → receipt |
| Legal documents | APPROVAL_GATED_LIVE_PENDING_RUNNER | Prepare → review → approve → submit |
| Modify production DB | BLOCKED_AUTONOMOUS_EXECUTION | Requires direct Ray intervention |
| Restart production | BLOCKED_AUTONOMOUS_EXECUTION | Requires direct Ray intervention |

## What's NOT Permanently Blocked

None of these are permanently blocked. They are approval-gated:
- Customer emails: draft ready, need Ray approval
- Social posting: content ready, need Ray approval
- Stripe charges: test mode active, live needs approval
- Credit disputes: packet ready, need compliance + Ray approval
- Grant submissions: packet ready, need Ray + client approval
- Trading: paper only by default, live needs risk guard + Ray approval

## What Nexus Does While Ray Is Away

- Monitors, researches, scores, drafts, prepares, routes
- Creates work orders and approval packets
- Writes receipts and reports
- Runs recovery checks
- All approval-gated workflows wait for Ray's return

## What Nexus Does NOT Do Without Approval

- Send customer emails
- Post to social media
- Charge real customers
- Submit credit disputes
- Submit grant applications
- Place live trades
- Export sensitive client data
- Modify production database
- Restart production services
