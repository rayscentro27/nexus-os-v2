# Nexus Prompt 2 — Live Supabase Verification

**Generated**: 2026-07-05T18:38:09.825198+00:00

---

## Environment Keys

| Key | Present | Length |
|-----|---------|--------|
| `VITE_SUPABASE_URL` | YES | 40 |
| `VITE_SUPABASE_ANON_KEY` | YES | 208 |
| `SUPABASE_URL` | YES | 40 |
| `SUPABASE_SERVICE_ROLE_KEY` | YES | 219 |

**All keys present**: YES

---

## Table Verification

| Table | Exists | Status | Rows (sample) |
|-------|--------|--------|---------------|
| `admin_users` | NO | connection_error | - |
| `approvals` | NO | connection_error | - |
| `task_requests` | NO | connection_error | - |
| `nexus_events` | NO | connection_error | - |
| `system_health` | NO | connection_error | - |
| `agent_jobs` | NO | connection_error | - |
| `research_sources` | NO | connection_error | - |
| `research_runs` | NO | connection_error | - |
| `business_opportunities` | NO | connection_error | - |
| `monetization_opportunities` | NO | connection_error | - |
| `client_profiles` | NO | connection_error | - |
| `client_tasks` | NO | connection_error | - |
| `readiness_scores` | NO | connection_error | - |
| `client_documents` | NO | connection_error | - |

**Tables found**: 0/14

---

## Write Test

**Table**: `nexus_events`
**Success**: NO
**Error**: <urlopen error [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:1081)>

---

## Overall Status: NOT_CONNECTED

Supabase not connected. Check env keys and migration status.
