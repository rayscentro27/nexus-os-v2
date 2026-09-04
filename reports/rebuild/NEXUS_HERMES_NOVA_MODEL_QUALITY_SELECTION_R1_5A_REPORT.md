# Nexus Hermes Nova Model Quality Selection R1.5A

## Executive Result

`HERMES_NOVA_MODEL_QUALITY_SELECTION_R1_5A=PARTIAL`.

The benchmark measurement instrument was repaired without changing Nova's
production reasoning architecture or the frozen dataset. The corrected capture
smoke succeeded for both named routes. The control dataset was captured in
bounded batches with all 40 cases represented. MiniMax responses were captured
when available, but the free route was materially slower/intermittent and its
bounded batch run did not complete all 40 cases in the operational window. No
model was activated, no prompt tuning was performed, and no real Telegram test
was requested.

## Starting State

Starting HEAD and `origin/main`: `8ceff01f1852cfdbf1141a7903988ca55f381681`.
Branch: `main`. The worktree contained unrelated changes; they were preserved.

## Architecture Freeze

No SOUL, AGENTS, Nova reasoning, intent, grounding, formatter, specialist,
session, MCP, or durable-process production code was modified. The R1.5 JSON
dataset is unchanged.

`NOVA_R1_5A_ARCHITECTURE_FROZEN=PASS_REAL`
`NOVA_R1_5A_DATASET_UNCHANGED=PASS_REAL`
`NOVA_R1_5A_NO_MODEL_SPECIFIC_TUNING=PASS_REAL`

## Capture Root Cause

R1.5 used a shell `jq` extraction path that assumed every provider payload was
strict JSON and treated malformed control characters as a generic parse
failure. The first R1.5A Python runner also incorrectly converted its own
HTTPS transport exception into a provider-error envelope. This was corrected by
using the already-proven curl transport and preserving transport status
separately.

## Capture Failure Classes

Observed classes: `INVALID_PROVIDER_JSON` from raw control-character payloads
in the original shell path; `HTTP_TRANSPORT_FAILURE` from the initial Python
runner; `PROVIDER_ERROR` for an actual provider error; and `CAPTURED` after the
corrected path. Provider errors are not semantic model scores.

`MODEL_CAPTURE_ROOT_CAUSE_AUDIT=PASS_REAL`
`MODEL_CAPTURE_FAILURE_CLASSES=INVALID_PROVIDER_JSON;HTTP_TRANSPORT_FAILURE;PROVIDER_ERROR`

## Safe Raw Evidence

Canonical results retain status, content type, envelope keys, model identity,
finish reason, usage when present, a short body hash, and parse mode. They do
not retain authorization headers or credential values. Captured JSONL evidence
is stored in `reports/rebuild/model_benchmark_r1_5a_*.jsonl`.

## Canonical Response Normalization

`scripts/nova/model_benchmark_capture.py` separates envelope parsing, assistant
text/tool-call extraction, and scoring input. Model prose remains a string.
Illegal raw controls inside a JSON string are represented as escaped Unicode,
not silently deleted. SSE, normal text, empty content/tool calls, provider
errors, usage, finish reasons, and unknown fields are handled generically.

`MODEL_CAPTURE_SAFE_RAW_EVIDENCE=PASS_REAL`
`MODEL_CAPTURE_LAYER_SEPARATION=PASS_REAL`
`MODEL_CAPTURE_CANONICAL_RESULT=PASS_REAL`
`MODEL_CAPTURE_TEXT_SERIALIZATION=PASS_REAL`
`MODEL_CAPTURE_RESPONSE_SHAPES=PASS_REAL`
`MODEL_PROVIDER_FAILURE_SEPARATION=PASS_REAL`

## Capture Unit Tests

Five capture fixtures pass, including Unicode/multiline text, illegal raw
controls, tool calls, provider errors, SSE, and safe serialization. Combined
focused suites pass: `21 passed`.

`MODEL_CAPTURE_UNIT_TESTS=PASS_REAL`
`MODEL_CAPTURE_SMOKE_RELIABILITY=PASS_REAL`

## Final Candidate Set

- `openai/gpt-4o-mini` — configured control.
- `minimax/minimax-m3:free` — named zero-priced candidate.

The GLM free route was excluded after a bounded provider error. The opaque
`openrouter/free` route was excluded because routed identity/repeatability are
not stable enough for fair selection.

`MODEL_COMPARISON_FINAL_CANDIDATE_SET=openai/gpt-4o-mini; minimax/minimax-m3:free`

## Candidate Reliability

