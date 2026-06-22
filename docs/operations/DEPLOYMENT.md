# Deployment

## Frontend (dashboard)
- Build: `npm run build` → `dist/`.
- Host on Netlify/Vercel/static host. Set env vars **`VITE_SUPABASE_URL`** and
  **`VITE_SUPABASE_ANON_KEY`** in the host's dashboard (not in the repo).
- Never set `SUPABASE_SERVICE_ROLE_KEY` or any token as a `VITE_*` var — that would ship it
  to the browser.

## Server / scripts / job runner
- Run with the full `.env` (service role + tokens) on a trusted host only.
- The Day 1 seed and future jobs use the service role to write the ledger.

## Branch discipline
- `main` is the source of truth. Protect it. Deploy from `main`.
- Small commits, secret-scanned, pushed. No long-lived preview branches.

## RLS / frontend reads
The chosen model (migration `0002_admin_read_policies.sql`) is **authenticated admin**:
- The browser uses the **anon key** to authenticate a Supabase session (sign-in).
- Only users in `admin_users` (active) can SELECT dashboard tables — no anon/public reads.
- The service role is **never** used in the browser; writes stay server/script-side.

To make the deployed dashboard show data: apply 0001 → seed → 0002, create an auth user for
the admin, add them to `admin_users`, and add a sign-in flow (Day 2B). Do not "fix" reads by
adding a public anon policy or by putting the service-role key in `VITE_*`.
