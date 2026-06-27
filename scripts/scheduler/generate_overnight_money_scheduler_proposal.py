#!/usr/bin/env python3
"""Phase 2 — Overnight Money scheduler PROPOSAL generator (inactive; approval-required)."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "night_run"))
from night_run_model import write_report, now, SAFETY  # noqa: E402

PROPOSAL = {
    "proposal_id": "overnight_money_run_v1",
    "title": "Overnight Money Opportunity Run",
    "description": "Proposes a nightly dry-run of the all-night money runner (research -> score -> draft -> rolling agenda -> safety verify). Activation NOT included.",
    "command": "python3 scripts/night_run/run_all_night_internal_tests.py --dry-run --cycles 8 --interval-minutes 45 --json",
    "dry_run": True,
    "cycles": 8,
    "interval_minutes": 45,
    "proposed_start_time": "22:00 local",
    "recurrence": "daily",
    "timing_mode": "proposed_only_not_installed",
    "expected_outputs": [
        "reports/runtime/overnight_money_cycle_history_latest.jsonl",
        "reports/manual_publish/all_night_money_run_summary_latest.md",
        "reports/manual_publish/rolling_morning_money_agenda_latest.md",
        "reports/manual_publish/hermes_rolling_money_morning_brief_latest.md",
        "reports/manual_publish/no_external_execution_verification_latest.md",
    ],
    "safety_checks": ["python3 scripts/safety/verify_no_external_execution.py --dry-run --json"],
    "approval_required": True,
    "approval_status": "awaiting_ray_approval",
    "activation_status": "not_enabled",
    "risk_level": "medium",
    "blocked_actions": [
        "install cron / launchd / systemd", "create a daemon",
        "publish / send / post / upload / deploy", "spend money / charge clients / activate payment links",
        "contact clients / activate partner links externally", "connect live Client Vault / use raw client data",
        "external AI on private client data / scrape / live trading",
    ],
}


def main() -> int:
    p = argparse.ArgumentParser(); p.add_argument("--dry-run", action="store_true", default=True); p.add_argument("--json", action="store_true"); a = p.parse_args()
    r = {
        "ok": True, "title": "Overnight Money Scheduler Proposal", "generated_at": now(), "dry_run": True,
        "proposal": {**PROPOSAL, "created_at": now(), "updated_at": now()},
        "counts": {"expected_outputs": len(PROPOSAL["expected_outputs"]), "blocked_actions": len(PROPOSAL["blocked_actions"])},
        "summary": "Scheduler PROPOSAL generated (inactive). Approval required; activation not enabled; no cron/launchd/systemd/daemon installed.",
        "safety": {**SAFETY, "scheduler_activated": False, "cron_installed": False, "launchd_installed": False,
                   "systemd_installed": False, "daemon_created": False},
    }
    md = [f"## {PROPOSAL['title']}", f"- proposal_id: {PROPOSAL['proposal_id']}",
          f"- command: `{PROPOSAL['command']}`",
          f"- schedule: {PROPOSAL['recurrence']} @ {PROPOSAL['proposed_start_time']} · {PROPOSAL['cycles']} cycles · {PROPOSAL['interval_minutes']}m interval",
          f"- dry_run: {PROPOSAL['dry_run']} · risk: {PROPOSAL['risk_level']}",
          f"- approval_status: {PROPOSAL['approval_status']} · activation_status: {PROPOSAL['activation_status']}",
          "", "## Expected outputs"] + [f"- {x}" for x in PROPOSAL["expected_outputs"]]
    md += ["", "## Safety checks"] + [f"- {x}" for x in PROPOSAL["safety_checks"]]
    md += ["", "## Blocked actions (not performed)"] + [f"- {x}" for x in PROPOSAL["blocked_actions"]]
    write_report("overnight_money_scheduler_proposal_latest", r, md)
    print(json.dumps(r, indent=2) if a.json else r["summary"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
