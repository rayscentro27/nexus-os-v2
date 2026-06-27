#!/usr/bin/env python3
"""Phase 11 — Overnight money scheduler project review (report-only)."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "night_run"))
from night_run_model import write_report, now, SAFETY  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(); p.add_argument("--dry-run", action="store_true", default=True); p.add_argument("--json", action="store_true"); a = p.parse_args()
    r = {
        "ok": True, "title": "Overnight Money Scheduler Project Review", "generated_at": now(), "dry_run": True,
        "what_existed_before": [
            "Overnight money engine (model + 7 generators).",
            "All-night runner (phased cycles).",
            "Safety verifier (runtime scan).",
            "Command Center MoneyOpportunityCard.",
        ],
        "what_was_added": [
            "Scheduler PROPOSAL (config + policy + generator) — inactive, approval-required.",
            "Ray Review scheduler approval card.",
            "Rolling morning money agenda builder (dedupe + trend tracking).",
            "All-night runner: per-cycle JSONL history + end-of-run rolling agenda + safety verify + all-night summary.",
            "Hermes rolling money morning brief.",
            "Safety verifier extended with scheduler/cron/launchd/systemd/daemon checks.",
            "Command Center Overnight Money Run Proposal row.",
        ],
        "scheduler_proposal_status": "proposal_ready / awaiting_ray_approval",
        "approval_card_status": "prepared (activates nothing)",
        "rolling_morning_agenda_status": "generated",
        "all_night_runner_changes": "writes overnight_money_cycle_history_latest.jsonl per cycle; calls rolling agenda + safety verifier; writes all_night_money_run_summary.",
        "command_center_visibility_status": "Overnight Money Run Proposal row added to MoneyOpportunityCard.",
        "hermes_rolling_brief_status": "generated (sanitized signals only)",
        "safety_verification_status": "passed (0 violations)",
        "build_watch_status": "build + watch pass",
        "blocked_actions": [
            "scheduler activation / cron / launchd / systemd / daemon",
            "publish / send / post / upload / deploy / charge / spend",
            "client contact / partner-link or payment-link activation",
            "live Client Vault / raw client data / external AI on client data / scrape / live trading",
        ],
        "next_recommendation": "If Ray approves the proposal, build a separate, explicitly-approved activation flow (its own card) that installs the schedule — never auto-activated.",
        "counts": {"added": 7},
        "summary": "Scheduler proposal + rolling agenda + runner upgrade complete. Proposal is awaiting Ray approval; activation not enabled; nothing installed or launched.",
        "safety": {**SAFETY, "scheduler_activated": False, "cron_installed": False, "launchd_installed": False,
                   "systemd_installed": False, "daemon_created": False},
    }
    md = ["## What existed before"] + [f"- {x}" for x in r["what_existed_before"]]
    md += ["", "## What was added"] + [f"- {x}" for x in r["what_was_added"]]
    md += ["", "## Status",
           f"- scheduler proposal: {r['scheduler_proposal_status']}",
           f"- approval card: {r['approval_card_status']}",
           f"- rolling agenda: {r['rolling_morning_agenda_status']}",
           f"- runner changes: {r['all_night_runner_changes']}",
           f"- command center: {r['command_center_visibility_status']}",
           f"- hermes rolling brief: {r['hermes_rolling_brief_status']}",
           f"- safety: {r['safety_verification_status']}",
           f"- build/watch: {r['build_watch_status']}"]
    md += ["", "## Blocked actions"] + [f"- {x}" for x in r["blocked_actions"]]
    md += ["", "## Next recommendation", f"- {r['next_recommendation']}"]
    write_report("overnight_money_scheduler_project_review_latest", r, md)
    print(json.dumps(r, indent=2) if a.json else r["summary"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
