# Alpha Nonresponsive Root Cause Audit

**Date**: 2026-07-06

---

## Root Causes Identified

### 1. Plain-language messages never route to Alpha (PRIMARY)
- **Failing layer**: `process_command()` in `scripts/telegram/nexus_telegram_bridge.py:591-625`
- **Evidence**: `cmd = parts[0].lower()` extracts first word; if it doesn't match a `/command`, falls through to `cmd_start()`
- **Function**: `process_command()` at line 591
- **Fix**: Add natural language intent detection before the command router fallback

### 2. No conversation context/memory
- **Failing layer**: Missing file `data/runtime/telegram_conversation_context.json`
- **Evidence**: No state persistence between messages
- **Fix**: Create context store and update it after each Alpha interaction

### 3. No Alpha brief or score creation
- **Failing layer**: `cmd_alpha()` at line 293
- **Evidence**: Only creates a work order, no brief/score/advisory
- **Fix**: Add deterministic Alpha fallback that classifies topic, produces ideas, scores them, writes brief

### 4. No follow-up capability
- **Failing layer**: No context to reference for "which one should we do first?"
- **Fix**: Read conversation context and respond based on last Alpha results

### 5. `/research` excludes Alpha
- **Failing layer**: `cmd_research()` at line 133
- **Evidence**: Only shows NotebookLM stats
- **Fix**: Add Alpha status, latest topic, brief path, recommendation

### 6. `/report` excludes Alpha
- **Failing layer**: `cmd_report()` at line 108
- **Evidence**: No Alpha section
- **Fix**: Add Alpha latest activity and recommendation

---

## Files Involved

| File | Role |
|------|------|
| `scripts/telegram/nexus_telegram_bridge.py` | Command router, Alpha handler, context |
| `data/runtime/telegram_conversation_context.json` | NEW — conversation state |
| `data/alpha/intake/` | NEW — Alpha intake records |
| `reports/alpha/briefs/` | NEW — Alpha briefs |
| `reports/alpha/scores/` | NEW — Alpha scores |
| `reports/hermes/alpha_advisory_feed_latest.md` | NEW — Hermes Alpha feed |

## Recommended Minimal Fix

1. Add `detect_alpha_intent()` before command router fallback
2. Add `cmd_alpha_fallback()` for plain-language Alpha
3. Add `load_conversation_context()` / `save_conversation_context()`
4. Add `cmd_followup()` for "which one", "turn number", "what did Alpha find"
5. Update `cmd_research()` and `cmd_report()` to include Alpha
6. Write debug receipts under `reports/telegram/receipts/alpha_debug/`
