#!/usr/bin/env python3
"""YouTube channel watchlist v1.

List/validate safe watchlist entries. Does not capture, download media, or start scheduling.
"""
from __future__ import annotations

import argparse
import json

from pathlib import Path

from common import ROOT, now, read_json, write_report

FIXTURE = ROOT / "tests" / "fixtures" / "research" / "sample_watched_resources.json"
RUNTIME = ROOT / "reports" / "runtime" / "youtube_channel_watchlist_latest.json"
MANUAL = ROOT / "reports" / "manual_publish" / "youtube_channel_watchlist_latest.md"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--list", action="store_true", dest="list_items")
    parser.add_argument("--input-file", default=str(FIXTURE))
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--report-path", default="")
    args = parser.parse_args()
    input_path = Path(args.input_file)
    if not input_path.is_absolute():
        input_path = ROOT / input_path
    rows = [r for r in read_json(input_path) if r["resource_type"] == "youtube_channel"]
    items = [{
        "channel_name": r["resource_name"],
        "channel_url": r["resource_url"],
        "channel_id": None,
        "topic_category": r["category"],
        "monetization_relevance": 90 if "credit" in r["category"] or "funding" in r["category"] else 60 if "trading" in r["category"] else 75,
        "approved_by_ray": r["approved_by_ray"],
        "enabled": r["enabled"],
        "risk_level": r["risk_level"],
        "last_checked_at": r["last_checked_at"],
        "last_seen_video_url": r["last_seen_item_url"],
        "last_seen_video_published_at": r["last_seen_item_published_at"],
        "notes": r["notes"],
    } for r in rows]
    report = {
        "ok": True, "title": "YouTube Channel Watchlist", "generated_at": now(), "dry_run": True,
        "items": items, "counts": {"channels": len(items), "enabled": sum(1 for i in items if i["enabled"])},
        "summary": "Watchlist entries loaded from explicit fixture/manual input. No capture, scraping, media download, or scheduling ran.",
        "safety": {
            "scheduler_started": False,
            "media_downloaded": False,
            "broad_scraping": False,
            "external_ai_called": False,
        },
    }
    write_report(report, RUNTIME, MANUAL, args.report_path)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
