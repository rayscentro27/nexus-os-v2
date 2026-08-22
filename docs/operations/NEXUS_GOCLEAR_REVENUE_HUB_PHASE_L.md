# Nexus GoClear Revenue Operating Hub — Phase L

Phase L extends the existing GoClear Revenue Hub into a read-only Revenue Truth Layer. It does not create a second dashboard, payment ledger, Stripe connector, or financial execution path.

## Reconciliation

The existing `GoClearMetricKey` taxonomy, Revenue Hub UI, test-mode payment tables/webhook flow, synthetic Persona D tooling, task-request feeder, reports, and Phase K opportunity collection remain the source-specific foundations. The heuristic `estimateGoClearRevenuePotential` path remains historical/planning output only. It is never accepted as actual revenue.

Canonical Phase L observations are stored in the governed append-only `revenue_observations` collection using `nexus.revenue-observation.v1`. Aggregates are persisted as `nexus.revenue-snapshot.v1` in `revenue_snapshots`; the snapshot is a read model, not a second transaction ledger. Audit events record ingestion, duplicate suppression, and snapshot refreshes without payment payloads or PII.

## Truth classes

Every observation is explicitly classified as `ACTUAL`, `TEST`, `SYNTHETIC`, `PIPELINE`, `OPPORTUNITY_ESTIMATE`, `FORECAST`, `MANUAL_VERIFIED`, `UNKNOWN`, or `NOT_CONNECTED`.

No source is not zero. A missing actual-revenue observation produces `value: null`, `truth_class: UNKNOWN`, and `source_status: NOT_CONNECTED`. An observed actual zero is retained as numeric zero with `observed_zero: true`. Test and synthetic amounts are summarized separately and are excluded from actual revenue.

Opportunity scores and expected values remain in `opportunity_pipeline`; they cannot populate actual revenue, MRR, purchases, commissions, or conversions. Funding requested/approved and commission opportunities remain pipeline data. Earned commissions require a source-backed observation. Gross revenue is not profit.

## Sources and safety

The current runtime does not provide a safe, unambiguous live Stripe reporting connection, so Stripe live revenue is `NOT_CONNECTED`; no Stripe read or mutation endpoint was added. Existing Stripe test-mode infrastructure remains available only for controlled test evidence. Affiliate and funding outcome sources remain `NOT_CONNECTED` or `PARTIAL` unless a reviewed source is connected. Opportunity Engine and Alpha are connected as intelligence sources, not money sources.

No charges, refunds, payouts, subscription mutations, customer mutations, checkout creation, affiliate enrollment, partner signup, funding application, grant submission, email/SMS, publishing, or trading authority was added. No service-role key, payment credential, card data, or client PII enters the operating snapshot.

## Snapshot and Hermes

Snapshots include period, UTC timestamps, metric observations, actual/test/synthetic separation, opportunity pipeline count/value class, unknown metrics, source connection state, freshness, and pending Ray decisions. Mission Control exposes Revenue Hub as optional and keeps core health independent. Hermes-facing answers use the canonical snapshot/read helper and explicitly say `UNKNOWN / NOT_CONNECTED` when actual revenue is unavailable.

The existing Revenue Dashboard was minimally updated to label `ACTUAL`, `TEST`, `SYNTHETIC`, `OPPORTUNITY_ESTIMATE`, and `UNKNOWN` distinctly. It does not claim `$0` when no actual source exists.

## Live certification

The Phase L live proof recorded controlled `$97` TEST and Persona D SYNTHETIC observations, replayed the test event and received `DUPLICATE_SUPPRESSED`, and refreshed a snapshot showing actual revenue `UNKNOWN / NOT_CONNECTED`. The snapshot retained the existing Phase K opportunity portfolio and pending Ray-review opportunity separately. Core Runtime, Active Operator, Recovery Check, Hermes, Mission Control, Evidence Ingestion, Remote CPU Worker, Alpha, and Opportunity Engine remained healthy.

The next phase may build measurable growth operations on this truth layer. Phase L does not begin that work.
