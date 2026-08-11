from __future__ import annotations

from datetime import datetime, timedelta, timezone


def test_event_schema_writer_reader_and_redaction(monkeypatch, tmp_path):
    store = tmp_path / "events.jsonl"
    monkeypatch.setenv("NEXUS_EXECUTION_TELEMETRY_PATH", str(store))

    from nexus_agent_platform.runtime.execution_telemetry import emit_event, read_events

    event = emit_event(
        process_id="system_health",
        process_name="System Health Check",
        worker_id="pytest",
        agent_id="tests",
        execution_type="system_health_check",
        event_type="started",
        status="running",
        source="test",
        metadata={"token": "123456789:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA", "safe": "ok"},
    )

    assert event["source_type"] == "verified_execution_telemetry"
    assert store.exists()
    assert oct(store.stat().st_mode & 0o777) == "0o600"

    loaded = read_events()
    assert len(loaded) == 1
    assert loaded[0]["metadata"]["token"] == "REDACTED"
    assert loaded[0]["metadata"]["safe"] == "ok"


def test_reducer_completed_failed_and_stale(monkeypatch, tmp_path):
    store = tmp_path / "events.jsonl"
    monkeypatch.setenv("NEXUS_EXECUTION_TELEMETRY_PATH", str(store))

    from nexus_agent_platform.runtime.execution_telemetry import append_event, build_event, query_runtime_telemetry

    now = datetime.now(timezone.utc)
    started = (now - timedelta(minutes=30)).isoformat()
    append_event(build_event(
        process_id="system_health",
        event_type="started",
        status="running",
        run_id="run_complete",
        worker_id="pytest",
        execution_type="system_health_check",
        source="test",
        started_at=started,
        event_at=started,
    ))
    append_event(build_event(
        process_id="system_health",
        event_type="completed",
        status="completed",
        run_id="run_complete",
        worker_id="pytest",
        execution_type="system_health_check",
        source="test",
        started_at=started,
        completed_at=now.isoformat(),
        event_at=now.isoformat(),
        duration_ms=12,
    ))
    append_event(build_event(
        process_id="work_orders",
        event_type="started",
        status="running",
        run_id="run_stale",
        worker_id="pytest",
        execution_type="bounded_manual_runner",
        source="test",
        started_at=started,
        event_at=started,
    ))

    result = query_runtime_telemetry(operation="overview", window="all")
    assert result["summary"]["run_count"] == 2
    assert result["summary"]["completed_count"] == 1
    assert result["summary"]["stale_count"] == 1
    stale = [r for r in result["runs"] if r["run_id"] == "run_stale"][0]
    assert stale["status"] == "stale"
    assert stale["current_state"] == "unknown"


def test_runtime_capability_and_planner_execution(monkeypatch, tmp_path):
    store = tmp_path / "events.jsonl"
    monkeypatch.setenv("NEXUS_EXECUTION_TELEMETRY_PATH", str(store))

    from nexus_agent_platform.capabilities.nexus_query_planner import execute_plan, register_executor, validate_plan
    from nexus_agent_platform.capabilities.shared import execute_shared_capability
    from nexus_agent_platform.runtime.execution_telemetry import emit_event

    emit_event(
        process_id="telegram_operator",
        process_name="Telegram Operator",
        worker_id="nova_telegram_worker",
        agent_id="hermes_nova",
        execution_type="worker_poll",
        event_type="started",
        status="running",
        run_id="run_poll",
        source="test",
    )
    emit_event(
        process_id="telegram_operator",
        process_name="Telegram Operator",
        worker_id="nova_telegram_worker",
        agent_id="hermes_nova",
        execution_type="worker_poll",
        event_type="completed",
        status="completed",
        run_id="run_poll",
        source="test",
        duration_ms=1,
    )

    capability = execute_shared_capability("hermes_nova", "get_recent_runs", {"limit": 10})
    assert capability["status"] == "success"
    assert capability["source_type"] == "verified_execution_telemetry"
    assert capability["data"]["summary"]["completed_count"] == 1

    def executor(name, args=None):
        return execute_shared_capability("hermes_nova", name, args or {})

    register_executor(executor)
    try:
        plan = validate_plan({
            "domain": "runtime_execution",
            "operation": "filter",
            "conditions": [{"field": "last_terminal_status", "operator": "eq", "value": "completed"}],
            "projection": [],
            "aggregate": None,
            "window": "all",
            "ambiguity": None,
            "source_requirement": "execution_telemetry",
            "reason": "completed runs",
        })
        result = execute_plan(plan)
    finally:
        register_executor(None)

    assert result["status"] == "success"
    assert result["coverage"]["execution_telemetry"] is True
    assert result["capability_selected"] == "get_runtime_execution_summary"
    assert result["data"]["returned_count"] == 1


