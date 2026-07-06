# Alpha Conversation Quality Patch Report

**Date**: 2026-07-06

---

## What Was Wrong

1. **"alpha good morning" created research brief** — The word "alpha" alone triggered `cmd_alpha_fallback()` which classified "good morning" as a topic and generated 5 scored ideas
2. **"alpha how did you sleep" created research brief** — Same issue; casual chat was treated as research
3. **Ranking inconsistency** — `cmd_alpha_fallback()` stored recommendations in unsorted order but displayed them sorted by score. "which one should we do first?" used the unsorted list, picking the wrong item

## What Changed

### Intent Classification
- Added `classify_message_intent()` that distinguishes GREETING, CASUAL_AGENT_CHAT, and ALPHA_RESEARCH_REQUEST
- "alpha good morning" → GREETING (agent=alpha) → `handle_greeting("alpha")`
- "alpha how did you sleep" → CASUAL_AGENT_CHAT (agent=alpha) → `handle_casual_chat("alpha")`
- "Alpha research 5 low-cost ways..." → ALPHA_RESEARCH_REQUEST → `cmd_alpha_fallback()`

### Ranking Consistency
- `cmd_alpha_fallback()` now stores `ranked` (sorted by score) in `last_alpha_recommendations`
- `cmd_followup("which_one_first")` uses `recs[0]` which is now the true top item
- `cmd_followup("turn_into_work_order")` uses `recs[idx]` which matches the visible list

## Before/After

| Message | Before | After |
|---------|--------|-------|
| alpha good morning | Alpha brief for "good morning" (5 ideas scored) | "Alpha is online. What should I look into?" |
| alpha how did you sleep | Alpha brief for "how did you sleep" | "Alpha does not sleep, but I'm online..." |
| which one should we do first? | Picks unsorted[0] (wrong item) | Picks sorted[0] (correct top item) |
| turn number 2 | Creates work order for unsorted[1] (wrong) | Creates work order for sorted[1] (matches visible list) |

## Tests

- "alpha good morning" → No brief created ✓
- "alpha how did you sleep" → No brief created ✓
- "Alpha research 5 low-cost ways..." → Brief created ✓
- "what did Alpha find?" → 5 sorted recommendations ✓
- "which one should we do first?" → Top item (score 6.0) ✓
- "turn number 2" → Second item ("Offer free 15-min readiness calls") ✓
