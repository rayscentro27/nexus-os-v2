# Nexus Continuous Operating Kernel R1.1 Closure

## Executive Result

The three R1 blockers were closed without creating a second Research scheduler.
The existing `com.nexus.continuous-loop` launchd label is now the durable owner
of the kernel, running the bounded daemon runner with a 1200-second cycle
interval and KeepAlive recovery. Stale knowledge now has a context-sensitive
policy over the canonical Alpha content/claim store, and the paper-only Trading
loop routes every backtest weakness into Research/Alpha and a bounded variant
retest. No live trading, external publishing, outreach, spending, or Telegram
change was performed.

## Durable Research Owner

`com.nexus.continuous-loop` owns durable Research wake execution. Its runner is
`scripts/ops/run_with_nexus_runtime_env.sh` → the existing agent-platform
Python → `scripts/run_continuous_operating_kernel.py --daemon
--interval-seconds 1200`. This preserves one owner and one Research heartbeat;
the prior `phase15.run_all` launchd target was a one-shot batch entry point, not
a second scheduler.

## Supervisor Root Cause

The prior launchd definition invoked `nexus_agent_platform.phase15.run_all`.
Its Phase 15 child capability path attempted to execute `npm`, but launchd's
default PATH was `/usr/bin:/bin:/usr/sbin:/sbin`; the recorded scheduler health
error was `[Errno 2] No such file or directory: 'npm'`, with exit code 1.
This was a dependency/entry-point failure, not a Research objective blocker.

## Supervisor Repair

The same launchd label was changed to the already-built kernel runner. The
runner gained explicit bounded daemon and interval arguments, persists a next
wake, and keeps the Research state `IDLE_BETWEEN_CYCLES` rather than stopped.
The temporary 30-second certification interval was removed; the live plist is
restored to 1200 seconds. The launchd service is currently loaded and running
with KeepAlive and one active PID.

## Real Scheduled Wake Proof

With the existing launchd owner, a clean certification run recorded:

| Evidence | Result |
|---|---|
| launchd service | `state=running`, `active count=1`, `KeepAlive`, one PID |
| automatic cycle A | `kernel_cycle_1`, `scheduler=ACTIVE_DAEMON`, `result_status=PASS` |
| automatic cycle B | `kernel_cycle_2`, `scheduler=ACTIVE_DAEMON`, `result_status=PASS` |
| next wake | persisted after each cycle |
| manual task creation | none; only the launchd service was bootstrapped |

## Worker Exit Recovery

The managed kernel process was safely terminated by PID during the bounded
certification. KeepAlive restarted the same launchd label from PID 12890 to PID
12942; the replacement wrote a fresh `ACTIVE_DAEMON` PASS heartbeat and retained
the next wake. Persisted program/source state was not removed.

## Stale Knowledge Refresh

Added `knowledge_freshness.py` over existing `alpha_content` and `alpha_claims`
records. Missing timestamps become `WAITING_SOURCE`, not fresh or zero age.
Policies are context-sensitive: general 30 days, software 7 days, market 2
days, SEO 3 days, funding 7 days, trading 1 day, and historical 3650 days.

A real MCP specification record was evaluated at a future policy time and
classified `STALE`. `refresh_once()` retrieved the public source, persisted
fresh content/claim lineage, and wrote refresh receipt
`refresh_a93fbd27b96ba819048f`, changing the refresh evidence to `FRESH`.
The scheduled runner now checks due canonical content and performs at most one
bounded refresh per cycle before normal Alpha research.

## Trading Research / Backtest Feedback

The existing `nexus_sma_cross_v1` OANDA Practice path was run for real. It
returned a bounded `REJECT` decision with three out-of-sample trades and
negative expectancy. Instead of terminating the objective, the loop persisted
feedback `trading_feedback_a270b7f19f3e4f35819981b67405ecb3`, created a fresh
Alpha research work order, retained `parent_objective_open=true`, and executed
a second bounded fast=8/slow=30 variant retest. The parent remains open for
research. `authority_denial=true` confirms live trading remained unavailable;
paper-only safety is intact.

## Empty Queue Regression

The existing kernel/Active Operator contract remains intact: empty immediate
work selects `CONTINUE_INCOMPLETE_OBJECTIVE` or the next due research action,
persists a heartbeat, and retains a next wake. `research_operational_state.py`
now observes the canonical continuous-loop owner instead of a nonexistent
dedicated Research worker label.

## Alpha Feedback Regression

Focused and prior live evidence remain valid: weak Alpha evidence creates a
bounded targeted follow-up, and rejected branches keep their parent objective
open. The scheduler and freshness changes do not alter specialist semantics.

## Multi-Wake Evidence

The launchd-owned daemon produced two automatic cycles, then recovered after a
managed process exit, and was finally reloaded with the production 1200-second
interval. Current state is `RESEARCH_ENABLED=YES`, `RESEARCH_HEARTBEAT=ACTIVE`,
`RESEARCH_SCHEDULER=ACTIVE_DAEMON`, `RESEARCH_WORKER_STATE=IDLE_BETWEEN_CYCLES`.

## Current Research State

The canonical runtime reports an active durable owner, an enabled heartbeat,
idle-between-cycles worker state, and next action `CONTINUE_INCOMPLETE_OBJECTIVE`.
Idle means yielding between scheduled cycles; it is not unavailable or stopped.

## Overnight Readiness

The required non-Telegram readiness gates are satisfied by this closure:
durable owner active, real scheduled wakes, worker-exit recovery, stale refresh,
Trading feedback, prior Alpha feedback, empty-queue continuation, resource
yield/resume, watchdog recovery, and previous kernel ownership/regression proofs.
No Telegram cutover was changed by this package.

## True Ray Blockers

None. Live Trading remains intentionally disabled by governance, which is not a
blocker to bounded paper/backtest Research operation.

## Safety

Only public read research and OANDA Practice data were used. No client PII,
secrets, live orders, external publishing, outreach, or financial transaction
was performed. Focused secret-pattern validation remained clean.

## Git

START_HEAD=`9b9a802ccc485e708963089a25b199549456f651`.
Unrelated worktree entries were preserved; task files were edited explicitly.
The live launchd plist is an external user configuration and is documented
above; it is not staged as repository content.

## Final Status

`CONTINUOUS_KERNEL_R1_1=PASS`; `RESEARCH_READY_FOR_OVERNIGHT_LOOP=YES` and
`NEXUS_READY_FOR_BOUNDED_OVERNIGHT_OPERATION=YES`, subject to the existing
bounded safety policy and no live Trading authority.
