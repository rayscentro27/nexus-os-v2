# Nexus / Hermes R16.5 — Cost-Optimized Router

Status: `RUN_LIMIT_CHECKPOINT`

## Result

The cost-first investigation found no second healthy authenticated Hermes route. The existing free Nemotron route remains the only ready route and retains its latency/no-evidence penalty. Oracle already has Gemma 3 4B locally, but a bounded 60-second low-token chat probe did not return; it is not promoted as a fallback. The cloud-tagged DeepSeek model was not invoked because its auth and cost state were not established.

Hermes 0.20.6 exposes native model selection and fallback commands, but the live fallback chain is empty. No router or timeout configuration was changed, and no paid provider was invoked.

Because a second healthy route was not proven, the official OpenCode skill retry was correctly suppressed. This avoids repeating the known failure and does not indicate an OpenCode skill defect.

## Contract

```text
NEXUS_HERMES_COST_OPTIMIZED_ROUTER_R16_5=RUN_LIMIT_CHECKPOINT
LIVE_MODEL_ROUTE_COUNT=3
AUTHENTICATED_MODEL_ROUTE_COUNT=1
COST_CANDIDATES_RESEARCHED=6
FREE_ROUTE_CANDIDATES=2
LOW_COST_ROUTE_CANDIDATES=0
BEST_FREE_HERMES_MODEL=NONE_MEETS_RELIABILITY_GATE
BEST_LOW_COST_HERMES_MODEL=NONE
BEST_COST_OPTIMIZED_HERMES_MODEL=openrouter/nvidia/nemotron-3.5-lightning:free (only ready route; penalized)
SECONDARY_HERMES_CONTROL_MODEL=NONE
EXPECTED_COST_PER_SUCCESS_PRIMARY=UNKNOWN/UNBOUNDED
EXPECTED_COST_PER_SUCCESS_SECONDARY=UNKNOWN
HERMES_NATIVE_MODEL_ROUTER_ACTIVE=FAIL
HERMES_MULTI_MODEL_FAILOVER=FAIL
TIMEOUT_HIERARCHY_RECONCILED=FAIL
OPENCODE_SKILL_ATTACHMENT_PROVENANCE=NOT_REACHED
OPENCODE_PROCESS_INVOKED=NOT_REACHED
HERMES_CAN_CALL_OPENCODE=NOT_REACHED
OPENCODE_MULTI_MODEL_SELECTION=NOT_REACHED
COST_GOVERNOR=PARTIAL
COST_TELEMETRY=PARTIAL
HERMES_EXECUTION_PLANE_STATUS=PARTIAL
TRUE_RAY_BLOCKERS=SECOND_AUTHENTICATED_HEALTHY_HERMES_MODEL_ROUTE_REQUIRED
```

Exact next action: authorize or expose one additional Hermes-supported provider/model through its native authentication mechanism, benchmark it on the lightweight tool task, then configure the native fallback chain and rerun the official OpenCode skill.
