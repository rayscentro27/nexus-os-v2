# Telegram Router Architecture Audit — 2026-07-07

## Current Router Order (classify_message_intent)

| # | Intent | Trigger |
|---|--------|---------|
| 1 | APPROVAL_ACTION | `^(approve\|reject\|revise)\s+\w+` |
| 2 | WORK_ORDER_REQUEST | create task, make this, assign to |
| 3 | GREETING | hello, hi, good morning |
| 4 | CASUAL_AGENT_CHAT | how did you sleep, are you there |
| 5 | HERMES_ADVISORY | `^hermes what...`, `^what should we do next` |
| 6 | HERMES_WEB_SEARCH | `hermes search the web for`, `research`, `look up` |
| 7 | HERMES_URL_REVIEW | URL in web search match |
| 8 | NEXUS_STATUS_OR_REPORT | status, report, what happened |
| 9 | ALPHA_OPINION | `^alpha what do you think`, `should we`, `challenge this` |
| 10 | ACTIVE_CONTEXT_FOLLOWUP | number selections, why scored, research deeper |
| 11 | ALPHA_CONTEXT_FOLLOWUP | what did alpha find, which one first |
| 12 | ALPHA_RESEARCH_REQUEST | `alpha research`, `research`, `search the web for` |
| 13 | TEMPORAL_INTENT | what time, what day, schedule |
| 14 | **UNKNOWN_HELPFUL_FALLBACK** | static help menu |

## Why Broad Business Questions Fall to Fallback

"how can i make money today" — traced through all 13 checks:
- Not APPROVAL, WORK_ORDER, GREETING, CASUAL
- HERMES_ADVISORY requires `^hermes what` or `^what should we do next`
- HERMES_WEB_SEARCH requires explicit search verbs
- Not STATUS, ALPHA_OPINION (requires `^alpha` or `^what do you think`)
- ACTIVE_CONTEXT_FOLLOWUP doesn't match
- Not ALPHA_RESEARCH (requires `^alpha research` or `^research`)
- Not TEMPORAL
- Falls to UNKNOWN_HELPFUL_FALLBACK → static help menu

**Root cause:** No intent family for business/money/advisory questions without agent prefix.

## Where Fallback Happens

1. `classify_message_intent()` line 1267-1268 → returns UNKNOWN_HELPFUL_FALLBACK
2. `process_command()` line 2075-2076 → calls `handle_unknown_fallback()`
3. `handle_unknown_fallback()` lines 1384-1395 → static help string

## Where Alpha/Hermes/Nexus Role Selection Happens

Only in GREETING (prefix detection) and CASUAL_AGENT_CHAT. No general-purpose role selection.

## Where Web Search Is Triggered

1. HERMES_WEB_SEARCH intent → `build_advisory_answer()` → `web_search()`
2. `hermes_direct_answer()` via HERMES_ADVISORY → checks HERMES_WEB_SEARCH_PATTERNS internally

## Where Active Context Is Saved

1. After HERMES_WEB_SEARCH (findings as items)
2. After ALPHA_RESEARCH_REQUEST (score record as items)
3. NOT after HERMES_ADVISORY, ALPHA_OPINION, or NEXUS_STATUS

## Where Pending Actions Are Saved/Cleared

- Saved: `format_deeper_research()` → `save_pending_action()`
- Cleared: `handle_confirm_pending()` → `clear_pending_action()`
- Loaded: `detect_followup_intent()` for confirm/yes patterns

## Why Research Makes Answers Worse

`generate_alpha_ideas()` for `general_strategy` produces 5 hardcoded templates:
- "Research core options for: {topic}"
- "Identify quick wins related to: {topic}"
- "Map competitive landscape for: {topic}"
- "Create a 1-page brief on: {topic}"
- "Define success metrics for: {topic}"

All score 6.0/10. Zero actual research. This is filler pretending to be recommendations.

## Exact Files Needing Refactor

| File | Function | Issue |
|------|----------|-------|
| bridge.py | `classify_message_intent()` | No business/money/advisory intent family |
| bridge.py | `handle_unknown_fallback()` | Dead-end static help |
| bridge.py | `generate_alpha_ideas()` | Hardcoded filler templates |
| bridge.py | `classify_alpha_topic()` | Keyword-only, falls to general_strategy |
| bridge.py | `hermes_direct_answer()` | Duplicate routing, no context save |
| bridge.py | `HERMES_ADVISORY_PATTERNS` | Missing natural business questions |
| bridge.py | `HERMES_WEB_SEARCH_PATTERNS` | Missing natural research requests |
