create or replace function public.nexus_claim_durable_job_by_id(
  p_job_id text, p_worker_id text, p_lease_seconds integer default 300
) returns setof public.nexus_durable_jobs
language plpgsql security definer set search_path = pg_catalog, public as $$
begin
  return query
  update public.nexus_durable_jobs j
     set state='CLAIMED', claimed_by=p_worker_id, claimed_at=now(),
         lease_until=now()+make_interval(secs=>greatest(15,least(p_lease_seconds,3600))),
         attempt_count=attempt_count+1
   where j.job_id=p_job_id and j.state in ('READY','FAILED_RETRYABLE')
     and j.scheduled_at<=now() and j.attempt_count<j.max_attempts
     and (select count(*) from public.nexus_durable_jobs a where a.state in ('CLAIMED','RUNNING')) < 2
     and ((j.department<>'RESEARCH' and j.job_type not in ('RESEARCH_GAP_VERIFY','NOTEBOOKLM_RESEARCH','FEEDER_RESEARCH_CONTINUATION','PROACTIVE_DISCOVERY','CONTENT_INTELLIGENCE','MARKET_HEARTBEAT'))
       or (select count(*) from public.nexus_durable_jobs a where a.state in ('CLAIMED','RUNNING') and (a.department='RESEARCH' or a.job_type in ('RESEARCH_GAP_VERIFY','NOTEBOOKLM_RESEARCH','FEEDER_RESEARCH_CONTINUATION','PROACTIVE_DISCOVERY','CONTENT_INTELLIGENCE','MARKET_HEARTBEAT'))) < 1)
     and ((j.job_type not ilike '%BROWSER%' and j.job_type<>'NOTEBOOKLM_RESEARCH')
       or (select count(*) from public.nexus_durable_jobs a where a.state in ('CLAIMED','RUNNING') and (a.job_type ilike '%BROWSER%' or a.job_type='NOTEBOOKLM_RESEARCH')) < 1)
     and ((j.job_type not similar to '%(NOTEBOOKLM|BROWSER|FFMPEG|VIDEO|MEDIA|LARGE_MODEL)%')
       or (select count(*) from public.nexus_durable_jobs a where a.state in ('CLAIMED','RUNNING') and a.job_type similar to '%(NOTEBOOKLM|BROWSER|FFMPEG|VIDEO|MEDIA|LARGE_MODEL)%') < 1)
   returning j.*;
end; $$;
revoke all on function public.nexus_claim_durable_job_by_id(text,text,integer) from public, anon, authenticated;
grant execute on function public.nexus_claim_durable_job_by_id(text,text,integer) to service_role;
