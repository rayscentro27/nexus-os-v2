#!/usr/bin/env python3
"""Seed the three active, test-mode service offers. Never enables live pricing."""
from __future__ import annotations
import argparse
from revenue_common import print_json, query, rest, settings

OFFERS = [
    ("offer_readiness_review_97", "readiness-review-97", "Credit & Funding Readiness Review", 1, 9700, "readiness_review", "STRIPE_TEST_PRICE_READINESS_REVIEW_97"),
    ("offer_readiness_action_plan_297", "readiness-action-plan-297", "Readiness Action Plan", 2, 29700, "action_plan", "STRIPE_TEST_PRICE_ACTION_PLAN_297"),
    ("offer_funding_readiness_concierge_497", "funding-readiness-concierge-497", "Funding Readiness Concierge", 3, 49700, "concierge", "STRIPE_TEST_PRICE_CONCIERGE_497"),
]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--seed", action="store_true")
    args = parser.parse_args()
    env = settings(); base = env.get("VITE_SUPABASE_URL", ""); key = env.get("SUPABASE_SERVICE_ROLE_KEY", "")
    rows = []
    for id_, slug, name, tier, cents, fulfillment, price_env in OFFERS:
        rows.append({"id": id_, "slug": slug, "name": name, "tier": tier, "price_cents": cents, "currency": "usd", "active": True, "fulfillment_type": fulfillment, "test_price_id_configured": bool(env.get(price_env, "").startswith("price_")), "terms_version": "readiness-services-v1"})
    if args.dry_run or not args.seed:
        print_json({"mode": "dry-run" if args.dry_run else "plan", "offers": rows, "live_mode_enabled": False})
        return
    if not base or not key: raise SystemExit("VITE_SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required server-side")
    for id_, slug, name, tier, cents, fulfillment, price_env in OFFERS:
        payload = {"id": id_, "slug": slug, "name": name, "tier": tier, "price_cents": cents, "currency": "usd", "description": name, "included_deliverables": [], "excluded_claims": ["funding approval guarantee", "credit deletion guarantee", "legal advice"], "consultation_entitlement": "none" if tier == 1 else "one_review_session" if tier == 2 else "priority_consultation", "active": True, "fulfillment_type": fulfillment, "test_price_id": env.get(price_env) if env.get(price_env, "").startswith("price_") else None, "public_route": "/readiness-review" if tier == 1 else "/readiness-action-plan" if tier == 2 else "/funding-readiness-concierge", "terms_version": "readiness-services-v1", "refund_policy_reference": "refund-policy-v1", "privacy_notice_reference": "privacy-notice-v1", "readiness_scope": ["credit", "business_foundation", "business_bankability", "funding_readiness"]}
        rest(base, key, f"/rest/v1/service_offers?id=eq.{id_}", "POST", payload, {"Prefer": "resolution=merge-duplicates"})
    if args.verify:
        print_json({"verified": query(base, key, "service_offers", "id,slug,tier,price_cents,currency,active,fulfillment_type", {"id": "in.(offer_readiness_review_97,offer_readiness_action_plan_297,offer_funding_readiness_concierge_497)"}), "live_mode_enabled": False})
    else: print_json({"seeded": 3, "live_mode_enabled": False})

if __name__ == "__main__": main()
