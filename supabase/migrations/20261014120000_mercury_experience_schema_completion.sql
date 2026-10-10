alter table public.trading_strategy_experience_bank
  add column if not exists selected_configuration jsonb not null default '{}'::jsonb,
  add column if not exists information_gain numeric,
  add column if not exists candidate_rank_score numeric,
  add column if not exists candidate_rank integer,
  add column if not exists is_control boolean not null default false,
  add column if not exists sample_quality text;
notify pgrst, 'reload schema';
