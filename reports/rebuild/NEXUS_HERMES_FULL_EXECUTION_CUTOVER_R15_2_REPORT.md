# Nexus / Hermes R15.2 Full Execution Cutover

## Verdict

`NEXUS_HERMES_FULL_EXECUTION_CUTOVER_R15_2=RUN_LIMIT_CHECKPOINT`

The R15.1 dispatcher repair remains valid: profile ownership was corrected
and three specialist smoke dispatches completed. R15.2 did not prove the full
cutover. The native Kanban graph revealed a dependency-semantics defect before
child execution: children linked to a running orchestrator cannot claim until
the parent is done.

## Multi-agent evidence

Scratch parent `t_bf11da8c` spawned and heartbeated. Its researcher child
`t_ab3e8fa6` was promoted but Hermes rejected the claim with
`parents_not_done`; engineer `t_ecd1363a` and reviewer `t_5fbedb6a` remained
blocked. The orchestrator only inspected child status and did not dispatch
children. All scratch tasks were reclaimed/archived safely.

Therefore:

```text
HERMES_MULTI_AGENT_KANBAN=FAIL
HERMES_KANBAN_RESTART_PERSISTENCE=FAIL (not proven)
HERMES_SKILL_ATTACHMENT_PROVENANCE=FAIL
HERMES_TASK_SKILL_PINNING=PASS_REAL (metadata persisted)
```

## CLI and Telegram state

The container still has git, Python, Node/npm/npx, Docker, curl, ripgrep, and
Hermes. OpenCode, gh, Supabase CLI, Netlify CLI, jq, fd, and a PATH Playwright
executable remain unavailable or uncertified. No durable installation was
performed without a verified ARM64 image/path strategy.

Telegram remains unconfigured in Oracle. Existing local runtime token names
were not copied or exposed, and no message was sent.

## Real Nexus goal

No existing company goal was routed through the complete Nexus → Hermes
Kanban → specialist → skill receipt → tool/CLI → reviewer → Nexus verifier
chain. Consequently:

```text
R14_RESULT_TO_HERMES_TASK_HANDOFF=FAIL
INVALID_MODEL_PLAN_TO_HERMES_RECOVERY=FAIL
PASS_WITHOUT_DELTA_TO_HERMES_RECOVERY=FAIL
REAL_GOAL_HERMES_AGENT_STACK_USED=NO
REAL_GOAL_MATERIAL_PROGRESS=NO
NEW_CRITERIA_VERIFIED=0
```

Portal goals were not reopened and remain `READY_FOR_HUMAN_REVIEW`.

## Exact remaining engineering action

Repair or configure the native Kanban dependency/handoff contract so an
orchestrator can create and dispatch children while remaining active, with
durable result and skill-attachment receipts. Then certify the dependency
graph, install/expose only the required CLI paths, and route one existing
Nexus criterion through the full stack. Telegram configuration is separate and
requires propagating the already-authorized bot configuration through the
protected Oracle path without exposing its secret.

Machine-readable evidence is in `reports/runtime/nexus_hermes_r15_2_*.json`.

```text
HERMES_CAN_CALL_OPENCODE=FAIL_WITH_EXACT_REASON (absent in Oracle container)
HERMES_CAN_CALL_GH=BLOCKED_WITH_EXACT_REASON (absent)
HERMES_CAN_CALL_JQ=FAIL
HERMES_CAN_CALL_FD=FAIL
HERMES_CAN_CALL_SUPABASE=BLOCKED_WITH_EXACT_REASON (absent)
HERMES_CAN_CALL_NETLIFY=BLOCKED_WITH_EXACT_REASON (absent)
HERMES_BROWSER=FAIL_WITH_EXACT_REASON (dependency unmet)
HERMES_FILE_WRITE=FAIL
HERMES_FILE_EDIT=FAIL
HERMES_MEMORY_PERSISTENCE=FAIL (not proven)
HERMES_SESSION_CONTINUITY=FAIL (not proven)
HERMES_CRON_ROUTINE=UNAVAILABLE_WITH_EXACT_REASON (not tested)
HERMES_TELEGRAM_CONFIGURED=FAIL_WITH_EXACT_REASON
HERMES_TELEGRAM_BASIC_ROUNDTRIP=FAIL
HERMES_TELEGRAM_COMMAND_SURFACE=FAIL
TELEGRAM_FULL_HERMES_AGENT_WORKFLOW=FAIL
TRUE_RAY_BLOCKERS=NONE
```
