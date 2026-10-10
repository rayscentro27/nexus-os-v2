-- Add structured follow-up details to the existing department Research request
-- table. This does not create a new request, handoff, or queue system.
alter table public.department_research_requests
  add column if not exists contract_payload jsonb not null default '{}'::jsonb,
  add column if not exists parent_goal_id text,
  add column if not exists parent_handoff_id text,
  add column if not exists return_to_department text,
  add column if not exists return_to_goal_id text,
  add column if not exists requesting_worker text,
  add column if not exists subject_type text,
  add column if not exists subject_id text,
  add column if not exists decision_unlocked_by_answers text,
  add column if not exists priority text,
  add column if not exists due_or_freshness_requirement text,
  add column if not exists updated_at timestamptz not null default now();

create index if not exists department_research_requests_return_goal_idx
  on public.department_research_requests(return_to_goal_id, status, updated_at desc);
