#!/usr/bin/env python3
"""Check transcript availability path without downloading media."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from common import ROOT, now, read_json, write_report

RUNTIME = ROOT / "reports" / "runtime" / "youtube_transcript_availability_latest.json"
MANUAL = ROOT / "reports" / "manual_publish" / "youtube_transcript_availability_latest.md"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--youtube-url", default="")
    parser.add_argument("--metadata-file", default="")
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--report-path", default="")
    args = parser.parse_args()
    candidates = []
    if args.metadata_file:
        path = Path(args.metadata_file)
        if not path.is_absolute():
            path = ROOT / path
        data = read_json(path)
        candidates = data.get("candidates", []) if isinstance(data, dict) else []
    elif args.youtube_url:
        candidates = [{"video_url": args.youtube_url, "source": "explicit_url"}]
    report = {
        "ok": True,
        "title": "YouTube Transcript Availability",
        "generated_at": now(),
        "dry_run": True,
        "items": [{
            "video_url": item.get("video_url"),
            "availability_status": "not_checked_connector_required",
            "allowed_sources": ["public captions if safely accessible", "local transcript file", "manual transcript paste", "approved transcript import", "existing captured transcript records"],
            "blocked_sources": ["audio/video download", "media ripping", "broad scraping", "private/member-only content", "paywalled transcripts"],
        } for item in candidates],
        "counts": {"checked": len(candidates), "available": 0, "not_configured": len(candidates)},
        "summary": "Transcript availability path is ready; no media download, scraping, or transcript capture occurred.",
        "safety": {"media_downloaded": False, "broad_scraping": False, "external_ai_called": False},
    }
    write_report(report, RUNTIME, MANUAL, args.report_path)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
