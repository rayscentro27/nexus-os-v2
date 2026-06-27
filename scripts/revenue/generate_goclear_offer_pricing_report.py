#!/usr/bin/env python3
"""Phase 4 — GoClear offer pricing validation report (report-only)."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "partners"))
import launch_model as lm  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(); p.add_argument("--dry-run", action="store_true", default=True); p.add_argument("--json", action="store_true"); a = p.parse_args()
    validations = lm.pricing_validations()
    offers = [{"offer_id": o[0], "offer_name": o[1], "price": o[2], "price_range": o[3], "billing_cycle": o[4],
               "client_stage": o[5], "trigger_condition": o[6], "upgrade_path": o[7], "downgrade_path": o[8],
               "ray_approval_status": "pending_review", "launch_status": "proposed", "approval_required": True}
              for o in lm.GOCLEAR_OFFERS]
    out_of_range = [v for v in validations if v["verdict"] in ("below_range", "above_range")]
    r = {
        "ok": True, "title": "GoClear Offer Pricing Validation", "generated_at": lm.now(), "dry_run": True,
        "disclaimer": "Internal market-research estimates to validate, not live offers. No client charged.",
        "offers": offers, "pricing_validations": validations,
        "counts": {"offers": len(offers), "in_range_or_one_time": len(validations) - len(out_of_range),
                   "out_of_range": len(out_of_range)},
        "summary": f"Validated {len(offers)} GoClear offers against market bands; {len(out_of_range)} outside band (informational). All offers proposed/approval-required.",
        "safety": {**lm.SAFETY, "client_charged": False, "subscription_activated": False},
    }
    md = ["## Offers"]
    for o in offers:
        md.append(f"- {o['offer_name']}: ${o['price']} ({o['billing_cycle']}) range {o['price_range']} · stage {o['client_stage']} · upgrade {o['upgrade_path']}")
    md += ["", "## Pricing validation"]
    for v in validations:
        md.append(f"- {v['offer_name']}: {v['verdict']} vs {v['reference_band']} — {v['note']}")
    lm.write_report("goclear_offer_pricing_validation_latest", r, md)
    print(json.dumps(r, indent=2) if a.json else r["summary"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
