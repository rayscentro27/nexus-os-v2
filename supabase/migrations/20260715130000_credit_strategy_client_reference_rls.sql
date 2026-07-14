-- Ensure client-written audit/tool rows reference the same visible tenant recommendation.
drop policy if exists credit_strategy_decisions_insert on public.credit_strategy_client_decisions;
create policy credit_strategy_decisions_insert on public.credit_strategy_client_decisions for insert to authenticated with check (
  public.nexus_is_active_admin() or (
    actor_type='client' and exists(
      select 1 from public.tenant_memberships tm
      join public.credit_strategy_recommendations r on r.id=credit_strategy_client_decisions.recommendation_id
        and r.tenant_id=credit_strategy_client_decisions.tenant_id and r.client_id=credit_strategy_client_decisions.client_id and r.client_visible
      where tm.user_id=auth.uid() and tm.tenant_id=credit_strategy_client_decisions.tenant_id and tm.client_id=credit_strategy_client_decisions.client_id
    )
  )
);
drop policy if exists credit_strategy_tools_client_insert on public.credit_strategy_tool_requests;
create policy credit_strategy_tools_client_insert on public.credit_strategy_tool_requests for insert to authenticated with check (
  public.nexus_is_active_admin() or exists(
    select 1 from public.tenant_memberships tm
    join public.credit_strategy_recommendations r on r.id=credit_strategy_tool_requests.recommendation_id
      and r.tenant_id=credit_strategy_tool_requests.tenant_id and r.client_id=credit_strategy_tool_requests.client_id and r.client_visible
    where tm.user_id=auth.uid() and tm.tenant_id=credit_strategy_tool_requests.tenant_id and tm.client_id=credit_strategy_tool_requests.client_id
  )
);
