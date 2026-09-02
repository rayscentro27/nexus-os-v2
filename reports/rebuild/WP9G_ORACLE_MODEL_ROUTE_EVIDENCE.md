# WP9G Oracle model route evidence

The existing private tunnel `127.0.0.1:18642` → Oracle `127.0.0.1:8642` is
running, but the Mac bridge environment lacks `NEXUS_ORACLE_HERMES_API_KEY`.
No credential was guessed or copied.

A direct safe invocation inside the existing Oracle container was attempted.
The Hermes CLI accepted the configured default route but produced no result
within the bounded observation window; the exact test process was terminated
and cleaned up. Consequently:

`ORACLE_HERMES_MODEL_ROUTE=AUTHORIZED_EXISTING_ROUTE_NOT_PROVEN`
`ORACLE_HERMES_MODEL_EXECUTION=NOT_PROVEN_TIMEOUT_NO_RESULT`

This is a runtime/provider responsiveness blocker, not evidence of successful
model execution.
