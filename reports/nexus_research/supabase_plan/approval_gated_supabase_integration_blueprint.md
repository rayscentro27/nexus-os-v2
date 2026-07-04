# Approval-Gated Supabase Integration Blueprint

**Generated**: 2026-07-04
**Status**: DRY RUN ONLY — NOT WRITTEN TO SUPABASE — NOT APPROVED

---

## Purpose

This blueprint defines how Nexus Research and GoClear Readiness outputs would integrate with Supabase after Ray approval. No writes are performed. No migrations are applied. This is a design document.

---

## How Adapter Outputs Become Draft Records

1. Adapter processes a seed artifact
2. Adapter generates `NexusArtifactMetadata`
3. Future: metadata written to `nexus_research_artifacts` with `ray_review_status: 'pending'`
4. Adapter generates admin note and Ray Review draft
5. Future: reviews written to `nexus_research_reviews` with `ray_review_status: 'pending'`
6. All records default to `client_facing_allowed: false`

---

## How Internal Test Reports Become Draft Records

1. Runner processes hypothetical profiles
2. Runner generates readiness scorecards and admin notes
3. Report builder generates internal readiness reports
4. Future: test results written to `goclear_readiness_internal_tests`
5. Future: report drafts written to `goclear_readiness_report_drafts`
6. All records default to `ray_review_status: 'pending'` and `client_facing_allowed: false`

---

## How Ray Review Approves/Rejects

1. Items appear in `ray_review_research_queue` with `status: 'pending'`
2. Ray reviews item in admin interface (future)
3. Ray sets `status: 'approved'` or `status: 'rejected'`
4. If approved: `client_facing_allowed` can be set to `true` (if appropriate)
5. If rejected: item remains admin-only, may be deleted or revised

---

## How Client-Facing Approval Stays Blocked

- All records default to `client_facing_allowed: false`
- Only Ray can change `client_facing_allowed` to `true`
- `client_facing_allowed: true` requires `ray_review_status: 'approved'`
- Client-facing content requires explicit Ray approval per item
- No bulk client-facing approval

---

## How Supabase Writes Remain Disabled Until Ray Approval

1. No Supabase client exists in Nexus Research code
2. No environment variables for Supabase are configured
3. No code path writes to Supabase
4. All outputs are local-only (files on disk)
5. Supabase integration will be added only after:
   - Ray approves the integration plan
   - RLS policies are defined and tested
   - Tenant isolation is verified
   - Audit logging is implemented
   - Rollback strategy is tested

---

## How Tenant Isolation Will Be Verified

1. Create test tenant A and test tenant B
2. Write records for tenant A
3. Attempt to read tenant A records as tenant B — should fail
4. Attempt to write to tenant A records as tenant B — should fail
5. Verify admin (service role) can access all tenants
6. Document verification results

---

## How RLS Will Be Tested Before Live Use

1. Create RLS policies in staging environment
2. Test each policy with multiple roles
3. Verify no anonymous access
4. Verify no public access
5. Verify tenant isolation
6. Verify admin bypass
7. Document all test results
8. Get Ray approval before production deployment

---

## Integration Sequence (Future)

1. Ray approves Supabase connection plan
2. Create Supabase project (if not exists)
3. Apply draft migrations in staging
4. Test RLS policies
5. Test tenant isolation
6. Test audit logging
7. Add Supabase client to Nexus Research
8. Add write paths for adapter outputs
9. Add write paths for test results
10. Add write paths for report drafts
11. Test with hypothetical data only
12. Get Ray approval for production use
13. Deploy to production

---

## Blocking Conditions

Supabase integration will NOT proceed if:
- Ray has not approved the plan
- RLS policies are not tested
- Tenant isolation is not verified
- Audit logging is not implemented
- Real client data would be involved
- Any guarantee would be made
- Any client-facing content would be auto-approved
