from types import SimpleNamespace

from nexus_agent_platform.governed import persistence
from nexus_agent_platform.systems_consumer import (
    claim_and_execute_systems,
    create_systems_work_order,
    systems_metrics,
)


def _handoff(decision="RESEARCH_MORE"):
    return {
        "handoff_id": "systems-handoff-real-shaped",
        "status": "RETURNED",
        "alpha_decision": decision,
        "department_target": "SYSTEMS",
        "alpha_receipt_id": "alpha-receipt",
        "finding_id": "systems-finding",
        "objective_id": "systems-project",
        "question": "Verify Needle and Jev for a safe isolated Nexus benchmark.",
        "source_refs": ["https://github.com/search?q=needle+jev&type=repositories"],
        "external_action_allowed": False,
    }


def _fake_runner(prompt, session_id, **kwargs):
    return SimpleNamespace(
        response='{"candidate_identity_status":"AMBIGUOUS","unknowns":["license"],"test_host":"ORACLE","test_host_reason":"isolated Linux host","resource_requirements":"UNKNOWN","isolation_method":"temporary container","rollback_method":"remove temporary container","production_risk":"LOW","disposition":"NEEDS_MORE_EVIDENCE","next_action":"Research official identity and license."}',
        status="SUCCEEDED",
        provider="openrouter",
        model="openai/gpt-4o-mini",
        runtime_host="ORACLE",
        hermes_version="0.20.6",
        latency_ms=12.0,
    )


def test_systems_research_more_assessment_claims_real_lineage(tmp_path, monkeypatch):
    monkeypatch.setenv("NEXUS_GOVERNED_DATA_DIR", str(tmp_path))
    persistence.append_record("research_v2_handoffs", _handoff())
    result = claim_and_execute_systems("systems-handoff-real-shaped", assessment_only=True, model_runner=_fake_runner)
    assert result["work_order"]["owner_specialist"] == "SYSTEMS_AI_WORKER"
    assert result["artifact"]["model"] == "openai/gpt-4o-mini"
    assert result["artifact"]["runtime_host"] == "ORACLE"
    assert result["artifact"]["disposition"] == "NEEDS_MORE_EVIDENCE"
    assert result["next_action"]["owner"] == "RESEARCH"
    assert result["work_order"]["result"]["output"]["production_touch"] is False
    assert len(persistence.read_records("systems_ai_analyses")) == 1
    assert systems_metrics()["systems_work_claimed"] == 1
    assert systems_metrics()["systems_ai_analyses"] == 1
    assert systems_metrics()["systems_tests_executed"] == 0


def test_systems_test_order_is_deduplicated_and_rejects_wrong_department(tmp_path, monkeypatch):
    monkeypatch.setenv("NEXUS_GOVERNED_DATA_DIR", str(tmp_path))
    handoff = _handoff("TEST")
    persistence.append_record("research_v2_handoffs", handoff)
    first = create_systems_work_order(handoff)
    second = create_systems_work_order(handoff)
    assert first["owner"] == "SYSTEMS_AI_WORKER"
    assert second["deduplicated"] is True
    assert len(persistence.read_records("work_orders")) == 1
    handoff["department_target"] = "TRADING"
    try:
        create_systems_work_order(handoff)
    except ValueError as exc:
        assert str(exc) == "not_systems_handoff"
    else:
        raise AssertionError("wrong department was accepted")
