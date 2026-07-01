# Nexus OS v2 — Full Operational Reality Audit

**Generated:** 2026-07-01T07:15:00Z
**Audit Version:** 1.0

---

## Supabase Live Data

| Table | Rows | Live R/W | RLS |
|---|---|---|---|
| task_requests (ray_review_item) | 62 | YES | nexus_is_active_admin() |
| business_opportunities | 26 | YES | nexus_is_active_admin() |
| monetization_opportunities | 11 | YES | nexus_is_active_admin() |
| client_profiles | 1 | YES | nexus_is_active_admin() |
| research_sources | 52 | YES | service_role, admin_users.active=true |
| nexus_events | 580 | YES | — |

**Total Supabase rows: 732**

---

## UI Sections Status

### LIVE (5 sections)

| Section | Source | Rows |
|---|---|---|
| Ray Review | task_requests (Live Supabase) | 62 |
| Business Opportunities | business_opportunities | 26 |
| Monetization | monetization_opportunities | 11 |
| Clients | client_profiles | 1 |
| Research Engine | research_sources | 52 |

### STATIC (7 sections)

| Section | Data Source | Notes |
|---|---|---|
| Trading Lab | Inline in NexusAdminUI | No Supabase table |
| System Health | systemHealthData.js | Hardcoded |
| Automation | Inline data | Hardcoded |
| Reports | reportRegistryData.js | Hardcoded |
| Settings | None | No data file |
| CLI | None | No data file |
| Credit/Funding | creditFundingData.js | Hardcoded |

---

## Background Processes

| Process | Schedule | Status | Proven Recent Execution |
|---|---|---|---|
| launchd daily | 8AM daily | Installed & loaded | YES |
| launchd evening | 6PM daily | Installed & loaded | YES |
| launchd continuous | Every 30 min | Installed & loaded | YES |
| Research scoring | launchd continuous loop | Active | YES |

All launchd jobs write local JSON. Python scripts have conditional Supabase writes via `sb.configured()`.

---

## YouTube Research

- **Scheduler exists:** YES
- **Proven live:** NO
- No recent fetch proof. Scheduler exists but is not confirmed running.

---

## Hermes Capabilities

| Capability | Status | Detail |
|---|---|---|
| Live Supabase read | YES | When authenticated |
| Live web search | NO | VITE_HERMES_SEARCH_ENABLED not set |
| Live model | NO | LLM provider not configured |
| Report snapshot access | YES | Reads local report JSON |
| Page context | YES | Reads from loaded components |
| Source reasoning | YES | hermesSourceReasoner.ts |
| Activity/memory | LIMITED | localStorage only |
| Background process visibility | NO | No process monitoring |

---

## Fake / Static Claims

| Claim | Reality |
|---|---|
| "Running safely" in Command Center | Partially true — launchd jobs run, but some UI claims "running" without process proof |
| "Oanda practice read checks" | launchd loads script, no proof of recent execution |
| "Vibe paper dry-run" | No proof of recent execution |
| "NotebookLM watched folder" | No proof of active monitoring |

---

## Summary

- **Live sections:** 5
- **Static sections:** 7
- **Total Supabase rows:** 732
- **Background jobs:** 4 (all running)
- **YouTube research:** Not proven

### Hermes Can Report On
- Supabase table row counts
- UI section statuses
- Local report file contents
- Launchd job schedules
- Static data file contents

### Hermes Cannot See
- Live web search results
- LLM-powered analysis
- Background process runtime logs
- YouTube research fetch activity
- Oanda execution results
- NotebookLM folder activity

### Blockers
1. `VITE_HERMES_SEARCH_ENABLED` not set — no live web search
2. LLM provider not configured — no live model in Edge Function
3. YouTube research scheduler unproven — no fetch evidence
4. Oanda and NotebookLM claims lack execution proof

### Next Actions
1. Enable `VITE_HERMES_SEARCH_ENABLED` for live web search
2. Configure LLM provider in Edge Function for live model
3. Add execution logging to YouTube research scheduler
4. Add proof-of-execution tracking to Oanda and NotebookLM scripts
5. Migrate remaining STATIC sections to Supabase-backed live data