def test_partial_line_is_tolerated(monkeypatch, tmp_path):
    store = tmp_path / "events.jsonl"
    monkeypatch.setenv("NEXUS_EXECUTION_TELEMETRY_PATH", str(store))

    from nexus_agent_platform.runtime.execution_telemetry import emit_event, read_events

    emit_event(
        process_id="system_health",
        worker_id="pytest",
        execution_type="system_health_check",
        event_type="started",
        status="running",
        source="test",
    )
    with store.open("a", encoding="utf-8") as fh:
        fh.write("{partial")

    assert len(read_events()) == 1


def test_stage_execution_records_child_run(monkeypatch, tmp_path):
    store = tmp_path / "events.jsonl"
    monkeypatch.setenv("NEXUS_EXECUTION_TELEMETRY_PATH", str(store))

    from nexus_agent_platform.runtime.execution_telemetry import (
        execution_run,
        read_events,
        stage_execution,
        telemetry_context,
    )

    with execution_run(
        process_id="telegram_operator",
        worker_id="pytest",
        agent_id="hermes_nova",
        execution_type="telegram_update_run",
        source="test",
        metadata={"update_id": 590356972, "raw_message": "do not store"},
    ) as parent_run:
        with telemetry_context(parent_run_id=parent_run, metadata={"update_id": 590356972}):
            with stage_execution(stage="planner", source="test", metadata={"model": "test-model"}):
                pass

    events = read_events()
    stage_events = [e for e in events if e["execution_type"] == "stage:planner"]
    assert len(stage_events) == 2
    assert {e["event_type"] for e in stage_events} == {"started", "completed"}
    assert all(e["parent_run_id"] == parent_run for e in stage_events)
    assert all(e["metadata"]["update_id"] == 590356972 for e in stage_events)
    assert all(e["metadata"]["stage"] == "planner" for e in stage_events)


def test_stage_execution_noops_without_parent(monkeypatch, tmp_path):
    store = tmp_path / "events.jsonl"
    monkeypatch.setenv("NEXUS_EXECUTION_TELEMETRY_PATH", str(store))

    from nexus_agent_platform.runtime.execution_telemetry import read_events, stage_execution

    with stage_execution(stage="generation", source="test"):
        pass

    assert read_events() == []


def test_generation_timeout_uses_fallback_without_regen(monkeypatch):
    from nexus_agent_platform.adapters.state_adapter import AgentState
    from nexus_agent_platform.agents import nova

    calls = {"count": 0}

    async def timeout_model(messages, chat_id, purpose="final_generation"):
        calls["count"] += 1
        raise TimeoutError("provider timed out")

    monkeypatch.setattr(nova, "_call_model", timeout_model)

    state = AgentState(
        agent_id=nova.AGENT_ID,
        mission_id="pytest",
        user_message="How are you?",
        metadata={"model_messages": [{"role": "user", "content": "How are you?"}]},
    )

    generated = nova._generate_response(state)
    assert generated.assistant_response == ""
    assert generated.metadata["model_error_type"] == "TimeoutError"

    validated = nova._validate_output(generated)
    assert validated.metadata["fallback_used"] is True
    assert validated.metadata["validation_regen"] is False
    assert calls["count"] == 1


def test_runtime_count_contradiction_rejected_offline():
    from nexus_agent_platform.agents.nova import _validate_against_capability

    result = {
        "tool": "nexus_query_planner",
        "query_type": "runtime_execution",
        "status": "success",
        "coverage": {"execution_telemetry": True},
        "plan": {
            "domain": "runtime_execution",
            "operation": "overview",
            "source_requirement": "execution_telemetry",
        },
        "data": {
            "coverage": {"coverage_status": "partial"},
            "summary": {
                "active_count": 1,
                "completed_count": 5,
                "failed_count": 0,
                "skipped_count": 0,
                "stale_count": 0,
            },
            "runs": [],
        },
    }

    err = _validate_against_capability("1 currently running and 4 completed.", result)
    assert err == "runtime_count_contradiction"


def test_telegram_send_uses_timeout_and_single_retry(monkeypatch):
    import importlib.util
    from pathlib import Path

    worker_path = Path(__file__).resolve().parents[2] / "nova" / "nova_telegram_worker.py"
    spec = importlib.util.spec_from_file_location("nova_telegram_worker_test", worker_path)
    worker = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(worker)

    calls = []

    def fake_tg_api(method, params=None, token=None, timeout=20):
        calls.append({"method": method, "timeout": timeout})
        if len(calls) == 1:
            return None
        return {"ok": True, "result": {"message_id": 123}}

    monkeypatch.setattr(worker, "_tg_api", fake_tg_api)
    monkeypatch.setattr(worker, "_log_error", lambda msg: None)

    ids = worker.tg_send_message(42, "hello", token="test-token", timeout=3)

    assert ids == [123]
    assert len(calls) == 2
    assert all(call["timeout"] == 3 for call in calls)
