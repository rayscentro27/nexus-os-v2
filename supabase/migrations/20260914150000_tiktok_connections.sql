create table if not exists public.nexus_tiktok_connections (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  tenant_id text not null,
  open_id text not null,
  encrypted_access_token text not null,
  encrypted_refresh_token text,
  access_token_expires_at timestamptz,
  refresh_token_expires_at timestamptz,
  scopes text[] not null default '{}',
  status text not null default 'CONNECTED' check (status in ('CONNECTED','DISCONNECTED','AUTH_EXPIRED','REVIEW_GATED','READY_FOR_PRIVATE_TEST','READY_FOR_GOVERNED_PUBLIC_POST')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  revoked_at timestamptz,
  unique (tenant_id, user_id, open_id)
);

alter table public.nexus_tiktok_connections enable row level security;
create policy "tiktok connections owner read" on public.nexus_tiktok_connections
  for select to authenticated using (user_id = auth.uid());
create policy "tiktok connections owner cannot write tokens" on public.nexus_tiktok_connections
  for all to authenticated using (false) with check (false);

create table if not exists public.nexus_tiktok_post_receipts (
  id uuid primary key default gen_random_uuid(),
  connection_id uuid not null references public.nexus_tiktok_connections(id) on delete cascade,
  tenant_id text not null,
  user_id uuid not null references auth.users(id) on delete cascade,
  publish_id text,
  action text not null check (action in ('CREATOR_INFO','UPLOAD_DRAFT','DIRECT_POST','STATUS_POLL','DISCONNECT')),
  status text not null,
  response_metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

alter table public.nexus_tiktok_post_receipts enable row level security;
create policy "tiktok receipts owner read" on public.nexus_tiktok_post_receipts
  for select to authenticated using (user_id = auth.uid());
create policy "tiktok receipts owner cannot write" on public.nexus_tiktok_post_receipts
  for all to authenticated using (false) with check (false);
