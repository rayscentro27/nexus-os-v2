#!/usr/bin/env python3
"""Content Opportunity Lab v1."""
from __future__ import annotations

import argparse
import json

from common import ROOT, candidate, now, read_csv, write_live_tasks, write_report

KEYWORDS = ROOT / "tests" / "fixtures" / "research" / "sample_seo_keywords.csv"
RUNTIME = ROOT / "reports" / "runtime" / "content_opportunity_lab_latest.json"
MANUAL = ROOT / "reports" / "manual_publish" / "content_opportunity_lab_latest.md"


def make_items(limit: int) -> list[dict]:
    rows = read_csv(KEYWORDS)
    formats = ["blog post", "SEO landing page", "YouTube script", "short-form video", "social carousel", "lead magnet/PDF", "email sequence", "webinar/workshop outline", "affiliate review article"]
    items = []
    for i, row in enumerate(rows[:limit]):
        fmt = formats[i % len(formats)]
        title = f"Content opportunity: {row['keyword']}"
        item = candidate(title, f"content-opportunity://{row['keyword']}", row.get("topic_cluster", "content monetization"), source_type="content_opportunity", proof_source=str(KEYWORDS.relative_to(ROOT)))
        item.update({
            "unique_key": f"content_opportunity:{row['keyword']}",
            "owner_tab": "creative" if fmt in {"YouTube script", "short-form video", "social carousel"} else "seo",
            "summary": f"{fmt} for {row['keyword']} targeting {row.get('search_intent')} intent and {row.get('target_offer')}.",
            "recommendation": "Create a draft-only content card; public use requires approval.",
            "content_opportunity": {
                "target_keyword_topic": row["keyword"],
                "audience": "small business owners",
                "intent": row.get("search_intent"),
                "offer_tie_in": row.get("target_offer"),
                "affiliate_tie_in": "manual affiliate review required",
                "estimated_difficulty": row.get("difficulty_estimate"),
                "expected_revenue_path": "lead, affiliate click, or $97 readiness review",
                "recommended_format": fmt,
                "next_action": "Draft outline and compliance note.",
                "proof_source": row.get("proof_source"),
                "experiment_hypothesis": f"{fmt} on {row['keyword']} can produce qualified leads or affiliate clicks.",
            },
        })
        item["project_enrichment"]["category"] = "content_opportunity"
        items.append(item)
    return items


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", dest="dry_run", action="store_true")
    parser.add_argument("--no-dry-run", dest="dry_run", action="store_false")
    parser.set_defaults(dry_run=True)
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--no-external-ai", action="store_true", default=True)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--report-path", default="")
    args = parser.parse_args()
    if not args.no_external_ai:
        print(json.dumps({"ok": False, "error": "no_external_ai_required"}, indent=2))
        return 2
    items = make_items(max(1, min(args.limit, 10)))
    live = {"created": 0, "duplicates": 0, "failed": 0, "results": []}
    if not args.dry_run:
        live = write_live_tasks(items, "content_opportunity", "content_opportunity_lab", "content_opportunity", args.limit)
    report = {
        "ok": True, "title": "Content Opportunity Lab", "generated_at": now(), "dry_run": args.dry_run,
        "items": items, "counts": {"content_opportunities": len(items), **{k: live.get(k, 0) for k in ("created", "duplicates", "failed")}},
        "summary": "Content opportunities created from safe keyword fixtures. No publishing.",
        "live": live,
    }
    write_report(report, RUNTIME, MANUAL, args.report_path)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
