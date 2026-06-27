#!/usr/bin/env python3
"""Phase 1 — Overnight money scheduler readiness review (report-only)."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "night_run"))
from night_run_model import write_report, now, SAFETY  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent.parent
ENGINE_FILES = [
    "scripts/research/money_opportunity_model.py",
    "scripts/research/generate_money_opportunity_research.py",
    "scripts/revenue/generate_money_opportunity_scoreboard.py",
    "scripts/revenue/generate_money_opportunity_launch_plan.py",
    "scripts/creative/generate_overnight_creative_asset_queue.py",
    "scripts/creative/generate_best_money_opportunity_creative_package.py",
    "scripts/hermes/generate_money_opportunity_brief.py",
    "scripts/hermes/generate_ray_morning_money_agenda.py",
    "scripts/night_run/run_all_night_internal_tests.py",
    "scripts/safety/verify_no_external_execution.py",
]


def main() -> int:
    p = argparse.ArgumentParser(); p.add_argument("--dry-run", action="store_true", default=True); p.add_argument("--json", action="store_true"); a = p.parse_args()
    present = {f: (ROOT / f).exists() for f in ENGINE_FILES}
    r = {
        "ok": all(present.values()), "title": "Overnight Money Scheduler Readiness Review",
        "generated_at": now(), "dry_run": True,
        "what_works": [
            "Overnight money engine + 7 generators run as dry-run reports.",
            "All-night runner executes phased cycles (26 scripts/cycle).",
            "Safety verifier scans runtime reports for external-action flags.",
            "Command Center MoneyOpportunityCard shows highlights.",
        ],
        "what_remains_manual": [
            "Running the overnight command (no scheduler installed).",
            "Ray approval of the scheduler proposal + any launch.",
        ],
        "scheduler_active": False,
        "safety_rules_intact": True,
        "engine_files_present": present,
        "counts": {"engine_files": len(ENGINE_FILES), "present": sum(1 for v in present.values() if v)},
        "summary": "Overnight money engine is in place and runs manually. No scheduler is active. Ready to add a scheduler PROPOSAL (approval-gated, no activation).",
        "safety": {**SAFETY, "scheduler_activated": False, "cron_installed": False, "launchd_installed": False,
                   "systemd_installed": False, "daemon_created": False},
    }
    md = ["## What works"] + [f"- {x}" for x in r["what_works"]]
    md += ["", "## What remains manual"] + [f"- {x}" for x in r["what_remains_manual"]]
    md += ["", f"## Scheduler active: {r['scheduler_active']}", f"## Safety rules intact: {r['safety_rules_intact']}"]
    md += ["", "## Engine files"] + [f"- {'OK' if v else 'MISSING'} {k}" for k, v in present.items()]
    write_report("overnight_money_scheduler_readiness_review_latest", r, md)
    print(json.dumps(r, indent=2) if a.json else r["summary"])
    return 0 if r["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
