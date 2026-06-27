#!/usr/bin/env python3
"""Part 6 — GoClear subscription market research (internal/report-only, no scraping)."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import night_run_model as nm  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(); p.add_argument("--dry-run", action="store_true", default=True); p.add_argument("--json", action="store_true"); a = p.parse_args()
    pricing_bands = {"low": [39, 69], "core": [79, 129], "premium": [149, 297], "post_funding": [99, 249]}
    r = {
        "ok": True, "title": "GoClear Subscription Market Research", "generated_at": nm.now(), "dry_run": True,
        "disclaimer": "Internal market-research estimates to validate, not live offers. No client charged.",
        "market_price_bands": nm.MARKET_PRICE_BANDS,
        "competitor_plan_features": nm.COMPETITOR_PLAN_FEATURES,
        "recommended_pricing_bands": pricing_bands,
        "recommended_tiers": nm.GOCLEAR_TIERS,
        "recommended_core_monthly": 97,
        "why_clients_stay_after_credit_repair": [
            "Ongoing score tracking + monitoring (SmartCredit).",
            "Business credit building continues after personal credit improves.",
            "Convenience: dashboard, reminders, letter/document tracking, prepared recommendations.",
            "Path to funding readiness keeps a clear next goal.",
        ],
        "post_credit_repair_next_tier": [
            "business credit building", "vendor accounts", "business bankability", "funding readiness",
            "funding applications prep", "grant/funding opportunity monitoring", "monthly financial readiness tracking",
        ],
        "counts": {"market_bands": len(nm.MARKET_PRICE_BANDS), "tiers": len(nm.GOCLEAR_TIERS)},
        "summary": "Recommended GoClear core tier ~$97/mo (range $79-$129), with $49 entry and $197 funding-readiness tiers; clients retain via ongoing tracking and the path to funding.",
        "safety": {**nm.SAFETY, "scraping": False, "report_only": True},
    }
    md = ["## Market price bands (USD/mo, validate)"]
    md += [f"- {b['category']}: ${b['low']}-${b['high']} (typical ${b['typical']})" for b in nm.MARKET_PRICE_BANDS]
    md += ["", "## Recommended GoClear tiers"]
    for t in nm.GOCLEAR_TIERS:
        md.append(f"### {t['name']} — ~${t['recommended_monthly']}/mo (range ${t['range'][0]}-${t['range'][1]})")
        md.append(f"- includes: {', '.join(t['includes'])}")
        md.append(f"- retention: {t['retention_reason']}")
        md.append(f"- next tier: {t['next_tier'] or 'none'}")
        md.append("")
    md += ["## Why clients stay after credit repair"] + [f"- {x}" for x in r["why_clients_stay_after_credit_repair"]]
    md += ["", "## Post-credit-repair next tier"] + [f"- {x}" for x in r["post_credit_repair_next_tier"]]
    nm.write_report("goclear_subscription_market_research_latest", r, md)
    print(json.dumps(r, indent=2) if a.json else r["summary"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
