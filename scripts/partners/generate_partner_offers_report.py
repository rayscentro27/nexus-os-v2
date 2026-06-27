#!/usr/bin/env python3
"""Phase 2 — Partner offers registry report (report-only)."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import launch_model as lm  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(); p.add_argument("--dry-run", action="store_true", default=True); p.add_argument("--json", action="store_true"); a = p.parse_args()
    offers = lm.partner_offer_dicts()
    r = {
        "ok": True, "title": "Partner Offers Registry", "generated_at": lm.now(), "dry_run": True,
        "partner_offers": offers,
        "counts": {
            "total": len(offers),
            "affiliate": sum(1 for o in offers if o["revenue_type"] == "affiliate"),
            "referral": sum(1 for o in offers if o["revenue_type"] == "referral"),
            "free_official": sum(1 for o in offers if o["revenue_type"] == "free_official"),
            "needs_config": sum(1 for o in offers if o["configuration_status"] == "needs_config"),
            "active": sum(1 for o in offers if o["activation_status"] == "active"),
        },
        "summary": f"{len(offers)} partner offers registered (proposed). No affiliate URL activated, no partner connector enabled.",
        "safety": {**lm.SAFETY, "affiliate_url_activated": False, "partner_connector_activated": False},
    }
    md = ["## Partner offers"]
    for o in offers:
        md.append(f"- [{o['activation_status']}/{o['configuration_status']}] {o['partner_name']} ({o['category']}) · {o['revenue_type']} · DIY: {o['diy_option_name']}")
    lm.write_report("partner_offers_latest", r, md)
    print(json.dumps(r, indent=2) if a.json else r["summary"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
