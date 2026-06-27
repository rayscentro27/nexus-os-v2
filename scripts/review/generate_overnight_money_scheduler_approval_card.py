#!/usr/bin/env python3
"""Phase 3 — Ray Review approval card for the overnight money scheduler proposal (activates nothing)."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "night_run"))
from night_run_model import write_report, now, SAFETY  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(); p.add_argument("--dry-run", action="store_true", default=True); p.add_argument("--json", action="store_true"); a = p.parse_args()
    card = {
        "title": "Approve Overnight Money Opportunity Run Proposal",
        "summary": "Approve the PROPOSAL to run the all-night money runner nightly in dry-run. Approval does NOT install or activate a scheduler — activation remains a separate, approval-gated step.",
        "proposed_command": "python3 scripts/night_run/run_all_night_internal_tests.py --dry-run --cycles 8 --interval-minutes 45 --json",
        "schedule": "daily @ 22:00 local · 8 cycles · 45m interval",
        "dry_run_mode": True,
        "output_reports": [
            "rolling_morning_money_agenda_latest", "all_night_money_run_summary_latest",
            "hermes_rolling_money_morning_brief_latest", "no_external_execution_verification_latest",
        ],
        "safety_verifier": "scripts/safety/verify_no_external_execution.py --dry-run --json",
        "what_it_can_do": [
            "Run internal dry-run research/scoring/drafting in cycles.",
            "Build a rolling morning agenda and Hermes brief.",
            "Run the safety verifier and write reports.",
        ],
        "what_it_cannot_do": [
            "Install cron/launchd/systemd or create a daemon.",
            "Publish, send, post, upload, deploy, charge, or spend.",
            "Contact clients, activate partner/payment links, connect Client Vault, or use raw client data.",
        ],
        "risk_level": "medium",
        "approval_required": True,
        "recommended_decision": "Approve proposal for future scheduler activation, but keep activation separate.",
        "launch_status": "proposal_ready",
        "decision_reason": "scheduler_activation_request",
        "executed": False,
        "report_links": [
            "reports/manual_publish/overnight_money_scheduler_proposal_latest.md",
            "reports/manual_publish/rolling_morning_money_agenda_latest.md",
        ],
    }
    r = {
        "ok": True, "title": "Overnight Money Scheduler Approval Card", "generated_at": now(), "dry_run": True,
        "card": card, "counts": {"cards": 1},
        "summary": "Ray Review approval card prepared (proposal-only). Approval enables a separate activation flow later; nothing is activated now.",
        "safety": {**SAFETY, "scheduler_activated": False, "cron_installed": False, "auto_approved": False, "executed": False},
    }
    md = [f"## {card['title']}", card["summary"], "",
          f"- proposed command: `{card['proposed_command']}`",
          f"- schedule: {card['schedule']}", f"- risk: {card['risk_level']}",
          f"- recommended decision: {card['recommended_decision']}", "",
          "### What it CAN do"] + [f"- {x}" for x in card["what_it_can_do"]]
    md += ["", "### What it CANNOT do"] + [f"- {x}" for x in card["what_it_cannot_do"]]
    write_report("overnight_money_scheduler_approval_card_latest", r, md)
    print(json.dumps(r, indent=2) if a.json else r["summary"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
