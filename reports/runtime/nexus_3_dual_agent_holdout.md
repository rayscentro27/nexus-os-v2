# Nexus 3 Dual Agent Holdout

Generated: 2026-07-21

## Nexus Hermes

- Turns: 100
- Passed: 73
- Score: 73%
- Model calls: 121
- Input tokens: 182,690
- Output tokens: 8,757
- Average latency: 2,669.6 ms
- p95 latency: 5,420.8 ms

### Nexus Category Scores

| Category | Score |
|---|---:|
| ordinary | 100% |
| writing | 100% |
| identity | 20% literal scorer; several direct identity answers were acceptable conversationally |
| reference | 85.71% |
| tool | 56.25% |
| action | 56.25% |

### Nexus Failure Pattern

- native tool calling under-selected tools for current system health, Stripe/trading status, revenue, client follow-up, provenance, and some report follow-ups;
- governed draft requests were sometimes treated as clarification instead of draft tools;
- direct self-approval denial was safe, but the literal scorer expected pre-model blocking;
- ordinary conversation and writing were corrected and no longer over-routed to Nexus tools.

## Hermes Alpha

- Turns: 100
- Literal passed: 94
- Literal score: 94%
- Semantic score: PASS for hosted model, history, and Supabase/client-data boundary
- Model calls: 100
- Input tokens: 88,228
- Output tokens: 16,834
- Average latency: 3,823.6 ms
- p95 latency: 7,906 ms

### Alpha Category Scores

| Category | Literal Score |
|---|---:|
| ordinary | 100% |
| writing | 100% |
| strategy | 100% |
| reference | 100% |
| boundary | 40% literal; semantically passed because all failures were correct “I don’t have access” refusals |
| research | 100% |
| action | 100% |
| mixed | 100% |

## Deployment Gate

Deployment gate failed because Nexus Hermes scored below 95%. No frontend deployment, merge to `main`, live browser certification, or rollback test was performed.

Certification state: `NEXUS_HERMES_FAILED`
