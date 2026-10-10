-- Additive durable queue. Large worker inputs remain in artifact storage.
create table if not exists public.nexus_durable_jobs (
  job_id text primary key,
  department text not null,
  job_type text not null,
  priority integer not null default 50,
  state text not null default 'READY' check (state in ('QUEUED','READY','CLAIMED','RUNNING','WAITING','COMPLETED','FAILED_RETRYABLE','BLOCKED','CANCELLED')),
  scheduled_at timestamptz not null default now(),
  claimed_at timestamptz,
  lease_until timestamptz,
  attempt_count integer not null default 0 check (attempt_count >= 0),
  max_attempts integer not null default 3 check (max_attempts between 1 and 10),
  payload_ref text,
  parent_job_id text references public.nexus_durable_jobs(job_id),
  correlation_id text not null,
  created_at timestamptz not null default now(),
  started_at timestamptz,
  completed_at timestamptz,
  last_error_code text,
  last_error_summary text,
  receipt_ref text,
  claimed_by text,
  idempotency_key text not null unique,
  result_hash text
);
create index if not exists nexus_durable_jobs_ready_idx on public.nexus_durable_jobs(state, scheduled_at, priority desc, created_at);
create index if not exists nexus_durable_jobs_lease_idx on public.nexus_durable_jobs(lease_until) where state in ('CLAIMED','RUNNING');
create table if not exists public.nexus_durable_schedules (
  schedule_id text primary key, department text not null, job_type text not null, priority integer not null default 50,
  payload_ref text, enabled boolean not null default true, interval_seconds integer,
  next_run_at timestamptz not null, correlation_id text not null, updated_at timestamptz not null default now()
);
alter table public.nexus_durable_schedules enable row level security;
revoke all on public.nexus_durable_schedules from public, anon, authenticated;
grant select, insert, update on public.nexus_durable_schedules to service_role;
alter table public.nexus_durable_jobs enable row level security;
revoke all on public.nexus_durable_jobs from public, anon, authenticated;
grant select, insert, update on public.nexus_durable_jobs to service_role;

create or replace function public.nexus_claim_durable_job(p_worker_id text, p_lease_seconds integer default 300)
returns setof public.nexus_durable_jobs language plpgsql security definer set search_path = pg_catalog, public as $$
declare claimed public.nexus_durable_jobs;
begin
  if p_worker_id is null or length(p_worker_id) < 1 or length(p_worker_id) > 160 then raise exception 'INVALID_WORKER_ID'; end if;
  perform pg_advisory_xact_lock(hashtext('nexus-durable-worker-limit'));
  update public.nexus_durable_jobs set state='FAILED_RETRYABLE', claimed_by=null, claimed_at=null, lease_until=null,
    scheduled_at=now()+interval '60 seconds', last_error_code='LEASE_EXPIRED', last_error_summary='Worker lease expired; recovered safely'
  where state in ('CLAIMED','RUNNING') and lease_until <= now() and attempt_count < max_attempts;
  update public.nexus_durable_jobs set state='BLOCKED', completed_at=now(), claimed_by=null, claimed_at=null, lease_until=null,
    last_error_code='RETRY_LIMIT', last_error_summary='Lease expired after maximum attempts'
  where state in ('CLAIMED','RUNNING') and lease_until <= now() and attempt_count >= max_attempts;
  select * into claimed from public.nexus_durable_jobs j where state in ('READY','FAILED_RETRYABLE') and scheduled_at <= now() and attempt_count < max_attempts
    and (select count(*) from public.nexus_durable_jobs active where active.state in ('CLAIMED','RUNNING')) < 2
    and ((j.department <> 'RESEARCH' and j.job_type not in ('RESEARCH_GAP_VERIFY','NOTEBOOKLM_RESEARCH','FEEDER_RESEARCH_CONTINUATION','PROACTIVE_DISCOVERY','CONTENT_INTELLIGENCE','MARKET_HEARTBEAT'))
      or (select count(*) from public.nexus_durable_jobs active where active.state in ('CLAIMED','RUNNING') and (active.department='RESEARCH' or active.job_type in ('RESEARCH_GAP_VERIFY','NOTEBOOKLM_RESEARCH','FEEDER_RESEARCH_CONTINUATION','PROACTIVE_DISCOVERY','CONTENT_INTELLIGENCE','MARKET_HEARTBEAT'))) < 1)
    and ((j.job_type not ilike '%BROWSER%' and j.job_type <> 'NOTEBOOKLM_RESEARCH')
      or (select count(*) from public.nexus_durable_jobs active where active.state in ('CLAIMED','RUNNING') and (active.job_type ilike '%BROWSER%' or active.job_type='NOTEBOOKLM_RESEARCH')) < 1)
    and (j.job_type not similar to '%(NOTEBOOKLM|BROWSER|FFMPEG|VIDEO|MEDIA|LARGE_MODEL)%'
      or (select count(*) from public.nexus_durable_jobs active where active.state in ('CLAIMED','RUNNING') and active.job_type similar to '%(NOTEBOOKLM|BROWSER|FFMPEG|VIDEO|MEDIA|LARGE_MODEL)%') < 1)
    order by priority desc, scheduled_at, created_at for update skip locked limit 1;
  if not found then return; end if;
  update public.nexus_durable_jobs set state='CLAIMED', claimed_by=p_worker_id, claimed_at=now(),
    lease_until=now()+make_interval(secs=>greatest(15,least(p_lease_seconds,3600))), attempt_count=attempt_count+1
    where job_id=claimed.job_id returning * into claimed;
  return next claimed;
