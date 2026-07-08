# Actual Schema Tester Activation Audit

**Generated:** 2026-07-07  
**Current Commit:** 9c719e5  
**Build:** ✓ Clean

## Actual Tables Verified (LIVE)

| Table | Exists | RLS | Columns Used |
|-------|--------|-----|--------------|
| client_profiles | ✓ | ✓ | tenant_id, client_id, title, status, category, client_visible, payload |
| tenant_memberships | ✓ | ✓ | tenant_id, user_id, role, client_id |
| client_tasks | ✓ | ✓ | id, tenant_id, client_id, category, title, status, priority, client_visible |
| client_documents | ✓ | ✓ | id, tenant_id, client_id, category, title, status, client_visible |
| readiness_scores | ✓ | ✓ | id, tenant_id, client_id, category, title, score, status, client_visible |
| credit_workflow_items | ✓ | ✓ | id, tenant_id, client_id, category, title, status, client_visible |
| business_profile_requirements | ✓ | ✓ | id, tenant_id, client_id, category, title, status, client_visible |
| approved_client_guidance | ✓ | ✓ | id, tenant_id, client_id, category, title, summary, status, client_visible, approval_required |

## Wrong Table References

- **Active source code (src/):** NONE ✓
- **Scripts:** NONE ✓
- **Data files:** NONE ✓
- **Old reports:** References exist in historical reports (not actionable, schema already corrected)

## Conclusion

No code changes needed. All active code uses the correct table names.
