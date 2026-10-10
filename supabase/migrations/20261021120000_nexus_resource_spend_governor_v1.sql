-- Additive, default-deny resource and spend controls. No existing rows or RLS
-- policies are changed. Policy rows intentionally start disabled.
create table if not exists public.nexus_resource_policies (
  provider text not null, service text not null default '*', job_type text not null default '*', budget_period text not null check (budget_period in ('DAILY','MONTHLY')),
  autonomous_usage_allowed boolean not null default false, autonomous_spend_allowed boolean not null default false,
  soft_limits jsonb not null default '{}'::jsonb, hard_limits jsonb not null default '{}'::jsonb,
  concurrency_limit integer not null default 0 check (concurrency_limit >= 0),
  resource_creation_limit integer not null default 0 check (resource_creation_limit >= 0),
  state text not null default 'DISABLED' check (state in ('NORMAL','ELEVATED','THROTTLED','HARD_STOP','HUMAN_APPROVAL_REQUIRED','DISABLED')),
  approval_required boolean not null default true, updated_at timestamptz not null default now(),
  primary key(provider,service,job_type,budget_period)
);
create table if not exists public.nexus_resource_reservations (
  reservation_id text primary key, idempotency_key text not null unique, provider text not null, service text not null,
  job_type text not null, budget_period text not null check (budget_period in ('DAILY','MONTHLY')), job_id text not null,
  estimate jsonb not null, actual jsonb not null default '{}'::jsonb,
  status text not null check(status in ('ACTIVE','RECONCILED','RELEASED','DENIED')),
  created_at timestamptz not null default now(), expires_at timestamptz not null default (now()+interval '6 hours'), reconciled_at timestamptz
);
create index if not exists nexus_resource_reservations_scope_idx on public.nexus_resource_reservations(provider,service,job_type,budget_period,status,created_at);
create table if not exists public.nexus_resource_incidents (
  incident_id text primary key, provider text, job_id text, project_id text, code text not null,
  threshold jsonb, observed jsonb, action text not null, unrelated_work_continued boolean, created_at timestamptz not null default now()
);
create index if not exists nexus_resource_incidents_recent_idx on public.nexus_resource_incidents(created_at desc);
create table if not exists public.nexus_job_footprints (
  job_id text primary key, correlation_id text, project_id text, department text, job_type text,
  footprint jsonb not null, receipt_hash text not null, created_at timestamptz not null default now()
);
create table if not exists public.nexus_certification_ledger (
  certification_id text primary key, capability text not null, status text not null check(status in ('NOT_TESTED','MOCK_PASS','LOCAL_REAL_PASS','DATABASE_REAL_PASS','EXTERNAL_REAL_PASS','END_TO_END_REAL_PASS','FAILED','BLOCKED')),
  project_id text, job_id text, evidence_ref text, provider text, host text, estimated_cost numeric, actual_cost numeric,
  result jsonb not null default '{}'::jsonb, updated_at timestamptz not null default now()
);
create table if not exists public.nexus_resource_creation_keys (
  resource_key text primary key, job_id text not null, provider text not null, purpose text not null,
  state text not null check(state in ('RESERVED','ACTIVE','RELEASED')), created_at timestamptz not null default now()
);

do $$ declare p text; period text; begin
  foreach p in array array['SUPABASE','ORACLE','MODAL','OPENROUTER','FAL_AI','KAGGLE','HUGGING_FACE','BROWSER_EXTERNAL_SERVICES','EMAIL_PROVIDER','SOCIAL_MEDIA_EXTERNAL_ACTIONS'] loop
    foreach period in array array['DAILY','MONTHLY'] loop
      insert into public.nexus_resource_policies(provider,service,job_type,budget_period,state,approval_required,soft_limits,hard_limits)
      values(p,'*','*',period,'DISABLED',true,
        '{"rate":{"requests":0,"operations":0,"window_seconds":60},"usage":{},"money":{}}'::jsonb,
        '{"rate":{"requests":0,"operations":0,"window_seconds":60},"usage":{},"money":{}}'::jsonb)
      on conflict(provider,service,job_type,budget_period) do nothing;
    end loop;
  end loop;