end; $$;

create or replace function public.nexus_renew_durable_job_lease(p_job_id text, p_worker_id text, p_lease_seconds integer default 300)
returns boolean language sql security definer set search_path = pg_catalog, public as $$
  update public.nexus_durable_jobs set lease_until=now()+make_interval(secs=>greatest(15,least(p_lease_seconds,3600)))
  where job_id=p_job_id and claimed_by=p_worker_id and state in ('CLAIMED','RUNNING') and lease_until>now()
  returning true;
$$;
create or replace function public.nexus_recover_expired_durable_jobs()
returns integer language plpgsql security definer set search_path = pg_catalog, public as $$
declare affected integer;
begin
  update public.nexus_durable_jobs set state=case when attempt_count < max_attempts then 'FAILED_RETRYABLE' else 'BLOCKED' end,
    scheduled_at=case when attempt_count < max_attempts then now()+interval '60 seconds' else scheduled_at end,
    completed_at=case when attempt_count >= max_attempts then now() else null end,
    claimed_by=null, claimed_at=null, lease_until=null, last_error_code='LEASE_EXPIRED',
    last_error_summary='Worker lease expired; recovered safely'
  where state in ('CLAIMED','RUNNING') and lease_until <= now();
  get diagnostics affected = row_count; return affected;
end; $$;
create or replace function public.nexus_schedule_durable_jobs()
returns integer language plpgsql security definer set search_path = pg_catalog, public as $$
declare item public.nexus_durable_schedules; affected integer := 0; key text;
begin
  for item in select * from public.nexus_durable_schedules where enabled and next_run_at <= now()
    order by next_run_at limit 50 for update skip locked loop
    key := 'schedule:' || item.schedule_id || ':' || item.next_run_at::text;
    insert into public.nexus_durable_jobs(job_id,department,job_type,priority,state,scheduled_at,max_attempts,
      payload_ref,correlation_id,idempotency_key)
    values('job_' || replace(gen_random_uuid()::text,'-',''), item.department,item.job_type,item.priority,'READY',
      item.next_run_at,3,item.payload_ref,item.correlation_id,key) on conflict(idempotency_key) do nothing;
    if item.interval_seconds is null then update public.nexus_durable_schedules set enabled=false,updated_at=now() where schedule_id=item.schedule_id;
    else update public.nexus_durable_schedules set next_run_at=now()+make_interval(secs=>greatest(60,item.interval_seconds)),updated_at=now() where schedule_id=item.schedule_id; end if;
    affected := affected + 1;
  end loop;
  return affected;
end; $$;
create or replace function public.nexus_durable_job_health()
returns jsonb language sql stable security definer set search_path = pg_catalog, public as $$
  select jsonb_build_object(
    'counts', coalesce((select jsonb_object_agg(state,n) from (select state,count(*) n from public.nexus_durable_jobs group by state) c), '{}'::jsonb),
    'expired_leases', (select count(*) from public.nexus_durable_jobs where state in ('CLAIMED','RUNNING') and lease_until<=now()),
    'oldest_queued_age_seconds', coalesce((select greatest(0,floor(extract(epoch from (now()-min(created_at))))::integer) from public.nexus_durable_jobs where state in ('QUEUED','READY')),0),
    'jobs_completed_today', (select count(*) from public.nexus_durable_jobs where state='COMPLETED' and completed_at>=date_trunc('day',now())),
    'retry_count', (select coalesce(sum(attempt_count),0) from public.nexus_durable_jobs),
    'active_worker_count', (select count(*) from public.nexus_durable_jobs where state in ('CLAIMED','RUNNING'))
  );
$$;
revoke all on function public.nexus_claim_durable_job(text,integer) from public, anon, authenticated;
revoke all on function public.nexus_renew_durable_job_lease(text,text,integer) from public, anon, authenticated;
revoke all on function public.nexus_recover_expired_durable_jobs() from public, anon, authenticated;
revoke all on function public.nexus_schedule_durable_jobs() from public, anon, authenticated;
revoke all on function public.nexus_durable_job_health() from public, anon, authenticated;
grant execute on function public.nexus_claim_durable_job(text,integer) to service_role;
grant execute on function public.nexus_renew_durable_job_lease(text,text,integer) to service_role;
grant execute on function public.nexus_recover_expired_durable_jobs() to service_role;
grant execute on function public.nexus_schedule_durable_jobs() to service_role;
grant execute on function public.nexus_durable_job_health() to service_role;
