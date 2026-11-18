#!/usr/bin/env python3
"""Assemble NEXUS_COMMERCE_CONVERSION_AND_MEASUREMENT_R1 state + reports for the ONE mug pilot.

Reads verified evidence produced by the other commerce modules, updates the
existing project's commerce offer (ESTIMATED / VERIFIED / TEST / LIVE kept
distinct), supersedes the stale Facebook approval, prepares the go-live package,
and writes the measurement summary. Never publishes, never activates payments.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT)]
from business_loop.commerce import funnel as F  # noqa: E402
from business_loop.project_state import ProjectStore  # noqa: E402
from business_loop import loop as L  # noqa: E402

REPORTS = ROOT / "reports/business_loop"


def _load(name: str) -> dict:
    p = REPORTS / name
    return json.loads(p.read_text()) if p.exists() else {}


def main() -> dict:
    printify_raw = _load("printify_cost_r1.json")
    choice = next(p for p in printify_raw["providers"] if p["id"] == 99)
    ship_15 = next(s for s in choice["shipping_us"] if 104692 in s["variant_ids"])
    printify = {"product_id": "NONE (no products in shops; draft creation not authorized)", "blueprint_id": 478,
                "blueprint": printify_raw["chosen_blueprint"]["title"], "provider_id": 99, "provider": choice["title"],
                "variant_id": 104692, "variant": "15oz", "print_area_px": next(v for v in choice["variants"] if v["id"] == 104692)["placeholders"],
                "us_shipping_first_item_usd": ship_15["first_item_cents"] / 100, "us_shipping_additional_item_usd": ship_15["additional_item_cents"] / 100,
                "handling_time": choice["shipping_handling_time"], "regions_sample": choice.get("shipping_countries_sample"),
                "description_facts": "white ceramic, BPA/lead-free, microwave & dishwasher safe (Printify catalog)",
                "base_cost_usd": None, "fulfillment": "Printify print-on-demand; no inventory", "orders_placed": 0}
    pricing = F.pricing(printify)
    stripe_state = _load("stripe_test_checkout_r1.json")
    meta = _load("meta_metrics_capability_r1.json")
    copy = F.copy_package(form_verified=True)

    store = ProjectStore()
    project = L.ensure_project(store)
    primary = "dist/creative/business_loop/proj_98ef515bccee4b58/primary_square_1080.jpg"
    approval = F.supersede_and_request_facebook(project, primary, copy["copy"]["FACEBOOK"])
    storefront_issues = ["Landing 'design intent' section describes a stoneware concept (raw unglazed clay base, dense heft); the fulfillable "
                         "Printify item is a white glossy ceramic mug - revise before live sales."]
    golive = F.go_live_package(printify, pricing, stripe_state, storefront_issues)
    (ROOT / "dist/creative/holiday_commerce_go_live_approval_request.json").write_text(json.dumps(golive, indent=1) + "\n")

    m = F.measure(meta={"facebook": meta.get("facebook"), "instagram": meta.get("instagram")})
    analysis = F.analyze(m)
    offer = {
        "PRODUCT_ID": "prod_stoneware_mug_14oz", "PRINTIFY_PRODUCT_ID": None, "PRINTIFY_BLUEPRINT": "478 / provider 99 / variant 104692 (15oz)",
        "PRODUCT_NAME": "The 6:12 AM Ritual Mug (Studio Preview)",
        "PRICE": {"value": 48.0, "status": "ESTIMATED (staged; not authoritative)", "recommended": {"value": 29.0, "status": "PROPOSED"}},
        "BASE_COST": {"value": None, "status": "NOT_VERIFIED"},
        "SHIPPING_ESTIMATE": {"value": printify["us_shipping_first_item_usd"], "status": "VERIFIED (Printify catalog, US)"},
        "GROSS_MARGIN_ESTIMATE": {"value": pricing["gross_margin_at_recommended"], "status": "NOT_AVAILABLE until base cost VERIFIED"},
        "FULFILLMENT_METHOD": {"value": printify["fulfillment"], "status": "VERIFIED (catalog availability)"},
        "STOREFRONT_URL": F.STORE_URL, "INTEREST_FORM_STATUS": "LIVE (verified in production)",
        "CHECKOUT_STATUS": "BLOCKED: no Stripe TEST key exists (the 'test' credential holds a LIVE key - refused)",
        "PUBLICATION_STATUS": "WAITING_FOR_RAY_APPROVAL", "SALES_STATUS": "NOT_FOR_SALE (interest capture only)",
        "updated_at": datetime.now(timezone.utc).isoformat()}
    approvals = [a for a in project.get("approvals_required") or [] if a.get("approval_request_id") != "apr_req_4fe6eb45cb6cc2fa"
                 and a.get("approval_kind") != "COMMERCE_GO_LIVE"]
    approvals += [{"approval_request_id": approval["PUBLICATION_APPROVAL_ID"], "platform": "FACEBOOK", "owner_command": approval["owner_commands"][0],
                   "then": approval["owner_commands"][1], "supersedes": "apr_req_4fe6eb45cb6cc2fa"},
                  {"approval_kind": "COMMERCE_GO_LIVE", "approval_id": golive["approval_id"], "status": golive["status"],
                   "file": "dist/creative/holiday_commerce_go_live_approval_request.json", "paused_action_only": True}]
    project = store.save_project(project, commerce_offer=offer, approvals_required=approvals, current_department="DISTRIBUTION",
                                 current_stage="AWAITING_PUBLICATION_APPROVAL", next_action=analysis["NEXT_BEST_ACTION"]["action"],
                                 last_conversion_analysis=analysis)
    store.event(project, "COMMERCE_CONVERSION_R1", detail="funnel instrumented; offer state updated", approval=approval["PUBLICATION_APPROVAL_ID"])
    costs = {"AI_MODEL_COST": 0.0, "MEDIA_COST": 0.0, "ANALYTICS_COST": 0.0, "COMMERCE_COST": 0.0, "AD_SPEND": 0.0, "TOTAL_COST": 0.0, "UNAUTHORIZED_COST": 0.0,
             "basis": "Supabase/Cloudflare Pages free usage; Printify reads free; no Stripe calls made; no orders; no ads."}
    payload = {"task": "NEXUS_COMMERCE_CONVERSION_AND_MEASUREMENT_R1", "project_id": project["project_id"], "generated_at": datetime.now(timezone.utc).isoformat(),
               "tracked_urls": F.tracked_urls(), "copy": copy, "printify": printify, "pricing": pricing, "stripe": stripe_state or {"status": "NOT_CREATED (no test key)"},
               "offer": offer, "publication_approval": approval, "go_live_approval": {"approval_id": golive["approval_id"], "status": golive["status"]},
               "ab_test": F.ab_plan(), "meta_capability": meta, "measurement": m, "analysis": analysis, "costs": costs}
    F.write_reports(payload)
    return payload


if __name__ == "__main__":
    p = main()
    print(json.dumps({"approval": p["publication_approval"], "go_live": p["go_live_approval"], "measurement": {k: p["measurement"][k] for k in
                      ("PAGE_VIEWS", "UNIQUE_SESSIONS", "CTA_CLICKS", "INTEREST_SUBMISSIONS", "CHECKOUT_CLICKS", "PURCHASES", "REVENUE")},
                      "nba": p["analysis"]["NEXT_BEST_ACTION"], "cta_validated": p["copy"]["CTA_VALIDATED"]}, indent=1, default=str))
