-- Tester Readiness System
-- Tables for tester sessions, feedback, and readiness tracking.
-- All operations are scoped to synthetic personas only.

-- ── Tester Sessions ──────────────────────────────────────────────────────────
create table if not exists public.tester_sessions (
  id uuid primary key default gen_random_uuid(),
  persona text not null check (persona in ('a', 'b', 'c')),
  tester_name text not null default 'ray',
  started_at timestamptz not null default now(),
  ended_at timestamptz,
  build_commit text,
  fixture_version text default 'v1',
  workflows_attempted integer default 0,
  workflows_completed integer default 0,
  defects_found integer default 0,
  blocker_count integer default 0,
  notes text,
  status text not null default 'in_progress' check (status in ('in_progress', 'completed', 'blocked', 'abandoned')),
  created_at timestamptz not null default now()
);

alter table public.tester_sessions enable row level security;

create policy "tester_sessions_admin_select" on public.tester_sessions
  for select using (public.nexus_is_active_admin());

create policy "tester_sessions_admin_insert" on public.tester_sessions
  for insert with check (public.nexus_is_active_admin());

create policy "tester_sessions_admin_update" on public.tester_sessions
  for update using (public.nexus_is_active_admin());

create policy "tester_sessions_admin_delete" on public.tester_sessions
  for delete using (public.nexus_is_active_admin());

-- ── Tester Feedback ──────────────────────────────────────────────────────────
create table if not exists public.tester_feedback (
  id uuid primary key default gen_random_uuid(),
  session_id uuid references public.tester_sessions(id) on delete set null,
  persona text not null check (persona in ('a', 'b', 'c')),
  page_route text,
  workflow_step text,
  issue_title text not null,
  issue_description text,
  expected_behavior text,
  actual_behavior text,
  severity text not null default 'medium' check (severity in ('blocker', 'high', 'medium', 'low', 'cosmetic')),
  reproducibility text default 'sometimes' check (reproducibility in ('always', 'often', 'sometimes', 'once', 'unable_to_reproduce')),
  evidence_reference text,
  browser_device text,
  tester_name text default 'ray',
  fixture_version text default 'v1',
  build_commit text,
  status text not null default 'open' check (status in ('open', 'acknowledged', 'in_review', 'resolved', 'wont_fix')),
  assigned_owner text default 'ray',
  ray_review_item_id text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.tester_feedback enable row level security;

create policy "tester_feedback_admin_select" on public.tester_feedback
  for select using (public.nexus_is_active_admin());

create policy "tester_feedback_admin_insert" on public.tester_feedback
  for insert with check (public.nexus_is_active_admin());

create policy "tester_feedback_admin_update" on public.tester_feedback
  for update using (public.nexus_is_active_admin());

create policy "tester_feedback_admin_delete" on public.tester_feedback
  for delete using (public.nexus_is_active_admin());

-- ── Tester Readiness History ─────────────────────────────────────────────────
create table if not exists public.tester_readiness_history (
  id uuid primary key default gen_random_uuid(),
  persona text not null check (persona in ('a', 'b', 'c')),
  fixture_version text default 'v1',
  build_commit text,
  auth_status text default 'unknown',
  client_linkage_status text default 'unknown',
  initial_report_status text default 'unknown',
  followup_report_status text default 'unknown',
  parser_status text default 'unknown',
  canonical_account_count integer default 0,
  discrepancy_count integer default 0,
  strategy_match_count integer default 0,
  decision_status text default 'unknown',
  evidence_status text default 'unknown',
  draft_status text default 'unknown',
  comparison_status text default 'unknown',
  readiness_history_status text default 'unknown',
  genuine_exception_status text default 'unknown',
  browser_certification_status text default 'unknown',
  browser_certification_result text,
  last_seeded_at timestamptz,
  last_browser_certification_at timestamptz,
  overall_status text default 'unknown' check (overall_status in ('ready', 'incomplete', 'processing', 'failed', 'stale', 'not_provisioned')),
  notes text,
  created_at timestamptz not null default now()
);

alter table public.tester_readiness_history enable row level security;

create policy "tester_readiness_history_admin_select" on public.tester_readiness_history
  for select using (public.nexus_is_active_admin());

create policy "tester_readiness_history_admin_insert" on public.tester_readiness_history
  for insert with check (public.nexus_is_active_admin());

create policy "tester_readiness_history_admin_update" on public.tester_readiness_history
  for update using (public.nexus_is_active_admin());

create policy "tester_readiness_history_admin_delete" on public.tester_readiness_history
  for delete using (public.nexus_is_active_admin());

-- ── Indexes ──────────────────────────────────────────────────────────────────
create index if not exists idx_tester_sessions_persona on public.tester_sessions(persona);
create index if not exists idx_tester_sessions_status on public.tester_sessions(status);
create index if not exists idx_tester_feedback_persona on public.tester_feedback(persona);
create index if not exists idx_tester_feedback_severity on public.tester_feedback(severity);
create index if not exists idx_tester_feedback_status on public.tester_feedback(status);
create index if not exists idx_tester_feedback_session on public.tester_feedback(session_id);
create index if not exists idx_tester_readiness_persona on public.tester_readiness_history(persona);
