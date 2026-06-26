#!/usr/bin/env python3
"""Bounded watched resource backfill v1.

No broad scraping. Uses approved/manual fixture data to create candidate research cards.
"""
from __future__ import annotations

import argparse
import json

from common import ROOT, candidate, now, read_json, write_live_tasks, write_report

FIXTURE = ROOT / "tests" / "fixtures" / "research" / "sample_watched_resources.json"
RUNTIME = ROOT / "reports" / "runtime" / "watched_resource_backfill_latest.json"
MANUAL = ROOT / "reports" / "manual_publish" / "watched_resource_backfill_latest.md"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", dest="dry_run", action="store_true")
    parser.add_argument("--no-dry-run", dest="dry_run", action="store_false")
    parser.set_defaults(dry_run=True)
    parser.add_argument("--limit", type=int, default=3)
    parser.add_argument("--no-external-ai", action="store_true", default=True)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--report-path", default="")
    args = parser.parse_args()
    if not args.no_external_ai:
        print(json.dumps({"ok": False, "error": "no_external_ai_required"}, indent=2))
        return 2
    resources = read_json(FIXTURE)[: max(1, min(args.limit, 10))]
    items = []
    for row in resources:
        item = candidate(
            f"Backfill review: {row['resource_name']}",
            row["resource_url"],
            row["category"].replace("_", " "),
            source_type=row["resource_type"],
            proof_source=str(FIXTURE.relative_to(ROOT)),
        )
        item["unique_key"] = f"watched_backfill:{row['resource_id']}"
        item["recommendation"] = "Backfill only selected/high-value historical items after Ray approval; do not scrape broadly."
        items.append(item)
    live = {"created": 0, "duplicates": 0, "failed": 0, "results": []}
    if not args.dry_run:
        live = write_live_tasks(items, "watched_resource_update", "watched_resource_backfill", "watched_resource_update", args.limit)
    report = {
        "ok": True, "title": "Watched Resource Backfill", "generated_at": now(), "dry_run": args.dry_run,
        "items": items, "counts": {"scanned": len(resources), **{k: live.get(k, 0) for k in ("created", "duplicates", "failed")}},
        "summary": "Backfill mode simulated bounded historical review from safe fixtures; no scraping/capture.",
        "live": live,
    }
    write_report(report, RUNTIME, MANUAL, args.report_path)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
