-- Nexus OS v2 — Day 2 premium foundation. Additive only (no destructive changes to 0001/0002).
-- UUID PKs, timestamps, JSONB payloads, indexes, RLS enabled, admin-only policies
-- consistent with the admin_users pattern from 0002. No anon/public policies.

create extension if not exists "pgcrypto";

-- A. workspaces
create table if not exists workspaces (
  id uuid primary key default gen_random_uuid(),
  workspace_key text unique not null,
  name text not null,
  description text,
  workspace_type text not null default 'internal',
  status text not null default 'active',
  metadata jsonb not null default '{}',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- B. agent_registry
create table if not exists agent_registry (
  id uuid primary key default gen_random_uuid(),
  agent_key text unique not null,
  name text not null,
  role text not null,
  description text,
  status text not null default 'stubbed',
  capabilities jsonb not null default '[]',
  workspace_keys jsonb not null default '[]',
  model_route_key text,
  metadata jsonb not null default '{}',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- C. research_runs
create table if not exists research_runs (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid references workspaces(id),
  requested_by text,
  question text not null,
  research_type text not null,
  status text not null default 'queued',
  summary text,
  decision text,
  confidence numeric,
  payload jsonb not null default '{}',
  created_at timestamptz not null default now(),
  completed_at timestamptz
);

-- D. research_sources
create table if not exists research_sources (
  id uuid primary key default gen_random_uuid(),
  research_run_id uuid references research_runs(id) on delete cascade,
  source_type text not null,
  title text,
  url text,
  author text,
  published_at timestamptz,
  accessed_at timestamptz default now(),
  snippet text,
  why_it_matters text,
  confidence numeric,
  metadata jsonb not null default '{}',
  created_at timestamptz not null default now()
);

-- E. monetization_opportunities
create table if not exists monetization_opportunities (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid references workspaces(id),
  title text not null,
  source_summary text,
  money_angle text,
  status text not null default 'captured',
  decision text not null default 'needs_review',
  speed_to_cash int,
  fit_with_goclear int,
  fit_with_nexus_tools int,
  audience_access int,
  implementation_effort int,
  compliance_risk int,
  automation_potential int,
  content_potential int,
  recurring_revenue_potential int,
  confidence int,
  overall_score int,
  smallest_test text,
  missing_tools jsonb not null default '[]',
  recommended_jobs jsonb not null default '[]',
  metadata jsonb not null default '{}',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- F. opportunity_experiments
create table if not exists opportunity_experiments (
  id uuid primary key default gen_random_uuid(),
  opportunity_id uuid references monetization_opportunities(id),
  workspace_id uuid references workspaces(id),
  title text not null,
  hypothesis text,
  test_plan text,
  success_metric text,
  status text not null default 'planned',
  cost_estimate numeric,
  result_summary text,
  result_status text,
  lessons text,
  metadata jsonb not null default '{}',
  created_at timestamptz not null default now(),
  completed_at timestamptz
);

-- G. partner_offers
create table if not exists partner_offers (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid references workspaces(id),
  offer_key text unique,
  name text not null,
  category text not null,
  description text,
  why_it_matters text,
  affiliate_disclosure text default 'Some recommendations may include partner links.',
  url text,
  secret_env_name text,
  approval_status text not null default 'draft',
  risk_level text not null default 'medium',
  metadata jsonb not null default '{}',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- H. client_recommendations
create table if not exists client_recommendations (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid references workspaces(id),
  client_label text,
  title text not null,
  recommendation_type text not null,
  reason text,
  next_step text,
  partner_offer_id uuid references partner_offers(id),
  status text not null default 'draft',
  metadata jsonb not null default '{}',
  created_at timestamptz not null default now()
);

-- I. creative_campaigns
create table if not exists creative_campaigns (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid references workspaces(id),
  campaign_key text unique,
  name text not null,
  goal text,
  audience text,
  offer text,
  status text not null default 'draft',
  compliance_notes text,
  metadata jsonb not null default '{}',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- J. creative_briefs
create table if not exists creative_briefs (
  id uuid primary key default gen_random_uuid(),
  campaign_id uuid references creative_campaigns(id),
  workspace_id uuid references workspaces(id),
  title text not null,
  platform text,
  audience text,
  pain_point text,
  hook text,
  angle text,
  cta text,
  compliance_notes text,
  status text not null default 'draft',
  metadata jsonb not null default '{}',
  created_at timestamptz not null default now()
);

-- K. creative_scores
create table if not exists creative_scores (
  id uuid primary key default gen_random_uuid(),
  creative_asset_id uuid references creative_assets(id),
  campaign_id uuid references creative_campaigns(id),
  hook_strength int,
  clarity int,
  money_alignment int,
  platform_fit int,
  brand_fit int,
  compliance_safety int,
  cta_strength int,
  uniqueness int,
  overall_score int,
  notes text,
  created_at timestamptz not null default now()
);

-- L. studio_outputs
create table if not exists studio_outputs (
  id uuid primary key default gen_random_uuid(),
  research_run_id uuid references research_runs(id),
  campaign_id uuid references creative_campaigns(id),
  workspace_id uuid references workspaces(id),
  output_type text not null,
  title text not null,
  summary text,
  script_text text,
  asset_url text,
  status text not null default 'draft',
  approval_id uuid references approvals(id),
  metadata jsonb not null default '{}',
  created_at timestamptz not null default now()
);

-- M. model_providers
create table if not exists model_providers (
  id uuid primary key default gen_random_uuid(),
  provider_key text unique not null,
  name text not null,
  provider_type text not null,
  base_url text,
  secret_env_name text,
  status text not null default 'registered',
  enabled boolean not null default false,
  privacy_level text not null default 'unknown',
  notes text,
  metadata jsonb not null default '{}',
  created_at timestamptz not null default now()
);

-- N. model_routes
create table if not exists model_routes (
  id uuid primary key default gen_random_uuid(),
  route_key text unique not null,
  task_type text not null,
  primary_provider_key text,
  fallback_provider_keys jsonb not null default '[]',
  policy text not null default 'manual_or_free_first',
  sensitive_data_allowed boolean not null default false,
  status text not null default 'registered',
  metadata jsonb not null default '{}',
  created_at timestamptz not null default now()
);

-- O. model_usage_logs
create table if not exists model_usage_logs (
  id uuid primary key default gen_random_uuid(),
  route_key text,
  provider_key text,
  task_type text,
  status text not null,
  fallback_used boolean default false,
  latency_ms int,
  token_estimate int,
  cost_estimate numeric,
  error_message text,
  metadata jsonb not null default '{}',
  created_at timestamptz not null default now()
);

-- P. integration_registry
create table if not exists integration_registry (
  id uuid primary key default gen_random_uuid(),
  integration_key text unique not null,
  name text not null,
  category text not null,
  purpose text,
  enabled boolean not null default false,
  status text not null default 'registered',
  requires_secret boolean not null default false,
  secret_env_names jsonb not null default '[]',
  risk_level text not null default 'medium',
  notes text,
  metadata jsonb not null default '{}',
  created_at timestamptz not null default now()
);

-- Q. trading_strategy_candidates
create table if not exists trading_strategy_candidates (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid references workspaces(id),
  title text not null,
  market text,
  timeframe text,
  source_summary text,
  entry_rules text,
  exit_rules text,
  risk_rules text,
  status text not null default 'captured',
  strategy_clarity int,
  rules_are_testable int,
  source_quality int,
  hype_risk int,
  backtest_feasibility int,
  confidence int,
  decision text,
  metadata jsonb not null default '{}',
  created_at timestamptz not null default now()
);

-- R. trading_backtests
create table if not exists trading_backtests (
  id uuid primary key default gen_random_uuid(),
  strategy_candidate_id uuid references trading_strategy_candidates(id),
  market text,
  timeframe text,
  start_date date,
  end_date date,
  status text not null default 'planned',
  win_rate numeric,
  profit_factor numeric,
  net_return numeric,
  max_drawdown numeric,
  trade_count int,
  expectancy numeric,
  stability_score numeric,
  result_summary text,
  metadata jsonb not null default '{}',
  created_at timestamptz not null default now(),
  completed_at timestamptz
);

-- S. trading_risk_rules
create table if not exists trading_risk_rules (
  id uuid primary key default gen_random_uuid(),
  rule_key text unique not null,
  description text not null,
  value jsonb not null default '{}',
  enabled boolean not null default true,
  created_at timestamptz not null default now()
);

-- T. seo_sites
create table if not exists seo_sites (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid references workspaces(id),
  site_key text unique,
  domain text not null,
  name text not null,
  status text not null default 'registered',
  metadata jsonb not null default '{}',
  created_at timestamptz not null default now()
);

-- U. seo_opportunities
create table if not exists seo_opportunities (
  id uuid primary key default gen_random_uuid(),
  site_id uuid references seo_sites(id),
  workspace_id uuid references workspaces(id),
  opportunity_type text not null,
  title text not null,
  keyword text,
  page_url text,
  reason text,
  recommended_action text,
  status text not null default 'captured',
  score int,
  metadata jsonb not null default '{}',
  created_at timestamptz not null default now()
);

-- V. ops_incidents
create table if not exists ops_incidents (
  id uuid primary key default gen_random_uuid(),
  incident_key text,
  severity text not null default 'info',
  component text not null,
  title text not null,
  description text,
  status text not null default 'open',
  diagnosis text,
  recommended_fix text,
  approval_required boolean not null default false,
  metadata jsonb not null default '{}',
  created_at timestamptz not null default now(),
  resolved_at timestamptz
);

-- W. worker_heartbeats
create table if not exists worker_heartbeats (
  id uuid primary key default gen_random_uuid(),
  worker_key text not null,
  status text not null default 'ok',
  last_seen_at timestamptz default now(),
  metadata jsonb not null default '{}',
  created_at timestamptz not null default now()
);

-- X. improvement_candidates
create table if not exists improvement_candidates (
  id uuid primary key default gen_random_uuid(),
  title text not null,
  source_type text,
  source_url text,
  summary text,
  capability_area text,
  capability_gain int,
  implementation_effort int,
  architecture_fit int,
  security_risk int,
  license_risk int,
  cost_risk int,
  money_impact int,
  urgency int,
  confidence int,
  decision text not null default 'needs_review',
  status text not null default 'captured',
  metadata jsonb not null default '{}',
  created_at timestamptz not null default now()
);

-- ── Indexes ──
create index if not exists idx_research_runs_status on research_runs (status, created_at desc);
create index if not exists idx_monetization_opps_status on monetization_opportunities (status, created_at desc);
create index if not exists idx_creative_campaigns_status on creative_campaigns (status, created_at desc);
create index if not exists idx_trading_candidates_status on trading_strategy_candidates (status, created_at desc);
create index if not exists idx_seo_opps_status on seo_opportunities (status, created_at desc);
create index if not exists idx_ops_incidents_status on ops_incidents (status, created_at desc);
create index if not exists idx_improvement_status on improvement_candidates (status, created_at desc);
create index if not exists idx_worker_heartbeats_key on worker_heartbeats (worker_key, last_seen_at desc);

-- ── RLS + admin policies (same admin_users pattern as 0002) ──
-- SELECT for active admins on every new table; INSERT/UPDATE for active admins on the
-- operational tables the admin dashboard writes to. No anon/public policies.
do $$
declare
  t text;
  read_tables text[] := array[
    'workspaces','agent_registry','research_runs','research_sources','monetization_opportunities',
    'opportunity_experiments','partner_offers','client_recommendations','creative_campaigns',
    'creative_briefs','creative_scores','studio_outputs','model_providers','model_routes',
    'model_usage_logs','integration_registry','trading_strategy_candidates','trading_backtests',
    'trading_risk_rules','seo_sites','seo_opportunities','ops_incidents','worker_heartbeats',
    'improvement_candidates'
  ];
  write_tables text[] := array[
    'research_runs','monetization_opportunities','opportunity_experiments','creative_campaigns',
    'creative_briefs','client_recommendations','improvement_candidates','ops_incidents'
  ];
begin
  foreach t in array read_tables loop
    execute format('alter table %I enable row level security', t);
    execute format('drop policy if exists %I on %I', 'admin read ' || t, t);
    execute format(
      'create policy %I on %I for select to authenticated using ('
      || 'exists (select 1 from admin_users a where a.id = auth.uid() and a.active = true))',
      'admin read ' || t, t);
  end loop;
  foreach t in array write_tables loop
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

-- Operational write access on the EXISTING core tables the admin dashboard drives
-- (Command Center creates jobs/events; Approval Center updates approvals). Admin-gated only.
do $$
declare t text;
begin
  foreach t in array array['nexus_events','agent_jobs','approvals'] loop
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
