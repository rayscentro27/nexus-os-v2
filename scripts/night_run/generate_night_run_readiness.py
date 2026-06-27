#!/usr/bin/env python3
"""Part 4 — Night-run readiness: run every safe dry-run script and aggregate results.

Each wrapped script is internal/report-only and run with --dry-run --json. No external action.
"""
from __future__ import annotations
import argparse, json, subprocess, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import night_run_model as nm  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent.parent

SAFE_SCRIPTS = [
    "scripts/automation/generate_automation_control_report.py",
    "scripts/automation/verify_automation_policy.py",
    "scripts/automation/verify_high_risk_guards.py",
    "scripts/automation/generate_scheduler_approval_candidates.py",
    "scripts/ai_access/verify_ai_department_access.py",
    "scripts/ai_access/verify_agent_runtime.py",
    "scripts/ai_access/generate_ai_access_report.py",
    "scripts/ai_access/generate_credit_specialist_contract_report.py",
    "scripts/ai_access/generate_hermes_redaction_report.py",
    "scripts/client_vault/generate_client_vault_contract_report.py",
    "scripts/client_vault/verify_client_vault_contract.py",
    "scripts/client_workflow/generate_client_workflow_report.py",
    "scripts/client_workflow/generate_affiliate_recommendation_report.py",
    "scripts/client_workflow/generate_stuck_client_report.py",
    "scripts/client_workflow/generate_hermes_client_recommendations.py",
    "scripts/client_workflow/verify_client_workflow_policy.py",
    "scripts/night_run/generate_night_run_project_review.py",
    "scripts/night_run/generate_process_inventory.py",
    "scripts/night_run/generate_automation_night_readiness.py",
    "scripts/night_run/generate_hermes_executive_brief.py",
    "scripts/night_run/generate_goclear_subscription_market_research.py",
    "scripts/night_run/generate_online_business_bank_affiliate_research.py",
    "scripts/night_run/generate_revenue_streams.py",
    "scripts/night_run/generate_client_workflow_monetization.py",
    "scripts/night_run/generate_business_setup_banking_monetization.py",
    "scripts/night_run/generate_docupost_usps_mailing_monetization.py",
    "scripts/night_run/generate_client_reminder_revenue_risk.py",
    "scripts/night_run/generate_approval_and_blocked.py",
]


def run_one(rel: str) -> dict:
    try:
        proc = subprocess.run([sys.executable, str(ROOT / rel), "--dry-run", "--json"],
                              capture_output=True, text=True, timeout=120)
        ok = None
        try:
            ok = json.loads(proc.stdout).get("ok")
        except Exception:
            ok = proc.returncode == 0
        return {"script": rel, "exit_code": proc.returncode, "ok": bool(ok),
                "error": proc.stderr.strip()[-300:] if proc.returncode != 0 else ""}
    except Exception as e:  # noqa: BLE001
        return {"script": rel, "exit_code": -1, "ok": False, "error": str(e)[-300:]}


def main() -> int:
    p = argparse.ArgumentParser(); p.add_argument("--dry-run", action="store_true", default=True); p.add_argument("--json", action="store_true"); a = p.parse_args()
    results = [run_one(s) for s in SAFE_SCRIPTS]
    ran = [r for r in results if r["exit_code"] == 0 and r["ok"]]
    failed = [r for r in results if not (r["exit_code"] == 0 and r["ok"])]
    report = {
        "ok": len(failed) == 0,
        "title": "Nexus Night-Run Readiness",
        "generated_at": nm.now(),
        "dry_run": True,
        "what_ran": [r["script"] for r in ran],
        "what_failed": failed,
        "what_is_blocked": [p[0] for p in nm.PROCESS_INVENTORY if p[2] == "blocked_by_policy"],
        "what_needs_approval": [p[0] for p in nm.PROCESS_INVENTORY if p[2] == "approval_required"],
        "what_should_happen_next": [
            "Validate GoClear subscription pricing; confirm online-bank affiliate primary.",
            "Review Ray Review Queue items; approve plans before client exposure.",
            "Keep schedulers/connectors off until approved.",
        ],
        "counts": {"total": len(results), "ran_ok": len(ran), "failed": len(failed)},
        "summary": f"Night run: {len(ran)}/{len(results)} safe dry-run scripts passed. "
                   + ("All green." if not failed else f"{len(failed)} failed."),
        "safety": nm.SAFETY,
    }
    md = [f"## Ran OK ({len(ran)}/{len(results)})"] + [f"- {s}" for s in report["what_ran"]]
    if failed:
        md += ["", "## Failed"] + [f"- {f['script']} (exit {f['exit_code']}): {f['error']}" for f in failed]
    md += ["", "## Blocked by policy"] + [f"- {x}" for x in report["what_is_blocked"]]
    md += ["", "## Needs approval"] + [f"- {x}" for x in report["what_needs_approval"]]
    md += ["", "## What should happen next"] + [f"- {x}" for x in report["what_should_happen_next"]]
    nm.write_report("nexus_night_run_readiness_latest", report, md)
    print(json.dumps(report, indent=2) if a.json else report["summary"])
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
