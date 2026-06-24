-- Nexus OS v2 — Day 11 Hermes task_requests. ADDITIVE ONLY.
-- Structured, Ray-approved requests that Hermes may CREATE but never EXECUTE. Each row is
-- sensitivity-labeled and assigned to a worker; Hermes only gets status_only/summary visibility.
-- This is distinct from agent_jobs (which is for execution). RLS admin-only (admin_users
-- pattern). No anon/public policies. No secrets stored here.

create table if not exists task_requests (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid references workspaces(id),
  task_type text not null,
  requested_by text not null default 'hermes',
  approved_by_ray text,
  sensitivity text not null default 'public',          -- public | internal_summary | customer_private | credit_sensitive | funding_sensitive | auth_sensitive | secrets | trading_sensitive
  allowed_data_scope jsonb not null default '[]',      -- scopes the assigned worker may read
  forbidden_data jsonb not null default '[]',          -- data the worker (and Hermes) must never read
  assigned_worker_type text not null default 'general_worker',  -- private_auth_worker / private_publish_worker / etc.
  hermes_visibility text not null default 'status_only',         -- status_only | summary
  status text not null default 'requested',            -- requested | assigned | in_progress | done | rejected
  payload jsonb not null default '{}',
  result_summary text,                                 -- redacted status/result a worker returns to Hermes
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_task_requests_status on task_requests (status, created_at desc);
create index if not exists idx_task_requests_worker on task_requests (assigned_worker_type, status);
create index if not exists idx_task_requests_sensitivity on task_requests (sensitivity, created_at desc);

-- RLS: admin-only read/insert/update (matches the existing admin_users gate on core tables).
do $$
declare t text;
begin
  foreach t in array array['task_requests'] loop
    execute format('alter table %I enable row level security', t);
    execute format('drop policy if exists %I on %I', 'admin read ' || t, t);
    execute format(
      'create policy %I on %I for select to authenticated using ('
      || 'exists (select 1 from admin_users a where a.id = auth.uid() and a.active = true))',
      'admin read ' || t, t);
    execute format('drop policy if exists %I on %I', 'admin insert ' || t, t);
    execute format(
      'create policy %I on %I for insert to authenticated with check ('
      || 'exists (select 1 from admin_users a where a.id = auth.uid() and a.active = true))',
      'admin insert ' || t, t);
    execute format('drop policy if exists %I on %I', 'admin update ' || t, t);
    execute format(
      'create policy %I on %I for update to authenticated using ('
      || 'exists (select 1 from admin_users a where a.id = auth.uid() and a.active = true))',
      'admin update ' || t, t);
  end loop;
end $$;
