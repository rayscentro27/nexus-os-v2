# Nexus / Hermes R15.4 Durable Workstation

## Verdict

`NEXUS_HERMES_DURABLE_WORKSTATION_R15_4=RUN_LIMIT_CHECKPOINT`

The live Oracle container was inspected without changing it. It runs on ARM64
from the pinned Hermes 0.20.6 image
`docker.io/nousresearch/hermes-agent@sha256:e3f4f0679f15556d5e09369cc36bf1074351b2d37bdd672dae593dfd07495180`,
with the upstream entrypoint, host networking, and the durable `/opt/data`
mount. Its Quadlet is `/home/opc/.config/containers/systemd/nexus-hermes-0206.container`.

## Durable build

Added [Containerfile.hermes-workstation](../../infra/hermes/Containerfile.hermes-workstation)
and its [build README](../../infra/hermes/README.md). The layer pins the live
base digest, Debian ARM64 `gh`, `jq`, and `fd-find`, and pinned npm packages
for OpenCode, Supabase, Netlify, and Playwright. It preserves the upstream
entrypoint and `/opt/data`; credentials remain outside the image.

Two Oracle builds were attempted. The first found the selected Playwright
version was not available under the Oracle registry's date constraint. The
second used Playwright 1.62.0 and completed package installation, but the
Oracle root volume reached 100% during the image commit. No workstation image
tag was produced and the running Hermes container was not modified. Therefore
the durable toolchain and rebuild-survival gates remain unproven.

## Kanban and reviewer evidence

Live Hermes source already proves `parents` means `PREREQUISITE`; the R15.3
corrected graph used research → engineering prerequisite edges, with the
orchestrator outside that chain. Research and engineering completed. The
reviewer timed out while its model attempted `tool_search`, then direct tool
calls errored while inspecting the scratch workspace. This is classified as a
worker tool-loop failure, not a dependency-semantics failure. The full graph,
review completion, restart persistence, and worker-side skill receipts are not
yet proven.

## Current R15.4 contract

```text
DURABLE_IMAGE_BUILD_PATH=FAIL (version-controlled definition exists, but live image commit did not complete)
HERMES_TOOLCHAIN_DURABLY_PROVISIONED=FAIL
HERMES_TOOLCHAIN_SURVIVES_CONTAINER_REBUILD=FAIL
HERMES_CAN_CALL_OPENCODE=FAIL (no rebuilt image)
HERMES_CAN_CALL_GH=FAIL (no rebuilt image)
HERMES_CAN_CALL_JQ=FAIL (no rebuilt image)
HERMES_CAN_CALL_FD=FAIL (no rebuilt image)
HERMES_CAN_CALL_SUPABASE=FAIL (no rebuilt image)
HERMES_CAN_CALL_NETLIFY=FAIL (no rebuilt image)
HERMES_BROWSER=FAIL (browser binary not included/certified)
HERMES_SKILL_ATTACHMENT_PROVENANCE=FAIL
SKILL_RECEIPTS_COMPLETE=0/3
REVIEWER_TIMEOUT_ROOT_CAUSE=worker model/tool-loop failure during tool_search/direct tool calls
HERMES_REVIEWER_COMPLETION=FAIL
HERMES_MULTI_AGENT_KANBAN=FAIL
HERMES_KANBAN_RESTART_PERSISTENCE=FAIL
R14_RESULT_TO_HERMES_TASK_HANDOFF=FAIL
INVALID_MODEL_PLAN_TO_HERMES_RECOVERY=FAIL
PASS_WITHOUT_DELTA_TO_HERMES_RECOVERY=FAIL
REAL_GOAL_HERMES_AGENT_STACK_USED=NO
REAL_GOAL_MATERIAL_PROGRESS=NO
NEW_CRITERIA_VERIFIED=0
STABLE_HERMES_FEATURES_BYPASSED_WITHOUT_REASON=[]
TRUE_RAY_BLOCKERS=NONE
```

Portal goals were not reopened and remain `READY_FOR_HUMAN_REVIEW`. No secret
was exposed, and no production or trading action occurred.

## Exact next engineering action

Expand or otherwise provide approved Oracle build storage, rerun the pinned
ARM64 build from the version-controlled Containerfile, verify every CLI and
browser prerequisite in a disposable container, then update the Quadlet only
after verification. Next instrument the actual Hermes dispatcher worker
startup/result boundary for per-execution skill receipts, rerun the corrected
three-worker graph, and only then route an existing Nexus criterion through
the normal broker.
