-- Phase 6.1: deployed PostgREST service-role requests identify as current_user
-- = service_role; their request.jwt.claim.role setting is not populated.
-- Preserve client/admin immutability while allowing only the server role to
-- advance provider-verified payment fields.
begin;

create or replace function public.nexus_revenue_immutable_fields()
returns trigger language plpgsql as $$
begin
  if current_user <> 'service_role' and coalesce(current_setting('request.jwt.claim.role', true), '') <> 'service_role' then
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

commit;
