from __future__ import annotations

from nexus_agent_platform.governed import persistence
from nexus_agent_platform.project_advancement import advancement_metrics, consume_trading_test


def test_trading_test_handoff_is_consumed_with_review_and_dependency(tmp_path, monkeypatch):
    monkeypatch.setenv("NEXUS_GOVERNED_DATA_DIR", str(tmp_path))
    handoff_id = "handoff-real-shaped"
    persistence.append_record("research_v2_handoffs", {
        "handoff_id": handoff_id,
        "status": "RETURNED",
        "alpha_decision": "TEST",
        "department_target": "TRADING",
        "finding_id": "trading-finding",
        "request_id": "trading-request",
        "source_refs": ["https://example.test/source"],
        "external_action_allowed": False,
    })
    result = consume_trading_test(handoff_id)
    assert result["work_order"]["owner_specialist"] == "TRADING_ENGINE"
    assert result["output"]["status"] == "BLOCKED_DEPENDENCY"
    assert result["review"]["status"] == "REVIEWED"
    assert result["next_action"]["owner"] == "RESEARCH"
    assert result["project_state"] == "WAITING_DEPENDENCY"
    assert result["output"]["live_trading"] is False
    assert len(persistence.read_records("work_orders")) == 4
    metrics = advancement_metrics()
    assert metrics["work_orders_created"] == 1
    assert metrics["work_orders_claimed"] == 1
    assert metrics["work_orders_completed"] == 1
    assert metrics["deterministic_executions"] == 1
    assert metrics["outputs_reviewed"] == 1
    assert metrics["project_state_transitions"] == 1


def test_trading_consumption_is_idempotent(tmp_path, monkeypatch):
    monkeypatch.setenv("NEXUS_GOVERNED_DATA_DIR", str(tmp_path))
    handoff_id = "handoff-idempotent"
    persistence.append_record("research_v2_handoffs", {
        "handoff_id": handoff_id, "status": "RETURNED", "alpha_decision": "TEST",
        "department_target": "TRADING", "finding_id": "finding", "request_id": "request",
    })
    first = consume_trading_test(handoff_id)
    second = consume_trading_test(handoff_id)
    assert second["deduplicated"] is True
    assert second["work_order"]["work_order_id"] == first["work_order"]["work_order_id"]
    assert len(persistence.read_records("work_orders")) == 4
