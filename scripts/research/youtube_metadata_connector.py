#!/usr/bin/env python3
"""YouTube metadata connector foundation.

Metadata only. No media/audio download, transcript capture, scheduler, broad scraping, or external
AI. If a safe YouTube metadata API is not configured, this reports not_configured and exits cleanly.
"""
from __future__ import annotations

import argparse
import json
import os

from common import ROOT, now, write_report

RUNTIME = ROOT / "reports" / "runtime" / "youtube_metadata_connector_latest.json"
MANUAL = ROOT / "reports" / "manual_publish" / "youtube_metadata_connector_latest.md"


def connector_status() -> dict:
    configured = bool(os.environ.get("YOUTUBE_DATA_API_KEY") or os.environ.get("NEXUS_YOUTUBE_METADATA_CONNECTOR"))
    return {
        "configured": configured,
        "status": "configured_metadata_only" if configured else "not_configured",
        "method": "youtube_data_api_metadata_only" if configured else "none",
        "requires_key": not configured,
        "secrets_printed": False,
        "media_downloaded": False,
        "transcripts_captured": False,
        "scheduler_started": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--mode", default="status", choices=["status", "check-channel", "latest-videos", "validate-handle"])
    parser.add_argument("--channel-url", default="")
    parser.add_argument("--channel-name", default="")
    parser.add_argument("--items-per-channel", type=int, default=3)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--report-path", default="")
    args = parser.parse_args()
    status = connector_status()
    report = {
        "ok": True,
        "title": "YouTube Metadata Connector",
        "generated_at": now(),
        "dry_run": args.dry_run,
        "mode": args.mode,
        "connector_status": status["status"],
        "status": status,
        "candidates": [],
        "counts": {"candidates": 0, "created": 0, "duplicates": 0, "failed": 0},
        "summary": "Metadata connector foundation ready. Live metadata lookup requires a configured safe connector." if not status["configured"] else "Metadata connector configured; live lookup remains bounded and metadata-only.",
        "safety": {
            "media_downloaded": False,
            "audio_downloaded": False,
            "transcripts_captured": False,
            "scheduler_started": False,
            "broad_scraping": False,
            "external_ai_called": False,
        },
    }
    write_report(report, RUNTIME, MANUAL, args.report_path)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
