-- Nexus OS v2 — Day 8 Transcript Intake + Orientation Intelligence. ADDITIVE ONLY.
-- New tables for capturing pasted videos/transcripts/ideas and deciding what Nexus should do.
-- RLS admin-only (admin_users pattern). No anon/public policies.

create table if not exists intake_events (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid references workspaces(id),
  source_type text not null default 'manual',
  source_url text,
  title text,
  raw_text text,
  note text,
  status text not null default 'new',
  category text,
  risk_level text not null default 'medium',
  metadata jsonb not null default '{}',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists orientation_notes (
  id uuid primary key default gen_random_uuid(),
  intake_event_id uuid references intake_events(id) on delete cascade,
  workspace_id uuid references workspaces(id),
  category text not null,
  summary text not null,
  decision text not null,
  reason text,
  suggested_jobs jsonb not null default '[]',
  suggested_tables jsonb not null default '[]',
  risk_flags jsonb not null default '[]',
  metadata jsonb not null default '{}',
  created_at timestamptz not null default now()
);

create table if not exists transcript_reviews (
  id uuid primary key default gen_random_uuid(),
  intake_event_id uuid references intake_events(id) on delete set null,
  workspace_id uuid references workspaces(id),
  title text not null,
  core_idea text not null,
  category text not null,
  usefulness_score int not null default 0,
  money_now_score int not null default 0,
  automation_score int not null default 0,
  risk_score int not null default 0,
  compliance_risk text not null default 'medium',
  decision text not null,
  recommended_action text not null,
  nexus_should_do jsonb not null default '[]',
  hermes_should_say text,
  jobs_to_create jsonb not null default '[]',
  tables_to_update jsonb not null default '[]',
  memory_to_store jsonb not null default '{}',
  claim_flags jsonb not null default '[]',
  metadata jsonb not null default '{}',
  created_at timestamptz not null default now()
);

create table if not exists dispositions (
  id uuid primary key default gen_random_uuid(),
  subject_table text not null,
  subject_id uuid not null,
  disposition text not null,
  reason text,
  decided_by text not null default 'system',
  metadata jsonb not null default '{}',
  created_at timestamptz not null default now()
);

create table if not exists wagers (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid references workspaces(id),
  title text not null,
  hypothesis text not null,
  success_metric text not null,
  target_value text,
  time_window text,
  status text not null default 'open',
  result text,
  metadata jsonb not null default '{}',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists nexus_lessons (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid references workspaces(id),
  source_table text,
  source_id uuid,
  lesson text not null,
  category text,
  confidence numeric not null default 0,
  metadata jsonb not null default '{}',
  created_at timestamptz not null default now()
);

create index if not exists idx_intake_events_status on intake_events (status, created_at desc);
create index if not exists idx_transcript_reviews_category on transcript_reviews (category, created_at desc);
create index if not exists idx_orientation_notes_decision on orientation_notes (decision, created_at desc);
create index if not exists idx_dispositions_subject on dispositions (subject_table, subject_id);

-- RLS: admin SELECT only
do $$
declare t text;
begin
  foreach t in array array['intake_events','orientation_notes','transcript_reviews','dispositions','wagers','nexus_lessons'] loop
    execute format('alter table %I enable row level security', t);
    execute format('drop policy if exists %I on %I', 'admin read ' || t, t);
    execute format(
      'create policy %I on %I for select to authenticated using ('
      || 'exists (select 1 from admin_users a where a.id = auth.uid() and a.active = true))',
      'admin read ' || t, t);
  end loop;
end $$;
