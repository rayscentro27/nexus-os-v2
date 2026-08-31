# Nova Resource Execution Repair

Baseline: `0b178e9`

Repairs:

1. Exposed Nexus capability-map reads through the existing model capability protocol, mapping to `get_capability_registry` behind the existing shared read boundary.
2. Preserved public web execution and model continuation through the existing generation stage.
3. Made Alpha model handoffs resilient when the objective is represented by a conversational referent.
4. Changed explicit conversational Alpha handoff to request bounded read-only research execution, while retaining governed intake and no operational mutation.

No new stage, router, provider, or direct Nexus authority was added. Resource failures still return structured capability results to Nova’s continuation path.
