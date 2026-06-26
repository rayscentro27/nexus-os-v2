#!/usr/bin/env python3
"""Generate scheduler approval candidates without activating any scheduler.

Every candidate is proposal-only: status defaults to "proposed". No cron/launchd/systemd is created.
Deterministic, local-first. Backward-compatible CLI (--dry-run, --limit, --json, --report-path).
"""
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

# (name, category, automation_level, frequency, allowed_writes, forbidden_actions,
#  owner, risk_level, connector_required, external_api_required, high_risk_guard)
SCHEDULES = [
    ("Daily Department Digest", "scheduler_automation", "approval_gated", "daily",
     ["safe task cards", "nexus_events proof"], "no capture/live connector/publish/send",
     "ops_improvements", "medium", False, False, False),
    ("Weekly YouTube Watched Resource Check", "youtube_research", "approval_gated", "weekly",
     ["research_sources metadata", "nexus_events proof"], "no publish/send/trade/deploy/media download",
     "source_intake", "medium", True, True, True),
    ("Weekly YouTube Research Report", "youtube_research", "autonomous_internal", "weekly",
     ["local reports"], "no external AI or outbound action",
     "source_intake", "low", False, False, False),
    ("Weekly Hermes Prep Brief", "hermes_jarvis", "autonomous_internal", "weekly",
     ["local reports", "Hermes memory summaries"], "no external AI on sensitive data",
     "command_center", "low", False, False, False),
    ("Weekly GoClear Revenue Report", "goclear_revenue_hub", "autonomous_internal", "weekly",
     ["safe revenue metric cards/reports"], "no payment or email action",
     "opportunity_lab", "low", False, False, False),
    ("Weekly Trading Paper Report", "trading_lab", "autonomous_internal", "weekly",
     ["paper-only summaries"], "no broker API or live trading",
     "trading_lab", "low", False, True, True),
    ("Weekly Automation Control Report", "scheduler_automation", "autonomous_internal", "weekly",
     ["local automation control report"], "no activation of any automation",
     "ops_improvements", "low", False, False, False),
    ("Weekly SEO Opportunity Report", "seo_marketing", "autonomous_internal", "weekly",
     ["local reports", "internal cards"], "no publish/site change",
     "growth", "low", False, False, False),
    ("Weekly Affiliate Opportunity Report", "affiliate_marketing", "autonomous_internal", "weekly",
     ["local reports", "internal cards"], "no outbound contact/publish",
     "opportunity_lab", "low", False, False, False),
    ("Weekly Client Readiness Report", "goclear_apex_client_intake", "autonomous_internal", "weekly",
     ["internal readiness cards/reports"], "no client contact/notification; no client data exposure",
     "opportunity_lab", "low", False, False, True),
    ("Weekly Ops Improvement Report", "monitoring_health", "autonomous_internal", "weekly",
     ["internal status reports", "proof events"], "no destructive remediation",
     "ops_improvements", "low", False, False, False),
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--limit", type=int, default=11)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--report-path", default="")
    args = parser.parse_args()
    limit = max(1, min(args.limit, len(SCHEDULES)))
    candidates = []
    for (name, category, level, frequency, writes, forbidden, owner, risk,
         connector, external_api, high_risk) in SCHEDULES[:limit]:
        candidates.append({
            "schedule_name": name,
            "category": category,
            "automation_level": level,
            "frequency": frequency,
            "allowed_writes": writes,
            "forbidden_actions": forbidden,
            "owner": owner,
            "risk_level": risk,
            "ray_approval_required": True,
            "current_status": "proposed",
            "connector_required": connector,
            "external_api_required": external_api,
            "high_risk_guard_applies": high_risk,
            "disable_rollback_command": "Do not install scheduler until Ray approves; rollback is deleting the proposed item / unloading the (not-yet-created) job.",
            "proof_report_path": "reports/manual_publish/scheduler_approval_candidates_latest.md",
        })
    report = {
        "ok": True,
        "title": "Scheduler Approval Candidates",
        "generated_at": now(),
        "dry_run": True,
        "candidates": candidates,
        "counts": {
            "candidates": len(candidates),
            "proposed": len(candidates),
            "approved": 0,
            "active": 0,
            "blocked": 0,
            "created": 0,
            "failed": 0,
        },
        "summary": "Generated schedule-ready proposals only. No scheduler activated. No cron/launchd/systemd created.",
        "safety": {
            "scheduler_started": False,
            "cron_launchd_systemd_created": False,
            "publish_send_trade_deploy": False,
            "external_ai_called": False,
        },
    }
    write_report(report, RUNTIME, MANUAL, args.report_path)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"Scheduler approval candidates written: {RUNTIME.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
