# Nexus Hermes Live Worker Reliability R15.8

## Outcome

The normal Nexus broker selected Hermes for the existing
`opportunity.engine` / `opportunity-scoring` criterion. The original task
`t_ca9d36f9` demonstrated a 45-second worker timeout against a 40-second cap,
then completed on a retry in 51 seconds with only a receipt-confirmation
summary. No criterion completion was claimed.

The policy was changed to enforce a bounded 75-second minimum task budget. A
fresh retry (`t_9dd66c78`) still exceeded the live dispatcher boundary: run 64
was timed out after 130 seconds against the 75-second task limit and requeued.
Thus the remaining defect is live Hermes worker/model-response latency and
dispatcher timeout reconciliation, not broker discovery or authorization.

## Direct evidence

Profile: `nexus_research_test`; provider: `openrouter`; model:
`nvidia/nemotron-3.5-lightning:free`. The worker emitted heartbeats and was
reclaimed/requeued by Hermes. This is classified as
`MODEL_TOO_SLOW_FOR_CURRENT_LIMIT`, not a hung SSH transport. The skill alias
fix is active (`research-intelligence` → installed Hermes `sdlc-review`).

## Contract

NEXUS_HERMES_LIVE_WORKER_RELIABILITY_R15_8=RUN_LIMIT_CHECKPOINT
MODEL_TIMEOUT_SOURCE_IDENTIFIED=YES
MODEL_RESPONSE_TIMEOUT_POLICY_REPAIRED=PASS_REAL (bounded 75s Nexus floor; live dispatcher still requires reconciliation)
MODEL_LATENCY_SAMPLES=4
REAL_GOAL_HERMES_EXECUTION_COMPLETED=FAIL
NEXUS_VERIFIER_RAN=FAIL (no trustworthy criterion result returned)
RESULT_TO_NEXT_HERMES_ACTION_CONTINUATION=FAIL
NO_PROGRESS_TRIGGERED_MATERIAL_STRATEGY_CHANGE=NOT_NEEDED
ALTERNATE_CAPABILITY_FALLBACK_WORKS=NOT_REACHED
REAL_GOAL_HERMES_AGENT_STACK_USED=NO
REAL_GOAL_MATERIAL_PROGRESS=NO
NEW_CRITERIA_VERIFIED=0
ACTIVE_OPERATOR_HERMES_LIVE_EXECUTION=NOT_REACHED
NORMAL_PORTFOLIO_HERMES_LIVE_EXECUTION=NOT_REACHED
HERMES_CAN_CALL_OPENCODE=NOT_REACHED
HERMES_CAN_CALL_FD=NOT_REACHED
HERMES_PLAYWRIGHT_CLI_BROWSER=NOT_REACHED
HERMES_KANBAN_RESTART_PERSISTENCE=NOT_REACHED
STABLE_HERMES_FEATURES_BYPASSED_WITHOUT_REASON=[]
TRUE_RAY_BLOCKERS=NONE

No portal goal was reopened and no secret or external side effect occurred.
