"""Regression coverage for nonterminal Company Case routing contracts.

These tests exercise pure routing/validation functions. They do not create
synthetic Company Case rows or write to Supabase.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from nexus_agent_platform.company_workflow import (  # noqa: E402
    build_handoff,
    governed_case_status,
    nonterminal_next_action,
    validate_actionable_handoff,
)
from nexus_agent_platform.project_stop_policy import guard_parent_state_write  # noqa: E402


SCENARIOS = {
    "INSUFFICIENT_DATA": ("RESEARCH", "Acquire missing evidence for the active case."),
    "PROVIDER_FAILURE": ("SYSTEMS", "Classify provider failure and attempt safe recovery."),
    "NEGATIVE_TEST_RESULT": ("TRADING", "Trading: interpret the backtest result and select a controlled next test."),
    "MISSING_CREDENTIAL": ("SYSTEMS", "Resolve credential availability without exposing values."),
    "DEPARTMENT_TASK_COMPLETE": ("RESEARCH", "Re-evaluate case contract and route remaining work."),
    "CAPABILITY_UNAVAILABLE": ("SYSTEMS", "Inspect existing capability and identify an alternative."),
    "BUSINESS_MODEL_WEAK": ("RESEARCH", "Preserve useful components and evaluate alternatives."),
    "SOURCE_MISSING": ("RESEARCH", "Acquire and verify the missing source."),
}


def test_nonterminal_scenarios_always_route_action():
    for outcome, (expected_owner, action) in SCENARIOS.items():
        result = nonterminal_next_action(outcome, action)
        assert result["parent_case_remains_active"] == "true"
        assert result["next_owner"] == expected_owner
        assert result["next_action"] == action
        packet = build_handoff(
            case={"case_id": "existing-case", "objective": "Existing objective",
                  "findings": [{"summary": "Prior evidence"}], "open_questions": [outcome]},
            request_id=f"directive-{outcome.lower()}", to_department=result["next_owner"],
            work=result["next_action"], why=f"Continue after {outcome.lower()}.",
            return_to="RESEARCH", expected_output="Evidence-backed department result",
        )
        validation = validate_actionable_handoff(packet)
        assert validation["valid"] is True
        assert validation["actionable_item_count"] >= 1
        assert packet["next_owner"] == expected_owner


def test_legacy_ai_terminal_labels_normalize_to_replanning_even_if_actor_claims_ray():
    for state in ("FAILED", "FAILED_FINAL", "REJECTED", "REJECTED_WITH_EVIDENCE",
                  "CANCELLED", "TERMINATED", "ABANDONED", "PARKED", "COMPLETED"):
        assert governed_case_status(state, actor="RAY") == "REPLANNING"


def test_handoff_without_action_is_rejected():
    packet = {"summary": "A result", "supporting_data": [{"source": "case"}],
              "next_owner": "RESEARCH", "expected_output": "Evidence"}
    validation = validate_actionable_handoff(packet)
    assert validation["valid"] is False
    assert "actionable_items" in validation["missing"]


def test_unauthorized_parent_stop_write_preserves_active_objective_and_routes_replan():
    row, receipt = guard_parent_state_write(
        collection="goals",
        proposed={"goal_id": "existing-goal", "status": "FAILED", "actor": "NEXUS"},
        prior={"goal_id": "existing-goal", "status": "ACTIVE"},
    )
    assert receipt and receipt["denied"] is True
    assert row["status"] == "ACTIVE"
    assert row["execution_state"] == "REPLANNING"
    assert row["continue_project"] is True
    assert row["requires_ray"] is False
    assert row["next_owner"] == "RESEARCH"
