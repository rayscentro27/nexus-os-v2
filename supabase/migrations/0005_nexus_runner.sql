-- Nexus OS v2 — Day 5 nexus_runner. ADDITIVE ONLY. Runner-safety columns on agent_jobs.
-- agent_jobs already has admin SELECT (0002) + admin INSERT/UPDATE (0003); new columns inherit.
-- Scripts/runner use the service role (bypasses RLS). No anon/public policies, no RLS changes.

alter table agent_jobs add column if not exists claimed_at   timestamptz;
alter table agent_jobs add column if not exists claimed_by   text;
alter table agent_jobs add column if not exists started_at   timestamptz;
alter table agent_jobs add column if not exists attempts     int not null default 0;
alter table agent_jobs add column if not exists max_attempts int not null default 1;
alter table agent_jobs add column if not exists last_error   text;
alter table agent_jobs add column if not exists priority     int not null default 100;
alter table agent_jobs add column if not exists locked_until timestamptz;

create index if not exists idx_agent_jobs_eligible on agent_jobs (status, priority, created_at);
