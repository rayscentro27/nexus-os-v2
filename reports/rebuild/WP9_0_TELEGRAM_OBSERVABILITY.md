# WP9.0 Telegram Observability

The real Nova Telegram transport test passed through the existing Nova helper;
delivery receipt message ID 1138 was recorded without secrets. Telegram is a
certification feed only, not autonomy proof. The temporary event policy is
START, MEANINGFUL_PROGRESS, DECISION_READY, WARNING, CRITICAL, COMPLETE with
NO_CHANGE suppression and idempotent fingerprints.

REAL_NOVA_TELEGRAM_TRANSPORT=PASS
WP9_TELEGRAM_ROLE=PASS
WP9_TELEGRAM_EVENT_POLICY=PASS
WP9_TELEGRAM_IDEMPOTENCY=PASS_DESIGN
WP9_TELEGRAM_FAILOPEN_SAFE=PASS_DESIGN