end $$;

alter table public.nexus_resource_policies enable row level security;
alter table public.nexus_resource_reservations enable row level security;
alter table public.nexus_resource_incidents enable row level security;
alter table public.nexus_job_footprints enable row level security;
alter table public.nexus_certification_ledger enable row level security;
alter table public.nexus_resource_creation_keys enable row level security;
revoke all on public.nexus_resource_policies,public.nexus_resource_reservations,public.nexus_resource_incidents,public.nexus_job_footprints,public.nexus_certification_ledger,public.nexus_resource_creation_keys from public,anon,authenticated;
revoke all on public.nexus_resource_policies,public.nexus_resource_reservations,public.nexus_resource_incidents,public.nexus_job_footprints,public.nexus_certification_ledger,public.nexus_resource_creation_keys from service_role;
grant select,insert,update on public.nexus_resource_policies,public.nexus_resource_reservations,public.nexus_resource_incidents,public.nexus_job_footprints,public.nexus_certification_ledger,public.nexus_resource_creation_keys to service_role;

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
  update public.nexus_resource_reservations set status='RELEASED',reconciled_at=now() where provider=pol.provider and status='ACTIVE' and expires_at<=now();
  select count(*) into active_count from public.nexus_resource_reservations where provider=pol.provider and status='ACTIVE';
  if pol.concurrency_limit>0 and active_count>=pol.concurrency_limit then return jsonb_build_object('allowed',false,'state','THROTTLED','code','CONCURRENCY_LIMIT'); end if;
  select reservation_id into rid from public.nexus_resource_reservations where idempotency_key=idem;
  if rid is not null then return jsonb_build_object('allowed',true,'reservation_id',rid,'idempotent_replay',true); end if;
  if coalesce((p_estimate->>'cost')::numeric,0)>coalesce((pol.hard_limits->'money'->>'per_job')::numeric,coalesce((pol.hard_limits->'money'->>'per_day')::numeric,0))
     and coalesce((pol.hard_limits->'money'->>'per_job')::numeric,coalesce((pol.hard_limits->'money'->>'per_day')::numeric,0))>0 then
    update public.nexus_resource_policies set state='HARD_STOP',updated_at=now() where provider=pol.provider and service=pol.service and job_type=pol.job_type and budget_period=pol.budget_period;
    insert into public.nexus_resource_incidents values('inc_'||replace(gen_random_uuid()::text,'-',''),pol.provider,p_job_id,null,'JOB_COST_LIMIT',pol.hard_limits->'money',p_estimate,'HARD_STOP',null,now());
    return jsonb_build_object('allowed',false,'state','HARD_STOP','code','JOB_COST_LIMIT');
  end if;
  for dim,amount in select key,value::text::numeric from jsonb_each_text(p_estimate) where key not in ('budget_period','billable') loop
    if dim in ('requests','operations') then
      cap:=coalesce((pol.hard_limits->'rate'->>dim)::numeric,0);
      if cap>0 then
        select coalesce(sum(coalesce(nullif(r.actual,'{}'::jsonb)->>dim,nullif(r.estimate,'{}'::jsonb)->>dim,'0')::numeric),0) into used from public.nexus_resource_reservations r
        where r.provider=pol.provider and r.status in ('ACTIVE','RECONCILED') and r.created_at>=now()-make_interval(secs=>greatest(1,coalesce((pol.hard_limits->'rate'->>'window_seconds')::integer,60)));
        if used+amount>cap then return jsonb_build_object('allowed',false,'state','THROTTLED','code','RATE_LIMIT','dimension',dim); end if;
      end if;
      continue;
    elsif dim='cost' then
      moneycap:=coalesce((pol.hard_limits->'money'->>case when p_budget_period='DAILY' then 'per_day' else 'per_month' end)::numeric,0);
      cap:=least(moneycap,coalesce((pol.hard_limits->'money'->>'per_job')::numeric,moneycap));
    else cap:=coalesce((pol.hard_limits->'usage'->>dim)::numeric,0);
    end if;
    if cap>0 then
      select coalesce(sum(coalesce(nullif(r.actual,'{}'::jsonb)->>dim,nullif(r.estimate,'{}'::jsonb)->>dim,'0')::numeric),0) into used
      from public.nexus_resource_reservations r where r.provider=pol.provider and r.service=p_service and r.job_type=p_job_type and r.budget_period=p_budget_period and r.status in ('ACTIVE','RECONCILED')
        and r.created_at>=case when p_budget_period='DAILY' then date_trunc('day',now()) else date_trunc('month',now()) end
        ;
      if used+amount>cap then
        update public.nexus_resource_policies set state='HARD_STOP',updated_at=now() where provider=pol.provider and service=pol.service and job_type=pol.job_type and budget_period=pol.budget_period;
        insert into public.nexus_resource_incidents values('inc_'||replace(gen_random_uuid()::text,'-',''),pol.provider,p_job_id,null,'BUDGET_HARD_LIMIT',jsonb_build_object(dim,cap),jsonb_build_object(dim,used+amount),'HARD_STOP',null,now());
        return jsonb_build_object('allowed',false,'state','HARD_STOP','code','BUDGET_HARD_LIMIT','dimension',dim);
      end if;
    end if;
  end loop;
  rid:='reserve_'||replace(gen_random_uuid()::text,'-','');
  insert into public.nexus_resource_reservations(reservation_id,idempotency_key,provider,service,job_type,budget_period,job_id,estimate,status,created_at,expires_at)
    values(rid,idem,pol.provider,p_service,p_job_type,p_budget_period,p_job_id,p_estimate,'ACTIVE',now(),now()+interval '6 hours');
  return jsonb_build_object('allowed',true,'reservation_id',rid,'idempotent_replay',false);
