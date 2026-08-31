# Nova Telegram Delivery Completeness

Scope: WP6.5 production reliability closeout. The prior live failure consumed update `590357249`, composed a response, attempted delivery twice, and lost the response after both sends failed with connection resets.

The worker now persists a per-update delivery record and requires a terminal state: `DELIVERED` or `FAILED_TERMINAL` (whose terminal outcome is `TERMINAL_DELIVERY_FAILURE`). Transient exhaustion is retained as `FAILED_TRANSIENT` / `DELIVERY_PENDING` for a later worker cycle. `delivery_completeness_check()` is separate from execution exactly-once and fails any response-producing mission without a terminal delivery record.

Recovery reuses the persisted response and never reruns Hermes or tools. Permanent errors are terminal; transient records are bounded by the delivery expiry policy.
