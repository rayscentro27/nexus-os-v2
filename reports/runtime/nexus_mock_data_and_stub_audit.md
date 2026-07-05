# Nexus Mock Data and Stub Audit

**Generated**: 2026-07-05

---

## Mock/Stub Data Files

| File | Type | Mock Risk |
|------|------|-----------|
| `src/data/systemHealthData.js` | Static health statuses | HIGH - All mock |
| `src/data/hermesWorkroomData.js` | Hermes workspace data | HIGH - All mock |
| `src/data/rayReviewData.js` | Review queue items | HIGH - All mock |
| `src/data/hermesPageContext.js` | Page context for Hermes | MEDIUM - Partial mock |
| `src/data/hermesContextData.js` | Hermes context data | MEDIUM - Partial mock |
| `src/data/hermesAdminData.js` | Admin Hermes data | MEDIUM - Partial mock |
| `src/data/researchEngineData.js` | Research engine data | HIGH - All mock |
| `src/data/clientPortalData.js` | Client portal data | HIGH - All mock |
| `src/data/clientsData.js` | Client list data | HIGH - All mock |
| `src/data/clientGuideResponses.js` | Client guide responses | MEDIUM - Template |
| `src/data/clientHermesBridgeData.js` | Client-Hermes bridge | MEDIUM - Partial mock |
| `src/data/creditFundingData.js` | Credit/funding data | HIGH - All mock |
| `src/data/businessOpportunitiesData.js` | Opportunities data | MEDIUM - Partial mock |
| `src/data/marketingDraftsData.js` | Marketing drafts | MEDIUM - Partial mock |
| `src/data/monetizationData.js` | Monetization data | MEDIUM - Partial mock |
| `src/data/automationScheduleData.js` | Scheduler data | MEDIUM - Partial mock |
| `src/data/nexusEngineStatusData.js` | Engine status | HIGH - All mock |
| `src/data/nexusNavigationConfig.js` | Navigation config | LOW - Config is real |
| `src/data/nexusCliCommandRegistry.js` | CLI commands | LOW - Config is real |
| `src/data/reportRegistry.js` | Report registry | LOW - Generated |
| `src/data/continuousDashboardData.json` | Dashboard data | HIGH - All mock |
| `src/data/clientDataMode.js` | Client data mode | LOW - Feature flag |

---

## Hardcoded Values Found

| Location | Hardcoded Value | Risk |
|----------|----------------|------|
| `src/services/clientDashboardLiveData.ts` | `client_id=client_test_julius_erving` | Medium - Test client only |
| `src/data/nexusNavigationConfig.js` | Card counts (e.g., "64 cards", "26 ready") | High - Stale counts |
| `src/data/systemHealthData.js` | All status values | High - Not live |
| `src/data/hermesWorkroomData.js` | All workspace data | High - Not live |

---

## Scan Results for Mock Keywords

| Keyword | Files Found | Assessment |
|---------|-------------|------------|
| `mock` | Multiple in tests/ | Test mocks only, acceptable |
| `sample` | Config files, test fixtures | Acceptable for testing |
| `demo` | OANDA demo, test data | Acceptable for demo mode |
| `placeholder` | Data files | Needs replacement |
| `fake` | Not found | Clean |
| `dummy` | Not found | Clean |
| `coming soon` | Not found | Clean |
| `static test data` | Implied in data files | Needs replacement |
| `hardcoded` | Multiple data files | Needs live sources |

---

## Classification

| Classification | Count | Action |
|----------------|-------|--------|
| Acceptable clearly labeled demo | 3 | Keep (OANDA demo, test fixtures) |
| Replace with live source | 15 | Connect to Supabase/reports |
| Replace with latest report | 4 | Wire to report generators |
| Hide until connected | 3 | Keep code, hide UI until data flows |
| Remove | 0 | None identified |
| Needs Ray decision | 2 | `continuousDashboardData.json`, hardcoded counts |

---

## Recommendation for Prompt 2

Priority replacement order:
1. System Health → live Supabase `system_health` table
2. Ray Review → live `approvals` / `task_requests` tables
3. Agent Jobs → live `agent_jobs` table
4. Client Portal → live `client_profiles` / `client_tasks` / `readiness_scores`
5. Research Engine → live research reports
6. Opportunities → live `business_opportunities` table
7. Command Center → aggregate live data from all sources
