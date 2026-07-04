# Nexus Credit & Funding Research Adapter v1 — Preflight

**Generated**: 2026-07-03

---

## Current State

| Item | Value |
|------|-------|
| Branch | `main` |
| Last commit | `9ddd5b1 design Nexus credit funding research engine alongside Hermes Alpha` |
| Dirty files | 9 runtime/cache/report files (unrelated to this task) |

### Dirty Files (not part of this task)

- `data/cache/youtube/api_metadata/alec_delpuech.json`
- `data/cache/youtube/api_metadata/credit_plug.json`
- `data/cache/youtube/api_metadata/michael_ionita.json`
- `data/cache/youtube/api_metadata/stedman_waiters.json`
- `data/cache/youtube/api_metadata/video_zbAmmnMh5ew.json`
- `data/exports/notebooklm/research_bundles/final_daily_research_memory_latest.json`
- `reports/manual_publish/daily_operating_cycle_latest.md`
- `reports/manual_publish/research_to_money_pipeline_latest.md`
- `reports/runtime/ray_review_queue_latest.json`

These will not be committed as part of this task.

---

## Inbox Inspection

### Approved Nexus Research Inbox Folders

All 10 approved folders found with README.md placeholders:

| Folder | README.md | Real Artifacts |
|--------|-----------|----------------|
| `credit_repair/` | Yes | None |
| `credit_utilization/` | Yes | None |
| `business_setup/` | Yes | None |
| `business_funding/` | Yes | None |
| `grants/` | Yes | None |
| `lenders/` | Yes | None |
| `affiliates/` | Yes | None |
| `compliance/` | Yes | None |
| `client_education/` | Yes | None |
| `manual_notes/` | Yes | None |

### Real Markdown Artifacts Found

**None.** All 10 inbox subdirectories contain only `README.md` placeholder files. No research artifacts have been collected. This is intentional — the inbox is empty by design until Ray adds approved research.

---

## Adapter Feasibility

| Check | Status |
|-------|--------|
| Can adapter run on a real artifact? | **No** — no real artifact exists |
| Is fallback fixture-only testing required? | **Yes** |
| Will adapter be built? | **Yes** |
| Will adapter be tested with labeled fixtures? | **Yes** |
| Will fake research be created? | **No** — never |
| Will "no real artifact" be honestly reported? | **Yes** |

---

## Decision

The adapter v1 will be:

1. Fully implemented with all safety checks, classification, routing, and draft output logic
2. Tested exclusively with clearly labeled fixture artifacts
3. Verified against all hard rules (no Supabase, no external connections, no fake research)
4. Documented with an honest "no real artifact available" report

Real ingestion requires Ray to add one approved `.md` file to `nexus_research/research_inbox/`.
