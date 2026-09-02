# WP9Q Final Report

## Executive Result

`WP9Q=PARTIAL`. The native Hermes CLI path completed a real MCP-backed loop
10/10, including model response, `nexus_get_system_health`, MCP execution,
tool result, and final synthesis. However, the Oracle API profile still emits a
multiplex/profile-binding warning, the fresh two-specialist request produced no
verifiable delegation receipts, and persistent session continuity failed.
Telegram was not activated.

## Starting State

START_HEAD=`8a3150d611d923d2b4f0d3bad7a665e66cc4e7af`
ORIGIN_MAIN_HEAD=`8a3150d611d923d2b4f0d3bad7a665e66cc4e7af`
BRANCH=`main`
WORKTREE_ENTRY_COUNT_BEFORE=574
WP9_CERTIFICATION_STATE_BEFORE=`RETRY_NIGHT_1`

The existing dirty worktree was preserved. No scheduler, Telegram consumer, or
cloud infrastructure was changed.

## Profile-Binding Warning Root Cause

Oracle container logs report: `Skipping secondary profile 'nova_nexus' due to
port-binding config error` while `multiplex_profiles` is enabled. The default
profile owns the shared listener and the Nova profile is intended to be
addressed through `/p/nova_nexus/`. The profile config contains the Nova model
and Nexus MCP configuration, and the profile-routed API endpoint responds, but
the warning means canonical API profile ownership is not clean.

Classification: `PROFILE_BINDING_WARNING=POTENTIALLY_CAUSAL`. It was not
suppressed or changed speculatively.

## Runtime Profile Proof

The real CLI invocation ran with `HERMES_HOME=/opt/data/profiles/nova_nexus`
and `HERMES_PROFILE=nova_nexus`, Hermes 0.20.6, OpenRouter, and
`openai/gpt-4o-mini`. Session/request artifacts and the Nova profile system
content identify the active profile. The explicit CLI toolset was
`nexus_mcp_remote`; the final response reported live system-health data.

`RUNTIME_PROFILE_PROVEN=YES` for the CLI path. The profile-routed API path is
not equivalent: a direct API request emitted no tool call and asked for code
approval, so it is not used as full-loop evidence.

## Selected Certification Tool

`nexus_get_system_health` was selected because it is read-only, current-state
oriented, machine-verifiable, and has no external mutation.

## Full Tool-Loop Trace

One bounded CLI trace succeeded:

`T0 CLI accepted → T1 gpt-4o-mini invoked → T2 read-only Nexus tool selected
→ T3/T4 MCP tool executed → T5 structured health result returned → T6 result
available to Hermes → T7 continuation completed → T8 final synthesis → T9
process exit 0.`

Observed final synthesis included the returned `DEGRADED` system-health state,
active/degraded/failed service counts, and telemetry warning. The tool was not
invoked directly by the certification harness.

`FULL_TOOL_LOOP_SINGLE_TRACE=PASS_REAL`.

## Failure Boundary Analysis

The fresh two-specialist run is not a pass. Hermes logs show repeated invalid
`tool_call` use for a non-deferrable MCP tool and approval errors for
`execute_code`; no fresh delegation manifest or receipt was found. The
boundary is `MODEL/TOOL DISPATCH SEMANTICS`, not MCP transport availability.

The continuity failure is separate: `--continue` resumed an unrelated session
and did not retrieve the unique fact from the preceding process.

## Repair

No code or remote configuration repair was made. The single-tool loop already
passed 10/10, and the remaining defects require profile/session/tool-dispatch
changes that would be speculative without a narrower reproduction. No retry or
timeout inflation was added.

## 10-Run Full Tool-Loop Certification

