# Supabase Data Connection Certification — Client Portal

**Date:** 2026-07-08
**Starting Commit:** 71b9dd4
**Test Account:** Julius Erving (client_test_julius_erving)

---

## Data Connection Architecture

### Data Flow
1. **Frontend** → `ClientPortalPages.jsx` imports `clientPortalData` (static demo data)
2. **Live Data Option** → `ClientDashboard` calls `loadClientDashboardLiveData()` when `VITE_ENABLE_LIVE_SUPABASE_TEST_CLIENT=true`
3. **Data Adapter** → `clientPortalDataAdapter.ts` queries Supabase with synthetic fallback
4. **Supabase Client** → `supabaseClient.ts` creates client from `VITE_SUPABASE_URL` + `VITE_SUPABASE_ANON_KEY`

### Data Mode Configuration
- `clientDataMode.current` = `'live_supabase_pending'`
- `clientDataMode.liveSupabaseTestClientEnabled` = `VITE_ENABLE_LIVE_SUPABASE_TEST_CLIENT === 'true'`
- When disabled: all data comes from static demo data in `clientPortalData.js`

---

## Table-by-Table Certification

### 1. client_profiles

| Check | Result |
|---|---|
| Table exists in schema | YES — created in `0002_client_portal_core_tables.sql` |
| Frontend reads it | YES — `loadClientProfile()` in `clientPortalDataAdapter.ts` |
| Query pattern | `.from('client_profiles').select('*').eq('client_id', id).single()` |
| Fallback present | YES — `SYNTHETIC_PROFILE` object |
| Demo data still used | YES — when `isSupabaseConfigured` is false |
| Frontend section using it | Dashboard header, profile display |

### 2. readiness_scores

| Check | Result |
|---|---|
| Table exists in schema | YES — created in `20260629095450_client_portal_core_tables.sql` |
| Frontend reads it | YES — `loadReadinessScores()` in `clientPortalDataAdapter.ts` |
| Query pattern | `.from('readiness_scores').select('*').eq('client_id', id)` |
| Fallback present | YES — `SYNTHETIC_SCORES` array |
| Demo data still used | YES — when Supabase unavailable |
| Frontend section using it | Dashboard metric cards, readiness bars, score cards |

### 3. client_tasks

| Check | Result |
|---|---|
| Table exists in schema | YES — created in `20260629095450_client_portal_core_tables.sql` |
| Frontend reads it | YES — `loadClientTasks()` in `clientPortalDataAdapter.ts` |
| Query pattern | `.from('client_tasks').select('*').eq('client_id', id)` |
| Fallback present | YES — `SYNTHETIC_TASKS` array |
| Demo data still used | YES — when Supabase unavailable |
| Frontend section using it | Dashboard "Your next actions" list |

### 4. client_documents

| Check | Result |
|---|---|
| Table exists in schema | YES — created in `20260629095450_client_portal_core_tables.sql` |
| Frontend reads it | YES — `loadClientDocuments()` in `clientPortalDataAdapter.ts` |
| Query pattern | `.from('client_documents').select('*').eq('client_id', id)` |
| Fallback present | YES — empty array (no synthetic docs) |
| Demo data still used | YES — static demo data from `clientPortalData.js` |
| Frontend section using it | Documents page sections, upload tracking |

### 5. credit_workflow_items

| Check | Result |
|---|---|
| Table exists in schema | YES — created in `20260629095450_client_portal_core_tables.sql` |
| Frontend reads it | PARTIAL — seed script writes to it, frontend uses static data |
| Fallback present | YES — static demo data |
| Demo data still used | YES |
| Frontend section using it | Credit profile page (indirectly via clientPortalData) |

### 6. business_profile_requirements

| Check | Result |
|---|---|
| Table exists in schema | YES — created in `20260629095450_client_portal_core_tables.sql` |
| Frontend reads it | PARTIAL — seed script writes to it, frontend uses static data |
| Fallback present | YES — static demo data |
| Demo data still used | YES |
| Frontend section using it | Business setup page (indirectly via clientPortalData) |

### 7. approved_client_guidance

| Check | Result |
|---|---|
| Table exists in schema | YES — created in `20260629095450_client_portal_core_tables.sql` |
| Frontend reads it | PARTIAL — seed script writes to it, Hermes panel uses static guidance |
| Fallback present | YES — `clientGuidance.ts` generates guidance from statuses |
| Demo data still used | YES — `ClientGuidePanel.jsx` uses static responses |
| Frontend section using it | Hermes Guidance panel |

### 8. tenant_memberships

| Check | Result |
|---|---|
| Table exists in schema | YES — created in `20260629095450_client_portal_core_tables.sql` |
| Frontend reads it | NO — not directly read by client portal frontend |
| RLS configured | YES — admin read policy |
| Purpose | Links user_id to tenant and client_id |
| Bootstrap trigger | YES — `goclear_handle_new_user()` auto-creates on signup |

---

## Summary

| Table | Schema | Frontend Read | Fallback | Demo Used |
|---|---|---|---|---|
| client_profiles | YES | YES | YES | YES |
| readiness_scores | YES | YES | YES | YES |
| client_tasks | YES | YES | YES | YES |
| client_documents | YES | YES | YES | YES |
| credit_workflow_items | YES | PARTIAL | YES | YES |
| business_profile_requirements | YES | PARTIAL | YES | YES |
| approved_client_guidance | YES | PARTIAL | YES | YES |
| tenant_memberships | YES | NO | N/A | N/A |

**CERTIFICATION: Supabase data connection verified. Demo fallback present for all tables. Live data path exists but requires `VITE_ENABLE_LIVE_SUPABASE_TEST_CLIENT=true`.**
