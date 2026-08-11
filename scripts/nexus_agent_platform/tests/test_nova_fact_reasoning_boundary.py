"""Regression tests for Nova's Nexus fact/reasoning boundary."""

import json
from unittest.mock import patch

from nexus_agent_platform.adapters.state_adapter import AgentState
from nexus_agent_platform.agents.nova import (
    _capability_gate,
    _format_planner_context,
    _validate_against_capability,
)
from nexus_agent_platform.capabilities.nexus_query_planner import (
    execute_plan,
    plan_query,
    register_executor,
)


PROCESS_DATA = {
    "status": "success",
    "source_type": "config_file",
    "freshness": "current_commit",
    "data": {
        "total": 19,
        "configuration_counts": {"enabled": 17, "disabled": 2},
        "mode_counts": {
            "ACTIVE_INTERNAL": 10,
            "DRY_RUN": 4,
            "TELEGRAM_OPERATOR": 1,
            "SANDBOX_TEST": 1,
            "BLOCKED": 1,
        },
        "runtime_counts": {"simulated": 16, "skipped": 1, "blocked": 2},
        "reconciliation": {
            "configuration": True,
            "execution_mode": True,
            "runtime_state": True,
            "all_reconciled": True,
        },
        "has_real_execution": False,
        "all_simulated_or_skipped": False,
        "processes": [
            {
                "process_id": "research_intelligence",
                "name": "Research Intelligence",
                "configuration_state": "enabled",
                "execution_mode": "DRY_RUN",
                "runtime_state": "simulated",
            },
            {
                "process_id": "creative_quality_loop",
                "name": "Creative Quality Loop",
                "configuration_state": "enabled",
                "execution_mode": "DRY_RUN",
                "runtime_state": "simulated",
            },
            {
                "process_id": "notebooklm_import_status",
                "name": "NotebookLM Import Status",
                "configuration_state": "enabled",
                "execution_mode": "DRY_RUN",
                "runtime_state": "simulated",
            },
            {
                "process_id": "marketing_content_pipeline",
                "name": "Marketing Content Pipeline",
                "configuration_state": "enabled",
                "execution_mode": "DRY_RUN",
                "runtime_state": "simulated",
            },
            {
                "process_id": "telegram_operator",
                "name": "Telegram Operator",
                "configuration_state": "enabled",
                "execution_mode": "TELEGRAM_OPERATOR",
                "runtime_state": "skipped",
            },
            {
                "process_id": "stripe_test_mode_paywall",
                "name": "Stripe Test-Mode Paywall",
                "configuration_state": "disabled",
                "execution_mode": "SANDBOX_TEST",
                "runtime_state": "blocked",
            },
            {
                "process_id": "client_portal_paywall_access",
                "name": "Client Portal Paywall Access",
                "configuration_state": "disabled",
                "execution_mode": "BLOCKED",
                "runtime_state": "blocked",
            },
        ],
    },
}


def _executor(capability):
    assert capability == "get_process_registry"
    return PROCESS_DATA


def _model_return(plan):
    def _call(_messages):
        return {
            "content": json.dumps(plan),
            "model": "openai/gpt-4o-mini",
            "provider": "test",
        }

    return _call


def setup_function():
    register_executor(_executor)


def teardown_function():
    register_executor(None)


def test_projection_preserves_independent_process_dimensions():
    plan = plan_query(
        "Which of those are skipped?",
        model_call_fn=_model_return({
            "domain": "processes",
            "operation": "filter",
            "conditions": [
                {"field": "runtime_state", "operator": "eq", "value": "skipped"}
            ],
            "projection": ["process_id", "name", "runtime_state"],
            "aggregate": None,
            "ambiguity": None,
            "source_requirement": "structural",
            "reason": "Filter skipped processes.",
        }),
    )
    result = execute_plan(plan)
    row = result["data"]["processes"][0]

    assert row["name"] == "Telegram Operator"
    assert row["configuration_state"] == "enabled"
    assert row["execution_mode"] == "TELEGRAM_OPERATOR"
    assert row["runtime_state"] == "skipped"


def test_intersection_enabled_and_skipped_returns_telegram_operator():
    result = execute_plan({
        "domain": "processes",
        "operation": "filter",
        "conditions": [
            {"field": "configuration_state", "operator": "eq", "value": "enabled"},
            {"field": "runtime_state", "operator": "eq", "value": "skipped"},
        ],
        "projection": ["process_id", "name"],
        "source_requirement": "structural",
    })

    rows = result["data"]["processes"]
    assert [row["name"] for row in rows] == ["Telegram Operator"]
    assert rows[0]["configuration_state"] == "enabled"
    assert rows[0]["runtime_state"] == "skipped"


