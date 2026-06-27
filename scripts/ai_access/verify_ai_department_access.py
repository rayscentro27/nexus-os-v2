#!/usr/bin/env python3
"""Verify AI Department Access Controls (dry-run).

Fails if any access invariant is violated: Hermes raw-data block, internet/vault separation,
specialist no-web-tools, researcher no-PII, client-facing gating, approved-knowledge-only.

    python3 scripts/ai_access/verify_ai_department_access.py --dry-run --json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "ai_access"))
import ai_access_model as m  # noqa: E402

RUNTIME = ROOT / "reports" / "runtime" / "ai_department_access_latest.json"
MANUAL = ROOT / "reports" / "manual_publish" / "ai_department_access_latest.md"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true", default=True)
    p.add_argument("--json", action="store_true")
    p.add_argument("--report-path", default="")
    a = p.parse_args()

    violations = m.verify_invariants()
    # Explicit blocked-access proofs.
    proofs = {
        "hermes_cannot_read_raw_credit_report": not m.can_access_data("hermes_ceo_advisor", "raw_credit_report"),
        "hermes_cannot_read_smartcredit_file": not m.can_access_data("hermes_ceo_advisor", "smartcredit_file"),
        "hermes_cannot_read_bank_statement": not m.can_access_data("hermes_ceo_advisor", "bank_statement"),
        "hermes_cannot_read_raw_letter": not m.can_access_data("hermes_ceo_advisor", "raw_letter"),
        "internet_tools_cannot_access_vault": all(
            not (m.TOOL_ACCESS[r]["allowed"] & m.INTERNET_TOOLS and "client_vault_adapter" in m.TOOL_ACCESS[r]["allowed"])
            for r in m.TOOL_ACCESS
        ),
        "credit_specialist_no_web_tools": not (m.TOOL_ACCESS["credit_specialist_ai"]["allowed"] & m.INTERNET_TOOLS),
        "researcher_cannot_access_pii": not m.can_access_data("researcher_ai", "raw_credit_report"),
        "client_facing_all_gated": all(meta["client_facing"] in ("blocked", "approval_gated") for meta in m.ROLE_META.values()),
    }
    ok = not violations and all(proofs.values())

    roles = []
    for role, meta in m.ROLE_META.items():
        roles.append({
            "role": role,
            "internet_allowed": meta["internet"],
            "vault_adapter_allowed": meta["vault"],
            "approved_knowledge_only": meta["approved_knowledge_only"],
            "client_facing_output": meta["client_facing"],
            "allowed_tools": sorted(m.TOOL_ACCESS[role]["allowed"]),
            "blocked_tools": sorted(m.TOOL_ACCESS[role]["blocked"]),
        })

    report = {
        "ok": ok,
        "title": "AI Department Access Verification",
        "generated_at": m.now(),
        "dry_run": True,
        "roles": roles,
        "blocked_access_proofs": proofs,
        "violations": violations,
        "counts": {"roles": len(roles), "violations": len(violations),
                   "proofs_passed": sum(1 for v in proofs.values() if v), "proofs_total": len(proofs)},
        "summary": "All AI department access invariants intact." if ok else f"{len(violations)} violation(s) detected.",
        "safety": {"external_calls": False, "db_writes": False, "real_vault_connected": False},
    }
    RUNTIME.parent.mkdir(parents=True, exist_ok=True)
    RUNTIME.write_text(json.dumps(report, indent=2))
    L = [f"# {report['title']}", "", f"- generated_at: {report['generated_at']}", f"- ok: {report['ok']}", "", "## Blocked-access proofs"]
    L += [f"- {k}: {v}" for k, v in proofs.items()]
    L += ["", "## Violations"] + ([f"- {v['rule']}: {v['detail']}" for v in violations] or ["- none"])
    MANUAL.parent.mkdir(parents=True, exist_ok=True)
    MANUAL.write_text("\n".join(L) + "\n")
    if a.report_path:
        Path(a.report_path).write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2) if a.json else report["summary"])
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
