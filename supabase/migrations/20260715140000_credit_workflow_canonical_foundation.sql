-- Additive credit workflow state separation, versioned queue, canonical model, and audit history.
create table if not exists public.credit_document_workflows (
  id uuid primary key default gen_random_uuid(), tenant_id text not null, client_id text not null, document_id text not null unique,
  document_status text not null default 'uploaded' check (document_status in ('uploaded','invalid','archived')),
  analysis_status text not null default 'not_queued' check (analysis_status in ('not_queued','queued','processing','complete','failed_retryable','failed_permanent','cancelled')),
  strategy_status text not null default 'not_started' check (strategy_status in ('not_started','pending','ready','blocked','not_applicable')),
  client_action_status text not null default 'not_ready' check (client_action_status in ('not_ready','ready','in_progress','waiting_for_client','complete')),
  exception_review_status text not null default 'not_required' check (exception_review_status in ('not_required','required','in_review','resolved','rejected')),
  mail_status text not null default 'not_requested' check (mail_status in ('not_requested','draft_ready','awaiting_authorization','authorized','queued','sent','failed','cancelled')),
  exception_code text, exception_reason text, latest_analysis_job_id uuid, latest_parser_result_id uuid references public.credit_report_parser_results(id) on delete set null,
  canonical_matching_completed_at timestamptz, discrepancy_detection_completed_at timestamptz, created_at timestamptz not null default now(), updated_at timestamptz not null default now()
);
comment on table public.credit_document_workflows is 'Independent document, analysis, strategy, client-action, exception-review, and mail states. A negative account alone is not an exception.';

alter table public.credit_analysis_jobs drop constraint if exists credit_analysis_jobs_status_check;
alter table public.credit_analysis_jobs add column if not exists analysis_type text not null default 'three_bureau_credit_report';
alter table public.credit_analysis_jobs add column if not exists parser_version text not null default 'live-0.1.0';
alter table public.credit_analysis_jobs add column if not exists worker_version text;
alter table public.credit_analysis_jobs add column if not exists ruleset_version text not null default 'canonical-v1';
alter table public.credit_analysis_jobs add column if not exists idempotency_key text;
alter table public.credit_analysis_jobs add column if not exists claimed_by text;
alter table public.credit_analysis_jobs add column if not exists lease_expires_at timestamptz;
alter table public.credit_analysis_jobs add column if not exists max_attempts integer not null default 3 check (max_attempts between 1 and 10);
alter table public.credit_analysis_jobs add column if not exists started_at timestamptz;
alter table public.credit_analysis_jobs add column if not exists requested_reason text;
alter table public.credit_analysis_jobs add column if not exists parent_attempt_id uuid references public.credit_analysis_jobs(id) on delete set null;
alter table public.credit_analysis_jobs add column if not exists superseded_by_job_id uuid references public.credit_analysis_jobs(id) on delete set null;
alter table public.credit_analysis_jobs add column if not exists retryable boolean;
alter table public.credit_analysis_jobs add constraint credit_analysis_jobs_status_check check (status in ('queued','processing','complete','failed_retryable','failed_permanent','cancelled')) not valid;
update public.credit_analysis_jobs set status=case when status='failed' then 'failed_retryable' when status='needs_manual_review' then 'failed_permanent' else status end where status in ('failed','needs_manual_review');
alter table public.credit_analysis_jobs validate constraint credit_analysis_jobs_status_check;
update public.credit_analysis_jobs set idempotency_key=document_id||':'||analysis_type||':'||parser_version where idempotency_key is null;
alter table public.credit_analysis_jobs alter column idempotency_key set not null;
drop index if exists public.credit_analysis_jobs_one_active_per_document;
create unique index if not exists credit_analysis_jobs_one_active_version on public.credit_analysis_jobs(document_id,analysis_type,parser_version) where status in ('queued','processing');
create unique index if not exists credit_analysis_jobs_one_current_complete_version on public.credit_analysis_jobs(document_id,analysis_type,parser_version) where status='complete' and superseded_by_job_id is null;
create index if not exists credit_analysis_jobs_lease_idx on public.credit_analysis_jobs(status,lease_expires_at);
alter table public.credit_report_parser_results add column if not exists analysis_job_id uuid references public.credit_analysis_jobs(id) on delete set null;
create unique index if not exists credit_parser_result_analysis_job_unique on public.credit_report_parser_results(analysis_job_id) where analysis_job_id is not null;

alter table public.credit_document_workflows add constraint credit_document_workflows_latest_job_fk foreign key(latest_analysis_job_id) references public.credit_analysis_jobs(id) on delete set null;

