-- Provisioning can create billable resources. Credentials are not authority;
-- the scoped policy must explicitly allow both autonomous use and spend.
create or replace function public.nexus_reserve_resource_creation(p_job_id text,p_provider text,p_purpose text,p_max_per_job integer,p_max_per_day integer)
returns jsonb language plpgsql security definer set search_path=pg_catalog,public as $$
declare p public.nexus_resource_policies; rkey text; job_n integer; day_n integer; provider_n integer;
begin
  if p_job_id is null or p_provider is null or p_purpose is null then raise exception 'INVALID_RESOURCE_CREATE_REQUEST'; end if;
  rkey:=md5(p_job_id||':'||upper(p_provider)||':'||p_purpose);
  perform pg_advisory_xact_lock(hashtext('nexus-resource-create:'||upper(p_provider)));
  if exists(select 1 from public.nexus_resource_creation_keys where resource_key=rkey) then return jsonb_build_object('allowed',true,'resource_key',rkey,'idempotent_replay',true); end if;
  select * into p from public.nexus_resource_policies where provider=upper(p_provider) and service='resource_creation' and job_type='*' and budget_period='DAILY' for update;
  if not found or p.state<>'NORMAL' or p.resource_creation_limit<=0 or not p.autonomous_usage_allowed or not p.autonomous_spend_allowed then
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
