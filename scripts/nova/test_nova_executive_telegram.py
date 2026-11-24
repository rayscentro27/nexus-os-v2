import json


def test_owner_turn_provider_context_uses_persisted_mission_and_restores_environment(monkeypatch):
    import nova_telegram_worker as worker

    monkeypatch.setenv("NEXUS_DURABLE_JOB_ID", "outer-job")
    monkeypatch.delenv("NEXUS_CORRELATION_ID", raising=False)
    monkeypatch.setenv("NEXUS_DEPARTMENT", "OUTER")
    mission = {"mission_id": "nova_20261011T123000_42", "correlation_id": "tg-42-abc"}
    previous = worker._set_owner_turn_governance_context(mission)
    assert worker.os.environ["NEXUS_DURABLE_JOB_ID"] == mission["mission_id"]
    assert worker.os.environ["NEXUS_CORRELATION_ID"] == mission["correlation_id"]
    assert worker.os.environ["NEXUS_DEPARTMENT"] == "NOVA"
    worker._restore_owner_turn_governance_context(previous)
    assert worker.os.environ["NEXUS_DURABLE_JOB_ID"] == "outer-job"
    assert "NEXUS_CORRELATION_ID" not in worker.os.environ
    assert worker.os.environ["NEXUS_DEPARTMENT"] == "OUTER"


def test_proactive_ray_gate_event_uses_executive_status(monkeypatch):
    import proactive_communications as proactive

    status = {
        "human_gates": [{"department": "clyde"}, {"department": "creative"}],
        "departments": {
            "clyde": {"next_action": "Review lender gate", "current_task": "Funding readiness"},
            "creative": {"next_action": "Approve design", "current_task": "Admin command center"},
        },
    }
    monkeypatch.setattr(proactive, "build_executive_status", lambda: status)
    monkeypatch.setattr(proactive, "_read", lambda path, default: default)
    events = proactive.collect_events()
    gate = next(item for item in events if item.get("kind") == "RAY_REQUIRED")
    assert "Clyde: Review lender gate" in gate["required_action"]
    assert "Creative: Approve design" in gate["required_action"]
    assert gate["source"] == "executive_status"


def test_executive_status_answer_does_not_use_legacy_grounder(monkeypatch):
    from nexus_agent_platform.bridge import oracle_hermes_cli

    monkeypatch.setattr(oracle_hermes_cli, "ORACLE_KEY", "/missing/oracle/key")
    result = oracle_hermes_cli.run_oracle_hermes("What is Nexus doing right now?", "telegram-grounding-test")
    assert result.provider == "nexus"
    assert result.model == "executive_status"
    assert "Research: has work queued" in result.response
