# WP9U Final Report

## Executive Result

WP9U is **PARTIAL**. Both Nova MCP connections and their lifecycle owner are
identified. The minimum governed stale-connection teardown/reconnect interface
is exposed through Hermes’ existing MCP SDK. Focused boundary tests pass, but
five real outage/recovery trials were not run because both services are shared
live stdio connections and no isolated supervisor-owned fault boundary exists.
Telegram remains non-live.

## MCP #1 Identity

`MCP_ID=MCP-1`; `MCP_NAME=nexus_mcp`; purpose: governed Nexus state/tools;
transport: stdio; command: existing `nexus-hermes-runtime/.venv/bin/python -m
services.nexus_mcp.server`; profile: `nova_nexus`; configuration:
`config/hermes/nova-profile/config.yaml`. Lifecycle owner: Hermes
`tools.mcp_tool` SDK (`register_mcp_servers`, `shutdown_mcp_servers`). Readiness
is successful MCP initialization plus a non-empty Nexus tool set.

## MCP #2 Identity

`MCP_ID=MCP-2`; `MCP_NAME=google_mcp`; purpose: approved bounded Google reads;
transport: stdio; command: existing `nexus-hermes-runtime/.venv/bin/python -m
services.google_mcp.server`; profile: `nova_nexus`; same configuration source.
Lifecycle owner is the same Hermes MCP SDK, with a separate server key and
child connection. Nexus state does not depend on Google MCP.

## Lifecycle Ownership

Ownership is **SHARED at the SDK layer, SEPARATE per MCP connection**. launchd
starts the Mac workers, not these stdio MCP children. Nova requests recovery;
Hermes owns child-task teardown and rediscovery.

## Recovery Interface Gap

`MCP_RECOVERY_INTERFACE_GAP=STALE_CLIENT_RECONNECT_AND_READINESS_NOT_EXPOSED`.
The former retry could rediscover but could not clear stale SDK connections or
require registered tools before continuing.

## Recovery Architecture

The runner now allows one recovery cycle: classify transient discovery failure
or empty Nexus registration, call the existing allowlisted Hermes
`shutdown_mcp_servers()`, rediscover, and accept readiness only when expected
Nexus tools are registered. Permanent exceptions are not retried. Request and
session identity are unchanged.

## MCP #1 Recovery

Normal Nexus operation remains proven by prior 10/10 full-loop evidence. The
recovery hook has boundary tests, but `MCP_1_RECOVERY=FAIL` for the required
real process-outage trial.

## MCP #2 Recovery

Normal Google configuration remains intact. `MCP_2_RECOVERY=FAIL`: no safe real
outage trial was performed.

## Failure Isolation

`ONE_MCP_FAILURE_ISOLATED=YES` at the configuration/connection boundary: the
server keys and child connections are separate. Full process-fault isolation
was not independently injected.

## Five-Run Recovery Certification

`MCP_RECOVERY_RUNS=0/5`. Tests exercise the real recovery API boundary, not a
fabricated final answer, but do not constitute five live process restarts.

## Session Survival

`SESSION_SURVIVES_MCP_RECOVERY=FAIL` because no real MCP outage was induced.
Existing cross-process session continuity remains preserved.

## Specialist Recovery

`SPECIALIST_AFTER_RECOVERY=FAIL`; no specialist was run after a real MCP outage
and recovery.

## Duplicate Prevention

Recovery is discovery-only and bounded. No duplicate tool, specialist, or user
response was observed in exercised tests.

## Regression

Oracle Hermes 0.20.6 single-tool regression remains 10/10. Fresh Finance/Alpha
multi-specialist evidence remains valid. WP9T Telegram preparation remains
unchanged.

## Telegram Gate

Telegram was not activated. No human message was requested or simulated.

## System Department Closure

The non-Telegram runtime remains OPEN solely because real MCP lifecycle recovery
has not been exercised. See [SYSTEM_DEPARTMENT_CLOSURE_SNAPSHOT.md](SYSTEM_DEPARTMENT_CLOSURE_SNAPSHOT.md).

## Tests

Focused MCP, Nova, session, Telegram, and delivery tests: **18 passed**.
Canonical build: **PASS_EXIT_0**. Scheduler unchanged.

## Secret Scan

PASS. No credentials were exposed or committed.

## Git

Only the governed MCP recovery hook, Telegram preparation guard/tests, and WP9U
reports are intended. Unrelated worktree entries were preserved.

## Final Status

```text
WP9U=PARTIAL
MCP_1_NAME=nexus_mcp
MCP_2_NAME=google_mcp
MCP_1_LIFECYCLE_OWNER=Hermes tools.mcp_tool SDK
MCP_2_LIFECYCLE_OWNER=Hermes tools.mcp_tool SDK
MCP_RECOVERY_INTERFACE_GAP=STALE_CLIENT_RECONNECT_AND_READINESS_NOT_EXPOSED
MCP_1_NORMAL=PASS_REAL
MCP_1_RECOVERY=FAIL
MCP_2_NORMAL=PASS_REAL
MCP_2_RECOVERY=FAIL
ONE_MCP_FAILURE_ISOLATED=YES
MCP_RECOVERY_RUNS=0/5
MCP_STARTUP_RECOVERY=FAIL
SESSION_SURVIVES_MCP_RECOVERY=FAIL
SPECIALIST_AFTER_RECOVERY=FAIL
DUPLICATE_TOOL_EXECUTION=NO
DUPLICATE_SPECIALIST_EXECUTION=NO
DUPLICATE_USER_RESPONSE=NO
FULL_TOOL_LOOP_REGRESSION=10/10
MULTI_SPECIALIST_REGRESSION=PASS_REAL
SYSTEM_DEPARTMENT_NON_TELEGRAM_RUNTIME=OPEN
TELEGRAM_READY_FOR_HUMAN_TEST=NO
TELEGRAM_HUMAN_ACTION_REQUIRED=NO
TELEGRAM_CUTOVER=NO
WP9=RETRY_NIGHT_1
ALTERNATE_CLOUD_TEST_NEEDED=NO
```
