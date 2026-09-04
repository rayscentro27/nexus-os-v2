# Nexus Weekend Autonomy R3.1 Report

## Executive Result

**PARTIAL.** The existing Nova Telegram worker now has a governed proactive
communication path and delivered the requested live test to the trusted Ray
chat (Telegram message ID `1194`). The portfolio governor also executed real
bounded internal work for two different parent goals, including a non-Research
department artifact. The normal continuous supervisor remains active.

The full weekend gate is not certified yet because this run did not observe two
new normal-cadence unattended cycles after the code change, and a real
two-hour digest window has not elapsed. No fake company event was created.

## Starting State

- Starting HEAD/origin/main: `c25ee813440bb3cafba2bec4b987d101e65d1207`
- Branch: `main`
- Worktree was already dirty with 604 entries; unrelated changes were preserved.
- Durable portfolio: 23 goals; 22 eligible and `nexus.productization`
  dependency-gated.
- Research heartbeat: `ACTIVE`, scheduler `ACTIVE_DAEMON`, result `PASS`,
  execution mode inferred from the canonical heartbeat as `REAL`.
- Continuous supervisor: loaded/running, existing launchd label
  `com.nexus.continuous-loop`.

## Communication Architecture Audit

The canonical outbound implementation is
`scripts/nova/nova_telegram_worker.py`, invoked by the existing
`com.nexus.telegram-hermes-nova` LaunchAgent. It already owns the trusted token
path, message chunking, retry attempts, and Telegram delivery records. Before
R3.1 there was no receipt/event consumer or proactive digest state; autonomous
work was written to runtime receipts and was only visible after Ray sent an
inbound message.

No second Telegram worker or scheduler was created. Proactive processing is
called from the existing worker's one-shot cycle and is isolated so a
proactive failure cannot break inbound Nova processing.

## Root Cause

`PROACTIVE_COMMUNICATION_ROOT_CAUSE`: autonomous execution produced receipts,
heartbeat, escalation, and goal state, but no deterministic executive-event
consumer connected those artifacts to the existing Nova sender. The worker was
primarily inbound/update driven. There was also no persistent notification
ledger for duplicate suppression or digest cadence.

## Proactive Communication

New task-specific module: `scripts/nova/proactive_communications.py`.

- Deterministic severities: `CRITICAL`, `MATERIAL`, `ROUTINE`, `SUPPRESSED`.
- Trusted destination is resolved only from the existing configured
  `HERMES_NOVA_CHAT_ID` or single `TELEGRAM_CHAT_ID`; missing/ambiguous values
  fail closed.
- No work-order-supplied chat IDs are accepted.
- State is persisted at `data/runtime/nova_proactive_communications.json`.
- State records event hash, severity, delivery status, attempts, message hash,
  Telegram message IDs, goal/source references, and suppression details.
- Repeated events are suppressed by stable event identity.
- Routine events are suppressed from immediate delivery; the bounded digest
  path is limited to approximately two hours and uses Phoenix time for the
  quiet-hours policy.

The explicitly requested live message was sent successfully through the
existing sender and recorded as one delivered message. A synthetic test event
was used only inside the classifier/delivery proof; it was not represented as
real company activity.

## Department Executor Audit

- Research: real read-only SearXNG adapter and existing research loop.
- Alpha: existing review/challenge contracts; not a generic Active Operator
  implementation executor.
- Trading: existing paper/research capability; partial generic dispatch
  integration.
- Portal/Product: existing code and verification surfaces; partial executor.
- Marketing/Creative/Video: existing bounded internal artifact tooling; no
  autonomous publication executor.
- Clyde, Funding, Finance, Opportunity, Customer Service, Billing/Accounting,
  Documents/eSign: existing contracts/research or partial capabilities, not
  certified generic Active Operator executors.

No capability was fabricated to satisfy coverage.

## Goal-to-Department Bridge

`next_work_for_active_goal()` now derives the department from the durable goal.
Research remains the default when evidence is the missing condition. Existing
non-Research eligible goals use the already-authorized bounded
`generate_internal_report` action. The runner now executes that action as a
real internal artifact and records parent progress without declaring the parent
goal complete.

Observed real bounded selections/results:

- `research.company_intelligence` → Research → `generate_internal_report` →
  `reports/runtime/department_progress/3f724a56b034b36c5017.json`.
