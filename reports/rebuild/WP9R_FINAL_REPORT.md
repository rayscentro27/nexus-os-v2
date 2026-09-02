# WP9R Final Report

## Executive Result

`WP9R=PARTIAL`. The canonical Mac-side Nova shadow session passed process
boundary continuity, and fresh Finance/Alpha delegations plus a same-parent
two-specialist request produced real MCP delegation results. The Oracle
multiplex warning remains unresolved as a warning, and no supported failover
architecture was exercised. Telegram was not changed.

## Starting State

START_HEAD=`161762668367a5d3ddfdc2b65684656945512694`
ORIGIN_MAIN_HEAD=`161762668367a5d3ddfdc2b65684656945512694`
BRANCH=`main`
WORKTREE_ENTRY_COUNT_BEFORE=574
WP9_CERTIFICATION_STATE_BEFORE=`RETRY_NIGHT_1`

The scheduler, Oracle container, tunnel, Telegram transport, and unrelated
dirty worktree entries were preserved.

## Session Architecture

The selected control-plane architecture is Mac-owned session state. The Nova
shadow runner derives a stable caller-supplied session ID, stores bounded
conversation/evidence state in
`data/runtime/nova_hermes_shadow_sessions/<session>.json`, and atomically
replaces the file with fsync plus rename. Each short-lived Hermes process loads
that sidecar before constructing model context. Specialist results are linked
to the parent turn/session and are not allowed to replace the parent identity.

The Oracle CLI uses Hermes' own SQLite session store, but unnamed `--continue`
and the tested named continuation created separate CLI sessions. It is not the
canonical Nexus Telegram session owner.

## Session Failure Boundary

`SESSION_FAILURE_BOUNDARY=ORACLE_CLI_CONTINUE_SESSION_SELECTION`. The Oracle
session database can persist records, but the tested CLI continuation semantics
did not select the original session. The Mac Nexus shadow sidecar is the
working persistence adapter for the control-plane session contract.

## Profile Binding Root Cause

Oracle startup logs say `nova_nexus` is skipped as a secondary API profile
because multiplex mode gives the shared listener to the default profile. The
Nova profile is still explicitly selected by `HERMES_HOME`/`HERMES_PROFILE` for
CLI execution and the profile carries the intended model and MCP configuration.
The warning is therefore not shown to block the proven explicit CLI path, but
canonical API ownership is not clean.

`PROFILE_BINDING_ROOT_CAUSE=SECONDARY_PROFILE_API_SERVER_IN_MULTIPLEX_MODE`.
`NOVA_NEXUS_PROFILE_BINDING=UNRESOLVED_WARNING`.

## Specialist Delegation Trace

The Mac shadow path model-selected `mcp_nexus_mcp_nexus_delegate_specialist`.
Fresh individual proof produced:

- Finance: `nexus-delegation-e24cceaebab44afe9b3e2a3944c9765e`.
- Alpha: `nexus-delegation-470fb39fb74d46fa936b5e451738577c`.

The combined same-session request produced two additional child executions:

- Finance: `nexus-delegation-65b890c2f6ad4f94b781cdbd559dee55`.
- Alpha: `nexus-delegation-01bb4519fcd841c0a313c35fa9e23bb0`.

Both returned structured live-governed results. The final synthesis compared
the results and concluded that no current no-new-spend opportunity was
actionable. The child calls were model-driven through the shadow tool surface,
not direct scripted specialist invocation.

## Common Root Cause Analysis

`COMMON_ROOT_CAUSE=PARTIAL`. The Oracle profile/multiplex boundary and Oracle
CLI session selection are related runtime identity problems, but the Mac shadow
sidecar independently provides stable session continuity and specialist
linkage. The specialist boundary itself works on the canonical Mac path.

## Repairs

No speculative production repair was made. Existing Mac persistence was
verified as the canonical session mechanism. Oracle profile warning and CLI
session selection require a narrower runtime configuration change before any
Oracle API promotion; changing them during this package without a safe rollback
would risk the proven worker.

## Finance Proof

`FINANCE_DELEGATION=PASS_REAL`.
Fresh receipt: `nexus-delegation-e24cceaebab44afe9b3e2a3944c9765e`.
The result was a live-governed, partial Finance assessment with current
system/opportunity evidence.

## Alpha Proof

`ALPHA_DELEGATION=PASS_REAL`.
Fresh receipt: `nexus-delegation-470fb39fb74d46fa936b5e451738577c`.
The result was a live-governed Alpha opportunity/research assessment.

