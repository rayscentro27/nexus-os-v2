# Nexus Report Stale Priority Fix Report

**Date**: 2026-07-06

---

## What Was Wrong

`/report` read priorities from `reports/runtime/nexus_anytime_operator_report_latest.json` which still listed "Rotate Telegram token to restore full operator control" as priority #1, even though:
- Telegram live polling was confirmed working
- launchd job `com.nexus.telegram-operator` was loaded
- `/report` itself was being served via Telegram

## What Changed

### Dynamic Status Checking
- `cmd_report()` now checks `launchctl list` to verify Telegram job status
- Shows "ACTIVE_LIVE_POLLING" when loaded, "NOT_LOADED" otherwise

### Dynamic Priority Building
- Priorities are built from current state, not from stale JSON:
  1. Pending approvals (from `reports/approval_packets/`)
  2. Alpha research needing action (from conversation context)
  3. GoClear landing page (always relevant)
  4. Supabase browser verification (always relevant)
  5. Stripe checkout connection (always relevant)
  6. RESEND_API_KEY setup (if email lane needed)

### Alpha Status
- Shows "ACTIVE_CONVERSATIONAL" when Alpha has recent activity
- Shows topic and top recommendation
- Shows what Ray needs to do (if anything)

## Before/After

| Section | Before | After |
|---------|--------|-------|
| Telegram status | Not shown | "Telegram: ACTIVE_LIVE_POLLING" |
| Alpha status | "Alpha: active — <topic>" | "Alpha: ACTIVE_CONVERSATIONAL" + topic detail |
| Priority #1 | "Rotate Telegram token to restore full operator control" | "Review N pending approval(s)" (dynamic) |
| Priority #2 | Static from JSON | "Publish GoClear public landing page..." |
| Priority #3 | Static from JSON | "Run Supabase browser verification (2 min)" |

## Tests

- `/report` → No stale "Rotate Telegram token" ✓
- `/report` → Shows "Telegram: ACTIVE_LIVE_POLLING" ✓
- `/report` → Shows "Alpha: ACTIVE_CONVERSATIONAL" ✓
- `/report` → Dynamic priorities based on current state ✓
