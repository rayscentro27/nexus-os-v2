# Client Portal Schema Reconciliation Audit

**Generated:** 2026-07-07  
**Root Cause:** Supabase Assistant queried for table names that were never part of the Nexus schema.

## Summary

The Supabase Assistant reported 7 "missing" tables. These tables **do not exist in any local migration, code, or schema**. They were never created because they were never part of the design. The assistant queried for the wrong table names.

## Tables Supabase Assistant Expected (DO NOT EXIST)

| Expected Table | Status | Explanation |
|---------------|--------|-------------|
| client_readiness_status | NEVER CREATED | App uses `readiness_scores` instead |
| client_document_requirements | NEVER CREATED | App uses `client_documents` with category field |
| client_document_uploads | NEVER CREATED | App uses `client_documents` + Supabase Storage |
| client_credit_checklist | NEVER CREATED | App uses `credit_workflow_items` |
| client_business_funding_checklist | NEVER CREATED | App uses `business_profile_requirements` |
| client_guidance_items | NEVER CREATED | App uses `approved_client_guidance` |
| client_recommended_tools | NEVER CREATED | App uses `approved_client_guidance` or `client_recommendations` |

## Tables That Actually Exist (LIVE DATABASE)

All 25+ client portal tables exist and are confirmed:

| Table | Exists | RLS | Rows |
|-------|--------|-----|------|
| client_profiles | ✓ | ✓ | 2 |
| client_tasks | ✓ | ✓ | 0 |
| client_documents | ✓ | ✓ | 0 |
| readiness_scores | ✓ | ✓ | 0 |
| credit_workflow_items | ✓ | ✓ | 0 |
| business_profile_requirements | ✓ | ✓ | 0 |
| dispute_cases | ✓ | ✓ | 0 |
| dispute_letter_drafts | ✓ | ✓ | 0 |
| funding_readiness_scores | ✓ | ✓ | 0 |
| approval_cards | ✓ | ✓ | 0 |
| admin_review_queue | ✓ | ✓ | 0 |
| approved_client_guidance | ✓ | ✓ | 0 |
| client_questions | ✓ | ✓ | 0 |
| client_escalations | ✓ | ✓ | 0 |
| proof_events | ✓ | ✓ | 0 |
| connector_health | ✓ | ✓ | 0 |
| engine_runs | ✓ | ✓ | 0 |
| youtube_sources | ✓ | ✓ | 0 |
| youtube_review_items | ✓ | ✓ | 0 |
| social_drafts | ✓ | ✓ | 0 |
| subscription_memberships | ✓ | ✓ | 0 |
| payments_status | ✓ | ✓ | 0 |
| tenant_memberships | ✓ | ✓ | 1 |
| client_recommendations | ✓ | ✓ | 0 |
| client_workflow_stage_history | ✓ | ✓ | 0 |

## Code-to-Table Mapping

| App Concept | Actual Table Name | Code Reference |
|-------------|------------------|----------------|
| Client readiness | readiness_scores | src/clientPortal/useClientPortalData.ts |
| Document uploads | client_documents | src/components/client/DocumentUploadZone.tsx |
| Credit checklist | credit_workflow_items | src/lib/clientPortalDataAdapter.ts |
| Business funding | business_profile_requirements | src/data/clientPortalData.js |
| Guidance items | approved_client_guidance | src/components/client/ClientGuidePanel.jsx |
| Recommended tools | approved_client_guidance | src/data/clientHermesBridgeData.js |

## Conclusion

**No migration fix needed.** The schema is correct. The Supabase Assistant used incorrect table names. The correct table names to use are the ones already in the codebase.
