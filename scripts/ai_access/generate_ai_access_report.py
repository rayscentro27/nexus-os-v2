#!/usr/bin/env python3
"""Generate the AI Department Access report (dry-run)."""
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
    violations = m.verify_invariants()
    report = {
        "ok": not violations,
        "title": "AI Department Access Report",
        "generated_at": m.now(),
        "dry_run": True,
        "roles": roles,
        "data_categories": m.DATA_CATEGORIES,
        "violations": violations,
        "counts": {"roles": len(roles), "data_categories": len(m.DATA_CATEGORIES), "violations": len(violations)},
        "summary": f"{len(roles)} AI roles documented; {len(violations)} access violation(s).",
        "safety": {"external_calls": False, "db_writes": False, "real_vault_connected": False},
    }
    RUNTIME.parent.mkdir(parents=True, exist_ok=True)
    RUNTIME.write_text(json.dumps(report, indent=2))
    L = [f"# {report['title']}", "", f"- generated_at: {report['generated_at']}", f"- ok: {report['ok']}", "", "## Roles"]
    for r in roles:
        L.append(f"### {r['role']}")
        L.append(f"- internet: {r['internet_allowed']} · vault: {r['vault_adapter_allowed']} · approved-knowledge-only: {r['approved_knowledge_only']} · client-facing: {r['client_facing_output']}")
        L.append(f"- allowed: {', '.join(r['allowed_tools'])}")
        L.append(f"- blocked: {', '.join(r['blocked_tools'])}")
        L.append("")
    MANUAL.parent.mkdir(parents=True, exist_ok=True)
    MANUAL.write_text("\n".join(L) + "\n")
    if a.report_path:
        Path(a.report_path).write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2) if a.json else report["summary"])
    return 0 if not violations else 1


if __name__ == "__main__":
    raise SystemExit(main())
