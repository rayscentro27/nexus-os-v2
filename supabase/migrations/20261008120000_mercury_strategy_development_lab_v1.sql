-- Mercury Development Lab. Additive to Trading's existing ownership/workflow.
create table if not exists public.trading_strategy_experience_bank (
  experiment_id text primary key, strategy_id text not null, strategy_family text,
  notebook_id text not null, experiment_class text not null check (experiment_class in ('PRACTICE_EXPERIMENT','MATERIAL_EXPERIMENT')),
  engine text not null, engine_version text, market text, symbol text, timeframe text,
  date_range jsonb, data_source text, base_configuration jsonb not null default '{}'::jsonb,
  modification jsonb not null default '{}'::jsonb, indicators jsonb not null default '[]'::jsonb,
  parameters jsonb not null default '{}'::jsonb, stop_method text, take_profit_method text,
  position_sizing text, risk_per_trade numeric, base_metrics jsonb not null default '{}'::jsonb,
  new_metrics jsonb not null default '{}'::jsonb, change_vs_baseline jsonb not null default '{}'::jsonb,
  result text check (result is null or result in ('POSITIVE','NEGATIVE','INCONCLUSIVE')),
  lesson text, confidence text, out_of_sample_tested boolean not null default false,
  robustness_tested boolean not null default false, engine_parity_status text not null default 'NOT_CROSS_ENGINE_TESTED',
  overfit_risk text, material_loop_incremented boolean not null default false,
  source_artifact text, created_at timestamptz not null default now(),
  check ((experiment_class='PRACTICE_EXPERIMENT' and material_loop_incremented=false) or experiment_class='MATERIAL_EXPERIMENT')
);
create index if not exists trading_experience_strategy_idx on public.trading_strategy_experience_bank(strategy_id, created_at desc);
create index if not exists trading_experience_context_idx on public.trading_strategy_experience_bank(strategy_family,market,timeframe);

