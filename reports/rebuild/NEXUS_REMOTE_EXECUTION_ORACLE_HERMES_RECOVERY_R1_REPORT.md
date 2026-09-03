# Nexus Remote Execution + Oracle Hermes Recovery R1

## Executive Result

`REMOTE_EXECUTION_ORACLE_HERMES_RECOVERY_R1=PARTIAL`.

The existing Oracle path was recovered and currently verified: SSH reaches
`nexus-llm-worker`, the `nexus-hermes-0206` container is running with zero
restarts, Hermes is `0.20.6`, Ollama is healthy, SearXNG returns HTTP 200, and
the Mac→Oracle Hermes tunnel returns HTTP 200. A real bounded Hermes turn also
executed on Oracle and returned the expected `ORACLE / 0.20.6 / nova_nexus`
runtime envelope.

The remaining partial status is caused by two concrete integration gaps, not
an absent account or inactive Hermes: the profile’s `nexus_mcp_remote` endpoint
at Oracle loopback `127.0.0.1:18765` refuses connections, and the current
container has no discoverable Chromium/Playwright executable or CUA driver.
The local Modal CLI and Python SDK are also unavailable, so the supplied Modal
workspace screenshot is retained as account evidence but no live Modal job is
claimed.

## Starting State

```text
START_HEAD=24a5468ead9983df1ee687b737576a041554dcde
ORIGIN_MAIN=24a5468ead9983df1ee687b737576a041554dcde
BRANCH=main
WORKTREE_ENTRY_COUNT_BEFORE=598
```

Unrelated worktree changes were preserved. No secrets, keys, cookies, tokens,
or credential values were written to this report or the new memory file.

## Historical Oracle Evidence

The prior reports identify the authorized path as `opc@161.153.40.41` using
`~/.ssh/oracle_vm`, with Hermes in `nexus-hermes-0206`, profile `nova_nexus`,
API loopback `127.0.0.1:8642`, and Mac tunnel `127.0.0.1:18642`. They also
document earlier browser proof, Hermes surface discovery, and a prior
authenticated Oracle→Mac Nexus read. Those reports were used to locate the
canonical wrapper; current probes below were run independently.

## Current Oracle Host Status

Current read-only SSH evidence:

- Reachable; host identity `nexus-llm-worker`.
- Oracle Linux Server 9.7, aarch64, 4 vCPU, approximately 22 GiB RAM and 5 GiB
  swap.
- Load `0.00 0.00 0.00`; uptime approximately 9 weeks; root disk 30 GiB with
  approximately 7.2 GiB free (76% used).
- Podman container `nexus-hermes-0206`: `running`, started 2026-09-02,
  restarts `0`.

```text
ORACLE_HOST_STATUS=HEALTHY
ORACLE_SSH_CONNECTIVITY=PASS_REAL
```

## Current Oracle Hermes Status

Hermes health returned HTTP 200 and `{"status":"ok","version":"0.20.6"}`.
The container’s Hermes gateway process is running. The profile directory
`/opt/data/profiles/nova_nexus` exists and contains current state/config/cache
artifacts. Hermes `status`, `mcp list`, and `skills list` all execute inside
the container.

```text
ORACLE_HERMES_CONTAINER_STATE=RUNNING
ORACLE_HERMES_PROCESS_STATE=RUNNING
ORACLE_HERMES_VERSION=0.20.6
ORACLE_HERMES_HEALTH=DEGRADED
```

It is degraded only at the Nexus MCP/browser integration layer; the container,
gateway, and basic Hermes API are healthy.

## Hermes Version

Current version is exactly the expected `0.20.6`; no drift and no upgrade was
performed.

```text
HERMES_VERSION_DRIFT=NONE
ORACLE_HERMES_RECOVERY=NOT_NEEDED
```

## nova_nexus Profile

The profile exists and loads as a Hermes profile. The real turn envelope reports
`profile=nova_nexus`, but the profile’s configured `nexus_mcp_remote` transport
points to `http://127.0.0.1:18765/mcp`, which currently refuses connections.
Therefore profile existence is proven while current Nexus-tool/context access
is not.

```text
NOVA_NEXUS_PROFILE=PARTIAL
```

## Ollama

Oracle loopback Ollama returned version `0.21.2` and HTTP success. Hermes
`status` shows configured provider/model state, but this campaign did not make
an additional paid/provider change or claim a model-quality result.

```text
ORACLE_OLLAMA=HEALTHY
```

## SearXNG

Oracle loopback SearXNG returned HTTP 200. No broad scrape or public mutation
was performed.

```text
ORACLE_SEARXNG=HEALTHY
```

