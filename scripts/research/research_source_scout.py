#!/usr/bin/env python3
"""Manual research source scout v1."""
from __future__ import annotations

import argparse
import json

from common import ROOT, candidate, now, write_live_tasks, write_report

RUNTIME = ROOT / "reports" / "runtime" / "research_source_scout_latest.json"
MANUAL = ROOT / "reports" / "manual_publish" / "research_source_scout_latest.md"


def candidates_for_topic(topic: str, limit: int) -> list[dict]:
    seeds = [
        f"{topic.title()} checklist and buyer intent keywords",
        f"{topic.title()} affiliate program research",
        f"{topic.title()} YouTube channel transcript review",
        f"{topic.title()} content monetization experiment",
        f"{topic.title()} beginner guide opportunity",
    ]
    return [
        {**candidate(title, f"https://example.com/research/{topic.replace(' ', '-')}/{i+1}", topic, proof_source="deterministic_topic_seed"), "unique_key": f"research_scout:{topic}:{i}"}
        for i, title in enumerate(seeds[:limit])
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--topic", required=True)
    parser.add_argument("--dry-run", dest="dry_run", action="store_true")
    parser.add_argument("--no-dry-run", dest="dry_run", action="store_false")
    parser.set_defaults(dry_run=True)
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--no-external-ai", action="store_true", default=True)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--report-path", default="")
    args = parser.parse_args()
    if not args.no_external_ai:
        print(json.dumps({"ok": False, "error": "no_external_ai_required"}, indent=2))
        return 2
    items = candidates_for_topic(args.topic, max(1, min(args.limit, 10)))
    live = {"created": 0, "duplicates": 0, "failed": 0, "results": []}
    if not args.dry_run:
        live = write_live_tasks(items, "research_source_candidate", "research_source_scout", "research_source", args.limit)
    report = {
        "ok": True, "title": "Research Source Scout", "generated_at": now(), "dry_run": args.dry_run,
        "topic": args.topic, "items": items,
        "counts": {"candidates": len(items), **{k: live.get(k, 0) for k in ("created", "duplicates", "failed")}},
        "summary": "Manual scout produced deterministic source candidates. No scraping or external AI.",
        "live": live,
    }
    write_report(report, RUNTIME, MANUAL, args.report_path)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
