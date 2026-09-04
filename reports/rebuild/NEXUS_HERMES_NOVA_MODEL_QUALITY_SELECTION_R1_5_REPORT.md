# Nexus Hermes Nova Model Quality Selection R1.5

## Executive Result

`HERMES_NOVA_MODEL_QUALITY_SELECTION_R1_5=PARTIAL`.

The production reasoning architecture was frozen. A 40-turn / 3-conversation
benchmark dataset was created before comparison. The live OpenRouter catalog
was audited without exposing credentials. A bounded comparison found that
`minimax/minimax-m3:free` produced a more specific Nexus-grounded opinion than
the `openai/gpt-4o-mini` control on one representative case, but the run did
not reach a certifiable full benchmark: multiple responses from both routes
were not consistently machine-parseable by the existing response extractor,
and `z-ai/glm-5.2:free` returned a provider error. No production model switch
was made.

## Starting State

Starting HEAD and `origin/main`: `51ca9de1282f3abb21a725187d15485ed71fc752`.
Branch: `main`. The worktree contained extensive unrelated changes; they were
preserved and not staged.

## Architecture Freeze

No SOUL, AGENTS, executive reasoning, classifier, formatter, grounding,
specialist, MCP, session, or durable-process architecture was changed during
the model comparison. The only task artifacts are the frozen dataset and this
report.

`NOVA_MODEL_BENCHMARK_ARCHITECTURE_FROZEN=PASS_REAL`
`NOVA_MODEL_BENCHMARK_NO_TUNING=PASS_REAL`

## Approved Model Surface

The only configured credential lane is OpenRouter, using the existing
credential-control environment. The live `/api/v1/models` catalog was reached
without printing the key. The current control is `openai/gpt-4o-mini`.
Paid stronger candidates were not invoked because no new paid-use approval was
provided. They remain cost-gated, even where catalog metadata exists.

## Candidate Set

- `openai/gpt-4o-mini` — current control; configured and previously used.
- `minimax/minimax-m3:free` — zero-priced catalog candidate; bounded probe ran.
- `z-ai/glm-5.2:free` — zero-priced catalog candidate; provider returned an
  error and it was not treated as a winner.
- `openrouter/free` — router candidate; bounded probe ran, but not selected.

`NOVA_APPROVED_MODEL_SURFACE_AUDIT=PASS_REAL`.

## Frozen Benchmark Dataset

The frozen dataset is [NEXUS_HERMES_NOVA_MODEL_BENCHMARK_R1_5_DATASET.json](/Users/raymonddavis/nexus-os-v2/reports/rebuild/NEXUS_HERMES_NOVA_MODEL_BENCHMARK_R1_5_DATASET.json).
It contains 40 independent turns across casual, opinion, priority, attention,
current state, strategy, evidence, contradiction, multi-specialist, process,
follow-through, and multi-gear classes, plus three multi-turn conversations.
Most formulations are held out from the historical certification probes.

`NOVA_MODEL_BENCHMARK_DATASET_FROZEN=PASS_REAL`

## Control Results

The control was probed with the same durable Nova identity context. It showed
generic answers for casual and executive-attention prompts and generic
architecture language for at least one Nexus-opinion prompt. Some responses
contained control characters that defeated the existing JSON extraction path.
This makes the attempted full control run incomplete rather than a fabricated
score.

`NOVA_MODEL_CONTROL_BENCHMARK=FAIL`

## Candidate Results

`minimax/minimax-m3:free` produced a materially stronger representative answer
to the Nexus-opinion probe, explicitly describing the shift from AI-as-tool to
AI-as-operator, durable objectives, departmental specialization, and
continuity. This is promising but is not sufficient to establish broad
generalization or Hermes tool-call compatibility.

`z-ai/glm-5.2:free` returned a provider error. `openrouter/free` returned a
specific architectural-risk answer in one bounded probe, but its routed model
identity and repeatability were not established.

`NOVA_MODEL_CANDIDATE_BENCHMARKS=FAIL`.

## Casual / Opinion / Strategic Comparison

The bounded probes suggest the free MiniMax route may improve Nexus-specific
opinion quality, but casual, strategic, evidence-relevance, contradiction,
tool-use, and multi-gear quality were not measured to the required controlled
standard. Provider payload parse failures also prevent reliable latency and
completion scoring.

## Tool Behavior

The direct provider comparison did not certify Hermes-native tool behavior.
Several payloads were not parseable through the existing extraction path. This
is recorded as a measurement/reliability limitation, not silently converted
into model success.

## Multi-Gear Comparison

Not certifiable. The frozen dataset includes three multi-turn conversations,
but a complete equivalent run with reliable response capture was not obtained.

`NOVA_MODEL_MULTI_GEAR_TEST=FAIL`

## Latency

No reliable median/p90 comparison is reported because the response-capture
failures prevented a complete, consistently timestamped scored sample.

`NOVA_MODEL_LATENCY_COMPARISON=FAIL`

## Cost / Resource Comparison

Model catalog pricing was observable for OpenRouter. The control is a paid
configured route; free candidates were zero-priced in the catalog. Actual
benchmark cost was not reliably attributable across the incomplete run.

