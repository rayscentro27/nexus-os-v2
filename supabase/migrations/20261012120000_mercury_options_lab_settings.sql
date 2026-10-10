create table if not exists public.options_strategy_lab_settings (
  settings_id text primary key default 'MERCURY_OPTIONS_STRATEGY_LAB' check(settings_id='MERCURY_OPTIONS_STRATEGY_LAB'),
  enabled boolean not null default true,
  live_trading_enabled boolean not null default false check(live_trading_enabled=false),
  autonomous_material_loop_limit integer not null default 2 check(autonomous_material_loop_limit=2),
  practice_limits jsonb not null default '{"max_candidates_per_cycle":6,"max_parameter_variants":2,"max_total_practice_runs":6,"max_runtime_seconds":1200,"max_compute_cost_usd":0,"requires_historical_option_chain":true,"source_claims_are_unverified":true}'::jsonb,
  updated_at timestamptz not null default now()
);
insert into public.options_strategy_lab_settings(settings_id) values('MERCURY_OPTIONS_STRATEGY_LAB') on conflict do nothing;
alter table public.options_strategy_lab_settings enable row level security;
drop policy if exists options_strategy_lab_settings_admin_all on public.options_strategy_lab_settings;
create policy options_strategy_lab_settings_admin_all on public.options_strategy_lab_settings for all to authenticated using (public.nexus_is_active_admin()) with check (public.nexus_is_active_admin());
notify pgrst, 'reload schema';
