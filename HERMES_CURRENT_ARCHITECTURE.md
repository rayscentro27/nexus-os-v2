# Hermes Current Architecture

Generated: 2026-08-03

## Internal Hermes

Nexus Hermes is the admin/operator assistant surfaced through `HermesChatPanel`, `HermesInlineDrawer`, the Command Center, and the Hermes Workroom. Routing still includes the existing priority router, model-first controller, local conversation engine, page context bridge, selection/advisory memory, and safe UI action allowlist.

## Repaired Call Path

Operational questions now route first through `src/lib/nexusOperationalTruth.ts` before model generation. The service reads bundled operations/process/scheduler snapshots, marks stale state explicitly, and includes provenance for source, timestamp, record count, confidence/state, and unavailable live sources.

## Health and Provider Truth

`HermesChatPanel` now shows independent states:

- Supabase
- Model
- Process Registry
- Last verified

The capability badge no longer says `Live Supabase + Model Ready` from configuration alone. Configured providers are labeled as requiring a probe unless a bounded probe succeeds.

## Known Remaining Limits

- Live Supabase process/run registry reads are not certified because the integration worktree has no env files and the original E2E admin password failed normal login.
- Existing research outputs are still mostly report/local-file based until ingestion jobs write to the new registry tables.
- Hermes can now answer operational questions truthfully from snapshots, but stale snapshots are not live production proof.
