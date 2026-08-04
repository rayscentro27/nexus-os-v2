-- Authoritative Nexus process/run registry.
-- Additive only: no existing operational, client, or auth data is modified.

create extension if not exists pgcrypto;

create table if not exists public.nexus_process_definitions (
  id uuid primary key default gen_random_uuid(),
  process_key text not null unique,
  name text not null,
  description text,
  system text not null default 'nexus',
  entry_point text,
  trigger_type text not null default 'manual',
  schedule text,
  enabled boolean not null default false,
  execution_mode text not null default 'manual',
  owner text,
  approval_policy text not null default 'none',
  max_runtime_seconds integer,
  max_items integer,
  max_retries integer,
  cost_limit numeric,
  is_mock boolean not null default false,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.nexus_process_runs (
  id uuid primary key default gen_random_uuid(),
  process_id uuid not null references public.nexus_process_definitions(id) on delete restrict,
  idempotency_key text unique,
  status text not null check (status in ('QUEUED','RUNNING','SUCCEEDED','PARTIAL','FAILED','BLOCKED','CANCELLED','TIMED_OUT','SIMULATED','UNKNOWN')),
  started_at timestamptz,
  completed_at timestamptz,
  heartbeat_at timestamptz,
  items_attempted integer not null default 0,
  items_succeeded integer not null default 0,
  items_failed integer not null default 0,
  output_location text,
  error_code text,
  error_message text,
  triggered_by text,
  approval_id text,
  trace_id text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists public.nexus_provider_probes (
  id uuid primary key default gen_random_uuid(),
  provider_key text not null,
  configured boolean not null default false,
  reachable boolean,
  authenticated boolean,
  supported_model text,
  selected_model text,
  last_successful_probe timestamptz,
  latency_ms integer,
  failure_reason text,
  cost_mode text,
  daily_limit numeric,
  request_limit numeric,
  metadata jsonb not null default '{}'::jsonb,
  checked_at timestamptz not null default now()
);

create table if not exists public.nexus_research_runs (
  id uuid primary key default gen_random_uuid(),
  process_run_id uuid references public.nexus_process_runs(id) on delete set null,
  script_path text not null,
  category text not null default 'general',
  source_type text,
  query_input text,
  output_destination text,
  status text not null default 'UNKNOWN',
  items_retrieved integer not null default 0,
  items_accepted integer not null default 0,
  items_rejected integer not null default 0,
  rejection_summary jsonb not null default '{}'::jsonb,
  metadata jsonb not null default '{}'::jsonb,
  started_at timestamptz,
  completed_at timestamptz,
  created_at timestamptz not null default now()
);

create table if not exists public.nexus_research_results (
  id uuid primary key default gen_random_uuid(),
  research_run_id uuid references public.nexus_research_runs(id) on delete cascade,
  category text not null,
  title text not null,
  summary text,
  claim text,
  source_url text,
  source_name text,
  published_at timestamptz,
  retrieved_at timestamptz not null default now(),
  confidence numeric,
  score numeric,
  duplicate_key text,
  status text not null default 'collected',
  approval_state text not null default 'not_reviewed',
  downstream_destination text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists nexus_process_runs_process_status_idx on public.nexus_process_runs(process_id, status, started_at desc);
create index if not exists nexus_process_runs_created_idx on public.nexus_process_runs(created_at desc);
create index if not exists nexus_research_results_duplicate_idx on public.nexus_research_results(duplicate_key) where duplicate_key is not null;
create index if not exists nexus_research_results_category_idx on public.nexus_research_results(category, approval_state, retrieved_at desc);

alter table public.nexus_process_definitions enable row level security;
alter table public.nexus_process_runs enable row level security;
alter table public.nexus_provider_probes enable row level security;
alter table public.nexus_research_runs enable row level security;
alter table public.nexus_research_results enable row level security;

grant select, insert, update on public.nexus_process_definitions to authenticated;
grant select, insert, update on public.nexus_process_runs to authenticated;
grant select, insert, update on public.nexus_provider_probes to authenticated;
grant select, insert, update on public.nexus_research_runs to authenticated;
grant select, insert, update on public.nexus_research_results to authenticated;

drop policy if exists nexus_process_definitions_admin_all on public.nexus_process_definitions;
create policy nexus_process_definitions_admin_all on public.nexus_process_definitions
  for all to authenticated
  using (public.nexus_is_active_admin())
  with check (public.nexus_is_active_admin());

drop policy if exists nexus_process_runs_admin_all on public.nexus_process_runs;
create policy nexus_process_runs_admin_all on public.nexus_process_runs
  for all to authenticated
  using (public.nexus_is_active_admin())
  with check (public.nexus_is_active_admin());

drop policy if exists nexus_provider_probes_admin_all on public.nexus_provider_probes;
create policy nexus_provider_probes_admin_all on public.nexus_provider_probes
  for all to authenticated
  using (public.nexus_is_active_admin())
  with check (public.nexus_is_active_admin());

drop policy if exists nexus_research_runs_admin_all on public.nexus_research_runs;
create policy nexus_research_runs_admin_all on public.nexus_research_runs
  for all to authenticated
  using (public.nexus_is_active_admin())
  with check (public.nexus_is_active_admin());

drop policy if exists nexus_research_results_admin_all on public.nexus_research_results;
create policy nexus_research_results_admin_all on public.nexus_research_results
  for all to authenticated
  using (public.nexus_is_active_admin())
  with check (public.nexus_is_active_admin());
