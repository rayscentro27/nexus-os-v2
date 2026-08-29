# Telegram Failure / Recovery Contract

Unauthorized identities, duplicate updates, malformed input, unknown intent,
missing loop/skill/worker/capability, unavailable Oracle/bridge/provider,
executor failure, stale state, receipt failure, and send failure must produce
an explicit blocked/degraded result. No success or authority is invented.

The update offset and per-update sanitized receipt preserve idempotency. The
legacy route remains available for rollback until real WP5 E2E certification.
