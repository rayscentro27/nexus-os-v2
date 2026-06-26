#!/usr/bin/env python3
"""Generate a concise Ray Review Queue report."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "review"))
from build_ray_review_queue import build_candidates, now  # noqa: E402

RUNTIME = ROOT / "reports" / "runtime" / "ray_review_queue_latest.json"
MANUAL = ROOT / "reports" / "manual_publish" / "ray_review_queue_latest.md"


def summarize(items: list[dict]) -> dict:
    return {
        "total_pending_decisions": len(items),
        "urgent_decisions": sum(1 for x in items if x.get("priority") == "urgent"),
        "campaign_approvals": sum(1 for x in items if x.get("decision_type") in {"campaign_publish", "social_post", "email_send"}),
        "revenue_decisions": sum(1 for x in items if x.get("decision_type") == "revenue_decision"),
        "scheduler_decisions": sum(1 for x in items if x.get("decision_type") == "scheduler_activation"),
        "connector_setup_decisions": sum(1 for x in items if x.get("decision_type") == "connector_setup"),
        "trading_blocked_decisions": sum(1 for x in items if x.get("decision_type") == "trading_live_execution_blocked"),
    }


def write(report: dict, report_path: str = "") -> None:
    RUNTIME.parent.mkdir(parents=True, exist_ok=True)
    RUNTIME.write_text(json.dumps(report, indent=2))
    lines = [
        "# Ray Review Queue Report",
        "",
        f"- generated_at: {report['generated_at']}",
        f"- dry_run: {report['dry_run']}",
        f"- ok: {report['ok']}",
        "",
        "## Counts",
    ]
    for key, value in report["counts"].items():
        lines.append(f"- {key}: {value}")
    lines += ["", "## Hermes Recommended First Reviews"]
    for item in report["top_decisions"]:
        lines.append(f"- {item['priority']} / {item['decision_type']}: {item['title']}")
    lines += [
        "",
        "## Autonomous Work That Does Not Need Review",
        "Transcript review, video scoring, SEO keyword scoring, affiliate scoring, watched resource updates, internal experiment cards, internal reports, and paper-only trading research stay out of this queue.",
        "",
        "## Safety",
        "- no publish/send/trade/deploy",
        "- no scheduler activation",
        "- no external AI",
    ]
    MANUAL.parent.mkdir(parents=True, exist_ok=True)
    MANUAL.write_text("\n".join(lines) + "\n")
    if report_path:
        p = Path(report_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(report, indent=2) if p.suffix == ".json" else "\n".join(lines) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Ray Review Queue report.")
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--no-external-ai", action="store_true", default=True)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--report-path", default="")
    args = parser.parse_args()
    built = build_candidates(max(1, min(args.limit, 50)), None, None)
    items = built["candidates"][: max(1, min(args.limit, 50))]
    counts = summarize(items)
    report = {
        "title": "Ray Review Queue Report",
        "generated_at": now(),
        "ok": True,
        "dry_run": True,
        "counts": counts,
        "top_decisions": items[:10],
        "what_nexus_completed_autonomously": [
            "research scoring",
            "transcript review",
            "SEO/affiliate/content report generation",
            "paper-only trading research",
        ],
        "what_can_wait": [x for x in items if x.get("priority") in {"low", "medium"}],
        "hermes_recommended_direction": "Review urgent execution/scheduler/connector decisions first; let autonomous research continue in departments.",
        "safety": {"publish_send_trade_deploy": False, "scheduler_started": False, "external_ai_called": False},
    }
    write(report, args.report_path)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"Ray Review report written: {RUNTIME.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
