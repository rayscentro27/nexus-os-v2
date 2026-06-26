#!/usr/bin/env python3
"""Watched resource manual watch check v1.

Dry-run detects synthetic new item candidates from approved fixtures. No scheduler.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from common import ROOT, candidate, now, read_json, write_live_tasks, write_report

FIXTURE = ROOT / "tests" / "fixtures" / "research" / "sample_watched_resources.json"
RAY_YOUTUBE_FIXTURE = ROOT / "tests" / "fixtures" / "research" / "ray_watched_youtube_channels.json"
RUNTIME = ROOT / "reports" / "runtime" / "watched_resource_watch_latest.json"
MANUAL = ROOT / "reports" / "manual_publish" / "watched_resource_watch_latest.md"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--resource-type", default="")
    parser.add_argument("--dry-run", dest="dry_run", action="store_true")
    parser.add_argument("--no-dry-run", dest="dry_run", action="store_false")
    parser.set_defaults(dry_run=True)
    parser.add_argument("--limit", type=int, default=3)
    parser.add_argument("--items-per-resource", type=int, default=3)
    parser.add_argument("--input-file", default=str(FIXTURE))
    parser.add_argument("--metadata-only", action="store_true", default=True)
    parser.add_argument("--no-media-download", action="store_true", default=True)
    parser.add_argument("--no-external-ai", action="store_true", default=True)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--report-path", default="")
    args = parser.parse_args()
    if not args.no_external_ai:
        print(json.dumps({"ok": False, "error": "no_external_ai_required"}, indent=2))
        return 2
    input_path = Path(args.input_file)
    if args.resource_type == "youtube_channel" and args.input_file == str(FIXTURE) and RAY_YOUTUBE_FIXTURE.exists():
        input_path = RAY_YOUTUBE_FIXTURE
    if not input_path.is_absolute():
        input_path = ROOT / input_path
    resources = [r for r in read_json(input_path) if not args.resource_type or r["resource_type"] == args.resource_type]
    resources = resources[: max(1, min(args.limit, 10))]
    items = []
    unsupported = []
    for row in resources:
        if row.get("enabled") is not True or row.get("approved_by_ray") is not True:
            unsupported.append({"resource_name": row["resource_name"], "reason": "not_enabled_or_not_approved"})
            continue
        per_resource = max(1, min(args.items_per_resource, 5))
        for idx in range(1, per_resource + 1):
            item_url = row["resource_url"].rstrip("/") + f"/sample-new-item-{idx}"
            item = candidate(
                f"New watched item {idx}: {row['resource_name']}",
                item_url,
                row["category"].replace("_", " ").replace("|", " "),
                source_type=row["resource_type"],
                proof_source=str(input_path.relative_to(ROOT)),
            )
            item["unique_key"] = f"watched_update:{row['resource_id']}:sample-new-item-{idx}"
            item["recommendation"] = "Watch adapter foundation ready. Live YouTube metadata lookup is not configured in this dry-run; create only metadata candidates when implemented."
            item["watch_adapter_status"] = "foundation_ready_live_check_not_configured"
            item["duplicate_status"] = "not_checked_without_live_connector"
            item["metadata_only"] = True
            item["media_downloaded"] = False
            item["approval_required"] = False
            items.append(item)
    live = {"created": 0, "duplicates": 0, "failed": 0, "results": []}
    if not args.dry_run:
        live = write_live_tasks(items, "watched_resource_update", "watched_resource_watch", "watched_resource_update", args.limit)
    report = {
        "ok": True, "title": "Watched Resource Watch", "generated_at": now(), "dry_run": args.dry_run,
        "resources_checked": len(resources),
        "resources_enabled": sum(1 for r in resources if r.get("enabled") is True),
        "items": items,
        "new_since_last_check_logic": {
            "compares": ["last_seen_item_url", "last_seen_item_published_at", "existing research_sources.source_url"],
            "dry_run_updates_last_seen": False,
            "live_update_supported": "future_metadata_connector_required",
        },
        "unsupported_checks": unsupported,
        "counts": {"resources_checked": len(resources), "resources_enabled": sum(1 for r in resources if r.get("enabled") is True), "new_items_found": len(items), **{k: live.get(k, 0) for k in ("created", "duplicates", "failed")}},
        "summary": "Watch mode checked explicit fixture/manual input only. YouTube live metadata lookup is not configured; scheduler remains disabled.",
        "safety": {"scheduler_started": False, "media_downloaded": False, "broad_scraping": False, "external_ai_called": False},
        "live": live,
    }
    write_report(report, RUNTIME, MANUAL, args.report_path)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
