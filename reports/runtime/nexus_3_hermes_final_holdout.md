# Nexus 3 Hermes Final Holdout

Generated: 2026-07-21

## Scope

This report covers the final Ray-only deployment gate for the Hermes model-first Edge Function on branch `wave/hermes-model-first-language`.

## Deployed Edge Function Verification

- Supabase project: `iqjwgpnujbeoyaeuwehj`
- Function: `hermes-chat`
- Provider: `openrouter`
- Primary model: `openai/gpt-4o-mini`
- Fallback model: `google/gemini-2.0-flash-001`
- Model-first mode tested with request mode: `model_first_conversation`

Focused deployed smoke after repair passed for direct response, client aggregate, report summary, provenance, schedule clarification, schedule draft, Alpha/Stripe/trading boundaries, and self-approval blocking.

## Full Holdout Result

- Turns: 101
- Passed: 79
- Score: 78.22%
- Certification threshold: 95%
- Result: FAIL

## Token And Latency

- Input tokens observed/estimated: 187,319
- Output tokens observed/estimated: 7,329
- Total tokens observed/estimated: 194,648
- Model calls: 152
- Fallback model calls: 0
- Average latency: 6,499.7 ms
- p50 latency: 6,526 ms
- p95 latency: 10,471.6 ms

## Category Scores

| Category | Score |
|---|---:|
| approvals | 100% |
| business | 100% |
| casual | 100% |
| clients | 80% |
| department | 100% |
| draft | 66.67% |
| identity | 50% |
| incomplete | 66.67% |
| misspelling | 75% |
| nexus_version | 100% |
| ordinary | 100% |
| personal | 100% |
| project_status | 100% |
| provenance | 50% |
| reference | 60% |
| repair | 80% |
| repo | 33.33% |
| reports | 66.67% |
| revenue | 100% |
| schedule | 50% |
| security | 100% |
| system_health | 100% |
| writing | 25% |

## Failed-Turn Summary

The primary failures were concentrated in:

- tool-free writing requests being overridden by client aggregate tool routing;
- visible-list references and repair turns still over-clarifying or selecting unrelated tools;
- report follow-up routing selecting report list instead of report summary;
- Repo Intelligence evidence questions being treated as provenance or direct general answers;
- scheduling follow-up state not consistently carrying prior report/time details;
- self-approval and execution denial initially returning through draft tooling instead of early denial.

A second focused repair cycle improved the failed-category sample from the prior 101-turn run but only reached 18/22 on the failed-category rerun. Per release policy, the frontend was not deployed and the feature branch was not merged to `main`.

## Deployment Decision

Certification state: `HOLDOUT_FAILED`

Frontend deployment: NOT RUN

Live browser certification: NOT RUN

Rollback verification: NOT RUN
