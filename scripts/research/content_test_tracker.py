#!/usr/bin/env python3
"""Content test tracker v1 from manual CSV."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from common import ROOT, candidate, num, now, read_csv, write_live_tasks, write_report

RUNTIME = ROOT / "reports" / "runtime" / "content_test_tracker_latest.json"
MANUAL = ROOT / "reports" / "manual_publish" / "content_test_tracker_latest.md"


def make_item(row: dict) -> dict:
    item = candidate(row["content_title"], row.get("published_url") or f"content-test://{row['content_title']}", row.get("target_keyword", "content monetization"), source_type="content_test", proof_source="manual_content_test_csv")
    impressions = num(row.get("impressions"), 0) or 0
    clicks = num(row.get("clicks"), 0) or 0
    leads = num(row.get("leads"), 0) or 0
    conversions = num(row.get("conversions"), 0) or 0
    revenue = num(row.get("revenue"), 0) or 0
    estimated = num(row.get("estimated_value"), 0) or 0
    score = min(100, int((clicks * 2 + leads * 8 + conversions * 20 + revenue + estimated / 5)))
    item.update({
        "unique_key": f"content_test:{row['content_title']}:{row.get('channel')}",
        "title": f"Content test: {row['content_title']}",
        "owner_tab": "seo",
        "score": score,
        "summary": f"{row.get('channel')} test for {row.get('target_keyword')}; status {row.get('status')}; clicks {clicks}; leads {leads}; revenue {revenue}.",
        "recommendation": "Review test performance manually before scaling or publishing more.",
        "content_test": row,
    })
    item["project_enrichment"]["score"] = score
    item["project_enrichment"]["category"] = "content_test_result"
    item["project_enrichment"]["destination"] = "SEO / Marketing"
    return item


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-file", required=True)
    parser.add_argument("--dry-run", dest="dry_run", action="store_true")
    parser.add_argument("--no-dry-run", dest="dry_run", action="store_false")
    parser.set_defaults(dry_run=True)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--report-path", default="")
    args = parser.parse_args()
    path = Path(args.input_file)
    if not path.is_absolute():
        path = ROOT / path
    items = [make_item(row) for row in read_csv(path)]
    live = {"created": 0, "duplicates": 0, "failed": 0, "results": []}
    if not args.dry_run:
        live = write_live_tasks(items, "content_test_result", "content_test_tracker", "content_test_result", len(items))
    report = {
        "ok": True, "title": "Content Test Tracker", "generated_at": now(), "dry_run": args.dry_run,
        "items": items, "counts": {"content_tests": len(items), **{k: live.get(k, 0) for k in ("created", "duplicates", "failed")}},
        "summary": "Content tests loaded from manual CSV. No live analytics API called.",
        "live": live,
    }
    write_report(report, RUNTIME, MANUAL, args.report_path)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
