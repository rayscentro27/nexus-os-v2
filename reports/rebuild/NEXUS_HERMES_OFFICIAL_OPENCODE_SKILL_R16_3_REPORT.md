# Nexus / Hermes R16.3 — Official OpenCode Skill Certification

Status: `RUN_LIMIT_CHECKPOINT`

## Live skill evidence

Hermes 0.20.6 reports the bundled `opencode` skill as enabled. The live instruction file is:

`/opt/hermes/skills/autonomous-ai-agents/opencode/SKILL.md`

It is builtin, version 1.2.0, and loadable. Its prescribed bounded path is `opencode run PROMPT`; interactive work uses Hermes terminal/process supervision with a PTY and polling. No raw Nexus OpenCode adapter was created.

## Real worker attempt

Task `t_d3f67f79` was created with the official `opencode` skill plus `codebase-inspection` and `worktree-safety`. The task’s live Kanban record shows those resolved skills. The disposable repository was `/tmp/nexus-opencode-r163-2ol0qkb7` and OpenCode 1.18.29 was present at `/usr/local/bin/opencode`.

Worker run 66 started and timed out at 99 seconds against the 90-second bound. Hermes automatically retried as run 67, which was still running at the observation boundary. No direct OpenCode process evidence, changed file, test result, diff, result envelope, worker-side skill receipt, or reviewer result was available. Therefore the official skill is present and loadable, but execution is not certified.

The observed failure is a model-response timeout before tool execution, not evidence that the official OpenCode skill is absent or defective. No production state was changed.

## Contract

```text
NEXUS_HERMES_OFFICIAL_OPENCODE_SKILL_R16_3=RUN_LIMIT_CHECKPOINT
OPENCODE_SKILL_PRESENT=YES
OPENCODE_SKILL_INSTALL_REQUIRED=NO
OPENCODE_SKILL_LOADABLE=YES
OPENCODE_SKILL_ATTACHMENT_PROVENANCE=FAIL
OPENCODE_CLI_PRESENT=PASS_REAL
OPENCODE_PROCESS_INVOKED=FAIL
OPENCODE_CODE_CHANGE_CORRECT=FAIL
HERMES_REVIEWER_COMPLETION=FAIL
OPENCODE_RESULT_NORMALIZATION=FAIL
HERMES_CAN_CALL_OPENCODE=FAIL
NORMAL_BROKER_SELECTED_OPENCODE=NOT_REACHED
REAL_ENGINEERING_TASK_MATERIAL_PROGRESS=NOT_REACHED
NEW_ENGINEERING_CRITERIA_VERIFIED=0
TRUE_RAY_BLOCKERS=NONE
```

The next bounded repair is to provide a healthy/faster authenticated Hermes model route or a proven model override for this engineering profile, then rerun the same official-skill task. The skill itself should not be replaced with a raw adapter.
