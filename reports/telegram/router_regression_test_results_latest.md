# Router Regression Test Results — 2026-07-07

## Test Sequence (clean state, no prior context)

```
=== FULL REGRESSION TEST SEQUENCE ===

 1. [Hermes Money Plan   ] how can i make money today                    -> Hermes — Hermes Money Plan — Today
 2. [Alpha Money Opinion ] alpha how can i make money today              -> Alpha — Alpha Outside Opinion — Money Moves
 3. [Deeper research     ] alpha can you do deeper research on this      -> I can investigate this further: alpha how can i make money today | Say "confirm"
 4. [Execute pending     ] confirm                                       -> Investigating further: alpha how can i make money today
 5. [Numbered follow-up  ] why is number 2 scored that way?              -> Use checklist + short call as the funnel
 6. [Work order from item] turn number 2 into a work order               -> Work Order Draft Created
 7. [Research deeper     ] research deeper                               -> I can investigate this further: alpha how can i make money today | Say "confirm"
 8. [Execute pending     ] confirm                                       -> Investigating further: alpha how can i make money today
 9. [Temporal            ] what time is it                               -> Ray, it is 11:22 AM in Phoenix. Nexus is running.
10. [Report              ] /report                                       -> Nexus Anytime Report | Score: 92/100 ACTIVE_OPERATING_SYSTEM
```

## Per-Command Verification

### 1. "how can i make money today"
- **Expected**: Hermes Money Plan with GoClear-specific items
- **Result**: PASS — 5 items including $97 readiness review (8.5/10), 15-min calls (7.5/10), checklist lead magnet (7.0/10)
- **Active context saved**: YES — context_type: money_plan, source: hermes

### 2. "alpha how can i make money today"
- **Expected**: Alpha Outside Opinion with 3 items
- **Result**: PASS — Fastest realistic move (8.0/10), checklist + call funnel (7.5/10), affiliates backend (5.5/10)
- **Active context saved**: YES — context_type: money_plan, source: alpha

### 3. "alpha can you do deeper research on this"
- **Expected**: Resolves "this" to active context topic "alpha how can i make money today"
- **Result**: PASS — Topic resolved correctly, pending_action saved with confirm_deeper_research
- **Active context preserved**: YES — not overwritten

### 4. "confirm" (after deeper research)
- **Expected**: Executes pending confirm_deeper_research action
- **Result**: PASS — "Investigating further: alpha how can i make money today"
- **Pending action cleared**: YES

### 5. "why is number 2 scored that way?"
- **Expected**: Explains item #2 from active context (Use checklist + short call as the funnel, 7.5/10)
- **Result**: PASS — Shows score, summary, strengths, weaknesses, next step
- **Active context preserved**: YES

### 6. "turn number 2 into a work order"
- **Expected**: Creates work order from active context item #2
- **Result**: PASS — "Work Order Draft Created" with title "Hermes: Use checklist + short call as the funnel"
- **Work order created from real item**: YES — not from "Clarify the question"

### 7. "research deeper"
- **Expected**: Resolves topic from active context
- **Result**: PASS — "I can investigate this further: alpha how can i make money today"
- **Pending action saved**: YES

### 8. "confirm" (after research deeper)
- **Expected**: Executes pending action
- **Result**: PASS — "Investigating further: alpha how can i make money today"
- **Pending action cleared**: YES

### 9. "what time is it"
- **Expected**: "Ray, it is <time> in Phoenix. Nexus is running."
- **Result**: PASS — "Ray, it is 11:22 AM in Phoenix. Nexus is running."
- **Temporal handler reached**: YES

### 10. "/report"
- **Expected**: Full system report with score, processes, approvals
- **Result**: PASS — Score 92/100, 17 processes, 350 receipts, Telegram ACTIVE_LIVE_POLLING

## Active Context State After Full Sequence

```json
{
  "topic": "alpha how can i make money today",
  "context_type": "money_plan",
  "source_agent": "alpha",
  "top_index": 1,
  "last_selected_index": 2,
  "items": [
    {"index": 1, "title": "Fastest realistic move: close a readiness review today", "score": 8.0},
    {"index": 2, "title": "Use checklist + short call as the funnel", "score": 7.5},
    {"index": 3, "title": "Affiliates are backend, not first sale", "score": 5.5}
  ]
}
```

## Regression Fixes Verified

| Issue | Before | After |
|-------|--------|-------|
| "what time is it" | "I understand the timeframe but need more context" | "Ray, it is 11:22 AM in Phoenix" |
| "confirm" (no pending) | Hermes guidance with "Clarify the question" | "I do not have a pending action to confirm" |
| Active context after "confirm" | "Clarify the question" as topic | Alpha Money Moves preserved |
| "alpha can you do deeper research on this" | Topic = raw phrase | Topic = active context topic |
| "why is number 2 scored that way?" | Could not find item | Explains real item #2 (7.5/10) |
| "turn number 2 into a work order" | Work order from "Clarify the question" | Work order from real item #2 |
| "research deeper" | Topic = "confirm" | Topic = active context topic |

## Test Commands for Ray to Retest in Telegram

1. `how can i make money today`
2. `alpha how can i make money today`
3. `alpha can you do deeper research on this`
4. `confirm`
5. `why is number 2 scored that way?`
6. `turn number 2 into a work order`
7. `research deeper`
8. `confirm`
9. `what time is it`
10. `/report`

## Report Paths
- Audit: `reports/telegram/router_regression_audit_latest.md`
- Tests: `reports/telegram/router_regression_test_results_latest.md`
