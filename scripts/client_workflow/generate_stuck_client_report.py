#!/usr/bin/env python3
"""Stuck-client / reminder report (dry-run).

Detects stuck clients, days stuck, escalation, and revenue risk. Generates reminder DRAFTS only —
no external email/SMS/DM is sent (Level 2, requires client opt-in + approval).

    python3 scripts/client_workflow/generate_stuck_client_report.py --dry-run --json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "research"))
sys.path.insert(0, str(ROOT / "scripts" / "client_workflow"))
from common import write_report  # noqa: E402
import client_workflow_model as m  # noqa: E402

RUNTIME = ROOT / "reports" / "runtime" / "client_reminder_engine_latest.json"
MANUAL = ROOT / "reports" / "manual_publish" / "client_reminder_engine_latest.md"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--report-path", default="")
    args = parser.parse_args()

    clients, source = m.load_clients()
    stuck = []
    for cl in clients:
        ds = cl["days_stuck"]
        if ds >= m.REMINDER_TIMINGS["incomplete_setup_days"]:
            stuck.append({
                "client_id": cl["client_id"],
                "client_label": cl["client_label"],
                "current_stage": cl["current_stage"],
                "days_stuck": ds,
                "revenue_risk_level": m.revenue_risk(ds),
                "escalation_status": m.escalation(ds),
                "reminder_draft": f'Reminder (draft, internal): {cl["client_label"]} — please complete the next step at "{cl["current_stage"]}".',
                "reminder_status": "pending",
                "external_send": False,
            })
    stuck.sort(key=lambda x: x["days_stuck"], reverse=True)

    report = {
        "ok": True,
        "title": "Client Reminder Engine",
        "generated_at": m.now(),
        "dry_run": True,
        "data_source": source,
        "timings_days": m.REMINDER_TIMINGS,
        "stuck_clients": stuck,
        "counts": {
            "total_clients": len(clients),
            "stuck_clients": len(stuck),
            "escalate_hermes": sum(1 for s in stuck if s["escalation_status"] == "hermes"),
            "escalate_ray": sum(1 for s in stuck if s["escalation_status"] == "ray"),
            "reminder_drafts": len(stuck),
            "external_messages_sent": 0,
        },
        "summary": f"{len(stuck)} stuck client(s) detected; {len(stuck)} reminder draft(s) generated. No external reminder sent (requires client opt-in + approval).",
        "safety": {"external_message_sent": False, "client_contacted": False, "money_spent": False},
    }
    write_report(report, RUNTIME, MANUAL, args.report_path)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(report["summary"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
