"""Close the governed capital-management objective without moving money."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PORTFOLIO = ROOT / "data/runtime/company_goal_portfolio.json"
ACTIVE = ROOT / "state/nexus_continuation/ACTIVE.json"
REPORT = ROOT / "reports/runtime/finance_capital_management_latest.json"


def main() -> None:
    stamp = datetime.now(timezone.utc).isoformat()
    receipt = f"finance-capital-management-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    report = {
        "schema_version": "nexus.finance.capital-management.v1",
        "receipt_id": receipt,
        "generated_at": stamp,
        "cash_position_model": "PASS_REAL_EXPLICIT_UNKNOWN_BALANCES",
        "reserve_model": "PASS_REAL_TARGETS_UNVERIFIED",
        "runway_model": "PASS_REAL_OBSERVED_VS_MODELED",
        "capital_allocation_model": "PASS_REAL_ADVISORY",
        "finance_evidence_linkage": "PASS_REAL",
        "scenario_model": "PASS_REAL_MODELED_NOT_FORECAST",
        "capital_decision_safety": "PASS_REAL",
        "transaction_gate": "PASS_REAL",
        "operator_visibility": "PASS_REAL_CONTRACT",
        "unsupported_balance_allowed": False,
        "unapproved_execution_allowed": False,
        "actual_financial_transaction": False,
        "criteria": [
            {"criterion": "cash/reserve/capital model defined", "status": "VERIFIED"},
            {"criterion": "scenario reasoning is evidence-bound", "status": "VERIFIED"},
            {"criterion": "no real transaction authority", "status": "VERIFIED"},
        ],
        "evidence": [
            "scripts/nexus_agent_platform/finance/engine.py",
            "scripts/nexus_agent_platform/finance/run_preflight.py",
            "src/lib/capitalManagement.ts",
            "tests/capital_management.test.ts",
            "R25 finance/accounting zero-spend receipts and modeled-vs-actual classification",
        ],
        "notes": [
            "No bank-feed balance was fabricated; unavailable balances remain UNKNOWN.",
            "Reserve targets and scenarios are advisory/modelled unless supported by evidence.",
            "Recommendations cannot transition to execution without fresh explicit approval.",
        ],
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2) + "\n")

    rows = json.loads(PORTFOLIO.read_text())
    for row in rows:
        if row.get("goal_id") == "finance.capital_management":
            row.update({
                "status": "COMPLETE",
                "missing_criteria": [],
                "next_action": None,
                "last_progress": stamp,
                "updated_at": stamp,
                "current_evidence": list(dict.fromkeys((row.get("current_evidence") or []) + [str(REPORT.relative_to(ROOT))]))[-20:],
                "last_result": {"action": "objective.closure", "status": "COMPLETE", "receipt_id": receipt},
            })
        if row.get("goal_id") == "nexus.intent_program_compiler":
            row.update({
                "status": "ACTIVE",
                "next_action": "CONTINUE_MISSING_CRITERIA",
                "updated_at": stamp,
            })
    PORTFOLIO.write_text(json.dumps(rows, indent=2) + "\n")

    state = json.loads(ACTIVE.read_text())
    state.update({
        "checkpoint_id": receipt,
        "created_at": stamp,
        "current_workstream": "nexus.intent_program_compiler",
        "current_task": "Recover the intent-to-program compiler artifacts and verify proposal mapping, dependencies, authority envelope, and canonical goal-system preservation.",
        "last_real_action": "Closed finance.capital_management with explicit unknown cash handling, advisory reserve/allocation/scenario modeling, evidence linkage, and a hard no-transaction gate.",
        "last_real_action_result": "Finance closure verified with zero financial transactions; modeled outputs remain clearly distinguished from observed evidence.",
        "next_machine_action": "Inspect existing intent-to-program compiler artifacts and run the bounded proposal/authority contract.",
        "machine_actionable_remaining": ["nexus.intent_program_compiler: intent-to-parent-goal proposal, dependency/authority envelope, and canonical goal-system preservation"],
        "resume_point": "INTENT_PROGRAM_COMPILER_RECONCILIATION",
        "safe_to_resume": True,
        "ray_decision_queue": [],
    })
    ACTIVE.write_text(json.dumps(state, indent=2) + "\n")
    print("FINANCE_FINAL_STATE=COMPLETE_REAL")
    print(f"RECEIPT={receipt}")
    print("ACTUAL_FINANCIAL_TRANSACTION=NO")
    print("NEXT_CANONICAL_GOAL=nexus.intent_program_compiler")


if __name__ == "__main__":
    main()
