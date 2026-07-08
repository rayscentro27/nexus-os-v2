# Client Portal Real Data Audit

**Date:** 2026-07-07
**Starting commit:** c5a0656

## Current Route Behavior

| Route | Behavior | Auth |
|-------|----------|------|
| `/` | Public GoClear landing page | None |
| `/client/login` | Client portal login (GoClear-branded) | None |
| `/client/preview` | Demo portal with preview banner | None |
| `/client/dashboard` | Client portal (redirects to `/client/login` if unauth) | Supabase session |
| `/admin` | Admin login | Supabase session (AuthGate) |
| `/admin/command-center` | Admin command center | Supabase session (AuthGate) |

## Current Preview Behavior

- `/client/preview` renders full `ClientPortalShell` with `clientPortalData` (mock)
- Shows "Preview Mode — Demo data only" banner
- No auth required

## Current Dashboard/Auth Behavior

- `ClientPortalGate` in `App.tsx:15` checks `useSession()` (Supabase auth)
- If no session: redirects to `/client/login`
- If authenticated: renders `ClientPortalRoot` → `ClientPortalShell` with `clientPortalData`
- Currently always uses mock data — no live Supabase queries on dashboard

## Supabase Tables Found

The migration `20260629095450_client_portal_core_tables.sql` creates:

| Table | Purpose | RLS |
|-------|---------|-----|
| `tenant_memberships` | Links auth users to tenants/clients | ✓ Self + admin |
| `client_profiles` | Client profile data | ✓ Tenant-based |
| `client_tasks` | Client tasks/actions | ✓ Tenant-based |
| `client_documents` | Document tracking | ✓ Tenant-based |
| `readiness_scores` | Readiness scores | ✓ Tenant-based |
| `credit_workflow_items` | Credit repair workflow | ✓ Tenant-based |
| `dispute_cases` | Dispute tracking | ✓ Tenant-based |
| `dispute_letter_drafts` | Dispute letter drafts | ✓ Tenant-based |
| `business_profile_requirements` | Business setup items | ✓ Tenant-based |
| `funding_readiness_scores` | Funding readiness | ✓ Tenant-based |
| `business_opportunities` | Business opportunities | ✓ Tenant-based |
| `partner_offers` | Partner/tool offers | ✓ Tenant-based |
| `approval_cards` | Approval tracking | ✓ Tenant-based |
| `admin_review_queue` | Admin review items | ✓ Tenant-based |
| `approved_client_guidance` | Approved guidance for clients | ✓ Tenant-based |
| `client_questions` | Client questions | ✓ Tenant-based |
| `client_escalations` | Client escalations | ✓ Tenant-based |
| `proof_events` | Proof/verification events | ✓ Tenant-based |
| `subscription_memberships` | Subscription status | ✓ Tenant-based |
| `payments_status` | Payment status | ✓ Tenant-based |

Plus existing admin tables: `admin_users`, `approvals`, `task_requests`, `nexus_events`, `system_health`, `agent_jobs`

## Existing Client-Related Schema

- `tenant_memberships` with `role = 'client'` and `client_id`
- `client_profiles` with portal fields (tenant_id, client_id, status, payload JSONB)
- `client_tasks` with client_visible flag
- `readiness_scores` for credit/business/funding scores
- `credit_workflow_items` for credit repair workflow
- `business_profile_requirements` for business setup
- `funding_readiness_scores` for funding readiness
- `approved_client_guidance` for approved client guidance

## Missing Client-Related Schema

- No dedicated `client_document_uploads` table (storage not configured)
- No dedicated `client_credit_checklist` table (uses `credit_workflow_items`)
- No dedicated `client_business_funding_checklist` table (uses `business_profile_requirements`)
- No `client_guidance_items` table (uses `approved_client_guidance`)

## Safest Implementation Path

1. Use existing tables — they already have the right structure and RLS
2. Use `payload JSONB` for flexible client-specific data
3. Use `client_visible` flag to control what clients see
4. Use `approved_client_guidance` for Hermes guidance
5. Create a data hook that tries Supabase first, falls back to demo data
6. Keep `/client/preview` always using demo data

## Risks/Blockers

- Migration `20260629095450` is marked "DRAFT ONLY" — not yet applied
- No storage bucket for document uploads
- No real client data seeded
- Live data reads gated behind `VITE_ENABLE_LIVE_SUPABASE_TEST_CLIENT`
- `client-warning` CSS class missing (fixed in this sprint)
