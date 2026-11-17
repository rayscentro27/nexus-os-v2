import json

import pytest

from scripts.nexus_agent_platform import supabase_egress_guard as guard


def test_static_cache_hits_and_invalidates(monkeypatch):
    guard.invalidate_cache()
    calls = []
    load = lambda: calls.append(1) or {"enabled": True}
    assert guard.cached_static("settings:test", load, ttl_seconds=20) == {"enabled": True}
    assert guard.cached_static("settings:test", load, ttl_seconds=20) == {"enabled": True}
    assert len(calls) == 1
    guard.invalidate_cache("settings:")
    guard.cached_static("settings:test", load, ttl_seconds=20)
    assert len(calls) == 2
    with pytest.raises(ValueError, match="NOT_ALLOWLISTED"):
        guard.cached_static("client_pii:test", load)


def test_safe_mode_state_is_persisted_without_sensitive_data(tmp_path, monkeypatch):
    state = tmp_path / "safe-mode.json"
    monkeypatch.setattr(guard, "SAFE_MODE_STATE", state)
    result = guard.set_safe_mode(True, reason="Systems egress response")
    assert guard.safe_mode_enabled() is True
    stored = json.loads(state.read_text())
    assert stored["enabled"] is True
    assert "token" not in json.dumps(stored).lower()
    assert result["reason"] == "Systems egress response"
    guard.set_safe_mode(False)
    assert guard.safe_mode_enabled() is False


def test_request_telemetry_counts_http_error_classes(tmp_path, monkeypatch):
    state = tmp_path / "egress.json"
    monkeypatch.setattr(guard, "STATE", state)
    guard.record_request("GET", "system_health?select=status&limit=1", 200, 24, trace=False)
    guard.record_request("GET", "system_health?select=status&limit=1", 522, 0, trace=False)
    guard.record_request("GET", "system_health?select=status&limit=1", 503, 12, trace=False)
    stored = json.loads(state.read_text())
    assert stored["status_counts"] == {"2xx": 1, "5xx": 2}
    assert stored["http_522_count"] == 1
    assert stored["endpoints"]["system_health"]["max_response_bytes"] == 24


def test_large_proactive_memory_reads_are_bounded_and_explicit_hydration_is_allowed():
    with pytest.raises(guard.LargeControlPlaneQueryBlocked):
        guard.preflight_request("GET", "research_proactive_memory?select=payload&order=recorded_at.desc&limit=2000")
    with pytest.raises(guard.LargeControlPlaneQueryBlocked):
        guard.preflight_request("GET", "research_proactive_memory?select=payload&limit=100")
    guard.preflight_request("GET", "research_proactive_memory?memory_id=eq.mem_1&select=memory_id%2Cpayload&limit=1")
    guard.preflight_request("GET", "research_proactive_memory?memory_kind=in.%28RESEARCH_CASE%2CPROACTIVE_RESEARCH_CASE%29&select=payload&limit=100")


def test_large_control_plane_response_is_persisted_and_warned(tmp_path, monkeypatch):
    state = tmp_path / "egress.json"
    incidents = tmp_path / "systems.jsonl"
    monkeypatch.setattr(guard, "STATE", state)
    monkeypatch.setattr(guard, "SYSTEMS_INCIDENTS", incidents)
    guard.record_request("GET", "research_proactive_memory?select=memory_id&limit=1", 200, 300_000, trace=False)
    stored = json.loads(state.read_text())
    assert stored["large_control_plane_response_count"] == 1
    assert stored["largest_control_plane_response_bytes"] == 300_000
    incident = json.loads(incidents.read_text().splitlines()[0])
    assert incident["component"] == "SUPABASE_LARGE_CONTROL_RESPONSE"
    assert incident["response_bytes"] == 300_000


def test_proactive_memory_telemetry_keeps_query_shape_without_filter_values(tmp_path, monkeypatch):
    monkeypatch.setattr(guard, "STATE", tmp_path / "egress.json")
    path = ("research_proactive_memory?memory_id=eq.private-case-value&"
            "select=memory_id%2Ccase_id%2Cstatus&limit=1")
    guard.record_request("GET", path, 200, 64, rows=1, trace=False)
    stored = json.loads((tmp_path / "egress.json").read_text())
    shape = stored["endpoints"]["research_proactive_memory"]["last_query_shape"]
    assert shape["selected_fields"] == ["memory_id", "case_id", "status"]
    assert shape["filters"] == [{"field": "memory_id", "operator": "eq"}]
    assert shape["limit"] == "1"
    assert "private-case-value" not in json.dumps(shape)


def test_research_sources_budget_is_wake_scoped_and_blocks_before_network(tmp_path, monkeypatch):
    # The guard imports the canonical top-level package under scripts/ on
    # PYTHONPATH. Patch that same module object so trace output stays in tmp.
    from nexus_agent_platform import research_sources_trace as trace
    monkeypatch.setattr(guard, "WAKE_BUDGET_STATE", tmp_path / "wake-budget.json")
    monkeypatch.setattr(guard, "SYSTEMS_INCIDENTS", tmp_path / "systems.jsonl")
    monkeypatch.setattr(trace, "TRACE_PATH", tmp_path / "research_sources_trace.jsonl")
    monkeypatch.setenv("NEXUS_WAKE_ID", "wake_budget_fixture")
    monkeypatch.setenv("NEXUS_RESEARCH_SOURCES_TRACE", "1")
    for _ in range(guard.MAX_RESEARCH_SOURCES_CALLS_FULL_WAKE):
        guard.preflight_request("GET", "research_sources?select=id&limit=1")
    with pytest.raises(guard.ResearchSourcesBurstExceeded):
        guard.preflight_request("GET", "research_sources?select=id&limit=1")
    stored = json.loads((tmp_path / "wake-budget.json").read_text())
    entry = stored["wakes"]["wake_budget_fixture"]
    assert entry["calls"] == guard.MAX_RESEARCH_SOURCES_CALLS_FULL_WAKE
    assert entry["blocked"] == 1
    assert sum(entry["callers"].values()) == guard.MAX_RESEARCH_SOURCES_CALLS_FULL_WAKE
    incident = json.loads((tmp_path / "systems.jsonl").read_text().splitlines()[0])
    assert incident["wake_id"] == "wake_budget_fixture"
    assert incident["next_workflow"] == "SUPABASE_EGRESS_BURST_RECOVERY"
    assert len((tmp_path / "research_sources_trace.jsonl").read_text().splitlines()) == guard.MAX_RESEARCH_SOURCES_CALLS_FULL_WAKE + 1
    monkeypatch.setenv("NEXUS_WAKE_ID", "wake_budget_next")
    guard.preflight_request("GET", "research_sources?select=id&limit=1")
    next_state = json.loads((tmp_path / "wake-budget.json").read_text())
    assert next_state["wakes"]["wake_budget_next"]["calls"] == 1
