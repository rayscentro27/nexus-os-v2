-- Fix the portable pgcrypto digest invocation used by the beta projection.
begin;
create or replace function public.goclear_refresh_beta_journey_projection(p_client_id text)
returns public.goclear_beta_journey_projection
language plpgsql security definer set search_path = public
as $$
declare r public.goclear_beta_journey_projection; l public.goclear_leads; u record; c record; s record; rp record; rv record; f record; m record; i record;
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
  select mm.*, gj.status as job_status, gj.provider_message_id as job_provider_id into m from public.marketing_email_messages mm left join public.goclear_followup_jobs gj on gj.email_message_id = mm.email_message_id where mm.lead_id = l.id::text and mm.message_type in ('NURTURE','TRANSACTIONAL','TEST') order by mm.created_at desc limit 1;
  insert into public.goclear_beta_journey_projection as p (tester_invite_id,tester_display_name,tester_email_hash,lead_id,client_id,current_stage,invite_status,funnel_started,account_created,portal_entered,upload_status,evaluation_status,clyde_status,report_status,review_status,followup_status,followup_provider_message_id,feedback_status,completion_status,last_activity_at,blocking_issue,ray_action_required,metadata,updated_at)
  values (u.id,u.tester_name,encode(digest(convert_to(lower(l.email),'UTF8'),'sha256'),'hex'),l.id,p_client_id,
    case when f.id is not null then 'feedback_submitted' when coalesce(m.delivery_status,'')='DELIVERED' then 'followup_delivered' when m.email_message_id is not null then 'followup_pending' when i.id is not null then 'review_requested' when rv.id is not null then 'report_ready' when rp.id is not null then 'clyde_guidance' when s.id is not null then 'evaluation_complete' when c.id is not null then 'document_uploaded' when l.status in ('account_created','portal_started','completed') then 'portal_entered' else 'lead_captured' end,
    u.invitation_status,true,l.auth_user_id is not null,l.auth_user_id is not null,coalesce(c.processing_status,'not_started'),case when s.id is null then 'not_started' else 'complete' end,case when rp.id is null then 'not_started' else rp.status end,coalesce(rv.status,'not_started'),case when i.id is null then 'not_started' else i.status end,case when m.email_message_id is null then 'not_started' when coalesce(m.delivery_status,'')='DELIVERED' then 'delivered' else coalesce(m.send_status,'queued') end,coalesce(m.provider_message_id,m.job_provider_id),case when f.id is null then 'not_started' else f.status end,case when f.id is not null then 'complete' else 'in_progress' end,greatest(coalesce(f.created_at,'epoch'::timestamptz),coalesce(m.created_at,'epoch'::timestamptz),coalesce(i.created_at,'epoch'::timestamptz),coalesce(rv.created_at,'epoch'::timestamptz),coalesce(rp.created_at,'epoch'::timestamptz),coalesce(c.created_at,'epoch'::timestamptz),l.updated_at),case when coalesce(m.delivery_status,'') in ('BOUNCED','FAILED') then 'followup_delivery_failed' when i.id is not null and coalesce(i.status,'')='pending_admin_review' then 'admin_review_pending' when c.id is not null and c.processing_status='failed' then 'document_processing_failed' else null end,(i.id is not null and coalesce(i.status,'')='pending_admin_review'),jsonb_build_object('funnel_id',l.funnel_id,'campaign_id',l.campaign_id,'variant',l.variant,'beta_mode',l.beta_mode),now())
  on conflict (client_id) do update set tester_invite_id=excluded.tester_invite_id,tester_display_name=excluded.tester_display_name,tester_email_hash=excluded.tester_email_hash,lead_id=excluded.lead_id,current_stage=excluded.current_stage,invite_status=excluded.invite_status,funnel_started=excluded.funnel_started,account_created=excluded.account_created,portal_entered=excluded.portal_entered,upload_status=excluded.upload_status,evaluation_status=excluded.evaluation_status,clyde_status=excluded.clyde_status,report_status=excluded.report_status,review_status=excluded.review_status,followup_status=excluded.followup_status,followup_provider_message_id=excluded.followup_provider_message_id,feedback_status=excluded.feedback_status,completion_status=excluded.completion_status,last_activity_at=excluded.last_activity_at,blocking_issue=excluded.blocking_issue,ray_action_required=excluded.ray_action_required,metadata=excluded.metadata,updated_at=now() returning * into r;
  return r;
end; $$;
revoke all on function public.goclear_refresh_beta_journey_projection(text) from public;
grant execute on function public.goclear_refresh_beta_journey_projection(text) to service_role;
commit;
