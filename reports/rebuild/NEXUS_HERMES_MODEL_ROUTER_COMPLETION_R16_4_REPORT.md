# Nexus / Hermes R16.4 — Model Router Completion

Status: `RUN_LIMIT_CHECKPOINT`

## Live findings

Hermes 0.20.6 supports model selection via its native CLI and its installed configuration documents fallback providers. The actual live fallback chain is empty. Active profiles use OpenRouter through the local inference proxy with `nvidia/nemotron-3.5-lightning:free`; that route retains the prior latency penalty.

The local `/v1/models` endpoint advertises `gemma3:4b` and `deepseek-v4-pro:cloud`, but advertising is not a ready Hermes route. A bounded Gemma chat probe produced no response within 20 seconds. Other configured provider families have no safe ready authentication evidence. Thus the authenticated route count remains one.

## Consequence

R16.4 did not widen timeouts, copy credentials, or rerun the official OpenCode task under the same failing control model. The official skill remains present/loadable from R16.3, but OpenCode process execution, reviewer completion, restart persistence, browser proof, and real engineering progress were not reached.

The exact remaining blocker is an authorized second healthy Hermes control-model route. This is an external authorization/configuration boundary, not an OpenCode integration defect. No production state or Portal goal was changed.

## Contract

```text
NEXUS_HERMES_MODEL_ROUTER_COMPLETION_R16_4=RUN_LIMIT_CHECKPOINT
LIVE_MODEL_ROUTE_COUNT=3
AUTHENTICATED_MODEL_ROUTE_COUNT=1
BEST_HERMES_CONTROL_MODEL=openrouter/nvidia/nemotron-3.5-lightning:free (penalized)
SECONDARY_HERMES_CONTROL_MODEL=NONE
HERMES_NATIVE_MODEL_ROUTER_ACTIVE=FAIL
HERMES_MULTI_MODEL_FAILOVER=FAIL
TIMEOUT_HIERARCHY_RECONCILED=FAIL
OPENCODE_SKILL_ATTACHMENT_PROVENANCE=NOT_REACHED
OPENCODE_PROCESS_INVOKED=FAIL
HERMES_PROCESS_SUPERVISION=NOT_REACHED
OPENCODE_CODE_CHANGE_CORRECT=FAIL
HERMES_REVIEWER_COMPLETION=FAIL
OPENCODE_RESULT_NORMALIZATION=FAIL
HERMES_CAN_CALL_OPENCODE=FAIL
HERMES_PLAYWRIGHT_CLI_BROWSER=NOT_REACHED
HERMES_KANBAN_RESTART_PERSISTENCE=NOT_REACHED
REAL_ENGINEERING_HERMES_STACK_USED=NOT_REACHED
REAL_ENGINEERING_TASK_MATERIAL_PROGRESS=NOT_REACHED
NEW_ENGINEERING_CRITERIA_VERIFIED=0
MULTI_DEPARTMENT_HERMES_EXECUTION=NOT_REACHED
HERMES_EXECUTION_PLANE_STATUS=PARTIAL
STABLE_HERMES_FEATURES_BYPASSED_WITHOUT_REASON=[]
TRUE_RAY_BLOCKERS=SECOND_AUTHENTICATED_HEALTHY_HERMES_MODEL_ROUTE_REQUIRED
```