def test_intersection_enabled_and_dry_run_preserves_four_rows():
    result = execute_plan({
        "domain": "processes",
        "operation": "filter",
        "conditions": [
            {"field": "configuration_state", "operator": "eq", "value": "enabled"},
            {"field": "execution_mode", "operator": "eq", "value": "DRY_RUN"},
        ],
        "projection": ["process_id", "name"],
        "source_requirement": "structural",
    })

    assert [row["name"] for row in result["data"]["processes"]] == [
        "Research Intelligence",
        "Creative Quality Loop",
        "NotebookLM Import Status",
        "Marketing Content Pipeline",
    ]


def test_overlap_categories_do_not_remove_enabled_skipped_process():
    data = PROCESS_DATA["data"]
    enabled = [
        row for row in data["processes"]
        if row["configuration_state"] == "enabled"
    ]
    skipped = [
        row for row in data["processes"]
        if row["runtime_state"] == "skipped"
    ]
    blocked = [
        row for row in data["processes"]
        if row["runtime_state"] == "blocked"
    ]

    assert data["configuration_counts"]["enabled"] == 17
    assert any(row["name"] == "Telegram Operator" for row in enabled)
    assert [row["name"] for row in skipped] == ["Telegram Operator"]
    assert [row["name"] for row in blocked] == [
        "Stripe Test-Mode Paywall",
        "Client Portal Paywall Access",
    ]


def test_planner_context_exposes_raw_independent_fields():
    capability_result = {
        "tool": "nexus_query_planner",
        "query_type": "processes",
        "status": "success",
        "data": PROCESS_DATA["data"],
        "coverage": {
            "structural": True,
            "operational_state": False,
            "execution_telemetry": False,
        },
        "provenance": {"source_type": "config_file", "freshness": "current_commit"},
        "plan": {"domain": "processes", "operation": "filter"},
        "planner_mode": "model",
        "planner_model": "openai/gpt-4o-mini",
        "planner_provider": "test",
        "source_requirement": "structural",
        "total_count": 19,
        "returned_count": 7,
        "truncated": True,
        "capability_selected": "get_process_registry",
    }

    context = _format_planner_context(capability_result)

    assert "Process records (independent dimensions; categories may overlap):" in context
    assert "Telegram Operator:" in context
    assert "configuration_state: enabled" in context
    assert "execution_mode: TELEGRAM_OPERATOR" in context
    assert "runtime_state: skipped" in context


def test_telemetry_guard_does_not_replace_structural_process_answer():
    capability_result = {
        "tool": "nexus_query_planner",
        "query_type": "processes",
        "status": "success",
        "coverage": {
            "structural": True,
            "operational_state": False,
            "execution_telemetry": False,
        },
        "source_requirement": "structural",
        "plan": {"domain": "processes", "operation": "filter"},
        "data": PROCESS_DATA["data"],
    }

    err = _validate_against_capability(
        "Telegram Operator is enabled and has runtime_state skipped.",
        capability_result,
    )
    assert err is None


def test_telemetry_guard_still_blocks_execution_proof_claims():
    capability_result = {
        "tool": "nexus_query_planner",
        "query_type": "recent_activity",
        "status": "success",
        "coverage": {
            "structural": False,
            "operational_state": False,
            "execution_telemetry": False,
        },
        "source_requirement": "execution_telemetry",
        "plan": {"domain": "recent_activity", "operation": "overview"},
        "data": {"has_any_real_execution": False},
    }

    err = _validate_against_capability("A real execution happened today.", capability_result)
    assert err == "planner_telemetry_contradiction"


def test_generic_reasoning_question_does_not_receive_nexus_context():
    state = AgentState(
        user_message=(
            "If I have no evidence that a machine ran today, can I conclude "
            "it definitely did not run?"
        ),
        metadata={"chat_id": 424242},
    )
    with patch(
        "nexus_agent_platform.agents.nova._planner_model_call",
        _model_return({"domain": "none", "reason": "Generic reasoning question."}),
    ):
        result = _capability_gate(state)

    assert result.metadata["capability_gate"]["decision"] == "no_capability"
    assert result.metadata["capability_result"] is None
