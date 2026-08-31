# Nova Live Resource Selection Trace

Campaign: `HG-WP6.5-NOVA-REAL-TELEGRAM-RESOURCE-EXECUTION-TRACE-AND-REPAIR-20260830-01`

## Findings

The existing five-stage graph already supports a model capability envelope and bounded continuation. The live failure was not a missing brain layer.

- Public web and retrieval envelopes were already allowlisted and executable through `shared.execute_shared_capability`.
- Nexus capability-map read was not exposed in the model envelope at the earlier failure point; it is now represented as `NEXUS_READ` / `NEXUS_CAPABILITY_MAP` and maps to the existing authorized capability-registry read.
- Alpha handoff validation could receive a request without an explicit objective. Contextual referent data is now accepted as the objective, and the explicit bounded Alpha handoff requests execution.
- Existing pre-model factual Nexus reads remain limited to relevant factual/company questions. No new router was added.

## Status

`RUNTIME_STAGE_COUNT=5`.

The current source does not contain enough historical receipt data to reconstruct the exact model output from the failed Telegram turns. The new focused test proves model envelope → broker validation → resource executor → result → model continuation for public web without exposing the envelope to the user.
