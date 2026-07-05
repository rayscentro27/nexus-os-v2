# Nexus Supabase Source-of-Truth Audit

**Generated**: 2026-07-05

---

## Executive Summary

Nexus OS v2 uses a **single Supabase project** for all database operations. There is **no legacy/old Supabase project** referenced in active code. The old `ygqglfbhxiumqdisauar.supabase.co` reference exists only in historical reports under `reports/hermes_alpha/` and is not used by any active process.

---

## Supabase Project Status

| Field | Value |
|-------|-------|
| Project URL | Set in `.env` via `VITE_SUPABASE_URL` and `SUPABASE_URL` |
| Anon Key | Set in `.env` via `VITE_SUPABASE_ANON_KEY` |
| Service Role Key | Set in `.env` via `SUPABASE_SERVICE_ROLE_KEY` |
| Frontend Client | `src/lib/supabaseClient.ts` — `createClient()` with anon key |
| Server Access | Direct HTTP to PostgREST with service role key |
| Total Tables | 77 (defined across 14 migration files) |
| RLS | Enabled on all tables; admin policies via `nexus_is_active_admin()` |
| Edge Functions | 2: `hermes-chat`, `hermes-search` |

---

## Env Var Usage Map

### Frontend (browser-safe)
| Env Var | Files Using It | Status |
|---------|---------------|--------|
| `VITE_SUPABASE_URL` | `supabaseClient.ts`, `hermesSupabaseAccessState.ts`, `hermesSupabaseContextAdapter.ts`, `hermesLiveContext.ts`, `hermesCapabilityStatus.ts`, `UpdatePasswordPage.tsx`, `auth.tsx`, `nexusConnectorRegistry.ts`, `clientDataMode.js` | Present in `.env` |
| `VITE_SUPABASE_ANON_KEY` | Same files as above | Present in `.env` |
| `VITE_ENABLE_LIVE_SUPABASE_TEST_CLIENT` | `clientDataMode.js` | Feature flag, not in `.env` |

### Server-side (secret)
| Env Var | Files Using It | Status |
|---------|---------------|--------|
| `SUPABASE_URL` | `nexusDepartmentFeeders.ts` (13 feeders), Python seed scripts, `social/_supabase.py`, `nexus_runner.py`, ops scripts | Present in `.env` |
| `SUPABASE_SERVICE_ROLE_KEY` | Same Python scripts as above, `seed_premium_foundation.py`, `seed_day1_event.py` | Present in `.env` |

---

## Frontend Database Access Points

### `src/lib/supabaseClient.ts`
- Creates anon-key Supabase client
- Exports `supabase` and `isSupabaseConfigured`
- Used by all frontend Supabase access

### `src/services/db.ts`
- READ operations: `listTableDetailed()`, `listTable()`, `countRows()`
- Auth check: `supabase.auth.getSession()` for admin verification
- Specific table: `admin_users` (SELECT)

### `src/lib/hermesSupabaseContextAdapter.ts`
- READ from 11 tables: `approvals`, `task_requests`, `research_sources`, `business_opportunities`, `monetization_opportunities`, `client_profiles`, `nexus_events`, `system_health`, `agent_jobs`, `demo_trades`, `ops_incidents`

### `src/lib/hermesSupabaseAccessState.ts`
- Head count queries on 12 tables to determine Supabase-backed status
- Tables: `approvals`, `task_requests`, `nexus_events`, `research_sources`, `research_runs`, `client_profiles`, `business_opportunities`, `monetization_opportunities`, `system_health`, `ops_incidents`, `agent_jobs`, `ray_review_items`

### `src/services/clientDashboardLiveData.ts`
- READ from: `client_profiles`, `client_tasks`, `readiness_scores`
- Filter: `client_id=client_test_julius_erving` (test client)

---

## Server-Side Write Points (Python Scripts)

