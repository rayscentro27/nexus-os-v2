# Nexus Remote Infrastructure Closure R1.1

## Executive Result

The three previously unverified internal paths were recovered and proven:

- the existing Mac Nexus MCP server is now supervised and reachable from Oracle through the canonical reverse SSH tunnel;
- Hermes 0.20.6 on Oracle, using `nova_nexus`, completed a current-state Nexus tool turn;
- the existing `goclearonline/nexus-remote-cpu-worker` Modal application completed a bounded remote CPU job through the canonical provider.

Oracle browser execution was also restored using the existing Hermes browser path. No new orchestration system, MCP server, remote worker, paid plan, external publication, payment, or live trade was introduced.

## MCP Root Cause

`nova_nexus` correctly referenced `http://127.0.0.1:18765/mcp`, but the launchd-owned Oracle tunnel only forwarded Hermes API port `18642`; it had no reverse `-R 127.0.0.1:18765` leg. The canonical Mac HTTP MCP process had also been left without a persistent launchd owner. A temporary bridge credential mistake was found during repair: the profile placeholder was initially treated literally. It was corrected by loading the actual profile credential through the existing non-secret credential-control path and storing only its Keychain reference in tracked configuration.

## MCP Repair

The existing architecture was reused:

`Mac launchd MCP bridge` → `services.nexus_mcp.http_server` → `launchd SSH tunnel` → `Oracle 127.0.0.1:18765` → `nova_nexus`.

The bridge is loopback-only, bearer-authenticated, read-only, and supervised by `com.nexus.nexus-mcp-bridge`. The tunnel now carries both the existing Hermes API forward and the MCP reverse forward. Anonymous access returned HTTP 401, proving the listener is present and fail-closed. Authenticated Hermes MCP discovery connected and found 7 canonical Nexus tools.

## nova_nexus

The existing profile remained in `/opt/data/profiles/nova_nexus`. With the repaired path, a real Hermes turn using `nexus_mcp_remote` returned current, timestamped system health including `status=partial`, freshness, source `composite`, and the observed Research heartbeat. This is a current structured read, not a static prompt response.

## Hermes Real Turn

Runtime evidence:

- host: `nexus-llm-worker`;
- container: `nexus-hermes-0206`;
- Hermes: `0.20.6`;
- profile: `nova_nexus`;
- toolset: `nexus_mcp_remote`;
- provider/model: `openrouter` / `openai/gpt-4o-mini`;
- result: successful current Nexus system-health response;
- execution: Oracle container via the existing SSH/Podman wrapper.

The reusable health command also reports Hermes HTTP health 200, zero container restarts, and profile presence.

## Browser Drift

The browser capability had not disappeared architecturally. The current profile had `browser.enabled: false`; the earlier probe also found no installed CUA driver. A Chromium headless shell was already present in the Hermes image at the existing Playwright cache path, but was not surfaced by the earlier discovery check. Desktop CUA doctor checks still report no X11 screen/AX capability on this headless Linux host; that does not invalidate the supported headless browser route used for the proof.

## Browser Repair

The supported Hermes `computer-use install` path restored `cua-driver` 0.23.2 at `/root/.local/bin/cua-driver`. The existing `nova_nexus` browser setting was enabled. The existing Chromium headless shell at `/opt/hermes/.playwright/chromium_headless_shell-1234/chrome-linux/headless_shell` was reused; Hermes was not upgraded and no unrelated browser stack was created.

## Oracle Remote Browser Proof

An actual bounded read-only task was invoked through SSH into the Oracle Podman container, using Hermes 0.20.6 with `browser,computer_use`: navigate to `https://example.com`, then read the page title and first heading. Hermes returned `Example Domain` for both. The invocation path and server-side container identity establish that the browser execution occurred on Oracle rather than the Mac. The result returned through the Oracle command bridge to the Mac control plane.

## Modal Dependency

The canonical repository environment was found at `.venv-agent-platform`; the previous “SDK unavailable” result was an environment-discovery defect. It contains Modal SDK 1.5.4 and the Modal CLI. `modal profile list` showed the existing `goclearonline` profile without exposing credential values.

## Modal Authentication

The existing profile and credential control path were reused. No plan change, payment method, or account mutation occurred. Authentication was sufficient for both a health call and a real bounded job.

## Modal CPU Proof

The existing app and function were called without redeployment:

- workspace/profile: `goclearonline`;
- app: `nexus-remote-cpu-worker`;
- health function: `health_check`, returned `HEALTHY`;
- job function: `submit_job`;
- job: bounded public `example.com` evidence-ingestion transform, with no PII or secrets;
- result: `SUCCESS`;
- job id: `job-6fb5154937d94f81`;
- worker id: `modal-worker-3ce13cff8733`;
- duration: 7.853 seconds wall time, with remote execution duration reported by the worker;
- receipt: `evidence-receipt-9b042182a2424063.json` returned by the worker;
- result integrity: input/output SHA-256 values were recorded in the runtime receipt and not treated as business evidence;
- provider cost: `UNKNOWN` (not inferred).

Remote proof is based on the Modal provider response, canonical app/function identity, remote worker id, remote timestamps, and returned receipt. One nested evidence metadata field labels the worker type as `MAC_MINI_ISOLATED_WORKER`; this is retained as a metadata-quality issue, not used to override the outer provider and remote-job evidence.

## GPU State

Modal GPU remains `BUILT_NOT_DEPLOYED`. The existing Creative GPU adapter and deployment source remain available for future governed activation, but no paid GPU execution was needed or performed. This is separate from the certified Modal CPU path.

## Health Check

