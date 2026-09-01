# Delivery completeness repair

Composed Hermes responses continue through the existing durable delivery
record. A progress-only model final is no longer considered a composed answer.
If both native attempts fail to produce a complete answer, the exception keeps
the update unadvanced so it can be retried rather than silently discarded.

Existing Telegram delivery retry/idempotency and terminal-outcome contracts are
preserved.
