# Nexus Specialist Architecture Audit

Current reusable structures: `scripts/nexus_agent_platform/agents/` (specialist
profiles), `governed/work_orders.py` (durable lifecycle/idempotency),
`loops/kernel.py` (bounded receipts), `loops/skill_resolver.py` (skills),
`capability_broker.py`/`access_resolver.py` (capability and authority), and the
existing Alpha, Creative, Growth, Clyde, Jax, and Trading paths. These are
`REUSE` or `ADAPT`, not a second runtime. Legacy conversational/router paths
are `SUPERSEDED` for this foundation.

The new `scripts/nexus_foundation/contracts.py` is a JSON-safe normalization
layer. It does not execute external actions or grant authority.

