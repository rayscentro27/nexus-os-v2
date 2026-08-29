# Telegram Routing Certification (WP5)

The new closed-world resolver is implemented in
`scripts/nexus_agent_platform/department_router.py`. It validates every
resolved loop, skill, worker, and department against canonical registries and
fails closed on unknown or unavailable routes.

Human-gate `APPROVE` / `HOLD` messages remain ahead of operator routing and are
handled by `human_gate_router.py`; ordinary Hermes conversation cannot spoof
approval. Real Telegram E2E remains pending execution and evidence.
