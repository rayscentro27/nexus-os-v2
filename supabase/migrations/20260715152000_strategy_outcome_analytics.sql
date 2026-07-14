-- Additive, non-causal outcome observations. These records never assert that a strategy caused a result.
create table if not exists public.credit_report_comparison_runs (
 id uuid primary key default gen_random_uuid(), tenant_id text not null, client_id text not null,
 prior_report_id text not null, later_report_id text not null, status text not null default 'queued' check (status in ('queued','processing','complete','failed','uncertain')),
 comparison_engine_version text not null, confidence text not null default 'medium' check (confidence in ('high','medium','low')),
 summary jsonb not null default '{}'::jsonb, created_at timestamptz not null default now(), completed_at timestamptz,
 unique(tenant_id, client_id, prior_report_id, later_report_id, comparison_engine_version)
);
create table if not exists public.credit_report_comparison_results (
 id uuid primary key default gen_random_uuid(), comparison_run_id uuid not null references public.credit_report_comparison_runs(id) on delete cascade,
 tenant_id text not null, client_id text not null, prior_report_id text not null, later_report_id text not null, canonical_account_id text,
 observation_type text not null check (observation_type in ('account_present_on_both_reports','account_not_found_on_later_report','account_newly_present','balance_changed','status_changed','payment_status_changed','ownership_changed','bureau_coverage_changed','no_measurable_change','uncertain_comparison')),
 observation_value jsonb not null default '{}'::jsonb, observation_source text not null default 'structured_report_comparison', confidence text not null check (confidence in ('high','medium','low')),
 strategy_match_id uuid references public.credit_strategy_matches(id), strategy_id text, strategy_version integer, client_decision_id uuid references public.credit_strategy_client_selections(id), evidence_document_id text references public.client_documents(id), notes text,
 created_at timestamptz not null default now()
);
create table if not exists public.strategy_outcome_observations (
 id uuid primary key default gen_random_uuid(), tenant_id text not null, client_id text not null, report_id text, prior_report_id text,
 canonical_account_id text, discrepancy_id text, strategy_match_id uuid references public.credit_strategy_matches(id), strategy_id text, strategy_version integer,
 client_decision_id uuid references public.credit_strategy_client_selections(id), observation_type text not null, observation_value jsonb not null default '{}'::jsonb,
 observation_source text not null check (observation_source in ('structured_report_comparison','client_reported','creditor_response','bureau_response','evidence_document','system')),
 confidence text not null default 'medium' check (confidence in ('high','medium','low')), observed_at timestamptz not null default now(), recorded_by text, evidence_document_id text references public.client_documents(id), comparison_engine_version text, notes text, created_at timestamptz not null default now()
);
create table if not exists public.credit_readiness_history (
 id uuid primary key default gen_random_uuid(), tenant_id text not null, client_id text not null, report_id text, prior_report_id text,
 credit_profile_status text check (credit_profile_status in ('ready_to_review','almost_ready','action_needed','insufficient_information')),
 tier_1_status text check (tier_1_status in ('ready_to_review','almost_ready','action_needed','insufficient_information')),
 tier_2_status text check (tier_2_status in ('ready_to_review','almost_ready','action_needed','insufficient_information')),
 readiness_score numeric, requirements jsonb not null default '[]'::jsonb, source text not null default 'system', observed_at timestamptz not null default now(), created_at timestamptz not null default now()
);
create index if not exists credit_report_comparison_runs_client_idx on public.credit_report_comparison_runs(tenant_id,client_id,created_at desc);
create index if not exists credit_report_comparison_results_run_idx on public.credit_report_comparison_results(comparison_run_id,created_at);
create index if not exists strategy_outcome_observations_client_idx on public.strategy_outcome_observations(tenant_id,client_id,observed_at desc);
create index if not exists credit_readiness_history_client_idx on public.credit_readiness_history(tenant_id,client_id,observed_at desc);
alter table public.credit_report_comparison_runs enable row level security;
alter table public.credit_report_comparison_results enable row level security;
alter table public.strategy_outcome_observations enable row level security;
alter table public.credit_readiness_history enable row level security;
create policy comparison_runs_read on public.credit_report_comparison_runs for select to authenticated using (public.nexus_is_active_admin() or exists(select 1 from public.tenant_memberships tm where tm.user_id=auth.uid() and tm.tenant_id=credit_report_comparison_runs.tenant_id and tm.client_id=credit_report_comparison_runs.client_id));
create policy comparison_results_read on public.credit_report_comparison_results for select to authenticated using (public.nexus_is_active_admin() or exists(select 1 from public.tenant_memberships tm where tm.user_id=auth.uid() and tm.tenant_id=credit_report_comparison_results.tenant_id and tm.client_id=credit_report_comparison_results.client_id));
create policy outcome_observations_read on public.strategy_outcome_observations for select to authenticated using (public.nexus_is_active_admin() or exists(select 1 from public.tenant_memberships tm where tm.user_id=auth.uid() and tm.tenant_id=strategy_outcome_observations.tenant_id and tm.client_id=strategy_outcome_observations.client_id));
create policy readiness_history_read on public.credit_readiness_history for select to authenticated using (public.nexus_is_active_admin() or exists(select 1 from public.tenant_memberships tm where tm.user_id=auth.uid() and tm.tenant_id=credit_readiness_history.tenant_id and tm.client_id=credit_readiness_history.client_id));
create policy comparison_runs_admin on public.credit_report_comparison_runs for all to authenticated using(public.nexus_is_active_admin()) with check(public.nexus_is_active_admin());
create policy comparison_results_admin on public.credit_report_comparison_results for all to authenticated using(public.nexus_is_active_admin()) with check(public.nexus_is_active_admin());
create policy outcome_observations_admin on public.strategy_outcome_observations for all to authenticated using(public.nexus_is_active_admin()) with check(public.nexus_is_active_admin());
create policy readiness_history_admin on public.credit_readiness_history for all to authenticated using(public.nexus_is_active_admin()) with check(public.nexus_is_active_admin());
grant select on public.credit_report_comparison_runs, public.credit_report_comparison_results, public.strategy_outcome_observations, public.credit_readiness_history to authenticated;
grant all on public.credit_report_comparison_runs, public.credit_report_comparison_results, public.strategy_outcome_observations, public.credit_readiness_history to service_role;
