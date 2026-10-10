-- Keep normalized records grouped by their deterministic discovery topic family.
alter table public.pulse_trends
  add column if not exists cluster_id text;

create index if not exists pulse_trends_cluster_recent_idx
  on public.pulse_trends(cluster_id, last_observed_at desc);