`scripts/ops/check_remote_stack_health.py` now provides one bounded, read-only status contract for Mac control plane, Research heartbeat, Oracle SSH/Hermes/version/profile, Nexus MCP listener, Ollama, SearXNG, CUA/browser runtime, Modal SDK/CLI/auth state, Modal CPU, and GPU state. Current output included:

`mac_control_plane=PASS_REAL`, `research_heartbeat=ACTIVE`, Oracle `status=PASS_REAL`, `nexus_mcp=LISTENER_401`, `browser_runtime=CHROMIUM_HEADLESS_SHELL`, `cua_driver=INSTALLED`, Modal SDK/CLI available, Modal auth configured, and Modal CPU `RUNTIME_CERTIFIED`. No secret values are emitted.

## Capability Memory

`config/remote_capability_memory.json` now records the canonical MCP bridge owner, reverse tunnel mapping, Keychain reference (never the value), Oracle browser runtime, CUA driver, Modal CPU path, GPU deferred state, and reusable health-check path. `configs/nexus_credential_registry.json` records the non-secret MCP bridge credential contract. The user LaunchAgent installation was also persisted at `~/Library/LaunchAgents/com.nexus.nexus-mcp-bridge.plist`.

## Mac Protection

The Mac remains the control plane for the Continuous Operating Kernel, Research, objectives, credentials, receipts, and orchestration. Browser and Modal tests were bounded and remote. The health check continued to report Research `ACTIVE`; the Research heartbeat next wake remained scheduled. No control-plane instability or Research interruption was observed.

## Remaining True Blockers

None. Desktop X11-specific CUA capabilities are unavailable on the headless Oracle host, but the required headless browser route is operational. Modal GPU is an intentionally deferred capability state, not a blocker for this closure.

## Research Continuity

Research remained enabled and active while MCP, Oracle browser, and Modal remote execution were repaired and tested. The scheduler/continuous runtime was not stopped or unloaded.

## Git

Starting state was `HEAD=6dfabc2afa83337f03fc9f97550a9cbab47e29c8`, `origin/main` at the same commit, branch `main`, with 598 pre-existing worktree entries. Unrelated work was preserved and was not staged. Only the explicit closure files are intended for this change.

Focused validation passed: 17 Nexus MCP tests and 16 remote/Modal/health tests, 33 total. A Pydantic warning was present in the existing runtime environment; it did not fail the tests.

```text
REMOTE_INFRASTRUCTURE_CLOSURE_R1_1=PASS

NEXUS_MCP_18765_ROOT_CAUSE=canonical Mac MCP listener was unsupervised and the launchd Oracle tunnel omitted the reverse -R 18765 forward; the Mac bridge also needed to load the profile credential through Keychain
NEXUS_MCP_REMOTE_LISTENER=PASS_REAL
NEXUS_MCP_REMOTE_TRANSPORT=PASS_REAL
NOVA_NEXUS_PROFILE=PASS_REAL
HERMES_MCP_SURFACE=PASS_REAL
ORACLE_TO_MAC_NEXUS_PATH=PASS_REAL
NOVA_CURRENT_COMPANY_CONTEXT=PASS_REAL
NOVA_CURRENT_STATE_QUERY=PASS_REAL
ORACLE_HERMES_REAL_TURN=PASS_REAL

ORACLE_BROWSER_DRIFT_ROOT_CAUSE=current nova_nexus browser.enabled was false; CUA driver was absent; existing Chromium headless shell was present but previously undiscovered
ORACLE_CUA_DRIVER=PASS_REAL
ORACLE_CHROMIUM_RUNTIME=PASS_REAL
ORACLE_BROWSER_AVAILABLE=PASS_REAL
HERMES_BROWSER_SURFACE=PASS_REAL
ORACLE_REMOTE_BROWSER=PASS_REAL
ORACLE_EXECUTION_PROVEN_REMOTE=PASS_REAL
ORACLE_BROWSER_RESULT_RETURN=PASS_REAL
AUTHENTICATED_BROWSER_ARCHITECTURE=PASS_REAL
POST_LOGIN_OBJECTIVE_RESUME_CONTRACT=PASS_REAL

MODAL_SDK_AVAILABLE=PASS_REAL
MODAL_CLI_AVAILABLE=PASS_REAL
MODAL_AUTHENTICATION=PASS_REAL
MODAL_CPU_WORKER_DEPLOYED=PASS_REAL
MODAL_CPU_HEALTH=PASS_REAL
MODAL_CPU_JOB_EXECUTION=PASS_REAL
MODAL_CPU_RESULT_RETURN=PASS_REAL
MODAL_EXECUTION_PROVEN_REMOTE=PASS_REAL
MODAL_REMOTE_RECEIPT=PASS_REAL
MODAL_GPU_STATE=BUILT_NOT_DEPLOYED
REMOTE_STACK_HEALTH_CHECK=PASS_REAL
REMOTE_CAPABILITY_MEMORY_UPDATED=PASS_REAL
MAC_CONTROL_PLANE_PROTECTED=PASS_REAL
RESEARCH_HEARTBEAT=ACTIVE
RESEARCH_CONTINUITY_DURING_REMOTE_EXECUTION=PASS_REAL

WEB_UI_TREATED_AS_TERMINAL_BLOCKER=NO
REAL_PAYMENTS_PERFORMED=NO
LIVE_TRADES_EXECUTED=NO
EXTERNAL_CONTENT_PUBLISHED=NO
TRUE_RAY_BLOCKERS=NONE
REMOTE_INFRASTRUCTURE_READY_FOR_HERMES_NOVA=YES
NEXT_RECOMMENDED_PHASE=COMPLIANCE_DEPARTMENT_AND_GOCLEAR_OFFER_VALIDATION_R1
```
