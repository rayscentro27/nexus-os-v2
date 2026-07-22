create table if not exists public.hermes_conversation_state (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null,
  tenant_id uuid,
  conversation_id text not null,
  pending_action jsonb,
  reference_state jsonb,
  version integer not null default 1,
  expires_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique(user_id, conversation_id)
);

alter table public.hermes_conversation_state enable row level security;

do $$
begin
  if not exists (
    select 1 from pg_policies
    where schemaname = 'public' and tablename = 'hermes_conversation_state'
      and policyname = 'hermes conversation state owner read'
  ) then
    create policy "hermes conversation state owner read"
    on public.hermes_conversation_state
    for select
    to authenticated
    using (auth.uid() = user_id);
  end if;
end $$;

do $$
begin
  if not exists (
    select 1 from pg_policies
    where schemaname = 'public' and tablename = 'hermes_conversation_state'
      and policyname = 'hermes conversation state owner insert'
  ) then
    create policy "hermes conversation state owner insert"
    on public.hermes_conversation_state
    for insert
    to authenticated
    with check (auth.uid() = user_id);
  end if;
end $$;

do $$
begin
  if not exists (
    select 1 from pg_policies
    where schemaname = 'public' and tablename = 'hermes_conversation_state'
      and policyname = 'hermes conversation state owner update'
  ) then
    create policy "hermes conversation state owner update"
    on public.hermes_conversation_state
    for update
    to authenticated
    using (auth.uid() = user_id)
    with check (auth.uid() = user_id);
  end if;
end $$;

create index if not exists hermes_conversation_state_user_conversation_idx
on public.hermes_conversation_state(user_id, conversation_id);

create index if not exists hermes_conversation_state_expires_at_idx
on public.hermes_conversation_state(expires_at);
