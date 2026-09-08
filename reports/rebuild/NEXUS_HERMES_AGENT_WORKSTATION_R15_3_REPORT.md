# Nexus / Hermes R15.3 Agent Workstation

## Verdict

`NEXUS_HERMES_AGENT_WORKSTATION_R15_3=RUN_LIMIT_CHECKPOINT`

The live 0.20.6 source confirms that Kanban `parents` are prerequisite edges,
not an active hierarchical container. `create_task`, `recompute_ready`, and
`claim_task` all require linked parents to be `done` or `archived` before a
child can claim. R15.2 therefore modeled the graph incorrectly; Hermes was not
patched.

## Native-semantics graph

Using the corrected graph, research `t_0b222960` completed and its dependent
engineering task `t_864ffd5b` was automatically promoted and completed. The
reviewer `t_6d04f968` was dispatched after engineering completion but timed out
at 60 seconds against a 45-second task limit. The scratch orchestrator tracker
also accumulated a stale run and was reclaimed. The graph is therefore only
partially proven:

```text
PARENTS_MEANING=PREREQUISITE
HERMES_ORCHESTRATION_GRAPH_USES_NATIVE_SEMANTICS=YES
HERMES_MULTI_AGENT_KANBAN=FAIL
HERMES_KANBAN_RESTART_PERSISTENCE=FAIL (not proven)
```

## Skill evidence

Kanban task metadata pinned `grounded-citations`, `codebase-inspection`, and
`github-code-review` to the respective workers. The first two workers
completed, but Hermes did not emit an independent worker-side skill attachment
receipt. `HERMES_SKILL_ATTACHMENT_PROVENANCE=FAIL`.

## Workstation/toolchain

The Oracle host is ARM64 and the running container mounts durable state at
`/opt/data`, but the base image and durable Containerfile/build path were not
recovered in this bounded run. The required CLIs remain absent: OpenCode, gh,
jq, fd, Supabase, Netlify, and Playwright/browser dependencies. No disposable
interactive install is being misrepresented as durable provisioning.

Telegram remains unconfigured in Oracle; no message or credential was sent.

## Real Nexus goal

No existing Nexus business goal completed the required Nexus → Hermes Kanban →
specialist → skill receipt → CLI/tool → reviewer → Nexus verifier chain. No
criterion was verified and no material business progress occurred. Portal
goals were preserved at `READY_FOR_HUMAN_REVIEW`.

```text
HERMES_TOOLCHAIN_DURABLY_PROVISIONED=FAIL
HERMES_TOOLCHAIN_SURVIVES_CONTAINER_REBUILD=FAIL
HERMES_CAN_CALL_OPENCODE=FAIL
HERMES_CAN_CALL_GH=FAIL
HERMES_CAN_CALL_JQ=FAIL
HERMES_CAN_CALL_FD=FAIL
HERMES_CAN_CALL_SUPABASE=FAIL
HERMES_CAN_CALL_NETLIFY=FAIL
HERMES_BROWSER=FAIL
HERMES_FILE_WRITE=FAIL (prior bounded write-loop timeout)
HERMES_FILE_EDIT=FAIL (prior bounded edit-loop timeout)
HERMES_MEMORY_PERSISTENCE=FAIL (not proven)
HERMES_SESSION_CONTINUITY=FAIL (not proven)
HERMES_TELEGRAM_CONFIGURED=FAIL_WITH_EXACT_REASON
TELEGRAM_FULL_HERMES_AGENT_WORKFLOW=FAIL
R14_RESULT_TO_HERMES_TASK_HANDOFF=FAIL
REAL_GOAL_HERMES_AGENT_STACK_USED=NO
REAL_GOAL_MATERIAL_PROGRESS=NO
NEW_CRITERIA_VERIFIED=0
STABLE_HERMES_FEATURES_BYPASSED_WITHOUT_REASON=[]
TRUE_RAY_BLOCKERS=NONE
```

Machine-readable evidence is in `reports/runtime/nexus_hermes_r15_3_*.json`.

## Exact next action

Recover or define the version-controlled ARM64 Hermes image build/start path,
add the required tools durably, and implement a worker-side attachment receipt
at the real dispatcher boundary. Then rerun the corrected executable
dependency chain with an orchestrator that monitors externally rather than
being a prerequisite parent, followed by one existing Nexus criterion.