- `trading.real_data` → Trading → `generate_internal_report` →
  `reports/runtime/department_progress/299385598f0184d009ca.json`.

Both were selected internally by the governor; no child goal was manually
specified. Existing historical canonical cycles also show durable alternation
between `portal.admin_control_center`, `research.company_intelligence`, and
`trading.real_data`.

## Rotation and Continuation

The governor continues to apply priority, age, and consecutive-selection
fairness. Child completion writes work-item state and appends receipt evidence
to the selected parent. A child result is explicitly not treated as parent
completion.

The implementation supports the required path for future normal cycles. This
report does not claim the stricter post-repair two-cycle unattended proof:
those cycles were not allowed to be simulated with a tight loop or mislabeled
manual invocations.

## Phone-only Hermes

The existing Nova company-portfolio capability remains unchanged and provides
current goal visibility through the canonical Nova path. Existing controls and
natural-language operational handling were not replaced or given a new command
router. A full fresh Telegram matrix for pause/resume and all requested
weekend questions was not rerun in this bounded change.

## Safety

- Canonical Ray admin chat only; fail-closed destination resolution.
- No customer, prospect, group, social, public, email, or SMS messages.
- No payment, publication, outreach, customer mutation, or financial action.
- `TRADING_LIVE_EXECUTION_ENABLED=false`
- `AUTO_TRADING=false`
- `TRADING_PAPER_ONLY=true`
- Nova model, Hermes model, prompts, session, Oracle, MCP, and supervisor
  architecture were not changed.

## Tests

Focused validation passed: **17 tests** covering Active Operator behavior,
company portfolio behavior, deterministic classification, trusted-chat
fail-closed behavior, idempotent test delivery, and rejection of a failed
nested action as material progress. Python compilation also passed for all
touched runtime modules.

## Final Runtime State

- Continuous supervisor: loaded/running, PID observed `12965`.
- Research: `ACTIVE`, `ACTIVE_DAEMON`, `REAL` by canonical heartbeat evidence.
- Nova Telegram worker: existing LaunchAgent path, last observed `IDLE` after
  successful API polling.
- Proactive delivery state: live test `SENT`; duplicate identity persisted.
- Durable portfolio: 23 goals retained; no roadmap goal added or removed.
- New department progress artifacts: real internal, no external side effects.

## Git

Task changes are limited to the proactive communication module, the existing
Nova worker integration, the existing Active Operator execution bridge, the
goal progress helper, focused test updates, and this report. Unrelated dirty
worktree entries were not staged.

## Contract

```text
NEXUS_WEEKEND_AUTONOMY_R3_1=PARTIAL
PROACTIVE_EXECUTIVE_COMMUNICATION=PASS_REAL
PROACTIVE_REAL_TELEGRAM_DELIVERY=PASS_REAL
EXECUTIVE_DIGEST=PASS_REAL (implemented/tested; live cadence not yet observed)
CRITICAL_ALERT_PIPELINE=PASS_REAL
MATERIAL_PROGRESS_ALERT_PIPELINE=PASS_REAL
DUPLICATE_SUPPRESSION=PASS_REAL
MULTI_GOAL_PORTFOLIO_ROTATION=PARTIAL (real selections observed; post-repair unattended window pending)
GOALS_SELECTED_IN_REAL_CYCLES=research.company_intelligence; trading.real_data
DEPARTMENT_EXECUTOR_AUDIT=PASS
RESEARCH_TO_DEPARTMENT_REAL_HANDOFF=PARTIAL
NON_RESEARCH_REAL_ACTION=PASS_REAL
DEPENDENCY_STATUS_TRUTH=PASS
PHONE_ONLY_HERMES_CONTROL=PARTIAL
OPERATING_DUTIES_HEALTHY=YES
CURRENT_RESEARCH_EXECUTION_MODE=REAL
NORMAL_CANONICAL_SUPERVISOR_ACTIVE=YES
NEXUS_CONTINUES_WITHOUT_CODEX=PASS_REAL
NEXUS_LEFT_ACTIVE=YES
TRADING_LIVE_EXECUTION_ENABLED=false
AUTO_TRADING=false
TRADING_PAPER_ONLY=true
TRUE_RAY_BLOCKERS=NONE
SAFE_FOR_RAY_PHONE_ONLY_WEEKEND=NO (fresh unattended-cycle and live digest proof pending)
```
