# GoClear Profile Membership Frontend Status

**Date**: 2026-07-06

---

## Frontend Changes Made

### `/goclear/signup` (GoClearPublicPages.tsx)
- **Status**: NO CHANGES NEEDED
- Already calls `supabase.auth.signUp()` with `full_name` and `business_name` metadata
- Already shows "Check Your Email" confirmation
- The trigger handles profile/membership creation automatically
- No frontend INSERT into `tenant_memberships` needed

### `/client` Auth Gate (App.tsx)
- **Status**: ALREADY IMPLEMENTED (commit `ecefa61`)
- `ClientPortalGate` checks `useSession()`
- Redirects unauthenticated users to `/goclear/login`
- Shows loading state while checking

### Client Portal Shell (ClientPortalShell.jsx)
- **Status**: ALREADY IMPLEMENTED (commit `ecefa61`)
- `LogOut` icon imported from lucide-react
- Sign-out button in header: calls `supabase?.auth.signOut()` then redirects to `/goclear/login`
- Supabase client imported from `../../lib/supabaseClient`

### Login Error Handling
- **Status**: ALREADY IMPLEMENTED (commit `ecefa61`)
- "Email not confirmed" → friendly message
- "Invalid login credentials" → "Incorrect email or password"
- "User already registered" → friendly message on signup

## What's Still Mock

| Component | Data Source | Status |
|-----------|-------------|--------|
| ClientPortalShell | `clientPortalData` (mock) | MOCK |
| ClientPortalPages | `clientPortalData` (mock) | MOCK |
| HermesGuidancePanel | Hardcoded guidance | MOCK |

## What the Trigger Provides

After migration is applied:
1. Signup creates `client_profiles` row with:
   - `id` = auth user ID
   - `tenant_id` = 'goclear'
   - `client_id` = 'gc_' + user_id (no dashes)
   - `client_label` = full_name or email
   - `title` = business_name (if provided)
   - `status` = 'active'
   - `client_visible` = true
   - `source` = 'goclear_signup'

2. Signup creates `tenant_memberships` row with:
   - `tenant_id` = 'goclear'
   - `user_id` = auth user ID
   - `role` = 'client'
   - `client_id` = same as profile

## Remaining Frontend Work (Future)

1. Replace `clientPortalData` mock with Supabase queries
2. Query `client_profiles` for logged-in user's data
3. Query `client_tasks`, `client_documents`, etc. filtered by `client_id`
4. Show "Welcome, {name}" instead of hardcoded profile name
5. Show real readiness scores from `readiness_scores` table

## Status: FRONTEND COMPLETE FOR CURRENT SCOPE

Auth gate, sign-out, error handling all working. Trigger handles DB bootstrap.
