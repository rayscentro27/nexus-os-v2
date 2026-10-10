create table if not exists public.nexus_feeder_templates (
  template_id text primary key,
  feeder_type text not null unique check (feeder_type in ('BUSINESS_OPPORTUNITY_FEEDER','BUSINESS_FUNDING_FEEDER','BUSINESS_CREATION_BANKABILITY_FEEDER','FOREX_INDICATOR_STRATEGY_FEEDER','OPTIONS_STRATEGY_FEEDER','RAY_NOVA_OPPORTUNITY_INTAKE')),
  version text not null,
  prompt_body text not null,
  active boolean not null default true,
  notebook_reference text,
  notebook_type text,
  notebook_owner text,
  notebook_manager text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.nexus_feeder_sources (
  source_id text primary key,
  feeder_type text not null check (feeder_type in ('BUSINESS_OPPORTUNITY_FEEDER','BUSINESS_FUNDING_FEEDER','BUSINESS_CREATION_BANKABILITY_FEEDER','FOREX_INDICATOR_STRATEGY_FEEDER','OPTIONS_STRATEGY_FEEDER','RAY_NOVA_OPPORTUNITY_INTAKE')),
  source_type text not null,
  source_title text not null,
  source_url text,
  source_creator text,
  source_date timestamptz,
  transcript_or_extract text,
  notebook_reference text,
  notebook_type text,
  notebook_owner text,
  notebook_manager text,
  notebook_output jsonb not null default '{}'::jsonb,
  structured_input jsonb not null default '{}'::jsonb,
  content_hash text,
  ingestion_status text not null default 'NEW' check (ingestion_status in ('WAITING_FOR_SOURCE','NEW','DETECTED','READY_FOR_QUESTIONNAIRE','QUESTIONNAIRE_RUNNING','QUESTIONNAIRE_COMPLETE','RESEARCH_REQUIRED','RESEARCH_IN_PROGRESS','READY_FOR_HANDOFF','HANDED_OFF','BLOCKED','FAILED_RETRYABLE')),
  block_reason text,
  next_owner text not null default 'FEEDER_INTAKE_WORKER',
  route_department text,
  case_id text,
  ray_opportunity_id text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create unique index if not exists nexus_feeder_source_url_uq on public.nexus_feeder_sources(feeder_type, lower(source_url)) where source_url is not null;
create unique index if not exists nexus_feeder_content_hash_uq on public.nexus_feeder_sources(feeder_type, content_hash) where content_hash is not null;

create table if not exists public.nexus_feeder_questionnaire_runs (
  run_id text primary key,
  source_id text not null references public.nexus_feeder_sources(source_id),
  feeder_type text not null,
  questionnaire_version text not null,
  started_at timestamptz not null,
  completed_at timestamptz,
  status text not null check (status in ('QUESTIONNAIRE_RUNNING','QUESTIONNAIRE_COMPLETE','BLOCKED','FAILED_RETRYABLE')),
  structured_fields jsonb not null default '{}'::jsonb,
  source_claims jsonb not null default '[]'::jsonb,
  verified_fields jsonb not null default '[]'::jsonb,
  contradictions jsonb not null default '[]'::jsonb,
  research_gaps jsonb not null default '[]'::jsonb,
  exact_research_questions jsonb not null default '[]'::jsonb,
  recommended_next_action text,
  next_owner text,
  error_code text
);

create table if not exists public.nexus_feeder_research_gaps (
  question_id text primary key,
  source_id text not null references public.nexus_feeder_sources(source_id),
  question text not null,
  why_it_matters text not null,
  return_to text not null,
  status text not null default 'OPEN' check (status in ('OPEN','IN_PROGRESS','COMPLETED','BLOCKED_EXTERNAL','BLOCKED_AUTH','FAILED_RETRYABLE')),
  research_request_id text,
  answer_packet jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.nexus_feeder_handoffs (
  handoff_id text primary key,
  source_id text references public.nexus_feeder_sources(source_id),
  opportunity_id text,
  case_id text not null,
  from_department text not null,
  to_department text not null,
  summary text not null,
  structured_data jsonb not null default '{}'::jsonb,
  what_was_completed jsonb not null default '[]'::jsonb,
  what_remains jsonb not null default '[]'::jsonb,
  recommendation text not null,
  action text not null,
  expected_output text not null,
  status text not null default 'CREATED' check (status in ('CREATED','CLAIMED','IN_PROGRESS','COMPLETED','BLOCKED','FAILED_RETRYABLE')),
  claimed_by text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.nexus_feeder_batch_slots (
  batch_slot_id text primary key,
  batch_name text not null,
  feeder_type text not null,
  slot_number integer not null,
  source_reference text,
  source_id text references public.nexus_feeder_sources(source_id),
  status text not null default 'WAITING_FOR_SOURCE' check (status in ('WAITING_FOR_SOURCE','NEW','DETECTED','READY_FOR_QUESTIONNAIRE','QUESTIONNAIRE_RUNNING','QUESTIONNAIRE_COMPLETE','RESEARCH_REQUIRED','RESEARCH_IN_PROGRESS','READY_FOR_HANDOFF','HANDED_OFF','BLOCKED','FAILED_RETRYABLE')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique(batch_name, feeder_type, slot_number)
);

create table if not exists public.nexus_ray_nova_opportunities (
  opportunity_id text primary key,
  source_id text not null unique references public.nexus_feeder_sources(source_id),
  opportunity_name text not null,
  idea_summary text not null,
  structured_analysis jsonb not null default '{}'::jsonb,
  conversational_response jsonb not null default '{}'::jsonb,
  ray_action text check (ray_action is null or ray_action in ('DISCUSS_FURTHER','SEND_TO_RESEARCH','SAVE_FOR_LATER')),
  status text not null default 'RAY_INTAKE_REVIEW' check (status in ('RAY_INTAKE_REVIEW','DISCUSSING','SENT_TO_RESEARCH','SAVED_BY_RAY','IN_ATLAS_WORKFLOW')),
  research_handoff_id text,
  atlas_opportunity_id text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.nexus_feeder_system_registry (
  component_id text primary key,
  component_group text not null,
  enabled boolean not null default true,
  status text not null default 'NOT_CONFIGURED' check (status in ('PASS','DEGRADED','FAIL','UNREACHABLE','BLOCKED_BY_AUTH','NOT_CONFIGURED','CHECK_ERROR','STALE','QUEUE_BACKLOG','HANDOFF_STALLED','RESEARCH_STALLED','DOWNSTREAM_STALLED','IDLE_HEALTHY')),
  next_workflow text not null,
  last_activity timestamptz,
  oldest_queued_age_seconds bigint not null default 0,
  queued_count integer not null default 0,
  processing_count integer not null default 0,
  research_required_count integer not null default 0,
  handed_off_count integer not null default 0,
  blocked_count integer not null default 0,
  failed_count integer not null default 0,
  unclaimed_handoff_count integer not null default 0,
  evidence jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now()
);
create table if not exists public.nexus_feeder_runtime_heartbeats (
  worker_id text primary key,
  worker_type text not null,
  status text not null,
  last_heartbeat timestamptz not null default now(),
  receipt jsonb not null default '{}'::jsonb
);

do $$ declare t text; begin
 foreach t in array array['nexus_feeder_templates','nexus_feeder_sources','nexus_feeder_questionnaire_runs','nexus_feeder_research_gaps','nexus_feeder_handoffs','nexus_feeder_batch_slots','nexus_ray_nova_opportunities','nexus_feeder_system_registry','nexus_feeder_runtime_heartbeats'] loop
  execute format('alter table public.%I enable row level security',t);
  execute format('drop policy if exists %I on public.%I',t||'_admin_all',t);
  execute format('create policy %I on public.%I for all to authenticated using (public.nexus_is_active_admin()) with check (public.nexus_is_active_admin())',t||'_admin_all',t);
  execute format('grant select, insert, update, delete on public.%I to authenticated',t);
 end loop;
end $$;
