# Nexus Live UI Connection Failure Audit

Date: 2026-06-24

## Executive finding

The deployed Netlify app is not obviously running an old bundle. The public JS bundle at `https://nexusv20.netlify.app` matches the current local build family and contains the Supabase session persistence fix: `persistSession`, `autoRefreshToken`, and `detectSessionInUrl`.

The backend is also not empty. Supabase contains pending approval `13eafcab-6940-4612-8239-54786e8c9e60` for `Enable one Facebook GoClear/Apex test post`, and `admin_users` contains an active admin row for `goclearonline@gmail.com`.

The confirmed UI failure was that generic frontend reads returned `[]` for every Supabase query problem. That made missing env, no auth session, admin mismatch, RLS denial, schema/query errors, and true empty tables all look identical.

## Root cause category

Evidence supports these categories:

- UI swallows errors: confirmed. `src/services/db.ts` returned an empty array on query error, and `DataList` rendered generic empty states.
- Session/admin/RLS unknown in Ray's live browser: likely remaining live issue. The app can now show the exact live status in the UI.
- Netlify stale bundle: not supported by current evidence.
- Service worker/PWA cache: not supported by current evidence.
- Wrong Supabase project: not supported by current evidence; deployed bundle points at project ref `iqjwgpnujbeoyaeuwehj`.

## Evidence

- Live app: `https://nexusv20.netlify.app`
- Live landing page: `https://nexusv20.netlify.app/goclear-apex-readiness.html`
- Deployed bundle contains the session persistence strings.
- No real service worker or PWA cache was found in the repo or public deployment.
- Netlify HTML cache headers are `max-age=0,must-revalidate`.
- Deployed bundle includes the expected Supabase project ref.
- Backend approval exists and is pending.
- Backend admin row exists and is active for `goclearonline@gmail.com`.

## Code repair

Changed:

- `src/services/db.ts`
- `src/components/sections.tsx`

The UI now returns and displays safe connection diagnostics:

- `missing_env`
- `no_authenticated_session`
- `not_admin`
- `rls_denied_no_access`
- `query_error`
- `no_records`
- `connected_with_records`

The Approvals tab now displays:

- Supabase configured: yes/no
- Auth session present: yes/no
- User email, if available
- User id prefix, first 8 characters only
- Admin mapping found: yes/no/unknown
- Table queried
- Filter used
- Query result count
- Safe query error category/message

No secrets, JWTs, service-role keys, publish tokens, or customer-private data are displayed.

## Approvals query

The Approvals tab queries:

- table: `approvals`
- select: `*`
- filter: `limit=30 order=created_at.desc`

There is no frontend status, tenant, item type, user, or visibility filter that would exclude approval `13eafcab-6940-4612-8239-54786e8c9e60`.

If Ray is signed into the deployed app as the active admin user whose auth id matches `admin_users.id`, the pending approval should appear after this diagnostic build is deployed. If it does not appear, the panel should identify the failure as one of: missing env, no authenticated session, admin mapping not found, RLS/no access, or query error.

## Auth/admin/RLS assessment

RLS policies gate dashboard tables through `admin_users.id = auth.uid()` and `active = true`. The admin mapping is id-based, not merely email-based.

Known backend admin email: `goclearonline@gmail.com`.

Unknown until Ray views the live diagnostics:

- Whether the deployed browser has a current authenticated session.
- Whether Ray is signed in as `goclearonline@gmail.com`.
- Whether that live auth user's id prefix matches the admin row.
- Whether Supabase auth redirect settings include `https://nexusv20.netlify.app`.

## Safety confirmations

- No Facebook approval was changed.
- `publish_enabled` was not changed.
- No social post was published.
- No email was sent.
- No trade was placed.
- Scheduler was not started.
- No service-role key was exposed to frontend code.
- RLS was not weakened.
- No `.env` file was read into output or staged.

## Next action

Deploy this diagnostic build to Netlify, then open the deployed Approvals tab in an incognito window or after clearing site data. Sign in as `goclearonline@gmail.com`. The diagnostic panel will show the exact live failure point.
