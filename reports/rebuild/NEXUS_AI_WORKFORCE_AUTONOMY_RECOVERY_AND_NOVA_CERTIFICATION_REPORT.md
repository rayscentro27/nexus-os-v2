# Nexus AI Workforce, Executor, and Nova Certification

## Executive result

`NEXUS_AI_WORKFORCE_AUTONOMY_RECOVERY=PARTIAL`

The current Nexus runtime is not yet a certified AI-operated company. The
control plane and continuation layer run, and two bounded lanes have real safe
execution: Research through the private SearXNG adapter and Trading through the
paper-only OANDA loop. Most of the 23 durable company goals still terminate at
an honest queued work-order boundary because no canonical safe department
executor is registered for them.

The AI-worker evidence is also narrower than the worker registry suggested:
Codex and OpenCode have historical availability/execution probes, but no
current evidence shows the canonical Active Operator dispatching them for a
company goal. The current builder pilot selected `local_python`, recorded zero
model calls, and produced an isolated deterministic artifact. Therefore
`provider available` is not being counted as `AI employee working`.

## Starting state

- Local HEAD: `1f1e3b7c014f7a234be7521d674c987e269555df`
- `origin/main`: `158fc60f8eaa59cd964eb37ad433f73abe67fd56`
- Branch: `main`
- The worktree was already substantially dirty; unrelated changes were not
  staged or reverted.
- Durable portfolio: 23 goals in `data/runtime/company_goal_portfolio.json`.
- Continuous process observed: `scripts/run_continuous_operating_kernel.py
  --daemon --interval-seconds 1200`.
- Trading safety remains paper-only; no funded or live order path was enabled.

## Root cause

The prior continuation repair fixed selection, starvation, and honest work-order
creation, but it did not create department executors for every portfolio lane.
The canonical path is currently:

`goal selector → next_work_for_active_goal → Active Operator action`

The action map has real execution only for:

- `research.refresh`;
- `trading.research_cycle`;
- `internal.capability_verify` for bounded local Portal/Product and Systems
  checks.

Unsupported departments are intentionally represented as
`WAITING_CAPABLE_DEPARTMENT_EXECUTOR`. That is honest, but it is also the
reason more than 20 unfinished projects do not advance.

The AI-boundary hypothesis is partially confirmed. A child report or
deterministic analysis can persist and update `last_progress`, but the current
canonical operator has no general post-AI adapter that turns a structured AI
decision into a department-specific executor and then into a verified next
action. It is not proven that every project was closed by an AI response;
the stronger proven defect is missing capability-aware dispatch after
selection/analysis.

## Orchestration result

| Layer | Evidence | Result |
|---|---|---|
| Scheduler/process | daemon process and recent operator report | PASS |
| Durable goals | 23-goal portfolio | PASS |
| Goal selector | starvation-aware selector and bounded child identity | PASS |
| Empty-queue continuation | selector creates a child action | PASS |
| General department dispatch | unsupported departments become queued work orders | PARTIAL |
| AI-to-executor continuation | no general canonical bridge | FAIL |
| Restart-safe state | portfolio/work-item JSON and receipts | PASS for existing lanes |

## Executor result by department

| Department / goal family | Registered canonical executor | AI worker invoked by autonomous goal path | Durable effect | Current classification |
|---|---|---:|---|---|
| Research | private Oracle SearXNG adapter | No model call; deterministic read-only research | Research receipt, goal evidence, heartbeat | REAL SAFE EXECUTION |
| Trading | paper-only OANDA research loop | No model call; deterministic strategy/backtest path | paper/backtest/OOS/feedback state | REAL SAFE EXECUTION |
| Portal/Product | local portal backend capability verifier | No | local verification artifact when selected | BOUNDED NON-AI EXECUTOR |
| Systems | generic local capability verifier | No | generic capability-state artifact | BOUNDED, NOT FULL CAPABILITY PROOF |
| Funding / Funding/Product | fixture-only `NEXUS_CREDIT_BUSINESS_FUNDING` loop connected as `funding.readiness_review` | No | bounded readiness receipt and verified fixture result | BOUNDED SAFE EXECUTOR; NO AI |
| Alpha | persistence/evaluation bridge exists | No autonomous model evaluation proof | Alpha evaluation store when input exists | PARTIAL |
| Marketing/Creative | content worker/skill registry entries | No | no current canonical portfolio executor | QUEUED / MISSING EXECUTOR |
| Creative / Video | historical lab and builder proof surfaces | No current autonomous project invocation | deterministic/internal artifacts only | QUEUED / MISSING EXECUTOR |
| Finance / Opportunity / Grants | goal definitions and research surfaces | No | no current canonical executor | QUEUED / MISSING EXECUTOR |
| Customer Service / Documents | registry or research surfaces only | No | no safe autonomous external mutation permitted | GOVERNANCE-BOUND |
| Nova | live conversational model path | Yes for inbound conversation only | response/provenance, not autonomous project execution | READ/CONVERSATION PROVEN |