| Script | Tables Written | Auth |
|--------|---------------|------|
| `scripts/social/_supabase.py` | `nexus_events`, `system_health`, dynamic | Service role |
| `scripts/seed_day1_event.py` | `nexus_events`, `system_health`, `approvals` | Service role |
| `scripts/seed_premium_foundation.py` | 24+ tables (full schema seed) | Service role |
| `scripts/supabase/seed_static_data_to_supabase.py` | Dynamic from static JS data | Service role |
| `scripts/run_social_publish_job.py` | `social_posts`, `social_publish_receipts` | Service role |
| `scripts/nexus_runner.py` | `agent_jobs`, `nexus_events` | Service role |

---

## Department Feeder Write Points

`src/config/nexusDepartmentFeeders.ts` defines 18 feeders that require `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY`:

1. `watched_resource_registry` → `research_sources`
2. `watched_resource_watch` → `research_sources`
3. `research_content_growth_engine` → `research_runs`, `research_sources`
4. `daily_department_digest` → `nexus_events`
5. `source_intake_enrichment_backfill` → `research_sources`
6. `direct_source_enrichment_feeder` → `research_sources`
7. `source_capture_queue_worker` → `task_requests`
8. `ops_improvement_research_feeder` → `improvement_candidates`
9. `opportunity_lab_research_feeder` → `business_opportunities`, `monetization_opportunities`
10. `creative_studio_project_feeder` → `creative_campaigns`, `creative_briefs`
11. `design_library_project_feeder` → `creative_design_briefs`
12. `agent_jobs_process_feeder` → `agent_jobs`
13. `goclear_revenue_hub_feeder` → `partner_offers`

---

## Legacy Supabase References

| Reference | Location | Status |
|-----------|----------|--------|
| `ygqglfbhxiumqdisauar.supabase.co` | `reports/hermes_alpha/alpha_audit_conclusions.md`, `alpha_legacy_nexus_folder_audit.md`, `alpha_existing_asset_inventory.json`, `alpha_existing_system_process_cli_audit.md` | **Legacy only** — in historical audit reports, not in active code |

**Verdict**: No active code references the old Supabase project. The old reference exists only in audit report files that document prior system state.

---

## Migration Status

| Migration | Tables | Status |
|-----------|--------|--------|
| 0001_nexus_os_v2_core | 13 core tables | Applied |
| 0002_admin_read_policies | admin_users + RLS | Applied |
| 0003_premium_foundation | 24 premium tables | Applied |
| 0004_creative_studio_asset_engine | Alter creative_assets | Applied |
| 0005_nexus_runner | Alter agent_jobs | Applied |
| 0006_ai_agent_permission_boundaries | approved_knowledge + alter | Applied |
| 0007_model_router_and_hermes_routes | model_route_decisions, hermes_model_requests | Applied |
| 0008_transcript_intake_orientation | 6 intake tables | Applied |
| 0009_creative_design_department | 8 design tables | Applied |
| 0010_publish_readiness_packages | 3 publish tables | Applied |
| 0011_hermes_task_requests | task_requests | Applied |
| 20260624190000_fix_admin_users_rls_recursion | RLS fix function | Applied |
| 20260629090000_client_workflow_engine | 7 client tables | Applied |
| 20260629095450_client_portal_core_tables | 22 client portal tables + alters | Applied |

**Note**: Migrations exist in file but deployment status to live Supabase requires verification via `supabase db push` or dashboard inspection.

---

## Classification Summary

| Classification | Count |
|----------------|-------|
| Connected to Nexus OS v2 | All active code paths |
| Connected to old Supabase | 0 (legacy reports only) |
| Connected to local files only | 0 |
| Environment variable missing | 0 (all set in `.env`) |
| Table missing or unknown | Needs live verification (77 tables defined, live status unconfirmed) |
| RLS likely blocked or unknown | RLS policies defined but live enforcement unverified |
| Write path unsafe or unknown | Python scripts use service role (safe if keys valid) |
| Needs redirect | No |
| Needs migration | Migrations defined but live push status unknown |
| Ready for activation | Code paths ready; live DB verification needed |
| Useful legacy data to migrate | Old Supabase data location unknown |
| Legacy dependency to replace | None in active code |
