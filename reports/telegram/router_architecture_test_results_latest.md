# Router Architecture Test Results — 2026-07-07

## Message Understanding Tests (15/15 PASS)

| Message | Expected Intent | Status |
|---------|----------------|--------|
| how can i make money today | money_plan | PASS |
| how do we make money today | money_plan | PASS |
| what can GoClear do to get paid today | money_plan | PASS |
| how can we get clients today | client_acquisition | PASS |
| what is the fastest revenue move | money_plan | PASS |
| alpha how can i make money today | money_plan | PASS |
| alpha research how to make money today | money_research | PASS |
| alpha can you do deeper research on this | opinion | PASS |
| hermes what should we do next for GoClear | business_strategy | PASS |
| research current business credit monitoring affiliate programs | web_research | PASS |
| why is number 2 scored that way | active_context_followup | PASS |
| turn this into a work order | active_context_followup | PASS |
| confirm | help (no pending action) | PASS |
| what time is it | temporal | PASS |
| /report | deterministic_command | PASS |

## Draft Engine Tests (11/11 PASS)

| Test | Status |
|------|--------|
| Hermes money_plan role = hermes | PASS |
| Hermes money_plan has items | PASS |
| Hermes money_plan item 1 = Readiness Review | PASS |
| Hermes money_plan item 1 score >= 7 | PASS |
| Hermes money_plan confidence >= 0.7 | PASS |
| Hermes money_plan no web needed | PASS |
| Hermes client_acquisition has items | PASS |
| Alpha money_plan role = alpha | PASS |
| Alpha money_plan mode = outside_opinion | PASS |
| Alpha money_plan has items | PASS |
| Alpha money_plan has readiness in item 1 | PASS |

## Golden Transcript Tests (12/12 PASS)

| Test | Status |
|------|--------|
| "how can i make money today" → Hermes Money Plan with Readiness Review | PASS |
| "alpha how can i make money today" → Alpha outside opinion with readiness | PASS |
| "how can we get clients today" → Client acquisition plan | PASS |
| "hermes what should we do next for GoClear" → Business strategy | PASS |
| "what time is it" → Time response | PASS |
| "/report" → System report | PASS |
| "/status" → System status | PASS |
| "confirm" (no pending) → Help message | PASS |
| "xyzzy" (unknown) → Intelligent fallback | PASS |

## Build

- tsc --noEmit: PASS
- vite build: PASS

## Safety Scan

- No .env staged
- No API keys in changed files
- No secrets in generated reports
