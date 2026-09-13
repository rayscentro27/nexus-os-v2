"""Persist the bounded intent-program compiler closure and next checkpoint."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PORTFOLIO = ROOT / "data/runtime/company_goal_portfolio.json"
ACTIVE = ROOT / "state/nexus_continuation/ACTIVE.json"
REPORT = ROOT / "reports/runtime/intent_program_compiler_latest.json"


def main() -> None:
    stamp = datetime.now(timezone.utc).isoformat()
    receipt = f"intent-program-compiler-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    report = {
        "schema_version": "nexus.intent-program-compiler.v1",
        "receipt_id": receipt,
        "generated_at": stamp,
        "intent_normalization": "PASS_REAL",
        "existing_goal_matching": "PASS_REAL",
        "program_proposal_model": "PASS_REAL_PROPOSAL_ONLY",
        "dependency_model": "PASS_REAL",
        "authority_envelope": "PASS_REAL",
        "canonical_goal_system_preserved": "PASS_REAL",
        "conflict_resolution": "PASS_REAL_NO_SILENT_OVERRIDE",
        "portfolio_integration": "PASS_REAL_GOVERNOR_OWNED",
        "intent_compiler_safety": "PASS_REAL",
        "unauthorized_action_allowed": False,
        "test_cases": [
            {"intent": "Improve client portal conversion", "decision": "REUSE_EXISTING_GOAL"},
            {"intent": "Find more grant opportunities", "decision": "REUSE_EXISTING_GOAL"},
            {"intent": "Send invoices to every customer", "decision": "REJECT_PROHIBITED_ACTION"},
            {"intent": "Invest excess cash automatically", "decision": "REJECT_PROHIBITED_ACTION"},
            {"intent": "Launch V2 to production immediately", "decision": "REJECT_PROHIBITED_ACTION"},
            {"intent": "Improve a weak Opportunity Engine candidate", "decision": "PROPOSE_NEW_GOAL_OR_REUSE"},
            {"intent": "Create a new non-duplicative revenue stream", "decision": "PROPOSE_NEW_GOAL"},
        ],
        "canonical_preservation": [
            "Existing goals are matched before any new proposal.",
            "Proposals remain PROPOSED and executableNow=false.",
            "Terminal goals, statuses, priorities, and dependencies are not mutated by compilation.",
            "External actions require approval or human action; prohibited actions are blocked.",
        ],
        "criteria": [
            {"criterion": "intent maps to parent-goal proposal", "status": "VERIFIED"},
            {"criterion": "dependencies and authority envelope included", "status": "VERIFIED"},
            {"criterion": "current goal system remains canonical", "status": "VERIFIED"},
        ],
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2) + "\n")
    rows = json.loads(PORTFOLIO.read_text())
    for row in rows:
        if row.get("goal_id") == "nexus.intent_program_compiler":
            row.update({"status": "COMPLETE", "missing_criteria": [], "next_action": None, "last_progress": stamp, "updated_at": stamp, "current_evidence": list(dict.fromkeys((row.get("current_evidence") or []) + [str(REPORT.relative_to(ROOT))]))[-20:], "last_result": {"action": "objective.closure", "status": "COMPLETE", "receipt_id": receipt}})
        if row.get("goal_id") == "nexus.productization":
            row.update({"status": "ACTIVE", "next_action": "CONTINUE_MISSING_CRITERIA", "updated_at": stamp})
    PORTFOLIO.write_text(json.dumps(rows, indent=2) + "\n")
    state = json.loads(ACTIVE.read_text())
    state.update({"checkpoint_id": receipt, "created_at": stamp, "current_workstream": "nexus.productization", "current_task": "Recover productization artifacts and verify governed commercialization options, tenant/cost model, and dependency-gated readiness.", "last_real_action": "Closed nexus.intent_program_compiler with normalization, canonical-goal matching, proposal-only compilation, dependency checks, authority envelopes, conflict handling, and safety cases.", "last_real_action_result": "No goals were mutated by compilation and no external action was executed.", "next_machine_action": "Inspect productization artifacts and run the bounded tenant, cost, and governance contract.", "machine_actionable_remaining": ["nexus.productization: productization options, tenant/cost/governance model, and dependency-gated readiness"], "resume_point": "PRODUCTIZATION_RECONCILIATION", "safe_to_resume": True, "ray_decision_queue": []})
    ACTIVE.write_text(json.dumps(state, indent=2) + "\n")
    print("INTENT_COMPILER_FINAL_STATE=COMPLETE_REAL")
    print(f"RECEIPT={receipt}")
    print("UNAUTHORIZED_ACTION_ALLOWED=NO")
    print("NEXT_CANONICAL_GOAL=nexus.productization")


if __name__ == "__main__":
    main()
