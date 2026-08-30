# Nova Fresh Session Migration

Baseline: `6114790`  
Implementation: memory-boundary migration only; the five-layer graph was not changed.

## Session result

- Old session: chat-backed Nova memory for the authorized Ray conversation; archived with timestamped filename.
- Fresh active session reference: `nova_0a662030c9c7277b`.
- Active memory schema: `3`.
- Capability state: `QUERY_ON_DEMAND`.
- Historical source: preserved in `scripts/data/runtime/nova_memory_archive/`.
- Active stale capability assertions: `0`.

Nova’s durable identity and business context remain in the SOUL/profile and current company-context mechanisms. Volatile capability state, service health, OAuth status, and temporary provider failures are not copied into active memory.

The migration deliberately does not claim that the resulting session has completed Telegram E2E proof; that requires Ray’s fresh Telegram prompts.
