#!/usr/bin/env python3
"""Provision Persona D without exposing credentials or marking payment paid."""
from __future__ import annotations
import argparse, uuid
from revenue_common import PERSONA_EMAIL, print_json, query, rest, require_synthetic_scope, settings

def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--persona", default="d", choices=["d"]); parser.add_argument("--offer", default="readiness-review-97"); parser.add_argument("--dry-run", action="store_true"); parser.add_argument("--verify", action="store_true")
    args = parser.parse_args(); env = settings(); base = env.get("VITE_SUPABASE_URL", ""); key = env.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if args.dry_run:
        print_json({"persona": "D", "email": PERSONA_EMAIL, "offer": args.offer, "synthetic_only": True, "creates_auth": False, "writes_paid": False}); return
    if not base or not key: raise SystemExit("VITE_SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required server-side")
    users = rest(base, key, "/auth/v1/admin/users?per_page=1000").get("users", [])
    matches = [u for u in users if str(u.get("email", "")).lower() == PERSONA_EMAIL]
    if len(matches) > 1: raise SystemExit("more than one Persona D Auth account found")
    if matches: user = matches[0]
    else:
        password = env.get("E2E_PERSONA_D_PASSWORD", "")
        if not password: raise SystemExit("E2E_PERSONA_D_PASSWORD must be loaded from ignored local environment")
        user = rest(base, key, "/auth/v1/admin/users", "POST", {"email": PERSONA_EMAIL, "password": password, "email_confirm": True, "user_metadata": {"full_name": "Synthetic Paid Readiness Client", "business_name": "Synthetic Readiness Studio"}})
    user_id = user.get("id")
    memberships = query(base, key, "tenant_memberships", "tenant_id,user_id,client_id,role", {"user_id": f"eq.{user_id}"})
    clients = [m for m in memberships if m.get("role") == "client"]
    if len(clients) != 1: raise SystemExit("Persona D must have exactly one client membership")
    scope = clients[0]; require_synthetic_scope(scope)
    offer = query(base, key, "service_offers", "id,slug,price_cents,terms_version", {"slug": f"eq.{args.offer}", "active": "eq.true"})
    if len(offer) != 1: raise SystemExit("requested active offer was not seeded")
    existing = query(base, key, "client_orders", "id,order_number,status,amount_cents", {"client_id": f"eq.{scope['client_id']}", "offer_id": f"eq.{offer[0]['id']}", "status": "in.(draft,checkout_created,payment_pending,paid)"})
    if not existing:
        order_id = str(uuid.uuid4()); order_number = "GC-TEST-D-" + order_id.replace("-", "")[-10:].upper()
        rest(base, key, "/rest/v1/client_orders", "POST", {"id": order_id, "tenant_id": scope["tenant_id"], "client_id": scope["client_id"], "auth_user_id": user_id, "offer_id": offer[0]["id"], "order_number": order_number, "status": "draft", "amount_cents": offer[0]["price_cents"], "currency": "usd", "payment_provider": "stripe", "payment_status": "unpaid", "fulfillment_status": "not_started", "terms_version": offer[0]["terms_version"], "terms_accepted_at": None})
        existing = [{"id": order_id, "order_number": order_number, "status": "draft", "amount_cents": offer[0]["price_cents"]}]
    print_json({"persona": "D", "email": PERSONA_EMAIL, "tenant_id": scope["tenant_id"], "client_id": scope["client_id"], "offer": args.offer, "order": existing[0], "payment_written": False, "synthetic_only": True})

if __name__ == "__main__": main()
