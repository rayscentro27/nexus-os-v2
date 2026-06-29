-- DRAFT ONLY: review, rename with timestamp, and approve before applying.
-- Additive core client portal schema; no DROP/TRUNCATE/destructive statements.
begin;

create table if not exists public.tenant_memberships (tenant_id text not null, user_id uuid not null references auth.users(id) on delete cascade, role text not null check (role in ('admin','operator','client')), client_id text, created_at timestamptz not null default now(), primary key (tenant_id,user_id));

create table if not exists public.client_profiles (
  id text primary key,
  tenant_id text not null,
  client_id text,
  category text,
  title text,
  summary text,
  status text not null default 'open',
  score numeric,
  priority text,
  risk_level text,
  automation_level text,
  client_visible boolean not null default false,
  approval_required boolean not null default false,
  goclear_review_status text,
  source text,
  source_concept text,
  recommended_next_action text,
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists client_profiles_tenant_client_idx on public.client_profiles(tenant_id,client_id);
alter table public.client_profiles enable row level security;
create policy "client_profiles_tenant_select" on public.client_profiles for select using (exists (select 1 from public.tenant_memberships tm where tm.tenant_id=client_profiles.tenant_id and tm.user_id=auth.uid() and (tm.role in ('admin','operator') or (tm.role='client' and tm.client_id=client_profiles.client_id and client_profiles.client_visible))));
create policy "client_profiles_operator_write" on public.client_profiles for all using (exists (select 1 from public.tenant_memberships tm where tm.tenant_id=client_profiles.tenant_id and tm.user_id=auth.uid() and tm.role in ('admin','operator'))) with check (exists (select 1 from public.tenant_memberships tm where tm.tenant_id=client_profiles.tenant_id and tm.user_id=auth.uid() and tm.role in ('admin','operator')));

create table if not exists public.client_tasks (
  id text primary key,
  tenant_id text not null,
  client_id text,
  category text,
  title text,
  summary text,
  status text not null default 'open',
  score numeric,
  priority text,
  risk_level text,
  automation_level text,
  client_visible boolean not null default false,
  approval_required boolean not null default false,
  goclear_review_status text,
  source text,
  source_concept text,
  recommended_next_action text,
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists client_tasks_tenant_client_idx on public.client_tasks(tenant_id,client_id);
alter table public.client_tasks enable row level security;
create policy "client_tasks_tenant_select" on public.client_tasks for select using (exists (select 1 from public.tenant_memberships tm where tm.tenant_id=client_tasks.tenant_id and tm.user_id=auth.uid() and (tm.role in ('admin','operator') or (tm.role='client' and tm.client_id=client_tasks.client_id and client_tasks.client_visible))));
create policy "client_tasks_operator_write" on public.client_tasks for all using (exists (select 1 from public.tenant_memberships tm where tm.tenant_id=client_tasks.tenant_id and tm.user_id=auth.uid() and tm.role in ('admin','operator'))) with check (exists (select 1 from public.tenant_memberships tm where tm.tenant_id=client_tasks.tenant_id and tm.user_id=auth.uid() and tm.role in ('admin','operator')));

create table if not exists public.client_documents (
  id text primary key,
  tenant_id text not null,
  client_id text,
  category text,
  title text,
  summary text,
  status text not null default 'open',
  score numeric,
  priority text,
  risk_level text,
  automation_level text,
  client_visible boolean not null default false,
  approval_required boolean not null default false,
  goclear_review_status text,
  source text,
  source_concept text,
  recommended_next_action text,
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists client_documents_tenant_client_idx on public.client_documents(tenant_id,client_id);
alter table public.client_documents enable row level security;
create policy "client_documents_tenant_select" on public.client_documents for select using (exists (select 1 from public.tenant_memberships tm where tm.tenant_id=client_documents.tenant_id and tm.user_id=auth.uid() and (tm.role in ('admin','operator') or (tm.role='client' and tm.client_id=client_documents.client_id and client_documents.client_visible))));
create policy "client_documents_operator_write" on public.client_documents for all using (exists (select 1 from public.tenant_memberships tm where tm.tenant_id=client_documents.tenant_id and tm.user_id=auth.uid() and tm.role in ('admin','operator'))) with check (exists (select 1 from public.tenant_memberships tm where tm.tenant_id=client_documents.tenant_id and tm.user_id=auth.uid() and tm.role in ('admin','operator')));

create table if not exists public.readiness_scores (
  id text primary key,
  tenant_id text not null,
  client_id text,
  category text,
  title text,
  summary text,
  status text not null default 'open',
  score numeric,
  priority text,
  risk_level text,
  automation_level text,
  client_visible boolean not null default false,
  approval_required boolean not null default false,
  goclear_review_status text,
  source text,
  source_concept text,
  recommended_next_action text,
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists readiness_scores_tenant_client_idx on public.readiness_scores(tenant_id,client_id);
alter table public.readiness_scores enable row level security;
create policy "readiness_scores_tenant_select" on public.readiness_scores for select using (exists (select 1 from public.tenant_memberships tm where tm.tenant_id=readiness_scores.tenant_id and tm.user_id=auth.uid() and (tm.role in ('admin','operator') or (tm.role='client' and tm.client_id=readiness_scores.client_id and readiness_scores.client_visible))));
create policy "readiness_scores_operator_write" on public.readiness_scores for all using (exists (select 1 from public.tenant_memberships tm where tm.tenant_id=readiness_scores.tenant_id and tm.user_id=auth.uid() and tm.role in ('admin','operator'))) with check (exists (select 1 from public.tenant_memberships tm where tm.tenant_id=readiness_scores.tenant_id and tm.user_id=auth.uid() and tm.role in ('admin','operator')));

create table if not exists public.credit_workflow_items (
  id text primary key,
  tenant_id text not null,
  client_id text,
  category text,
  title text,
  summary text,
  status text not null default 'open',
  score numeric,
  priority text,
  risk_level text,
  automation_level text,
  client_visible boolean not null default false,
  approval_required boolean not null default false,
  goclear_review_status text,
  source text,
  source_concept text,
  recommended_next_action text,
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists credit_workflow_items_tenant_client_idx on public.credit_workflow_items(tenant_id,client_id);
alter table public.credit_workflow_items enable row level security;
create policy "credit_workflow_items_tenant_select" on public.credit_workflow_items for select using (exists (select 1 from public.tenant_memberships tm where tm.tenant_id=credit_workflow_items.tenant_id and tm.user_id=auth.uid() and (tm.role in ('admin','operator') or (tm.role='client' and tm.client_id=credit_workflow_items.client_id and credit_workflow_items.client_visible))));
create policy "credit_workflow_items_operator_write" on public.credit_workflow_items for all using (exists (select 1 from public.tenant_memberships tm where tm.tenant_id=credit_workflow_items.tenant_id and tm.user_id=auth.uid() and tm.role in ('admin','operator'))) with check (exists (select 1 from public.tenant_memberships tm where tm.tenant_id=credit_workflow_items.tenant_id and tm.user_id=auth.uid() and tm.role in ('admin','operator')));

create table if not exists public.dispute_cases (
  id text primary key,
  tenant_id text not null,
  client_id text,
  category text,
  title text,
  summary text,
  status text not null default 'open',
  score numeric,
  priority text,
  risk_level text,
  automation_level text,
  client_visible boolean not null default false,
  approval_required boolean not null default false,
  goclear_review_status text,
  source text,
  source_concept text,
  recommended_next_action text,
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists dispute_cases_tenant_client_idx on public.dispute_cases(tenant_id,client_id);
alter table public.dispute_cases enable row level security;
create policy "dispute_cases_tenant_select" on public.dispute_cases for select using (exists (select 1 from public.tenant_memberships tm where tm.tenant_id=dispute_cases.tenant_id and tm.user_id=auth.uid() and (tm.role in ('admin','operator') or (tm.role='client' and tm.client_id=dispute_cases.client_id and dispute_cases.client_visible))));
create policy "dispute_cases_operator_write" on public.dispute_cases for all using (exists (select 1 from public.tenant_memberships tm where tm.tenant_id=dispute_cases.tenant_id and tm.user_id=auth.uid() and tm.role in ('admin','operator'))) with check (exists (select 1 from public.tenant_memberships tm where tm.tenant_id=dispute_cases.tenant_id and tm.user_id=auth.uid() and tm.role in ('admin','operator')));

create table if not exists public.dispute_letter_drafts (
  id text primary key,
  tenant_id text not null,
  client_id text,
  category text,
  title text,
  summary text,
  status text not null default 'open',
  score numeric,
  priority text,
  risk_level text,
  automation_level text,
  client_visible boolean not null default false,
  approval_required boolean not null default false,
  goclear_review_status text,
  source text,
  source_concept text,
  recommended_next_action text,
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists dispute_letter_drafts_tenant_client_idx on public.dispute_letter_drafts(tenant_id,client_id);
alter table public.dispute_letter_drafts enable row level security;
create policy "dispute_letter_drafts_tenant_select" on public.dispute_letter_drafts for select using (exists (select 1 from public.tenant_memberships tm where tm.tenant_id=dispute_letter_drafts.tenant_id and tm.user_id=auth.uid() and (tm.role in ('admin','operator') or (tm.role='client' and tm.client_id=dispute_letter_drafts.client_id and dispute_letter_drafts.client_visible))));
create policy "dispute_letter_drafts_operator_write" on public.dispute_letter_drafts for all using (exists (select 1 from public.tenant_memberships tm where tm.tenant_id=dispute_letter_drafts.tenant_id and tm.user_id=auth.uid() and tm.role in ('admin','operator'))) with check (exists (select 1 from public.tenant_memberships tm where tm.tenant_id=dispute_letter_drafts.tenant_id and tm.user_id=auth.uid() and tm.role in ('admin','operator')));

create table if not exists public.business_profile_requirements (
  id text primary key,
  tenant_id text not null,
  client_id text,
  category text,
  title text,
  summary text,
  status text not null default 'open',
  score numeric,
  priority text,
  risk_level text,
  automation_level text,
  client_visible boolean not null default false,
  approval_required boolean not null default false,
  goclear_review_status text,
  source text,
  source_concept text,
  recommended_next_action text,
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists business_profile_requirements_tenant_client_idx on public.business_profile_requirements(tenant_id,client_id);
alter table public.business_profile_requirements enable row level security;
create policy "business_profile_requirements_tenant_select" on public.business_profile_requirements for select using (exists (select 1 from public.tenant_memberships tm where tm.tenant_id=business_profile_requirements.tenant_id and tm.user_id=auth.uid() and (tm.role in ('admin','operator') or (tm.role='client' and tm.client_id=business_profile_requirements.client_id and business_profile_requirements.client_visible))));
create policy "business_profile_requirements_operator_write" on public.business_profile_requirements for all using (exists (select 1 from public.tenant_memberships tm where tm.tenant_id=business_profile_requirements.tenant_id and tm.user_id=auth.uid() and tm.role in ('admin','operator'))) with check (exists (select 1 from public.tenant_memberships tm where tm.tenant_id=business_profile_requirements.tenant_id and tm.user_id=auth.uid() and tm.role in ('admin','operator')));

create table if not exists public.funding_readiness_scores (
  id text primary key,
  tenant_id text not null,
  client_id text,
  category text,
  title text,
  summary text,
  status text not null default 'open',
  score numeric,
  priority text,
  risk_level text,
  automation_level text,
  client_visible boolean not null default false,
  approval_required boolean not null default false,
  goclear_review_status text,
  source text,
  source_concept text,
  recommended_next_action text,
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists funding_readiness_scores_tenant_client_idx on public.funding_readiness_scores(tenant_id,client_id);
alter table public.funding_readiness_scores enable row level security;
create policy "funding_readiness_scores_tenant_select" on public.funding_readiness_scores for select using (exists (select 1 from public.tenant_memberships tm where tm.tenant_id=funding_readiness_scores.tenant_id and tm.user_id=auth.uid() and (tm.role in ('admin','operator') or (tm.role='client' and tm.client_id=funding_readiness_scores.client_id and funding_readiness_scores.client_visible))));
create policy "funding_readiness_scores_operator_write" on public.funding_readiness_scores for all using (exists (select 1 from public.tenant_memberships tm where tm.tenant_id=funding_readiness_scores.tenant_id and tm.user_id=auth.uid() and tm.role in ('admin','operator'))) with check (exists (select 1 from public.tenant_memberships tm where tm.tenant_id=funding_readiness_scores.tenant_id and tm.user_id=auth.uid() and tm.role in ('admin','operator')));

create table if not exists public.business_opportunities (
  id text primary key,
  tenant_id text not null,
  client_id text,
  category text,
  title text,
  summary text,
  status text not null default 'open',
  score numeric,
  priority text,
  risk_level text,
  automation_level text,
  client_visible boolean not null default false,
  approval_required boolean not null default false,
  goclear_review_status text,
  source text,
  source_concept text,
  recommended_next_action text,
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists business_opportunities_tenant_client_idx on public.business_opportunities(tenant_id,client_id);
alter table public.business_opportunities enable row level security;
create policy "business_opportunities_tenant_select" on public.business_opportunities for select using (exists (select 1 from public.tenant_memberships tm where tm.tenant_id=business_opportunities.tenant_id and tm.user_id=auth.uid() and (tm.role in ('admin','operator') or (tm.role='client' and tm.client_id=business_opportunities.client_id and business_opportunities.client_visible))));
create policy "business_opportunities_operator_write" on public.business_opportunities for all using (exists (select 1 from public.tenant_memberships tm where tm.tenant_id=business_opportunities.tenant_id and tm.user_id=auth.uid() and tm.role in ('admin','operator'))) with check (exists (select 1 from public.tenant_memberships tm where tm.tenant_id=business_opportunities.tenant_id and tm.user_id=auth.uid() and tm.role in ('admin','operator')));

create table if not exists public.partner_offers (
  id text primary key,
  tenant_id text not null,
  client_id text,
  category text,
  title text,
  summary text,
  status text not null default 'open',
  score numeric,
  priority text,
  risk_level text,
  automation_level text,
  client_visible boolean not null default false,
  approval_required boolean not null default false,
  goclear_review_status text,
  source text,
  source_concept text,
  recommended_next_action text,
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists partner_offers_tenant_client_idx on public.partner_offers(tenant_id,client_id);
alter table public.partner_offers enable row level security;
create policy "partner_offers_tenant_select" on public.partner_offers for select using (exists (select 1 from public.tenant_memberships tm where tm.tenant_id=partner_offers.tenant_id and tm.user_id=auth.uid() and (tm.role in ('admin','operator') or (tm.role='client' and tm.client_id=partner_offers.client_id and partner_offers.client_visible))));
create policy "partner_offers_operator_write" on public.partner_offers for all using (exists (select 1 from public.tenant_memberships tm where tm.tenant_id=partner_offers.tenant_id and tm.user_id=auth.uid() and tm.role in ('admin','operator'))) with check (exists (select 1 from public.tenant_memberships tm where tm.tenant_id=partner_offers.tenant_id and tm.user_id=auth.uid() and tm.role in ('admin','operator')));

create table if not exists public.approval_cards (
  id text primary key,
  tenant_id text not null,
  client_id text,
  category text,
  title text,
  summary text,
  status text not null default 'open',
  score numeric,
  priority text,
  risk_level text,
  automation_level text,
  client_visible boolean not null default false,
  approval_required boolean not null default false,
  goclear_review_status text,
  source text,
  source_concept text,
  recommended_next_action text,
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists approval_cards_tenant_client_idx on public.approval_cards(tenant_id,client_id);
alter table public.approval_cards enable row level security;
create policy "approval_cards_tenant_select" on public.approval_cards for select using (exists (select 1 from public.tenant_memberships tm where tm.tenant_id=approval_cards.tenant_id and tm.user_id=auth.uid() and (tm.role in ('admin','operator') or (tm.role='client' and tm.client_id=approval_cards.client_id and approval_cards.client_visible))));
create policy "approval_cards_operator_write" on public.approval_cards for all using (exists (select 1 from public.tenant_memberships tm where tm.tenant_id=approval_cards.tenant_id and tm.user_id=auth.uid() and tm.role in ('admin','operator'))) with check (exists (select 1 from public.tenant_memberships tm where tm.tenant_id=approval_cards.tenant_id and tm.user_id=auth.uid() and tm.role in ('admin','operator')));

create table if not exists public.admin_review_queue (
  id text primary key,
  tenant_id text not null,
  client_id text,
  category text,
  title text,
  summary text,
  status text not null default 'open',
  score numeric,
  priority text,
  risk_level text,
  automation_level text,
  client_visible boolean not null default false,
  approval_required boolean not null default false,
  goclear_review_status text,
  source text,
  source_concept text,
  recommended_next_action text,
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists admin_review_queue_tenant_client_idx on public.admin_review_queue(tenant_id,client_id);
alter table public.admin_review_queue enable row level security;
create policy "admin_review_queue_tenant_select" on public.admin_review_queue for select using (exists (select 1 from public.tenant_memberships tm where tm.tenant_id=admin_review_queue.tenant_id and tm.user_id=auth.uid() and (tm.role in ('admin','operator') or (tm.role='client' and tm.client_id=admin_review_queue.client_id and admin_review_queue.client_visible))));
create policy "admin_review_queue_operator_write" on public.admin_review_queue for all using (exists (select 1 from public.tenant_memberships tm where tm.tenant_id=admin_review_queue.tenant_id and tm.user_id=auth.uid() and tm.role in ('admin','operator'))) with check (exists (select 1 from public.tenant_memberships tm where tm.tenant_id=admin_review_queue.tenant_id and tm.user_id=auth.uid() and tm.role in ('admin','operator')));

create table if not exists public.approved_client_guidance (
  id text primary key,
  tenant_id text not null,
  client_id text,
  category text,
  title text,
  summary text,
  status text not null default 'open',
  score numeric,
  priority text,
  risk_level text,
  automation_level text,
  client_visible boolean not null default false,
  approval_required boolean not null default false,
  goclear_review_status text,
  source text,
  source_concept text,
  recommended_next_action text,
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists approved_client_guidance_tenant_client_idx on public.approved_client_guidance(tenant_id,client_id);
alter table public.approved_client_guidance enable row level security;
create policy "approved_client_guidance_tenant_select" on public.approved_client_guidance for select using (exists (select 1 from public.tenant_memberships tm where tm.tenant_id=approved_client_guidance.tenant_id and tm.user_id=auth.uid() and (tm.role in ('admin','operator') or (tm.role='client' and tm.client_id=approved_client_guidance.client_id and approved_client_guidance.client_visible))));
create policy "approved_client_guidance_operator_write" on public.approved_client_guidance for all using (exists (select 1 from public.tenant_memberships tm where tm.tenant_id=approved_client_guidance.tenant_id and tm.user_id=auth.uid() and tm.role in ('admin','operator'))) with check (exists (select 1 from public.tenant_memberships tm where tm.tenant_id=approved_client_guidance.tenant_id and tm.user_id=auth.uid() and tm.role in ('admin','operator')));

create table if not exists public.client_questions (
  id text primary key,
  tenant_id text not null,
  client_id text,
  category text,
  title text,
  summary text,
  status text not null default 'open',
  score numeric,
  priority text,
  risk_level text,
  automation_level text,
  client_visible boolean not null default false,
  approval_required boolean not null default false,
  goclear_review_status text,
  source text,
  source_concept text,
  recommended_next_action text,
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists client_questions_tenant_client_idx on public.client_questions(tenant_id,client_id);
alter table public.client_questions enable row level security;
create policy "client_questions_tenant_select" on public.client_questions for select using (exists (select 1 from public.tenant_memberships tm where tm.tenant_id=client_questions.tenant_id and tm.user_id=auth.uid() and (tm.role in ('admin','operator') or (tm.role='client' and tm.client_id=client_questions.client_id and client_questions.client_visible))));
create policy "client_questions_operator_write" on public.client_questions for all using (exists (select 1 from public.tenant_memberships tm where tm.tenant_id=client_questions.tenant_id and tm.user_id=auth.uid() and tm.role in ('admin','operator'))) with check (exists (select 1 from public.tenant_memberships tm where tm.tenant_id=client_questions.tenant_id and tm.user_id=auth.uid() and tm.role in ('admin','operator')));

create table if not exists public.client_escalations (
  id text primary key,
  tenant_id text not null,
  client_id text,
  category text,
  title text,
  summary text,
  status text not null default 'open',
  score numeric,
  priority text,
  risk_level text,
  automation_level text,
  client_visible boolean not null default false,
  approval_required boolean not null default false,
  goclear_review_status text,
  source text,
  source_concept text,
  recommended_next_action text,
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists client_escalations_tenant_client_idx on public.client_escalations(tenant_id,client_id);
alter table public.client_escalations enable row level security;
create policy "client_escalations_tenant_select" on public.client_escalations for select using (exists (select 1 from public.tenant_memberships tm where tm.tenant_id=client_escalations.tenant_id and tm.user_id=auth.uid() and (tm.role in ('admin','operator') or (tm.role='client' and tm.client_id=client_escalations.client_id and client_escalations.client_visible))));
create policy "client_escalations_operator_write" on public.client_escalations for all using (exists (select 1 from public.tenant_memberships tm where tm.tenant_id=client_escalations.tenant_id and tm.user_id=auth.uid() and tm.role in ('admin','operator'))) with check (exists (select 1 from public.tenant_memberships tm where tm.tenant_id=client_escalations.tenant_id and tm.user_id=auth.uid() and tm.role in ('admin','operator')));

create table if not exists public.proof_events (
  id text primary key,
  tenant_id text not null,
  client_id text,
  category text,
  title text,
  summary text,
  status text not null default 'open',
  score numeric,
  priority text,
  risk_level text,
  automation_level text,
  client_visible boolean not null default false,
  approval_required boolean not null default false,
  goclear_review_status text,
  source text,
  source_concept text,
  recommended_next_action text,
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists proof_events_tenant_client_idx on public.proof_events(tenant_id,client_id);
alter table public.proof_events enable row level security;
create policy "proof_events_tenant_select" on public.proof_events for select using (exists (select 1 from public.tenant_memberships tm where tm.tenant_id=proof_events.tenant_id and tm.user_id=auth.uid() and (tm.role in ('admin','operator') or (tm.role='client' and tm.client_id=proof_events.client_id and proof_events.client_visible))));
create policy "proof_events_operator_write" on public.proof_events for all using (exists (select 1 from public.tenant_memberships tm where tm.tenant_id=proof_events.tenant_id and tm.user_id=auth.uid() and tm.role in ('admin','operator'))) with check (exists (select 1 from public.tenant_memberships tm where tm.tenant_id=proof_events.tenant_id and tm.user_id=auth.uid() and tm.role in ('admin','operator')));

create table if not exists public.connector_health (
  id text primary key,
  tenant_id text not null,
  client_id text,
  category text,
  title text,
  summary text,
  status text not null default 'open',
  score numeric,
  priority text,
  risk_level text,
  automation_level text,
  client_visible boolean not null default false,
  approval_required boolean not null default false,
  goclear_review_status text,
  source text,
  source_concept text,
  recommended_next_action text,
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists connector_health_tenant_client_idx on public.connector_health(tenant_id,client_id);
alter table public.connector_health enable row level security;
create policy "connector_health_tenant_select" on public.connector_health for select using (exists (select 1 from public.tenant_memberships tm where tm.tenant_id=connector_health.tenant_id and tm.user_id=auth.uid() and (tm.role in ('admin','operator') or (tm.role='client' and tm.client_id=connector_health.client_id and connector_health.client_visible))));
create policy "connector_health_operator_write" on public.connector_health for all using (exists (select 1 from public.tenant_memberships tm where tm.tenant_id=connector_health.tenant_id and tm.user_id=auth.uid() and tm.role in ('admin','operator'))) with check (exists (select 1 from public.tenant_memberships tm where tm.tenant_id=connector_health.tenant_id and tm.user_id=auth.uid() and tm.role in ('admin','operator')));

create table if not exists public.engine_runs (
  id text primary key,
  tenant_id text not null,
  client_id text,
  category text,
  title text,
  summary text,
  status text not null default 'open',
  score numeric,
  priority text,
  risk_level text,
  automation_level text,
  client_visible boolean not null default false,
  approval_required boolean not null default false,
  goclear_review_status text,
  source text,
  source_concept text,
  recommended_next_action text,
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists engine_runs_tenant_client_idx on public.engine_runs(tenant_id,client_id);
alter table public.engine_runs enable row level security;
create policy "engine_runs_tenant_select" on public.engine_runs for select using (exists (select 1 from public.tenant_memberships tm where tm.tenant_id=engine_runs.tenant_id and tm.user_id=auth.uid() and (tm.role in ('admin','operator') or (tm.role='client' and tm.client_id=engine_runs.client_id and engine_runs.client_visible))));
create policy "engine_runs_operator_write" on public.engine_runs for all using (exists (select 1 from public.tenant_memberships tm where tm.tenant_id=engine_runs.tenant_id and tm.user_id=auth.uid() and tm.role in ('admin','operator'))) with check (exists (select 1 from public.tenant_memberships tm where tm.tenant_id=engine_runs.tenant_id and tm.user_id=auth.uid() and tm.role in ('admin','operator')));

create table if not exists public.youtube_sources (
  id text primary key,
  tenant_id text not null,
  client_id text,
  category text,
  title text,
  summary text,
  status text not null default 'open',
  score numeric,
  priority text,
  risk_level text,
  automation_level text,
  client_visible boolean not null default false,
  approval_required boolean not null default false,
  goclear_review_status text,
  source text,
  source_concept text,
  recommended_next_action text,
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists youtube_sources_tenant_client_idx on public.youtube_sources(tenant_id,client_id);
alter table public.youtube_sources enable row level security;
create policy "youtube_sources_tenant_select" on public.youtube_sources for select using (exists (select 1 from public.tenant_memberships tm where tm.tenant_id=youtube_sources.tenant_id and tm.user_id=auth.uid() and (tm.role in ('admin','operator') or (tm.role='client' and tm.client_id=youtube_sources.client_id and youtube_sources.client_visible))));
create policy "youtube_sources_operator_write" on public.youtube_sources for all using (exists (select 1 from public.tenant_memberships tm where tm.tenant_id=youtube_sources.tenant_id and tm.user_id=auth.uid() and tm.role in ('admin','operator'))) with check (exists (select 1 from public.tenant_memberships tm where tm.tenant_id=youtube_sources.tenant_id and tm.user_id=auth.uid() and tm.role in ('admin','operator')));

create table if not exists public.youtube_review_items (
  id text primary key,
  tenant_id text not null,
  client_id text,
  category text,
  title text,
  summary text,
  status text not null default 'open',
  score numeric,
  priority text,
  risk_level text,
  automation_level text,
  client_visible boolean not null default false,
  approval_required boolean not null default false,
  goclear_review_status text,
  source text,
  source_concept text,
  recommended_next_action text,
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists youtube_review_items_tenant_client_idx on public.youtube_review_items(tenant_id,client_id);
alter table public.youtube_review_items enable row level security;
create policy "youtube_review_items_tenant_select" on public.youtube_review_items for select using (exists (select 1 from public.tenant_memberships tm where tm.tenant_id=youtube_review_items.tenant_id and tm.user_id=auth.uid() and (tm.role in ('admin','operator') or (tm.role='client' and tm.client_id=youtube_review_items.client_id and youtube_review_items.client_visible))));
create policy "youtube_review_items_operator_write" on public.youtube_review_items for all using (exists (select 1 from public.tenant_memberships tm where tm.tenant_id=youtube_review_items.tenant_id and tm.user_id=auth.uid() and tm.role in ('admin','operator'))) with check (exists (select 1 from public.tenant_memberships tm where tm.tenant_id=youtube_review_items.tenant_id and tm.user_id=auth.uid() and tm.role in ('admin','operator')));

create table if not exists public.social_drafts (
  id text primary key,
  tenant_id text not null,
  client_id text,
  category text,
  title text,
  summary text,
  status text not null default 'open',
  score numeric,
  priority text,
  risk_level text,
  automation_level text,
  client_visible boolean not null default false,
  approval_required boolean not null default false,
  goclear_review_status text,
  source text,
  source_concept text,
  recommended_next_action text,
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists social_drafts_tenant_client_idx on public.social_drafts(tenant_id,client_id);
alter table public.social_drafts enable row level security;
create policy "social_drafts_tenant_select" on public.social_drafts for select using (exists (select 1 from public.tenant_memberships tm where tm.tenant_id=social_drafts.tenant_id and tm.user_id=auth.uid() and (tm.role in ('admin','operator') or (tm.role='client' and tm.client_id=social_drafts.client_id and social_drafts.client_visible))));
create policy "social_drafts_operator_write" on public.social_drafts for all using (exists (select 1 from public.tenant_memberships tm where tm.tenant_id=social_drafts.tenant_id and tm.user_id=auth.uid() and tm.role in ('admin','operator'))) with check (exists (select 1 from public.tenant_memberships tm where tm.tenant_id=social_drafts.tenant_id and tm.user_id=auth.uid() and tm.role in ('admin','operator')));

create table if not exists public.subscription_memberships (
  id text primary key,
  tenant_id text not null,
  client_id text,
  category text,
  title text,
  summary text,
  status text not null default 'open',
  score numeric,
  priority text,
  risk_level text,
  automation_level text,
  client_visible boolean not null default false,
  approval_required boolean not null default false,
  goclear_review_status text,
  source text,
  source_concept text,
  recommended_next_action text,
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists subscription_memberships_tenant_client_idx on public.subscription_memberships(tenant_id,client_id);
alter table public.subscription_memberships enable row level security;
create policy "subscription_memberships_tenant_select" on public.subscription_memberships for select using (exists (select 1 from public.tenant_memberships tm where tm.tenant_id=subscription_memberships.tenant_id and tm.user_id=auth.uid() and (tm.role in ('admin','operator') or (tm.role='client' and tm.client_id=subscription_memberships.client_id and subscription_memberships.client_visible))));
create policy "subscription_memberships_operator_write" on public.subscription_memberships for all using (exists (select 1 from public.tenant_memberships tm where tm.tenant_id=subscription_memberships.tenant_id and tm.user_id=auth.uid() and tm.role in ('admin','operator'))) with check (exists (select 1 from public.tenant_memberships tm where tm.tenant_id=subscription_memberships.tenant_id and tm.user_id=auth.uid() and tm.role in ('admin','operator')));

create table if not exists public.payments_status (
  id text primary key,
  tenant_id text not null,
  client_id text,
  category text,
  title text,
  summary text,
  status text not null default 'open',
  score numeric,
  priority text,
  risk_level text,
  automation_level text,
  client_visible boolean not null default false,
  approval_required boolean not null default false,
  goclear_review_status text,
  source text,
  source_concept text,
  recommended_next_action text,
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists payments_status_tenant_client_idx on public.payments_status(tenant_id,client_id);
alter table public.payments_status enable row level security;
create policy "payments_status_tenant_select" on public.payments_status for select using (exists (select 1 from public.tenant_memberships tm where tm.tenant_id=payments_status.tenant_id and tm.user_id=auth.uid() and (tm.role in ('admin','operator') or (tm.role='client' and tm.client_id=payments_status.client_id and payments_status.client_visible))));
create policy "payments_status_operator_write" on public.payments_status for all using (exists (select 1 from public.tenant_memberships tm where tm.tenant_id=payments_status.tenant_id and tm.user_id=auth.uid() and tm.role in ('admin','operator'))) with check (exists (select 1 from public.tenant_memberships tm where tm.tenant_id=payments_status.tenant_id and tm.user_id=auth.uid() and tm.role in ('admin','operator')));

alter table public.tenant_memberships enable row level security;
create policy "memberships_self_select" on public.tenant_memberships for select using (user_id=auth.uid());

-- Private storage bucket and storage.objects policies require separate review and are intentionally not auto-created.
commit;