## Hermes Skills / Tools / MCP / Browser / Sessions / Gateway

Discovery and safe status evidence:

- Skills: installed-skill listing succeeds; bundled skills include
  `computer-use`, `comfyui`, and agent/runtime skills.
- Tools: Hermes tool command surface exists; a summary invocation was not
  treated as execution proof.
- MCP: `nexus_mcp_remote` is configured/enabled, but `hermes mcp test` fails
  because `127.0.0.1:18765` refuses the connection.
- Browser: `browser` and `computer-use` command surfaces exist; current CUA
  status says `cua-driver: not installed`, and no current Chromium/Playwright
  executable was discoverable in the container.
- Sessions: session command surface exists; current status shows zero active
  sessions.
- Gateway: running under s6 with Hermes PID 162.

```text
HERMES_SKILLS_SURFACE=PASS_REAL
HERMES_TOOLS_SURFACE=PASS_REAL
HERMES_MCP_SURFACE=DISCOVERED_ONLY
HERMES_BROWSER_SURFACE=DISCOVERED_ONLY
HERMES_SESSIONS_SURFACE=PASS_REAL
HERMES_GATEWAY_SURFACE=PASS_REAL
```

## Oracle → Mac Nexus Connectivity

The existing Mac loopback tunnel on `127.0.0.1:18642` is listening and its
Hermes health endpoint returns HTTP 200. This proves the private SSH/API path.
The current profile’s configured Nexus MCP endpoint is separate and is
unavailable on Oracle, so the state-query path cannot be certified current.

```text
ORACLE_TO_MAC_NEXUS_PATH=PARTIAL
NOVA_CURRENT_COMPANY_CONTEXT=FAIL
NOVA_CURRENT_STATE_QUERY=FAIL
```

The failure is `SOLVABLE_WITH_EXISTING_CODE_OR_CONFIG_REPAIR`, not a Ray
blocker: restore the canonical Nexus MCP listener/forwarding path, then rerun
the existing context proof.

## Real Oracle Hermes Turn

A real bounded call through `oracle_hermes_cli.py` completed in approximately
15.7 seconds with:

```text
runtime_host=ORACLE
hermes_version=0.20.6
profile=nova_nexus
provider=openrouter
model=openai/gpt-4o-mini
toolset=nexus_mcp_remote
status=SUCCEEDED
```

The returned text said Nexus status/tools were unavailable, which matches the
MCP connection failure. A second explicit request to call
`nexus_get_system_health` produced the same limitation. This is genuine remote
Hermes execution, but not a successful current-state Nexus turn.

```text
ORACLE_HERMES_REAL_TURN=FAIL
```

## Oracle Browser

Historical evidence proves that this container previously executed a bounded
Playwright Chromium task. Current inspection found no Python Playwright module,
no discoverable Chromium executable, and `hermes computer-use status` reports
the CUA driver is not installed. No installation was attempted because the
appropriate browser dependency path and authority are not yet established.

```text
ORACLE_BROWSER_AVAILABLE=FAIL
ORACLE_REMOTE_BROWSER=FAIL
ORACLE_EXECUTION_PROVEN_REMOTE=FAIL
ORACLE_BROWSER_RESULT_RETURN=FAIL
```

This does not invalidate the earlier proof; it records current runtime drift.

## Authenticated Browser Readiness

The architecture supports governed SSH/API credential handling and a profile
with session/browser surfaces. No safe authenticated external browser action
was needed or attempted. No credentials were exposed, and no MFA/CAPTCHA
boundary was reached.

```text
AUTHENTICATED_BROWSER_ARCHITECTURE=PASS_REAL
AUTHENTICATED_BROWSER_LIVE_PROOF=NOT_NEEDED
POST_LOGIN_OBJECTIVE_RESUME_CONTRACT=PASS_REAL
WEB_UI_TREATED_AS_TERMINAL_BLOCKER=NO
```

## Modal Historical Path

The canonical repository path is `ModalRemoteWorkerProvider` using the local
authenticated Modal profile and `modal.Function.from_name(app, function)`;
defaults are profile `goclearonline`, app `nexus-remote-cpu-worker`, function
`submit_job`, and health function `health_check`. Jobs are signed with the
existing HMAC contract and results are validated for schema, job, capability,
and tenant identity.

## Modal Root Cause

```text
MODAL_ACCESS_ROOT_CAUSE=LOCAL_MODAL_RUNTIME_DEPENDENCY_AND_AUTH_PROFILE_UNAVAILABLE
```

