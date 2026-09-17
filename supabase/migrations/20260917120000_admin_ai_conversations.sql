begin;

-- Canonical Admin AI Command history. This is deliberately separate from the
-- client portal AI tables and stores only authenticated Admin conversations.
create table if not exists public.admin_ai_conversations (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  agent text not null default 'nova' check (agent in ('nova', 'hermes', 'alpha')),
  title text not null default 'New conversation' check (char_length(title) <= 120),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.admin_ai_messages (
  id uuid primary key default gen_random_uuid(),
  conversation_id uuid not null references public.admin_ai_conversations(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  role text not null check (role in ('user', 'assistant', 'error')),
  content text not null check (char_length(content) <= 12000),
  created_at timestamptz not null default now()
);

create index if not exists admin_ai_conversations_owner_activity_idx
  on public.admin_ai_conversations(user_id, updated_at desc);
create index if not exists admin_ai_messages_conversation_created_idx
  on public.admin_ai_messages(conversation_id, created_at asc);

alter table public.admin_ai_conversations enable row level security;
alter table public.admin_ai_messages enable row level security;

grant select, insert, update on public.admin_ai_conversations to authenticated;
grant select, insert on public.admin_ai_messages to authenticated;

drop policy if exists admin_ai_conversations_owner_read on public.admin_ai_conversations;
create policy admin_ai_conversations_owner_read on public.admin_ai_conversations
  for select to authenticated using (public.nexus_is_active_admin() or user_id = auth.uid());
drop policy if exists admin_ai_conversations_owner_insert on public.admin_ai_conversations;
create policy admin_ai_conversations_owner_insert on public.admin_ai_conversations
  for insert to authenticated with check (user_id = auth.uid());
drop policy if exists admin_ai_conversations_owner_update on public.admin_ai_conversations;
create policy admin_ai_conversations_owner_update on public.admin_ai_conversations
  for update to authenticated using (public.nexus_is_active_admin() or user_id = auth.uid())
  with check (public.nexus_is_active_admin() or user_id = auth.uid());

drop policy if exists admin_ai_messages_owner_read on public.admin_ai_messages;
create policy admin_ai_messages_owner_read on public.admin_ai_messages
  for select to authenticated using (
    public.nexus_is_active_admin() or user_id = auth.uid()
  );
drop policy if exists admin_ai_messages_owner_insert on public.admin_ai_messages;
create policy admin_ai_messages_owner_insert on public.admin_ai_messages
  for insert to authenticated with check (user_id = auth.uid());

commit;
