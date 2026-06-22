-- Nexus OS v2 — Day 2A: authenticated ADMIN read policies for the dashboard.
--
-- Model: role-based, not blanket-authenticated. Only rows in `admin_users` (active) can read
-- dashboard data. This is stricter than "any logged-in user" — sensitive tables like
-- social_accounts must not be readable by arbitrary authenticated users.
--
-- NOT added here (on purpose): anon/public read, and any INSERT/UPDATE/DELETE for the
-- frontend. Writes stay server/script-side with the service role (which bypasses RLS).

-- ── Admin allowlist ──
create table if not exists admin_users (
  id         uuid primary key references auth.users(id) on delete cascade,
  created_at timestamptz not null default now(),
  email      text,
  role       text not null default 'admin',
  active      boolean not null default true
);
alter table admin_users enable row level security;

-- An admin may read the admin list (e.g. to confirm their own membership). No writes here —
-- membership is managed by the service role / SQL editor only.
drop policy if exists "admin read admin_users" on admin_users;
create policy "admin read admin_users"
  on admin_users for select to authenticated
  using (exists (select 1 from admin_users a where a.id = auth.uid() and a.active = true));

-- ── Reusable predicate: is the caller an active admin? ──
-- Inlined into each policy below (Postgres RLS can't reference a shared expression directly).

-- ── SELECT-only admin read policies on every dashboard table ──
do $$
declare t text;
begin
  foreach t in array array[
    'nexus_events','agent_jobs','approvals','social_accounts','social_posts',
    'social_publish_receipts','creative_assets','business_opportunities',
    'trading_signals','demo_trades','telegram_messages','system_health','settings'
  ]
  loop
    execute format('drop policy if exists %I on %I', 'admin read ' || t, t);
    execute format(
      'create policy %I on %I for select to authenticated using ('
      || 'exists (select 1 from admin_users a where a.id = auth.uid() and a.active = true))',
      'admin read ' || t, t
    );
  end loop;
end $$;

-- ── How to grant Ray admin access (run once, in the SQL editor) ──
-- 1) Create an auth user for Ray (Supabase Dashboard → Authentication → Add user),
--    or have him sign up through the app.
-- 2) Insert his auth user id into admin_users:
--      insert into admin_users (id, email)
--      select id, email from auth.users where email = 'goclearonline@gmail.com'
--      on conflict (id) do update set active = true;
-- After that, an authenticated session for Ray can READ the dashboard tables; no one else can.
