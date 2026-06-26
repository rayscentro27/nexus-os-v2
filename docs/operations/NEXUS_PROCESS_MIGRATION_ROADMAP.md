# Nexus Process Migration Roadmap

This roadmap moves existing scripts into department feeders without exposing raw worker control.

## Current Phase

- Department workspace UI is live.
- Project enrichment exists.
- Historical research sources have been backfilled.
- Department feeder registry exists.
- Manual feeder runner exists in dry-run/report mode.
- Scheduler activation remains disabled.

## Migration Order

1. Source Intake metadata/enrichment feeders.
2. Opportunity Lab feeder from enriched research.
3. Ops & Improvements feeder from safe reports and docs.
4. Creative/Design feeder from existing creative/design tables.
5. SEO/Marketing feeder after connector or seeded SEO rows exist.
6. Process Registry/Agent Jobs feeder.
7. Command Center summary consolidation.

## Rules

- Prefer `task_requests`, metadata JSON, and `nexus_events`.
- Approval-required/risky actions go to `approvals`.
- No raw v1 execution from UI.
- No scheduler activation without Ray approval.
- No publish/send/trade/deploy paths in feeders.

## Next Recommendation

Add live writes only one feeder at a time, starting with deterministic Opportunity Lab task request creation from enriched public research rows.