## AI worker result

The historical workforce certification still proves provider probes and
bounded worker availability only. The follow-up recovery additionally proves
current model calls through the existing OpenRouter/Nova gateway for bounded
company-goal planning and result review:

- Codex: historical `AVAILABLE` / execution probe verified;
- OpenCode: historical `AVAILABLE` / execution probe verified;
- MiMo and Kilo: installed but not execution-certified;
- OpenHands: not installed;
- local Python: available and execution-verified.

The builder pilot evidence at
`reports/hermes_modernization/end_to_end_pilot.json` explicitly records:

- selected worker: `local_python`;
- `model_calls`: `0`;
- `zero_token_execution`: `true`;
- isolated artifact and deterministic verification.

The append-only builder ledger is dominated by `local_python` records. Older
records containing `worker_id=codex` do not provide reliable model-usage
evidence: their cost provenance falls back to `local_python`, token usage is
zero, and they are historical Product Evolution records rather than current
Active Operator company-goal executions. They are not treated as proof of an
AI employee producing business progress.

## Observability repair

`scripts/nexus_agent_platform/builders/runtime.py` now records worker execution
truth separately:

- CLI invocation observed is reported as one observed model call;
- input/output token counts remain `null` when the adapter does not expose them;
- CLI cost provenance is not silently rewritten to `local_python`;
- deterministic local execution remains explicitly zero-token;
- invocation, reasoning-output presence, and business-state mutation evidence
  are recorded separately.

`run_builder_pilot()` now preserves the builder result's measured usage instead
of overwriting it with a zero-token claim.

`engineering_broker.run_voice_task()` now uses one canonical worker-registry
snapshot for selection and execution. This fixes the prior handoff mismatch in
which a test/registered worker could be selected in one view and appear absent
in a second probe.

These changes repair measurement and worker handoff semantics. The new
`ai.plan_and_verify` path proves a model-backed worker for selected safe
internal departments, but it is not yet a general implementation worker for
every company department.

## Objective/backlog recovery

The durable portfolio contains 23 goals. Current evidence supports:

- 7 goals with observed real bounded progress: `research.company_intelligence`,
  `trading.real_data`, `clyde.entity_readiness`, `goclear.economic_model`,
  `goclear.example_campaign`, `portal.admin_control_center`, and
  `opportunity.engine`;
- 1 Portal/Product executor available for local verification but not proven as
  a complete portal implementation loop;
- 1 Systems generic verifier available, not a full Modal/Oracle executor;
- the remaining goals remain active/ready or dependency-gated with missing
  capable department execution.

No objective was marked complete merely because a report or child receipt
exists. A queued unsupported work order remains a continuation boundary, not a
business completion claim.

## YouTube recovery

The prior company-wide audit remains the authoritative reconciliation:

- 5 recoverable YouTube metadata records;
- 5 corresponding yt-dlp metadata records;
- 0 approved transcript corpus records;
- 1 recoverable transcript-like certification artifact;
- no current evidence for an autonomous live batch of approximately 40
  transcripts routed through the canonical Research → Alpha store.

Cached metadata and NotebookLM exports are not counted as current durable
company knowledge until imported through the canonical lineage. Opportunity
rejection must remain separate from source knowledge preservation; the current
evidence does not prove the historical batch had that separation.

## Alpha rejection analysis

The current Alpha bridge is deterministic and evidence-bound. It can persist
`QUALIFIED`, `FOLLOW_UP_RESEARCH`, and `REJECTED` decisions, and its rejection
reason says to retain research evidence. It is not a proof of model reasoning.
The current Active Operator Research action does not, by itself, prove a
Research result was handed to Alpha on every cycle. That is a routing gap, not
evidence that Alpha consciously rejected every project.

## Nova executive control

Nova has verified read access to the company goal portfolio and conversational
model access. Generic writes remain denied, but a narrow governed
`assign_safe_internal_work` primitive queues only an existing eligible goal
for Active Operator pickup and derives an allowlisted action. It cannot create
arbitrary records or perform external actions.

`Write operations are not permitted. I have read-only access.`

Therefore the following remain not certified for Nova as a full autonomous
company operator:

- priority recommendation persisted into canonical goal state;
- autonomous rerouting;
- completion notification based on a completed recovery campaign.

