alter table public.trading_strategy_experience_bank
  add column if not exists candidate_rank integer;
notify pgrst, 'reload schema';
