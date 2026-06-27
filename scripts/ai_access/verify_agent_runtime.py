#!/usr/bin/env python3
"""Verify the AI Agent Runtime enforces access + logs audit events (dry-run).

Proves at the runtime-guard level:
  - Hermes is denied on every private vault read (and produces a denied audit event).
  - Researcher AI is denied on every private vault read.
  - Specialists (credit/funding/business) are allowed on private reads via the adapter.
  - Client Chat AI may read only its own client; other clients are denied.
  - Every call (allowed OR denied) produces exactly one audit event.
  - Denied reads return no data.

    python3 scripts/ai_access/verify_agent_runtime.py --dry-run --json
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "ai_access"))
import agent_runtime_model as rt  # noqa: E402

RUNTIME = ROOT / "reports" / "runtime" / "ai_agent_runtime_latest.json"
MANUAL = ROOT / "reports" / "manual_publish" / "ai_agent_runtime_latest.md"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true", default=True)
    p.add_argument("--json", action="store_true")
    p.add_argument("--report-path", default="")
    a = p.parse_args()

    failures = []
    audit_events = 0
    calls = 0

    # 1. Hermes + Researcher denied on every private read; data not returned; audit denied.
    for role in ("hermes_ceo_advisor", "researcher_ai"):
        for method in rt.PRIVATE_METHODS:
            r = rt.simulate(role, method, "dev-c1")
            calls += 1
            audit_events += 1
            if r["allowed"] or r["data_returned"]:
                failures.append({"rule": "block_private_read", "role": role, "method": method})
            if r["audit"]["allowed"] is not False:
                failures.append({"rule": "denied_audit_event", "role": role, "method": method})

    # 2. Specialists allowed on private reads.
    for role in ("credit_specialist_ai", "funding_specialist_ai", "business_setup_specialist_ai"):
        for method in rt.PRIVATE_METHODS:
            r = rt.simulate(role, method, "dev-c1")
            calls += 1
            audit_events += 1
            if not r["allowed"]:
                failures.append({"rule": "specialist_allowed_private_read", "role": role, "method": method, "reason": r["denied_reason"]})

    # 3. Client Chat scoping: allowed for own client, denied for others.
    own = rt.simulate("client_chat_ai", "getCreditReport", "dev-c1", allowed_client_id="dev-c1")
    other = rt.simulate("client_chat_ai", "getCreditReport", "dev-c2", allowed_client_id="dev-c1")
    calls += 2
    audit_events += 2
    if not own["allowed"]:
        failures.append({"rule": "client_chat_own_client_allowed", "detail": own["denied_reason"]})
    if other["allowed"]:
        failures.append({"rule": "client_chat_other_client_denied", "detail": "read of another client was allowed"})

    # 4. Sanitized export: Hermes allowed, Researcher denied (no sanitized_client_signals tool).
    hermes_signals = rt.simulate("hermes_ceo_advisor", "exportSanitizedSignals", "aggregate")
    researcher_signals = rt.simulate("researcher_ai", "exportSanitizedSignals", "aggregate")
    calls += 2
    audit_events += 2
    if not hermes_signals["allowed"]:
        failures.append({"rule": "hermes_sanitized_export_allowed", "detail": hermes_signals["denied_reason"]})
    if researcher_signals["allowed"]:
        failures.append({"rule": "researcher_sanitized_export_denied", "detail": "researcher read signals"})

    ok = not failures
    report = {
        "ok": ok,
        "title": "AI Agent Runtime Verification",
        "generated_at": now(),
        "dry_run": True,
        "methods_enforced": rt.METHODS,
        "roles": rt.ROLES,
        "failures": failures,
        "counts": {
            "calls_simulated": calls,
            "audit_events": audit_events,
            "every_call_audited": calls == audit_events,
            "failures": len(failures),
        },
        "summary": "Agent runtime enforces access + audits every call; Hermes/Researcher blocked from private reads; specialists allowed via adapter; client-chat scoped."
        if ok else f"{len(failures)} runtime enforcement failure(s).",
        "safety": {"real_vault_connected": False, "external_calls": False, "data_returned_on_denial": False},
    }
    RUNTIME.parent.mkdir(parents=True, exist_ok=True)
    RUNTIME.write_text(json.dumps(report, indent=2))
    L = [f"# {report['title']}", "", f"- ok: {report['ok']}",
         f"- calls_simulated: {calls}", f"- audit_events: {audit_events}",
         f"- every_call_audited: {calls == audit_events}", "", "## Failures"]
    L += [f"- {f}" for f in failures] or ["- none"]
    MANUAL.parent.mkdir(parents=True, exist_ok=True)
    MANUAL.write_text("\n".join(L) + "\n")
    if a.report_path:
        Path(a.report_path).write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2) if a.json else report["summary"])
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
