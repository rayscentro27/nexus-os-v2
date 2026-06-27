#!/usr/bin/env python3
"""Overnight money-opportunity research (internal/report-only). Also emits the affiliate queue."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import money_opportunity_model as mo  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(); p.add_argument("--dry-run", action="store_true", default=True); p.add_argument("--json", action="store_true"); a = p.parse_args()
    items = mo.ranked()
    research = {
        "ok": True, "title": "Money Opportunity Research", "generated_at": mo.now(), "dry_run": True,
        "publish_status": "draft_only", "approval_required": True,
        "research_categories": mo.RESEARCH_CATEGORIES,
        "opportunities": items,
        "counts": {"opportunities": len(items), "categories": len(mo.RESEARCH_CATEGORIES)},
        "summary": f"Researched {len(items)} money opportunities across {len(mo.RESEARCH_CATEGORIES)} categories (curated/internal, not scraped). Draft-only.",
        "safety": {**mo.SAFETY, "external_action_performed": False, "client_contacted": False, "money_spent": False, "client_charged": False},
    }
    md = ["## Research categories"] + [f"- {c}" for c in mo.RESEARCH_CATEGORIES]
    md += ["", "## Opportunities (ranked)"]
    for o in items:
        md.append(f"- [{o['overall_score']}] {o['title']} ({', '.join(o['opportunity_types'])}) — {o['ray_next_action']}")
    mo.write_report("money_opportunity_research_latest", research, md)

    # Affiliate opportunity queue
    aff = mo.needs_affiliate_approval()
    affq = {
        "ok": True, "title": "Overnight Affiliate Opportunity Queue", "generated_at": mo.now(), "dry_run": True,
        "publish_status": "draft_only", "approval_required": True,
        "affiliate_opportunities": [{"title": o["title"], "source_category": o["source_category"],
                                     "affiliate_potential": o["scores"]["affiliate_potential"],
                                     "ray_next_action": o["ray_next_action"]} for o in aff],
        "counts": {"affiliate_opportunities": len(aff)},
        "summary": f"{len(aff)} affiliate opportunities queued (approval + program application required). No partner contacted.",
        "safety": {**mo.SAFETY, "partner_contacted": False, "affiliate_url_activated": False},
    }
    md2 = ["## Affiliate opportunity queue"]
    for o in sorted(aff, key=lambda x: x["scores"]["affiliate_potential"], reverse=True):
        md2.append(f"- [{o['scores']['affiliate_potential']}] {o['title']} — {o['ray_next_action']}")
    mo.write_report("overnight_affiliate_opportunity_queue_latest", affq, md2)

    print(json.dumps(research, indent=2) if a.json else research["summary"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
