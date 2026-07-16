#!/usr/bin/env python3
"""Verify Persona D purchase-to-delivery state without printing private data."""
from __future__ import annotations
import argparse
from revenue_common import PERSONA_EMAIL, print_json, query, rest, require_synthetic_scope, settings

def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--persona", default="d", choices=["d"]); parser.add_argument("--offer", default="readiness-review-97"); parser.add_argument("--verify", action="store_true"); parser.add_argument("--require-delivered", action="store_true"); args = parser.parse_args()
    env = settings(); base = env.get("VITE_SUPABASE_URL", ""); key = env.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not base or not key: raise SystemExit("VITE_SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required server-side")
    users = rest(base, key, "/auth/v1/admin/users?per_page=1000").get("users", []); matches = [u for u in users if str(u.get("email", "")).lower() == PERSONA_EMAIL]
    if len(matches) != 1: raise SystemExit("expected exactly one Persona D Auth account")
    memberships = [m for m in query(base, key, "tenant_memberships", "tenant_id,user_id,client_id,role", {"user_id": f"eq.{matches[0]['id']}"}) if m.get("role") == "client"]
    if len(memberships) != 1: raise SystemExit("expected exactly one Persona D client membership")
    scope = memberships[0]; require_synthetic_scope(scope)
    orders = query(base, key, "client_orders", "id,order_number,status,payment_status,fulfillment_status,amount_cents,offer_id", {"client_id": f"eq.{scope['client_id']}"}); fulfillments = query(base, key, "service_fulfillments", "id,order_id,fulfillment_status,readiness_packet_id", {"client_id": f"eq.{scope['client_id']}"}); packets = query(base, key, "readiness_packets", "id,order_id,version,status,approval_status,client_visible", {"client_id": f"eq.{scope['client_id']}"}); events = []
    for order in orders: events += query(base, key, "payment_events", "id,provider_event_id,event_type,processed_status,order_id", {"order_id": f"eq.{order['id']}"})
    delivered = any(p.get("status") == "delivered" and p.get("client_visible") is True for p in packets); duplicate_fulfillment = len({f.get("order_id") for f in fulfillments}) != len(fulfillments); duplicate_events = len({e.get("provider_event_id") for e in events}) != len(events)
    result = {"persona": "D", "client_scope_verified": True, "orders": len(orders), "fulfillments": len(fulfillments), "packets": len(packets), "verified_events": len([e for e in events if e.get("processed_status") == "processed"]), "duplicate_fulfillment": duplicate_fulfillment, "duplicate_provider_events": duplicate_events, "delivered_packet_present": delivered, "payment_state": orders[0].get("payment_status") if orders else "missing", "live_mode_enabled": False}
    print_json(result)
    if args.require_delivered and not delivered: raise SystemExit("approved delivered packet not present")
    if duplicate_fulfillment or duplicate_events: raise SystemExit("idempotency verification failed")

if __name__ == "__main__": main()