create table if not exists public.credit_bureau_tradelines (
  id uuid primary key default gen_random_uuid(), tenant_id text not null, client_id text not null, document_id text not null, parser_result_id uuid not null references public.credit_report_parser_results(id) on delete cascade,
  source_index integer not null, bureau text not null check (bureau in ('experian','equifax','transunion','other')), creditor_name_original text, creditor_name_normalized text,
  original_creditor_original text, original_creditor_normalized text, account_type_original text, account_type_normalized text, account_reference_masked text, account_suffix text,
  account_status_original text, account_status_normalized text, payment_status_original text, payment_status_normalized text, balance numeric, credit_limit numeric, high_balance numeric, past_due numeric,
  date_opened date, date_closed date, last_reported_date date, ownership_original text, ownership_normalized text, remarks text, comments text, payment_history jsonb not null default '[]'::jsonb,
  source_reference text, parser_confidence text not null default 'low' check (parser_confidence in ('low','medium','high')), raw_normalized_extraction_reference text,
  created_at timestamptz not null default now(), unique(parser_result_id,source_index)
);
create table if not exists public.credit_canonical_accounts (
  id uuid primary key default gen_random_uuid(), tenant_id text not null, client_id text not null, document_id text not null, parser_result_id uuid not null references public.credit_report_parser_results(id) on delete cascade,
  normalized_creditor_label text not null, normalized_account_type text not null, canonical_status text, match_confidence numeric not null check (match_confidence between 0 and 1),
  match_tier text not null check (match_tier in ('high_confidence','ambiguous','rejected')), match_reasons jsonb not null default '[]'::jsonb, conflict_reasons jsonb not null default '[]'::jsonb,
  review_requirement text not null default 'not_required' check (review_requirement in ('not_required','exception_required')), threshold_version text not null, matching_engine_version text not null,
  version integer not null default 1, created_at timestamptz not null default now(), updated_at timestamptz not null default now()
);
create table if not exists public.credit_canonical_account_tradelines (
  canonical_account_id uuid not null references public.credit_canonical_accounts(id) on delete cascade, tradeline_id uuid not null references public.credit_bureau_tradelines(id) on delete cascade,
  primary key(canonical_account_id,tradeline_id)
);
create table if not exists public.credit_tradeline_match_decisions (
  id uuid primary key default gen_random_uuid(), tenant_id text not null, client_id text not null, document_id text not null, parser_result_id uuid not null references public.credit_report_parser_results(id) on delete cascade,
  left_tradeline_id uuid not null references public.credit_bureau_tradelines(id) on delete cascade, right_tradeline_id uuid not null references public.credit_bureau_tradelines(id) on delete cascade,
  decision text not null check (decision in ('high_confidence','ambiguous','rejected')), total_score numeric not null, component_scores jsonb not null default '{}'::jsonb,
  positive_reasons jsonb not null default '[]'::jsonb, conflict_reasons jsonb not null default '[]'::jsonb, threshold_version text not null, matching_engine_version text not null, created_at timestamptz not null default now()
);
create table if not exists public.credit_unmatched_tradelines (
  id uuid primary key default gen_random_uuid(), tenant_id text not null, client_id text not null, document_id text not null, parser_result_id uuid not null references public.credit_report_parser_results(id) on delete cascade,
  tradeline_id uuid not null references public.credit_bureau_tradelines(id) on delete cascade, reason text not null, exception_required boolean not null default false, created_at timestamptz not null default now(), unique(parser_result_id,tradeline_id)
);
create table if not exists public.credit_report_discrepancies (
  id uuid primary key default gen_random_uuid(), tenant_id text not null, client_id text not null, document_id text not null, parser_result_id uuid not null references public.credit_report_parser_results(id) on delete cascade,
  canonical_account_id uuid references public.credit_canonical_accounts(id) on delete cascade, discrepancy_type text not null, involved_tradeline_ids jsonb not null default '[]'::jsonb, bureau_values jsonb not null default '{}'::jsonb,
  confidence text not null check (confidence in ('low','medium','high')), severity text not null check (severity in ('low','medium','high')), detection_rule text not null, ruleset_version text not null,
  explanation text not null, client_confirmation_required boolean not null default false, exception_review_required boolean not null default false, status text not null default 'detected' check (status in ('detected','acknowledged','resolved','dismissed')), created_at timestamptz not null default now()
);
create table if not exists public.credit_workflow_events (
  id uuid primary key default gen_random_uuid(), tenant_id text not null, client_id text not null, document_id text not null, analysis_job_id uuid references public.credit_analysis_jobs(id) on delete set null,
  event_type text not null check (event_type in ('document_uploaded','analysis_queued','analysis_claimed','analysis_completed','analysis_failed','analysis_retried','canonical_matching_completed','ambiguous_match_detected','discrepancy_created','exception_required','exception_resolved','admin_rerun_requested')),
  metadata jsonb not null default '{}'::jsonb, actor_type text not null check (actor_type in ('system','client','admin','worker')), actor_id text, parser_version text, worker_version text, ruleset_version text, created_at timestamptz not null default now()
);