Safe assignment and tracking of an existing Portal/Product goal through Active
Operator were proven by control request
`nova_control_4431686837894b41bf4611d02d6e0438` and its completed AI receipt.

This is an authority/control-plane capability gap, not a model-quality claim.
No arbitrary write authority was granted in this recovery.

## Real business effects

Verified effects are limited to safe internal state:

- Research performed bounded private SearXNG reads and persisted work/goal
  evidence;
- Trading acquired real OANDA Practice candles and produced backtest/OOS/
  paper feedback without live orders;
- builder proof produced isolated deterministic artifacts;
- AI-backed planning/review caused bounded internal verification and durable
  progress on four existing company goals; no production/customer mutation was
  attempted.

## Multi-cycle and restart proof

The follow-up run proved multiple canonical cycles and multiple AI-backed
departments. It still does not prove a full restart plus later AI continuation
for every lane:

- Cycle continuation: PASS for Research/Trading and bounded AI lanes;
- multi-department AI execution: PASS bounded;
- provider-worker autonomous invocation: PASS through the existing OpenRouter
  gateway; external coding-worker path remains unproven;
- restart-safe unsupported department assignment: queued work survives;
- restart-safe AI worker task/result lineage: PARTIAL; receipts are durable,
  but a dedicated restart certification remains.

## Additional safe executor recovery

The existing fixture-only `NEXUS_CREDIT_BUSINESS_FUNDING` governed loop was
connected to the canonical portfolio as `funding.readiness_review` for
`Funding` and `Funding/Product`. A direct bounded proof returned:

- loop: `NEXUS_CREDIT_BUSINESS_FUNDING`;
- final state: `SUCCEEDED_VERIFIED`;
- receipt: `reports/rebuild/nexus_loop_receipts/receipt_4c826069cd8a4b7186ba7701482afaf1.json`;
- authority: `INTERNAL_REVIEW`;
- financial transactions: `false`;
- applications submitted: `false`.

This closes one previously disconnected safe executor. It remains a fixture /
readiness analysis, not an AI-funded workflow or external financial action.

## Follow-up AI workforce recovery

The missing model-backed boundary was repaired as a bounded, allowlisted
`ai.plan_and_verify` action. It uses the existing Nova/OpenRouter gateway and
does not grant the model shell, arbitrary file, production, customer,
financial, or messaging authority. The sequence is:

`durable goal → model plan → exact allowlisted internal.capability_verify → model review → receipt → parent progress`

Real canonical Active Operator cycles then produced the following evidence
without a manually selected child action:

| Cycle | Existing objective | Department | Model evidence | Executor/result |
|---|---|---|---|---|
| `operator_ddb4113e8b8f40c5b3c6688116281505` | `clyde.entity_readiness` | Clyde | `openai/gpt-4o-mini`, planning and review usage persisted | local capability verification; goal remains ACTIVE with missing criteria |
| `operator_c7b4081ef5aa46919ad5e3f13c7cfab1` | `goclear.economic_model` | Finance/Opportunity | real planning/review calls | bounded internal verification; goal remains ACTIVE |
| `operator_0597a7c1b3914ac091cd19032eea2bf5` | `goclear.example_campaign` | Marketing/Creative | real planning/review calls | bounded internal verification; goal remains ACTIVE |
| `operator_b17c5efdc7a340a9a729d4319e01b9da` | `portal.admin_control_center` | Portal/Product | Nova-assigned request caused real planning/review calls | existing portal backend build and local-only artifacts; no production mutation |

Receipt references:

- `reports/runtime/ai_workforce_receipts/aiwf_014deca968164f2d85be5ebc2ba87845.json`
- `reports/runtime/ai_workforce_receipts/aiwf_961f2cf5ca484a2b9ba8a2eb052ba439.json`
- `reports/runtime/ai_workforce_receipts/aiwf_84f54764f14149f6b3ac253028616118.json`
- `reports/runtime/ai_workforce_receipts/aiwf_12daeb1c86784f1d881c7f472ad82251.json`
- `reports/runtime/ai_workforce_receipts/aiwf_21e27eb828c542ea8683df5d6e3cbd38.json`
- `reports/runtime/ai_workforce_receipts/aiwf_795b0a583585420792786b1347c3b5cc.json`
- `reports/runtime/ai_workforce_receipts/aiwf_7a0919aca5d1475d987f8e9bb2d3d7a9.json`

