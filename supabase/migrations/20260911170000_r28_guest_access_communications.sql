-- R28: first-class free guest access and governed customer communications.
begin;

create extension if not exists pgcrypto;

create table if not exists public.guest_invitations (
  id uuid primary key default gen_random_uuid(),
  tenant_id text not null default 'goclear',
  email text not null,
  name text not null,
  invite_type text not null default 'GUEST_FREE' check (invite_type = 'GUEST_FREE'),
  access_tier text not null default 'FREE_GUEST' check (access_tier = 'FREE_GUEST'),
  created_by uuid references auth.users(id) on delete set null,
  created_at timestamptz not null default now(),
  expires_at timestamptz not null,
  used_at timestamptz,
  user_id uuid references auth.users(id) on delete set null,
  status text not null default 'CREATED' check (status in ('CREATED','SENT','DELIVERED','SIGNED_UP','ONBOARDING','FREE_ACTIVE','CONVERTED_TO_PAID','EXPIRED','REVOKED')),
  payment_bypass_scope text not null default 'ONBOARDING_AND_READINESS',
  funding_gate text not null default 'PAYMENT_OR_SERVICE_AGREEMENT_REQUIRED',
  token_hash text not null unique,
  token_last_four text not null,
  revoked_at timestamptz,
  note text,
  provider_message_id text,
  last_error text,
  updated_at timestamptz not null default now()
);
create unique index if not exists guest_invitations_active_email on public.guest_invitations(lower(email)) where status in ('CREATED','SENT','DELIVERED');

create table if not exists public.customer_communications (
  id uuid primary key default gen_random_uuid(),
  tenant_id text not null,
  client_id text,
  template_id text not null,
  template_version text not null default 'v1',
  trigger text not null,
  channel text not null default 'EMAIL' check (channel = 'EMAIL'),
  recipient text not null,
  created_at timestamptz not null default now(),
  sent_at timestamptz,
  provider text not null default 'RESEND',
  provider_message_id text,
  status text not null default 'QUEUED' check (status in ('QUEUED','SENT','DELIVERED','BOUNCED','FAILED','COMPLAINT','CANCELLED')),
  failure_reason text,
  related_invite_id uuid references public.guest_invitations(id) on delete set null,
  related_case_id uuid,
  related_payment_id uuid,
  related_workflow_id uuid,
  metadata jsonb not null default '{}'::jsonb
);

alter table if exists public.invitation_events
  add column if not exists guest_invitation_id uuid references public.guest_invitations(id) on delete set null;
create index if not exists idx_invitation_events_guest_invitation on public.invitation_events(guest_invitation_id, created_at desc);
create index if not exists customer_communications_tenant_created on public.customer_communications(tenant_id, created_at desc);
create index if not exists customer_communications_invite on public.customer_communications(related_invite_id);

create or replace function public.nexus_guest_free_access_allowed(p_tenant_id text, p_user_id uuid)
returns boolean language sql stable security definer set search_path = public as $$
  select exists (
    select 1 from public.guest_invitations gi
    where gi.tenant_id = p_tenant_id and gi.user_id = p_user_id
      and gi.access_tier = 'FREE_GUEST'
      and gi.status in ('SIGNED_UP','ONBOARDING','FREE_ACTIVE')
      and gi.expires_at > now() and gi.revoked_at is null
  )
$$;

alter table public.guest_invitations enable row level security;
drop policy if exists guest_invitations_admin_manage on public.guest_invitations;
create policy guest_invitations_admin_manage on public.guest_invitations for all to authenticated using (public.nexus_is_active_admin()) with check (public.nexus_is_active_admin());
drop policy if exists guest_invitations_owner_select on public.guest_invitations;
create policy guest_invitations_owner_select on public.guest_invitations for select to authenticated using (user_id = auth.uid() and status in ('SIGNED_UP','ONBOARDING','FREE_ACTIVE'));

alter table public.customer_communications enable row level security;
drop policy if exists customer_communications_admin_manage on public.customer_communications;
create policy customer_communications_admin_manage on public.customer_communications for all to authenticated using (public.nexus_is_active_admin()) with check (public.nexus_is_active_admin());
drop policy if exists customer_communications_owner_select on public.customer_communications;
create policy customer_communications_owner_select on public.customer_communications for select to authenticated using (
  exists (select 1 from public.tenant_memberships tm where tm.tenant_id = customer_communications.tenant_id and tm.user_id = auth.uid() and tm.role = 'client' and (customer_communications.client_id is null or tm.client_id = customer_communications.client_id))
);

grant select on public.guest_invitations to authenticated;
grant select on public.customer_communications to authenticated;

create or replace function public.nexus_guest_invitations_updated_at()
returns trigger language plpgsql as $$ begin new.updated_at = now(); return new; end; $$;
drop trigger if exists guest_invitations_updated_at on public.guest_invitations;
create trigger guest_invitations_updated_at before update on public.guest_invitations for each row execute function public.nexus_guest_invitations_updated_at();

commit;
