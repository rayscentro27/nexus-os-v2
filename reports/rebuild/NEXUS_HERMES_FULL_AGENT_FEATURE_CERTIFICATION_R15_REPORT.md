# Nexus / Hermes R15 Full Agent Feature Certification

## Verdict

`NEXUS_HERMES_FULL_AGENT_FEATURE_CERTIFICATION_R15=RUN_LIMIT_CHECKPOINT`

Hermes 0.20.6 is live and exposes a substantial native CLI surface. The
bounded tests proved native profiles can be created and directly invoked,
Kanban's manual lifecycle works in scratch scope, MCP discovery works, and
the individually certified R12.6 terminal/file-read/execute-code/subagent
capabilities remain valid. Full multi-agent unattended certification did not
pass: a real Kanban dispatcher worker remained running beyond its 30-second
bound and was reclaimed; no business goal was routed through the full Hermes
stack.

## Live feature results

| Feature | Result | Evidence / limitation |
|---|---|---|
| Hermes version | PASS_REAL | 0.20.6, build `5fc308a7` |
| Test profiles | PARTIAL | five created from authenticated default; three direct profile turns passed; two did not finish within bound |
| Named worker | PARTIAL | profile identity works, dispatched worker did not return |
| Kanban lifecycle | PASS_REAL | scratch task `t_0f597ebe`: create, claim, comment, review, complete |
| Kanban dispatch / multi-agent | FAIL | task `t_92c132db` spawned but exceeded bound and was reclaimed |
| Skill discovery | PASS_REAL | 78 installed skills listed |
| Skill attachment / learning | PARTIAL | attachment provenance not machine-verifiable; learning requires approval |
| MCP | PASS_REAL | `nexus_mcp_remote` connected; 7 tools discovered; R12.6 execution evidence retained |
| Terminal | PASS_REAL | R12.6 individual probe |
| File read | PASS_REAL | R12.6 individual probe |
| File write/edit | FAIL | R12.6 write/edit loop timeout |
| Execute code | PASS_REAL | R12.6 deterministic probe |
| Subagents | PASS_REAL | R12.6 bounded delegation probe |
| Browser | FAIL | R12.6 browser tool-loop timeout |
| Telegram | UNAVAILABLE | live status says Telegram is not configured |
| Memory/session/cron/plugins | PRESENT_NOT_TESTED | no safe R15 proof receipt |

## CLI toolchain

The Oracle container exposes: `git`, Python 3.13.5, Node 26.5.1, npm/npx
11.17.0, Docker 26.1.5, curl, ripgrep, and Hermes 0.20.6. It does not expose
`gh`, pnpm, bun, Supabase CLI, Netlify CLI, Podman, jq, fd, Playwright,
OpenCode, Codex, or Ollama. The CLI matrix is in
`reports/runtime/nexus_hermes_r15_cli_matrix.json`.

## Native profile and Kanban evidence

Five test-only profiles were created by cloning the authenticated default
profile; no production profile was changed and no secret was exposed. A
manual scratch Kanban lifecycle completed successfully. A dispatcher-created
worker task was then bounded, reclaimed, and archived after it failed to
complete. This proves the dispatcher path is present, not that it is reliable
enough for Nexus autonomous use.

## Nexus integration and real-goal result

No R15 code was changed to force Hermes into production routing. No existing
Nexus business goal was selected through the full Hermes profile → Kanban →
skill → CLI/MCP → review stack. Therefore:

```text
HERMES_CAN_CALL_OPENCODE=FAIL_WITH_EXACT_REASON (OpenCode absent in Oracle container)
R14_RESULT_TO_HERMES_TASK_HANDOFF=FAIL (not proven)
REAL_GOAL_HERMES_AGENT_STACK_USED=NO
REAL_GOAL_MATERIAL_PROGRESS=NO
NEW_CRITERIA_VERIFIED=0
```

Portal states remained `READY_FOR_HUMAN_REVIEW`. No production deployment,
customer mutation, spending, outreach, public publishing, live trading, or
secret exposure occurred.

## Exact remaining gap

The native Hermes feature surface is not yet a reliable governed Nexus worker
loop. The missing proof is bounded dispatcher completion and result return
under the cloned specialist profiles, followed by machine-verifiable skill
attachment and one normal Nexus real-goal canary. Browser and file-edit
tool-loop failures remain separately unhealthy. Telegram is not configured.

Machine-readable evidence:

- `reports/runtime/nexus_hermes_r15_feature_matrix.json`
- `reports/runtime/nexus_hermes_r15_cli_matrix.json`
- `reports/runtime/nexus_hermes_r15_profiles.json`
- `reports/runtime/nexus_hermes_r15_kanban_receipts.json`
- `reports/runtime/nexus_hermes_r15_skill_receipts.json`
- `reports/runtime/nexus_hermes_r15_telegram_canary.json`
- `reports/runtime/nexus_hermes_r15_real_goal_canary.json`

```text
HERMES_VERSION=0.20.6
HERMES_TEST_PROFILES=PARTIAL
HERMES_NAMED_AGENT_WORKER=PARTIAL
HERMES_MULTI_AGENT_KANBAN=FAIL_WITH_EXACT_REASON
HERMES_KANBAN_RESTART_PERSISTENCE=NOT_PROVEN
HERMES_SKILL_DISCOVERY=PASS_REAL
HERMES_SKILL_ATTACHMENT=PARTIAL
HERMES_SKILL_LEARNING_LOOP=AVAILABLE_REQUIRES_APPROVAL
HERMES_NATIVE_TERMINAL=PASS_REAL
HERMES_FILE_READ=PASS_REAL
HERMES_FILE_WRITE=FAIL_WITH_EXACT_REASON
HERMES_FILE_EDIT=FAIL_WITH_EXACT_REASON
HERMES_EXECUTE_CODE=PASS_REAL
HERMES_SUBAGENT_DELEGATION=PASS_REAL
HERMES_MCP_EXECUTION=PASS_REAL
HERMES_TOOL_SEARCH=PASS_REAL (R12.6 discovery evidence)
HERMES_BROWSER=FAIL_WITH_EXACT_REASON
HERMES_MEMORY_PERSISTENCE=NOT_PROVEN
HERMES_SESSION_CONTINUITY=NOT_PROVEN
HERMES_CRON_ROUTINE=NOT_PROVEN
HERMES_PLUGIN_HOOKS=PRESENT_NOT_TESTED_WITH_REASON
HERMES_TELEGRAM_COMMAND_SURFACE=FAIL (not configured)
TELEGRAM_FULL_HERMES_AGENT_WORKFLOW=FAIL_WITH_EXACT_REASON
R14_RESULT_TO_HERMES_TASK_HANDOFF=FAIL
REAL_GOAL_HERMES_AGENT_STACK_USED=NO
REAL_GOAL_MATERIAL_PROGRESS=NO
TRUE_RAY_BLOCKERS=NONE
```
