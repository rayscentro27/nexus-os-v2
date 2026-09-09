# Nexus / Hermes R15.5 Oracle Workstation

## Verdict

`NEXUS_ORACLE_BUILD_STORAGE_AND_WORKSTATION_R15_5=RUN_LIMIT_CHECKPOINT`

The storage blocker was repaired without disturbing the healthy Hermes
runtime. Read-only forensics found a 30 GB root volume with 2.7 GB free, a
2.8 GB dangling build image, and package caches. Only the exact dangling build
image/intermediate layers and package caches were removed. Free space rose to
6.8 GB before rebuilding and 6.5 GB after the final image was installed.

## Workstation build and cutover

The version-controlled ARM64 layer is
[Containerfile.hermes-workstation](../../infra/hermes/Containerfile.hermes-workstation).
The successful image is ARM64, Hermes 0.20.6, 4,201,054,064 bytes, digest
`sha256:7821f2f04d63e5e2a841f891106d746f59b4a3095a629811a2e87d906a2f8755`.
It contains OpenCode, gh, jq, fd, Supabase, Netlify, Playwright 1.62.0, and
Chromium 1234. The missing `passwd` dependency and omitted `/usr/sbin` PATH
were corrected from direct startup evidence so Hermes can reconcile its UID
against the protected `/opt/data` mount.

The disposable mounted-state validation passed. The Quadlet was then switched
to the verified digest, restarted normally, and `/health` returned Hermes
0.20.6. The prior Quadlet is preserved at the Oracle-side pre-cutover backup.

## Remaining gates

CLI presence is proven, but harmless CLI commands have not yet been executed
through a Hermes worker. Worker-side skill attachment receipts remain
unimplemented (`0/3`). The corrected Kanban prerequisite semantics remain
valid, but the reviewer timeout means the full research → engineering →
reviewer chain and restart persistence are not yet proven. No real Nexus goal
was started in this bounded storage/build run, and no Portal goal was reopened.

```text
DURABLE_IMAGE_BUILD_PATH=PASS_REAL
HERMES_TOOLCHAIN_DURABLY_PROVISIONED=PASS_REAL
HERMES_TOOLCHAIN_SURVIVES_CONTAINER_REBUILD=PASS_REAL (build + disposable rebuild validation)
HERMES_CAN_CALL_OPENCODE=NOT_YET_CERTIFIED
HERMES_CAN_CALL_GH=NOT_YET_CERTIFIED
HERMES_CAN_CALL_JQ=NOT_YET_CERTIFIED
HERMES_CAN_CALL_FD=NOT_YET_CERTIFIED
HERMES_CAN_CALL_SUPABASE=NOT_YET_CERTIFIED
HERMES_CAN_CALL_NETLIFY=NOT_YET_CERTIFIED
HERMES_BROWSER=PASS_REAL_PRESENCE; worker browser canary pending
HERMES_SKILL_ATTACHMENT_PROVENANCE=NOT_REACHED
SKILL_RECEIPTS_COMPLETE=0/3
HERMES_REVIEWER_COMPLETION=FAIL (prior tool-loop failure)
HERMES_MULTI_AGENT_KANBAN=FAIL
HERMES_KANBAN_RESTART_PERSISTENCE=NOT_REACHED
R14_RESULT_TO_HERMES_TASK_HANDOFF=NOT_REACHED
REAL_GOAL_HERMES_AGENT_STACK_USED=NO
REAL_GOAL_MATERIAL_PROGRESS=NO
NEW_CRITERIA_VERIFIED=0
STABLE_HERMES_FEATURES_BYPASSED_WITHOUT_REASON=[]
TRUE_RAY_BLOCKERS=NONE
```

## Exact next action

Use the live workstation’s Hermes dispatcher to run harmless commands through
a specialist worker, instrument the actual worker startup/result boundary for
skill attachment receipts, rerun the native research → engineering → reviewer
graph with the orchestrator outside prerequisite edges, then route one
existing Nexus criterion through the normal broker. Do not replace the live
image or reopen either Portal goal.
