-- GoClear friends-beta closure. Additive only; reuses client_tasks,
-- client_documents, tester_invitations, tester_feedback, and the existing
-- client email/queue paths.
begin;

create extension if not exists pgcrypto;

create table if not exists public.goclear_leads (
  id uuid primary key default gen_random_uuid(),
  email text not null,
  name text,
  campaign_id text,
  funnel_id text not null default 'goclear_funding_readiness_funnel_v1',
  variant text,
  source text not null default 'goclear_funnel',
  beta_mode boolean not null default false,
  tester_invitation_id uuid references public.tester_invitations(id) on delete set null,
  auth_user_id uuid references auth.users(id) on delete set null,
  tenant_id text,
  client_id text,
  status text not null default 'captured' check (status in ('captured','account_created','portal_started','completed','suppressed','duplicate')),
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create unique index if not exists goclear_leads_email_campaign_uq on public.goclear_leads(lower(email), coalesce(campaign_id,''), coalesce(variant,''));
create index if not exists goclear_leads_client_idx on public.goclear_leads(client_id, created_at desc);

create table if not exists public.goclear_upload_receipts (
  id uuid primary key default gen_random_uuid(),
  client_id text not null,
  tenant_id text not null,
  document_id text not null,
  storage_object text not null,
  category text not null,
  processing_status text not null default 'uploaded' check (processing_status in ('uploaded','queued','processing','complete','failed','manual_review')),
  result_ref text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create index if not exists goclear_upload_receipts_client_idx on public.goclear_upload_receipts(client_id, created_at desc);

create table if not exists public.goclear_clyde_receipts (
  id uuid primary key default gen_random_uuid(),
  client_id text not null,
  input_context_hash text not null,
  research_refs jsonb not null default '[]'::jsonb,
  guidance text not null,
  provider text not null default 'client-ai-gateway',
  model text not null default 'TIER_0',
  status text not null default 'completed' check (status in ('completed','policy_denied','escalated','failed')),
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create index if not exists goclear_clyde_receipts_client_idx on public.goclear_clyde_receipts(client_id, created_at desc);

create table if not exists public.goclear_client_reports (
  id uuid primary key default gen_random_uuid(),
  client_id text not null,
  tenant_id text not null,
  report_version integer not null default 1,
  status text not null default 'draft' check (status in ('draft','ready','delivered','superseded')),
  readiness_summary jsonb not null default '{}'::jsonb,
  priority_issues jsonb not null default '[]'::jsonb,
  missing_items jsonb not null default '[]'::jsonb,
  next_steps jsonb not null default '[]'::jsonb,
  credit_repair_options jsonb not null default '[]'::jsonb,
  business_recommendations jsonb not null default '[]'::jsonb,
  funding_guidance jsonb not null default '{}'::jsonb,
  resource_refs jsonb not null default '[]'::jsonb,
  clyde_receipt_ids jsonb not null default '[]'::jsonb,
  request_review_cta text not null default '/client/request-review',
  client_visible boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists goclear_client_reports_client_idx on public.goclear_client_reports(client_id, created_at desc);

create table if not exists public.goclear_email_events (
  id uuid primary key default gen_random_uuid(),
  email_message_id text,
  provider text not null default 'resend',
  provider_message_id text,
  event_type text not null check (event_type in ('sent','delivered','bounced','clicked','complained','unsubscribed')),
  recipient_hash text,
  payload jsonb not null default '{}'::jsonb,
  occurred_at timestamptz not null default now(),
  created_at timestamptz not null default now()
);
create index if not exists goclear_email_events_provider_idx on public.goclear_email_events(provider_message_id, occurred_at desc);

create table if not exists public.goclear_email_suppressions (
  id uuid primary key default gen_random_uuid(),
  recipient_hash text not null unique,
  reason text not null check (reason in ('unsubscribed','bounced','complained')),
  source_event_id uuid references public.goclear_email_events(id) on delete set null,
  created_at timestamptz not null default now()
);

-- Authenticated clients may read their own closure artifacts. Inserts and
-- provider lifecycle updates remain server-side/service-role operations.
alter table public.goclear_leads enable row level security;
alter table public.goclear_upload_receipts enable row level security;
alter table public.goclear_clyde_receipts enable row level security;
alter table public.goclear_client_reports enable row level security;
alter table public.goclear_email_events enable row level security;
alter table public.goclear_email_suppressions enable row level security;

drop policy if exists goclear_leads_own_select on public.goclear_leads;
create policy goclear_leads_own_select on public.goclear_leads for select to authenticated using (auth_user_id = auth.uid() or public.nexus_is_active_admin());
drop policy if exists goclear_upload_receipts_own_select on public.goclear_upload_receipts;
create policy goclear_upload_receipts_own_select on public.goclear_upload_receipts for select to authenticated using (exists (select 1 from public.tenant_memberships tm where tm.client_id = goclear_upload_receipts.client_id and tm.user_id = auth.uid()) or public.nexus_is_active_admin());
drop policy if exists goclear_clyde_receipts_own_select on public.goclear_clyde_receipts;
create policy goclear_clyde_receipts_own_select on public.goclear_clyde_receipts for select to authenticated using (exists (select 1 from public.tenant_memberships tm where tm.client_id = goclear_clyde_receipts.client_id and tm.user_id = auth.uid()) or public.nexus_is_active_admin());
drop policy if exists goclear_client_reports_own_select on public.goclear_client_reports;
create policy goclear_client_reports_own_select on public.goclear_client_reports for select to authenticated using (client_visible and (exists (select 1 from public.tenant_memberships tm where tm.client_id = goclear_client_reports.client_id and tm.user_id = auth.uid()) or public.nexus_is_active_admin()));
drop policy if exists goclear_email_events_admin_select on public.goclear_email_events;
create policy goclear_email_events_admin_select on public.goclear_email_events for select to authenticated using (public.nexus_is_active_admin());
drop policy if exists goclear_email_suppressions_admin_select on public.goclear_email_suppressions;
create policy goclear_email_suppressions_admin_select on public.goclear_email_suppressions for select to authenticated using (public.nexus_is_active_admin());

grant select on public.goclear_leads, public.goclear_upload_receipts, public.goclear_clyde_receipts, public.goclear_client_reports, public.goclear_email_events, public.goclear_email_suppressions to authenticated;

create or replace function public.goclear_capture_lead(
  p_email text,
  p_name text default null,
  p_campaign_id text default null,
  p_variant text default null,
  p_beta_mode boolean default false,
  p_auth_user_id uuid default null,
  p_tenant_id text default null,
  p_client_id text default null,
  p_tester_invitation_id uuid default null
) returns public.goclear_leads
language plpgsql security definer set search_path = public
as $$
declare result_row public.goclear_leads;
begin
  if length(trim(coalesce(p_email,''))) < 3 then raise exception 'valid_email_required'; end if;
  insert into public.goclear_leads(email,name,campaign_id,variant,beta_mode,auth_user_id,tenant_id,client_id,tester_invitation_id,status)
  values (lower(trim(p_email)), nullif(trim(p_name),''), nullif(trim(p_campaign_id),''), nullif(trim(p_variant),''), coalesce(p_beta_mode,false), p_auth_user_id, p_tenant_id, p_client_id, p_tester_invitation_id, case when p_auth_user_id is null then 'captured' else 'account_created' end)
  on conflict (lower(email), coalesce(campaign_id,''), coalesce(variant,'')) do update set name=coalesce(excluded.name, public.goclear_leads.name), auth_user_id=coalesce(excluded.auth_user_id, public.goclear_leads.auth_user_id), tenant_id=coalesce(excluded.tenant_id, public.goclear_leads.tenant_id), client_id=coalesce(excluded.client_id, public.goclear_leads.client_id), beta_mode=public.goclear_leads.beta_mode or excluded.beta_mode, status=case when excluded.auth_user_id is not null then 'account_created' else public.goclear_leads.status end, updated_at=now()
  returning * into result_row;
  return result_row;
end;
$$;
revoke all on function public.goclear_capture_lead(text,text,text,text,boolean,uuid,text,text,uuid) from public;
grant execute on function public.goclear_capture_lead(text,text,text,text,boolean,uuid,text,text,uuid) to anon, authenticated;

commit;
