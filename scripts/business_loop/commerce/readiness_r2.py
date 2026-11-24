#!/usr/bin/env python3
"""NEXUS_COMMERCE_PRODUCT_TRUTH_AND_GO_LIVE_READINESS_R2 assembler (no publish, no live payments, no orders)."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "scripts/creative"), str(ROOT)]
from business_loop import loop as L  # noqa: E402
from business_loop.commerce import funnel as F  # noqa: E402
from business_loop.commerce import storefront_patch as P  # noqa: E402
from business_loop.project_state import ProjectStore  # noqa: E402

REPORT = ROOT / "reports/business_loop/commerce_readiness_r2_latest.json"
GOLIVE = ROOT / "dist/creative/holiday_commerce_go_live_approval_request.json"
R2_H1 = "dist/creative/business_loop/proj_98ef515bccee4b58/r2_h1_square_1080.jpg"
PRODUCT_ID = "prod_stoneware_mug_14oz"  # immutable tracking identity (RLS policies, events, leads, approvals)


def main() -> dict:
    from product_truth_validator import ProductTruthValidator as Truth
    draft = json.loads((ROOT / "reports/business_loop/printify_draft_r2.json").read_text())
    cat = json.loads((ROOT / "reports/business_loop/printify_cost_r1.json").read_text())
    choice = next(p for p in cat["providers"] if p["id"] == 99)
    ship = next(s for s in choice["shipping_us"] if 104692 in s["variant_ids"])
    printify = {"product_id": draft["product_id"], "shop_id": draft["shop_id"], "product_name": draft["title"],
                "variant": {"id": 104692, "title": draft["variant"]["title"], "sku": draft["variant"]["sku"], "grams": draft["variant"]["grams"]},
                "blueprint_id": 478, "provider_id": 99, "provider": choice["title"],
                "base_cost_usd": draft["variant"]["cost_cents"] / 100, "us_shipping_first_item_usd": ship["first_item_cents"] / 100,
                "us_shipping_additional_item_usd": ship["additional_item_cents"] / 100, "currency": "USD",
                "production_time": choice["shipping_handling_time"], "regions_sample": choice.get("shipping_countries_sample"),
                "published": False, "external_channel": draft.get("external"), "orders": 0}
    pricing = F.pricing(printify)
    copy = F.copy_package(form_verified=True)
    page_text = P.visible_text(P.PAGE.read_text())
    truth = {"page_validator": Truth.audit_copy(page_text)["status"], "page_banned_terms": sorted({m.lower() for m in P.BANNED.findall(page_text)}),
             "page_uses_printify_mockup": P.MOCKUP in P.PAGE.read_text(),
             "page_concept_media_removed": "meta_holiday_ceramic_mug_1794355016.webp" not in P.PAGE.read_text(),
             "hooks": {h: Truth.audit_copy(t)["status"] for h, t in F.HOOKS.items()},
             "social_copy": {ch: c["truth"] for ch, c in copy["checks"].items()}, "cta_validated": copy["CTA_VALIDATED"]}
    truth["PRODUCT_TRUTH_CHECK"] = "PASS" if (truth["page_validator"] == "PASS" and not truth["page_banned_terms"] and truth["page_uses_printify_mockup"]
                                               and truth["page_concept_media_removed"] and all(v == "PASS" for v in truth["hooks"].values())
                                               and copy["CTA_VALIDATED"]) else "FAIL"

    store = ProjectStore()
    project = L.ensure_project(store)
    approval = F.supersede_and_request_facebook(project, R2_H1, copy["copy"]["FACEBOOK"], old_request_id="apr_req_a385caddb64d1c34",
                                                file_tag="r2_truth_h1", purpose="COMMERCE_READINESS_R2_TRUTH_H1")
    golive = F.go_live_package(printify, pricing, {}, ["Optional: shrink the printed mark slightly so '6:12 AM' clears the wrap edge (draft metadata update)"])
    GOLIVE.write_text(json.dumps(golive, indent=1) + "\n")
    product = {"PRODUCT_ID": PRODUCT_ID, "id_status": "HISTORICAL_IMMUTABLE_IDENTITY (name is not descriptive; see display metadata)",
               "CANONICAL_PRODUCT_ID": PRODUCT_ID, "display_name": "The 6:12 AM Ritual Mug - 15 oz White Ceramic",
               "material": "white ceramic, glossy (VERIFIED: Printify spec)", "capacity": "15 oz (VERIFIED: Printify variant)",
               "printify": printify, "supersedes_description": "stoneware concept (prod_stoneware_mug_14oz original description)",
               "lineage": {"events_and_leads_keyed_on": PRODUCT_ID, "rls_policies_keyed_on": PRODUCT_ID, "approvals_keyed_on_project": project["project_id"]}}
    offer = {**(project.get("commerce_offer") or {}), "PRODUCT_ID": PRODUCT_ID, "PRINTIFY_PRODUCT_ID": printify["product_id"],
             "PRODUCT_NAME": product["display_name"],
             "PRICE": {"value": pricing["recommended_price"], "status": "STAGED (recommended; not live)", "previous_staged": 48.0},
             "BASE_COST": {"value": printify["base_cost_usd"], "status": "VERIFIED (Printify draft variant cost)"},
             "SHIPPING_ESTIMATE": {"value": printify["us_shipping_first_item_usd"], "status": "VERIFIED (Printify catalog, US first item)"},
             "GROSS_MARGIN_ESTIMATE": {"value": pricing["gross_margin_at_recommended"], "status": "ESTIMATE (card fee estimated)"},
             "FULFILLMENT_METHOD": {"value": "Printify print-on-demand (provider 99)", "status": "VERIFIED"},
             "CHECKOUT_STATUS": "BLOCKED_MISSING_REAL_TEST_KEY", "PUBLICATION_STATUS": "WAITING_FOR_RAY_APPROVAL",
             "SALES_STATUS": "NOT_FOR_SALE (interest capture only)", "updated_at": datetime.now(timezone.utc).isoformat()}
    approvals = [a for a in project.get("approvals_required") or [] if a.get("approval_request_id") != "apr_req_a385caddb64d1c34" and a.get("approval_kind") != "COMMERCE_GO_LIVE"]
    approvals += [{"approval_request_id": approval["PUBLICATION_APPROVAL_ID"], "platform": "FACEBOOK", "stage": "A_INTEREST_CAMPAIGN",
                   "owner_command": approval["owner_commands"][0], "then": approval["owner_commands"][1], "supersedes": "apr_req_a385caddb64d1c34"},
                  {"approval_kind": "COMMERCE_GO_LIVE", "stage": "B_LIVE_SALES", "approval_id": golive["approval_id"], "status": golive["status"],
                   "file": str(GOLIVE.relative_to(ROOT)), "paused_action_only": True}]
    project = store.save_project(project, commerce_offer=offer, product_record=product, approvals_required=approvals,
                                 next_action="Ray: review publication approval to start Stage A real-traffic test")
    store.event(project, "COMMERCE_READINESS_R2", detail="product truth reconciled; verified Printify cost; approvals rebuilt",
                printify_product=printify["product_id"], publication_approval=approval["PUBLICATION_APPROVAL_ID"], go_live=golive["approval_id"])
    payload = {"task": "NEXUS_COMMERCE_PRODUCT_TRUTH_AND_GO_LIVE_READINESS_R2", "generated_at": datetime.now(timezone.utc).isoformat(),
               "printify": printify, "pricing": pricing, "truth": truth, "copy": copy, "product": product, "offer": offer,
               "publication_approval": approval, "go_live": {"approval_id": golive["approval_id"], "covers": golive["covers"]},
               "stages": {"INTEREST_CAMPAIGN_READY": "YES (pending publication approval)", "LIVE_SALES_READY": "NO_PENDING_TEST_CHECKOUT_AND_APPROVAL"},
               "costs": {"TOTAL_COST": 0.0, "UNAUTHORIZED_COST": 0.0, "printify_writes": draft["writes"], "orders": 0, "stripe_calls": 0}}
    REPORT.write_text(json.dumps(payload, indent=2, default=str) + "\n")
    return payload


if __name__ == "__main__":
    p = main()
    print(json.dumps({"truth": p["truth"]["PRODUCT_TRUTH_CHECK"], "approval": p["publication_approval"], "go_live": p["go_live"]["approval_id"],
                      "price": p["pricing"]["recommended_price"], "gp": p["pricing"]["gross_profit_at_recommended"],
                      "gm": p["pricing"]["gross_margin_at_recommended"]}, indent=1))
