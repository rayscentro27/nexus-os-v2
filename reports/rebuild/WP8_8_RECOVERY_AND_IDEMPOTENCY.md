# WP8.8 Recovery and Idempotency

BUSINESS_OPPORTUNITY_RECOVERY=PASS
BUSINESS_OPPORTUNITY_IDEMPOTENCY=PASS

The opportunity fingerprint reused the existing mobile-detailing record. Alpha and Growth work-order checks reused completed durable work on rerun. Reload uses governed opportunities, metrics, work_orders, research, and loop_state.

Interrupted processing reloads research, opportunity, economics, decision, and work orders; completed work is not fabricated or replayed.
