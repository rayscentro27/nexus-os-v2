# Telegram Failure / Recovery Contract

Unauthorized identities, duplicate updates, malformed input, unknown intent,
missing loop/skill/worker/capability, unavailable Oracle/bridge/provider,
executor failure, stale state, receipt failure, and send failure must produce
an explicit blocked/degraded result. No success or authority is invented.

The update offset and per-update sanitized receipt preserve idempotency. The
legacy route remains available for rollback until real WP5 E2E certification.

Independent certification passed for unauthorized identity rejection, replay
suppression, unknown-intent safe handling, and Telegram-send failure handling
using bounded synthetic updates. Live API health is PASS; live E2E remains
unproven because no authorized inbound test updates were available.

Result rendering also fails closed: if a verified loop lacks a structured
payload, the response is `RESULT_INSUFFICIENT_FOR_SUMMARY` rather than a status
claim or receipt-path dump.
