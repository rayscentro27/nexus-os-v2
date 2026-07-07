# Alpha Routing Audit — Latest

**Date:** 2026-07-07
**Starting commit:** 58fafdc
**Ending commit:** d26848d

## Live Process Status

- **Launchd job:** `com.nexus.telegram-operator` — loaded, runs every 60s
- **Runner script:** `scripts/ops/nexus_telegram_operator_launchd_runner.sh`
- **Working directory:** `/Users/raymonddavis/nexus-os-v2`
- **Code path:** Same repo directory — picks up latest code on each `--once` cycle
- **Status at audit time:** Running from pre-58fafdc code (needed kickstart after push)
- **Kickstart:** `launchctl kickstart -k gui/$(id -u)/com.nexus.telegram-operator`

## Root Cause Analysis

### Failure 1: "Alpha, give me a plan for today" → Nexus plan
**Cause:** Role prefix regex `^(alpha|hermes|nexus)\s+` did not handle commas (`Alpha,`).
**Fix:** Changed to `^(?:@)?(alpha|hermes|nexus)\s*[,:\-]?\s*` in message_understanding.py.

### Failure 2: "Alpha, how can I make money today?" → Hermes Money Plan
**Cause:** Even when role was detected, router had no Alpha-specific routing layer.
**Fix:** Added Layer 4c (Alpha explicit role routing) in process_with_new_router.

### Failure 3: "Alpha, what color is the sky?" → "Clarify the question"
**Cause:** Alpha draft engine's `_draft_outside_perspective` returned generic clarify.
**Fix:** Added `_alpha_general_answer()` with direct answers for factual questions.

### Failure 4: "Alpha, research..." → "Clarify the question"
**Cause:** No Alpha research handler; fell through to clarify fallback.
**Fix:** Added `_alpha_research()` with web search or graceful fallback.

### Failure 5: "Nexus, research..." → "Clarify the question"
**Cause:** Nexus was attempting open research instead of refusing.
**Fix:** Added Layer 4d (Nexus research refusal) that refers to Alpha.

### Failure 6: "Nexus, give me a plan for today" → "Review 3 pending approvals"
**Cause:** "plan for today" matched temporal intent ("today" with "plan" in time verbs).
**Fix:** Added "plan" to business verbs exclusion in temporal detection.

## Files Changed

| File | Changes |
|------|---------|
| `scripts/telegram/message_understanding.py` | Role prefix regex, business verb exclusion, research intent, challenge followup detection |
| `scripts/telegram/nexus_telegram_bridge.py` | Alpha routing layer, Nexus research refusal, Nexus prefix reroute, Alpha handlers, dynamic header |
| `scripts/alpha/alpha_draft_engine.py` | Prefix stripping regex for comma/colon/dash/@ |
| `scripts/telegram/brain_contracts.py` | Command plan patterns, group(1) NoneType fix |

## Test Results: 13/13 PASS

| # | Command | Expected | Actual | Status |
|---|---------|----------|--------|--------|
| 1 | `Nexus, give me a plan for today` | Hermes strategy (not "Review 3 pending approvals") | Hermes Strategy | PASS |
| 2 | `Alpha, give me a plan for today` | Alpha outside plan | Alpha Outside Plan for Today | PASS |
| 3 | `Nexus, how can I make money today...` | Hermes money plan | Hermes Money Plan | PASS |
| 4 | `Alpha, how can I make money today?` | Alpha money opinion | Alpha Outside Money Opinion | PASS |
| 5 | `Nexus, create a 30-day plan...` | Hermes strategy | Hermes Strategy | PASS |
| 6 | `Alpha, give me outside opinion on 30-day money` | Alpha money opinion (30-day) | Alpha Outside Money Opinion | PASS |
| 7 | `Nexus, what color is the sky?` | Direct answer (not clarify) | Nexus General Answer | PASS |
| 8 | `Alpha, what color is the sky?` | Alpha direct answer | Alpha Simple Explanation | PASS |
| 9 | `Nexus, research...` | Nexus research refusal | Nexus Command — Internal Scope | PASS |
| 10 | `Alpha, research...` | Alpha research (web or fallback) | Alpha Outside Research | PASS |
| 11 | `Alpha, based on Nexus option 1, is there a better option?` | Alpha challenge | Alpha Outside Challenge | PASS |
| 12 | `what time is it` | Temporal response | Ray, it is X PM in Phoenix | PASS |
| 13 | `/report` | Operator report | Nexus Anytime Report | PASS |

## Telegram Launchd Status

- Job was running from pre-fix code
- Kickstarted after push to pick up d26848d
- Next `--once` cycle will use the fixed code

## Remaining Items

- Client portal: replace mock data with real Supabase queries
- Stripe frontend: fill product/price IDs
- Social platform access tokens
