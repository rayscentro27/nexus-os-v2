#!/usr/bin/env python3
"""Generate deterministic Hermes prep for YouTube research."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from common import ROOT, now, read_json, write_report

RUNTIME = ROOT / "reports" / "runtime" / "hermes_youtube_prep_brief_latest.json"
MANUAL = ROOT / "reports" / "manual_publish" / "hermes_youtube_prep_brief_latest.md"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--no-external-ai", action="store_true", default=True)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--report-path", default="")
    args = parser.parse_args()
    if not args.no_external_ai:
        print(json.dumps({"ok": False, "error": "no_external_ai_required"}, indent=2))
        return 2
    report_path = ROOT / "reports" / "runtime" / "youtube_research_report_latest.json"
    yt = read_json(report_path) if report_path.exists() else {}
    top = yt.get("top_videos_or_candidates", [])[: max(1, min(args.limit, 25))] if isinstance(yt.get("top_videos_or_candidates"), list) else []
    report = {
        "ok": True,
        "title": "Hermes YouTube Prep Brief",
        "generated_at": now(),
        "dry_run": True,
        "top_items": top,
        "questions_prepared": [
            "What are the top 10 YouTube videos scored this week?",
            "Which channel is producing the best ideas?",
            "Which credit/funding content should become GoClear SEO content?",
            "Which AI/automation idea should go to Ops?",
            "Which trading strategy should stay in paper testing?",
            "What can Ray ignore for now?",
        ],
        "memory_hooks": [
            "source_channel_pattern",
            "winning_topic_pattern",
            "rejected_low_value_pattern",
            "ray_feedback_preference",
            "recommended_next_direction",
        ],
        "hermes_recommended_direction": yt.get("hermes_recommended_direction", "Review YouTube research report first; keep execution gated."),
        "counts": {"top_items": len(top), "memory_hooks": 5, "created": 0, "failed": 0},
        "summary": "Prepared deterministic Hermes YouTube context without external AI.",
        "safety": {"external_ai_called": False, "ray_review_queue_flood": False, "publish_send_trade_deploy": False},
    }
    write_report(report, RUNTIME, MANUAL, args.report_path)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
