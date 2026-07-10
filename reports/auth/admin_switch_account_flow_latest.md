# Admin Switch Account Flow

## Blocked Admin Page

When a non-admin authenticated user visits `/admin`, Nexus now shows:

- `Admin access required`
- Signed-in email when safely available
- `Sign out and switch account`
- `Go to client dashboard`
- `Admin login`

The switch-account and admin-login actions clear Supabase and Nexus local session cache before routing to `/admin/login`.

## Admin Login Path

- Route: `/admin/login`
- Copy: `Use an approved GoClear admin account.`
- Login still uses Supabase email/password auth.
- Admin access is still decided by AdminGuard after login.

## Emergency Reset

- Route: `/auth/reset`
- Clears stuck Supabase/Nexus auth cache.
- Offers buttons to client login and admin login.

## Ray Test Flow

1. Log in as `theworldzmine@gmail.com`.
2. Visit `/admin`; access remains blocked.
3. Click `Sign out and switch account`.
4. Sign in at `/admin/login` with an approved admin account.
5. Visit `/admin` and `/admin/credit-specialist`.
