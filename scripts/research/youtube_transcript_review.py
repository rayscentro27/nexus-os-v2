#!/usr/bin/env python3
"""YouTube transcript review/scoring v1.

Accepts an explicit YouTube URL or local transcript file. No media download, channel scraping,
scheduler, or external AI.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from common import ROOT, enrichment, now, score_research_text, write_live_tasks, write_report

RUNTIME = ROOT / "reports" / "runtime" / "youtube_transcript_review_latest.json"
MANUAL = ROOT / "reports" / "manual_publish" / "youtube_transcript_review_latest.md"


def topic_from_text(blob: str) -> str:
    lowered = blob.lower()
    if "business credit" in lowered or "funding" in lowered or "credit" in lowered:
        return "business credit"
    if "affiliate" in lowered:
        return "affiliate marketing"
    if "trading" in lowered:
        return "trading strategies"
    if "seo" in lowered:
        return "seo"
    if "ai" in lowered:
        return "ai automation"
    return "content monetization"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--youtube-url", default="")
    parser.add_argument("--input-file", default="")
    parser.add_argument("--dry-run", dest="dry_run", action="store_true")
    parser.add_argument("--no-dry-run", dest="dry_run", action="store_false")
    parser.set_defaults(dry_run=True)
    parser.add_argument("--no-external-ai", action="store_true", default=True)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--report-path", default="")
    args = parser.parse_args()
    if not args.no_external_ai:
        print(json.dumps({"ok": False, "error": "no_external_ai_required"}, indent=2))
        return 2
    if args.input_file:
        path = Path(args.input_file)
        if not path.is_absolute():
            path = ROOT / path
        transcript = path.read_text(errors="ignore")
        proof = str(path.relative_to(ROOT))
        title = transcript.splitlines()[0].replace("Title:", "").strip() or "Transcript review"
    else:
        transcript = f"Explicit YouTube URL metadata only: {args.youtube_url}. Transcript capture pending."
        proof = args.youtube_url
        title = args.youtube_url or "YouTube transcript review"
    topic = topic_from_text(transcript)
    e = enrichment(title, transcript[:700], topic, source="deterministic")
    item = {
        "title": f"YouTube transcript review: {title}"[:140],
        "source_url": args.youtube_url or proof,
        "source_type": "youtube_video",
        "owner_tab": "goclear" if e["destination"] == "GoClear/Apex Revenue Hub" else "seo",
        "score": e["score"],
        "summary": e["summary"],
        "recommendation": e["recommendation"],
        "next_action": e["next_action"],
        "proof_source": proof,
        "project_enrichment": e,
        "unique_key": f"youtube_transcript_review:{proof}",
    }
    live = {"created": 0, "duplicates": 0, "failed": 0, "results": []}
    if not args.dry_run:
        live = write_live_tasks([item], "youtube_transcript_review", "youtube_transcript_review", "youtube_transcript_review", 1)
    report = {
        "ok": True, "title": "YouTube Transcript Review", "generated_at": now(), "dry_run": args.dry_run,
        "scores": score_research_text(transcript, topic), "items": [item],
        "counts": {"reviews": 1, **{k: live.get(k, 0) for k in ("created", "duplicates", "failed")}},
        "summary": "Transcript scored deterministically. No media download or external AI.",
        "live": live,
    }
    write_report(report, RUNTIME, MANUAL, args.report_path)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
