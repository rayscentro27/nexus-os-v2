#!/usr/bin/env python3
"""Phase 8 — Payment/billing readiness contract ONLY (no Stripe, no links, no charge)."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "partners"))
import launch_model as lm  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(); p.add_argument("--dry-run", action="store_true", default=True); p.add_argument("--json", action="store_true"); a = p.parse_args()
    offers = lm.payment_offers()
    r = {
        "ok": True, "title": "Payment Readiness Contract", "generated_at": lm.now(), "dry_run": True,
        "payment_offers": offers,
        "contract_meta": {"stripe_connected": False, "live_payment_links": False, "charges_enabled": False,
                          "subscriptions_active": False, "activation_status": "not_connected"},
        "counts": {"payment_offers": len(offers)},
        "summary": "Payment/billing is contract + placeholders only. Stripe not connected, no live links, no charges, no subscriptions active.",
        "safety": {**lm.SAFETY, "stripe_connected": False, "payment_link_activated": False, "client_charged": False,
                   "subscription_activated": False},
    }
    md = ["## Payment offers (placeholders, not_connected)"]
    for o in offers:
        md.append(f"- {o['offer_name']}: ${o['price']} ({o['billing_cycle']}) · {o['activation_status']} · {o['payment_link_placeholder']}")
    md += ["", "## Contract meta"] + [f"- {k}: {v}" for k, v in r["contract_meta"].items()]
    lm.write_report("payment_readiness_contract_latest", r, md)
    print(json.dumps(r, indent=2) if a.json else r["summary"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
