create table if not exists public.research_notebooklm_automation_settings (
  settings_id text primary key,
  automation_mode text not null check (automation_mode in ('AUTO_OPERATOR_BOUNDED','MANUAL_ASSISTED','UNAVAILABLE')),
  preferred_path text not null default 'CLI' check (preferred_path in ('CLI','BROWSER_OPERATOR','MANUAL_ASSISTED')),
  enabled boolean not null default false,
  max_imported_sources_per_pass integer not null default 5 check (max_imported_sources_per_pass between 1 and 5),
  max_research_passes_per_gap integer not null default 2 check (max_research_passes_per_gap between 1 and 2),
  max_gaps_per_notebook_session integer not null default 5 check (max_gaps_per_notebook_session between 1 and 5),
  public_sources_only boolean not null default true,
  sensitive_client_data_allowed boolean not null default false,
  destructive_notebook_actions_allowed boolean not null default false,
  sharing_actions_allowed boolean not null default false,
  updated_at timestamptz not null default now()
);

insert into public.research_notebooklm_automation_settings
  (settings_id,automation_mode,preferred_path,enabled,max_imported_sources_per_pass,max_research_passes_per_gap,max_gaps_per_notebook_session,public_sources_only,sensitive_client_data_allowed,destructive_notebook_actions_allowed,sharing_actions_allowed)
values ('NOTEBOOKLM_RESEARCH','AUTO_OPERATOR_BOUNDED','CLI',true,5,2,5,true,false,false,false)
on conflict (settings_id) do update set
  automation_mode=excluded.automation_mode, preferred_path=excluded.preferred_path, enabled=excluded.enabled,
  max_imported_sources_per_pass=excluded.max_imported_sources_per_pass,
  max_research_passes_per_gap=excluded.max_research_passes_per_gap,
  max_gaps_per_notebook_session=excluded.max_gaps_per_notebook_session,
  public_sources_only=excluded.public_sources_only,sensitive_client_data_allowed=false,
  destructive_notebook_actions_allowed=false,sharing_actions_allowed=false,updated_at=now();

create table if not exists public.research_notebooklm_sessions (
  research_session_id text primary key,
  source_id text not null,
  notebook_reference text not null,
  research_method text not null check (research_method in ('NOTEBOOKLM_FAST_RESEARCH','NOTEBOOKLM_DEEP_RESEARCH')),
  automation_path text not null check (automation_path in ('CLI','BROWSER_OPERATOR','MANUAL_ASSISTED')),
  gaps_attempted jsonb not null default '[]'::jsonb,
  gaps_closed jsonb not null default '[]'::jsonb,
  gaps_remaining jsonb not null default '[]'::jsonb,
  sources_discovered jsonb not null default '[]'::jsonb,
  sources_imported jsonb not null default '[]'::jsonb,
  status text not null default 'RUNNING' check (status in ('RUNNING','COMPLETED','RESEARCH_REQUIRED','BLOCKED_BY_AUTH','FAILED_RETRYABLE')),
  started_at timestamptz not null default now(),
  completed_at timestamptz
);

alter table public.research_notebooklm_automation_settings enable row level security;
alter table public.research_notebooklm_sessions enable row level security;
drop policy if exists research_notebooklm_automation_settings_admin_all on public.research_notebooklm_automation_settings;
create policy research_notebooklm_automation_settings_admin_all on public.research_notebooklm_automation_settings
  for all to authenticated using (public.nexus_is_active_admin()) with check (public.nexus_is_active_admin());
drop policy if exists research_notebooklm_sessions_admin_all on public.research_notebooklm_sessions;
create policy research_notebooklm_sessions_admin_all on public.research_notebooklm_sessions
  for all to authenticated using (public.nexus_is_active_admin()) with check (public.nexus_is_active_admin());
