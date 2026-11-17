-- Daily usage circuits recover at the next UTC window only when the circuit
-- was opened by the matching budget-limit incident. Manual/health hard stops
-- remain closed for operator-controlled recovery.
create or replace function public.nexus_reset_daily_budget_hard_stops()
returns integer language plpgsql security definer set search_path=pg_catalog,public as $$
declare changed integer;
begin
  update public.nexus_resource_policies p
     set state='NORMAL',updated_at=now()
   where p.budget_period='DAILY' and p.state='HARD_STOP'
     and coalesce((p.hard_limits->'usage'->>'bytes')::numeric,0)>0
     and exists (
       select 1 from public.nexus_resource_incidents i
        where i.provider=p.provider and i.code='BUDGET_HARD_LIMIT'
          and i.threshold=jsonb_build_object('bytes',p.hard_limits->'usage'->'bytes')
          and i.created_at=p.updated_at
          and i.created_at < (date_trunc('day',now() at time zone 'UTC') at time zone 'UTC')
     );
  get diagnostics changed=row_count;
  return changed;
end; $$;
revoke all on function public.nexus_reset_daily_budget_hard_stops() from public,anon,authenticated;
grant execute on function public.nexus_reset_daily_budget_hard_stops() to service_role;
