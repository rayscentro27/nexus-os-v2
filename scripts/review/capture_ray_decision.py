#!/usr/bin/env python3
"""Capture Ray's review decision without executing the underlying action."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "social"))
sys.path.insert(0, str(ROOT / "scripts" / "review"))
import _supabase as sb  # noqa: E402
from build_ray_review_queue import now  # noqa: E402

RUNTIME = ROOT / "reports" / "runtime" / "ray_decision_capture_latest.json"
MANUAL = ROOT / "reports" / "manual_publish" / "ray_decision_capture_latest.md"
ALLOWED = {"reviewed", "approved", "rejected", "changes_requested", "parked", "escalated"}


def build(review_id: str, decision: str, feedback: str) -> dict:
    return {
        "title": "Ray Decision Capture",
        "generated_at": now(),
        "ok": decision in ALLOWED,
        "dry_run": True,
        "review_id": review_id,
        "decision": decision,
        "feedback": feedback[:1000],
        "counts": {"updated": 0, "created": 0, "failed": 0},
        "hermes_memory": {
            "kind": "ray_feedback",
            "summary": feedback[:1000],
            "source_type": "ray_review_queue",
            "source_id": review_id,
            "safe_visibility": "internal_summary",
        },
        "safety": {"publish_send_trade_deploy": False, "scheduler_started": False, "external_ai_called": False},
    }


def write_live(report: dict) -> dict:
    if not sb.configured():
        report["ok"] = False
        report["error"] = "supabase_not_configured"
        report["counts"]["failed"] = 1
        return report
    _status, rows = sb.get("task_requests", f"select=id,payload&task_type=eq.ray_review_item&payload->>review_id=eq.{sb.q(report['review_id'])}&limit=1")
    row = rows[0] if isinstance(rows, list) and rows else None
    if not row:
        report["ok"] = False
        report["error"] = "review_item_not_found"
        report["counts"]["failed"] = 1
        return report
    p = row.get("payload") if isinstance(row.get("payload"), dict) else {}
    p["status"] = report["decision"]
    p["ray_feedback"] = report["feedback"]
    p["decision_captured_at"] = now()
    sb.update("task_requests", f"id=eq.{sb.q(row['id'])}", {"status": report["decision"], "payload": p, "result_summary": report["feedback"][:500]})
    _status, events = sb.insert("nexus_events", {
        "lane": "command",
        "source": "capture_ray_decision",
        "action": "ray_review_decision_captured",
        "status": report["decision"],
        "title": f"Ray decision: {report['decision']}",
        "summary": report["feedback"][:500],
        "payload": {"review_id": report["review_id"], "task_request_id": row["id"], "no_execution": True, "no_external_ai": True},
    })
    report["counts"]["updated"] = 1
    report["proof_event_id"] = events[0]["id"] if isinstance(events, list) and events else None
    return report


def write_report(report: dict) -> None:
    RUNTIME.parent.mkdir(parents=True, exist_ok=True)
    RUNTIME.write_text(json.dumps(report, indent=2))
    MANUAL.parent.mkdir(parents=True, exist_ok=True)
    MANUAL.write_text("\n".join([
        "# Ray Decision Capture",
        "",
        f"- generated_at: {report['generated_at']}",
        f"- dry_run: {report['dry_run']}",
        f"- ok: {report['ok']}",
        f"- review_id: {report['review_id']}",
        f"- decision: {report['decision']}",
        f"- feedback: {report['feedback']}",
        "- no execution performed",
        "- no publish/send/trade/deploy/scheduler",
    ]) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture Ray decision/feedback.")
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--no-dry-run", action="store_true")
    parser.add_argument("--review-id", required=True)
    parser.add_argument("--decision", required=True, choices=sorted(ALLOWED))
    parser.add_argument("--feedback", required=True)
    parser.add_argument("--no-external-ai", action="store_true", default=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = build(args.review_id, args.decision, args.feedback)
    report["dry_run"] = not args.no_dry_run
    if args.no_dry_run:
        report = write_live(report)
    write_report(report)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"Ray decision capture written: {RUNTIME.relative_to(ROOT)}")
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
