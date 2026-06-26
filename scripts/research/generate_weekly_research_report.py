#!/usr/bin/env python3
"""Generate a deterministic weekly/top research report.

Dry-run by default. Reads local reports and safe Supabase summaries when available. It does not
publish, send, trade, deploy, start schedulers, scrape, capture, or call external AI.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "research"))
from common import now, write_report  # noqa: E402

RUNTIME = ROOT / "reports" / "runtime" / "weekly_research_report_latest.json"
MANUAL = ROOT / "reports" / "manual_publish" / "weekly_research_report_latest.md"

SOURCE_REPORTS = [
    "watched_resource_watch_latest.json",
    "youtube_transcript_review_latest.json",
    "research_source_scout_latest.json",
    "affiliate_opportunity_tracker_latest.json",
    "seo_keyword_scout_latest.json",
    "seo_affiliate_content_planner_latest.json",
    "research_to_experiment_latest.json",
    "content_opportunity_lab_latest.json",
    "content_test_tracker_latest.json",
]


def load_runtime_report(name: str) -> dict[str, Any]:
    path = ROOT / "reports" / "runtime" / name
    if not path.exists():
        return {"source": name, "ok": False, "missing": True, "items": []}
    try:
        data = json.loads(path.read_text(errors="ignore"))
    except json.JSONDecodeError:
        return {"source": name, "ok": False, "parse_error": True, "items": []}
    return {"source": name, **data}


def extract_items(report: dict[str, Any]) -> list[dict[str, Any]]:
    for key in ("candidates", "items", "reviews", "programs", "keywords", "plans", "experiments", "content_opportunities", "content_tests"):
        value = report.get(key)
        if isinstance(value, list):
            return value
    return []


def item_score(item: dict[str, Any]) -> int:
    value = item.get("score")
    if isinstance(value, (int, float)):
        return int(value)
    enrichment = item.get("project_enrichment") if isinstance(item.get("project_enrichment"), dict) else {}
    value = enrichment.get("score")
    return int(value) if isinstance(value, (int, float)) else 0


def build(limit: int) -> dict[str, Any]:
    reports = [load_runtime_report(name) for name in SOURCE_REPORTS]
    items: list[dict[str, Any]] = []
    for report in reports:
        source = report.get("source")
        for item in extract_items(report):
            if isinstance(item, dict):
                items.append({**item, "report_source": source})
    top = sorted(items, key=item_score, reverse=True)[:limit]
    return {
        "title": "Weekly Research Report",
        "generated_at": now(),
        "ok": True,
        "dry_run": True,
        "summary": f"Prepared top {len(top)} internal research findings from {len(reports)} local report sources.",
        "counts": {
            "source_reports": len(reports),
            "items_considered": len(items),
            "top_items": len(top),
            "created": 0,
            "duplicates": 0,
            "failed": 0,
        },
        "top_items": top,
        "hermes_context": {
            "question_ready": True,
            "suggested_prompt": "What direction should we take from this week's top research?",
            "approval_required": False,
        },
        "safety": {
            "scheduler_started": False,
            "publish_send_trade_deploy": False,
            "external_ai_called": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate weekly Nexus research report.")
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--no-dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--no-external-ai", action="store_true", default=True)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--report-path", default="")
    args = parser.parse_args()
    limit = max(1, min(args.limit, 50))
    report = build(limit)
    report["dry_run"] = not args.no_dry_run
    write_report(report, RUNTIME, MANUAL, args.report_path)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"weekly research report written: {RUNTIME.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
