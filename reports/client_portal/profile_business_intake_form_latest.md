# Profile & Business Intake Form — Implementation Report

**Date:** 2026-07-08
**Starting commit:** 8818221
**Route added:** `/client/profile`

## What was added

### Route
- `/client/profile` — "Profile & Business Info" page

### Component
- `ProfileBusinessIntakeForm` in `ClientPortalPages.jsx`
- Form sections: Personal Contact, Business Identity, Business Address, Funding Readiness
- Shows live data banner when connected to Supabase
- Shows progress bar with completeness percentage
- Shows missing required fields
- Warns: "Do not enter SSN or bank account numbers here"

### Fields supported (21 fields)

**Personal Contact:**
- `legal_name` (required)
- `preferred_name`
- `phone` (required)
- `mailing_address_line1`
- `mailing_address_line2`
- `city`
- `state`
- `postal_code`

**Business Identity:**
- `business_name` (required)
- `entity_type` (required) — dropdown: LLC, Corporation, Sole Proprietorship, Partnership, S Corp, Nonprofit, Other
- `ein_status` — dropdown: Active, Pending, Not applicable
- `industry` (required)
- `naics_code`

**Business Address:**
- `business_address_line1`
- `business_address_line2`
- `business_city`
- `business_state`
- `business_postal_code`

**Funding Readiness:**
- `time_in_business` — dropdown: <1yr, 1-2yr, 2-5yr, 5+yr
- `monthly_revenue_range` — dropdown: <$5k to $100k+
- `funding_goal_range` — dropdown: <$10k to $250k+

### Table / Columns used
- `client_profiles` — 21 new text columns added via migration

### Migration
- `20260708120000_client_profile_intake_fields.sql`
- Adds all 21 columns with `add column if not exists`
- No RLS changes — existing self-update policy covers the row
- No policy weaken, no DROP, no TRUNCATE

### Adapter functions added
- `loadClientProfileIntake()` — reads profile intake fields from `client_profiles`
- `saveClientProfileIntake(payload)` — updates profile intake fields on `client_profiles`
- `checkProfileIntakeComplete(data)` — validates required fields and returns completeness

### Dashboard integration
- Dashboard shows "Complete Profile & Business Info" CTA if profile is incomplete
- Shows missing fields and completeness percentage

### Hermes guidance integration
- Added `profileIncomplete` status to `generateClientGuidance()`
- Hermes shows "Complete Profile & Business Info" as high priority if incomplete
- Shell fetches profile intake on mount to compute `profileIncomplete`

### Admin integration
- `ClientsPanel.jsx` ClientDetailDrawer shows profile fields for selected client
- Fetches `legal_name`, `phone`, `business_name`, `entity_type`, `industry`, etc.
- Shows "No profile intake data submitted yet" if empty

## Security

- No SSN, full DOB, bank account, or credit card fields
- Warning displayed: "Do not enter SSN or bank account numbers here"
- Client updates only their own row via existing RLS self-update policy
- Admin reads via existing admin select policy
- No service-role usage in frontend
- No RLS disabled

## Manual test steps

1. Sign in as a test client
2. Navigate to `/client/profile`
3. Fill in required fields (legal name, phone, business name, entity type, industry)
4. Click "Save Profile"
5. Verify "Profile saved" confirmation
6. Verify "Live data connected" banner
7. Navigate to Dashboard — verify profile completion CTA is gone
8. Sign in as admin
9. Navigate to Admin > Clients
10. Click a client — verify profile fields appear in detail drawer

## Remaining caveats

- Profile completeness is client-side only — no server-side validation yet
- No email/phone verification
- No entity type verification
- Admin cannot edit client profile from drawer (read-only)
- No bulk profile import