create table if not exists public.trading_indicator_intelligence_bank (
  indicator_id text primary key, name text not null, function_class text not null,
  context jsonb not null default '{}'::jsonb, tests_run integer not null default 0,
  positive_results integer not null default 0, negative_results integer not null default 0,
  inconclusive_results integer not null default 0, metric_impacts jsonb not null default '{}'::jsonb,
  confidence text, last_updated timestamptz not null default now()
);
create table if not exists public.trading_timeframe_intelligence_bank (
  context_id text primary key, strategy_family text not null, market text not null,
  symbol_class text, timeframe text not null, tests_run integer not null default 0,
  positive_results integer not null default 0, negative_results integer not null default 0,
  metrics jsonb not null default '{}'::jsonb, robustness text, confidence text,
  last_updated timestamptz not null default now()
);
create table if not exists public.trading_market_intelligence_bank (
  context_id text primary key, strategy_family text not null, asset_class text,
  market text not null, symbol text, session text, regime_if_known text,
  result_metrics jsonb not null default '{}'::jsonb, test_count integer not null default 0,
  confidence text, last_updated timestamptz not null default now()
);
create table if not exists public.trading_money_management_bank (
  configuration_id text primary key, strategy_family text, market text, timeframe text,
  configuration jsonb not null, outcomes jsonb not null default '{}'::jsonb,
  test_count integer not null default 0, confidence text, last_updated timestamptz not null default now()
);
create table if not exists public.trading_repository_capability_bank (
  repository_id text primary key, repository text not null, owner text, url text,
  purpose text, language text, license text, active_status text, last_activity text,
  capabilities jsonb not null default '{}'::jsonb, risks jsonb not null default '{}'::jsonb,
  nexus_tested boolean not null default false, nexus_compatibility text,
  benchmark_result jsonb not null default '{}'::jsonb,
  use_class text check (use_class is null or use_class in ('PRODUCTION_COMPONENT','REFERENCE_IMPLEMENTATION','FALLBACK','RESEARCH_ONLY','REJECTED')),
  last_updated timestamptz not null default now()
);
create table if not exists public.trading_development_projects (
  strategy_id text primary key, notebook_id text not null,
  material_test_loops_completed integer check(material_test_loops_completed between 0 and 2),
  autonomous_material_loop_limit integer not null default 2 check(autonomous_material_loop_limit=2),
  development_state text not null default 'DEVELOPING',
  ray_gate_status text not null default 'NOT_DUE', live_trading_enabled boolean not null default false,
  practice_limits jsonb not null default '{"max_candidates_per_cycle":6,"max_parameter_variants":3,"max_timeframes_per_cycle":2,"max_markets_per_cycle":1,"max_total_practice_runs":6,"max_runtime_seconds":1200,"max_compute_cost_usd":0}'::jsonb,
  scorecard jsonb not null default '{}'::jsonb, updated_at timestamptz not null default now()
);
create table if not exists public.trading_development_lab_settings (
  settings_id text primary key default 'MERCURY_STRATEGY_DEVELOPMENT_LAB' check(settings_id='MERCURY_STRATEGY_DEVELOPMENT_LAB'),
  enabled boolean not null default true,
  live_trading_enabled boolean not null default false check(live_trading_enabled=false),
  autonomous_material_loop_limit integer not null default 2 check(autonomous_material_loop_limit=2),
  practice_limits jsonb not null default '{"max_practice_candidates_per_cycle":3,"max_parameter_variants":1,"max_timeframes_per_cycle":2,"max_markets_per_cycle":1,"max_total_practice_runs":4,"max_runtime_seconds":1200,"max_compute_cost_usd":0,"in_sample_fraction":0.7}'::jsonb,
  updated_at timestamptz not null default now()
);
insert into public.trading_development_lab_settings(settings_id) values('MERCURY_STRATEGY_DEVELOPMENT_LAB') on conflict do nothing;
create table if not exists public.trading_experiment_engine_runs (
  experiment_id text primary key, engine text not null, engine_version text,
  strategy_id text not null, symbol text, timeframe text, date_range jsonb,
  normalized_result jsonb not null, parity_status text not null default 'NOT_CROSS_ENGINE_TESTED',
  errors jsonb not null default '[]'::jsonb, warnings jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now()
);
create table if not exists public.trading_ray_campaigns (
  campaign_id text primary key, strategy_id text not null, approved_by text not null check(approved_by='RAY'),
  allowed_scope jsonb not null, max_runs integer not null, runs_used integer not null default 0,
  status text not null default 'APPROVED', created_at timestamptz not null default now()
);
create table if not exists public.trading_material_test_reservations (
  experiment_id text primary key, strategy_id text not null references public.trading_development_projects(strategy_id),
  selected_practice_experiment_id text not null references public.trading_strategy_experience_bank(experiment_id),
  notebook_id text not null, loop_number integer not null check(loop_number between 1 and 2),
  status text not null default 'TEST_READY' check(status in ('TEST_READY','TEST_EXECUTING','RESULT_PERSISTED','CANCELLED_BY_RAY')),
  created_at timestamptz not null default now(), completed_at timestamptz
);
create unique index if not exists trading_one_active_material_per_strategy_idx
  on public.trading_material_test_reservations(strategy_id) where status in ('TEST_READY','TEST_EXECUTING');

