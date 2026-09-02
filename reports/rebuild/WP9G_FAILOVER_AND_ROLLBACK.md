# WP9G failover and rollback

No live cutover occurred. The safe rollback is therefore unchanged:
`NOVA_PRIMARY_RUNTIME=hermes` continues to use the current Mac Hermes path;
Oracle remains an unselected worker. A future cutover must be feature-flagged,
single-consumer, receipt-proven, and reversible by restoring that value through
the canonical runtime configuration and verifying launchd status.

Heavy Oracle work must defer rather than silently fall back to an uncontrolled
Mac workload. No scheduler, Telegram offset, certification state, or Finance
gate was changed.
