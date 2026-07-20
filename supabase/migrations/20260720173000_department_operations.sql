-- Nexus OS 3.0 Wave 4 — Department Operations and Governed Automation.
-- ADDITIVE ONLY. Admin-only internal department operating tables.
-- No anon/public policies. No client PII is required for department queues.

create extension if not exists "pgcrypto";

create table if not exists public.nexus_departments (
  department_id text primary key,
  name text not null,
  description text not null,
  owner_role text not null,
  executive_coordinator text not null default 'hermes',
  default_operation_mode text not null check (default_operation_mode in ('READ_ONLY','ADVISORY','DRAFT_ONLY','APPROVAL_GATED','BOUNDED_EXECUTION')),
  allowed_capability_ids jsonb not null default '[]',
  prohibited_capability_ids jsonb not null default '[]',
  allowed_data_classes jsonb not null default '[]',
  prohibited_data_classes jsonb not null default '[]',
  intake_sources jsonb not null default '[]',
  escalation_targets jsonb not null default '[]',
  service_level_policy jsonb not null default '{}',
  health_source text not null,
  status text not null default 'ACTIVE' check (status in ('ACTIVE','DEGRADED','PAUSED','NOT_CONFIGURED')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.department_queue_items (
  item_id text primary key,
  department_id text not null references public.nexus_departments(department_id),
  title text not null,
  summary text not null,
  source_type text not null,
  source_id text,
  priority text not null check (priority in ('P0_COMPANY','P1_CUSTOMER','P2_REVENUE','P3_OPERATIONS','P4_RESEARCH')),
  urgency text not null check (urgency in ('CRITICAL','HIGH','MEDIUM','LOW')),
  risk_level text not null check (risk_level in ('CRITICAL','HIGH','MEDIUM','LOW')),
  operation_mode text not null check (operation_mode in ('READ_ONLY','ADVISORY','DRAFT_ONLY','APPROVAL_GATED','BOUNDED_EXECUTION')),
  status text not null check (status in ('NEW','TRIAGED','PLANNED','AWAITING_APPROVAL','READY','IN_PROGRESS','BLOCKED','VERIFYING','COMPLETE','CANCELLED','ESCALATED')),
  owner_role text,
  assigned_actor_id text,
  capability_ids jsonb not null default '[]',
  dependency_ids jsonb not null default '[]',
  blocker_ids jsonb not null default '[]',
  requires_approval boolean not null default false,
  approval_id uuid references public.approvals(id),
  evidence_ids jsonb not null default '[]',
  completion_criteria jsonb not null default '[]',
  synthetic boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  due_at timestamptz
);

create table if not exists public.department_blockers (
  blocker_id text primary key,
  department_id text not null references public.nexus_departments(department_id),
  title text not null,
  description text not null,
  blocker_type text not null check (blocker_type in ('DEPENDENCY','APPROVAL','CREDENTIAL','POLICY','DATA','SYSTEM_HEALTH','EXTERNAL_SERVICE','HUMAN_DECISION','UNKNOWN')),
  severity text not null check (severity in ('CRITICAL','HIGH','MEDIUM','LOW')),
  status text not null default 'OPEN' check (status in ('OPEN','MITIGATED','RESOLVED','ACCEPTED')),
  affected_item_ids jsonb not null default '[]',
  owner_role text,
  mitigation text,
  evidence_ids jsonb not null default '[]',
  created_at timestamptz not null default now(),
  resolved_at timestamptz
);

create table if not exists public.department_incidents (
  incident_id text primary key,
  department_id text not null references public.nexus_departments(department_id),
  title text not null,
  status text not null check (status in ('DETECTED','TRIAGED','CONTAINED','REPAIR_PLANNED','AWAITING_APPROVAL','REPAIRING','VERIFYING','RESOLVED','POSTMORTEM_REQUIRED','CLOSED')),
  impact text not null,
  affected_systems jsonb not null default '[]',
  current_state text not null,
  containment text not null,
  owner_role text not null,
  next_action text not null,
  evidence_ids jsonb not null default '[]',
  verification text not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.department_work_verifications (
  verification_id text primary key,
  queue_item_id text not null references public.department_queue_items(item_id),
  criteria_results jsonb not null default '[]',
  verified_by text not null,
  verified_at timestamptz not null default now(),
  result text not null check (result in ('PASS','FAIL','PARTIAL')),
  notes text
);

create table if not exists public.governed_execution_plans (
  execution_id text primary key,
  queue_item_id text not null references public.department_queue_items(item_id),
  capability_id text not null,
  operation_mode text not null default 'BOUNDED_EXECUTION' check (operation_mode = 'BOUNDED_EXECUTION'),
  approved_scope jsonb not null default '[]',
  prohibited_scope jsonb not null default '[]',
  maximum_operations int not null default 1,
  time_limit_minutes int not null default 10,
  cost_limit numeric,
  preconditions jsonb not null default '[]',
  completion_criteria jsonb not null default '[]',
  rollback_plan jsonb not null default '[]',
  approval_id uuid references public.approvals(id),
  approved_by text not null,
  approved_at timestamptz not null,
  status text not null check (status in ('READY','RUNNING','PAUSED','COMPLETE','FAILED','ROLLED_BACK','EXPIRED')),
  evidence_ids jsonb not null default '[]',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_department_queue_department_status on public.department_queue_items(department_id, status, priority, created_at desc);
create index if not exists idx_department_queue_approval on public.department_queue_items(requires_approval, status);
create index if not exists idx_department_blockers_department_status on public.department_blockers(department_id, status, severity);
create index if not exists idx_department_incidents_department_status on public.department_incidents(department_id, status, created_at desc);

alter table public.nexus_departments enable row level security;
alter table public.department_queue_items enable row level security;
alter table public.department_blockers enable row level security;
alter table public.department_incidents enable row level security;
alter table public.department_work_verifications enable row level security;
alter table public.governed_execution_plans enable row level security;

-- Admin-only RLS. Clients, anonymous users, and Alpha have no direct table policies.
do $$
declare t text;
begin
  foreach t in array array['nexus_departments','department_queue_items','department_blockers','department_incidents','department_work_verifications','governed_execution_plans'] loop
    execute format('alter table public.%I enable row level security', t);
    execute format('drop policy if exists %I on public.%I', 'admin_select_' || t, t);
    execute format('create policy %I on public.%I for select to authenticated using (exists (select 1 from public.admin_users a where a.id = auth.uid() and a.active = true))', 'admin_select_' || t, t);
    execute format('drop policy if exists %I on public.%I', 'admin_insert_' || t, t);
    execute format('create policy %I on public.%I for insert to authenticated with check (exists (select 1 from public.admin_users a where a.id = auth.uid() and a.active = true))', 'admin_insert_' || t, t);
    execute format('drop policy if exists %I on public.%I', 'admin_update_' || t, t);
    execute format('create policy %I on public.%I for update to authenticated using (exists (select 1 from public.admin_users a where a.id = auth.uid() and a.active = true)) with check (exists (select 1 from public.admin_users a where a.id = auth.uid() and a.active = true))', 'admin_update_' || t, t);
  end loop;
end $$;
