# Work Order: Connect Client Portal to Supabase Client Profile Data

**Status:** Draft
**Priority:** High
**Source:** Client Portal Premium UI Foundation Sprint
**Created:** 2026-07-07

## Objective
Replace mock `clientPortalData` with live Supabase client profile queries.

## Scope
- Query `client_profiles` table for name, membership tier, current goal, subscription status
- Query `client_tasks` table for open tasks and next actions
- Query `client_documents` table for document status
- Query `client_credit_profile` table for readiness scores
- Enable `clientDataMode.liveSupabaseTestClientEnabled` when ready

## Acceptance Criteria
- Dashboard shows real client name and membership tier
- Task list reflects actual open tasks from Supabase
- Document status shows real upload status
- Credit scores reflect live data (or graceful fallback to demo)
- No regressions in existing portal pages

## Dependencies
- Supabase schema must have `client_profiles`, `client_tasks`, `client_documents` tables
- RLS policies must allow authenticated client reads
- `clientDataMode` must be configurable per environment

## Notes
- Existing `loadClientDashboardLiveData()` service already exists
- Demo data remains as fallback when live data unavailable
