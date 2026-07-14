-- Additive, admin-gated storage for deterministic report reviews and bounded analysis jobs.
create table if not exists public.credit_report_system_reviews (
  id uuid primary key default gen_random_uuid(),
  tenant_id text not null,
  client_id text not null,
  document_id text not null,
  parser_result_id uuid references public.credit_report_parser_results(id) on delete set null,
  status text not null default 'pending_review' check (status in ('pending_review','approved_summary','needs_evidence','rejected')),
  summary jsonb not null default '{}'::jsonb,
  funding_impact_items jsonb not null default '[]'::jsonb,
  utilization_actions jsonb not null default '[]'::jsonb,
  report_item_reviews jsonb not null default '[]'::jsonb,
  inquiry_reviews jsonb not null default '[]'::jsonb,
  personal_info_reviews jsonb not null default '[]'::jsonb,
  evidence_needed jsonb not null default '[]'::jsonb,
  specialist_exceptions jsonb not null default '[]'::jsonb,
  no_action_items jsonb not null default '[]'::jsonb,
  recommended_next_steps jsonb not null default '[]'::jsonb,
  confidence_summary jsonb not null default '{}'::jsonb,
  tier_1_impact jsonb not null default '{}'::jsonb,
  tier_2_impact jsonb not null default '{}'::jsonb,
  needs_specialist_review boolean not null default true,
  client_visible boolean not null default false,
  reviewed_by text,
  reviewed_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.credit_analysis_jobs (
  id uuid primary key default gen_random_uuid(),
  tenant_id text not null,
  client_id text not null,
  document_id text not null,
  status text not null default 'queued' check (status in ('queued','processing','complete','failed','needs_manual_review')),
  parser_result_id uuid references public.credit_report_parser_results(id) on delete set null,
  system_review_id uuid references public.credit_report_system_reviews(id) on delete set null,
  requested_by uuid default auth.uid(),
  claimed_at timestamptz,
  completed_at timestamptz,
  failure_code text,
  failure_message text,
  attempt_count integer not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists credit_report_system_reviews_document_idx on public.credit_report_system_reviews(document_id, created_at desc);
create index if not exists credit_report_system_reviews_client_idx on public.credit_report_system_reviews(tenant_id, client_id, created_at desc);
create index if not exists credit_report_system_reviews_parser_idx on public.credit_report_system_reviews(parser_result_id);
create index if not exists credit_analysis_jobs_status_idx on public.credit_analysis_jobs(status, created_at);
create index if not exists credit_analysis_jobs_document_idx on public.credit_analysis_jobs(document_id, created_at desc);
create unique index if not exists credit_analysis_jobs_one_active_per_document on public.credit_analysis_jobs(document_id) where status in ('queued','processing');

alter table public.credit_report_system_reviews enable row level security;
alter table public.credit_analysis_jobs enable row level security;

do $$ begin
  if not exists (select 1 from pg_policies where policyname='credit_report_system_reviews_admin_manage' and tablename='credit_report_system_reviews') then
    create policy credit_report_system_reviews_admin_manage on public.credit_report_system_reviews for all to authenticated using (public.nexus_is_active_admin()) with check (public.nexus_is_active_admin());
  end if;
  if not exists (select 1 from pg_policies where policyname='credit_report_system_reviews_client_approved_select' and tablename='credit_report_system_reviews') then
    create policy credit_report_system_reviews_client_approved_select on public.credit_report_system_reviews for select to authenticated using (
      client_visible and status='approved_summary' and exists (
        select 1 from public.tenant_memberships tm where tm.user_id=auth.uid() and tm.tenant_id=credit_report_system_reviews.tenant_id and tm.client_id=credit_report_system_reviews.client_id
      )
    );
  end if;
  if not exists (select 1 from pg_policies where policyname='credit_analysis_jobs_admin_manage' and tablename='credit_analysis_jobs') then
    create policy credit_analysis_jobs_admin_manage on public.credit_analysis_jobs for all to authenticated using (public.nexus_is_active_admin()) with check (public.nexus_is_active_admin());
  end if;
end $$;

grant select, insert, update on public.credit_report_system_reviews to authenticated;
grant select, insert, update on public.credit_analysis_jobs to authenticated;
