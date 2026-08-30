# Nova Truth / Capability Map and Restriction Audit

Campaign: `HG-WP6.5-NOVA-TRUTH-CAPABILITY-MAP-AND-RESTRICTION-AUDIT-20260830-01`

Baseline: `5427416`

## Findings

Nova has broad conversational and approved read capability. The main stale
behavior was a fallback that translated a failed specific tool read into a
global “I don't have access” statement. That wording is now scoped to the
failed source. Direct mutation and execution remain blocked at the capability
and TruthKernel/Nexus boundaries.

The prior “12 production clients” claim originates in the governed Supabase
`client_profiles` read via `hermes._get_client_count`, filtered to the GoClear
production tenant and normalized into production/active/onboarding counts. The
claim’s current validity depends on a successful fresh read; a numeric value
alone does not establish overnight activity or operational health.

The Active Operator launchd definition is `ops/launchd/com.nexus.active-operator-v2.plist`
with `StartInterval=900`. That proves configuration only. Runtime health and
real work remain heartbeat/receipt questions. Process-registry counts are not
equivalent to OS processes, running services, or Active Operator cycles.

## Implemented checkpoint

- Added a compact provenance-preserving `NOVA_TRUTH_VIEW` over existing
  canonical readers.
- Added capability maps for Nexus OS, Hermes Operations, and Alpha Research.
- Injected compact capability discovery into Nova’s bounded company context.
- Kept daily brief data as context only, never as a replacement for current
  canonical reads.
- Preserved free/private research preference and all direct-execution guards.

Development verification: 142 focused tests passed. This is not live Telegram
E2E evidence; fresh real Telegram retesting remains required.
