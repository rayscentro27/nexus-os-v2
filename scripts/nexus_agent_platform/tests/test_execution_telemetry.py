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

