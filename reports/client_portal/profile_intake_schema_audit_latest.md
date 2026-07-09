# Profile Intake Schema Audit

**Date:** 2026-07-08
**Starting commit:** 8818221

## 1. Existing client_profiles columns

The `client_profiles` table (UUID PK) has these columns from migrations:

| Column | Type | Notes |
|--------|------|-------|
| `id` | uuid (PK) | Auth user ID |
| `workspace_id` | uuid | Workspace reference |
| `client_label` | text | Used for display name |
| `current_stage` | text | Workflow stage |
| `next_required_action` | text | Workflow action |
| `due_at` | timestamptz | Due date |
| `days_stuck` | integer | Stuck counter |
| `progress_percentage` | integer | Progress |
| `funding_readiness_impact` | integer | Funding impact |
| `revenue_risk_level` | text | Risk level |
| `ray_review_status` | text | Review status |
| `client_visible_status` | text | Client-facing status |
| `selected_credit_report_source` | text | Credit source |
| `source_selected_at` | timestamptz | Source selection time |
| `affiliate_partner_id` | uuid | Affiliate ref |
| `affiliate_url` | text | Affiliate URL |
| `affiliate_disclosure_accepted` | bool | Disclosure |
| `client_consent_accepted` | bool | Consent |
| `score_available` | bool | Score flag |
| `score_source` | text | Score source |
| `report_upload_status` | text | Upload status |
| `report_import_status` | text | Import status |
| `sensitivity` | text | Sensitivity level |
| `metadata` | jsonb | Generic metadata |
| `external_id` | text | External identifier |
| `tenant_id` | text | Portal tenant ID |
| `client_id` | text | Portal client ID |
| `category` | text | Category |
| `title` | text | Business name |
| `summary` | text | Summary |
| `status` | text | Status |
| `score` | numeric | Score |
| `priority` | text | Priority |
| `risk_level` | text | Risk level |
| `automation_level` | text | Automation level |
| `client_visible` | bool | Client visibility |
| `approval_required` | bool | Approval flag |
| `goclear_review_status` | text | Review status |
| `source` | text | Data source |
| `source_concept` | text | Source concept |
| `recommended_next_action` | text | Next action |
| `payload` | jsonb | Generic JSON payload |
| `created_at` | timestamptz | Created |
| `updated_at` | timestamptz | Updated |

## 2. What's missing for profile intake

The `client_profiles` table has NO dedicated columns for:
- Legal name (only `client_label` which is set at signup)
- Preferred name
- Phone
- Mailing address (line1, line2, city, state, postal)
- Business address (line1, line2, city, state, postal)
- Entity type
- EIN status
- Industry / NAICS
- Time in business
- Monthly revenue range
- Funding goal range

## 3. Where data currently lives

- `client_label` — set to full_name from signup metadata (or email)
- `title` — set to business_name from signup metadata (or null)
- `payload` — JSONB, currently stores `membershipTier`, `currentGoal`, `subscriptionStatus`, etc.

## 4. business_profile_requirements

This table stores field-level completion **requirements** only (rows with `title`, `status`, `payload`). It does NOT store actual client-provided answers. It's a checklist tracker, not a data store.

## 5. Existing profile/intake form component

**None.** No dedicated profile or intake form component exists in the codebase.

## 6. Recommended route

Add `/client/profile` — "Profile & Business Info"

## 7. Recommended storage

Add explicit columns to `client_profiles` for the intake fields. This enables:
- Direct column reads (no JSONB parsing)
- RLS on specific fields if needed
- Admin querying
- Clean adapter pattern

## 8. Migration needed

**Yes.** Create `20260708120000_client_profile_intake_fields.sql` that:
- Adds ~20 safe text columns to `client_profiles`
- Keeps RLS enabled (no policy changes needed — existing self-update policy covers the row)
- Does not weaken existing policies
- Client updates only their own row via tenant_memberships relationship

## 9. Security caveats

- Existing RLS: self-select (own row via tenant_memberships), self-update (own row), admin manage
- No additional RLS needed — the new columns are on the existing `client_profiles` row
- Client can only UPDATE their own row (existing policy)
- Admin can read all rows (existing policy)
- No service role, no RLS disable, no anon access