| Run | Host | Profile | Model | Tool | Result |
|---:|---|---|---|---|---|
| 1 | Oracle | nova_nexus | gpt-4o-mini | nexus_get_system_health | PASS |
| 2 | Oracle | nova_nexus | gpt-4o-mini | nexus_get_system_health | PASS |
| 3 | Oracle | nova_nexus | gpt-4o-mini | nexus_get_system_health | PASS |
| 4 | Oracle | nova_nexus | gpt-4o-mini | nexus_get_system_health | PASS |
| 5 | Oracle | nova_nexus | gpt-4o-mini | nexus_get_system_health | PASS |
| 6 | Oracle | nova_nexus | gpt-4o-mini | nexus_get_system_health | PASS |
| 7 | Oracle | nova_nexus | gpt-4o-mini | nexus_get_system_health | PASS |
| 8 | Oracle | nova_nexus | gpt-4o-mini | nexus_get_system_health | PASS |
| 9 | Oracle | nova_nexus | gpt-4o-mini | nexus_get_system_health | PASS |
| 10 | Oracle | nova_nexus | gpt-4o-mini | nexus_get_system_health | PASS |

`USER_VISIBLE_FULL_LOOP_SUCCESS=10/10`. Individual elapsed times were
approximately 8–12 seconds. Attempt count was one for each observed run.

## Multi-Specialist Proof

`MULTI_SPECIALIST_REASONING=FAIL`. The response text named Alpha and Finance,
but runtime logs showed invalid tool dispatch and approval failures, and no
fresh delegation receipts were present. Text alone is insufficient evidence.

## Session Continuity

`SESSION_CONTINUITY=FAIL`. A unique HELIOS fact was stored in one CLI process;
the separate `--continue` invocation returned unrelated values. No durable
session identity was safely established across the process boundary.

## Failover / Recovery

`FAILOVER_RECOVERY=NOT_RUN`. It was gated on full-loop reliability plus
continuity and was not induced against the live Oracle service.

## Oracle Warning Recheck

`NOVA_NEXUS_PROFILE_BINDING=UNRESOLVED_WARNING`. The warning remains in
container startup logs. The CLI path can run with explicit profile/toolset
environment, but the shared API profile ownership needs a controlled repair and
retest before production certification.

## Cloud Decision

`ALTERNATE_CLOUD_TEST_NEEDED=NO` for now. The native Oracle CLI full-loop
passed 10/10, so there is no evidence yet that another cloud would solve the
remaining profile/session/dispatch issues.

## Tests

- Native Oracle Hermes full-loop: `10/10` real MCP-backed completions.
- Fresh multi-specialist attempt: not certified; runtime dispatch errors found.
- Session continuity: failed across separate CLI invocations.
- Canonical build: `PASS_EXIT_0`; Tailwind, TypeScript, and Vite completed.

## Secret Scan

`PASS` for the intended WP9Q report; no secret values were printed or stored.

## Git

Only this WP9Q report is intended for commit. Existing unrelated worktree
entries were not staged.

IMPLEMENTATION_HEAD=`8a3150d611d923d2b4f0d3bad7a665e66cc4e7af`
REPORT_COMMIT=`RECORDED_AFTER_COMMIT`
FINAL_ORIGIN_MAIN_HEAD=`RECORDED_AFTER_PUSH`
PUSHED=`YES`
WORKTREE_ENTRY_COUNT_AFTER=574
UNRELATED_EXISTING_CHANGES_PRESERVED=YES

The report cannot contain the hash of the commit that contains its final hash
field. Finalization records the report-introduction commit and the separately
verified pushed head in the handoff.

## Remaining WP9 Gates

- Repair/retest canonical `nova_nexus` API profile binding.
- Produce fresh delegation receipts proving model-driven specialist calls.
- Implement/prove durable session namespace and continuity.
- Run bounded failover/recovery after those gates.
- Keep Telegram cutover and human proof deferred.

## Final Status

WP9Q=PARTIAL
PROFILE_BINDING_WARNING=POTENTIALLY_CAUSAL
RUNTIME_PROFILE_PROVEN=YES
FULL_TOOL_LOOP_SINGLE_TRACE=PASS_REAL
FULL_TOOL_LOOP_RUNS=10/10
FULL_HERMES_TOOL_LOOP=PASS_REAL_SINGLE_TOOL_ONLY
MULTI_SPECIALIST_REASONING=FAIL
SESSION_CONTINUITY=FAIL
FAILOVER_RECOVERY=NOT_RUN
NOVA_NEXUS_PROFILE_BINDING=UNRESOLVED_WARNING
ALTERNATE_CLOUD_TEST_NEEDED=NO
TELEGRAM_READY=NO
TELEGRAM_CUTOVER=NO
WP9=RETRY_NIGHT_1
