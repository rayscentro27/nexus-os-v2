#!/usr/bin/env python3
"""Generate scheduler approval candidates without activating any scheduler."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "research"))
from common import now, write_report  # noqa: E402

RUNTIME = ROOT / "reports" / "runtime" / "scheduler_approval_candidates_latest.json"
MANUAL = ROOT / "reports" / "manual_publish" / "scheduler_approval_candidates_latest.md"

SCHEDULES = [
    ("Weekly YouTube watched resource check", "weekly", ["research_sources metadata", "nexus_events proof"], "no publish/send/trade/deploy/media download"),
    ("Weekly YouTube top report", "weekly", ["local reports"], "no external AI or outbound action"),
    ("Daily Department Digest", "daily", ["safe task cards", "nexus_events proof"], "no capture/live connector unless separately approved"),
    ("Weekly Hermes prep brief", "weekly", ["local reports", "Hermes memory summaries"], "no external AI on sensitive data"),
    ("Weekly GoClear Revenue Hub report", "weekly", ["safe revenue metric cards/reports"], "no payment or email action"),
    ("Weekly Trading Lab paper performance report", "weekly", ["paper-only summaries"], "no broker API or live trading"),
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--report-path", default="")
    args = parser.parse_args()
    candidates = []
    for name, frequency, writes, forbidden in SCHEDULES[: max(1, min(args.limit, 10))]:
        candidates.append({
            "schedule_name": name,
            "frequency": frequency,
            "allowed_writes": writes,
            "forbidden_actions": forbidden,
            "risk_level": "medium",
            "disable_rollback_plan": "Do not install scheduler until Ray approves; rollback is deleting the proposed item.",
            "ray_approval_required": True,
            "proof_report_path": "reports/manual_publish/scheduler_approval_candidates_latest.md",
        })
    report = {
        "ok": True,
        "title": "Scheduler Approval Candidates",
        "generated_at": now(),
        "dry_run": True,
        "candidates": candidates,
        "counts": {"candidates": len(candidates), "created": 0, "failed": 0},
        "summary": "Generated schedule-ready proposals only. No scheduler activated.",
        "safety": {"scheduler_started": False, "cron_launchd_systemd_created": False, "publish_send_trade_deploy": False},
    }
    write_report(report, RUNTIME, MANUAL, args.report_path)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
