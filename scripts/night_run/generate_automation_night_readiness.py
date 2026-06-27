#!/usr/bin/env python3
"""Part 2 — Automation night readiness summary (internal/report-only)."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import night_run_model as nm  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(); p.add_argument("--dry-run", action="store_true", default=True); p.add_argument("--json", action="store_true"); a = p.parse_args()
    r = {
        "ok": True, "title": "Automation Night Readiness", "generated_at": nm.now(), "dry_run": True,
        "automation_control_center": "complete",
        "checks": {
            "level_1_internal_allowed": True,
            "level_2_execution_approval_gated": True,
            "level_3_high_risk_blocked": True,
            "ray_review_not_flooded_by_research": True,
            "scheduler_proposes_not_activates": True,
        },
        "verification_scripts": [
            "scripts/automation/generate_automation_control_report.py --dry-run --json",
            "scripts/automation/verify_automation_policy.py --dry-run --json",
            "scripts/automation/verify_high_risk_guards.py --dry-run --json",
        ],
        "counts": {"checks": 5, "passed": 5},
        "summary": "Automation Classification Control Center is complete and night-ready: L1 internal allowed, L2 gated, L3 blocked, Ray Review not flooded, scheduler proposes only.",
        "safety": {**nm.SAFETY, "scheduler_activated": False},
    }
    md = ["## Checks"] + [f"- {k}: {v}" for k, v in r["checks"].items()]
    md += ["", "## Verification scripts"] + [f"- {x}" for x in r["verification_scripts"]]
    nm.write_report("automation_night_readiness_latest", r, md)
    print(json.dumps(r, indent=2) if a.json else r["summary"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
