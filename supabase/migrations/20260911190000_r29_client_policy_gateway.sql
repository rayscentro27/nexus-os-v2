-- R29: client policy gateway, bounded Clyde/Customer Service state.
begin;

create table if not exists public.client_ai_conversations (
  id uuid primary key default gen_random_uuid(),
  tenant_id text not null,
  client_id text not null,
  user_id uuid not null references auth.users(id) on delete cascade,
  session_id text,
  channel text not null default 'CLIENT_PORTAL' check (channel = 'CLIENT_PORTAL'),
  intent text not null,
  user_message text not null check (char_length(user_message) <= 2000),
  assistant_message text not null check (char_length(assistant_message) <= 6000),
  policy_decision text not null check (policy_decision in ('POLICY_ALLOW','POLICY_DENY','POLICY_ESCALATE','POLICY_REQUIRE_HUMAN','POLICY_REQUIRE_PAYMENT')),
  model_tier text not null default 'TIER_0',
  estimated_cost_class text not null default 'NEAR_ZERO',
  created_at timestamptz not null default now()
);

create table if not exists public.client_ai_escalations (
  id uuid primary key default gen_random_uuid(),
  tenant_id text not null,
  client_id text not null,
  user_id uuid not null references auth.users(id) on delete cascade,
  intent text not null,
  question text not null check (char_length(question) <= 2000),
  known_facts jsonb not null default '{}'::jsonb,
  missing_facts jsonb not null default '[]'::jsonb,
  recommended_owner text not null,
  priority text not null default 'normal' check (priority in ('low','normal','high','urgent')),
  status text not null default 'OPEN' check (status in ('OPEN','IN_REVIEW','ANSWERED','CLOSED','CANCELLED')),
  created_at timestamptz not null default now(),
  resolved_at timestamptz,
  resolution_summary text
);

create table if not exists public.client_ai_usage (
  id uuid primary key default gen_random_uuid(),
  tenant_id text not null,
  client_id text not null,
  user_id uuid not null references auth.users(id) on delete cascade,
  request_date date not null default current_date,
  call_count integer not null default 0,
  expensive_call_count integer not null default 0,
  last_request_at timestamptz not null default now(),
  unique (user_id, request_date)
);

create index if not exists client_ai_conversations_owner_idx on public.client_ai_conversations(tenant_id, client_id, created_at desc);
create index if not exists client_ai_conversations_session_idx on public.client_ai_conversations(user_id, session_id, created_at desc);
create index if not exists client_ai_escalations_owner_idx on public.client_ai_escalations(tenant_id, client_id, created_at desc);

alter table public.client_ai_conversations enable row level security;
alter table public.client_ai_escalations enable row level security;
alter table public.client_ai_usage enable row level security;

drop policy if exists client_ai_conversations_owner_select on public.client_ai_conversations;
create policy client_ai_conversations_owner_select on public.client_ai_conversations for select to authenticated using (
  public.nexus_is_active_admin() or (user_id = auth.uid() and exists (select 1 from public.tenant_memberships tm where tm.tenant_id = client_ai_conversations.tenant_id and tm.user_id = auth.uid() and tm.role = 'client' and tm.client_id = client_ai_conversations.client_id))
);
drop policy if exists client_ai_escalations_owner_select on public.client_ai_escalations;
create policy client_ai_escalations_owner_select on public.client_ai_escalations for select to authenticated using (
  public.nexus_is_active_admin() or (user_id = auth.uid() and exists (select 1 from public.tenant_memberships tm where tm.tenant_id = client_ai_escalations.tenant_id and tm.user_id = auth.uid() and tm.role = 'client' and tm.client_id = client_ai_escalations.client_id))
);
drop policy if exists client_ai_usage_admin_select on public.client_ai_usage;
create policy client_ai_usage_admin_select on public.client_ai_usage for select to authenticated using (public.nexus_is_active_admin() or user_id = auth.uid());

grant select on public.client_ai_conversations, public.client_ai_escalations, public.client_ai_usage to authenticated;
commit;
