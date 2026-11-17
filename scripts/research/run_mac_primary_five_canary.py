#!/usr/bin/env python3
"""Run five real no-caption YouTube items sequentially on the Mac ASR path."""
from __future__ import annotations

import json
import os
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path

from scheduled_research_router import process_scheduled_item


SAMPLE = [
    {"queue_sequence": 81, "source_id": "L29CpyBLFd4", "title": "Why Every 6-Figure Funding Business Tracks These KPIs", "channel": "Alec Delpuech"},
    {"queue_sequence": 82, "source_id": "2BLHD1Nlw3U", "title": "How Credit Repair Worked Back in 2016 #shorts", "channel": "Stedman Waiters"},
    {"queue_sequence": 84, "source_id": "gtyjrQxG_kw", "title": "Stop Scrubbing Through Retakes (Let an AI Video Editor Do It)", "channel": "Luuk Alleman"},
    {"queue_sequence": 88, "source_id": "3ns6LAcuRP0", "title": "My Funding Business is Boring, But It Did $312K In The Last 30 Days", "channel": "Stedman Waiters"},
    {"queue_sequence": 257, "source_id": "G7QFT0xL9bw", "title": "How to Use Credit to Buy Cash-Flowing Businesses with $0 down", "channel": "Alec Delpuech"},
]
OUT = Path(__file__).resolve().parents[2] / "reports/runtime/mac_primary_five_canary.json"


def disk_free() -> int:
    return shutil.disk_usage(Path.home()).free


def main() -> int:
    # This certification is explicitly Mac-primary; do not dispatch Oracle.
    os.environ["NEXUS_DISABLE_ORACLE_ASR"] = "1"
    results = []
    for row in SAMPLE:
        item = {
            "source_type": "YOUTUBE_VIDEO", "source_id": row["source_id"],
            "source_url": f"https://www.youtube.com/watch?v={row['source_id']}",
            "title": row["title"], "author": row["channel"], "channel_name": row["channel"],
            "queue_sequence": row["queue_sequence"], "force_asr": True,
            "work_id": f"mac-asr-canary:{row['source_id']}", "question": "captionless_youtube_transcription_canary",
        }
        before = disk_free()
        started = time.monotonic()
        try:
            result = process_scheduled_item(item)
            result["exception"] = None
        except Exception as exc:  # one failure must not stop later items
            result = {"final_status": "FAILED_RETRYABLE", "error": str(exc)[:1000], "exception": type(exc).__name__}
        result.update({"video_id": row["source_id"], "title": row["title"], "channel": row["channel"],
                       "queue_sequence": row["queue_sequence"], "free_disk_before": before,
                       "free_disk_after": disk_free(), "runtime_seconds_wall": round(time.monotonic() - started, 3),
                       "attempted_at": datetime.now(timezone.utc).isoformat()})
        print(json.dumps(result, default=str), flush=True)
        results.append(result)
    payload = {"worker": "mac", "oracle_disabled": True, "max_simultaneous_asr": 1,
               "videos_attempted": len(results), "videos_ingested": sum(x.get("final_status") == "INGESTED" for x in results),
               "results": results}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2, default=str) + "\n")
    print(json.dumps(payload, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
