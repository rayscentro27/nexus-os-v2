# Nexus GoClear Automation Policy

See [NEXUS_AUTOMATION_LEVELS.md](NEXUS_AUTOMATION_LEVELS.md). Covers GoClear Revenue Hub.

- **Level 1 (autonomous):** internal revenue metric cards, internal reports, scoring.
- **Level 2 (approval-gated):** lead contact, payment-link creation, campaign publishing,
  scheduler activation. Nexus prepares; Ray approves before anything reaches a lead/customer.
- **Level 3 (blocked):** payment/spend actions, destructive DB writes.

No money leaves the building without explicit Ray approval. The `goclear_revenue_hub_feeder` is
Level 1 for internal cards and escalates lead-contact / payment work to Ray.
