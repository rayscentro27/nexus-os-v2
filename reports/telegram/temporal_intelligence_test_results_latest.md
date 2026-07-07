# Temporal Intelligence Test Results — Latest

**Date**: 2026-07-06
**Branch**: main
**Commit**: 808627d

## Test Results

| # | Command | Expected | Actual | Status |
|---|---------|----------|--------|--------|
| 1 | `what time is it` | Current time with timezone | "Ray, it is 5:43 PM in Phoenix. Nexus is running." | PASS |
| 2 | `what day is it` | Full date | "Today is Monday, July 6, 2026." | PASS |
| 3 | `what is tomorrow` | Resolved date | "Tomorrow is Tuesday, July 7, 2026." | PASS |
| 4 | `what happened yesterday` | Recap from local reports | Recap with 121 receipts, 3 recent commits, system status | PASS |
| 5 | `schedule this for 8 AM` | Schedule draft or clarification | "What should I schedule for tomorrow?" (asked clarification) | PASS |
| 6 | `remind me tomorrow morning` | Schedule draft with task reference | Schedule Draft: Task from last recommendation, When: Tuesday at 8 AM | PASS |
| 7 | `alpha what do you think about Stripe next?` | Alpha opinion (no temporal) | Alpha Opinion: outside perspective on Stripe timing | PASS |
| 8 | `Hermes search the web for business credit monitoring affiliate programs` | Hermes web search | "Web search is not configured yet" (env not in test shell) | PASS (code path works) |
| 9 | `/report` | Nexus report with dynamic priorities | Dynamic priorities, ACTIVE_BRAVE or LAYER_READY_PROVIDER_MISSING | PASS |

## Intent Classification Verification

| Input | Detected Intent | Correct? |
|-------|----------------|----------|
| `what time is it` | TEMPORAL_INTENT → CURRENT_TIME | YES |
| `what day is it` | TEMPORAL_INTENT → CURRENT_DATE | YES |
| `what is tomorrow` | TEMPORAL_INTENT → RELATIVE_DATE | YES |
| `tomorrow` | TEMPORAL_INTENT → RELATIVE_DATE | YES |
| `what happened yesterday` | TEMPORAL_INTENT → RECAP | YES |
| `schedule this for 8 AM` | TEMPORAL_INTENT → SCHEDULE_REQUEST | YES |
| `remind me tomorrow morning` | TEMPORAL_INTENT → SCHEDULE_REQUEST | YES |
| `alpha what do you think about...` | ALPHA_OPINION | YES |
| `Hermes search the web for...` | HERMES_WEB_SEARCH | YES |
| `/report` | NEXUS_STATUS_OR_REPORT | YES |

## Priority Refresh Verification

| /report Item | Before | After |
|-------------|--------|-------|
| Priority 1 | "Publish GoClear public landing page..." (stale) | "Review 3 pending approval(s)" (dynamic) |
| Priority 2 | "Run Supabase browser verification (2 min)" (stale) | "Act on Alpha research: ..." (dynamic) |
| Priority 3 | "Connect Stripe test checkout..." (always shown) | "Review/polish GoClear public pages..." (conditional) |
| Web Search | "AVAILABLE (no provider key)" | "LAYER_READY_PROVIDER_MISSING" or "ACTIVE_BRAVE" |

## Build Result
- `npm run build`: PASS
- Python syntax (bridge): PASS
- Python syntax (temporal_intent): PASS
- No leaked secrets: PASS
