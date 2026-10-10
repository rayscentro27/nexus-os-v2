alter table public.nexus_feeder_research_gaps
  add column if not exists notebook_id text,
  add column if not exists notebook_reference text,
  add column if not exists exact_research_question text,
  add column if not exists recommended_research_method text,
  add column if not exists preferred_source_type text,
  add column if not exists related_gap_ids jsonb not null default '[]'::jsonb,
  add column if not exists can_one_research_pass_close_multiple_gaps boolean not null default false,
  add column if not exists evidence jsonb not null default '[]'::jsonb,
  add column if not exists confidence text,
  add column if not exists completed_at timestamptz;

alter table public.options_data_source_bank
  add column if not exists data_support text,
  add column if not exists open_interest_support text,
  add column if not exists volume_support text,
  add column if not exists last_tested_at timestamptz,
  add column if not exists status text;

alter table public.options_execution_engine_bank
  add column if not exists data_support text,
  add column if not exists open_interest_support text,
  add column if not exists volume_support text,
  add column if not exists last_tested_at timestamptz,
  add column if not exists status text;
