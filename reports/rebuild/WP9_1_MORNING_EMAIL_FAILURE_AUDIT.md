# WP9.1 Morning Email Failure Audit

## Actual 06:00 path

Launchd ran the loaded canonical job at local 06:00 (UTC
`2026-09-02T13:00:00Z`). The runtime generated
`reports/runtime/wp9/morning_reports/wp9-20260902T130000Z-e224c982c3.json`
and wrote an email receipt. The receipt uses the canonical authenticated
Supabase `send-client-email` route and has provider ID
`da2e8dee-2b09-4979-9e33-a1b50918f5b9`.

The durable provider claim is `REQUEST_ACCEPTED_PROVIDER_QUEUED` /
`PROVIDER_QUEUED`. There is no inbox, delivery, bounce, or suppression event
in the runtime evidence. Therefore the observed non-receipt cannot be
reclassified as delivered. Delivery state: `PROVIDER_QUEUED`.

## Root cause and repair

The scheduler did not miss the local-time event. The failure was a reporting
quality/claim gap: the report used the cumulative daily ledger and placeholder
text, and the route exposed queue acceptance rather than inbox confirmation.
The repaired report uses the explicit previous-06:00-to-current-06:00 local
window and includes the actual cycle summaries. Test and real-report
idempotency keys remain separate. Failed sends continue to persist receipts.

A corrective message titled `Nexus Night 1 Audit / Missed Morning Report` was
generated from the actual Night 1 receipts and sent through the existing route.
It was accepted/queued; inbox delivery remains unconfirmed.

Configured recipient was present and redacted in this report; no secret or
full address is printed. The runtime timezone is America/Phoenix, and 06:00
means local 06:00 rather than UTC.
