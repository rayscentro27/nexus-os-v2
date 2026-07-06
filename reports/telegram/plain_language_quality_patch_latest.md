# Plain-Language Quality Patch Report

**Date**: 2026-07-06
**Commit**: da7c6bb → patched

---

## What Was Wrong

1. **Greeting showed command menu** — "good morning" fell through to `cmd_start()`, showing a wall of commands
2. **"alpha good morning" created research brief** — any message with "alpha" triggered research routing
3. **"alpha how did you sleep" created research brief** — casual chat was misclassified as research
4. **Hermes only created work orders** — `/hermes what is today's priority?` returned a routing receipt instead of an answer
5. **/report showed stale "Rotate Telegram token"** — even though Telegram live polling was confirmed working
6. **Alpha ranking inconsistency** — displayed recommendations were sorted by score, but stored list was unsorted, so "which one should we do first?" picked the wrong item

## What Changed

### New Intent Classifier
- Added `classify_message_intent()` with 9 categories: GREETING, CASUAL_AGENT_CHAT, ALPHA_RESEARCH_REQUEST, ALPHA_CONTEXT_FOLLOWUP, HERMES_ADVISORY, NEXUS_STATUS_OR_REPORT, APPROVAL_ACTION, WORK_ORDER_REQUEST, UNKNOWN_HELPFUL_FALLBACK
- Intent is determined by regex patterns, not just keyword presence
- Agent prefix ("alpha", "hermes", "nexus") is stripped before classification

### Greeting Handler
- `handle_greeting()` returns natural status summary with quick metrics
- Agent-specific greetings: "Alpha is online..." / "Hermes is online..." / "Nexus is online..."
- No work orders, no research briefs, no command menu

### Casual Chat Handler
- `handle_casual_chat()` returns conversational replies
- "Alpha does not sleep, but I'm online and ready..."
- No research briefs, no scoring, no work orders

### Hermes Direct Advisory
- `hermes_direct_answer()` reads current state and generates contextual advice
- Handles: priorities, recommendations, risk assessment, approvals, status
- Creates work order in background (non-blocking), but answer comes first

### Alpha Ranking Fix
- `cmd_alpha_fallback()` now stores sorted (ranked) recommendations, not unsorted ideas
- "which one should we do first?" and "turn number N" now match the visible list

### /report Dynamic Priorities
- Checks `launchctl list` for Telegram status dynamically
- Shows "ACTIVE_LIVE_POLLING" when loaded, not stale "Rotate token"
- Builds priorities from current state (approvals, Alpha, landing page, Supabase, Stripe)

## Examples Before/After

| Message | Before | After |
|---------|--------|-------|
| good morning | Command menu (17 commands) | Natural greeting with status |
| alpha good morning | Alpha brief for "good morning" | "Alpha is online. What should I look into?" |
| alpha how did you sleep | Alpha brief for "how did you sleep" | "Alpha does not sleep, but I'm online..." |
| /hermes what is today's priority? | "Hermes Request / Routed to: hermes_general / Work Order: wo_xxx" | Direct advisory with 5 priorities |
| what did Alpha find? | "Unknown follow-up" | Lists 5 recommendations sorted by score |
| which one should we do first? | Wrong item (unsorted list) | Correct top item (sorted by score) |
| /report | "Rotate Telegram token" as priority #1 | "Telegram: ACTIVE_LIVE_POLLING" + dynamic priorities |

## Tests Run

All 11 quality tests pass:
1. good morning → greeting with status
2. alpha good morning → Alpha greeting, no brief
3. alpha how did you sleep → casual Alpha reply, no brief
4. are you there → natural Nexus reply
5. /hermes what is today's priority? → direct advisory
6. Hermes what should we do next? → direct advisory
7. Alpha research → creates brief (correct)
8. what did Alpha find? → sorted summary
9. which one should we do first? → picks top item
10. turn number 2 → creates work order matching visible list
11. /report → no stale Telegram token blocker

## Remaining Blockers

None for plain-language quality. All success criteria met.

## Exact Telegram Phrases Ray Should Test

1. `good morning`
2. `alpha good morning`
3. `alpha how did you sleep`
4. `are you there`
5. `/hermes what is today's priority?`
6. `Hermes what should we do next?`
7. `Alpha research 5 low-cost ways GoClear can get paid readiness review clients this week`
8. `what did Alpha find?`
9. `which one should we do first?`
10. `turn number 2 into a work order`
11. `/report`
