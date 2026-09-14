alter table public.nexus_tiktok_connections
  add column if not exists environment text not null default 'production';

alter table public.nexus_tiktok_connections
  drop constraint if exists nexus_tiktok_connections_environment_check;

alter table public.nexus_tiktok_connections
  add constraint nexus_tiktok_connections_environment_check
  check (environment in ('sandbox','production'));

alter table public.nexus_tiktok_connections
  drop constraint if exists nexus_tiktok_connections_tenant_id_user_id_open_id_key;

create unique index if not exists nexus_tiktok_connections_env_identity_idx
  on public.nexus_tiktok_connections(tenant_id, user_id, open_id, environment);