The control captured all 40 frozen cases with `CAPTURED` status; observed model
identity was stable. MiniMax captured returned responses with observed identity
`minimax/minimax-m3:free`, but the route was slow/intermittent and did not
complete all bounded batches. This is a production-reliability penalty, not a
semantic failure score.

`MODEL_CANDIDATE_RELIABILITY_COMPARISON=PASS_REAL`
`MODEL_PRODUCTION_RELIABILITY_ASSESSMENT=PASS_REAL`

## Benchmark Fairness

Both named routes received the same frozen cases, system context, temperature,
maximum output, and request shape. The provider route and actual availability
were recorded. No model-specific prompt or retry policy was introduced.

`MODEL_BENCHMARK_FAIRNESS=PASS_REAL`
`MODEL_FROZEN_DATASET_RERUN=FAIL` — control coverage is complete, but the
MiniMax candidate run is incomplete.

## Blinded Scoring and Objective Metrics

The repaired canonical result supports blinded scoring and objective metrics,
but a complete blinded semantic score was not produced in this bounded run.
The control’s 40-case capture is complete; MiniMax’s incomplete run cannot
support a fair quality win. Latency is observable for captured records but not
comparable at the required complete-sample level.

`MODEL_BLINDED_QUALITY_SCORING=FAIL`
`MODEL_OBJECTIVE_METRICS=PASS_REAL`

## Control Results

`openai/gpt-4o-mini` remains the only fully repeatable production control in
this campaign. It was not replaced.

## MiniMax Results

The earlier representative MiniMax answer was more Nexus-grounded than the
control, and returned records are now safely capturable. However, the route's
bounded completion behavior and latency were insufficient to establish broad
quality, tool compatibility, or production suitability.

## Other Candidate Results

`z-ai/glm-5.2:free` returned a provider failure in the prior bounded probe and
was not selected. `openrouter/free` was not repeatable/identity-stable enough
for comparison.

## Hermes Tool Compatibility

Not run for MiniMax. No production switch is allowed without canonical Hermes
0.20.6 / `nova_nexus` tool-call, result-consumption, guardrail, and synthesis
proof.

`MODEL_HERMES_TOOL_COMPATIBILITY=NOT_RUN`
`MODEL_SESSION_COMPATIBILITY=NOT_RUN`

## Latency

Captured control records averaged approximately 2.4 seconds in the complete
bounded batches. MiniMax captured records were materially slower (approximately
6.7 seconds in the initial successful sample) and its full run did not complete
within the bounded execution window. A formal p90 comparison is deferred.

`MODEL_LATENCY_COMPARISON=FAIL`

## Cost

The control is a configured paid OpenRouter route. MiniMax was catalogued as
zero-priced. No new paid provider, plan, or billing action was used.

`MODEL_COST_COMPARISON=PASS_REAL`

## Production Reliability

The best answer is not automatically the best production model. MiniMax is a
quality candidate but not a production winner because availability, completion
time, Hermes tools, and session compatibility remain unproven.

## Model Routing Decision

`NOVA_MODEL_ROUTING_DECISION=KEEP_CURRENT`.
`NOVA_EXECUTIVE_MODEL_DECISION=NO_RELIABLE_BETTER_MODEL_AVAILABLE`.
`NOVA_SELECTED_MODEL_ACTIVATED=KEEP_CURRENT`.

No two-gear route is justified until a complete, fairly scored candidate run
and Hermes compatibility test exists.

## Post-Selection Held-Out Test

Not run because no candidate was selected.

`NOVA_POST_SELECTION_HELD_OUT_GENERALIZATION=NOT_RUN`
`NOVA_SELECTED_MODEL_PRIMARY_PATH=NOT_RUN`

## Real Telegram Certification

Not requested. The required model selection, Hermes tool compatibility, and
post-selection held-out gates did not pass. No Ray-originated messages were
fabricated.

`REAL_TELEGRAM_RAY_ORIGIN=WAITING_RAY_HUMAN_ACTION`
`REAL_TELEGRAM_MODEL_GENERALIZATION=NOT_RUN`

## Nova Executive Interface Readiness

`NOVA_EXECUTIVE_INTERFACE_READY=NO`
`NOVA_READY_TO_RECEIVE_NEW_COMPANY_CAPABILITIES=NO`
`NOVA_BLOCKING_FULL_COMPANY_AUTONOMY=YES`

## Remaining Limitation

The capture instrument is repaired. The remaining limitation is an incomplete
fair comparison plus MiniMax route reliability and absent Hermes tool proof.
The next phase should complete capture/scoring from the same frozen dataset,
then test the candidate through the actual Hermes path. Do not add Nova prompt
rules.

## True Ray Blockers

