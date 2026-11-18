#!/usr/bin/env python3
"""Read-only Printify discovery for the pilot mug (no product creation, no orders, no publishing)."""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT)]
from business_loop.commerce.governed_clients import PrintifyReader, job_context  # noqa: E402

OUT = ROOT / "reports/business_loop/printify_cost_r1.json"


def discover() -> dict:
    job_context("printify")
    p = PrintifyReader()
    report: dict = {"generated_at": datetime.now(timezone.utc).isoformat(), "mode": "READ_ONLY", "orders_placed": 0, "products_created": 0}
    st, shops = p.get("/shops.json")
    report["shops"] = [{"id": s.get("id"), "title": s.get("title"), "sales_channel": s.get("sales_channel")} for s in (shops or [])] if st == 200 else {"error": shops, "http": st}
    existing = []
    for s in report["shops"] if isinstance(report["shops"], list) else []:
        st2, prods = p.get(f"/shops/{s['id']}/products.json?limit=50")
        for pr in (prods or {}).get("data", []) if st2 == 200 else []:
            if re.search(r"mug", (pr.get("title") or "") + " " + json.dumps(pr.get("tags") or []), re.I):
                existing.append({"shop_id": s["id"], "product_id": pr.get("id"), "title": pr.get("title"), "visible": pr.get("visible"),
                                 "blueprint_id": pr.get("blueprint_id"), "print_provider_id": pr.get("print_provider_id"),
                                 "variants": [{"id": v.get("id"), "title": v.get("title"), "cost_cents": v.get("cost"), "price_cents": v.get("price"),
                                               "enabled": v.get("is_enabled")} for v in pr.get("variants", []) if v.get("is_enabled")][:6]})
    report["existing_mug_products"] = existing
    st, bps = p.get("/catalog/blueprints.json")
    mugs = [b for b in (bps or []) if st == 200 and re.search(r"\bmug\b", b.get("title", ""), re.I) and not re.search(r"travel|enamel|steel|tumbler|camp|latte|beer|glass", b.get("title", ""), re.I)]
    report["catalog_ceramic_mug_blueprints"] = [{"id": b["id"], "title": b["title"], "brand": b.get("brand"), "model": b.get("model")} for b in mugs[:15]]
    chosen = next((b for b in mugs if re.search(r"accent|11|15", b["title"], re.I) and "ceramic" in b["title"].lower()), mugs[0] if mugs else None)
    if chosen:
        bp = chosen["id"]
        st, provs = p.get(f"/catalog/blueprints/{bp}/print_providers.json")
        report["chosen_blueprint"] = {"id": bp, "title": chosen["title"], "description": re.sub("<[^>]+>", " ", chosen.get("description") or "")[:600]}
        report["providers"] = []
        for pv in (provs or [])[:4] if st == 200 else []:
            st3, var = p.get(f"/catalog/blueprints/{bp}/print_providers/{pv['id']}/variants.json")
            st4, ship = p.get(f"/catalog/blueprints/{bp}/print_providers/{pv['id']}/shipping.json")
            us_ship = [prof for prof in (ship or {}).get("profiles", []) if "US" in (prof.get("countries") or [])] if st4 == 200 else []
            report["providers"].append({
                "id": pv["id"], "title": pv.get("title"), "location": pv.get("location"),
                "variants": [{"id": v["id"], "title": v.get("title"), "options": v.get("options"),
                              "placeholders": [{"position": ph.get("position"), "width": ph.get("width"), "height": ph.get("height")} for ph in v.get("placeholders", [])]}
                             for v in (var or {}).get("variants", [])][:6] if st3 == 200 else {"http": st3},
                "shipping_handling_time": (ship or {}).get("handling_time") if st4 == 200 else None,
                "shipping_us": [{"variant_ids": prof.get("variant_ids", [])[:4], "first_item_cents": (prof.get("first_item") or {}).get("cost"),
                                 "additional_item_cents": (prof.get("additional_items") or {}).get("cost")} for prof in us_ship][:3],
                "shipping_countries_sample": sorted({c for prof in (ship or {}).get("profiles", []) for c in prof.get("countries", [])})[:25] if st4 == 200 else None})
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    r = discover()
    print(json.dumps({"shops": r["shops"], "existing_mug_products": len(r["existing_mug_products"]), "blueprint": r.get("chosen_blueprint", {}).get("title"),
                      "providers": [(p["title"], p.get("shipping_handling_time"), p.get("shipping_us")[:1]) for p in r.get("providers", [])]}, indent=1, default=str))
