# Nexus Mock Data Replacement Plan

**Generated**: 2026-07-05

---

## Replacement Priority Matrix

### Priority 1: Critical Dashboard Data (Prompt 2)

| Mock File | Replacement Source | Table/Source | Implementation |
|-----------|-------------------|--------------|----------------|
| `systemHealthData.js` | Supabase `system_health` | `system_health` | Frontend query via `supabaseClient` |
| `rayReviewData.js` | Supabase `approvals` + `task_requests` | `approvals`, `task_requests` | Frontend query with filters |
| `nexusEngineStatusData.js` | Supabase `agent_jobs` | `agent_jobs` | Frontend query with status filter |
| `continuousDashboardData.json` | Aggregate live data | Multiple tables | New aggregation service |

### Priority 2: Client Portal Data (Prompt 2)

| Mock File | Replacement Source | Table/Source | Implementation |
|-----------|-------------------|--------------|----------------|
| `clientPortalData.js` | Supabase `client_profiles` | `client_profiles` | Frontend query by client_id |
| `clientsData.js` | Supabase `client_profiles` | `client_profiles` | Frontend query (admin) |
| `creditFundingData.js` | Supabase `credit_score_history` + `credit_workflow_items` | Multiple | Frontend query by client_id |

### Priority 3: Research/Opportunity Data (Prompt 2-3)

| Mock File | Replacement Source | Table/Source | Implementation |
|-----------|-------------------|--------------|----------------|
| `researchEngineData.js` | Local reports + Supabase `research_sources` | `research_sources` | Hybrid local/Supabase |
| `businessOpportunitiesData.js` | Supabase `business_opportunities` | `business_opportunities` | Frontend query |
| `monetizationData.js` | Supabase `monetization_opportunities` | `monetization_opportunities` | Frontend query |

### Priority 4: Hermes Context Data (Prompt 2-3)

| Mock File | Replacement Source | Table/Source | Implementation |
|-----------|-------------------|--------------|----------------|
| `hermesWorkroomData.js` | Live Hermes state + Supabase | Multiple | New context builder |
| `hermesContextData.js` | Live page context + Supabase | Multiple | New context builder |
| `hermesPageContext.js` | Route-based context | N/A | Dynamic context |
| `hermesAdminData.js` | Supabase `approvals` + config | Multiple | Frontend query |

### Priority 5: Marketing/Automation Data (Prompt 3)

| Mock File | Replacement Source | Table/Source | Implementation |
|-----------|-------------------|--------------|----------------|
| `marketingDraftsData.js` | Supabase `social_drafts` | `social_drafts` | Frontend query |
| `automationScheduleData.js` | `configs/automation_schedule_registry.json` | Local config | Direct config read |

---

## Implementation Pattern

For each replacement:

1. **Create data loader** in `src/services/` or `src/lib/`
2. **Query Supabase** using existing `supabaseClient`
3. **Handle loading states** in components
4. **Fall back to local data** if Supabase unavailable
5. **Cache responses** to avoid repeated queries
6. **Add error boundaries** for failed queries

---

## Estimated Effort

| Priority | Files to Change | New Loaders | Effort |
|----------|----------------|-------------|--------|
| 1 (Critical) | 4 mock files | 4 loaders | 1-2 days |
| 2 (Client) | 3 mock files | 3 loaders | 1-2 days |
| 3 (Research) | 3 mock files | 3 loaders | 1 day |
| 4 (Hermes) | 4 mock files | 4 loaders | 1-2 days |
| 5 (Marketing) | 2 mock files | 2 loaders | 0.5 day |
| **Total** | **16 files** | **16 loaders** | **5-8 days** |

---

## Recommendation

Prompt 2 should implement Priority 1 (Critical Dashboard Data) first, as this transforms the Command Center from a mock dashboard to a live operating view. This alone would significantly increase the system's perceived value and actual utility.
