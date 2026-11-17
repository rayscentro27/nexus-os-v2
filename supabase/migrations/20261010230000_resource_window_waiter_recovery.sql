-- Recover only daily circuits opened by an exhausted configured usage
-- dimension. Rate limits and operator-set hard stops stay closed.
create or replace function public.nexus_reset_daily_budget_hard_stops()
returns integer language plpgsql security definer set search_path=pg_catalog,public as $$
declare changed integer;
begin
  update public.nexus_resource_policies p
     set state='NORMAL',updated_at=now()
   where p.budget_period='DAILY' and p.state='HARD_STOP'
     and exists (
       select 1
         from jsonb_each(coalesce(p.hard_limits->'usage','{}'::jsonb)) cap
         join public.nexus_resource_incidents i
           on i.provider=p.provider
          and i.code='BUDGET_HARD_LIMIT'
          and i.threshold=jsonb_build_object(cap.key,cap.value)
          and i.created_at=p.updated_at
        where coalesce(cap.value::text,'0') not in ('0','null')
          and i.created_at < (date_trunc('day',now() at time zone 'UTC') at time zone 'UTC')
     );
  get diagnostics changed=row_count;
  return changed;
end; $$;
revoke all on function public.nexus_reset_daily_budget_hard_stops() from public,anon,authenticated;
grant execute on function public.nexus_reset_daily_budget_hard_stops() to service_role;

-- Resume the same durable job only after its exact resource policy is NORMAL.
create or replace function public.nexus_resume_resource_waiting_jobs()
returns integer language plpgsql security definer set search_path=pg_catalog,public as $$
declare changed integer;
begin
  update public.nexus_durable_jobs j
     set state='READY',scheduled_at=now(),attempt_count=greatest(0,j.attempt_count-1),
         governance_context=jsonb_set(coalesce(j.governance_context,'{}'::jsonb),
           '{resource_wait,resumed_at}',to_jsonb(now()),true)
   where j.state='WAITING'
     and coalesce(j.governance_context->'resource_wait'->>'resume_condition','')='RESOURCE_POLICY_NORMAL'
     and exists (
       select 1 from public.nexus_resource_policies p
        where p.provider=j.governance_context->'resource_wait'->>'provider'
          and p.service=j.governance_context->'resource_wait'->>'service'
          and p.job_type=j.governance_context->'resource_wait'->>'policy_job_type'
          and p.budget_period=j.governance_context->'resource_wait'->>'budget_period'
          and p.state='NORMAL'
     );
  get diagnostics changed=row_count;
  return changed;
end; $$;
revoke all on function public.nexus_resume_resource_waiting_jobs() from public,anon,authenticated;
grant execute on function public.nexus_resume_resource_waiting_jobs() to service_role;
