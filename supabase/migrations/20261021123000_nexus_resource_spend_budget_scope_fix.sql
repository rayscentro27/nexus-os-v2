-- Per-job cost stops must not place the whole provider into HARD_STOP. A zero
-- per-job limit means "not configured"; daily/monthly limits remain active.
create or replace function public.nexus_reserve_resource_budget(p_provider text,p_service text,p_job_type text,p_budget_period text,p_job_id text,p_estimate jsonb,p_purpose text default 'execution')
returns jsonb language plpgsql security definer set search_path=pg_catalog,public as $$
declare pol public.nexus_resource_policies; idem text; rid text; dim text; amount numeric; cap numeric; used numeric; moneycap numeric; active_count integer;
begin
  if p_provider is null or p_job_id is null or p_estimate is null or p_budget_period is null or p_budget_period not in ('DAILY','MONTHLY') then raise exception 'INVALID_GOVERNOR_RESERVATION'; end if;
  idem:=md5(p_job_id||':'||upper(p_provider)||':'||p_purpose);
  perform pg_advisory_xact_lock(hashtext('nexus-governor:'||upper(p_provider)||':'||p_service||':'||p_job_type||':'||p_budget_period));
  select * into pol from public.nexus_resource_policies where provider=upper(p_provider) and service in (p_service,'*') and job_type in (p_job_type,'*') and budget_period=p_budget_period order by (service='*'),(job_type='*') limit 1 for update;
  if not found then
    insert into public.nexus_resource_incidents values('inc_'||replace(gen_random_uuid()::text,'-',''),upper(p_provider),p_job_id,null,'UNKNOWN_PAID_PROVIDER',null,p_estimate,'HUMAN_APPROVAL_REQUIRED',null,now());
    return jsonb_build_object('allowed',false,'state','HUMAN_APPROVAL_REQUIRED','code','UNKNOWN_PAID_PROVIDER');
  end if;
  if pol.state='HARD_STOP' or pol.state='DISABLED' or not pol.autonomous_usage_allowed or ((coalesce((p_estimate->>'cost')::numeric,0)>0) and not pol.autonomous_spend_allowed) then
    insert into public.nexus_resource_incidents values('inc_'||replace(gen_random_uuid()::text,'-',''),pol.provider,p_job_id,null,case when pol.state='HARD_STOP' then 'PROVIDER_HARD_STOP' else 'SPEND_OR_USAGE_NOT_AUTHORIZED' end,pol.hard_limits,p_estimate,case when pol.state='HARD_STOP' then 'STOP_AFFECTED_JOB' else 'HUMAN_APPROVAL_REQUIRED' end,null,now());
    return jsonb_build_object('allowed',false,'state',case when pol.state='HARD_STOP' then 'HARD_STOP' else 'HUMAN_APPROVAL_REQUIRED' end,'code','POLICY_DENIED');
  end if;
  if coalesce((p_estimate->>'billable')::boolean,false) and not (p_estimate ? 'cost') then
    insert into public.nexus_resource_incidents values('inc_'||replace(gen_random_uuid()::text,'-',''),pol.provider,p_job_id,null,'COST_ESTIMATE_UNAVAILABLE',pol.hard_limits,p_estimate,'HUMAN_APPROVAL_REQUIRED',null,now());
    return jsonb_build_object('allowed',false,'state','HUMAN_APPROVAL_REQUIRED','code','COST_ESTIMATE_UNAVAILABLE');
  end if;
  select reservation_id into rid from public.nexus_resource_reservations where idempotency_key=idem;
  if rid is not null then return jsonb_build_object('allowed',true,'reservation_id',rid,'idempotent_replay',true); end if;
  update public.nexus_resource_reservations set status='RELEASED',reconciled_at=now() where provider=pol.provider and status='ACTIVE' and expires_at<=now();
  select count(*) into active_count from public.nexus_resource_reservations where provider=pol.provider and status='ACTIVE';
  if pol.concurrency_limit>0 and active_count>=pol.concurrency_limit then return jsonb_build_object('allowed',false,'state','THROTTLED','code','CONCURRENCY_LIMIT'); end if;
  if coalesce((p_estimate->>'cost')::numeric,0)>coalesce(nullif((pol.hard_limits->'money'->>'per_job')::numeric,0),coalesce((pol.hard_limits->'money'->>'per_day')::numeric,0)) and coalesce(nullif((pol.hard_limits->'money'->>'per_job')::numeric,0),coalesce((pol.hard_limits->'money'->>'per_day')::numeric,0))>0 then
    insert into public.nexus_resource_incidents values('inc_'||replace(gen_random_uuid()::text,'-',''),pol.provider,p_job_id,null,'JOB_COST_LIMIT',pol.hard_limits->'money',p_estimate,'STOP_AFFECTED_JOB',null,now());
    return jsonb_build_object('allowed',false,'state','HARD_STOP','code','JOB_COST_LIMIT');
  end if;
  for dim,amount in select key,value::text::numeric from jsonb_each_text(p_estimate) where key not in ('budget_period','billable') loop
    if dim in ('requests','operations') then
      cap:=coalesce((pol.hard_limits->'rate'->>dim)::numeric,0);
      if cap>0 then
        select coalesce(sum(coalesce(nullif(r.actual,'{}'::jsonb)->>dim,nullif(r.estimate,'{}'::jsonb)->>dim,'0')::numeric),0) into used from public.nexus_resource_reservations r where r.provider=pol.provider and r.status in ('ACTIVE','RECONCILED') and r.created_at>=now()-make_interval(secs=>greatest(1,coalesce((pol.hard_limits->'rate'->>'window_seconds')::integer,60)));
        if used+amount>cap then return jsonb_build_object('allowed',false,'state','THROTTLED','code','RATE_LIMIT','dimension',dim); end if;
      end if;
      continue;
    elsif dim='cost' then
      moneycap:=coalesce((pol.hard_limits->'money'->>case when p_budget_period='DAILY' then 'per_day' else 'per_month' end)::numeric,0);
      cap:=case when coalesce((pol.hard_limits->'money'->>'per_job')::numeric,0)>0 then least(moneycap,(pol.hard_limits->'money'->>'per_job')::numeric) else moneycap end;
    else cap:=coalesce((pol.hard_limits->'usage'->>dim)::numeric,0);
    end if;
    if cap>0 then
      select coalesce(sum(coalesce(nullif(r.actual,'{}'::jsonb)->>dim,nullif(r.estimate,'{}'::jsonb)->>dim,'0')::numeric),0) into used from public.nexus_resource_reservations r where r.provider=pol.provider and r.service=p_service and r.job_type=p_job_type and r.budget_period=p_budget_period and r.status in ('ACTIVE','RECONCILED') and r.created_at>=case when p_budget_period='DAILY' then date_trunc('day',now()) else date_trunc('month',now()) end;
      if used+amount>cap then
        update public.nexus_resource_policies set state='HARD_STOP',updated_at=now() where provider=pol.provider and service=pol.service and job_type=pol.job_type and budget_period=pol.budget_period;
        insert into public.nexus_resource_incidents values('inc_'||replace(gen_random_uuid()::text,'-',''),pol.provider,p_job_id,null,'BUDGET_HARD_LIMIT',jsonb_build_object(dim,cap),jsonb_build_object(dim,used+amount),'HARD_STOP',null,now());
        return jsonb_build_object('allowed',false,'state','HARD_STOP','code','BUDGET_HARD_LIMIT','dimension',dim);
      end if;
    end if;
  end loop;
  rid:='reserve_'||replace(gen_random_uuid()::text,'-','');
  insert into public.nexus_resource_reservations(reservation_id,idempotency_key,provider,service,job_type,budget_period,job_id,estimate,status,created_at,expires_at) values(rid,idem,pol.provider,p_service,p_job_type,p_budget_period,p_job_id,p_estimate,'ACTIVE',now(),now()+interval '6 hours');
  return jsonb_build_object('allowed',true,'reservation_id',rid,'idempotent_replay',false);
end $$;
