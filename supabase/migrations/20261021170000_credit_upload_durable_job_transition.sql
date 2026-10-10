-- Route new client credit-report uploads through the existing durable queue.
-- The legacy credit_analysis_jobs table and historical rows remain intact.
alter table public.nexus_durable_jobs
  add column if not exists tenant_id text,
  add column if not exists client_id text,
  add column if not exists source_document_id text,
  add column if not exists governance_context jsonb not null default '{}'::jsonb;

alter table public.nexus_durable_jobs
  add constraint nexus_durable_jobs_governance_context_object
  check (jsonb_typeof(governance_context)='object');

alter table public.credit_report_parser_results
  add column if not exists nexus_job_id text;
create unique index if not exists credit_parser_result_nexus_job_unique
  on public.credit_report_parser_results(nexus_job_id) where nexus_job_id is not null;

create or replace function public.queue_credit_report_after_upload()
returns trigger
language plpgsql
security definer
set search_path = pg_catalog, public
as $$
declare
  durable_job_id text;
  correlation text := gen_random_uuid()::text;
  document_category text := lower(coalesce(new.category,''));
begin
  if document_category not in ('credit_report','credit report','credit_reports','three_bureau_credit_report') then
    return new;
  end if;

  -- The document RLS policy is the primary authorization boundary; repeat the
  -- membership check here so the SECURITY DEFINER path cannot be repurposed.
  if auth.uid() is null or not exists (
    select 1 from public.tenant_memberships tm
    where tm.user_id=auth.uid() and tm.tenant_id=new.tenant_id and tm.client_id=new.client_id
  ) then
    raise exception 'CREDIT_UPLOAD_MEMBERSHIP_REQUIRED';
  end if;
  if coalesce(new.source,'') <> 'client_portal_upload' or not new.client_visible or not new.approval_required then
    raise exception 'CREDIT_UPLOAD_SOURCE_NOT_ELIGIBLE';
  end if;

  insert into public.credit_document_workflows(tenant_id,client_id,document_id,analysis_status)
  values(new.tenant_id,new.client_id,new.id,'queued')
  on conflict(document_id) do nothing;

  insert into public.nexus_durable_jobs(
    job_id,department,job_type,priority,state,scheduled_at,max_attempts,payload_ref,
    correlation_id,idempotency_key,tenant_id,client_id,source_document_id,governance_context
  ) values (
    'job_'||replace(gen_random_uuid()::text,'-',''),
    'CREDIT_BUSINESS_FUNDING','CREDIT_REPORT_ANALYSIS',50,'READY',now(),3,new.id,
    correlation,'credit-report-upload:'||new.id,new.tenant_id,new.client_id,new.id,
    jsonb_build_object(
      'source','client_documents_insert_trigger',
      'policy_version','credit-upload-durable-v1',
      'requires_governed_dispatch',true,
      'paid_provider_authorized',false,
      'external_actions_authorized',false,
      'approval_required_for_external_actions',true
    )
  ) on conflict(idempotency_key) do nothing returning job_id into durable_job_id;

  if durable_job_id is not null then
    insert into public.credit_workflow_events(
      tenant_id,client_id,document_id,event_type,metadata,actor_type,actor_id,parser_version,ruleset_version
    ) values (
      new.tenant_id,new.client_id,new.id,'document_uploaded',
      jsonb_build_object('classification','credit_report','durable_job_id',durable_job_id,'correlation_id',correlation),
      'client',auth.uid()::text,'live-0.1.0','canonical-v1'
    ), (
      new.tenant_id,new.client_id,new.id,'analysis_queued',
      jsonb_build_object('automatic',true,'durable_job_id',durable_job_id,'correlation_id',correlation),
      'system',null,'live-0.1.0','canonical-v1'
    );
  end if;
  return new;
end;
$$;

revoke all on function public.queue_credit_report_after_upload() from public,anon,authenticated;
grant execute on function public.queue_credit_report_after_upload() to service_role;

comment on table public.credit_analysis_jobs is
  'Legacy credit-analysis queue retained for historical records and rollback; new client uploads enqueue nexus_durable_jobs.';