create index if not exists credit_bureau_tradelines_document_idx on public.credit_bureau_tradelines(document_id,parser_result_id); create index if not exists credit_canonical_accounts_document_idx on public.credit_canonical_accounts(document_id,parser_result_id); create index if not exists credit_discrepancies_document_idx on public.credit_report_discrepancies(document_id,parser_result_id); create index if not exists credit_workflow_events_document_idx on public.credit_workflow_events(document_id,created_at);

create or replace function public.validate_credit_workflow_transition() returns trigger language plpgsql as $$ begin
  if old.document_status<>new.document_status and not ((old.document_status='uploaded' and new.document_status in ('invalid','archived')) or (old.document_status='invalid' and new.document_status='archived')) then raise exception 'invalid document status transition'; end if;
  if old.analysis_status<>new.analysis_status and not ((old.analysis_status='not_queued' and new.analysis_status in ('queued','cancelled')) or (old.analysis_status='queued' and new.analysis_status in ('processing','cancelled','failed_retryable')) or (old.analysis_status='processing' and new.analysis_status in ('complete','failed_retryable','failed_permanent','cancelled')) or (old.analysis_status='failed_retryable' and new.analysis_status in ('queued','failed_permanent','cancelled')) or (old.analysis_status='complete' and new.analysis_status='queued')) then raise exception 'invalid analysis status transition'; end if;
  new.updated_at=now(); return new;
end $$;
drop trigger if exists validate_credit_workflow_transition_trigger on public.credit_document_workflows; create trigger validate_credit_workflow_transition_trigger before update on public.credit_document_workflows for each row execute function public.validate_credit_workflow_transition();

create or replace function public.queue_credit_report_after_upload() returns trigger language plpgsql security definer set search_path=public as $$ declare job_id uuid; parser_v text:='live-0.1.0'; begin
  if lower(coalesce(new.category,'')) not in ('credit_report','credit report','three_bureau_credit_report') then return new; end if;
  insert into public.credit_document_workflows(tenant_id,client_id,document_id,analysis_status) values(new.tenant_id,new.client_id,new.id,'queued') on conflict(document_id) do nothing;
  insert into public.credit_analysis_jobs(tenant_id,client_id,document_id,status,analysis_type,parser_version,ruleset_version,idempotency_key,requested_by,requested_reason)
    values(new.tenant_id,new.client_id,new.id,'queued','three_bureau_credit_report',parser_v,'canonical-v1',new.id||':three_bureau_credit_report:'||parser_v,auth.uid(),'automatic valid credit-report upload')
    on conflict(document_id,analysis_type,parser_version) where status in ('queued','processing') do nothing returning id into job_id;
  if job_id is not null then update public.credit_document_workflows set latest_analysis_job_id=job_id where document_id=new.id; insert into public.credit_workflow_events(tenant_id,client_id,document_id,analysis_job_id,event_type,metadata,actor_type,actor_id,parser_version,ruleset_version) values(new.tenant_id,new.client_id,new.id,job_id,'document_uploaded','{"classification":"credit_report"}'::jsonb,'client',auth.uid()::text,parser_v,'canonical-v1'),(new.tenant_id,new.client_id,new.id,job_id,'analysis_queued','{"automatic":true}'::jsonb,'system',null,parser_v,'canonical-v1'); end if;
  return new;
end $$;
drop trigger if exists queue_credit_report_after_upload_trigger on public.client_documents; create trigger queue_credit_report_after_upload_trigger after insert on public.client_documents for each row execute function public.queue_credit_report_after_upload();