create or replace function public.guard_material_experience_insert()
returns trigger language plpgsql security invoker set search_path=public as $$
declare reservation public.trading_material_test_reservations%rowtype;
begin
  if new.experiment_class='MATERIAL_EXPERIMENT' then
    select * into reservation from public.trading_material_test_reservations where experiment_id=new.experiment_id;
    if not found or reservation.strategy_id<>new.strategy_id then
      raise exception 'APPROVED_TRADING_MATERIAL_RESERVATION_REQUIRED';
    end if;
    if reservation.selected_practice_experiment_id is null then raise exception 'SELECTED_PRACTICE_CANDIDATE_REQUIRED'; end if;
    if tg_op='INSERT' then
      if reservation.status<>'TEST_EXECUTING' then raise exception 'APPROVED_TRADING_MATERIAL_RESERVATION_REQUIRED'; end if;
      new.material_loop_incremented:=false;
    elsif reservation.status='RESULT_PERSISTED' and old.material_loop_incremented=false and new.material_loop_incremented=true then
      null;
    else
      raise exception 'MATERIAL_LOOP_COUNTER_MUTATION_REQUIRES_COMPLETION_RPC';
    end if;
  else
    new.material_loop_incremented:=false;
  end if;
  return new;
end $$;
drop trigger if exists trading_experience_material_guard on public.trading_strategy_experience_bank;
create trigger trading_experience_material_guard before insert or update on public.trading_strategy_experience_bank
  for each row execute function public.guard_material_experience_insert();

create or replace function public.reserve_trading_material_experiment(p_strategy_id text,p_experiment_id text,p_notebook_id text,p_selected_practice_experiment_id text)
returns jsonb language plpgsql security invoker set search_path=public as $$
declare project public.trading_development_projects%rowtype; existing public.trading_material_test_reservations%rowtype;
begin
  if not public.nexus_is_active_admin() then raise exception 'ADMIN_REQUIRED'; end if;
  if not exists(select 1 from public.trading_strategy_experience_bank where experiment_id=p_selected_practice_experiment_id and experiment_class='PRACTICE_EXPERIMENT' and engine_parity_status<>'FAIL') then
    raise exception 'SELECTED_PRACTICE_CANDIDATE_NOT_AVAILABLE_OR_PARITY_FAILED';
  end if;
  select * into project from public.trading_development_projects where strategy_id=p_strategy_id for update;
  if not found then return jsonb_build_object('status','WAITING_ON_SYSTEMS','next_owner','TRADING','reason','Create/reconcile Trading-owned development project and import authoritative material loop count before reservation.'); end if;
  if project.material_test_loops_completed is null then return jsonb_build_object('status','WAITING_ON_SYSTEMS','next_owner','TRADING','reason','Reconcile authoritative material-loop count before any material test.'); end if;
  if project.material_test_loops_completed >= project.autonomous_material_loop_limit then
    update public.trading_development_projects set ray_gate_status='RAY_REVIEW_REQUIRED',updated_at=now() where strategy_id=p_strategy_id;
    return jsonb_build_object('status','RAY_REVIEW_REQUIRED','next_owner','RAY','reason','Two autonomous material loops are complete.');
  end if;
  select * into existing from public.trading_material_test_reservations where experiment_id=p_experiment_id;
  if found then return jsonb_build_object('status',existing.status,'loop_number',existing.loop_number); end if;
  insert into public.trading_material_test_reservations(experiment_id,strategy_id,selected_practice_experiment_id,notebook_id,loop_number)
    values(p_experiment_id,p_strategy_id,p_selected_practice_experiment_id,p_notebook_id,project.material_test_loops_completed+1);
  return jsonb_build_object('status','TEST_READY','loop_number',project.material_test_loops_completed+1,'next_owner','TRADING');
end $$;

