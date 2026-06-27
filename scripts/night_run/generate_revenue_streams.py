#!/usr/bin/env python3
"""Part 8 — Four revenue streams (internal/report-only; proposed, not launched)."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import night_run_model as nm  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(); p.add_argument("--dry-run", action="store_true", default=True); p.add_argument("--json", action="store_true"); a = p.parse_args()
    affiliate_items = [{"category": c, "recommended_partner": rp, "diy_option": diy, "revenue_opportunity_score": sc}
                       for (c, rp, diy, sc) in nm.AFFILIATE_STREAM_ITEMS]
    r = {
        "ok": True, "title": "Nexus Revenue Streams", "generated_at": nm.now(), "dry_run": True,
        "revenue_streams": nm.REVENUE_STREAMS,
        "affiliate_items": affiliate_items,
        "subscription_tiers": [{"tier": t["name"], "monthly": t["recommended_monthly"]} for t in nm.GOCLEAR_TIERS],
        "status": "proposed",
        "counts": {"streams": len(nm.REVENUE_STREAMS), "affiliate_items": len(affiliate_items)},
        "summary": "Four revenue streams proposed: readiness review ($97), monthly subscription (tiered), affiliate/partner engine, funding commission pipeline. All proposed only — nothing launched.",
        "safety": {**nm.SAFETY, "streams_launched": False},
    }
    md = ["## Revenue streams (proposed)"]
    for s in nm.REVENUE_STREAMS:
        md.append(f"### {s['name']}")
        md.append(f"- trigger: {s['trigger']}")
        md.append(f"- pricing: {s['pricing']}")
        md.append(f"- approval gate: {s['approval_gate']}")
        md.append(f"- upsell: {s['upsell']}")
        md.append("")
    md += ["## Affiliate items (partner + DIY)"]
    md += [f"- {i['category']}: {i['recommended_partner']} / DIY: {i['diy_option']} (score {i['revenue_opportunity_score']})" for i in affiliate_items]
    nm.write_report("nexus_revenue_streams_latest", r, md)
    print(json.dumps(r, indent=2) if a.json else r["summary"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
