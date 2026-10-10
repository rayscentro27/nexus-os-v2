-- Durable metadata for proactive Research query, objective, and novelty state.
-- This is a state ledger; work remains in the existing Research queue.
create table if not exists public.research_proactive_memory (
  memory_id text primary key,
  memory_kind text not null,
  objective_id text,
  query_family text,
  recorded_at timestamptz not null default now(),
  payload jsonb not null default '{}'::jsonb
);

create index if not exists research_proactive_memory_kind_recorded_idx
  on public.research_proactive_memory(memory_kind, recorded_at desc);
create index if not exists research_proactive_memory_objective_idx
  on public.research_proactive_memory(objective_id, recorded_at desc);
create index if not exists research_proactive_memory_family_idx
  on public.research_proactive_memory(query_family, recorded_at desc);

alter table public.research_proactive_memory enable row level security;
drop policy if exists research_proactive_memory_admin_all on public.research_proactive_memory;
create policy research_proactive_memory_admin_all on public.research_proactive_memory
  for all to authenticated using (public.nexus_is_active_admin())
  with check (public.nexus_is_active_admin());
grant select, insert, update on public.research_proactive_memory to authenticated;
