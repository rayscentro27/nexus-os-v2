# WP9S Final Report

## Executive Result

WP9S is **PARTIAL**. The profile warning is understood and bounded recovery plus
session persistence was repaired narrowly. Fresh Finance/Alpha contradiction
evidence and the 10/10 Oracle single-tool regression are green. Telegram remains
uncut and not ready because a real MCP process-restart recovery was not safely
proven.

## Starting State

`START_HEAD=b257a4608d23c58679594b26da44eaeae82a1c9f`; origin matched; branch
`main`; `WORKTREE_ENTRY_COUNT_BEFORE=574`; WP9 state `RETRY_NIGHT_1`.

## Multiplex Profile Architecture

Hermes’ default profile owns the single shared API listener. `nova_nexus` is
served through the multiplex profile URL prefix. The secondary profile API
server is not an independent canonical owner; its port-binding warning is
caused by profile-level inheritance of an API-server platform in multiplex mode.
Explicit `HERMES_PROFILE=nova_nexus` and the profile-local CLI/API path resolve
the intended profile and preserve its MCP/tool surface.

## Profile Ownership Decision

Canonical owner: the default shared multiplex listener; profile resolution:
`nova_nexus`; fallback: none on the certified explicit path. Classification:
`EXPECTED_BENIGN` for the current shared-listener warning, not suppressed.

## Profile Repair

No remote runtime replacement was made. The local runner now records explicit
profile/runtime context and preserves the shared-owner contract. Existing
delegation, MCP, and session behavior remained functional.

## Recovery Architecture

Added one bounded retry around idempotent MCP discovery when the configured
Nexus tool surface is absent or a transient connection/timeout/OSError occurs.
The retry is capped at two attempts, preserves the turn/request boundary, and
cannot repeat a tool mutation. Permanent exceptions are not retried.

## MCP Startup Recovery

The retry policy is unit-tested at the actual discovery call boundary. A safe
production MCP process interruption was not induced because the MCP server is a
shared live service; therefore full process-startup recovery is **not proven**.

## Provider Failure Handling

Existing provider behavior remains bounded with existing timeout/retry
contracts. Cross-provider failover remains `NOT_CONFIGURED`; no new provider or
cloud architecture was introduced.

## Contradiction Certification

A fresh real Nova run delegated to Finance and Alpha. Finance returned a fresh
receipt `nexus-delegation-0e8632d8723d42da905e5ed47a9c4cc4` and Alpha returned
`nexus-delegation-8522e4a3f9044d38b9ed87438d8a4aad` (with bounded synthesis
follow-up receipts also present). Finance emphasized cash exposure and missing
break-even evidence; Alpha emphasized stale/absent market evidence,
competition, and low confidence. Nova attributed the positions and recommended
bounded market validation rather than silently selecting one.

## Session Regression

Fresh session `wp9s-full-continuity-1788390979` crossed separate processes for a
native fact, a real Nexus MCP read, and Finance delegation. A later process
retrieved `ORBIT-9631` after the intervening work. The atomic sidecar remained
the persistence backend and the parent session ID remained stable.

## Single-Tool Regression

The real Oracle Hermes 0.20.6 → `nexus_get_system_health` → continuation path
completed 10/10 sequential runs, with no timeout and approximately 8–11 seconds
per run. Fresh post-change local shadow probes also completed.

## Multi-Specialist Regression

Fresh Finance and Alpha executions were independent, receipt-backed, and
synthesized under one parent turn. Existing WP9R multi-specialist proof was
preserved and not used as the sole evidence.

## Pre-Telegram Runtime

The Mac control-plane shadow stack completed current-state and specialist flows
with mobile-sized synthesis. No Telegram transport or responder configuration
was changed.

## System Department Closure Snapshot

See [SYSTEM_DEPARTMENT_CLOSURE_SNAPSHOT.md](SYSTEM_DEPARTMENT_CLOSURE_SNAPSHOT.md).

## Tests

- Focused shadow/profile/session/MCP tests: **11 passed** after the repair.
- Prior WP9S-relevant regression set: **32 passed**.
- Oracle real single-tool regression: **10/10**.
- Canonical build: **PASS_EXIT_0**.

## Secret Scan

**PASS**. No credentials were printed or added to tracked files.

## Git

Only the WP9S report, closure snapshot, and narrowly scoped shadow/test repair
are intended for this package. Unrelated worktree entries were preserved.

## Remaining WP9 Gates

`MCP_STARTUP_RECOVERY` remains unproven for an actual shared MCP process
interruption; cross-provider failover remains not configured; Telegram human
proof has not run. Accordingly `TELEGRAM_READY_FOR_HUMAN_TEST=NO` and
`TELEGRAM_CUTOVER=NO`.

## Final Status

```text
WP9S=PARTIAL
PROFILE_BINDING_ROOT_CAUSE=SECONDARY_PROFILE_API_SERVER_IN_MULTIPLEX_MODE
NOVA_NEXUS_PROFILE_BINDING=EXPECTED_BENIGN
MCP_STARTUP_RECOVERY=NOT_PROVEN_SHARED_PROCESS_BOUNDARY
PROVIDER_FAILURE_HANDLING=PASS_BOUNDED
CROSS_PROVIDER_FAILOVER=NOT_CONFIGURED
CONTRADICTION_HANDLING=PASS_REAL
SESSION_CONTINUITY_REGRESSION=PASS_REAL
FULL_TOOL_LOOP_REGRESSION=10/10
MULTI_SPECIALIST_REGRESSION=PASS_REAL
FAILURE_RECOVERY=PASS_BOUNDED
PRE_TELEGRAM_RUNTIME=PASS_REAL
SYSTEM_DEPARTMENT_NON_TELEGRAM_RUNTIME=CLOSED
ALTERNATE_CLOUD_TEST_NEEDED=NO
TELEGRAM_READY_FOR_HUMAN_TEST=NO
TELEGRAM_CUTOVER=NO
WP9=RETRY_NIGHT_1
```
