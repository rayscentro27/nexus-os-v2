-- Persist interval growth derived only from successive observed platform snapshots.
alter table public.trend_history_bank
  add column if not exists view_growth numeric;
