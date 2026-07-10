# Logout / Admin Session Audit

- Starting commit: `1779a94`
- Admin guard status before patch: secure; client tester accounts were blocked from `/admin`.
- Problem found: logout buttons called `supabase.auth.signOut()` directly and did not clear matching Supabase/Nexus/client/admin local/session storage keys.

## Logout Locations Found

- `src/pages/client/WorldClassClientPortal.jsx`
- `src/components/client/ClientPortalShell.jsx`
- `src/components/NexusAppShell.jsx`
- `src/components/auth.tsx`
- password recovery cleanup in `src/lib/authHelpers.ts`

## Supabase Session Storage

- Supabase client uses `persistSession: true`, `autoRefreshToken: true`, and `detectSessionInUrl: true`.
- Storage keys may include Supabase `sb-` keys plus app-level Nexus/client/admin cache keys.

## Admin Guard

- `src/components/auth/AdminGuard.tsx` checks `admin_users` first, then `tenant_memberships` roles `super_admin`, `admin`, or `operator`.
- No admin access was granted to `theworldzmine@gmail.com`.
- AdminGuard remains active and `/admin` is not public.

## Patch Plan Applied

- Add central `clearNexusAuthSession`.
- Route all discovered sign-out buttons through cleanup helper.
- Add blocked admin page switch-account controls.
- Add explicit `/admin/login`.
- Add emergency `/auth/reset`.
- Add client login reset-stuck-session button.
