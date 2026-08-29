# Telegram Routing Certification (WP5)

The new closed-world resolver is implemented in
`scripts/nexus_agent_platform/department_router.py`. It validates every
resolved loop, skill, worker, and department against canonical registries and
fails closed on unknown or unavailable routes.

Human-gate `APPROVE` / `HOLD` messages remain ahead of operator routing and are
handled by `human_gate_router.py`; ordinary Hermes conversation cannot spoof
approval. Real Telegram E2E remains pending execution and evidence.

The strict execution resolver is not applied to every message. Conversation
and state-query lanes are explicit, while unknown execution requests remain
fail-closed.

Routing correction certified locally: `Hello Nexus, how are you today?` maps
to `CONVERSATIONAL_LANE`; `What is the current status of Nexus?` maps to
`READ_ONLY_STATE_LANE`. Neither requires a department, loop, worker, or
executor.
