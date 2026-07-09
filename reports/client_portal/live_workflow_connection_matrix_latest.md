# Live Workflow Connection Matrix

**Date:** 2026-07-08
**Starting commit:** 8818221

## Client Portal Live Data Wiring Status

| Page | Route | Live Data Source | Status |
|------|-------|-----------------|--------|
| Dashboard | `/client/dashboard` | `loadClientDashboardLiveData` + `loadClientProfileIntake` | LIVE |
| Profile & Info | `/client/profile` | `loadClientProfileIntake` + `saveClientProfileIntake` | LIVE |
| Credit Profile | `/client/credit-profile` | `usePortalLiveData` (readiness_scores) | LIVE |
| Credit Utilization | `/client/credit-utilization` | `usePortalLiveData` (credit_workflow_items) | LIVE |
| Documents | `/client/documents` | `loadClientDashboardLiveData` (client_documents) | LIVE |
| Business Setup | `/client/business-setup` | `usePortalLiveData` (business_profile_requirements) | LIVE |
| Business Bankability | `/client/business-bankability` | `usePortalLiveData` (business_profile_requirements) | LIVE |
| Funding Readiness | `/client/funding-readiness` | `usePortalLiveData` (funding_readiness_scores) | LIVE |
| Recommendations | `/client/recommendations` | `usePortalLiveData` (partner_offers) | LIVE |
| Resources | `/client/resources` | `usePortalLiveData` (partner_offers) | LIVE |
| Request Review | `/client/request-review` | `usePortalLiveData` + `loadClientDashboardLiveData` | LIVE |
| Messages | `/client/messages` | Static fallback | STATIC |
| Settings | `/client/settings` | Static fallback | STATIC |

## Admin Panel Live Data Wiring

| Panel | Data Source | Status |
|-------|------------|--------|
| Clients List | `loadSection('clients', clientsList)` — queries `client_profiles` | LIVE |
| Client Detail Drawer | Direct Supabase queries: `client_profiles`, `client_documents`, `client_tasks`, `storage.objects` | LIVE |
| Profile Fields | `client_profiles` intake columns | LIVE |
| Document Metadata | `client_documents` table | LIVE |
| Review Requests | `client_tasks` where `category = 'review_request'` | LIVE |
| Storage Files | `supabase.storage.from('client-documents').list()` | LIVE |

## Hermes Guidance Live Wiring

| Status | Source | Live? |
|--------|--------|-------|
| `creditReportUploaded` | `client_documents` | LIVE |
| `addressVerified` | `client_documents` | LIVE |
| `identityVerified` | `client_documents` | LIVE |
| `utilizationHigh` | `readiness_scores` | LIVE |
| `negativeItemsIdentified` | `readiness_scores` | LIVE |
| `businessBankAccount` | `client_documents` | LIVE |
| `revenueDocuments` | `client_documents` | LIVE |
| `documentsComplete` | `client_documents` | LIVE |
| `adminReviewRequired` | `client_documents` | LIVE |
| `readinessScore` | `readiness_scores` | LIVE |
| `profileIncomplete` | `client_profiles` intake columns | LIVE |

## Adapter Functions

| Function | Table | Status |
|----------|-------|--------|
| `loadClientProfile` | `client_profiles` | LIVE |
| `loadClientTasks` | `client_tasks` | LIVE |
| `loadReadinessScores` | `readiness_scores` | LIVE |
| `loadClientDocuments` | `client_documents` | LIVE |
| `loadBusinessProfileRequirements` | `business_profile_requirements` | LIVE |
| `loadFundingReadinessScores` | `funding_readiness_scores` | LIVE |
| `loadApprovedClientGuidance` | `approved_client_guidance` | LIVE |
| `loadPartnerOffers` | `partner_offers` | LIVE |
| `loadCreditWorkflowItems` | `credit_workflow_items` | LIVE |
| `loadClientPortalLiveData` | All above | LIVE |
| `loadClientProfileIntake` | `client_profiles` (intake columns) | LIVE |
| `saveClientProfileIntake` | `client_profiles` (intake columns) | LIVE |
| `checkProfileIntakeComplete` | Client-side validation | LIVE |

## Tables Used

| Table | Client Read | Client Write | Admin Read | Status |
|-------|------------|--------------|------------|--------|
| `client_profiles` | Own row via RLS | Own row (intake fields) | All rows | LIVE |
| `tenant_memberships` | Own row | No | All rows | LIVE |
| `client_tasks` | Own visible tasks | `review_request` inserts | All tasks | LIVE |
| `client_documents` | Own visible docs | Own uploads + metadata | All docs | LIVE |
| `readiness_scores` | Own visible scores | No | All scores | LIVE |
| `credit_workflow_items` | Own visible items | No | All items | LIVE |
| `business_profile_requirements` | Own visible | No | All items | LIVE |
| `funding_readiness_scores` | Own visible | No | All scores | LIVE |
| `approved_client_guidance` | Own visible | No | All guidance | LIVE |
| `partner_offers` | All (public) | No | All | LIVE |
| `storage.client-documents` | Own folder | Own uploads | All folders | LIVE |
