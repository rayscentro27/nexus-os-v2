# Supabase Setup

## 1. Create the project
1. Create a **new** Supabase project (do not reuse the old Nexus project).
2. Copy from Project Settings → API:
   - Project URL → `VITE_SUPABASE_URL` (and `SUPABASE_URL` for scripts)
   - `anon` public key → `VITE_SUPABASE_ANON_KEY`
   - `service_role` secret key → `SUPABASE_SERVICE_ROLE_KEY` (server/scripts only)
3. Put these in `.env` (never commit them).

## 2. Apply the schema (in order)
In the Supabase SQL editor (or `supabase db push`):
```sql
-- 1) supabase/migrations/0001_nexus_os_v2_core.sql   -- 13 tables, indexes, RLS enabled
-- 2) supabase/seed/0001_social_accounts.sql          -- FB + IG accounts (no tokens)
-- 3) supabase/migrations/0002_admin_read_policies.sql -- admin_users + admin SELECT policies
```

## 2b. Grant yourself admin read access
RLS is on, and 0002 only lets **active rows in `admin_users`** read dashboard data (no anon,
no blanket-authenticated). To enable Ray's dashboard:
1. Create an auth user: Supabase Dashboard → Authentication → Add user (e.g.
   `goclearonline@gmail.com`), or sign up through the app.
2. Add him to the admin allowlist (SQL editor):
   ```sql
   insert into admin_users (id, email)
   select id, email from auth.users where email = 'goclearonline@gmail.com'
   on conflict (id) do update set active = true;
   ```
An authenticated session for that user can now READ the dashboard tables; nobody else can.

## 3. Seed the Day 1 proof
```bash
python3 scripts/seed_day1_event.py
```
Inserts: 1 `nexus_events` row, 6 `system_health` rows, 1 pending `approval`. Uses the
service-role key from `.env`. The key is never printed.

## 4. Verify in the dashboard
```bash
npm run dev
```
Overview should show health pills; Approvals/Proof Log should show the seed event.

## RLS note
RLS is enabled on every table. Writes are service-role only (server/scripts). Reads:
- **anon / public:** none (no public policy — by design).
- **authenticated admin** (after migration 0002 + an `admin_users` row): SELECT on the
  dashboard tables.
The service role bypasses RLS and must stay server/script-side — never in `VITE_*`.
