#!/usr/bin/env python3
"""Generate the AI Agent Runtime report (dry-run): full enforcement matrix + sample audit log."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "ai_access"))
import agent_runtime_model as rt  # noqa: E402

RUNTIME = ROOT / "reports" / "runtime" / "ai_agent_runtime_report_latest.json"
MANUAL = ROOT / "reports" / "manual_publish" / "ai_agent_runtime_report_latest.md"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true", default=True)
    p.add_argument("--json", action="store_true")
    p.add_argument("--report-path", default="")
    a = p.parse_args()

    matrix = {}
    sample_audit = []
    allowed_total = 0
    denied_total = 0
    for role in rt.ROLES:
        row = {}
        for method in rt.METHODS:
            scope = "dev-c1" if role == "client_chat_ai" else None
            r = rt.simulate(role, method, "dev-c1", allowed_client_id=scope)
            row[method] = "allow" if r["allowed"] else "deny"
            allowed_total += 1 if r["allowed"] else 0
            denied_total += 0 if r["allowed"] else 1
            if method in ("getCreditReport", "exportSanitizedSignals"):
                sample_audit.append(r["audit"])
        matrix[role] = row

    report = {
        "ok": True,
        "title": "AI Agent Runtime Report",
        "generated_at": now(),
        "dry_run": True,
        "enforcement_matrix": matrix,
        "method_specs": {k: {"tool": v[0], "data_category": v[1], "audit_category": v[2], "client_scoped": v[3]}
                         for k, v in rt.VAULT_METHOD_SPECS.items()},
        "sample_audit_log": sample_audit,
        "counts": {
            "roles": len(rt.ROLES),
            "methods": len(rt.METHODS),
            "allow_cells": allowed_total,
            "deny_cells": denied_total,
            "sample_audit_events": len(sample_audit),
        },
        "summary": "Runtime enforcement matrix generated; every vault read is access-gated and audit-logged. Mock adapter only.",
        "safety": {"real_vault_connected": False, "external_calls": False},
    }
    RUNTIME.parent.mkdir(parents=True, exist_ok=True)
    RUNTIME.write_text(json.dumps(report, indent=2))
    L = [f"# {report['title']}", "", f"- generated_at: {report['generated_at']}", "", "## Enforcement matrix (role × method)"]
    for role, row in matrix.items():
        denies = [meth for meth, d in row.items() if d == "deny"]
        allows = [meth for meth, d in row.items() if d == "allow"]
        L.append(f"### {role}")
        L.append(f"- allow: {', '.join(allows) or 'none'}")
        L.append(f"- deny: {', '.join(denies) or 'none'}")
        L.append("")
    L += ["## Sample audit log"]
    for e in sample_audit:
        L.append(f"- {e['agent_role']} · {e['data_category']} · allowed={e['allowed']}" + (f" · {e['denied_reason']}" if e["denied_reason"] else ""))
    MANUAL.parent.mkdir(parents=True, exist_ok=True)
    MANUAL.write_text("\n".join(L) + "\n")
    if a.report_path:
        Path(a.report_path).write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2) if a.json else report["summary"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
