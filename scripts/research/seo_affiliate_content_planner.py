#!/usr/bin/env python3
"""SEO-to-affiliate content planner v1."""
from __future__ import annotations

import argparse
import json

from common import ROOT, candidate, now, read_csv, write_live_tasks, write_report

KEYWORDS = ROOT / "tests" / "fixtures" / "research" / "sample_seo_keywords.csv"
AFFILIATES = ROOT / "tests" / "fixtures" / "research" / "sample_affiliate_programs.csv"
RUNTIME = ROOT / "reports" / "runtime" / "seo_affiliate_content_planner_latest.json"
MANUAL = ROOT / "reports" / "manual_publish" / "seo_affiliate_content_planner_latest.md"


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
    keywords = read_csv(KEYWORDS)
    affiliates = read_csv(AFFILIATES)
    items = []
    for i, row in enumerate(keywords[: max(1, min(args.limit, 10))]):
        affiliate = affiliates[i % len(affiliates)]
        title = f"Content plan: {row['keyword']}"
        item = candidate(title, f"content-plan://{row['keyword']}", row.get("topic_cluster", "seo"), source_type="content_plan", proof_source=str(KEYWORDS.relative_to(ROOT)))
        item.update({
            "unique_key": f"seo_affiliate_plan:{row['keyword']}",
            "owner_tab": "seo",
            "summary": f"Article angle: {row.get('content_type_recommendation')} for {row['keyword']}; affiliate offer: {affiliate['program_name']}; GoClear offer: {row.get('target_offer')}.",
            "recommendation": "Create SEO/Marketing card and route draft-only creative needs to Creative Studio.",
            "content_plan": {
                "target_keyword": row["keyword"],
                "article_angle": row.get("content_type_recommendation"),
                "affiliate_offer": affiliate["program_name"],
                "GoClear_offer": row.get("target_offer"),
                "internal_links": ["GoClear readiness page", "Opportunity Lab"],
                "CTA": row.get("target_offer"),
                "compliance_note": "No guarantees; include affiliate disclosure when applicable.",
                "test_plan": "Draft outline, validate compliance, then publish only after approval.",
                "estimated_value": 150,
                "priority_score": item["score"],
                "department_destination": "SEO / Marketing",
            },
        })
        item["project_enrichment"]["category"] = "seo_affiliate_content_plan"
        item["project_enrichment"]["destination"] = "SEO / Marketing"
        items.append(item)
    live = {"created": 0, "duplicates": 0, "failed": 0, "results": []}
    if not args.dry_run:
        live = write_live_tasks(items, "seo_affiliate_content_plan", "seo_affiliate_content_planner", "content_plan", args.limit)
    report = {
        "ok": True, "title": "SEO Affiliate Content Planner", "generated_at": now(), "dry_run": args.dry_run,
        "items": items, "counts": {"plans": len(items), **{k: live.get(k, 0) for k in ("created", "duplicates", "failed")}},
        "summary": "Planner connected manual keywords to manual affiliate samples and GoClear offers.",
        "live": live,
    }
    write_report(report, RUNTIME, MANUAL, args.report_path)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
