-- GoClear friends-beta release gates. Additive only.
-- Reuses the existing review work item, Marketing Distribution records, and
-- provider lifecycle events; this is not a second scheduler or CRM model.
begin;

alter table public.goclear_email_events
  add column if not exists signature_verified boolean not null default false,
  add column if not exists provider_event_id text;
create unique index if not exists goclear_email_events_provider_event_uq
  on public.goclear_email_events(provider, provider_event_id)
  where provider_event_id is not null;

create table if not exists public.goclear_followup_jobs (
  id uuid primary key default gen_random_uuid(),
  client_id text not null,
  tenant_id text not null,
  work_id text not null unique,
  trigger_event text not null check (trigger_event in ('review_requested','client_report_ready','evaluation_completed','beta_feedback_submitted')),
  status text not null default 'queued' check (status in ('queued','sending','sent','delivered','failed','blocked')),
  email_message_id text,
  provider_message_id text,
  failure_reason text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists goclear_followup_jobs_client_idx on public.goclear_followup_jobs(client_id, created_at desc);

create table if not exists public.goclear_beta_journey_projection (
  projection_id uuid primary key default gen_random_uuid(),
  tester_invite_id uuid references public.tester_invitations(id) on delete set null,
  tester_display_name text,
  tester_email_hash text,
  lead_id uuid references public.goclear_leads(id) on delete set null,
  client_id text not null unique,
  current_stage text not null,
  invite_status text,
  funnel_started boolean not null default false,
  account_created boolean not null default false,
  portal_entered boolean not null default false,
  upload_status text not null default 'not_started',
  evaluation_status text not null default 'not_started',
  clyde_status text not null default 'not_started',
  report_status text not null default 'not_started',
  review_status text not null default 'not_started',
  followup_status text not null default 'not_started',
  followup_provider_message_id text,
  feedback_status text not null default 'not_started',
  completion_status text not null default 'in_progress',
  last_activity_at timestamptz not null default now(),
  blocking_issue text,
  ray_action_required boolean not null default false,
  metadata jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now()
);
alter table public.goclear_beta_journey_projection enable row level security;
drop policy if exists goclear_beta_projection_admin_select on public.goclear_beta_journey_projection;
create policy goclear_beta_projection_admin_select on public.goclear_beta_journey_projection
  for select to authenticated using (public.nexus_is_active_admin());
grant select on public.goclear_beta_journey_projection to authenticated;

create or replace function public.goclear_refresh_beta_journey_projection(p_client_id text)
returns public.goclear_beta_journey_projection
language plpgsql security definer set search_path = public
as $$
declare r public.goclear_beta_journey_projection;
declare l public.goclear_leads;
declare u record; c record; s record; rp record; rv record; f record; m record; i record;
begin
  select * into l from public.goclear_leads where client_id = p_client_id order by created_at desc limit 1;
  if l.id is null then raise exception 'beta_lead_not_found'; end if;
  select * into u from public.tester_invitations where assigned_client_id = p_client_id or auth_user_id = l.auth_user_id order by created_at desc limit 1;
  select * into c from public.goclear_upload_receipts where client_id = p_client_id order by created_at desc limit 1;
  select * into s from public.readiness_scores where client_id = p_client_id order by created_at desc limit 1;
  select * into rp from public.goclear_clyde_receipts where client_id = p_client_id order by created_at desc limit 1;
  select * into rv from public.goclear_client_reports where client_id = p_client_id order by created_at desc limit 1;
  select * into i from public.client_tasks where client_id = p_client_id and category = 'review_request' order by created_at desc limit 1;
  select * into f from public.goclear_beta_feedback where client_id = p_client_id order by created_at desc limit 1;
  select mm.*, gj.status as job_status, gj.provider_message_id as job_provider_id
    into m from public.marketing_email_messages mm
    left join public.goclear_followup_jobs gj on gj.email_message_id = mm.email_message_id
    where mm.lead_id = l.id::text and mm.message_type in ('NURTURE','TRANSACTIONAL','TEST')
    order by mm.created_at desc limit 1;
  insert into public.goclear_beta_journey_projection as p (
    tester_invite_id, tester_display_name, tester_email_hash, lead_id, client_id,
    current_stage, invite_status, funnel_started, account_created, portal_entered,
    upload_status, evaluation_status, clyde_status, report_status, review_status,
    followup_status, followup_provider_message_id, feedback_status, completion_status,
    last_activity_at, blocking_issue, ray_action_required, metadata, updated_at
  ) values (
    u.id, u.tester_name, encode(digest(lower(l.email), 'sha256'), 'hex'), l.id, p_client_id,
    case when f.id is not null then 'feedback_submitted'
      when coalesce(m.delivery_status,'') = 'DELIVERED' then 'followup_delivered'
      when m.email_message_id is not null then 'followup_pending'
      when i.id is not null then 'review_requested'
      when rv.id is not null then 'report_ready'
      when rp.id is not null then 'clyde_guidance'
      when s.id is not null then 'evaluation_complete'
      when c.id is not null then 'document_uploaded'
      when l.status in ('account_created','portal_started','completed') then 'portal_entered'
      else 'lead_captured' end,
    u.invitation_status, true, l.auth_user_id is not null, l.auth_user_id is not null,
    coalesce(c.processing_status,'not_started'), case when s.id is null then 'not_started' else 'complete' end,
    case when rp.id is null then 'not_started' else rp.status end,
    coalesce(rv.status,'not_started'), case when i.id is null then 'not_started' else i.status end,
    case when m.email_message_id is null then 'not_started' when coalesce(m.delivery_status,'') = 'DELIVERED' then 'delivered' else coalesce(m.send_status,'queued') end,
    coalesce(m.provider_message_id, m.job_provider_id), case when f.id is null then 'not_started' else f.status end,
    case when f.id is not null then 'complete' else 'in_progress' end,
    greatest(coalesce(f.created_at,'epoch'::timestamptz), coalesce(m.created_at,'epoch'::timestamptz), coalesce(i.created_at,'epoch'::timestamptz), coalesce(rv.created_at,'epoch'::timestamptz), coalesce(rp.created_at,'epoch'::timestamptz), coalesce(c.created_at,'epoch'::timestamptz), l.updated_at),
    case when coalesce(m.delivery_status,'') in ('BOUNCED','FAILED') then 'followup_delivery_failed'
      when i.id is not null and coalesce(i.status,'') = 'pending_admin_review' then 'admin_review_pending'
      when c.id is not null and c.processing_status = 'failed' then 'document_processing_failed' else null end,
    (i.id is not null and coalesce(i.status,'') = 'pending_admin_review'),
    jsonb_build_object('funnel_id', l.funnel_id, 'campaign_id', l.campaign_id, 'variant', l.variant, 'beta_mode', l.beta_mode), now()
  ) on conflict (client_id) do update set
    tester_invite_id=excluded.tester_invite_id, tester_display_name=excluded.tester_display_name,
    tester_email_hash=excluded.tester_email_hash, lead_id=excluded.lead_id, current_stage=excluded.current_stage,
    invite_status=excluded.invite_status, funnel_started=excluded.funnel_started, account_created=excluded.account_created,
    portal_entered=excluded.portal_entered, upload_status=excluded.upload_status, evaluation_status=excluded.evaluation_status,
    clyde_status=excluded.clyde_status, report_status=excluded.report_status, review_status=excluded.review_status,
    followup_status=excluded.followup_status, followup_provider_message_id=excluded.followup_provider_message_id,
    feedback_status=excluded.feedback_status, completion_status=excluded.completion_status, last_activity_at=excluded.last_activity_at,
    blocking_issue=excluded.blocking_issue, ray_action_required=excluded.ray_action_required, metadata=excluded.metadata, updated_at=now()
  returning * into r;
  return r;
end;
$$;
revoke all on function public.goclear_refresh_beta_journey_projection(text) from public;
grant execute on function public.goclear_refresh_beta_journey_projection(text) to service_role;

create or replace function public.goclear_create_review_request(
  p_tenant_id text,
  p_client_id text,
  p_title text default 'GoClear readiness review requested',
  p_notes text default null,
  p_readiness_snapshot jsonb default '{}'::jsonb
) returns public.client_tasks
language plpgsql security definer set search_path = public
as $$
declare result_row public.client_tasks;
begin
  if not exists (select 1 from public.tenant_memberships tm where tm.tenant_id=p_tenant_id and tm.client_id=p_client_id and tm.user_id=auth.uid() and tm.role='client') then
    raise exception 'client_context_required';
  end if;
  insert into public.client_tasks(id, tenant_id, client_id, title, summary, category, status, priority, client_visible, approval_required, source, payload)
  values (gen_random_uuid()::text, p_tenant_id, p_client_id, left(coalesce(p_title,'GoClear readiness review requested'),200), left(coalesce(p_notes,''),4000), 'review_request', 'pending_admin_review', 'high', true, true, 'goclear_friends_beta', jsonb_build_object('readiness_snapshot',p_readiness_snapshot,'notes',p_notes,'requested_by',auth.uid(),'department_owner','credit_funding','customer_response_required',true))
  returning * into result_row;
  insert into public.goclear_followup_jobs(client_id, tenant_id, work_id, trigger_event)
  values (p_client_id, p_tenant_id, result_row.id, 'review_requested')
  on conflict (work_id) do nothing;
  return result_row;
end;
$$;
revoke all on function public.goclear_create_review_request(text,text,text,text,jsonb) from public;
grant execute on function public.goclear_create_review_request(text,text,text,text,jsonb) to authenticated;

commit;
