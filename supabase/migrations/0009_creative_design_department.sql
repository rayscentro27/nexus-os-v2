-- Nexus OS v2 — Day 9 Creative Design Department + Design Inspiration Registry. ADDITIVE ONLY.
-- RLS admin-only (admin_users pattern). No anon/public policies.

create table if not exists creative_design_briefs (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid references workspaces(id),
  campaign_id uuid references creative_campaigns(id),
  title text not null,
  platform text not null,
  audience text not null,
  offer text,
  tone text,
  visual_metaphor text,
  image_concept text,
  compliance_rules jsonb not null default '[]',
  required_text jsonb not null default '{}',
  avoid_text jsonb not null default '[]',
  status text not null default 'draft',
  metadata jsonb not null default '{}',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists creative_design_variants (
  id uuid primary key default gen_random_uuid(),
  design_brief_id uuid references creative_design_briefs(id) on delete cascade,
  route_key text not null,
  variant_type text not null,
  title text not null,
  post_copy text,
  image_prompt text,
  layout_notes text,
  background_concept text,
  asset_ref text,
  status text not null default 'draft',
  metadata jsonb not null default '{}',
  created_at timestamptz not null default now()
);

create table if not exists creative_design_scores (
  id uuid primary key default gen_random_uuid(),
  design_variant_id uuid references creative_design_variants(id) on delete cascade,
  hook_strength int not null default 0,
  trust_score int not null default 0,
  brand_fit int not null default 0,
  readability int not null default 0,
  compliance_safety int not null default 0,
  emotional_clarity int not null default 0,
  cta_strength int not null default 0,
  platform_fit int not null default 0,
  overall_score int not null default 0,
  recommendation text,
  risk_flags jsonb not null default '[]',
  metadata jsonb not null default '{}',
  created_at timestamptz not null default now()
);

create table if not exists creative_asset_comparisons (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid references workspaces(id),
  design_brief_id uuid references creative_design_briefs(id) on delete cascade,
  winning_variant_id uuid references creative_design_variants(id),
  summary text not null,
  reason text not null,
  next_action text not null,
  approval_required boolean not null default true,
  metadata jsonb not null default '{}',
  created_at timestamptz not null default now()
);

create table if not exists design_inspiration_sources (
  id uuid primary key default gen_random_uuid(),
  source_type text not null,
  source_name text not null,
  source_url text,
  category text not null,
  summary text,
  usefulness_score int not null default 0,
  risk_level text not null default 'low',
  metadata jsonb not null default '{}',
  created_at timestamptz not null default now()
);

create table if not exists design_pattern_registry (
  id uuid primary key default gen_random_uuid(),
  inspiration_source_id uuid references design_inspiration_sources(id) on delete set null,
  pattern_name text not null,
  pattern_category text not null,
  use_case text not null,
  description text not null,
  design_rules jsonb not null default '{}',
  avoid_rules jsonb not null default '[]',
  metadata jsonb not null default '{}',
  created_at timestamptz not null default now()
);

create table if not exists ui_quality_reviews (
  id uuid primary key default gen_random_uuid(),
  subject_type text not null,
  subject_id uuid,
  review_title text not null,
  layout_score int not null default 0,
  readability_score int not null default 0,
  brand_fit_score int not null default 0,
  mobile_score int not null default 0,
  accessibility_score int not null default 0,
  conversion_score int not null default 0,
  compliance_score int not null default 0,
  overall_score int not null default 0,
  recommendation text not null,
  revision_notes jsonb not null default '[]',
  metadata jsonb not null default '{}',
  created_at timestamptz not null default now()
);

create table if not exists feature_design_packets (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid references workspaces(id),
  feature_name text not null,
  target_surface text not null,
  user_goal text not null,
  required_sections jsonb not null default '[]',
  component_guidance jsonb not null default '{}',
  copy_guidance jsonb not null default '{}',
  visual_guidance jsonb not null default '{}',
  compliance_rules jsonb not null default '[]',
  status text not null default 'draft',
  metadata jsonb not null default '{}',
  created_at timestamptz not null default now()
);

create index if not exists idx_design_variants_brief on creative_design_variants (design_brief_id, created_at desc);
create index if not exists idx_design_briefs_status on creative_design_briefs (status, created_at desc);
create index if not exists idx_inspiration_category on design_inspiration_sources (category, created_at desc);
create index if not exists idx_pattern_category on design_pattern_registry (pattern_category, created_at desc);

do $$
declare t text;
begin
  foreach t in array array['creative_design_briefs','creative_design_variants','creative_design_scores',
    'creative_asset_comparisons','design_inspiration_sources','design_pattern_registry',
    'ui_quality_reviews','feature_design_packets'] loop
    execute format('alter table %I enable row level security', t);
    execute format('drop policy if exists %I on %I', 'admin read ' || t, t);
    execute format(
      'create policy %I on %I for select to authenticated using ('
      || 'exists (select 1 from admin_users a where a.id = auth.uid() and a.active = true))',
      'admin read ' || t, t);
  end loop;
end $$;
