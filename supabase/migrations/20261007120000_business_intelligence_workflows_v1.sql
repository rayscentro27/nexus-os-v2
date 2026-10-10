-- Business intelligence workflows v1: authoritative workflow state and durable banks.
create table if not exists public.business_intelligence_notebooks (
  notebook_type text primary key check (notebook_type in ('BUSINESS_OPPORTUNITY_FEEDER','BUSINESS_FUNDING_FEEDER','BUSINESS_CREATION_BANKABILITY')),
  notebook_id text,
  owner_department text not null,
  manager_department text not null default 'RESEARCH',
  master_prompt_version text not null default 'v1',
  master_prompt text not null default '',
  created_at timestamptz not null default now(),
  last_updated timestamptz not null default now(),
  source_count integer not null default 0,
  active_projects integer not null default 0,
  last_review timestamptz,
  status text not null default 'ACTIVE',
  notebook_reference text
);

create table if not exists public.business_intelligence_banks (
  bank_type text primary key check (bank_type in ('BUSINESS_HUB','OPPORTUNITY_BANK','OPPORTUNITY_COMPONENT_BANK','FUNDING_PRODUCT_BANK','BUSINESS_CREDIT_PRODUCT_BANK')),
  item_count integer not null default 0,
  stale_items integer not null default 0,
  last_sync timestamptz,
  last_research_run timestamptz,
  next_refresh timestamptz,
  metadata jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now()
);

create table if not exists public.business_intelligence_project_notebooks (
  notebook_id text primary key,
  notebook_type text not null,
  case_id text not null,
  owner_department text not null,
  manager_department text not null default 'RESEARCH',
  source_references jsonb not null default '[]'::jsonb,
  initial_research_packet jsonb not null default '{}'::jsonb,
  status text not null default 'ACTIVE',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.business_intelligence_records (
  id uuid primary key default gen_random_uuid(),
  record_type text not null,
  record_key text not null,
  case_id text,
  lane text check (lane is null or lane in ('CLIENT_GOCLEAR','NEXUS_INTERNAL')),
  status text not null default 'RESEARCH_REQUIRED',
  evidence_level text not null default 'RESEARCH_REQUIRED' check (evidence_level in ('VERIFIED','SOURCE_CLAIM','CROSS_SUPPORTED','CONTRADICTED','RESEARCH_REQUIRED')),
  payload jsonb not null default '{}'::jsonb,
  source_references jsonb not null default '[]'::jsonb,
  confidence text not null default 'LOW',
  next_action text not null,
  next_owner text not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique(record_type, record_key)
);

create table if not exists public.business_intelligence_handoffs (
  id uuid primary key default gen_random_uuid(),
  case_id text not null,
  handoff_type text not null,
  from_department text not null,
  next_owner text not null,
  status text not null default 'OPEN',
  packet jsonb not null,
  created_at timestamptz not null default now(),
  completed_at timestamptz
);

create index if not exists bi_records_type_updated_idx on public.business_intelligence_records(record_type, updated_at desc);
create index if not exists bi_handoffs_case_created_idx on public.business_intelligence_handoffs(case_id, created_at desc);
alter table public.business_intelligence_notebooks enable row level security;
alter table public.business_intelligence_banks enable row level security;
alter table public.business_intelligence_records enable row level security;
alter table public.business_intelligence_handoffs enable row level security;
alter table public.business_intelligence_project_notebooks enable row level security;
do $$ declare t text; begin
  foreach t in array array['business_intelligence_notebooks','business_intelligence_banks','business_intelligence_records','business_intelligence_handoffs','business_intelligence_project_notebooks'] loop
    execute format('drop policy if exists %I on public.%I', t || '_admin_all', t);
    execute format('create policy %I on public.%I for all to authenticated using (public.nexus_is_active_admin()) with check (public.nexus_is_active_admin())', t || '_admin_all', t);
    execute format('grant select, insert, update, delete on public.%I to authenticated', t);
  end loop;
end $$;

insert into public.business_intelligence_banks(bank_type) values
 ('BUSINESS_HUB'),('OPPORTUNITY_BANK'),('OPPORTUNITY_COMPONENT_BANK'),('FUNDING_PRODUCT_BANK'),('BUSINESS_CREDIT_PRODUCT_BANK')
on conflict do nothing;
