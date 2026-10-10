create table if not exists public.nexus_feeder_runtime_settings (
 settings_id text primary key check(settings_id='NEXUS_FEEDER_RUNTIME'),
 external_feeders_enabled boolean not null default true,
 ray_nova_intake_enabled boolean not null default true,
 first_pass_criteria_version text not null default 'v1',
 default_recommendation_mode text not null default 'DISCUSS_FURTHER',
 research_handoff_enabled boolean not null default true,
 max_sources_per_wake integer not null default 4 check(max_sources_per_wake between 1 and 10),
 updated_at timestamptz not null default now()
);
insert into public.nexus_feeder_runtime_settings(settings_id) values('NEXUS_FEEDER_RUNTIME') on conflict do nothing;
alter table public.nexus_feeder_runtime_settings enable row level security;
drop policy if exists nexus_feeder_runtime_settings_admin_all on public.nexus_feeder_runtime_settings;
create policy nexus_feeder_runtime_settings_admin_all on public.nexus_feeder_runtime_settings for all to authenticated using (public.nexus_is_active_admin()) with check (public.nexus_is_active_admin());
grant select,insert,update,delete on public.nexus_feeder_runtime_settings to authenticated;
notify pgrst, 'reload schema';
