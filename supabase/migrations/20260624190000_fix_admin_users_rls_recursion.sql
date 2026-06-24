-- Fix admin_users RLS recursion.
--
-- Root cause: the SELECT policy on public.admin_users queried public.admin_users
-- again to decide whether the caller was an admin. PostgreSQL applies RLS to that
-- inner read too, causing "infinite recursion detected in policy for relation
-- admin_users".
--
-- Safety model after this migration:
-- - admin_users is NOT made public.
-- - authenticated users may read only their own admin_users row.
-- - dashboard tables, including approvals, remain gated to active admins through
--   public.nexus_is_active_admin().
-- - no service-role key or privileged credential is exposed to the frontend.

create or replace function public.nexus_is_active_admin()
returns boolean
language sql
security definer
set search_path = public
stable
as $$
  select exists (
    select 1
    from public.admin_users
    where id = auth.uid()
      and active = true
  );
$$;

revoke all on function public.nexus_is_active_admin() from public;
grant execute on function public.nexus_is_active_admin() to authenticated;

alter table public.admin_users enable row level security;

drop policy if exists "admin read admin_users" on public.admin_users;
drop policy if exists "admin_users_select_self" on public.admin_users;

create policy "admin_users_select_self"
  on public.admin_users
  for select
  to authenticated
  using (id = auth.uid());

do $$
declare
  t text;
  rel regclass;
  read_tables text[] := array[
    'nexus_events','agent_jobs','approvals','social_accounts','social_posts',
    'social_publish_receipts','creative_assets','business_opportunities',
    'trading_signals','demo_trades','telegram_messages','system_health','settings',
    'workspaces','agent_registry','research_runs','research_sources','monetization_opportunities',
    'opportunity_experiments','partner_offers','client_recommendations','creative_campaigns',
    'creative_briefs','creative_scores','studio_outputs','model_providers','model_routes',
    'model_usage_logs','integration_registry','trading_strategy_candidates','trading_backtests',
    'trading_risk_rules','seo_sites','seo_opportunities','ops_incidents','worker_heartbeats',
    'improvement_candidates','approved_knowledge','model_route_decisions','hermes_model_requests',
    'intake_events','orientation_notes','transcript_reviews','dispositions','wagers','nexus_lessons',
    'creative_design_briefs','creative_design_variants','creative_design_scores',
    'creative_asset_comparisons','design_inspiration_sources','design_pattern_registry',
    'ui_quality_reviews','feature_design_packets','publish_readiness_packages',
    'publish_package_reviews','manual_publish_receipts','task_requests'
  ];
begin
  foreach t in array read_tables loop
    rel := to_regclass('public.' || t);
    if rel is not null then
      execute format('alter table %s enable row level security', rel);
      execute format('drop policy if exists %I on %s', 'admin read ' || t, rel);
      execute format(
        'create policy %I on %s for select to authenticated using (public.nexus_is_active_admin())',
        'admin read ' || t,
        rel
      );
    end if;
  end loop;
end $$;

do $$
declare
  t text;
  rel regclass;
  insert_tables text[] := array[
    'research_runs','monetization_opportunities','opportunity_experiments',
    'creative_campaigns','creative_briefs','client_recommendations',
    'improvement_candidates','ops_incidents','nexus_events','agent_jobs',
    'approvals','task_requests'
  ];
begin
  foreach t in array insert_tables loop
    rel := to_regclass('public.' || t);
    if rel is not null then
      execute format('drop policy if exists %I on %s', 'admin insert ' || t, rel);
      execute format(
        'create policy %I on %s for insert to authenticated with check (public.nexus_is_active_admin())',
        'admin insert ' || t,
        rel
      );
    end if;
  end loop;
end $$;

do $$
declare
  t text;
  rel regclass;
  update_tables text[] := array[
    'research_runs','monetization_opportunities','opportunity_experiments',
    'creative_campaigns','creative_briefs','client_recommendations',
    'improvement_candidates','ops_incidents','nexus_events','agent_jobs',
    'approvals','task_requests'
  ];
begin
  foreach t in array update_tables loop
    rel := to_regclass('public.' || t);
    if rel is not null then
      execute format('drop policy if exists %I on %s', 'admin update ' || t, rel);
      execute format(
        'create policy %I on %s for update to authenticated using (public.nexus_is_active_admin())',
        'admin update ' || t,
        rel
      );
    end if;
  end loop;
end $$;
