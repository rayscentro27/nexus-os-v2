-- Nexus OS v2 — Day 6 AI agent permission boundaries. ADDITIVE ONLY.
-- Extends agent_registry with an explicit permission model and adds an approved_knowledge
-- table for controlled client-facing agents. RLS stays admin-only; no anon/public policies.

-- ── agent_registry permission columns ──
alter table agent_registry add column if not exists audience_type         text not null default 'internal';   -- client | ray_private | internal | system
alter table agent_registry add column if not exists agent_class           text not null default 'worker';      -- client_agent | internal_worker | hermes_advisor | runner | admin_control
alter table agent_registry add column if not exists allowed_data_sources  jsonb not null default '[]';
alter table agent_registry add column if not exists web_access_allowed     boolean not null default false;
alter table agent_registry add column if not exists external_api_allowed   boolean not null default false;
alter table agent_registry add column if not exists can_create_jobs        boolean not null default false;
alter table agent_registry add column if not exists can_create_approvals   boolean not null default false;
alter table agent_registry add column if not exists can_execute_actions    boolean not null default false;
alter table agent_registry add column if not exists requires_approval_for  jsonb not null default '[]';
alter table agent_registry add column if not exists cost_policy            text not null default 'controlled';
alter table agent_registry add column if not exists compliance_policy      text not null default 'default';
alter table agent_registry add column if not exists communication_channel  text not null default 'dashboard';
alter table agent_registry add column if not exists risk_level             text not null default 'medium';
alter table agent_registry add column if not exists system_prompt_summary  text;
alter table agent_registry add column if not exists active                 boolean not null default true;

-- ── approved_knowledge — the ONLY answer source for client-facing agents ──
create table if not exists approved_knowledge (
  id              uuid primary key default gen_random_uuid(),
  workspace_id    uuid references workspaces(id),
  knowledge_key   text unique not null,
  title           text not null,
  body            text not null,
  category        text,
  audience_type   text not null default 'client',
  compliance_notes text,
  status          text not null default 'approved',
  created_at      timestamptz not null default now()
);
alter table approved_knowledge enable row level security;
drop policy if exists "admin read approved_knowledge" on approved_knowledge;
create policy "admin read approved_knowledge" on approved_knowledge
  for select to authenticated
  using (exists (select 1 from admin_users a where a.id = auth.uid() and a.active = true));

create index if not exists idx_approved_knowledge_category on approved_knowledge (category, status);
