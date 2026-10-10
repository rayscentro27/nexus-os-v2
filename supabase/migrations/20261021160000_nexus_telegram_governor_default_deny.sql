-- Telegram was discovered as a real external-action provider. Register only
-- disabled daily/monthly policies; credentials never create send authority.
insert into public.nexus_resource_policies
  (provider,service,job_type,budget_period,autonomous_usage_allowed,autonomous_spend_allowed,
   soft_limits,hard_limits,concurrency_limit,resource_creation_limit,state,approval_required,updated_at)
select 'TELEGRAM','*','*',period,false,false,
  '{"rate":{"requests":0,"operations":0,"window_seconds":60},"usage":{},"money":{}}'::jsonb,
  '{"rate":{"requests":0,"operations":0,"window_seconds":60},"usage":{},"money":{}}'::jsonb,
  0,0,'DISABLED',true,now()
from unnest(array['DAILY','MONTHLY']) as period
on conflict(provider,service,job_type,budget_period) do nothing;