end $$;
revoke all on function public.nexus_reserve_resource_budget(text,text,text,text,text,jsonb,text) from public,anon,authenticated;
grant execute on function public.nexus_reserve_resource_budget(text,text,text,text,text,jsonb,text) to service_role;

create or replace function public.nexus_reserve_resource_creation(p_job_id text,p_provider text,p_purpose text,p_max_per_job integer,p_max_per_day integer)
returns jsonb language plpgsql security definer set search_path=pg_catalog,public as $$
declare p public.nexus_resource_policies; rkey text; job_n integer; day_n integer; provider_n integer;
begin
  if p_job_id is null or p_provider is null or p_purpose is null then raise exception 'INVALID_RESOURCE_CREATE_REQUEST'; end if;
  rkey:=md5(p_job_id||':'||upper(p_provider)||':'||p_purpose);
  perform pg_advisory_xact_lock(hashtext('nexus-resource-create:'||upper(p_provider)));
  if exists(select 1 from public.nexus_resource_creation_keys where resource_key=rkey) then return jsonb_build_object('allowed',true,'resource_key',rkey,'idempotent_replay',true); end if;
  select * into p from public.nexus_resource_policies where provider=upper(p_provider) and service='resource_creation' and job_type='*' and budget_period='DAILY' for update;
  if not found or p.state<>'NORMAL' or p.resource_creation_limit<=0 then
    insert into public.nexus_resource_incidents values('inc_'||replace(gen_random_uuid()::text,'-',''),upper(p_provider),p_job_id,null,'RESOURCE_CREATION_NOT_AUTHORIZED',null,jsonb_build_object('purpose',p_purpose),'HUMAN_APPROVAL_REQUIRED',null,now());
    return jsonb_build_object('allowed',false,'state','HUMAN_APPROVAL_REQUIRED','code','RESOURCE_CREATION_NOT_AUTHORIZED');
  end if;
  select count(*) into job_n from public.nexus_resource_creation_keys where job_id=p_job_id and state in ('RESERVED','ACTIVE');
  select count(*) into day_n from public.nexus_resource_creation_keys where provider=upper(p_provider) and created_at>=date_trunc('day',now()) and state in ('RESERVED','ACTIVE');
  select count(*) into provider_n from public.nexus_resource_creation_keys where provider=upper(p_provider) and state in ('RESERVED','ACTIVE');
  if p_max_per_job<=0 or p_max_per_day<=0 or job_n>=p_max_per_job or day_n>=p_max_per_day or provider_n>=p.resource_creation_limit then
    insert into public.nexus_resource_incidents values('inc_'||replace(gen_random_uuid()::text,'-',''),upper(p_provider),p_job_id,null,'RESOURCE_CREATION_LIMIT',jsonb_build_object('per_job',p_max_per_job,'per_day',p_max_per_day,'provider_active',p.resource_creation_limit),jsonb_build_object('job',job_n,'day',day_n,'provider',provider_n),'REJECT_CREATION',null,now());
    return jsonb_build_object('allowed',false,'state','HARD_STOP','code','RESOURCE_CREATION_LIMIT');
  end if;
  insert into public.nexus_resource_creation_keys(resource_key,job_id,provider,purpose,state) values(rkey,p_job_id,upper(p_provider),p_purpose,'RESERVED');
  return jsonb_build_object('allowed',true,'resource_key',rkey,'idempotent_replay',false);
