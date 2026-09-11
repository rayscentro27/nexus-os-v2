begin;
alter table public.client_ai_conversations add column if not exists session_id text;
create index if not exists client_ai_conversations_session_idx on public.client_ai_conversations(user_id, session_id, created_at desc);
commit;
