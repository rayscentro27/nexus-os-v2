# Nexus Hermes Adaptive Model Routing R15.9

The live Oracle profile has one configured authenticated route:
`openrouter / nvidia/nemotron-3.5-lightning:free`. Hermes fallback inspection
returned an empty chain. No unauthenticated or invented provider was advertised.

The previous evidence is direct: the same profile completed one bounded turn in
51 seconds after a 45-second timeout, while a 75-second task later reached a
130-second dispatcher timeout/reclaim. This confirms
`MODEL_TOO_SLOW_FOR_CURRENT_LIMIT`; increasing the limit alone is insufficient.

The adaptive routing module now fingerprints provider + model + task class,
penalizes failures, ranks healthy routes, and rejects receipt-only prose unless
the worker returns a structured criterion envelope with matching IDs, expected /
observed fields, non-empty evidence items, and remaining delta. The executor
also preserves Hermes skill aliasing and canonical run outcomes.

The existing `opportunity.engine` criterion was selected through the normal
broker and routed to Hermes, but no trustworthy structured evidence was returned
within the bounded window. Nexus verification therefore did not run and no
canonical progress was claimed.

NEXUS_HERMES_ADAPTIVE_MODEL_ROUTING_R15_9=RUN_LIMIT_CHECKPOINT
MODEL_CANDIDATES_TESTED=1
CURRENT_NEMOTRON_ROUTE_PENALIZED=YES
HERMES_MODEL_FAILOVER=PASS_REAL (policy implemented; no second authenticated Hermes route live)
MODEL_FAILURE_LEARNING_USED_IN_SCORING=PASS_REAL
TIMEOUT_HIERARCHY_RECONCILED=FAIL (live dispatcher 130s boundary remains inconsistent with Nexus polling window)
CRITERION_SHAPED_TASK_CONTRACT=PASS_REAL
STRUCTURED_WORKER_EVIDENCE=PASS_REAL (strict validation; live valid envelope not returned)
REAL_GOAL_EXECUTION_COMPLETED=FAIL
NEXUS_VERIFIER_RAN=FAIL
RESULT_TO_NEXT_HERMES_ACTION_CONTINUATION=FAIL
ALTERNATE_CAPABILITY_FALLBACK_WORKS=NOT_REACHED
HERMES_PATH_FAILED_BUT_GOAL_REROUTED=NO
REAL_GOAL_HERMES_AGENT_STACK_USED=NO
REAL_GOAL_MATERIAL_PROGRESS=NO
NEW_CRITERIA_VERIFIED=0
ACTIVE_OPERATOR_LIVE_EXECUTION=NOT_REACHED
HERMES_CAN_CALL_OPENCODE=NOT_REACHED
STABLE_HERMES_FEATURES_BYPASSED_WITHOUT_REASON=[]
TRUE_RAY_BLOCKERS=NONE

No Portal goal was reopened; no secret or external side effect occurred.
