#!/usr/bin/env python3
"""Phase 10 — Hermes launch recommendations (internal/report-only, plain language)."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "partners"))
import launch_model as lm  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(); p.add_argument("--dry-run", action="store_true", default=True); p.add_argument("--json", action="store_true"); a = p.parse_args()
    needs_config = [c["partner_offer_id"] for c in lm.partner_config_checks() if c["needs_config"]]
    r = {
        "ok": True, "title": "Hermes Launch Recommendations", "generated_at": lm.now(), "dry_run": True,
        "approve_first": "The $97 Readiness Review — lowest risk, fastest money, and it funds the relationship.",
        "missing_partner_config": needs_config,
        "closest_to_launch": "$97 Readiness Review (offer + copy ready; only needs Ray approval + payment wiring later).",
        "lowest_risk": "$97 Readiness Review and SmartCredit placement (free DIY option always shown).",
        "fastest_money": "$97 Readiness Review at signup, then the ~$97/mo core subscription.",
        "needs_more_validation": "Online business bank referral terms (Bluevine/Mercury/Relay) and DocuPost affiliate terms.",
        "should_stay_blocked": [
            "Charging clients / activating payment links / activating subscriptions.",
            "Partner connector activation; SmartCredit login/scrape; DocuPost sending.",
            "Live Client Vault / 2nd Supabase / external AI on client data.",
        ],
        "do_tonight": [
            "Approve the $97 Readiness Review offer + copy (prep only).",
            "Approve SmartCredit placement + affiliate disclosure language.",
            "Add partner URLs for the needs_config partners, then re-validate.",
            "Keep payment + connectors off until explicitly approved.",
        ],
        "counts": {"partners_needing_config": len(needs_config)},
        "summary": "Approve the $97 Readiness Review first (lowest risk, fastest money); add partner URLs; keep payment/connectors blocked until approved.",
        "safety": {**lm.SAFETY, "internal_only": True},
    }
    md = ["## Hermes launch recommendations",
          f"- Approve first: {r['approve_first']}",
          f"- Closest to launch: {r['closest_to_launch']}",
          f"- Lowest risk: {r['lowest_risk']}",
          f"- Fastest money: {r['fastest_money']}",
          f"- Needs more validation: {r['needs_more_validation']}",
          f"- Missing partner config: {', '.join(needs_config) or 'none'}",
          "", "## Should stay blocked"] + [f"- {x}" for x in r["should_stay_blocked"]]
    md += ["", "## Do tonight"] + [f"- {x}" for x in r["do_tonight"]]
    lm.write_report("hermes_launch_recommendations_latest", r, md)
    print(json.dumps(r, indent=2) if a.json else r["summary"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
