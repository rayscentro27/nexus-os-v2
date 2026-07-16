-- Nexus OS v2 Phase 6 — controlled revenue activation.
-- Additive only. All payment provider writes are server/webhook only and must remain test mode.
begin;

create extension if not exists pgcrypto;

create table if not exists public.service_offers (
  id text primary key,
  slug text not null unique,
  name text not null,
  tier integer not null check (tier in (1, 2, 3)),
  price_cents integer not null check (price_cents > 0),
  currency text not null default 'usd' check (currency = 'usd'),
  description text not null default '',
  included_deliverables jsonb not null default '[]'::jsonb,
  excluded_claims jsonb not null default '[]'::jsonb,
  consultation_entitlement text not null default 'none' check (consultation_entitlement in ('none','one_review_session','priority_consultation')),
  active boolean not null default false,
  fulfillment_type text not null,
  test_price_id text,
  public_route text not null,
  terms_version text not null,
  refund_policy_reference text not null,
  privacy_notice_reference text not null,
  readiness_scope jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.client_orders (
  id uuid primary key default gen_random_uuid(),
  tenant_id text not null,
  client_id text not null,
  auth_user_id uuid not null references auth.users(id) on delete restrict,
  offer_id text not null references public.service_offers(id),
  order_number text not null unique,
  status text not null default 'draft' check (status in ('draft','checkout_created','payment_pending','paid','payment_failed','cancelled','refunded','disputed','expired')),
  amount_cents integer not null check (amount_cents > 0),
  currency text not null default 'usd' check (currency = 'usd'),
  payment_provider text not null default 'stripe',
  provider_customer_id text,
  provider_checkout_session_id text unique,
  provider_payment_intent_id text unique,
  payment_status text not null default 'unpaid',
  fulfillment_status text not null default 'not_started',
  terms_version text not null,
  terms_accepted_at timestamptz,
  referral_code text,
  referral_source text,
  readiness_snapshot_id text,
  created_at timestamptz not null default now(),
  paid_at timestamptz,
  cancelled_at timestamptz,
  refunded_at timestamptz,
  updated_at timestamptz not null default now()
);

create table if not exists public.payment_events (
  id uuid primary key default gen_random_uuid(),
  provider text not null default 'stripe',
  provider_event_id text not null unique,
  event_type text not null,
  event_created_at timestamptz,
  order_id uuid references public.client_orders(id) on delete set null,
  processed_status text not null default 'received' check (processed_status in ('received','processed','duplicate','rejected','failed')),
  processed_at timestamptz,
  sanitized_payload jsonb not null default '{}'::jsonb,
  error_code text,
  created_at timestamptz not null default now()
);

create table if not exists public.service_fulfillments (
  id uuid primary key default gen_random_uuid(),
  order_id uuid not null unique references public.client_orders(id) on delete cascade,
  client_id text not null,
  offer_id text not null references public.service_offers(id),
  fulfillment_status text not null default 'not_started' check (fulfillment_status in ('not_started','onboarding_required','intake_in_progress','awaiting_documents','analysis_in_progress','admin_review','ray_review','approved_for_delivery','delivered','completed','blocked','cancelled')),
  assigned_reviewer text,
  review_request_id text,
  readiness_packet_id uuid,
  consultation_entitlement text not null default 'none',
  consultation_status text not null default 'not_entitled',
  approval_status text not null default 'not_required' check (approval_status in ('not_required','pending','approved','rejected','revision_requested')),
  delivery_status text not null default 'not_ready',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  completed_at timestamptz
);

create table if not exists public.readiness_packets (
  id uuid primary key default gen_random_uuid(),
  order_id uuid not null references public.client_orders(id) on delete cascade,
  client_id text not null,
  version integer not null check (version > 0),
  status text not null default 'draft' check (status in ('draft','admin_review','ray_review','approved_for_delivery','delivered','rejected','revision_requested')),
  content jsonb not null default '{}'::jsonb,
  reviewer_id text,
  reviewed_at timestamptz,
  approval_status text not null default 'draft' check (approval_status in ('draft','pending','approved','rejected','revision_requested')),
  rejection_reason text,
  client_visible boolean not null default false,
  delivered_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (order_id, version)
);

create table if not exists public.consultation_requests (
  id uuid primary key default gen_random_uuid(),
  order_id uuid not null references public.client_orders(id) on delete cascade,
  client_id text not null,
  entitlement_type text not null,
  allowed_duration_minutes integer not null default 0,
  scheduling_status text not null default 'pending_admin_confirmation' check (scheduling_status in ('pending_admin_confirmation','requested','confirmed','cancelled','completed')),
  requested_slots jsonb not null default '[]'::jsonb,
  confirmed_start timestamptz,
  confirmed_end timestamptz,
  timezone text,
  meeting_method text,
  attendance_status text not null default 'not_scheduled',
  notes text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.referral_attributions (
  id uuid primary key default gen_random_uuid(),
  referral_code text,
  referrer_type text,
  referrer_id text,
  offer_id text references public.service_offers(id),
  order_id uuid references public.client_orders(id) on delete set null,
  payment_status text not null default 'unpaid',
  eligible_revenue_cents integer not null default 0,
  nexus_commission_basis_bps integer not null default 0,
  referral_commission_basis_bps integer not null default 0,
  commission_status text not null default 'not_eligible',
  payout_status text not null default 'not_scheduled',
  created_at timestamptz not null default now(),
  approved_at timestamptz,
  paid_at timestamptz
);

create index if not exists client_orders_client_idx on public.client_orders(tenant_id, client_id, created_at desc);
create index if not exists client_orders_status_idx on public.client_orders(status, fulfillment_status, created_at desc);
create index if not exists payment_events_order_idx on public.payment_events(order_id, created_at desc);
create index if not exists service_fulfillments_client_idx on public.service_fulfillments(client_id, updated_at desc);
create index if not exists readiness_packets_client_idx on public.readiness_packets(client_id, status, created_at desc);
create unique index if not exists one_active_consultation_per_order on public.consultation_requests(order_id) where scheduling_status not in ('cancelled','completed');
create unique index if not exists one_referral_attribution_per_order on public.referral_attributions(order_id) where order_id is not null;

alter table public.service_offers enable row level security;
alter table public.client_orders enable row level security;
alter table public.payment_events enable row level security;
alter table public.service_fulfillments enable row level security;
alter table public.readiness_packets enable row level security;
alter table public.consultation_requests enable row level security;
alter table public.referral_attributions enable row level security;

-- Public catalog only exposes active offers. No order/payment/fulfillment data is public.
drop policy if exists service_offers_public_active on public.service_offers;
create policy service_offers_public_active on public.service_offers for select to anon, authenticated using (active = true or public.nexus_is_active_admin());
drop policy if exists service_offers_admin_manage on public.service_offers;
create policy service_offers_admin_manage on public.service_offers for all to authenticated using (public.nexus_is_active_admin()) with check (public.nexus_is_active_admin());
grant select on public.service_offers to anon, authenticated;
grant insert, update, delete on public.service_offers to authenticated;

drop policy if exists client_orders_owner_select on public.client_orders;
create policy client_orders_owner_select on public.client_orders for select to authenticated using (
  public.nexus_is_active_admin() or exists (select 1 from public.tenant_memberships tm where tm.tenant_id = client_orders.tenant_id and tm.user_id = auth.uid() and tm.role = 'client' and tm.client_id = client_orders.client_id and client_orders.auth_user_id = auth.uid())
);
drop policy if exists client_orders_admin_update on public.client_orders;
create policy client_orders_admin_update on public.client_orders for update to authenticated using (public.nexus_is_active_admin()) with check (public.nexus_is_active_admin());
grant select on public.client_orders to authenticated;
grant update on public.client_orders to authenticated;

drop policy if exists payment_events_admin_select on public.payment_events;
create policy payment_events_admin_select on public.payment_events for select to authenticated using (public.nexus_is_active_admin());
grant select on public.payment_events to authenticated;

drop policy if exists service_fulfillments_owner_select on public.service_fulfillments;
create policy service_fulfillments_owner_select on public.service_fulfillments for select to authenticated using (
  public.nexus_is_active_admin() or exists (select 1 from public.tenant_memberships tm where tm.tenant_id = (select co.tenant_id from public.client_orders co where co.id = service_fulfillments.order_id) and tm.user_id = auth.uid() and tm.role = 'client' and tm.client_id = service_fulfillments.client_id)
);
drop policy if exists service_fulfillments_admin_manage on public.service_fulfillments;
create policy service_fulfillments_admin_manage on public.service_fulfillments for all to authenticated using (public.nexus_is_active_admin()) with check (public.nexus_is_active_admin());
grant select, update on public.service_fulfillments to authenticated;

drop policy if exists readiness_packets_owner_select on public.readiness_packets;
create policy readiness_packets_owner_select on public.readiness_packets for select to authenticated using (
  public.nexus_is_active_admin() or (client_visible = true and status = 'delivered' and exists (select 1 from public.client_orders co join public.tenant_memberships tm on tm.tenant_id = co.tenant_id where co.id = readiness_packets.order_id and tm.user_id = auth.uid() and tm.role = 'client' and tm.client_id = readiness_packets.client_id))
);
drop policy if exists readiness_packets_admin_manage on public.readiness_packets;
create policy readiness_packets_admin_manage on public.readiness_packets for all to authenticated using (public.nexus_is_active_admin()) with check (public.nexus_is_active_admin());
grant select, insert, update on public.readiness_packets to authenticated;

drop policy if exists consultation_owner_select on public.consultation_requests;
create policy consultation_owner_select on public.consultation_requests for select to authenticated using (public.nexus_is_active_admin() or exists (select 1 from public.client_orders co join public.tenant_memberships tm on tm.tenant_id = co.tenant_id where co.id = consultation_requests.order_id and tm.user_id = auth.uid() and tm.role = 'client' and tm.client_id = consultation_requests.client_id));
drop policy if exists consultation_admin_manage on public.consultation_requests;
create policy consultation_admin_manage on public.consultation_requests for all to authenticated using (public.nexus_is_active_admin()) with check (public.nexus_is_active_admin());
grant select, update, insert on public.consultation_requests to authenticated;

drop policy if exists referral_admin_manage on public.referral_attributions;
create policy referral_admin_manage on public.referral_attributions for all to authenticated using (public.nexus_is_active_admin()) with check (public.nexus_is_active_admin());
grant select, update, insert on public.referral_attributions to authenticated;

-- Provider identifiers, customer/order ownership, and paid amount cannot be changed by a UI admin.
create or replace function public.nexus_revenue_immutable_fields()
returns trigger language plpgsql as $$
begin
  if coalesce(current_setting('request.jwt.claim.role', true), '') <> 'service_role' then
    if new.tenant_id <> old.tenant_id or new.client_id <> old.client_id or new.auth_user_id <> old.auth_user_id or new.offer_id <> old.offer_id or new.amount_cents <> old.amount_cents or new.currency <> old.currency then
      raise exception 'immutable_order_fields';
    end if;
    if new.provider_checkout_session_id is distinct from old.provider_checkout_session_id then raise exception 'immutable_provider_checkout_id'; end if;
    if new.provider_payment_intent_id is distinct from old.provider_payment_intent_id then raise exception 'immutable_provider_payment_id'; end if;
    if new.status is distinct from old.status or new.payment_status is distinct from old.payment_status or new.paid_at is distinct from old.paid_at or new.refunded_at is distinct from old.refunded_at then raise exception 'payment_state_is_server_verified'; end if;
  end if;
  new.updated_at = now();
  return new;
end;
$$;
drop trigger if exists client_orders_immutable_fields on public.client_orders;
create trigger client_orders_immutable_fields before update on public.client_orders for each row execute function public.nexus_revenue_immutable_fields();

create or replace function public.nexus_readiness_packet_immutable_delivery()
returns trigger language plpgsql as $$
begin
  if old.status = 'delivered' and (new.status <> old.status or new.content <> old.content or new.version <> old.version or new.client_visible <> old.client_visible) then raise exception 'delivered_packet_is_immutable'; end if;
  new.updated_at = now();
  return new;
end;
$$;
drop trigger if exists readiness_packets_immutable_delivery on public.readiness_packets;
create trigger readiness_packets_immutable_delivery before update on public.readiness_packets for each row execute function public.nexus_readiness_packet_immutable_delivery();

commit;
