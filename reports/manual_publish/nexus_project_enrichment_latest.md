# Nexus Project Enrichment Latest

Deterministic enrichment was connected to department project cards.

## Added

- Canonical enrichment types in `src/config/nexusProjectTypes.ts`.
- Script helper `scripts/intake/nexus_enrichment.py`.
- Monitor and capture worker writes to `project_enrichment`.
- Project adapter read order across transcript reviews, research sources, task requests, and fallback.
- Hermes advisor uses `hermes_memory_summary` when available.
- Command Center shows enriched/missing-enrichment counts and enriched recommendations.

## Storage

`research_sources.metadata.project_enrichment`, `transcript_reviews.metadata.project_enrichment`,
`task_requests.payload.project_enrichment`, and proof snapshots in `nexus_events.payload`.

## Safety

No external AI, broad scraping, scheduler activation, v1 writes, publish, send, trade, or deploy were added.

## Next Recommendation

Add a safe manual backfill command that computes `project_enrichment` for existing historical `research_sources` rows without running capture.