create or replace function public.start_trading_material_experiment(p_experiment_id text)
returns jsonb language plpgsql security invoker set search_path=public as $$
declare reservation public.trading_material_test_reservations%rowtype; project public.trading_development_projects%rowtype;
begin
  if not public.nexus_is_active_admin() then raise exception 'ADMIN_REQUIRED'; end if;
  select * into reservation from public.trading_material_test_reservations where experiment_id=p_experiment_id for update;
  if not found or reservation.status<>'TEST_READY' then raise exception 'TRADING_TEST_READY_RESERVATION_REQUIRED'; end if;
  select * into project from public.trading_development_projects where strategy_id=reservation.strategy_id for update;
  if project.material_test_loops_completed is null then return jsonb_build_object('status','WAITING_ON_SYSTEMS','next_owner','TRADING','reason','Reconcile material loop count before execution.'); end if;
  if project.material_test_loops_completed>=project.autonomous_material_loop_limit then
    update public.trading_development_projects set ray_gate_status='RAY_REVIEW_REQUIRED',updated_at=now() where strategy_id=project.strategy_id;
    return jsonb_build_object('status','RAY_REVIEW_REQUIRED','next_owner','RAY');
  end if;
  update public.trading_material_test_reservations set status='TEST_EXECUTING' where experiment_id=p_experiment_id;
  return jsonb_build_object('status','TEST_EXECUTING','loop_number',reservation.loop_number,'next_owner','TRADING');
end $$;

create or replace function public.complete_trading_material_experiment(p_experiment_id text)
returns jsonb language plpgsql security invoker set search_path=public as $$
declare reservation public.trading_material_test_reservations%rowtype; project public.trading_development_projects%rowtype;
begin
  if not public.nexus_is_active_admin() then raise exception 'ADMIN_REQUIRED'; end if;
  select * into reservation from public.trading_material_test_reservations where experiment_id=p_experiment_id for update;
  if not found then raise exception 'MATERIAL_RESERVATION_REQUIRED'; end if;
  if reservation.status='RESULT_PERSISTED' then return jsonb_build_object('status','ALREADY_COMPLETED'); end if;
  if reservation.status<>'TEST_EXECUTING' then raise exception 'MATERIAL_TEST_NOT_EXECUTING'; end if;
  if not exists(select 1 from public.trading_strategy_experience_bank where experiment_id=p_experiment_id and experiment_class='MATERIAL_EXPERIMENT') then raise exception 'PERSIST_MATERIAL_RESULT_BEFORE_COMPLETION'; end if;
  update public.trading_material_test_reservations set status='RESULT_PERSISTED',completed_at=now() where experiment_id=p_experiment_id;
  update public.trading_strategy_experience_bank set material_loop_incremented=true where experiment_id=p_experiment_id;
  update public.trading_development_projects set material_test_loops_completed=material_test_loops_completed+1,updated_at=now()
    where strategy_id=reservation.strategy_id returning * into project;
  if project.material_test_loops_completed>=project.autonomous_material_loop_limit then
    update public.trading_development_projects set ray_gate_status='RAY_REVIEW_REQUIRED',updated_at=now() where strategy_id=project.strategy_id;
    return jsonb_build_object('status','RAY_REVIEW_REQUIRED','material_test_loops_completed',project.material_test_loops_completed,'next_owner','RAY');
  end if;
  return jsonb_build_object('status','RESULT_PERSISTED','material_test_loops_completed',project.material_test_loops_completed,'next_owner','TRADING');
end $$;

do $$ declare t text; begin
  foreach t in array array['trading_strategy_experience_bank','trading_indicator_intelligence_bank','trading_timeframe_intelligence_bank','trading_market_intelligence_bank','trading_money_management_bank','trading_repository_capability_bank','trading_development_projects','trading_development_lab_settings','trading_experiment_engine_runs','trading_ray_campaigns','trading_material_test_reservations'] loop
    execute format('alter table public.%I enable row level security', t);
    execute format('drop policy if exists %I on public.%I', t || '_admin_all', t);
    execute format('create policy %I on public.%I for all to authenticated using (public.nexus_is_active_admin()) with check (public.nexus_is_active_admin())', t || '_admin_all', t);
    execute format('grant select, insert, update, delete on public.%I to authenticated', t);
  end loop;
end $$;
grant execute on function public.reserve_trading_material_experiment(text,text,text,text) to authenticated;
grant execute on function public.start_trading_material_experiment(text) to authenticated;
grant execute on function public.complete_trading_material_experiment(text) to authenticated;
