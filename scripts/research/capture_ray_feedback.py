#!/usr/bin/env python3
"""Capture Ray feedback as safe Hermes decision memory.

Dry-run by default. Live mode writes only internal summaries to task_requests/nexus_events when
Supabase is configured. It never executes the requested action.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "research"))
sys.path.insert(0, str(ROOT / "scripts" / "social"))
from common import now, write_report  # noqa: E402
import _supabase as sb  # noqa: E402

RUNTIME = ROOT / "reports" / "runtime" / "ray_feedback_capture_latest.json"
MANUAL = ROOT / "reports" / "manual_publish" / "ray_feedback_capture_latest.md"


def classify(feedback: str) -> str:
    low = feedback.lower()
    if re.search(r"reject|do not|stop|avoid", low):
        return "rejected_idea"
    if re.search(r"prioritize|prefer|focus|more .* like", low):
        return "preferred_topic"
    if re.search(r"format|video|article|carousel|landing page|email", low):
        return "preferred_format"
    if re.search(r"compliance|risk|claim|guarantee", low):
        return "compliance_concern"
    if re.search(r"trading|strategy|backtest|paper", low):
        return "trading_strategy_pattern"
    return "ray_feedback"


def build(feedback: str, source_id: str | None, department: str | None) -> dict:
    kind = classify(feedback)
    memory = {
        "kind": kind,
        "title": f"Ray feedback: {kind.replace('_', ' ')}",
        "summary": feedback[:1000],
        "source_type": "ray_feedback",
        "source_id": source_id,
        "department": department,
        "confidence": 0.8,
        "weight": 1,
        "safe_visibility": "internal_summary",
        "created_at": now(),
    }
    return {
        "title": "Ray Feedback Capture",
        "generated_at": now(),
        "ok": True,
        "dry_run": True,
        "summary": "Prepared safe Hermes decision memory from Ray feedback.",
        "counts": {"memories": 1, "created": 0, "duplicates": 0, "failed": 0},
        "memory": memory,
        "approval_required": False,
        "safety": {
            "external_ai_called": False,
            "publish_send_trade_deploy": False,
            "scheduler_started": False,
        },
    }


def write_live(report: dict) -> dict:
    if not sb.configured():
        report["ok"] = False
        report["error"] = "supabase_not_configured"
        report["counts"]["failed"] = 1
        return report
    memory = report["memory"]
    payload = {
        "task_type": "hermes_decision_memory",
        "requested_by": "capture_ray_feedback",
        "sensitivity": "internal_summary",
        "allowed_data_scope": ["internal_summary"],
        "forbidden_data": ["secrets", "cookies", "tokens", "raw_private_customer_data", "broker_credentials"],
        "assigned_worker_type": "hermes_memory_worker",
        "hermes_visibility": "summary",
        "status": "proposed",
        "payload": {
            "department": memory.get("department"),
            "project_type": "hermes_decision_memory",
            "project_enrichment": {
                "enrichment_status": "scored",
                "summary": memory["summary"],
                "score": 80,
                "score_label": "medium",
                "category": memory["kind"],
                "destination": "Hermes Decision Memory",
                "pros": ["Ray preference captured as internal summary."],
                "cons": ["Apply as guidance, not an automatic execution command."],
                "recommendation": "Use this feedback to tune future internal recommendations.",
                "proposed_schedule": "Use in the next weekly Hermes prep brief.",
                "next_action": "Compare future recommendations against this preference.",
                "confidence": memory["confidence"],
                "risk_triggers": [],
                "approval_required": False,
                "hermes_memory_summary": memory["summary"],
                "source_summary": memory["summary"],
                "enrichment_source": "manual",
                "enriched_at": now(),
            },
            "hermes_decision_memory": memory,
            "approval_required": False,
            "source": "capture_ray_feedback",
        },
        "result_summary": memory["summary"][:500],
    }
    _status, rows = sb.insert("task_requests", payload)
    task_id = rows[0]["id"] if isinstance(rows, list) and rows else None
    if not task_id:
        report["counts"]["failed"] = 1
        return report
    _status, events = sb.insert("nexus_events", {
        "lane": "command",
        "source": "capture_ray_feedback",
        "action": "ray_feedback_captured",
        "status": "success",
        "title": memory["title"],
        "summary": memory["summary"][:500],
        "payload": {"task_request_id": task_id, "memory_kind": memory["kind"], "no_external_ai": True},
    })
    report["counts"]["created"] = 1
    report["task_request_id"] = task_id
    report["proof_event_id"] = events[0]["id"] if isinstance(events, list) and events else None
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture Ray feedback into Hermes decision memory.")
    parser.add_argument("--feedback", required=True)
    parser.add_argument("--source-id", default=None)
    parser.add_argument("--department", default=None)
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--no-dry-run", action="store_true")
    parser.add_argument("--no-external-ai", action="store_true", default=True)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--report-path", default="")
    args = parser.parse_args()
    report = build(args.feedback, args.source_id, args.department)
    report["dry_run"] = not args.no_dry_run
    if args.no_dry_run:
        report = write_live(report)
    write_report(report, RUNTIME, MANUAL, args.report_path)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"Ray feedback report written: {RUNTIME.relative_to(ROOT)}")
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
