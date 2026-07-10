# Logout Session Cleanup

Implemented `src/lib/authSessionCleanup.ts`.

## Behavior

- Calls `supabase.auth.signOut({ scope: "global" })` when available.
- Falls back to normal `supabase.auth.signOut()`.
- Removes matching `localStorage` and `sessionStorage` keys containing:
  - `supabase`
  - `sb-`
  - `nexus`
  - `client_profile`
  - `clientProfile`
  - `tenant_membership`
  - `tenantMembership`
  - `admin_user`
  - `adminUser`
  - `goclear`
- Returns a safe cleanup summary.
- Does not print tokens, refresh tokens, or secrets.

## Logout Destinations

- Client logout: `/client/login`
- Admin logout: `/admin/login`
- Reset page: `/auth/reset`

## Security

- AdminGuard remains secure.
- RLS was not changed.
- Service role is not used in frontend.
