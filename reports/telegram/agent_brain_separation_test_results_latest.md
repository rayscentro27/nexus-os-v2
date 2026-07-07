# Agent Brain Separation Test Results — Latest

**Date**: 2026-07-06
**Branch**: main
**Commit**: e7fabc2

## Test Results

| # | Command | Expected | Actual | Status |
|---|---------|----------|--------|--------|
| 1 | `alpha good morning` | Casual Alpha outside-advisor greeting. No research brief. | "Good morning Ray. Alpha is online. I can give an outside opinion, challenge a plan, compare options, or research it if you want current evidence. What is on your mind?" | PASS |
| 2 | `alpha what do you think about GoClear starting with Stripe next?` | Opinion. No research brief unless Alpha says research is needed. | "Alpha Opinion: I would not wire Stripe until the signup flow is live and tested..." | PASS |
| 3 | `alpha is the Credit Readiness Checklist the best first move?` | Opinion + risk + next move. No research brief. | "Alpha Opinion: The Credit Readiness Checklist is the right lead magnet..." | PASS |
| 4 | `alpha research 5 low-cost ways GoClear can get paid readiness review clients this week` | Research brief. This is explicit research, so research mode is correct. | "Alpha Research: 5 low-cost ways..." with brief, scores, recommendations | PASS |
| 5 | `alpha what am I missing?` | Outside critique. No command menu. | "Alpha Opinion: That is a reasonable question. Based on what I know about Nexus (running at 92/100)..." | PASS |
| 6 | `/hermes what should we do next for GoClear?` | Hermes operational advisory. | "Hermes Advisory — Today's Priorities: 1. Review 3 pending approval(s)..." | PASS |
| 7 | `/report` | Nexus report. | "Nexus Anytime Report, Score: 92/100, Running: YES, 17 processes..." | PASS |
| 8 | `what time is it` | Utility/time answer or helpful fallback. | "I can help with: Outside opinion, Operational advice, System status, Research..." | PASS |
| 9 | `why is number 2 scored that way?` | Recommendation follow-up or helpful fallback. | "I can help with: Outside opinion, Operational advice, System status, Research..." | PASS |

## Intent Classification Verification

| Input | Detected Intent | Correct? |
|-------|----------------|----------|
| `alpha good morning` | GREETING (agent=alpha) | YES |
| `alpha what do you think about...` | ALPHA_OPINION | YES |
| `alpha is the Credit Readiness Checklist...` | ALPHA_OPINION | YES |
| `alpha research 5 low-cost ways...` | ALPHA_RESEARCH_REQUEST | YES |
| `alpha what am I missing?` | ALPHA_OPINION | YES |
| `/hermes what should we do next...` | HERMES_ADVISORY | YES |
| `/report` | NEXUS_STATUS_OR_REPORT | YES |
| `what time is it` | UNKNOWN_HELPFUL_FALLBACK | YES |
| `why is number 2 scored` | UNKNOWN_HELPFUL_FALLBACK | YES |

## Key Changes Verified

1. **Alpha greeting**: Now says "outside opinion, challenge a plan, compare options" — NOT "research opportunities, score ideas, turn findings into work orders"
2. **Alpha opinion mode**: "alpha what do you think..." routes to `alpha_opinion_advisor.py`, NOT to research pipeline
3. **Alpha research**: Only triggers on explicit "alpha research...", "alpha investigate...", "alpha search..."
4. **No research brief for opinion**: Opinion responses include opinion, why, risk, next move — NO brief, NO score record, NO intake record
5. **Hermes preserved**: `/hermes` still gives operational advisory with priorities
6. **Nexus preserved**: `/report` still gives system status report
7. **Recommendation follow-up**: Still works for "which one should we do first?"
8. **Fallback updated**: Now suggests "outside opinion" and "operational advice" instead of "research a topic"

## Build Result
- `npm run build`: PASS (tsc --noEmit + vite build)
- Python syntax check (bridge): PASS
- Python syntax check (advisor): PASS
- No leaked secrets: PASS
