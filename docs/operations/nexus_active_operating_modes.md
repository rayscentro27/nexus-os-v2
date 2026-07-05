# Nexus Active Operating Modes

**Generated**: 2026-07-05

---

## Mode Definitions

### 1. OBSERVE
- **Behavior**: Reads status only. No action.
- **Examples**: Read process registry, read health checks, read reports
- **Receipt**: Optional (read receipt)
- **Risk**: NONE

### 2. DRY_RUN
- **Behavior**: Simulates action. Writes report/receipt only.
- **Examples**: Score a decision packet, classify intent, draft creative
- **Receipt**: Required
- **Risk**: NONE

### 3. SANDBOX_TEST
- **Behavior**: Tests in isolated test mode only.
- **Examples**: Test Supabase connectivity, test Hermes routing, test Alpha scoring
- **Receipt**: Required
- **Risk**: LOW

### 4. ACTIVE_INTERNAL
- **Behavior**: Real internal operation is allowed.
- **Allowed actions**:
  - monitor
  - audit
  - score
  - draft
  - route
  - create local work orders
  - write receipts
  - update safe internal queues
  - produce reports
  - run recovery checks
- **Receipt**: Required
- **Risk**: LOW

### 5. TELEGRAM_OPERATOR
- **Behavior**: Telegram acts as Ray's mobile command center.
- **Allowed actions**:
  - status queries
  - daily summaries
  - review queue access
  - internal requests
  - Hermes requests
  - Alpha requests
  - approve/reject/revise
  - safe internal work orders
- **Receipt**: Required for all mutations
- **Risk**: LOW-MEDIUM

### 6. APPROVAL_GATED_LIVE
- **Behavior**: A real workflow may proceed after Ray approval.
- **Conditions**:
  - Approval type is allowed
  - Runner exists
  - Guard allows it
  - Receipts are written
  - No sensitive data exposed
  - Not in blocked high-risk category
- **Receipt**: Required
- **Risk**: MEDIUM

### 7. APPROVED_LIVE
- **Behavior**: Only for explicitly allowed live workflows.
- **Conditions**:
  - Verified env
  - Guard allows
  - Approval record exists
  - Runner exists
  - Receipt path exists
- **Receipt**: Required
- **Risk**: MEDIUM-HIGH

### 8. BLOCKED
- **Behavior**: Missing env, runner, guard, or unsafe action.
- **Examples**: Customer emails, social posting, trading, charges, disputes, grants
- **Receipt**: Blocked receipt
- **Risk**: HIGH (prevented)

---

## Decision Matrix

| Action | Mode | Reason |
|--------|------|--------|
| Monitor/audit/report | ACTIVE_INTERNAL | Safe internal operation |
| Research intake | ACTIVE_INTERNAL | Safe internal operation |
| Creative draft | ACTIVE_INTERNAL | Safe internal operation |
| Ray Review queue | ACTIVE_INTERNAL | Safe internal operation |
| Approve via Telegram | TELEGRAM_OPERATOR + APPROVAL_GATED_LIVE | Needs approval record |
| Reject via Telegram | TELEGRAM_OPERATOR + APPROVAL_GATED_LIVE | Needs approval record |
| Revise via Telegram | TELEGRAM_OPERATOR + APPROVAL_GATED_LIVE | Needs approval record |
| Social posting | BLOCKED | Needs approved publish runner |
| Customer email | BLOCKED | Needs approved email runner |
| Trading | BLOCKED | No approved trading runner |
| Stripe charge | BLOCKED except test mode | Test mode only |
| Credit disputes | BLOCKED | Needs compliance runner |
| Grant applications | BLOCKED | Needs compliance runner |
| Internal work order | ACTIVE_INTERNAL | Safe internal operation |
| Hermes routing | ACTIVE_INTERNAL | Safe local classification |
| Alpha scoring | ACTIVE_INTERNAL | Safe local computation |
| Daily monitor | ACTIVE_INTERNAL | Safe internal operation |
| Recovery check | ACTIVE_INTERNAL | Safe internal operation |
| Process registry validation | ACTIVE_INTERNAL | Safe internal operation |