## Multi-Specialist Proof

`MULTI_SPECIALIST_REASONING=PASS_REAL`.
The combined request produced fresh Finance and Alpha receipts under the same
session and returned a synthesis based on both. A second contradiction-focused
follow-up was cancelled after MCP startup exceeded the bounded test window;
that cancellation is not counted as a successful contradiction test.

## Contradiction Handling

`CONTRADICTION_HANDLING=NOT_RUN`. The two returned specialist results differed
in status and evidence shape, but the synthesis did not clearly identify a
material disagreement. The bounded follow-up timed out during MCP startup, so
no stronger claim is made.

## Session Continuity Certification

`SESSION_CONTINUITY=PASS_REAL` for the canonical Mac control-plane session.
Session ID: `wp9r-certification-7q`.

One process stored `HELIOS-MAC-7Q` and `18427`; a separate process using the
same session ID recovered both exact values. A subsequent MCP state read and
Finance/Alpha delegation retained the same session ID. The sidecar contained
three persisted turns after the tests. This proves conversation continuity,
not that all durable executive memory is externalized to Oracle.

## Single-Tool Regression

The WP9Q native Oracle single-tool evidence remains valid at 10/10 and was not
re-run unnecessarily. The Mac shadow continuity tests passed 32 focused
regression tests covering persistence and Nova context behavior.

## Failure Recovery

`FAILURE_RECOVERY=NOT_SUPPORTED` for a complete specialist/provider failover
contract. The bounded contradiction test was cancelled safely and left no
claimed success. No duplicate production mutation was observed.

`CROSS_PROVIDER_FAILOVER=NOT_CONFIGURED`.

## Telegram Readiness

`TELEGRAM_READY_FOR_HUMAN_TEST=NO`. Full contradiction proof, Oracle profile
canonicality, and bounded recovery remain incomplete. `TELEGRAM_CUTOVER=NO`.

## Tests

- Persistence, shadow, context, and session tests: `32 passed`.
- Canonical build: `PASS_EXIT_0`.
- Fresh Finance and Alpha delegations: real structured results and receipts.
- Same-parent two-specialist request: real Finance and Alpha child receipts.
- Scheduler state remained `RETRY_NIGHT_1`.

## Secret Scan

`PASS`; no secret values were printed or written.

## Git

Only this WP9R report is intended for commit. Existing unrelated worktree
entries were preserved.

START_HEAD=`161762668367a5d3ddfdc2b65684656945512694`
END_HEAD=`RECORDED_AFTER_PUSH`
FINAL_ORIGIN_MAIN_HEAD=`RECORDED_AFTER_PUSH`
PUSHED=`YES`
WORKTREE_ENTRY_COUNT_AFTER=574
UNRELATED_EXISTING_CHANGES_PRESERVED=YES

## Remaining WP9 Gates

- Cleanly resolve or classify Oracle `nova_nexus` profile binding.
- Run a bounded contradiction case that completes and proves reconciliation.
- Implement/prove supported failure recovery and provider/host failover.
- Keep Telegram cutover and human-originated proof deferred.

## Final Status

WP9R=PARTIAL
SESSION_FAILURE_BOUNDARY=ORACLE_CLI_CONTINUE_SESSION_SELECTION
PROFILE_BINDING_ROOT_CAUSE=SECONDARY_PROFILE_API_SERVER_IN_MULTIPLEX_MODE
COMMON_ROOT_CAUSE=PARTIAL
NOVA_NEXUS_PROFILE_BINDING=UNRESOLVED_WARNING
FINANCE_DELEGATION=PASS_REAL
FINANCE_RECEIPT=nexus-delegation-e24cceaebab44afe9b3e2a3944c9765e
ALPHA_DELEGATION=PASS_REAL
ALPHA_RECEIPT=nexus-delegation-470fb39fb74d46fa936b5e451738577c
MULTI_SPECIALIST_REASONING=PASS_REAL
CONTRADICTION_HANDLING=NOT_RUN
SESSION_CONTINUITY=PASS_REAL
FULL_TOOL_LOOP_REGRESSION=10/10_REUSED_WP9Q
FAILURE_RECOVERY=NOT_SUPPORTED
CROSS_PROVIDER_FAILOVER=NOT_CONFIGURED
ALTERNATE_CLOUD_TEST_NEEDED=NO
TELEGRAM_READY_FOR_HUMAN_TEST=NO
TELEGRAM_CUTOVER=NO
WP9=RETRY_NIGHT_1
