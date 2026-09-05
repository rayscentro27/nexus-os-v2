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

The existing workforce certification proves provider probes and bounded worker
availability, not current company execution:

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

These changes repair measurement and worker handoff semantics. They do not
pretend that an AI worker has been activated for every company department.

## Objective/backlog recovery

The durable portfolio contains 23 goals. Current evidence supports:

- 2 goals with observed real bounded progress: `research.company_intelligence`
  and `trading.real_data`;
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
model access. It can create governed work orders through existing Telegram
approval flows, but the current pre-model capability gate explicitly denies
generic writes:

`Write operations are not permitted. I have read-only access.`

Therefore the following are not certified for Nova as an autonomous company
operator:

- direct safe objective creation;
- department assignment;
- priority recommendation persisted into canonical goal state;
- autonomous rerouting;
- tracking a newly assigned work item through execution;
- completion notification based on a completed recovery campaign.

This is an authority/control-plane capability gap, not a model-quality claim.
No new write authority was granted in this recovery because the existing
governed approval path and exact authority envelope need to be reused rather
than bypassed.

## Real business effects

Verified effects are limited to safe internal state:

- Research performed bounded private SearXNG reads and persisted work/goal
  evidence;
- Trading acquired real OANDA Practice candles and produced backtest/OOS/
  paper feedback without live orders;
- builder proof produced isolated deterministic artifacts;
- no current evidence proves an AI-generated implementation was applied to an
  active company project by the unattended operator.

## Multi-cycle and restart proof

The prior run proved repeated canonical cycles and restart-safe JSON state for
Research and Trading. It did not prove a multi-department AI-worker cycle:

- Cycle continuation: PASS for Research/Trading;
- multi-department AI execution: NOT PROVEN;
- provider-worker autonomous invocation: NOT PROVEN;
- restart-safe unsupported department assignment: queued work survives;
- restart-safe AI worker task/result lineage: NOT PROVEN for a current company
  objective.

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

## Tests

Focused tests completed:

`25 passed`

Covered builder selection/verification, deterministic fallback, retry
behavior, engineering-worker handoff, goal continuation, and the new
distinction between CLI invocation evidence and zero-token local execution.

## Nova Telegram outbound proof

No new outbound completion message is claimed in this report. A repository
search did not find a certified proactive Nova sender in the current tracked
AI-worker/control path; the existing Telegram runtime is primarily inbound /
reply-oriented and governed work-order creation remains approval-mediated.
Sending a completion claim before Nova write/control and outbound delivery are
certified would be misleading.

## Remaining blockers

1. Register and verify safe department executors for the incomplete portfolio
   goals, continuing with Portal/Product, Systems, and Marketing/Creative
   internal-only paths; Funding's existing fixture executor is now connected.
2. Add a governed AI-worker invocation contract to the canonical operator:
   context → structured decision → executor → result → AI review → next action.
3. Connect current Research outputs to autonomous Alpha intake/evaluation on
   the same cycle, without replacing deterministic evidence checks with fake
   scores.
4. Extend Nova's existing governed control path for safe internal goal/work
   assignment; do not convert the current read-only denial into arbitrary
   writes.
5. Reuse or certify the existing proactive Telegram path before sending a
   recovery-complete message.

These are repairable Nexus-owned engineering gaps except where provider
credentials, external service access, or consequential authority is required.

## Git

- Local prior continuation commit: `1f1e3b7c014f7a234be7521d674c987e269555df`.
- This recovery task adds the builder telemetry/worker-handoff repair, the
  bounded Funding executor connection, its receipt, and this report.
- Unrelated worktree changes remain preserved and unstaged.
- The builder/worker-handoff commit was pushed as `bca402b`; the bounded
  Funding follow-up is staged for the next task-specific commit.

## Certification

`AI_WORKER_PROVIDER_PROBES=PASS_HISTORICAL`

`AUTONOMOUS_AI_PROJECT_INVOCATION=NOT_PROVEN`

`REGISTERED_SAFE_EXECUTOR_COVERAGE=PARTIAL`

`RESEARCH_AUTONOMOUS_EXECUTION=PASS_REAL`

`TRADING_AUTONOMOUS_EXECUTION=PASS_REAL`

`NOVA_READ_VISIBILITY=PASS_REAL`

`NOVA_ASSIGN_TRACK_REROUTE=NOT_PROVEN`

`NOVA_COMPLETION_NOTIFICATION=NOT_SENT`

`SAFE_TO_CERTIFY_COMPANY_WIDE_AI_AUTONOMY=NO`