end $$;
revoke all on function public.nexus_reserve_resource_creation(text,text,text,integer,integer) from public,anon,authenticated;
grant execute on function public.nexus_reserve_resource_creation(text,text,text,integer,integer) to service_role;

create or replace function public.nexus_resource_governor_health()
returns jsonb language sql stable security definer set search_path=pg_catalog,public as $$
  select jsonb_build_object(
    'providers',coalesce((select jsonb_agg(jsonb_build_object('provider',p.provider,'service',p.service,'state',p.state,'autonomous_usage_allowed',p.autonomous_usage_allowed,'autonomous_spend_allowed',p.autonomous_spend_allowed,'approval_required',p.approval_required,'daily_usage',coalesce(u.daily_usage,'{}'::jsonb),'monthly_usage',coalesce(u.monthly_usage,'{}'::jsonb),'reserved_usage',coalesce(u.reserved_usage,'{}'::jsonb),'active_paid_jobs',coalesce(u.active_paid_jobs,0))) from public.nexus_resource_policies p left join lateral (select jsonb_build_object('reservations',count(*) filter(where r.budget_period='DAILY' and r.status='RECONCILED'),'estimated_cost',coalesce(sum((r.actual->>'cost')::numeric) filter(where r.budget_period='DAILY' and r.status='RECONCILED'),0)) daily_usage,jsonb_build_object('reservations',count(*) filter(where r.budget_period='MONTHLY' and r.status='RECONCILED'),'estimated_cost',coalesce(sum((r.actual->>'cost')::numeric) filter(where r.budget_period='MONTHLY' and r.status='RECONCILED'),0)) monthly_usage,jsonb_build_object('active_reservations',count(*) filter(where r.status='ACTIVE'),'estimated_cost',coalesce(sum((r.estimate->>'cost')::numeric) filter(where r.status='ACTIVE'),0)) reserved_usage,count(*) filter(where r.status='ACTIVE' and coalesce((r.estimate->>'cost')::numeric,0)>0) active_paid_jobs from public.nexus_resource_reservations r where r.provider=p.provider) u on true where p.service='*' and p.job_type='*'), '[]'::jsonb),
    'recent_incidents',coalesce((select jsonb_agg(jsonb_build_object('provider',provider,'job_id',job_id,'code',code,'action',action,'created_at',created_at) order by created_at desc) from (select provider,job_id,code,action,created_at from public.nexus_resource_incidents order by created_at desc limit 20) recent),'[]'::jsonb));
$$;
revoke all on function public.nexus_resource_governor_health() from public,anon,authenticated;
grant execute on function public.nexus_resource_governor_health() to service_role;
