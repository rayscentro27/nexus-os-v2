# Client Portal Table Health Check

**Generated:** 2026-07-07

## Table-by-Table Status

| Table | Exists | RLS Enabled | Client Read | Admin Read | Notes |
|-------|--------|-------------|-------------|------------|-------|
| client_profiles | ✓ | ✓ | ✓ (own) | ✓ | 2 rows, active |
| tenant_memberships | ✓ | ✓ | ✓ (self) | ✓ | 1 row |
| client_tasks | ✓ | ✓ | ✓ (own) | ✓ | Ready |
| client_documents | ✓ | ✓ | ✓ (own) | ✓ | Ready |
| readiness_scores | ✓ | ✓ | ✓ (own) | ✓ | Ready |
| credit_workflow_items | ✓ | ✓ | ✓ (own) | ✓ | Ready |
| dispute_cases | ✓ | ✓ | ✓ (own) | ✓ | Ready |
| dispute_letter_drafts | ✓ | ✓ | ✓ (own) | ✓ | Ready |
| business_profile_requirements | ✓ | ✓ | ✓ (own) | ✓ | Ready |
| funding_readiness_scores | ✓ | ✓ | ✓ (own) | ✓ | Ready |
| approval_cards | ✓ | ✓ | ✓ (own) | ✓ | Ready |
| admin_review_queue | ✓ | ✓ | ✓ (own) | ✓ | Ready |
| approved_client_guidance | ✓ | ✓ | ✓ (own) | ✓ | Ready |
| client_questions | ✓ | ✓ | ✓ (own) | ✓ | Ready |
| client_escalations | ✓ | ✓ | ✓ (own) | ✓ | Ready |
| proof_events | ✓ | ✓ | ✓ (own) | ✓ | Ready |
| connector_health | ✓ | ✓ | ✓ (own) | ✓ | Ready |
| engine_runs | ✓ | ✓ | ✓ (own) | ✓ | Ready |
| youtube_sources | ✓ | ✓ | ✓ (own) | ✓ | Ready |
| youtube_review_items | ✓ | ✓ | ✓ (own) | ✓ | Ready |
| social_drafts | ✓ | ✓ | ✓ (own) | ✓ | Ready |
| subscription_memberships | ✓ | ✓ | ✓ (own) | ✓ | Ready |
| payments_status | ✓ | ✓ | ✓ (own) | ✓ | Ready |

## RLS Policies

All tables use the same pattern:
- **Client read:** Via `tenant_memberships` link (client_id match + client_visible)
- **Admin read:** Via `nexus_is_active_admin()` function
- **Admin write:** Via `nexus_is_active_admin()` function

## Safety

- No overly broad public access
- Client can only read own records
- Admin remains isolated
- Frontend does not require service role key
- No risky policies found

## Blockers

- None.
