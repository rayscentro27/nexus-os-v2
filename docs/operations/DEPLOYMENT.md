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
RLS blocks anon reads until a policy exists. Two safe options:
1. **Authenticated admin** (preferred): add Supabase Auth, then policies that allow the
   authenticated admin role to read the relevant tables.
2. **Public read-only projection**: create a restricted view + policy exposing only
   non-sensitive columns for the dashboard.

Do not "fix" reads by loosening to the service role in the browser.