`NONE` for this campaign. Paid-model benchmarking would require explicit cost
approval, but no such benchmark was attempted.

## Git

Task-scoped artifacts: capture normalizer, capture runner, capture tests,
benchmark result JSONL, and this report. Unrelated worktree entries were not
staged.

## Final Contract

```text
HERMES_NOVA_MODEL_QUALITY_SELECTION_R1_5A=PARTIAL
NOVA_R1_5A_ARCHITECTURE_FROZEN=PASS_REAL
NOVA_R1_5A_DATASET_UNCHANGED=PASS_REAL
NOVA_R1_5A_NO_MODEL_SPECIFIC_TUNING=PASS_REAL
MODEL_CAPTURE_ROOT_CAUSE_AUDIT=PASS_REAL
MODEL_CAPTURE_FAILURE_CLASSES=INVALID_PROVIDER_JSON;HTTP_TRANSPORT_FAILURE;PROVIDER_ERROR
MODEL_CAPTURE_SAFE_RAW_EVIDENCE=PASS_REAL
MODEL_CAPTURE_LAYER_SEPARATION=PASS_REAL
MODEL_CAPTURE_CANONICAL_RESULT=PASS_REAL
MODEL_CAPTURE_TEXT_SERIALIZATION=PASS_REAL
MODEL_CAPTURE_RESPONSE_SHAPES=PASS_REAL
MODEL_PROVIDER_FAILURE_SEPARATION=PASS_REAL
MODEL_CAPTURE_UNIT_TESTS=PASS_REAL
MODEL_CAPTURE_SMOKE_RELIABILITY=PASS_REAL
MODEL_COMPARISON_FINAL_CANDIDATE_SET=openai/gpt-4o-mini;minimax/minimax-m3:free
MODEL_CANDIDATE_RELIABILITY_COMPARISON=PASS_REAL
MODEL_BENCHMARK_FAIRNESS=PASS_REAL
MODEL_FROZEN_DATASET_RERUN=FAIL
MODEL_BLINDED_QUALITY_SCORING=FAIL
MODEL_OBJECTIVE_METRICS=PASS_REAL
MINIMAX_VS_CONTROL_COMPARISON=FAIL
MODEL_HERMES_TOOL_COMPATIBILITY=NOT_RUN
MODEL_SESSION_COMPATIBILITY=NOT_RUN
MODEL_LATENCY_COMPARISON=FAIL
MODEL_COST_COMPARISON=PASS_REAL
MODEL_PRODUCTION_RELIABILITY_ASSESSMENT=PASS_REAL
NOVA_MODEL_ROUTING_DECISION=KEEP_CURRENT
NOVA_MODEL_ROUTING_REMAINS_GENERAL=PASS_REAL
MODEL_MATERIAL_QUALITY_IMPROVEMENT=NO
NOVA_EXECUTIVE_MODEL_DECISION=NO_RELIABLE_BETTER_MODEL_AVAILABLE
NOVA_SELECTED_MODEL_ACTIVATED=KEEP_CURRENT
NOVA_POST_SELECTION_HELD_OUT_GENERALIZATION=NOT_RUN
NOVA_SELECTED_MODEL_PRIMARY_PATH=NOT_RUN
REAL_TELEGRAM_RAY_ORIGIN=WAITING_RAY_HUMAN_ACTION
REAL_TELEGRAM_MODEL_GENERALIZATION=NOT_RUN
NOVA_EXECUTIVE_INTERFACE_READY=NO
NOVA_READY_TO_RECEIVE_NEW_COMPANY_CAPABILITIES=NO
NOVA_BLOCKING_FULL_COMPANY_AUTONOMY=YES
NOVA_R1_5A_REGRESSION=PASS_REAL
NOVA_INITIATIVE_RETAINED=PASS_REAL
NEW_COMPLIANCE_DEPARTMENT_IMPLEMENTED=NO
NEW_PRE_CREATIVE_COMPLIANCE_GATE=NO
NOVA_REASONING_RESTRICTED_BY_NEW_COMPLIANCE=NO
CREATIVE_REASONING_RESTRICTED_BY_NEW_COMPLIANCE=NO
SESSION_CONTINUITY=PASS_REAL
NOVA_NEXUS_PROFILE=PASS_REAL
ORACLE_HERMES=HEALTHY
MAC_CONTROL_PLANE_PROTECTED=PASS_REAL
RESEARCH_HEARTBEAT=ACTIVE
TRUE_RAY_BLOCKERS=NONE
NEXT_RECOMMENDED_PHASE=HERMES_TOOL_COMPATIBILITY_AND_COMPLETE_FROZEN_MODEL_SCORING
```
