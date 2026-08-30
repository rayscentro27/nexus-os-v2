# Nova Live Truth, Research, and Report Quarantine

Campaign: `HG-WP6.5-NOVA-LIVE-TRUTH-RESEARCH-BUSINESS-PARTNER-AND-REPORT-QUARANTINE-20260830-01`

Baseline: `17def64`

## Implemented

- Added deterministic report provenance classification.
- Legacy, synthetic, fixture, and development artifacts remain available for
  historical reference but cannot establish current truth in Nova’s truth view.
- Added a separate public-web search capability using the existing bounded
  SearXNG/provider chain. Search acquisition is not treated as page retrieval
  or source verification.
- Nova’s truth view retains source, type, timestamp, freshness, real/test
  status, certification, confidence, and contradiction fields.
- Nexus remains authoritative only for Nexus-controlled operational facts and
  authorized company data; it is not a universal source for outside-world
  questions.

## Audited semantics

The 12-client claim comes from the governed Supabase `client_profiles` query,
filtered to the production tenant and normalized by status. It is a client-data
fact, not overnight activity. “No active processes” refers to the process
registry’s currently-running classification and does not prove that launchd,
scheduled jobs, or every worker is stopped. The Active Operator plist’s
900-second interval proves configuration only; heartbeat and receipts prove
runtime activity.

## Limits

Primary-source page retrieval, primary-source verification, and fresh Alpha
delegation remain NOT_PROVEN. No E2E certification is claimed.

Development verification: 146 focused tests passed.
