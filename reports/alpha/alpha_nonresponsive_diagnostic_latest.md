# Alpha Nonresponsive Diagnostic

**Date**: 2026-07-06

---

## Root Cause

Plain-language messages (e.g., "Alpha research ...") were not routed to Alpha. The `process_command()` function only handled slash commands (`/alpha`, `/status`, etc.) and fell through to `cmd_start()` for anything else.

## What Was Found

1. **No natural language intent detection** — `process_command()` had no logic for non-slash messages
2. **No conversation context** — `data/runtime/telegram_conversation_context.json` did not exist
3. **No Alpha brief/score creation** — `cmd_alpha()` only created a work order, no brief or scoring
4. **No follow-up memory** — "which one should we do first?" had no context to reference
5. **`/research` excluded Alpha** — Only showed NotebookLM stats
6. **`/report` excluded Alpha** — No Alpha section

## Files Changed

| File | Change |
|------|--------|
| `scripts/telegram/nexus_telegram_bridge.py` | Added Alpha intent detection, fallback handler, follow-up handler, context, debug receipts, updated /research and /report |

## Test Results

| Test | Before | After |
|------|--------|-------|
| `/alpha test` | PASS (work order only) | PASS (work order) |
| `Alpha research ...` | FAIL (help menu) | PASS (brief + score + 5 ideas) |
| `what did Alpha find?` | FAIL (help menu) | PASS (shows 5 recs) |
| `which one should we do first?` | FAIL (help menu) | PASS (shows top rec) |
| `turn number 2 into a work order` | FAIL (help menu) | PASS (creates WO) |
| `send that to Hermes` | FAIL (help menu) | PASS (routes to Hermes) |
| `/research` | PASS (no Alpha) | PASS (includes Alpha) |
| `/report` | PASS (no Alpha) | PASS (includes Alpha) |
| `/status` | PASS | PASS (unchanged) |
| `/hermes` | PASS | PASS (unchanged) |
| `/approve` | PASS | PASS (unchanged) |

## Remaining Blockers

None. Alpha is fully responsive via Telegram.
