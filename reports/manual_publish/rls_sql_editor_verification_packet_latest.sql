-- READ-ONLY Nexus client RLS verification packet
select c.relname as table_name, c.relrowsecurity as rls_enabled, c.relforcerowsecurity as force_rls
from pg_class c join pg_namespace n on n.oid=c.relnamespace
where n.nspname='public' and c.relname in (
  'client_profiles','client_tasks','client_documents','readiness_scores','credit_workflow_items',
  'dispute_cases','dispute_letter_drafts','business_profile_requirements','funding_readiness_scores',
  'business_opportunities','partner_offers','approval_cards','admin_review_queue','approved_client_guidance',
  'client_questions','client_escalations','proof_events','connector_health','engine_runs','youtube_sources',
  'youtube_review_items','social_drafts','subscription_memberships','payments_status','tenant_memberships')
order by c.relname;

select schemaname, tablename, policyname, permissive, roles, cmd, qual, with_check
from pg_policies
where schemaname='public' and tablename in (
  'client_profiles','client_tasks','client_documents','readiness_scores','credit_workflow_items',
  'dispute_cases','dispute_letter_drafts','business_profile_requirements','funding_readiness_scores',
  'business_opportunities','partner_offers','approval_cards','admin_review_queue','approved_client_guidance',
  'client_questions','client_escalations','proof_events','connector_health','engine_runs','youtube_sources',
  'youtube_review_items','social_drafts','subscription_memberships','payments_status','tenant_memberships')
order by tablename, policyname;

-- Must return zero rows: public/anon or unconditional permissive access.
select schemaname, tablename, policyname, roles, cmd, qual, with_check
from pg_policies
where schemaname='public' and (
  roles && array['public','anon']::name[] or coalesce(qual,'') ~* '^\s*true\s*$' or coalesce(with_check,'') ~* '^\s*true\s*$');
