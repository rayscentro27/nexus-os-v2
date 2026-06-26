#!/usr/bin/env python3
"""Watched resource registry v1.

Dry-run default. Saves approved resources as internal project cards only when explicitly live.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from common import RESOURCE_TYPES, ROOT, candidate, now, read_json, write_live_tasks, write_report

FIXTURE = ROOT / "tests" / "fixtures" / "research" / "sample_watched_resources.json"
RUNTIME = ROOT / "reports" / "runtime" / "watched_resource_registry_latest.json"
MANUAL = ROOT / "reports" / "manual_publish" / "watched_resource_registry_latest.md"


def resource_to_candidate(row: dict) -> dict:
    category = str(row["category"]).replace("_", " ").replace("|", " ")
    item = candidate(
        row["resource_name"],
        row["resource_url"],
        category,
        source_type=row["resource_type"],
        proof_source="manual_fixture",
    )
    item.update({
        "unique_key": f"watched_resource:{row['resource_type']}:{row['resource_url'].rstrip('/').lower()}",
        "resource": row,
        "summary": f"Watched resource candidate: {row['resource_name']} ({row['resource_type']}).",
        "recommendation": "Approved for autonomous internal research only. Scheduler remains disabled until Ray approves activation.",
        "next_action": "Use manual dry-run watch/backfill; do not scrape broadly or download media.",
        "duplicate_keys": [
            row["resource_url"].rstrip("/").lower(),
            row["resource_url"].rstrip("/").lower().split("/")[-1],
            row["resource_type"],
        ],
    })
    return item


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", dest="dry_run", action="store_true")
    parser.add_argument("--no-dry-run", dest="dry_run", action="store_false")
    parser.set_defaults(dry_run=True)
    parser.add_argument("--input-file", default=str(FIXTURE))
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--report-path", default="")
    args = parser.parse_args()

    rows = read_json(Path(args.input_file))[: max(1, min(args.limit, 50))]
    items = [resource_to_candidate(row) for row in rows]
    live = {"created": 0, "duplicates": 0, "failed": 0, "results": []}
    if not args.dry_run:
        live = write_live_tasks(items, "watched_resource", "watched_resource_registry", "watched_resource", args.limit)
    report = {
        "ok": True,
        "title": "Watched Resource Registry",
        "generated_at": now(),
        "dry_run": args.dry_run,
        "resource_types_supported": RESOURCE_TYPES,
        "items": items,
        "counts": {"resources": len(items), **{k: live.get(k, 0) for k in ("created", "duplicates", "failed")}},
        "summary": "Watched resources loaded from safe fixture/manual input. Scheduler remains disabled.",
        "live": live,
    }
    write_report(report, RUNTIME, MANUAL, args.report_path)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
