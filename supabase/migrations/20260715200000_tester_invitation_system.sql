-- Nexus OS v2 Phase 7 — Tester Invitation System and Controlled Pilot Foundation.
-- Additive only. Invites testers, supports test-mode payments, foundations for $1 pilot.
begin;

create extension if not exists pgcrypto;

-- ── Tester Invitations ────────────────────────────────────────────────────────
create table if not exists public.tester_invitations (
  id uuid primary key default gen_random_uuid(),
  tenant_id text not null default 'nexus',
  invited_by_admin_id uuid references auth.users(id) on delete set null,
  tester_name text not null,
  tester_email text not null,
  testing_level text not null default 'invited_test_mode'
    check (testing_level in ('synthetic_internal', 'invited_test_mode', 'controlled_live_pilot')),
  assigned_persona text check (assigned_persona in ('a', 'b', 'c')),
  assigned_client_id text,
  assigned_tenant_id text,
  invitation_status text not null default 'draft'
    check (invitation_status in ('draft', 'awaiting_approval', 'approved', 'sent', 'accepted', 'expired', 'revoked', 'completed', 'failed')),
  token_hash text not null,
  token_last_four text not null,
  expires_at timestamptz not null,
  accepted_at timestamptz,
  revoked_at timestamptz,
  completed_at timestamptz,
  auth_user_id uuid references auth.users(id) on delete set null,
  max_sessions integer not null default 3,
  sessions_used integer not null default 0,
  task_checklist_version text not null default 'v1',
  build_commit text,
  fixture_version text default 'v1',
  payment_offer_slug text,
  payment_mode text not null default 'test'
    check (payment_mode in ('test', 'controlled_live_pilot', 'public_live')),
  allowlisted_for_pilot boolean not null default false,
  terms_version text not null default 'readiness-services-v1',
  consent_version text not null default 'tester-consent-v1',
  resend_count integer not null default 0,
  last_sent_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_tester_invitations_email on public.tester_invitations(tester_email);
create index if not exists idx_tester_invitations_status on public.tester_invitations(invitation_status);
create index if not exists idx_tester_invitations_level on public.tester_invitations(testing_level);
create index if not exists idx_tester_invitations_token_hash on public.tester_invitations(token_hash);
create index if not exists idx_tester_invitations_auth_user on public.tester_invitations(auth_user_id);

-- Prevent duplicate active invitations for same email+level unless explicitly allowed
create unique index if not exists one_active_invitation_per_email_level
  on public.tester_invitations(tester_email, testing_level)
  where invitation_status in ('draft', 'awaiting_approval', 'approved', 'sent');

-- ── Payment Pilot Allowlist ───────────────────────────────────────────────────
create table if not exists public.payment_pilot_allowlist (
  id uuid primary key default gen_random_uuid(),
  tester_invitation_id uuid references public.tester_invitations(id) on delete set null,
  tester_email text not null,
  auth_user_id uuid references auth.users(id) on delete set null,
  enabled boolean not null default true,
  allowed_offer_slug text not null,
  max_orders integer not null default 1,
  orders_used integer not null default 0,
  approved_by uuid references auth.users(id) on delete set null,
  approved_at timestamptz not null default now(),
  expires_at timestamptz,
  revoked_at timestamptz,
  notes text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_pilot_allowlist_email on public.payment_pilot_allowlist(tester_email);
create index if not exists idx_pilot_allowlist_invitation on public.payment_pilot_allowlist(tester_invitation_id);
create index if not exists idx_pilot_allowlist_offer on public.payment_pilot_allowlist(allowed_offer_slug);

-- ── Payment Pilot Controls ────────────────────────────────────────────────────
create table if not exists public.payment_pilot_controls (
  id text primary key default 'singleton',
  mode text not null default 'test' check (mode in ('test', 'controlled_live_pilot', 'public_live')),
  invitations_enabled boolean not null default false,
  test_mode_purchases_enabled boolean not null default false,
  controlled_live_pilot_enabled boolean not null default false,
  public_live_enabled boolean not null default false,
  hidden_pilot_offer_enabled boolean not null default false,
  emergency_checkout_disabled boolean not null default false,
  max_live_pilot_orders integer not null default 10,
  live_pilot_orders_used integer not null default 0,
  activated_by uuid references auth.users(id) on delete set null,
  activated_at timestamptz,
  deactivated_at timestamptz,
  activation_reason text,
  current_build_commit text,
  terms_version text not null default 'readiness-services-v1',
  updated_at timestamptz not null default now()
);

-- ── Pilot Disclosures ─────────────────────────────────────────────────────────
create table if not exists public.pilot_disclosures (
  id uuid primary key default gen_random_uuid(),
  invitation_id uuid not null references public.tester_invitations(id) on delete cascade,
  order_id uuid references public.client_orders(id) on delete set null,
  disclosure_version text not null default 'pilot-disclosure-v1',
  disclosure_text text not null,
  accepted_at timestamptz not null default now(),
  accepted_ip_hash text,
  accepted_user_agent text,
  created_at timestamptz not null default now()
);

create index if not exists idx_pilot_disclosures_invitation on public.pilot_disclosures(invitation_id);

-- ── Invitation Events (Audit Log) ─────────────────────────────────────────────
create table if not exists public.invitation_events (
  id uuid primary key default gen_random_uuid(),
  invitation_id uuid references public.tester_invitations(id) on delete cascade,
  event_type text not null,
  actor_admin_id uuid references auth.users(id) on delete set null,
  actor_email text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists idx_invitation_events_invitation on public.invitation_events(invitation_id, created_at desc);
create index if not exists idx_invitation_events_type on public.invitation_events(event_type);

-- ── Invite Email Drafts ───────────────────────────────────────────────────────
create table if not exists public.invite_email_drafts (
  id uuid primary key default gen_random_uuid(),
  invitation_id uuid not null references public.tester_invitations(id) on delete cascade,
  template_name text not null,
  to_email text not null,
  subject text not null,
  html_preview text,
  status text not null default 'draft' check (status in ('draft', 'approved', 'sent', 'failed')),
  provider_message_id text,
  sent_at timestamptz,
  error_message text,
  created_at timestamptz not null default now()
);

create index if not exists idx_invite_email_drafts_invitation on public.invite_email_drafts(invitation_id);

-- ── RLS ───────────────────────────────────────────────────────────────────────

-- tester_invitations
alter table public.tester_invitations enable row level security;

-- Admin: full manage
drop policy if exists tester_invitations_admin_manage on public.tester_invitations;
create policy tester_invitations_admin_manage on public.tester_invitations
  for all to authenticated using (public.nexus_is_active_admin()) with check (public.nexus_is_active_admin());

-- Tester: can read only their own accepted invitation
drop policy if exists tester_invitations_own_select on public.tester_invitations;
create policy tester_invitations_own_select on public.tester_invitations
  for select to authenticated using (
    auth_user_id = auth.uid() and invitation_status = 'accepted'
  );

-- payment_pilot_allowlist
alter table public.payment_pilot_allowlist enable row level security;

drop policy if exists pilot_allowlist_admin_manage on public.payment_pilot_allowlist;
create policy pilot_allowlist_admin_manage on public.payment_pilot_allowlist
  for all to authenticated using (public.nexus_is_active_admin()) with check (public.nexus_is_active_admin());

-- Tester: can read only their own allowlist entry
drop policy if exists pilot_allowlist_own_select on public.payment_pilot_allowlist;
create policy pilot_allowlist_own_select on public.payment_pilot_allowlist
  for select to authenticated using (
    auth_user_id = auth.uid()
  );

-- payment_pilot_controls
alter table public.payment_pilot_controls enable row level security;

drop policy if exists pilot_controls_admin_manage on public.payment_pilot_controls;
create policy pilot_controls_admin_manage on public.payment_pilot_controls
  for all to authenticated using (public.nexus_is_active_admin()) with check (public.nexus_is_active_admin());

-- pilot_disclosures
alter table public.pilot_disclosures enable row level security;

drop policy if exists pilot_disclosures_admin_manage on public.pilot_disclosures;
create policy pilot_disclosures_admin_manage on public.pilot_disclosures
  for all to authenticated using (public.nexus_is_active_admin()) with check (public.nexus_is_active_admin());

-- Tester: can read their own disclosures
drop policy if exists pilot_disclosures_own_select on public.pilot_disclosures;
create policy pilot_disclosures_own_select on public.pilot_disclosures
  for select to authenticated using (
    exists (
      select 1 from public.tester_invitations ti
      where ti.id = pilot_disclosures.invitation_id and ti.auth_user_id = auth.uid()
    )
  );

-- invitation_events
alter table public.invitation_events enable row level security;

drop policy if exists invitation_events_admin_select on public.invitation_events;
create policy invitation_events_admin_select on public.invitation_events
  for select using (public.nexus_is_active_admin());

drop policy if exists invitation_events_admin_insert on public.invitation_events;
create policy invitation_events_admin_insert on public.invitation_events
  for insert with check (public.nexus_is_active_admin());

-- invite_email_drafts
alter table public.invite_email_drafts enable row level security;

drop policy if exists invite_email_drafts_admin_manage on public.invite_email_drafts;
create policy invite_email_drafts_admin_manage on public.invite_email_drafts
  for all to authenticated using (public.nexus_is_active_admin()) with check (public.nexus_is_active_admin());

-- ── Grants ────────────────────────────────────────────────────────────────────
grant select on public.tester_invitations to authenticated;
grant select on public.payment_pilot_allowlist to authenticated;
grant select on public.payment_pilot_controls to authenticated;
grant select on public.pilot_disclosures to authenticated;
grant select, insert on public.invitation_events to authenticated;
grant select on public.invite_email_drafts to authenticated;

-- ── Helper: hash invitation token ─────────────────────────────────────────────
create or replace function public.nexus_hash_invitation_token(raw_token text)
returns text language sql immutable as $$
  encode(digest(raw_token, 'sha256'), 'hex')
$$;

-- ── Trigger: update updated_at ────────────────────────────────────────────────
create or replace function public.nexus_set_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists tester_invitations_updated_at on public.tester_invitations;
create trigger tester_invitations_updated_at before update on public.tester_invitations
  for each row execute function public.nexus_set_updated_at();

drop trigger if exists pilot_allowlist_updated_at on public.payment_pilot_allowlist;
create trigger pilot_allowlist_updated_at before update on public.payment_pilot_allowlist
  for each row execute function public.nexus_set_updated_at();

drop trigger if exists pilot_controls_updated_at on public.payment_pilot_controls;
create trigger pilot_controls_updated_at before update on public.payment_pilot_controls
  for each row execute function public.nexus_set_updated_at();

-- ── Seed default pilot controls row ───────────────────────────────────────────
insert into public.payment_pilot_controls (id, mode, invitations_enabled, test_mode_purchases_enabled, controlled_live_pilot_enabled, public_live_enabled, hidden_pilot_offer_enabled, emergency_checkout_disabled)
values ('singleton', 'test', false, false, false, false, false, false)
on conflict (id) do nothing;

commit;
