# Nexus Tier-1 Runtime Certification — 2026-11-17

## Certification scale

- `LEVEL_0_REGISTERED`: identity/configuration exists.
- `LEVEL_1_ACCESS_VERIFIED`: approved access or runtime identity was observed.
- `LEVEL_2_CAPABILITY_VERIFIED`: a bounded capability check passed.
- `LEVEL_3_END_TO_END_CERTIFIED`: a real workflow completed through persistence/receipt.
- `LEVEL_4_PRODUCTION_CERTIFIED`: existing production certification is current and authoritative.

## Environment results

| Environment | Highest supported level | Evidence and limits |
|---|---|---|
| Oracle Hermes | LEVEL_2_CAPABILITY_VERIFIED (MCP only) | Approved resolver passed; Nova service active; Hermes running; authenticated `nexus_mcp_remote` test connected and discovered 154 tools; Codex OAuth reports logged in. No tool invocation or native skills/cron/browser canary was run. |
| Contabo | LEVEL_1_ACCESS_VERIFIED | Canonical SSH identity resolved; read-only host inspection succeeded. Docker and current services were visible. No browser canary: host lacks Node/Playwright; REA container lacks Playwright/Selenium/Chromium and a browser listener. |
| Contabo n8n capability | LEVEL_2_CAPABILITY_VERIFIED | Existing n8n 2.45.6 authenticated health and workflow list (five flows) were previously verified. Nexus outbound callback remains unverified; adapter is read-only. |
| Modal | LEVEL_1_ACCESS_VERIFIED | Existing profile and two deployed app identities visible. No Modal function launched, no artifact returned, no R2 persistence canary. |
| Mac Research | LEVEL_2_CAPABILITY_VERIFIED | Fresh API and R10 health probes returned HTTP 200. Research MCP returned expected unauthenticated HTTP 401; authenticated MCP tool discovery is verified through the approved tunnel. No bounded research task was executed. |
| Cloudflare R2 | LEVEL_4_PRODUCTION_CERTIFIED (prior evidence) | Existing Systems Ledger records live image/video Asset Persistence Bot ingestion and signed read. No broad retest in this pass. |
| Supabase | LEVEL_4_PRODUCTION_CERTIFIED (prior evidence) | Existing Systems Ledger records the governed metadata/workflow persistence certification. No broad retest or mutation in this pass. |

## Hermes capability matrix

| Capability | Result | Evidence |
|---|---|---|
| HERMES_MCP | LEVEL_2 / PASS | Authenticated resolver-mediated connection; 154 tools discovered. |
| HERMES_WEB_SEARCH | NOT_VERIFIED | No execution canary. |
| HERMES_WEB_EXTRACT | NOT_VERIFIED | No execution canary. |
| HERMES_BROWSER | NOT_VERIFIED | No execution canary. |
| HERMES_CDP | NOT_VERIFIED | No execution canary. |
| HERMES_COMPUTER_USE | NOT_VERIFIED | No execution canary. |
| HERMES_DELEGATE | NOT_VERIFIED | No execution canary. |
| HERMES_SKILLS | NOT_VERIFIED | Native discovery/load/execute/receipt was not available through the approved resolver command set. |
| HERMES_SESSION | NOT_VERIFIED | No session canary. |
| HERMES_MESSAGING | NOT_VERIFIED | No internal delivery canary. |
| HERMES_CRON | NOT_VERIFIED | No create/trigger/cleanup canary; production scheduling remains disabled. |
| HERMES_MODEL_RUNTIME | ACCESS_ONLY | Codex OAuth status reports logged in; no model call was made. |

The resolver was used for Oracle checks. An attempted compound remote inspection was rejected by its read-only command allowlist; no command was run through an alternate SSH path. The resolver policy was not changed.

## Other bounded observations

- Modal: `goclearonline` profile lists `nexus-creative-gpu-worker` and `nexus-remote-cpu-worker` as deployed with zero active tasks. No compute job was launched because the governed job/cost preflight and safe artifact return path were not verified.
- Google: a local Gemini credential identity is configured, but a Model Manager API route and bounded model canary were not verified. Gemini Web, Flow, AI Studio, Notebook, and Colab interactive access were not tested in this pass.
- Remotion: Node and FFmpeg are present on Mac, but no bounded render and R2 persistence test was run. No Remotion capability is newly certified.
- Mac endpoint observations: Research API `127.0.0.1:4000/health` → 200; R10 `127.0.0.1:18766/health` → 200; Research MCP `127.0.0.1:18768/health` → 401 (authentication required).

## Workflow Fabric activation state

The existing durable GoClear workflow was read by its current root job and remains:

```text
WORKFLOW_ID=wf_dfccb523f5114f68a53e226b4c33f402
STATUS=WAITING_DEPENDENCY
CURRENT_STEP=OBJECTIVE_INTAKE
LAST_CERTIFIED_STEP=none
STEP_COUNT=15
BLOCKER_COUNT=1
RUNTIME_HANDLERS_BOUND=NO
```

No workflow step was advanced. The controller requires each step to execute in its authorized environment; a Mac-local stand-in for Oracle-owned Nova work would misstate execution provenance. Research and Campaign handlers also need their canonical provider/connector invocation paths wired before dispatch.

`workflow_runtime_health.py` adds bounded timestamped probes for Mac Research API/R10/MCP and a freshness filter for adapter observations. It does not probe Oracle, Contabo, or Modal itself; those must be supplied by their approved adapters. The authenticated MCP `401` is retained as `AUTH_REQUIRED`, not collapsed into a success state.

## Outstanding activation work

1. Add/enable approved runtime health adapters for Oracle Hermes, Contabo, and Modal with freshness timestamps.
2. Implement real handler adapters for Nova objective intake and Research Lead planning that dispatch in their registered environments and emit canonical receipts.
3. Continue the existing GoClear workflow only after handler authorization and provider execution are verified.
4. Certify Hermes native skills and cron through an explicitly approved read/canary path; keep cron inactive meanwhile.
5. Add an authenticated n8n-to-Nexus callback canary and a safe internal completion notification canary.
6. Certify a bounded Modal compute/artifact return path and Contabo browser support before routing work to either capability.
7. Verify Google AI interactive environments, Gemini API through Model Manager, and Remotion render separately before marking them available.

No secrets, cookies, API keys, or credential values are included in this report.
