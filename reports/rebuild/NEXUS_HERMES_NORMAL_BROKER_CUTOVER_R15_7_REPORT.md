# Nexus Hermes Normal Broker Cutover R15.7

## Result

The normal Nexus selector now discovers and scores `hermes.kanban.executor`,
and the selected candidate is dispatched through the live Oracle Hermes Kanban
surface. Nexus retains criterion verification authority and does not claim
completion from worker status alone.

## Exact cutover

`select_and_execute()` derives typed requirements, calls the existing unified
selector, and resolves the selected Hermes candidate to
`execute_with_hermes_kanban()`. The executor uses only the fixed, allowlisted
Podman/Hermes CLI surface over the existing Oracle SSH path. It creates a task,
dispatches it, polls the canonical nested `task.status`, and normalizes the
result including worker run errors.

The real canary was the existing `opportunity.engine` goal. Normal scoring
selected Hermes (`15.75`) over Research/Alpha (`15.125`). Task `t_ca9d36f9`
was created with Nexus `research-intelligence` mapped to the installed Hermes
`sdlc-review` skill. The worker was reclaimed/requeued after a model response
timeout (`elapsed 45s > limit 40s`), so no criterion delta was claimed.

## Remaining boundary

The executor boundary is implemented and unit-tested, but the real goal did
not materially advance in this bounded run. The remaining break is live Hermes
worker model-response reliability on the selected task, followed by the
criterion-verification/continuation pass. OpenCode, fd, Playwright, and restart
persistence were not retried in this cutover run.

## Safety

No portal goal was reopened, no production mutation or external action was
performed, and no secret was exposed. `API_SERVER_KEY` remained Oracle-side.

## Contract

NEXUS_HERMES_NORMAL_BROKER_CUTOVER_R15_7=RUN_LIMIT_CHECKPOINT
NORMAL_BROKER_HERMES_EXECUTOR_REGISTERED=YES
HERMES_SELECTED_BY_NORMAL_SCORING=PASS_REAL
ACTIVE_OPERATOR_CAN_ROUTE_TO_HERMES=PASS_REAL (shared unified selector boundary)
NORMAL_PORTFOLIO_LOOP_CAN_ROUTE_TO_HERMES=PASS_REAL (shared unified selector boundary)
R14_RESULT_TO_HERMES_TASK_HANDOFF=PASS_REAL (executor contract and route)
INVALID_MODEL_PLAN_TO_HERMES_RECOVERY=PASS_REAL (contract route; live recovery not exercised)
PASS_WITHOUT_DELTA_TO_HERMES_RECOVERY=PASS_REAL (normalized NO_PROGRESS recovery hint)
RESULT_TO_NEXT_HERMES_ACTION_CONTINUATION=FAIL (live worker timed out before result)
REAL_GOAL_HERMES_AGENT_STACK_USED=NO
REAL_GOAL_MATERIAL_PROGRESS=NO
NEW_CRITERIA_VERIFIED=0
HERMES_CAN_CALL_OPENCODE=FAIL (not re-run; prior direct-edit evidence)
HERMES_CAN_CALL_FD=FAIL (not re-run; prior proof unsuccessful)
HERMES_PLAYWRIGHT_CLI_BROWSER=FAIL (not re-run; prior worker failure)
HERMES_KANBAN_RESTART_PERSISTENCE=NOT_REACHED
STABLE_HERMES_FEATURES_BYPASSED_WITHOUT_REASON=[]
TRUE_RAY_BLOCKERS=NONE