`NOVA_MODEL_COST_COMPARISON=COST_UNKNOWN`

## MoA Benchmark

No separate MoA benchmark was run. It would add latency and model calls before
the single-model capture path is reliable.

`NOVA_MOA_BENCHMARK=DEFERRED_FOR_COST`

## Model Routing Decision

No activation or routing change is justified by the incomplete evidence.
Current decision: `NO_APPROVED_BETTER_MODEL_AVAILABLE` as a certification
decision, with `minimax/minimax-m3:free` retained as a candidate for a future
repeatable benchmark after the provider-response capture path is repaired.

`NOVA_MODEL_ROUTING_ARCHITECTURE=KEEP_CURRENT`
`NOVA_EXECUTIVE_MODEL_DECISION=KEEP_CURRENT_PENDING_RELIABLE_COMPARISON`
`NOVA_SELECTED_MODEL_ACTIVATED=KEEP_CURRENT`

## Production Activation

No production configuration, profile, prompt, or Telegram route was changed.

## Post-Selection Held-Out Benchmark

Not run because no model was selected.

`NOVA_POST_SELECTION_HELD_OUT_GENERALIZATION=NOT_RUN`
`NOVA_SELECTED_MODEL_PRIMARY_PATH=NOT_RUN`

## Real Ray Telegram Generalization

Not requested. The prerequisite candidate benchmark and post-selection held-out
benchmark did not pass. No Ray-originated messages were fabricated.

`REAL_TELEGRAM_RAY_ORIGIN=WAITING_RAY_HUMAN_ACTION`
`REAL_TELEGRAM_MODEL_GENERALIZATION=NOT_RUN`

## Previous Capability Regression

No previous Nova or remote-infrastructure capability was intentionally changed.
Focused pre-existing Nova tests remain green from the prior checkpoint; no
production model change was made here.

`NOVA_MODEL_CHANGE_REGRESSION=PASS_REAL`

## Remaining Limitation

`NOVA_MODEL_LIMITATION_OUTCOME=NO_APPROVED_BETTER_MODEL` is a current
certification outcome, not proof that no better model exists. The next safe
step is to repair or replace the non-secret response-capture/benchmark harness,
then rerun the frozen dataset unchanged. No prompt accumulation is warranted.

## Full Autonomy Assessment

`HERMES_NOVA_READY_FOR_FULL_COMPANY_AUTONOMY=NO`.

## True Ray Blockers

`NONE`. No payment, upgrade, new account, or new secret was requested.

## Git

Task-scoped commit:

`8a3f56a`

No unrelated files were staged. No payments, live trades, publication, or
external consequential actions occurred.

## Final Contract

```text
HERMES_NOVA_MODEL_QUALITY_SELECTION_R1_5=PARTIAL
NOVA_MODEL_BENCHMARK_ARCHITECTURE_FROZEN=PASS_REAL
NOVA_MODEL_BENCHMARK_NO_TUNING=PASS_REAL
NOVA_APPROVED_MODEL_SURFACE_AUDIT=PASS_REAL
NOVA_MODEL_CANDIDATE_SET=openai/gpt-4o-mini; minimax/minimax-m3:free; z-ai/glm-5.2:free; openrouter/free
NOVA_MODEL_BENCHMARK_DATASET_FROZEN=PASS_REAL
NOVA_MODEL_MULTI_GEAR_TEST=FAIL
NOVA_MODEL_LATENCY_COMPARISON=FAIL
NOVA_MODEL_COST_COMPARISON=COST_UNKNOWN
NOVA_MODEL_CONTROL_BENCHMARK=FAIL
NOVA_MODEL_CANDIDATE_BENCHMARKS=FAIL
NOVA_MOA_BENCHMARK=DEFERRED_FOR_COST
NOVA_MODEL_ROUTING_ARCHITECTURE=KEEP_CURRENT
NOVA_MODEL_ROUTING_GENERALIZED=NOT_APPLICABLE
NOVA_MODEL_IMPROVEMENT_MATERIAL=NO
NOVA_EXECUTIVE_MODEL_DECISION=KEEP_CURRENT_PENDING_RELIABLE_COMPARISON
NOVA_SELECTED_MODEL_ACTIVATED=KEEP_CURRENT
NOVA_POST_SELECTION_HELD_OUT_GENERALIZATION=NOT_RUN
NOVA_SELECTED_MODEL_PRIMARY_PATH=NOT_RUN
REAL_TELEGRAM_RAY_ORIGIN=WAITING_RAY_HUMAN_ACTION
REAL_TELEGRAM_MODEL_GENERALIZATION=NOT_RUN
NOVA_MODEL_LIMITATION_OUTCOME=NO_APPROVED_BETTER_MODEL
NOVA_MODEL_CHANGE_REGRESSION=PASS_REAL
NOVA_READY_TO_RECEIVE_NEW_COMPANY_CAPABILITIES=NO
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
HERMES_NOVA_READY_FOR_FULL_COMPANY_AUTONOMY=NO
NEXT_RECOMMENDED_PHASE=RELIABLE_MODEL_BENCHMARK_CAPTURE_REPAIR
```
