CREATE ROLE anon;
CREATE ROLE authenticated;
CREATE ROLE service_role;
CREATE TABLE public.nexus_resource_policies (
 provider text not null, service text not null default '*', job_type text not null default '*',
 budget_period text not null check (budget_period in ('DAILY','MONTHLY')),
 autonomous_usage_allowed boolean not null default false, autonomous_spend_allowed boolean not null default false,
 soft_limits jsonb not null default '{}'::jsonb, hard_limits jsonb not null default '{}'::jsonb,
 concurrency_limit integer not null default 0 check (concurrency_limit >= 0),
 resource_creation_limit integer not null default 0 check (resource_creation_limit >= 0),
 state text not null default 'DISABLED', approval_required boolean not null default true,
 updated_at timestamptz not null default now(),
 PRIMARY KEY(provider,service,job_type,budget_period)
);
CREATE TABLE public.nexus_resource_reservations (
 reservation_id text PRIMARY KEY, idempotency_key text not null unique,
 provider text not null, service text not null, job_type text not null,
 budget_period text not null check (budget_period in ('DAILY','MONTHLY')),
 job_id text not null, estimate jsonb not null, actual jsonb not null default '{}'::jsonb,
 status text not null check (status in ('ACTIVE','RECONCILED','RELEASED','DENIED')),
 created_at timestamptz not null default now(), expires_at timestamptz not null default now()+interval '6 hours',
 reconciled_at timestamptz
);
CREATE TABLE public.nexus_resource_incidents (
 incident_id text PRIMARY KEY, provider text, job_id text, project_id text, code text not null,
 threshold jsonb, observed jsonb, action text not null, unrelated_work_continued boolean,
 created_at timestamptz not null default now()
);
-- Legacy RPC exists in the predecessor schema and is explicitly retired by the migration.
CREATE FUNCTION public.nexus_reserve_resource_budget(text,text,text,text,text,jsonb,text)
RETURNS jsonb LANGUAGE sql AS $$ SELECT '{}'::jsonb $$;
