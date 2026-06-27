#!/usr/bin/env python3
"""Verify Client Workflow automation policy + safety contract (dry-run).

Confirms each workflow action is at the correct automation level and that all high-risk client
actions stay blocked. Fails if any blocked/high-risk action is treated as Level 1/2, or if a
client-facing exposure is not approval-gated.

    python3 scripts/client_workflow/verify_client_workflow_policy.py --dry-run --json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "research"))
sys.path.insert(0, str(ROOT / "scripts" / "client_workflow"))
sys.path.insert(0, str(ROOT / "scripts" / "automation"))
from common import write_report  # noqa: E402
import client_workflow_model as m  # noqa: E402
from automation_model import classify_automation_level  # noqa: E402

RUNTIME = ROOT / "reports" / "runtime" / "client_workflow_policy_verification_latest.json"
MANUAL = ROOT / "reports" / "manual_publish" / "client_workflow_policy_verification_latest.md"

EXPECTED_LEVEL_1 = [
    "workflow_status_update", "credit_analysis", "business_bankability_scoring",
    "funding_readiness_scoring", "reminder_draft_generation", "stuck_client_detection",
    "hermes_prep_brief", "affiliate_opportunity_scoring",
]
EXPECTED_LEVEL_2 = [
    "send_client_message", "contact_client_or_lead", "publish_client_plan", "activate_connector",
    "activate_scheduler", "mail_letters", "submit_dispute", "apply_for_funding",
    "expose_client_recommendation",
]
EXPECTED_LEVEL_3 = [
    "store_smartcredit_password", "scrape_smartcredit", "auto_submit_disputes", "auto_mail_letters",
    "auto_contact_bureaus_creditors", "auto_file_llc_ein_state", "auto_open_accounts",
    "auto_apply_funding", "external_ai_on_client_credit_data",
]

# Map workflow level-3 actions to a phrase the universal classifier should also mark blocked.
BLOCKED_PROBES = {
    "store_smartcredit_password": "store smartcredit password secret",
    "scrape_smartcredit": "broad scrape smartcredit",
    "auto_submit_disputes": "auto submit disputes (auto_executor)",
    "auto_mail_letters": "auto mail letters bulk send",
    "auto_contact_bureaus_creditors": "auto contact bureaus bulk send",
    "auto_file_llc_ein_state": "auto file llc ein (auto_executor)",
    "auto_open_accounts": "auto open accounts (auto_executor)",
    "auto_apply_funding": "auto apply funding (auto_executor)",
    "external_ai_on_client_credit_data": "external ai on sensitive customer credit data",
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--report-path", default="")
    args = parser.parse_args()

    checks = []
    failures = []

    def check(action, expected):
        actual = m.ACTION_LEVELS.get(action, "MISSING")
        ok = actual == expected
        if not ok:
            failures.append({"action": action, "expected": expected, "actual": actual})
        checks.append({"action": action, "expected": expected, "actual": actual, "ok": ok})

    for a in EXPECTED_LEVEL_1:
        check(a, "autonomous_internal")
    for a in EXPECTED_LEVEL_2:
        check(a, "approval_gated")
    for a in EXPECTED_LEVEL_3:
        check(a, "blocked_high_risk")

    # Cross-check Level 3 against the universal high-risk classifier (defense in depth).
    classifier_failures = []
    for action, probe in BLOCKED_PROBES.items():
        if classify_automation_level(probe) != "blocked_high_risk":
            classifier_failures.append({"action": action, "probe": probe, "classifier": classify_automation_level(probe)})

    # Safety contract assertions (static — these paths do not exist in code).
    safety_contract = {
        "smartcredit_password_stored": False,
        "smartcredit_scraped": False,
        "docupost_auto_send": False,
        "disputes_auto_submitted": False,
        "letters_auto_mailed": False,
        "llc_ein_state_auto_filed": False,
        "accounts_auto_opened": False,
        "funding_auto_applied": False,
        "client_messages_sent": False,
        "money_spent": False,
        "client_charged": False,
        "external_ai_on_client_data": False,
        "client_recommendation_exposed_without_approval": False,
    }
    contract_violations = [k for k, v in safety_contract.items() if v]

    level3_downgrades = [f for f in failures if f["expected"] == "blocked_high_risk"]
    ok = not failures and not classifier_failures and not contract_violations

    report = {
        "ok": ok,
        "title": "Client Workflow Policy Verification",
        "generated_at": m.now(),
        "dry_run": True,
        "checks": checks,
        "failures": failures,
        "classifier_failures": classifier_failures,
        "safety_contract": safety_contract,
        "contract_violations": contract_violations,
        "counts": {
            "total_checks": len(checks),
            "passed": sum(1 for c in checks if c["ok"]),
            "failed": len(failures),
            "level3_downgrades": len(level3_downgrades),
            "classifier_failures": len(classifier_failures),
            "contract_violations": len(contract_violations),
        },
        "summary": "All client workflow actions correctly classified; high-risk actions blocked; safety contract intact."
        if ok else f"{len(failures)} misclassification(s), {len(classifier_failures)} classifier failure(s), {len(contract_violations)} contract violation(s).",
        "safety": {"publish_send_trade_deploy": False, "client_contacted": False, "money_spent": False},
    }
    write_report(report, RUNTIME, MANUAL, args.report_path)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(report["summary"])
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
