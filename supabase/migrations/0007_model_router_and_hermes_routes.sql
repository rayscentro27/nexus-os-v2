-- Nexus OS v2 — Day 7 policy-gated Model Router. ADDITIVE ONLY.
-- Extends the existing model_routes (from 0003) and adds model_route_decisions +
-- hermes_model_requests. RLS admin-only (admin_users pattern). No anon/public policies.

-- ── extend model_routes ──
alter table model_routes add column if not exists provider_key          text;
alter table model_routes add column if not exists model_key             text;
alter table model_routes add column if not exists route_type            text not null default 'deterministic'; -- deterministic|manual|local_private|free_public_cloud|premium_cloud|blocked
alter table model_routes add column if not exists active                boolean not null default true;
alter table model_routes add column if not exists public_research_allowed boolean not null default false;
alter table model_routes add column if not exists client_data_allowed   boolean not null default false;
alter table model_routes add column if not exists credit_data_allowed   boolean not null default false;
alter table model_routes add column if not exists funding_data_allowed  boolean not null default false;
alter table model_routes add column if not exists trading_data_allowed  boolean not null default false;
alter table model_routes add column if not exists external_call_allowed boolean not null default false;
alter table model_routes add column if not exists requires_approval     boolean not null default true;
alter table model_routes add column if not exists cost_tier             text not null default 'unknown';
alter table model_routes add column if not exists daily_budget_cents    int;
alter table model_routes add column if not exists monthly_budget_cents  int;
alter table model_routes add column if not exists max_input_tokens      int;
alter table model_routes add column if not exists max_output_tokens     int;
alter table model_routes add column if not exists priority              int not null default 100;
alter table model_routes add column if not exists notes                 text;
alter table model_routes add column if not exists updated_at            timestamptz not null default now();

-- ── model_route_decisions ──
create table if not exists model_route_decisions (
  id uuid primary key default gen_random_uuid(),
  agent_key text not null,
  task_type text not null,
  sensitivity text not null,
  selected_route_key text,
  decision text not null,                 -- selected | blocked | approval_required | external_disabled
  reason text not null,
  requires_approval boolean not null default false,
  approval_id uuid references approvals(id),
  job_id uuid references agent_jobs(id),
  metadata jsonb not null default '{}',
  created_at timestamptz not null default now()
);

-- ── hermes_model_requests ──
create table if not exists hermes_model_requests (
  id uuid primary key default gen_random_uuid(),
  conversation_id uuid,
  agent_key text not null default 'hermes_advisor',
  prompt_summary text not null,
  task_type text not null,
  sensitivity text not null,
  selected_route_key text,
  status text not null default 'draft',   -- draft | routed | blocked | needs_approval | manual_packet
  dry_run boolean not null default true,
  request_payload jsonb not null default '{}',
  response_summary text,
  blocked_reason text,
  metadata jsonb not null default '{}',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_route_decisions_created on model_route_decisions (created_at desc);
create index if not exists idx_hermes_requests_created on hermes_model_requests (created_at desc);

-- ── RLS: admin SELECT only ──
do $$
declare t text;
begin
  foreach t in array array['model_route_decisions','hermes_model_requests'] loop
    execute format('alter table %I enable row level security', t);
    execute format('drop policy if exists %I on %I', 'admin read ' || t, t);
    execute format(
      'create policy %I on %I for select to authenticated using ('
      || 'exists (select 1 from admin_users a where a.id = auth.uid() and a.active = true))',
      'admin read ' || t, t);
  end loop;
end $$;