create or replace function public.request_credit_analysis_rerun(p_document_id text,p_reason text) returns uuid language plpgsql security definer set search_path=public as $$ declare prior public.credit_analysis_jobs%rowtype; new_id uuid:=gen_random_uuid(); begin
  if not public.nexus_is_active_admin() then raise exception 'active admin required'; end if;
  if length(trim(coalesce(p_reason,'')))<5 then raise exception 'rerun reason required'; end if;
  select * into prior from public.credit_analysis_jobs where document_id=p_document_id and status='complete' and superseded_by_job_id is null order by completed_at desc nulls last,created_at desc limit 1 for update;
  if prior.id is null then raise exception 'no completed analysis to rerun'; end if;
  insert into public.credit_analysis_jobs(id,tenant_id,client_id,document_id,status,analysis_type,parser_version,ruleset_version,idempotency_key,requested_by,requested_reason,parent_attempt_id)
  values(new_id,prior.tenant_id,prior.client_id,prior.document_id,'queued',prior.analysis_type,prior.parser_version,prior.ruleset_version,prior.idempotency_key||':rerun:'||new_id::text,auth.uid(),trim(p_reason),prior.id);
  update public.credit_analysis_jobs set superseded_by_job_id=new_id,updated_at=now() where id=prior.id;
  update public.credit_document_workflows set analysis_status='queued',latest_analysis_job_id=new_id where document_id=p_document_id;
  insert into public.credit_workflow_events(tenant_id,client_id,document_id,analysis_job_id,event_type,metadata,actor_type,actor_id,parser_version,ruleset_version) values(prior.tenant_id,prior.client_id,prior.document_id,new_id,'admin_rerun_requested',jsonb_build_object('reason',left(trim(p_reason),200),'parent_attempt_id',prior.id),'admin',auth.uid()::text,prior.parser_version,prior.ruleset_version);
  return new_id;
end $$;
revoke all on function public.request_credit_analysis_rerun(text,text) from public; grant execute on function public.request_credit_analysis_rerun(text,text) to authenticated;

-- Backfill successful reports as complete normal cases; do not manufacture exceptions.
insert into public.credit_document_workflows(tenant_id,client_id,document_id,analysis_status,exception_review_status,latest_parser_result_id,canonical_matching_completed_at,discrepancy_detection_completed_at)
select d.tenant_id,d.client_id,d.id,case when p.id is null then 'not_queued' else 'complete' end,'not_required',p.id,case when p.id is null then null else now() end,case when p.id is null then null else now() end
from public.client_documents d left join lateral(select id from public.credit_report_parser_results p where p.document_id=d.id and p.extraction_success=true order by p.created_at desc limit 1)p on true
where lower(coalesce(d.category,'')) in ('credit_report','credit report','three_bureau_credit_report') on conflict(document_id) do nothing;

alter table public.credit_document_workflows enable row level security; alter table public.credit_bureau_tradelines enable row level security; alter table public.credit_canonical_accounts enable row level security; alter table public.credit_canonical_account_tradelines enable row level security; alter table public.credit_tradeline_match_decisions enable row level security; alter table public.credit_unmatched_tradelines enable row level security; alter table public.credit_report_discrepancies enable row level security; alter table public.credit_workflow_events enable row level security;
create policy credit_document_workflows_admin on public.credit_document_workflows for all to authenticated using(public.nexus_is_active_admin()) with check(public.nexus_is_active_admin()); create policy credit_document_workflows_client_read on public.credit_document_workflows for select to authenticated using(exists(select 1 from public.tenant_memberships tm where tm.user_id=auth.uid() and tm.tenant_id=credit_document_workflows.tenant_id and tm.client_id=credit_document_workflows.client_id));
create policy credit_bureau_tradelines_admin on public.credit_bureau_tradelines for all to authenticated using(public.nexus_is_active_admin()) with check(public.nexus_is_active_admin()); create policy credit_canonical_accounts_admin on public.credit_canonical_accounts for all to authenticated using(public.nexus_is_active_admin()) with check(public.nexus_is_active_admin()); create policy credit_canonical_links_admin on public.credit_canonical_account_tradelines for all to authenticated using(public.nexus_is_active_admin()) with check(public.nexus_is_active_admin()); create policy credit_match_decisions_admin on public.credit_tradeline_match_decisions for all to authenticated using(public.nexus_is_active_admin()) with check(public.nexus_is_active_admin()); create policy credit_unmatched_admin on public.credit_unmatched_tradelines for all to authenticated using(public.nexus_is_active_admin()) with check(public.nexus_is_active_admin()); create policy credit_discrepancies_admin on public.credit_report_discrepancies for all to authenticated using(public.nexus_is_active_admin()) with check(public.nexus_is_active_admin()); create policy credit_workflow_events_admin on public.credit_workflow_events for all to authenticated using(public.nexus_is_active_admin()) with check(public.nexus_is_active_admin()); create policy credit_workflow_events_client_read on public.credit_workflow_events for select to authenticated using(exists(select 1 from public.tenant_memberships tm where tm.user_id=auth.uid() and tm.tenant_id=credit_workflow_events.tenant_id and tm.client_id=credit_workflow_events.client_id));
grant select,insert,update on public.credit_document_workflows,public.credit_bureau_tradelines,public.credit_canonical_accounts,public.credit_canonical_account_tradelines,public.credit_tradeline_match_decisions,public.credit_unmatched_tradelines,public.credit_report_discrepancies,public.credit_workflow_events to authenticated;
