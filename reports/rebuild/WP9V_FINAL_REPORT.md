# WP9V Final Report

## Executive Result

WP9V is **PARTIAL** pending the genuine Telegram human test. The installed
Hermes MCP SDK cache defect was reproduced: a dead named `MCPServerTask` stayed
in `_servers`, so discovery skipped reconnect. Targeted per-server teardown and
fresh discovery now recover both MCPs without replacing the healthy peer.

## SDK Trace and Repair

Both `nexus_mcp` and `google_mcp` are Hermes-owned stdio `MCPServerTask`
connections. Normal traces showed distinct server, session, task, readiness,
and tool registrations. The stale object was reused by discovery (`YES`), and
tool wrappers remained associated with the stale registration until shutdown.
The repair invokes the existing SDK `server.shutdown()` for only the failed
named server, removes that cache entry, then performs fresh initialization and
tool registration. It is one bounded reconnect cycle.

`ASYNC_LIFECYCLE_DEFECT=PARTIAL`: the dead async/session lifecycle was not
recreated when the cached name remained, while Hermes’ background event loop
itself was healthy. `TOOL_WRAPPER_BOUND_TO_STALE_CLIENT=YES` before repair.

## Recovery Certification

Real targeted stale-client recovery passed 3/3 for `nexus_mcp` and 3/3 for
`google_mcp`. Five real model-driven Nexus recovery trials all reached fresh
registration and real tool execution; four returned user-visible final
responses. One response was blanked by the existing evidence validator after
an over-broad model continuation, so the user-visible result is 4/5.

The recovery type is `CLIENT_RECONNECT`; no external MCP process restart was
claimed. The normal peer remained configured and independently usable during
the targeted tests.

## Session and Specialist Recovery

Session `wp9v-session-recovery-1788392682` survived a real targeted MCP client
interruption, reconnect, subsequent MCP read, and Finance delegation. Finance
returned a fresh post-recovery receipt. Fresh Finance + Alpha synthesis also
completed with independent specialist outputs and reconciliation.

## Duplicate Guarantees

The targeted recovery path performs no mutation and no duplicate specialist or
user response was observed. Read-only Nexus calls are memoized per turn; model
transcript repetitions are not treated as additional external executions.

## Telegram Crossover Preparation

Existing WP9T gates remain intact: stable chat-to-session mapping, durable
offset/delivery records, replay suppression before runtime invocation,
mobile-safe response guards, failure formatting, and reversible rollback.
Telegram transport was not activated or simulated.

## Human Telegram Handoff

All non-human gates are sufficient for human certification. `TELEGRAM_CUTOVER=NO`.

`TELEGRAM_HUMAN_ACTION_REQUIRED=YES`

RAY_SEND_THIS_EXACT_MESSAGE=

> Nexus, WP9V human certification NEXUS-WP9V-7K42. Give me current system health, tell me the highest-priority item requiring my attention, and confirm whether Finance and Alpha are available.

## Tests

Focused MCP/Nova/Telegram/session tests: **18 passed**. Canonical build:
**PASS_EXIT_0**. Secret scan: **PASS**. Scheduler preserved.

## Final Status

```text
WP9V=PARTIAL
SDK_RECOVERY_FAILURE_STAGE=T2-T12_CACHED_DEAD_MCP_SERVER_SKIPPED_RECONNECT
STALE_OBJECT_REUSED=YES
STALE_OBJECT_TYPE=MCPServerTask_AND_CLIENT_SESSION
ASYNC_LIFECYCLE_DEFECT=PARTIAL
TOOL_WRAPPER_BOUND_TO_STALE_CLIENT=YES
NEXUS_MCP_TRANSPORT=STDIO
GOOGLE_MCP_TRANSPORT=STDIO
MCP_RECOVERY_TYPE=CLIENT_RECONNECT
MCP_1_NORMAL=PASS_REAL
MCP_1_RECOVERY=PASS_REAL
NEXUS_MCP_RECOVERY_RUNS=3/3
MCP_2_NORMAL=PASS_REAL
MCP_2_RECOVERY=PASS_REAL
GOOGLE_MCP_RECOVERY_RUNS=3/3
ONE_MCP_FAILURE_ISOLATED=YES
MCP_RECOVERY_RUNS=4/5
MCP_STARTUP_RECOVERY=PASS_REAL
SESSION_SURVIVES_MCP_RECOVERY=PASS_REAL
SPECIALIST_AFTER_RECOVERY=PASS_REAL
SPECIALIST_RECEIPT=nexus-delegation-155be71cba0f4965b3101b7f74d35a3c
DUPLICATE_TOOL_EXECUTION=NO
DUPLICATE_SPECIALIST_EXECUTION=NO
DUPLICATE_USER_RESPONSE=NO
FULL_TOOL_LOOP_REGRESSION=10/10
MULTI_SPECIALIST_REGRESSION=PASS_REAL
SYSTEM_DEPARTMENT_NON_TELEGRAM_RUNTIME=CLOSED
TELEGRAM_READY_FOR_HUMAN_TEST=YES
TELEGRAM_HUMAN_ACTION_REQUIRED=YES
TELEGRAM_CUTOVER=NO
WP9=RETRY_NIGHT_1
ALTERNATE_CLOUD_TEST_NEEDED=NO
```
