# Client Schema Reconciliation

**Generated:** 2026-07-07

## Status: RESOLVED — No Fix Needed

The Supabase Assistant queried for table names that were never part of the Nexus schema. All active code uses the correct table names.

## Correct Table Mapping

| App Concept | Correct Table Name | Old/Incorrect Name |
|-------------|-------------------|-------------------|
| Client readiness | `readiness_scores` | ~~client_readiness_status~~ |
| Document uploads | `client_documents` | ~~client_document_uploads~~ |
| Document requirements | `client_documents` | ~~client_document_requirements~~ |
| Credit checklist | `credit_workflow_items` | ~~client_credit_checklist~~ |
| Business funding | `business_profile_requirements` | ~~client_business_funding_checklist~~ |
| Guidance items | `approved_client_guidance` | ~~client_guidance_items~~ |
| Recommended tools | `approved_client_guidance` | ~~client_recommended_tools~~ |

## Files Using Correct Names

- `src/clientPortal/useClientPortalData.ts` ✓
- `src/lib/clientPortalDataAdapter.ts` ✓
- `src/components/client/DocumentUploadZone.tsx` ✓
- `src/components/client/ClientGuidePanel.jsx` ✓
- `src/data/clientHermesBridgeData.js` ✓
- `supabase/migrations/20260629095450_client_portal_core_tables.sql` ✓

## Old Reports With Wrong Names

Historical reports reference the incorrect names but do not affect current functionality. No action needed.
