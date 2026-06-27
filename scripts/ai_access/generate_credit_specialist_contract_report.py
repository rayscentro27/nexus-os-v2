#!/usr/bin/env python3
"""Generate the Credit Specialist Supabase-only contract report (dry-run)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "ai_access"))
import ai_access_model as m  # noqa: E402

RUNTIME = ROOT / "reports" / "runtime" / "credit_specialist_contract_latest.json"
MANUAL = ROOT / "reports" / "manual_publish" / "credit_specialist_contract_latest.md"

MAY_USE = [
    "approved_credit_knowledge", "approved_dispute_rules", "approved_funding_readiness_rules",
    "approved_compliance_language", "mock_client_credit_report_via_vault_adapter",
    "mock_client_business_setup_via_vault_adapter", "client_workflow_tasks_via_adapter",
    "client_action_plan_drafts",
]
MUST_NOT_USE = [
    "internet", "web_browsing", "youtube", "unapproved_research", "external_ai_on_client_data",
    "raw_client_vault_production_connection", "production_smartcredit_files",
]


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true", default=True)
    p.add_argument("--json", action="store_true")
    p.add_argument("--report-path", default="")
    a = p.parse_args()

    acc = m.TOOL_ACCESS["credit_specialist_ai"]
    no_web = not (acc["allowed"] & m.INTERNET_TOOLS)
    proofs = {
        "supabase_only_no_web_tools": no_web,
        "approved_knowledge_only": m.ROLE_META["credit_specialist_ai"]["approved_knowledge_only"],
        "vault_mock_only": m.ROLE_META["credit_specialist_ai"]["vault"],
        "client_facing_approval_gated": m.ROLE_META["credit_specialist_ai"]["client_facing"] == "approval_gated",
        "no_external_ai_on_client_data": "external_ai_api" in acc["blocked"],
    }
    ok = all(proofs.values())
    report = {
        "ok": ok,
        "title": "Credit Specialist Supabase-Only Contract",
        "generated_at": m.now(),
        "dry_run": True,
        "may_use": MAY_USE,
        "must_not_use": MUST_NOT_USE,
        "proofs": proofs,
        "counts": {"may_use": len(MAY_USE), "must_not_use": len(MUST_NOT_USE),
                   "proofs_passed": sum(1 for v in proofs.values() if v), "proofs_total": len(proofs)},
        "summary": "Credit Specialist Supabase-only contract intact." if ok else "Contract proof failed.",
        "safety": {"internet_used": False, "external_ai_on_client_data": False, "production_vault_connected": False},
    }
    RUNTIME.parent.mkdir(parents=True, exist_ok=True)
    RUNTIME.write_text(json.dumps(report, indent=2))
    L = [f"# {report['title']}", "", f"- ok: {report['ok']}", "", "## Proofs"] + [f"- {k}: {v}" for k, v in proofs.items()]
    L += ["", "## May use"] + [f"- {x}" for x in MAY_USE] + ["", "## Must NOT use"] + [f"- {x}" for x in MUST_NOT_USE]
    MANUAL.parent.mkdir(parents=True, exist_ok=True)
    MANUAL.write_text("\n".join(L) + "\n")
    if a.report_path:
        Path(a.report_path).write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2) if a.json else report["summary"])
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
