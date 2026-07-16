#!/usr/bin/env python3
"""Reset Persona D revenue rows only; Auth, client, offers, and other personas remain."""
from __future__ import annotations
import argparse, urllib.parse
from revenue_common import PERSONA_EMAIL, print_json, query, rest, require_synthetic_scope, settings

def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--persona", default="d", choices=["d"]); parser.add_argument("--dry-run", action="store_true"); parser.add_argument("--verify", action="store_true"); parser.add_argument("--reset", action="store_true"); args = parser.parse_args()
    env = settings(); base = env.get("VITE_SUPABASE_URL", ""); key = env.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if args.dry_run:
        print_json({"persona": "D", "email": PERSONA_EMAIL, "target_tables": ["payment_events", "readiness_packets", "consultation_requests", "referral_attributions", "service_fulfillments", "client_orders"], "auth_deleted": False, "client_deleted": False, "other_personas_touched": False}); return
    if not args.reset: raise SystemExit("pass --reset or --dry-run")
    if not base or not key: raise SystemExit("VITE_SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required server-side")
    users = rest(base, key, "/auth/v1/admin/users?per_page=1000").get("users", []); matches = [u for u in users if str(u.get("email", "")).lower() == PERSONA_EMAIL]
    if len(matches) != 1: raise SystemExit("expected exactly one Persona D Auth account")
    membership = query(base, key, "tenant_memberships", "tenant_id,user_id,client_id,role", {"user_id": f"eq.{matches[0]['id']}"}); clients = [m for m in membership if m.get("role") == "client"]
    if len(clients) != 1: raise SystemExit("expected exactly one Persona D client membership")
    scope = clients[0]; require_synthetic_scope(scope); orders = query(base, key, "client_orders", "id", {"client_id": f"eq.{scope['client_id']}"}); order_ids = [o["id"] for o in orders]
    counts = {}
    for table, column in [("payment_events", "order_id"), ("readiness_packets", "order_id"), ("consultation_requests", "order_id"), ("referral_attributions", "order_id"), ("service_fulfillments", "order_id"), ("client_orders", "id")]:
        count = 0
        for order_id in order_ids:
            filter_value = urllib.parse.quote(str(order_id), safe="")
            rows = rest(base, key, f"/rest/v1/{table}?{column}=eq.{filter_value}")
            if rows: rest(base, key, f"/rest/v1/{table}?{column}=eq.{filter_value}", "DELETE"); count += len(rows)
        counts[table] = count
    print_json({"persona": "D", "client_id": scope["client_id"], "deleted": counts, "auth_deleted": False, "client_deleted": False, "other_personas_touched": False})

if __name__ == "__main__": main()