Evidence: `command -v modal` failed, Python `importlib.util.find_spec("modal")`
was false, and the relevant environment variables were unset. The supplied
Modal screenshot remains valid account/UI evidence; it is not runtime job
evidence. No redeploy or arbitrary dependency installation occurred.

## Modal SDK / CLI

```text
MODAL_SDK_AVAILABLE=FAIL
MODAL_CLI_AVAILABLE=FAIL
MODAL_AUTHENTICATION=FAIL_TRUE_EXTERNAL
```

The last field means this control plane cannot authenticate the current Modal
profile with available local tools; no claim is made that Ray’s account is
missing. Restoring the approved project environment/credential broker is the
next safe repair.

## Modal CPU Live Proof

No live job was submitted because the signed transport could not be reached
without the SDK/profile or endpoint/secret. The provider unit tests and
in-process worker tests remain engineering/integration evidence only.

```text
MODAL_CPU_WORKER_DEPLOYED=FAIL
MODAL_CPU_HEALTH=FAIL
MODAL_CPU_JOB_EXECUTION=FAIL
MODAL_CPU_RESULT_RETURN=FAIL
MODAL_EXECUTION_PROVEN_REMOTE=FAIL
MODAL_REMOTE_RECEIPT=FAIL
```

## Modal GPU State

The repository has historical Creative GPU/ComfyUI foundations but no current
authenticated/deployed GPU route, capacity, model, or commercial-license
evidence.

```text
MODAL_GPU_STATE=BUILT_NOT_DEPLOYED
REMOTE_GPU_PATH=DEFERRED_TRUE_CURRENT_LIMIT
GPU_ROUTE_READY_FOR_FUTURE_ACTIVATION=NO
```

The Modal CPU app and a future GPU/Creative worker remain separate capabilities.

## Workload Placement

The durable placement contract is:

- Mac: control plane, Research, objectives, credentials, receipts, watchdogs,
  and light orchestration.
- Oracle: Hermes, bounded CPU, and browser workloads once browser runtime is
  restored.
- Modal CPU: bursty CPU workloads after profile/auth recovery.
- Modal GPU: image/video/model workloads after a governed worker exists.

```text
WORKLOAD_PLACEMENT_ENGINE=PASS_REAL
```

## Mac Protection

The remote host probe and Hermes turn did not stop Research or alter the Mac
control plane. The heartbeat remained active and the local tunnel stayed
available.

```text
MAC_CONTROL_PLANE_PROTECTED=PASS_REAL
RESEARCH_CONTINUITY_DURING_REMOTE_EXECUTION=PASS_REAL
```

## Oracle Resource Governance

Current Oracle has 4 vCPU, approximately 22 GiB RAM, 5 GiB swap, 76% root-disk
use, zero load at probe, and Hermes/Ollama/SearXNG coexistence. Policy remains
bounded concurrency, loopback services, no artifact accumulation, no GPU
assumption, and no heavy work that displaces Hermes or SearXNG.

```text
ORACLE_RESOURCE_GOVERNANCE=PASS_REAL
```

## Hermes Recovery

No container restart was necessary. The exact recoverable issue is configuration
drift or missing service for `nexus_mcp_remote` at port 18765, plus missing
current browser runtime. Future repair should restore the canonical Nexus MCP
listener/forwarding path first, then restore the browser dependency through an
approved Hermes installation path, and rerun functional probes.

## Version Drift

```text
HERMES_VERSION_DRIFT=NONE
```

Hermes remains 0.20.6; no automatic upgrade was performed.

## Self-Improvement Memory

Added [remote_capability_memory.json](../../config/remote_capability_memory.json)
with non-secret durable knowledge of the Mac/Oracle/Modal roles, canonical
names, ports, expected version, current observed states, and exact unresolved
integration conditions. No secret value is stored.

```text
REMOTE_CAPABILITY_MEMORY_UPDATED=PASS_REAL
```

## Reusable Remote Health Check

Added [check_remote_stack_health.py](../../scripts/ops/check_remote_stack_health.py).
It performs read-only, secret-safe checks for the Mac tunnel, Oracle SSH,
Hermes health/container, Ollama, SearXNG, Nexus MCP availability, Modal CLI
presence, and GPU deferral. Current output records Oracle/Hermes/Ollama/SearXNG
healthy, Nexus MCP unavailable, and Modal CLI unavailable.

```text
REMOTE_STACK_HEALTH_CHECK=PASS_REAL
```

Focused bridge/worker/health tests passed `17/17`.

## Remaining True Blockers

`TRUE_RAY_BLOCKERS=NONE` for the internal recovery work. The next repairs are
safe configuration/dependency tasks: restore the Oracle MCP listener or its
private forwarding path, restore current browser runtime, and restore the
approved Modal SDK/CLI credential environment. Any later MFA/identity,
purchase, or paid-plan step would be isolated as a Ray human/approval boundary.

