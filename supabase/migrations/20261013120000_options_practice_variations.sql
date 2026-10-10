alter table public.options_strategy_experience_bank
  add column if not exists candidate_modification jsonb not null default '{}'::jsonb;
notify pgrst, 'reload schema';
