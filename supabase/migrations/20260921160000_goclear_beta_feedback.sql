begin;
create table if not exists public.goclear_beta_feedback (
  id uuid primary key default gen_random_uuid(),
  tenant_id text not null,
  client_id text not null,
  offer_clarity integer not null check (offer_clarity between 1 and 5),
  funnel_clarity integer not null check (funnel_clarity between 1 and 5),
  portal_usability integer not null check (portal_usability between 1 and 5),
  report_usefulness integer not null check (report_usefulness between 1 and 5),
  next_step_clarity integer not null check (next_step_clarity between 1 and 5),
  credit_repair_choice_clarity integer not null check (credit_repair_choice_clarity between 1 and 5),
  affiliate_resource_clarity integer not null check (affiliate_resource_clarity between 1 and 5),
  broken_areas text,
  comments text,
  category text not null default 'beta_feedback',
  severity text not null default 'low' check (severity in ('blocker','high','medium','low')),
  department_owner text not null default 'customer_service',
  cross_department boolean not null default false,
  customer_response_required boolean not null default false,
  status text not null default 'feedback_submitted' check (status in ('feedback_started','feedback_submitted','feedback_triaged','feedback_routed','feedback_closed')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
alter table public.goclear_beta_feedback enable row level security;
drop policy if exists goclear_beta_feedback_own_insert on public.goclear_beta_feedback;
create policy goclear_beta_feedback_own_insert on public.goclear_beta_feedback for insert to authenticated with check (exists (select 1 from public.tenant_memberships tm where tm.client_id=goclear_beta_feedback.client_id and tm.tenant_id=goclear_beta_feedback.tenant_id and tm.user_id=auth.uid() and tm.role='client'));
drop policy if exists goclear_beta_feedback_own_select on public.goclear_beta_feedback;
create policy goclear_beta_feedback_own_select on public.goclear_beta_feedback for select to authenticated using (exists (select 1 from public.tenant_memberships tm where tm.client_id=goclear_beta_feedback.client_id and tm.user_id=auth.uid()) or public.nexus_is_active_admin());
grant select, insert on public.goclear_beta_feedback to authenticated;
commit;
