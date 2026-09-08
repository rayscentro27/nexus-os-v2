# Nexus / Hermes R15.1 Execution Plane Completion

## Checkpoint verdict

`NEXUS_HERMES_EXECUTION_PLANE_COMPLETION_R15_1=RUN_LIMIT_CHECKPOINT`

The dispatcher defect was repaired and independently retested. The root cause
was a real permissions mismatch: cloned test profile `config.yaml` and `.env`
files were `root:root` mode 600, while spawned workers run as `hermes:hermes`.
Changing ownership only on the five test profiles restored worker startup.

## Dispatcher proof

Three bounded dispatches passed:

- `t_e05913a1` / `nexus_engineer_test` / `codebase-inspection` → `ENGINEER_DISPATCH_OK`
- `t_cc6505b4` / `nexus_research_test` / `grounded-citations` → `RESEARCH_DISPATCH_OK`
- `t_2a864e0f` / `nexus_review_test` / `github-code-review` → `REVIEW_DISPATCH_OK`

Each task was created, claimed, spawned, heartbeated, and completed. The prior
stalled worker task `t_92c132db` was safely reclaimed. This proves:

```text
DISPATCH_TIMEOUT_LAYER_IDENTIFIED=YES
HERMES_DISPATCHER_WORKER_COMPLETION=PASS_REAL
DISPATCHER_TESTS_PASS=3/3
HERMES_WORKER_HEARTBEAT=PASS_REAL
HERMES_STALLED_WORKER_RECLAIM=PASS_REAL
HERMES_TASK_SKILL_PINNING=PASS_REAL
```

Kanban lifecycle and task-level skill pinning now work in scratch scope. A
multi-agent dependency/handoff graph and a separate machine-readable skill
attachment receipt were not proven.

## CLI results

The Oracle container has `git`, Python, Node/npm/npx, Docker, curl, ripgrep,
and Hermes. `gh`, Supabase CLI, Netlify CLI, Playwright on PATH, OpenCode,
jq, fd, pnpm, bun, Podman, and Ollama remain unavailable or uncertified. A
bounded npx probe for Netlify/Supabase did not return a usable executable.
No blind package installation or image rebuild was performed.

OpenCode therefore remains unavailable to Hermes in this environment; no
OpenCode adapter or real OpenCode workflow is claimed.

## Remaining gates

Telegram is not configured in the Oracle Hermes runtime. Local Nexus runtime
configuration contains token variable names, but no credential was copied or
exposed and no Telegram message was sent. The full Telegram workflow is not
proven.

The R14 result-to-Hermes-task handoff and a real existing Nexus goal through
the complete Hermes profile → Kanban → skill → CLI/MCP → reviewer path remain
unproven. No business goal was modified, and both Portal goals remain
`READY_FOR_HUMAN_REVIEW`.

## Contract

```text
HERMES_MULTI_AGENT_KANBAN=FAIL
HERMES_SKILL_ATTACHMENT_PROVENANCE=FAIL (partial task metadata only)
HERMES_CAN_CALL_OPENCODE=FAIL_WITH_EXACT_REASON (absent in Oracle container)
HERMES_CAN_CALL_GH=UNAVAILABLE_WITH_EXACT_REASON
HERMES_CAN_CALL_SUPABASE=UNAVAILABLE_WITH_EXACT_REASON
HERMES_CAN_CALL_NETLIFY=UNAVAILABLE_WITH_EXACT_REASON
HERMES_BROWSER=FAIL_WITH_EXACT_REASON (browser dependency unmet)
HERMES_FILE_WRITE=FAIL (prior bounded write loop timeout)
HERMES_FILE_EDIT=FAIL (prior bounded edit loop timeout)
HERMES_MEMORY_PERSISTENCE=FAIL (not proven)
HERMES_SESSION_CONTINUITY=FAIL (not proven)
HERMES_CRON_ROUTINE=UNAVAILABLE_WITH_EXACT_REASON (not tested)
HERMES_TELEGRAM_CONFIGURED=FAIL_WITH_EXACT_REASON (Oracle not configured)
HERMES_TELEGRAM_COMMAND_SURFACE=FAIL
TELEGRAM_FULL_HERMES_AGENT_WORKFLOW=FAIL_WITH_EXACT_REASON
R14_RESULT_TO_HERMES_TASK_HANDOFF=FAIL
REAL_GOAL_HERMES_AGENT_STACK_USED=NO
REAL_GOAL_MATERIAL_PROGRESS=NO
NEW_CRITERIA_VERIFIED=0
STABLE_HERMES_FEATURES_BYPASSED_WITHOUT_REASON=[]
TRUE_RAY_BLOCKERS=NONE
```

Machine-readable evidence is in `reports/runtime/nexus_hermes_r15_1_*.json`.

The next exact engineering action is to make the repaired dispatcher emit a
machine-verifiable skill-attachment receipt, then route one existing bounded
Nexus criterion through the normal broker into a proven Hermes specialist. CLI
installation and Telegram propagation should be handled only after their
durable, authorized Oracle configuration paths are identified.