The later canonical cycles were not manually assigned child actions. Cycle
`operator_a965994710a94f1e9333a22b36d4e3d2` reloaded the portfolio, consumed
Nova request `nova_control_93916450abcf465bbc8bf81bea96d5e2`, and advanced both
`portal.admin_control_center` and `opportunity.engine`. Later cycle
`operator_3269f02473b9435ca3056d5af03ddc91` selected the Portal objective again
and produced `aiwf_7a0919aca5d1475d987f8e9bb2d3d7a9.json`, proving persisted
continuation of the same incomplete objective after the first AI result.

The AI review explicitly preserved remaining work; no parent goal was marked
complete from a child result. The first Portal/Product attempt also exposed a
real legacy import defect (`ModuleNotFoundError: common`), which was repaired
at the governed executor boundary before the successful cycle.

Nova safe control is now a narrow governed primitive, not generic write access:
`assign_safe_internal_work` validates an existing eligible goal, derives its
allowlisted action, persists a request for Active Operator, and records no
external side effect. The real request for `portal.admin_control_center`
(`nova_control_4431686837894b41bf4611d02d6e0438`) was picked up by the next
canonical cycle and completed with the receipt above.

## Proactive communication path status

The existing `scripts/nova/proactive_communications.py` is a real bounded
extension of the Nova Telegram worker, not a second worker. It resolves only
the trusted configured Ray chat, uses the existing `tg_send_message` retry
path, persists event/delivery/message state, suppresses duplicates, and is
called by the launchd Nova worker. A recovery-complete message was deliberately
not sent because this campaign remains PARTIAL; sending one would overclaim
company-wide certification. The implementation is available for the final
certification event, but real completion delivery remains unproven.

## Tests

Focused tests completed:

`36 passed`

Covered builder selection/verification, deterministic fallback, retry
behavior, engineering-worker handoff, goal continuation, the distinction
between CLI invocation evidence and zero-token local execution, model-plan /
result-review contracts, proactive-message suppression, safe Nova assignment,
and durable control-request validation.

## Nova Telegram outbound proof

No outbound completion message is claimed in this report. The existing
proactive path is now identified and wired into the Nova worker, but the
company-wide recovery has not reached a truthful terminal certification state.
Sending a completion claim now would be misleading.

## Remaining blockers

1. Extend bounded AI-backed executors to additional safe internal lanes where
   the existing artifacts support meaningful work; customer communication,
   e-sign, publication, live finance, and production mutation remain gated.
2. Connect current Research outputs to autonomous Alpha intake/evaluation on
   the same cycle, without replacing deterministic evidence checks with fake
   scores.
3. Prove multiple later cycles reloading prior AI receipts and generating the
   next bounded action without Codex intervention.
4. Send and persist the proactive completion notification only after those
   conditions are met.

These are repairable Nexus-owned engineering gaps except where provider
credentials, external service access, or consequential authority is required.

## Git

- Local prior continuation commit: `1f1e3b7c014f7a234be7521d674c987e269555df`.
- This recovery task adds the builder telemetry/worker-handoff repair, the
  bounded Funding executor connection, model-backed safe internal planning and
  review, Nova safe assignment, the proactive-parser repair, selected runtime
  receipts, and this report.
- Unrelated worktree changes remain preserved and unstaged.
- The builder/worker-handoff commit `bca402b` and bounded Funding follow-up
  commit `2dd05f8` are pushed to `origin/main`.

## Certification

`AI_WORKER_PROVIDER_PROBES=PASS_HISTORICAL`

`AUTONOMOUS_AI_PROJECT_INVOCATION=PASS_REAL_BOUNDED_PLANNING_AND_VERIFICATION; FULL_IMPLEMENTATION_NOT_PROVEN`

`REAL_AI_MODEL_INVOCATIONS=PASS_REAL_FOR_BOUNDED_INTERNAL_PLANNING_AND_REVIEW`

`REAL_OBJECTIVES_ADVANCED=clyde.entity_readiness,goclear.economic_model,goclear.example_campaign,portal.admin_control_center`

`MULTI_DEPARTMENT_AI_EXECUTION=PASS_REAL_BOUNDED`

`REGISTERED_SAFE_EXECUTOR_COVERAGE=PARTIAL`

`RESEARCH_AUTONOMOUS_EXECUTION=PASS_REAL`

`TRADING_AUTONOMOUS_EXECUTION=PASS_REAL`

`NOVA_READ_VISIBILITY=PASS_REAL`

`NOVA_ASSIGN_TRACK_REROUTE=PASS_REAL_FOR_SAFE_INTERNAL_ASSIGNMENT; REROUTE_NOT_PROVEN`

`NOVA_COMPLETION_NOTIFICATION=NOT_SENT`

`SAFE_TO_CERTIFY_COMPANY_WIDE_AI_AUTONOMY=NO`
