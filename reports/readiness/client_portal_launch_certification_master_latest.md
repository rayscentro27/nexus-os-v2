# Client Portal Launch Certification — Master Report

**Date:** 2026-07-08
**Starting commit:** 8818221

## Routes Certified

| Route | Component | Live Data | Build | Status |
|-------|-----------|-----------|-------|--------|
| `/client/login` | `ClientLoginPage` | Supabase auth | PASS | READY |
| `/client/dashboard` | `ClientDashboard` | Live scores + tasks | PASS | READY |
| `/client/profile` | `ProfileBusinessIntakeForm` | Live profile intake | PASS | READY |
| `/client/credit-profile` | `CreditProfilePage` | Live readiness_scores | PASS | READY |
| `/client/credit-utilization` | `CreditUtilizationPage` | Live credit_workflow_items | PASS | READY |
| `/client/documents` | `ClientDocumentsPage` | Live client_documents | PASS | READY |
| `/client/business-setup` | `BusinessSetupPage` | Live business_profile_requirements | PASS | READY |
| `/client/business-bankability` | `BusinessBankabilityPage` | Live business_profile_requirements | PASS | READY |
| `/client/funding-readiness` | `FundingReadinessPage` | Live funding_readiness_scores | PASS | READY |
| `/client/recommendations` | `RecommendationsPage` | Live partner_offers | PASS | READY |
| `/client/resources` | `ResourcesPage` | Live partner_offers | PASS | READY |
| `/client/request-review` | `RequestReviewPage` | Live tasks + funding scores | PASS | READY |
| `/admin` | `NexusAdminUI` | AdminGuard protected | PASS | READY |
| `/admin/command-center` | `NexusAdminUI` | AdminGuard protected | PASS | READY |

## Fields Supported (Profile Intake)

- `legal_name` (required)
- `preferred_name`
- `phone` (required)
- `mailing_address_line1`, `mailing_address_line2`, `city`, `state`, `postal_code`
- `business_name` (required)
- `entity_type` (required) — dropdown
- `ein_status` — dropdown
- `industry` (required)
- `naics_code`
- `business_address_line1`, `business_address_line2`, `business_city`, `business_state`, `business_postal_code`
- `time_in_business` — dropdown
- `monthly_revenue_range` — dropdown
- `funding_goal_range` — dropdown

## Table / Columns Used

- `client_profiles` — 21 new text columns via migration `20260708120000_client_profile_intake_fields.sql`
- No new tables created
- No duplicate tables

## Migration

- Name: `20260708120000_client_profile_intake_fields.sql`
- Type: Additive only (ALTER TABLE ADD COLUMN IF NOT EXISTS)
- RLS: No changes — existing policies cover new columns
- Rollback: DROP COLUMN IF EXISTS (not included in migration)

## RLS / Security Status

- RLS enabled on all client portal tables
- Client can SELECT/UPDATE own row via `tenant_memberships` relationship
- Admin can SELECT/ALL via `nexus_is_active_admin()` function
- No service-role key in frontend
- No RLS disabled
- No anon/public policies
- AdminGuard protects `/admin` routes
- Profile intake: client writes only to own `client_profiles` row

## Build Results

| Check | Result |
|-------|--------|
| `npm run build` | PASS |
| `npx tsc --noEmit` | PASS |
| `check_client_portal_actions.py` | PASS |
| `check_admin_route_guard.py` | PASS (11/11) |
| `check_client_live_data_wiring.py` | PASS |

## Manual Test Steps

### Client Profile Intake
1. Sign in as test client
2. Navigate to `/client/profile`
3. Fill required fields: legal name, phone, business name, entity type, industry
4. Click "Save Profile" — verify success confirmation
5. Refresh page — verify fields persist
6. Navigate to Dashboard — verify no incomplete profile CTA

### Admin Profile View
1. Sign in as admin
2. Navigate to Admin > Clients
3. Click a client with profile data
4. Verify "Profile & Business Info" section shows in detail drawer
5. Verify all submitted fields are visible

### Route Safety
1. Verify `/client/login` works
2. Verify `/client/dashboard` works
3. Verify `/client/documents` works
4. Verify `/client/request-review` works
5. Verify `/admin` requires admin access
6. Verify `/admin/command-center` requires admin access

## Remaining Caveats

- Profile completeness is client-side only — no server-side validation
- No email/phone verification
- No entity type verification
- Admin cannot edit client profile from drawer (read-only)
- No bulk profile import
- No real sensitive data collection (SSN, DOB, bank accounts blocked by design)
- Messages and Settings pages still use static demo data

## Tester Readiness

| Criterion | Status |
|-----------|--------|
| 1 tester ready | YES — Ray can test |
| 3 testers ready | NO — needs 2 more test accounts |
| Paid clients ready | NO — needs billing integration |
| Real sensitive data ready | NO — by design, not collected |
