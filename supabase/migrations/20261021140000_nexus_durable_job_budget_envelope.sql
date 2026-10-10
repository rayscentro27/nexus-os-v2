-- Explicit per-job resource envelope. Cost remains zero by default; adding a
-- credential or creating a job does not authorize spend.
alter table public.nexus_durable_jobs
  add column if not exists budget_envelope jsonb not null default
  '{"max_requests":120,"max_response_bytes":2000000,"max_tokens":12000,"max_gpu_seconds":0,"max_runtime_seconds":900,"max_resource_creations":0,"max_estimated_cost":0,"max_retries":3}'::jsonb;
alter table public.nexus_durable_jobs
  add constraint nexus_durable_jobs_budget_envelope_object
  check (jsonb_typeof(budget_envelope)='object');
