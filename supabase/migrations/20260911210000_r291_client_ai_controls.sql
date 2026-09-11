begin;

create table if not exists public.client_ai_controls (
  id uuid primary key default gen_random_uuid(),
  tenant_id text not null,
  client_id text not null,
  user_id uuid references auth.users(id) on delete cascade,
  clyde_enabled boolean not null default true,
  customer_service_ai_enabled boolean not null default true,
  access_tier text not null default 'CLIENT',
  token_daily_limit integer not null default 40 check (token_daily_limit between 0 and 1000),
  session_limit integer not null default 12 check (session_limit between 0 and 200),
  expensive_call_limit integer not null default 0 check (expensive_call_limit between 0 and 100),
  escalation_only_mode boolean not null default false,
  client_ai_paused boolean not null default false,
  guest_access_revoked boolean not null default false,
  convert_to_paid_workflow boolean not null default false,
  updated_by uuid references auth.users(id),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (tenant_id, client_id)
);

create index if not exists client_ai_controls_user_idx on public.client_ai_controls(user_id);
alter table public.client_ai_controls enable row level security;
drop policy if exists client_ai_controls_admin_select on public.client_ai_controls;
create policy client_ai_controls_admin_select on public.client_ai_controls for select to authenticated using (public.nexus_is_active_admin());
drop policy if exists client_ai_controls_admin_write on public.client_ai_controls;
create policy client_ai_controls_admin_write on public.client_ai_controls for all to authenticated using (public.nexus_is_active_admin()) with check (public.nexus_is_active_admin());
drop policy if exists client_ai_controls_owner_select on public.client_ai_controls;
create policy client_ai_controls_owner_select on public.client_ai_controls for select to authenticated using (user_id = auth.uid());
grant select, insert, update on public.client_ai_controls to authenticated;

commit;
