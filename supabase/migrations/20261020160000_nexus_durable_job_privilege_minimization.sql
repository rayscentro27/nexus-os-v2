-- Supabase project defaults grant broad service_role table privileges.
-- Keep queue mutations to read/insert/update; certification cleanup is run by
-- the linked database owner, not by the production service-role adapter.
revoke all on public.nexus_durable_jobs from service_role;
grant select, insert, update on public.nexus_durable_jobs to service_role;
revoke all on public.nexus_durable_schedules from service_role;
grant select, insert, update on public.nexus_durable_schedules to service_role;
