# Nexus Command Acknowledgement Contract

Nova may translate a natural-language request into a Nexus command, but Nexus must acknowledge the command before any execution claim is made.

Required lifecycle:

`RECEIVED → ASSIGNED → QUEUED → STARTED → COMPLETED`

or a terminal safe outcome:

`RECEIVED → BLOCKED | REJECTED | FAILED`

Each acknowledgement contains `request_id`, optional `work_order_id`, assigned department/worker or queue, authority status, current state, timestamp, receipt reference, and `authority=NEXUS_TRUTHKERNEL`. The acknowledgement builder does not claim completion when a request is merely queued.

Implementation: `scripts/nexus_agent_platform/nexus_command_acknowledgement.py`. Existing governed work-order and campaign execution paths remain the execution authority; this module is a typed contract boundary, not a second queue.

Nova has no write allowlist. Approval continuity remains explicit and scoped; casual conversation cannot mutate TruthKernel.

