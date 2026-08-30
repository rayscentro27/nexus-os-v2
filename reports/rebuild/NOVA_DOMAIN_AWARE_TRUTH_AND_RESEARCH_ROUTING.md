# Nova Domain-Aware Truth and Research Routing

Campaign: `HG-WP6.5-NOVA-DOMAIN-AWARE-TRUTH-AND-RESEARCH-20260830-01`

Baseline: `1b50dfa`

## Repair

Added a domain source policy and semantic classifier. Nova now distinguishes
Nexus operations, client data, internal Alpha research, public business/company
research, website analysis, general knowledge/business, economics,
delegation, and operational action. Domain metadata can contain multiple
domains and does not grant any capability.

Outside-world questions are no longer allowed to select Nexus canonical reads
by default. Internal company and Nexus questions retain canonical current-state
reads. Public research remains free/private-first and keeps paid paths behind
the existing cost boundary.

## Evidence discipline

The 12-client value is sourced by the governed Supabase `client_profiles` read;
it is not an overnight activity counter. Process-registry active counts are
only process classifications and do not prove all services or scheduled jobs
are stopped. Active Operator’s 900-second interval is configuration evidence;
runtime health requires current heartbeat and receipt evidence.

## Verification

Focused Nova, governance, daily-brief, and canonical reasoning tests: 144
passed. This is development evidence only. Fresh real Telegram retesting is
required; no E2E pass is claimed.
