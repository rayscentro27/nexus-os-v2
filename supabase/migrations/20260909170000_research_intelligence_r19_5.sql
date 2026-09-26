-- R19.5: additive Research intelligence contracts. Existing source/run/result
-- and opportunity tables remain canonical; these tables bind their missing
-- question, finding, handoff, heartbeat, and capability edges.

create table if not exists public.research_questions (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid,
  question text not null,
  requester text,
  parent_goal_id text,
  department text,
  business_decision_supported text,
  priority integer not null default 50,
  status text not null default 'OPEN',
  sources_reviewed jsonb not null default '[]'::jsonb,
  current_findings jsonb not null default '[]'::jsonb,
  answer text,
  confidence numeric,
  next_action text,
  created_at timestamptz not null default now(),
  last_worked_at timestamptz,
  updated_at timestamptz not null default now()
);

create table if not exists public.research_claims (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid,
  source_id uuid references public.research_sources(id) on delete set null,
  question_id uuid references public.research_questions(id) on delete set null,
  claim text not null,
  evidence text,
  support_status text not null default 'UNKNOWN',
  confidence numeric,
  freshness_at timestamptz,
  cross_checked boolean not null default false,
  contradiction_of uuid references public.research_claims(id) on delete set null,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists public.research_findings (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid,
  question_id uuid references public.research_questions(id) on delete set null,
  finding text not null,
  evidence_ids uuid[] not null default '{}',
  confidence numeric,
  commercial_relevance numeric,
  actionability numeric,
  risk text,
  alpha_decision text not null default 'PENDING',
  recommendation text,
  next_action text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.research_handoffs (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid,
  finding_id uuid references public.research_findings(id) on delete set null,
  question_id uuid references public.research_questions(id) on delete set null,
  target_department text not null,
  parent_goal_id text,
  source_evidence jsonb not null default '[]'::jsonb,
  requested_action text not null,
  status text not null default 'QUEUED',
  receiving_work_order_id text,
  action_receipt jsonb,
  created_at timestamptz not null default now(),
  completed_at timestamptz
);

create table if not exists public.research_discovery_runs (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid,
  lane text not null,
  trigger text not null,
  question_id uuid references public.research_questions(id) on delete set null,
  sources_discovered integer not null default 0,
  sources_processed integer not null default 0,
  claims_created integer not null default 0,
  findings_created integer not null default 0,
  opportunities_created integer not null default 0,
  handoffs_created integer not null default 0,
  status text not null default 'STARTED',
  started_at timestamptz not null default now(),
  completed_at timestamptz,
  metadata jsonb not null default '{}'::jsonb
);

create table if not exists public.research_heartbeat_telemetry (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid,
  lane text not null,
  window_start timestamptz not null,
  window_end timestamptz not null,
  sources_registered integer not null default 0,
  sources_processed integer not null default 0,
  claims_extracted integer not null default 0,
  supported_claims integer not null default 0,
  cross_checked_claims integer not null default 0,
  contradictions_found integer not null default 0,
  handoffs_created integer not null default 0,
  department_actions integer not null default 0,
  created_at timestamptz not null default now(),
  unique (tenant_id, lane, window_start, window_end)
);

create table if not exists public.research_capability_intelligence (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid,
  capability_id text not null,
  name text not null,
  owner text,
  provider text,
  version_discovered text,
  version_last_verified text,
  status text not null default 'UNKNOWN',
  execution_host text,
  interface text,
  what_it_can_do text,
  what_it_cannot_do text,
  auth_required boolean not null default false,
  human_boundary text,
  safe_autonomous_use text,
  last_real_proof timestamptz,
  proof_receipt text,
  replaces_capability text,
  deprecates_workaround text,
  departments_using jsonb not null default '[]'::jsonb,
  next_reverify timestamptz,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (tenant_id, capability_id)
);

create index if not exists research_questions_status_idx on public.research_questions(status, priority desc, last_worked_at);
create index if not exists research_claims_source_idx on public.research_claims(source_id, created_at desc);
create index if not exists research_findings_alpha_idx on public.research_findings(alpha_decision, created_at desc);
create index if not exists research_handoffs_status_idx on public.research_handoffs(status, created_at);
create index if not exists research_discovery_runs_lane_idx on public.research_discovery_runs(lane, started_at desc);

alter table public.research_questions enable row level security;
alter table public.research_claims enable row level security;
alter table public.research_findings enable row level security;
alter table public.research_handoffs enable row level security;
alter table public.research_discovery_runs enable row level security;
alter table public.research_heartbeat_telemetry enable row level security;
alter table public.research_capability_intelligence enable row level security;

do $$
declare t text;
begin
  foreach t in array array['research_questions','research_claims','research_findings','research_handoffs','research_discovery_runs','research_heartbeat_telemetry','research_capability_intelligence'] loop
    execute format('drop policy if exists %I_admin_all on public.%I', t, t);
    execute format('create policy %I_admin_all on public.%I for all to authenticated using (public.nexus_is_active_admin()) with check (public.nexus_is_active_admin())', t, t);
  end loop;
end $$;

grant select, insert, update on public.research_questions to authenticated;
grant select, insert, update on public.research_claims to authenticated;
grant select, insert, update on public.research_findings to authenticated;
grant select, insert, update on public.research_handoffs to authenticated;
grant select, insert, update on public.research_discovery_runs to authenticated;
grant select, insert, update on public.research_heartbeat_telemetry to authenticated;
grant select, insert, update on public.research_capability_intelligence to authenticated;
