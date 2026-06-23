-- Nexus OS v2 — Day 10 Manual Publish Readiness Packages. ADDITIVE ONLY.
-- Turns a winning creative/design variant into an approval-gated, manual publish-ready package.
-- No real publishing. RLS admin-only (admin_users pattern). No anon/public policies.

create table if not exists publish_readiness_packages (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid references workspaces(id),
  design_brief_id uuid references creative_design_briefs(id) on delete set null,
  design_variant_id uuid references creative_design_variants(id) on delete set null,
  comparison_id uuid references creative_asset_comparisons(id) on delete set null,
  platform text not null,
  package_title text not null,
  final_post_copy text not null,
  image_prompt text,
  design_notes text,
  cta text,
  compliance_footer text,
  hashtags jsonb not null default '[]',
  risk_flags jsonb not null default '[]',
  compliance_status text not null default 'needs_review',
  approval_status text not null default 'pending',
  approval_id uuid references approvals(id) on delete set null,
  manual_posting_instructions text,
  dry_run_receipt jsonb not null default '{}',
  status text not null default 'draft',
  metadata jsonb not null default '{}',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists publish_package_reviews (
  id uuid primary key default gen_random_uuid(),
  package_id uuid references publish_readiness_packages(id) on delete cascade,
  review_type text not null default 'compliance',
  reviewer text not null default 'system',
  score int not null default 0,
  decision text not null,
  reason text,
  revision_notes jsonb not null default '[]',
  risk_flags jsonb not null default '[]',
  metadata jsonb not null default '{}',
  created_at timestamptz not null default now()
);

create table if not exists manual_publish_receipts (
  id uuid primary key default gen_random_uuid(),
  package_id uuid references publish_readiness_packages(id) on delete cascade,
  platform text not null,
  receipt_type text not null default 'dry_run',
  summary text not null,
  posted_by text,
  posted_at timestamptz,
  external_url text,
  proof_notes text,
  metadata jsonb not null default '{}',
  created_at timestamptz not null default now()
);

create index if not exists idx_pub_packages_status on publish_readiness_packages (status, created_at desc);
create index if not exists idx_pub_packages_approval on publish_readiness_packages (approval_status, created_at desc);
create index if not exists idx_pub_reviews_pkg on publish_package_reviews (package_id, created_at desc);
create index if not exists idx_manual_receipts_pkg on manual_publish_receipts (package_id, created_at desc);

do $$
declare t text;
begin
  foreach t in array array['publish_readiness_packages','publish_package_reviews','manual_publish_receipts'] loop
    execute format('alter table %I enable row level security', t);
    execute format('drop policy if exists %I on %I', 'admin read ' || t, t);
    execute format(
      'create policy %I on %I for select to authenticated using ('
      || 'exists (select 1 from admin_users a where a.id = auth.uid() and a.active = true))',
      'admin read ' || t, t);
  end loop;
end $$;
