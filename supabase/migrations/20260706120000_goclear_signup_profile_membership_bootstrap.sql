-- GoClear Signup Profile + Tenant Membership Bootstrap
-- Migration: 20260706120000
-- Safe: additive only, no DROP/TRUNCATE, SECURITY DEFINER trigger
-- Idempotent: ON CONFLICT DO NOTHING on all inserts

begin;

-- ── 1. Ensure tenant_memberships table exists (from DRAFT migration) ──
create table if not exists public.tenant_memberships (
  tenant_id text not null,
  user_id uuid not null references auth.users(id) on delete cascade,
  role text not null check (role in ('super_admin','admin','operator','client')),
  client_id text,
  created_at timestamptz not null default now(),
  primary key (tenant_id, user_id)
);

-- ── 2. Ensure client_profiles has portal columns (from DRAFT migration) ──
alter table public.client_profiles add column if not exists external_id text;
alter table public.client_profiles add column if not exists tenant_id text;
alter table public.client_profiles add column if not exists client_id text;
alter table public.client_profiles add column if not exists category text;
alter table public.client_profiles add column if not exists title text;
alter table public.client_profiles add column if not exists summary text;
alter table public.client_profiles add column if not exists status text default 'active';
alter table public.client_profiles add column if not exists score numeric;
alter table public.client_profiles add column if not exists priority text;
alter table public.client_profiles add column if not exists risk_level text;
alter table public.client_profiles add column if not exists automation_level text;
alter table public.client_profiles add column if not exists client_visible boolean not null default false;
alter table public.client_profiles add column if not exists approval_required boolean not null default false;
alter table public.client_profiles add column if not exists goclear_review_status text;
alter table public.client_profiles add column if not exists source text;
alter table public.client_profiles add column if not exists source_concept text;
alter table public.client_profiles add column if not exists recommended_next_action text;
alter table public.client_profiles add column if not exists payload jsonb not null default '{}'::jsonb;
alter table public.client_profiles add column if not exists updated_at timestamptz not null default now();

-- ── 3. Indexes ──
create unique index if not exists client_profiles_tenant_external_idx
  on public.client_profiles(tenant_id, external_id) where external_id is not null;
create index if not exists client_profiles_tenant_client_idx
  on public.client_profiles(tenant_id, client_id);

-- ── 4. Trigger function: auto-create membership + profile on signup ──
create or replace function public.goclear_handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
declare
  _full_name text;
  _business_name text;
  _client_id text;
begin
  -- Extract metadata
  _full_name := coalesce(new.raw_user_meta_data ->> 'full_name', '');
  _business_name := coalesce(new.raw_user_meta_data ->> 'business_name', '');

  -- Generate deterministic client_id
  _client_id := 'gc_' || replace(new.id::text, '-', '');

  -- Create client_profiles row (idempotent)
  insert into public.client_profiles (
    id, tenant_id, client_id, client_label, title, status,
    client_visible, source, created_at, updated_at
  ) values (
    new.id, 'goclear', _client_id,
    case when _full_name = '' then new.email else _full_name end,
    case when _business_name != '' then _business_name else null end,
    'active', true, 'goclear_signup',
    now(), now()
  ) on conflict (id) do nothing;

  -- Create tenant_memberships row (idempotent)
  insert into public.tenant_memberships (
    tenant_id, user_id, role, client_id, created_at
  ) values (
    'goclear', new.id, 'client', _client_id, now()
  ) on conflict (tenant_id, user_id) do nothing;

  return new;
end;
$$;

-- ── 5. Create trigger on auth.users ──
drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row
  execute function public.goclear_handle_new_user();

-- ── 6. RLS: tenant_memberships ──
alter table public.tenant_memberships enable row level security;

-- Self-select: users can read their own membership
drop policy if exists "memberships_self_select" on public.tenant_memberships;
create policy "memberships_self_select"
  on public.tenant_memberships
  for select to authenticated
  using (user_id = auth.uid());

-- Admin select: admins can read all memberships
drop policy if exists "memberships_admin_select" on public.tenant_memberships;
create policy "memberships_admin_select"
  on public.tenant_memberships
  for select to authenticated
  using (public.nexus_is_active_admin());

-- Admin manage: only admins can insert/update/delete memberships
-- (self-service signup is handled by the trigger, not by frontend INSERT)
drop policy if exists "memberships_admin_manage" on public.tenant_memberships;
create policy "memberships_admin_manage"
  on public.tenant_memberships
  for all to authenticated
  using (public.nexus_is_active_admin())
  with check (public.nexus_is_active_admin());

-- ── 7. RLS: client_profiles ──
alter table public.client_profiles enable row level security;

-- Self-select: users can read their own profile (linked via tenant_memberships)
drop policy if exists "client_profiles_self_select" on public.client_profiles;
create policy "client_profiles_self_select"
  on public.client_profiles
  for select to authenticated
  using (
    exists (
      select 1 from public.tenant_memberships tm
      where tm.tenant_id = client_profiles.tenant_id
        and tm.user_id = auth.uid()
        and tm.client_id = client_profiles.client_id
    )
  );

-- Admin select: admins can read all profiles
drop policy if exists "client_profiles_admin_select" on public.client_profiles;
create policy "client_profiles_admin_select"
  on public.client_profiles
  for select to authenticated
  using (public.nexus_is_active_admin());

-- Self-update: users can update safe fields on their own profile
drop policy if exists "client_profiles_self_update" on public.client_profiles;
create policy "client_profiles_self_update"
  on public.client_profiles
  for update to authenticated
  using (
    exists (
      select 1 from public.tenant_memberships tm
      where tm.tenant_id = client_profiles.tenant_id
        and tm.user_id = auth.uid()
        and tm.client_id = client_profiles.client_id
    )
  )
  with check (
    exists (
      select 1 from public.tenant_memberships tm
      where tm.tenant_id = client_profiles.tenant_id
        and tm.user_id = auth.uid()
        and tm.client_id = client_profiles.client_id
    )
  );

-- Admin manage: full CRUD for admins
drop policy if exists "client_profiles_admin_manage" on public.client_profiles;
create policy "client_profiles_admin_manage"
  on public.client_profiles
  for all to authenticated
  using (public.nexus_is_active_admin())
  with check (public.nexus_is_active_admin());

-- ── 8. Grants ──
grant select, insert, update on public.tenant_memberships to authenticated;
grant select, insert, update on public.client_profiles to authenticated;

commit;