## Research Continuity

Research remained `ACTIVE` and the scheduler remained `ACTIVE_DAEMON` during
SSH probes, Hermes turns, MCP diagnostics, and the health-check run.

## Git

Only this report, the non-secret capability memory, the reusable health check,
and its focused test are task-scoped. Unrelated worktree changes were not
staged.

## Final Contract

```text
REMOTE_EXECUTION_ORACLE_HERMES_RECOVERY_R1=PARTIAL
ORACLE_HOST_STATUS=HEALTHY
ORACLE_SSH_CONNECTIVITY=PASS_REAL
ORACLE_HERMES_CONTAINER_STATE=RUNNING
ORACLE_HERMES_PROCESS_STATE=RUNNING
ORACLE_HERMES_VERSION=0.20.6
ORACLE_HERMES_HEALTH=DEGRADED
ORACLE_HERMES_RECOVERY=NOT_NEEDED
NOVA_NEXUS_PROFILE=PARTIAL
ORACLE_OLLAMA=HEALTHY
ORACLE_SEARXNG=HEALTHY
HERMES_SKILLS_SURFACE=PASS_REAL
HERMES_TOOLS_SURFACE=PASS_REAL
HERMES_MCP_SURFACE=DISCOVERED_ONLY
HERMES_BROWSER_SURFACE=DISCOVERED_ONLY
HERMES_SESSIONS_SURFACE=PASS_REAL
HERMES_GATEWAY_SURFACE=PASS_REAL
ORACLE_TO_MAC_NEXUS_PATH=PARTIAL
NOVA_CURRENT_COMPANY_CONTEXT=FAIL
NOVA_CURRENT_STATE_QUERY=FAIL
ORACLE_HERMES_REAL_TURN=FAIL
ORACLE_BROWSER_AVAILABLE=FAIL
ORACLE_REMOTE_BROWSER=FAIL
ORACLE_EXECUTION_PROVEN_REMOTE=FAIL
ORACLE_BROWSER_RESULT_RETURN=FAIL
AUTHENTICATED_BROWSER_ARCHITECTURE=PASS_REAL
AUTHENTICATED_BROWSER_LIVE_PROOF=NOT_NEEDED
POST_LOGIN_OBJECTIVE_RESUME_CONTRACT=PASS_REAL
MODAL_ACCESS_ROOT_CAUSE=LOCAL_MODAL_RUNTIME_DEPENDENCY_AND_AUTH_PROFILE_UNAVAILABLE
MODAL_SDK_AVAILABLE=FAIL
MODAL_CLI_AVAILABLE=FAIL
MODAL_AUTHENTICATION=FAIL_TRUE_EXTERNAL
MODAL_CPU_WORKER_DEPLOYED=FAIL
MODAL_CPU_HEALTH=FAIL
MODAL_CPU_JOB_EXECUTION=FAIL
MODAL_CPU_RESULT_RETURN=FAIL
MODAL_EXECUTION_PROVEN_REMOTE=FAIL
MODAL_REMOTE_RECEIPT=FAIL
MODAL_GPU_STATE=BUILT_NOT_DEPLOYED
REMOTE_GPU_PATH=DEFERRED_TRUE_CURRENT_LIMIT
GPU_ROUTE_READY_FOR_FUTURE_ACTIVATION=NO
WORKLOAD_PLACEMENT_ENGINE=PASS_REAL
MAC_CONTROL_PLANE_PROTECTED=PASS_REAL
ORACLE_RESOURCE_GOVERNANCE=PASS_REAL
RESEARCH_HEARTBEAT=ACTIVE
RESEARCH_CONTINUITY_DURING_REMOTE_EXECUTION=PASS_REAL
HERMES_VERSION_DRIFT=NONE
REMOTE_CAPABILITY_MEMORY_UPDATED=PASS_REAL
REMOTE_STACK_HEALTH_CHECK=PASS_REAL
WEB_UI_TREATED_AS_TERMINAL_BLOCKER=NO
REAL_PAYMENTS_PERFORMED=NO
LIVE_TRADES_EXECUTED=NO
EXTERNAL_CONTENT_PUBLISHED=NO
TRUE_RAY_BLOCKERS=NONE
REMOTE_INFRASTRUCTURE_READY_FOR_HERMES_NOVA=NO
NEXT_RECOMMENDED_PHASE=HERMES_NOVA_EXECUTIVE_ORCHESTRATION_AND_CUSTOMER_INTERFACE
```
