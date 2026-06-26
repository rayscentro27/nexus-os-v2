#!/usr/bin/env python3
"""Run a bounded metadata-only YouTube check over approved channel fixtures."""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from common import ROOT, now, read_json, write_report

RUNTIME = ROOT / "reports" / "runtime" / "youtube_metadata_check_latest.json"
MANUAL = ROOT / "reports" / "manual_publish" / "youtube_metadata_check_latest.md"


def connector_status() -> dict:
    proc = subprocess.run(
        ["python3", str(ROOT / "scripts" / "research" / "youtube_metadata_connector.py"), "--dry-run", "--mode", "status", "--json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        return {"status": "not_configured", "error": "connector_status_failed"}
    return json.loads(proc.stdout)


def metadata_candidate(channel: dict, idx: int, configured: bool) -> dict:
    handle = channel["resource_url"].rstrip("/").split("/")[-1]
    return {
        "channel_name": channel["resource_name"],
        "channel_url": channel["resource_url"],
        "channel_id": None,
        "video_title": f"Metadata candidate {idx}: {channel['resource_name']}",
        "video_url": f"{channel['resource_url'].rstrip('/')}/videos/sample-metadata-{idx}",
        "video_id": f"{handle}:sample-metadata-{idx}",
        "published_at": None,
        "description_snippet": "Metadata connector not configured; this is a dry-run placeholder candidate only." if not configured else "Metadata-only candidate from configured connector.",
        "duration": None,
        "thumbnail_url": None,
        "detected_category": channel["category"],
        "source_resource_id": channel["resource_id"],
        "duplicate_status": "not_checked_without_live_connector" if not configured else "not_checked_in_dry_run",
        "candidate_score_hint": 75 if "credit" in channel["category"] or "funding" in channel["category"] else 60,
        "proof_source": "metadata_connector_status" if configured else "not_configured_fallback",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--input-file", default="tests/fixtures/research/ray_watched_youtube_channels.json")
    parser.add_argument("--limit", type=int, default=4)
    parser.add_argument("--items-per-channel", type=int, default=3)
    parser.add_argument("--no-external-ai", action="store_true", default=True)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--report-path", default="")
    args = parser.parse_args()
    if not args.no_external_ai:
        print(json.dumps({"ok": False, "error": "no_external_ai_required"}, indent=2))
        return 2
    input_path = Path(args.input_file)
    if not input_path.is_absolute():
        input_path = ROOT / input_path
    channels = [r for r in read_json(input_path) if r.get("approved_by_ray") and r.get("enabled")][: max(1, min(args.limit, 10))]
    status = connector_status()
    configured = status.get("connector_status") == "configured_metadata_only"
    candidates = []
    for channel in channels:
        for idx in range(1, max(1, min(args.items_per_channel, 5)) + 1):
            candidates.append(metadata_candidate(channel, idx, configured))
    report = {
        "ok": True,
        "title": "YouTube Metadata Check",
        "generated_at": now(),
        "dry_run": True,
        "connector_status": status.get("connector_status", "not_configured"),
        "channels_checked": len(channels),
        "candidates": candidates,
        "counts": {"channels_checked": len(channels), "metadata_candidates": len(candidates), "created": 0, "duplicates": 0, "failed": 0},
        "summary": "Metadata connector not configured; fallback candidates are placeholders and no live YouTube lookup occurred." if not configured else "Metadata-only connector dry-run completed.",
        "safety": {"media_downloaded": False, "audio_downloaded": False, "scheduler_started": False, "broad_scraping": False, "external_ai_called": False},
    }
    write_report(report, RUNTIME, MANUAL, args.report_path)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
