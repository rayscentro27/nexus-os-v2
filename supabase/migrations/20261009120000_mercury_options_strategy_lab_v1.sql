-- Additive Options-specific Mercury memory. Existing Trading authority remains unchanged.
create table if not exists public.options_strategy_template_bank (
  strategy_family text primary key,
  market_outlook text,
  volatility_outlook text,
  standard_leg_pattern jsonb not null default '{}'::jsonb,
  risk_profile jsonb not null default '{}'::jsonb,
  key_greeks jsonb not null default '[]'::jsonb,
  ideal_environment jsonb not null default '{}'::jsonb,
  common_failure_modes jsonb not null default '[]'::jsonb,
  management_variables jsonb not null default '[]'::jsonb,
  capital_requirements jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now()
);
create table if not exists public.options_strategy_experience_bank (
  experiment_id text primary key,
  strategy_id text not null,
  strategy_family text not null,
  experiment_class text not null check (experiment_class in ('PRACTICE_EXPERIMENT','MATERIAL_EXPERIMENT')),
  underlying text, asset_class text, dte integer, expiration date,
  legs jsonb not null default '[]'::jsonb, strikes jsonb not null default '[]'::jsonb,
  strike_spacing jsonb not null default '{}'::jsonb, delta_values jsonb not null default '{}'::jsonb,
  entry_iv numeric, iv_rank numeric, iv_percentile numeric,
  bid_ask_spread jsonb not null default '{}'::jsonb, open_interest jsonb not null default '{}'::jsonb,
  volume jsonb not null default '{}'::jsonb, debit_or_credit text,
  max_loss numeric, theoretical_max_profit numeric, break_evens jsonb not null default '[]'::jsonb,
  entry_price numeric, exit_price numeric, profit_take_rule text, stop_rule text, time_exit text, roll_rule text,
  assignment_occurred boolean, early_exercise_occurred boolean, expiration_event text,
  capital_required numeric, capital_lockup_days integer,
  premium_pnl numeric, underlying_pnl numeric, covered_call_pnl numeric, option_pnl numeric,
  total_strategy_pnl numeric, max_adverse_excursion numeric, max_favorable_excursion numeric,
  max_drawdown numeric, return_on_capital numeric, expectancy numeric,
  theoretical_edge_score numeric, execution_feasibility_score numeric,
  result text check (result is null or result in ('POSITIVE','NEGATIVE','INCONCLUSIVE')),
  confidence text, sample_quality text, lesson text,
  source_claims jsonb not null default '[]'::jsonb,
  verification_gaps jsonb not null default '[]'::jsonb,
  test_fixture boolean not null default false,
  live_trading_enabled boolean not null default false check (live_trading_enabled=false),
  material_loop_incremented boolean not null default false,
  created_at timestamptz not null default now(),
  check (experiment_class <> 'PRACTICE_EXPERIMENT' or material_loop_incremented=false)
);
create table if not exists public.options_underlying_quality_bank (
  context_id text primary key, ticker text not null, asset_class text, strategy_family text not null,
  trend_score numeric, fundamental_score numeric, premium_score numeric, liquidity_score numeric,
  volatility_score numeric, earnings_risk text, assignment_risk text, test_count integer not null default 0,
  avg_return numeric, avg_drawdown numeric, avg_assignment_recovery_time numeric, avg_capital_lockup numeric,
  confidence text, evidence jsonb not null default '{}'::jsonb, updated_at timestamptz not null default now()
);
create table if not exists public.options_data_source_bank (
  source_id text primary key, source_or_engine text not null, purpose text, license text, active_status text,
  option_chain_support text, greeks_support text, iv_support text, historical_options_support text,
  multi_leg_support text, paper_trading_support text, live_trading_capability text, order_flow_support text,
  nexus_tested boolean not null default false, nexus_compatibility text, use_class text,
  evidence jsonb not null default '{}'::jsonb, updated_at timestamptz not null default now()
);
create table if not exists public.options_execution_engine_bank (
  engine_id text primary key, source_or_engine text not null, purpose text, license text, active_status text,
  option_chain_support text, greeks_support text, iv_support text, historical_options_support text,
  multi_leg_support text, paper_trading_support text, live_trading_capability text not null default 'OFF',
  order_flow_support text, nexus_tested boolean not null default false, nexus_compatibility text,
  use_class text, evidence jsonb not null default '{}'::jsonb, updated_at timestamptz not null default now(),
  check (live_trading_capability in ('OFF','UNAVAILABLE','CAPABLE_BUT_DISABLED'))
);
alter table public.options_strategy_template_bank enable row level security;
alter table public.options_strategy_experience_bank enable row level security;
alter table public.options_underlying_quality_bank enable row level security;
alter table public.options_data_source_bank enable row level security;
alter table public.options_execution_engine_bank enable row level security;
do $$ declare t text; begin
  foreach t in array array['options_strategy_template_bank','options_strategy_experience_bank','options_underlying_quality_bank','options_data_source_bank','options_execution_engine_bank'] loop
    execute format('drop policy if exists %I on public.%I',t||'_admin_all',t);
    execute format('create policy %I on public.%I for all to authenticated using (public.nexus_is_active_admin()) with check (public.nexus_is_active_admin())',t||'_admin_all',t);
  end loop;
end $$;
