#!/usr/bin/env python3
"""Watched resource manual watch check v1.

Dry-run detects synthetic new item candidates from approved fixtures. No scheduler.
"""
from __future__ import annotations

import argparse
import json

from common import ROOT, candidate, now, read_json, write_live_tasks, write_report

FIXTURE = ROOT / "tests" / "fixtures" / "research" / "sample_watched_resources.json"
RUNTIME = ROOT / "reports" / "runtime" / "watched_resource_watch_latest.json"
MANUAL = ROOT / "reports" / "manual_publish" / "watched_resource_watch_latest.md"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--resource-type", default="")
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
    resources = [r for r in read_json(FIXTURE) if not args.resource_type or r["resource_type"] == args.resource_type]
    resources = resources[: max(1, min(args.limit, 10))]
    items = []
    for row in resources:
        item_url = row["resource_url"].rstrip("/") + "/sample-new-item"
        item = candidate(
            f"New watched item: {row['resource_name']}",
            item_url,
            row["category"].replace("_", " "),
            source_type=row["resource_type"],
            proof_source=str(FIXTURE.relative_to(ROOT)),
        )
        item["unique_key"] = f"watched_update:{row['resource_id']}:sample-new-item"
        item["recommendation"] = "If Ray approves this resource, create a research_source for the new item and route by score."
        items.append(item)
    live = {"created": 0, "duplicates": 0, "failed": 0, "results": []}
    if not args.dry_run:
        live = write_live_tasks(items, "watched_resource_update", "watched_resource_watch", "watched_resource_update", args.limit)
    report = {
        "ok": True, "title": "Watched Resource Watch", "generated_at": now(), "dry_run": args.dry_run,
        "items": items, "counts": {"new_items_found": len(items), **{k: live.get(k, 0) for k in ("created", "duplicates", "failed")}},
        "summary": "Watch mode checked safe fixtures only. Scheduler remains disabled.",
        "live": live,
    }
    write_report(report, RUNTIME, MANUAL, args.report_path)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
