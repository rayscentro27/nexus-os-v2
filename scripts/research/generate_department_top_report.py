#!/usr/bin/env python3
"""Generate a deterministic top-N report for one research department/source class."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "research"))
from common import now, write_report  # noqa: E402

RUNTIME = ROOT / "reports" / "runtime" / "department_top_report_latest.json"
MANUAL = ROOT / "reports" / "manual_publish" / "department_top_report_latest.md"

DEPARTMENT_SOURCES = {
    "youtube_transcripts": ["youtube_transcript_review_latest.json", "watched_resource_watch_latest.json"],
    "seo_marketing": ["seo_keyword_scout_latest.json", "seo_affiliate_content_planner_latest.json", "content_opportunity_lab_latest.json"],
    "affiliate": ["affiliate_opportunity_tracker_latest.json", "seo_affiliate_content_planner_latest.json"],
    "experiments": ["research_to_experiment_latest.json", "content_test_tracker_latest.json"],
    "goclear": ["research_source_scout_latest.json", "seo_keyword_scout_latest.json", "content_opportunity_lab_latest.json"],
    "trading": ["trading_backtest_import_latest.json"],
}


def load(name: str) -> dict[str, Any]:
    path = ROOT / "reports" / "runtime" / name
    if not path.exists():
        return {"source": name, "items": []}
    try:
        return {"source": name, **json.loads(path.read_text(errors="ignore"))}
    except json.JSONDecodeError:
        return {"source": name, "items": []}


def extract(report: dict[str, Any]) -> list[dict[str, Any]]:
    for key in ("reviews", "items", "candidates", "programs", "keywords", "plans", "experiments", "content_opportunities", "content_tests"):
        value = report.get(key)
        if isinstance(value, list):
            return [x for x in value if isinstance(x, dict)]
    return []


def score(item: dict[str, Any]) -> int:
    value = item.get("score")
    if isinstance(value, (int, float)):
        return int(value)
    enrichment = item.get("project_enrichment") if isinstance(item.get("project_enrichment"), dict) else {}
    value = enrichment.get("score")
    if isinstance(value, (int, float)):
        return int(value)
    metrics = item.get("metrics") if isinstance(item.get("metrics"), dict) else {}
    value = metrics.get("priority_score")
    return int(value) if isinstance(value, (int, float)) else 0


def build(department: str, limit: int) -> dict[str, Any]:
    sources = DEPARTMENT_SOURCES.get(department, [f"{department}_latest.json"])
    reports = [load(name) for name in sources]
    items = []
    for report in reports:
        for item in extract(report):
            items.append({**item, "report_source": report["source"]})
    top = sorted(items, key=score, reverse=True)[:limit]
    return {
        "title": f"Department Top Report: {department}",
        "generated_at": now(),
        "ok": True,
        "dry_run": True,
        "summary": f"Prepared top {len(top)} {department} items from {len(sources)} local report sources.",
        "department": department,
        "counts": {
            "source_reports": len(sources),
            "items_considered": len(items),
            "top_items": len(top),
            "created": 0,
            "duplicates": 0,
            "failed": 0,
        },
        "top_items": top,
        "approval_required": False,
        "hermes_context": {
            "suggested_prompt": f"Why did these {department} items score highest, and what should we test next?",
            "approval_required": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate department top-N research report.")
    parser.add_argument("--department", required=True)
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--no-dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--no-external-ai", action="store_true", default=True)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--report-path", default="")
    args = parser.parse_args()
    report = build(args.department, max(1, min(args.limit, 50)))
    report["dry_run"] = not args.no_dry_run
    write_report(report, RUNTIME, MANUAL, args.report_path)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"department top report written: {RUNTIME.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
