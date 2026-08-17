from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from nexus_agent_platform.loops.runtime import (
    LoopExecutionError,
    LoopRuntime,
    LoopSpec,
    LoopStateStore,
    opportunity_discovery_loop_spec,
    run_opportunity_discovery_loop,
    run_system_health_loop,
    system_health_loop_spec,
)


def _ledger_lines(path: Path) -> list[dict]:
    if not path.exists():
        return []
    lines = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        if raw.strip():
            lines.append(json.loads(raw))
    return lines


def _runtime(tmp_path: Path) -> tuple[LoopRuntime, Path, Path]:
    state_path = tmp_path / "loop_state.json"
    ledger_path = tmp_path / "loop_ledger.jsonl"
    runtime = LoopRuntime(state_store=LoopStateStore(state_path), ledger_path=ledger_path)
    return runtime, state_path, ledger_path


def _fake_capability_factory(payloads: dict[str, dict], calls: list[tuple[str, str]]):
    def _fake(agent_id: str, capability: str, arguments=None, conversation_id: str = "", trace_id: str = ""):
        calls.append((agent_id, capability))
        payload = payloads.get(capability)
        if payload is None:
            raise AssertionError(f"unexpected capability: {capability}")
        return payload

    return _fake


def test_system_health_loop_second_run_is_zero_token(monkeypatch, tmp_path):
    runtime, state_path, ledger_path = _runtime(tmp_path)
    calls: list[tuple[str, str]] = []
    payloads = {
        "get_system_health": {
            "status": "success",
            "source_type": "live_governed_read",
            "data": {"overall_status": "healthy", "active_services": 7},
        },
        "get_process_registry": {
            "status": "success",
            "source_type": "process_registry",
            "data": {"total": 19},
        },
        "get_runtime_execution_summary": {
            "status": "success",
            "source_type": "verified_execution_telemetry",
            "summary": {"active_count": 1, "failed_count": 0},
        },
        "get_pending_approvals": {
            "status": "success",
            "source_type": "live_governed_read",
            "data": {"count": 2},
        },
    }
    monkeypatch.setattr(
        "nexus_agent_platform.loops.runtime.execute_shared_capability",
        _fake_capability_factory(payloads, calls),
    )

    first = runtime.run(system_health_loop_spec, {"window": "today"})
    second = runtime.run(system_health_loop_spec, {"window": "today"})

    assert first.ai_calls == 0
    assert first.zero_token_execution is True
    assert second.ai_calls == 0
    assert second.zero_token_execution is True
    assert second.estimated_cost == 0.0
    assert second.telemetry_run_id

    ledger = _ledger_lines(ledger_path)
    assert len(ledger) == 2
    assert ledger[-1]["zero_token_execution"] is True
    assert ledger[-1]["ai_used"] is False
    assert state_path.exists()


def test_opportunity_duplicate_input_does_not_trigger_ai(monkeypatch, tmp_path):
    runtime, _, ledger_path = _runtime(tmp_path)
    calls: list[tuple[str, str]] = []
    payloads = {
        "get_opportunities": {
            "status": "success",
            "source_type": "live_governed_read",
            "data": {
                "total": 3,
                "items": [
                    {"id": "opp_1", "title": "Same", "status": "open", "revenue_potential": 500},
                    {"id": "opp_1", "title": "Same", "status": "open", "revenue_potential": 500},
                    {"id": "opp_2", "title": "Same 2", "status": "open", "revenue_potential": 250},
                ],
            },
        },
        "get_recent_research": {
            "status": "success",
            "source_type": "live_governed_read",
            "data": {"runs": {"total": 0, "items": []}, "results": {"total": 0, "items": []}},
        },
        "get_business_model_summary": {
            "status": "success",
            "source_type": "study_snapshot_artifact",
            "offers_count": 9,
            "offers": [],
        },
    }
    monkeypatch.setattr(
        "nexus_agent_platform.loops.runtime.execute_shared_capability",
        _fake_capability_factory(payloads, calls),
    )

    def _ai_call(_payload):
        raise AssertionError("AI should not be called for duplicate low-signal input")

    result = runtime.run(
        opportunity_discovery_loop_spec,
        {"window": "last_24_hours"},
        ai_call=_ai_call,
    )

    assert result.ai_calls == 0
    assert result.zero_token_execution is True
    assert result.result["top_candidates"]
    assert len(result.result["normalized_opportunities"]) == 2
    assert _ledger_lines(ledger_path)[-1]["ai_used"] is False


def test_max_ai_calls_enforced(monkeypatch, tmp_path):
    runtime, _, _ = _runtime(tmp_path)

    def collect(trigger, previous_state):
        return {
            "deterministic_precheck": True,
            "state_version": 1,
            "records": [{"id": "x", "status": "new"}],
            "deterministic_output": {"status": "success", "records": [{"id": "x"}]},
            "material": {"changed": True},
        }

    spec = replace(
        system_health_loop_spec,
        loop_id="max_ai_calls_loop",
        name="Max AI Calls Loop",
        model_tier="T1_CHEAP_AI",
        max_ai_calls=0,
        max_input_tokens=128,
        max_output_tokens=128,
        estimated_token_budget=256,
        cost_ceiling=1.0,
        deterministic_precheck=collect,
        ai_decider=lambda collected, reduced, previous_state: {"use_ai": True, "requested_tier": "T1_CHEAP_AI", "reason": "needed"},
        ai_context_builder=lambda collected, reduced, previous_state: {"brief": "x"},
        memory_projection=lambda result, collected, previous_state: {"result": result},
        verifier=lambda result, collected, previous_state: {"status": "fail", "reason": "force retry"},
    )

    with pytest.raises(LoopExecutionError, match="max_ai_calls"):
        runtime.run(spec, {}, ai_call=lambda payload: {"status": "success", "text": "ok"})


def test_input_token_budget_enforced(tmp_path):
    runtime, _, _ = _runtime(tmp_path)

    def collect(trigger, previous_state):
        return {
            "deterministic_precheck": True,
            "state_version": 1,
            "records": [{"id": "x"}],
            "deterministic_output": {"status": "success"},
            "material": {"changed": True},
        }

    spec = replace(
        opportunity_discovery_loop_spec,
        loop_id="input_budget_loop",
        name="Input Budget Loop",
        max_ai_calls=1,
        max_input_tokens=1,
        max_output_tokens=16,
        estimated_token_budget=32,
        cost_ceiling=1.0,
        deterministic_precheck=collect,
        ai_decider=lambda collected, reduced, previous_state: {"use_ai": True, "requested_tier": "T1_CHEAP_AI", "reason": "needed"},
        ai_context_builder=lambda collected, reduced, previous_state: {"brief": "x" * 100},
        memory_projection=lambda result, collected, previous_state: {"result": result},
        verifier=lambda result, collected, previous_state: {"status": "pass", "reason": "ok"},
    )

    with pytest.raises(LoopExecutionError, match="input token budget"):
        runtime.run(spec, {}, ai_call=lambda payload: {"status": "success", "text": "ok"})


def test_output_token_budget_enforced(tmp_path):
    runtime, _, _ = _runtime(tmp_path)

    def collect(trigger, previous_state):
        return {
            "deterministic_precheck": True,
            "state_version": 1,
            "records": [{"id": "x"}],
            "deterministic_output": {"status": "success"},
            "material": {"changed": True},
        }

    spec = replace(
        opportunity_discovery_loop_spec,
        loop_id="output_budget_loop",
        name="Output Budget Loop",
        max_ai_calls=1,
        max_input_tokens=128,
        max_output_tokens=1,
        estimated_token_budget=32,
        cost_ceiling=1.0,
        deterministic_precheck=collect,
        ai_decider=lambda collected, reduced, previous_state: {"use_ai": True, "requested_tier": "T1_CHEAP_AI", "reason": "needed"},
        ai_context_builder=lambda collected, reduced, previous_state: {"brief": "small"},
        memory_projection=lambda result, collected, previous_state: {"result": result},
        verifier=lambda result, collected, previous_state: {"status": "pass", "reason": "ok"},
    )

    with pytest.raises(LoopExecutionError, match="output token budget"):
        runtime.run(spec, {}, ai_call=lambda payload: {"status": "success", "text": "this is longer than one token"})


def test_premium_escalation_requires_explicit_rule(tmp_path):
    runtime, _, _ = _runtime(tmp_path)

    def collect(trigger, previous_state):
        return {
            "deterministic_precheck": True,
            "state_version": 1,
            "records": [{"id": "x"}],
            "deterministic_output": {"status": "success"},
            "material": {"changed": True},
        }

    spec = replace(
        opportunity_discovery_loop_spec,
        loop_id="premium_loop",
        name="Premium Loop",
        max_ai_calls=1,
        max_input_tokens=128,
        max_output_tokens=128,
        estimated_token_budget=256,
        cost_ceiling=1.0,
        deterministic_precheck=collect,
        ai_decider=lambda collected, reduced, previous_state: {"use_ai": True, "requested_tier": "T3_PREMIUM_AI", "reason": "needs premium"},
        ai_context_builder=lambda collected, reduced, previous_state: {"brief": "small"},
        memory_projection=lambda result, collected, previous_state: {"result": result},
        verifier=lambda result, collected, previous_state: {"status": "pass", "reason": "ok"},
    )

    with pytest.raises(LoopExecutionError, match="premium escalation"):
        runtime.run(spec, {}, ai_call=lambda payload: {"status": "success", "text": "ok"})

    ok = runtime.run(
        spec,
        {},
        ai_call=lambda payload: {"status": "success", "text": "ok"},
        explicit_premium_escalation=True,
    )
    assert ok.ai_used is True
    assert ok.tier3_calls == 1


def test_deterministic_capability_preferred_where_available(monkeypatch, tmp_path):
    runtime, _, ledger_path = _runtime(tmp_path)
    calls: list[tuple[str, str]] = []
    payloads = {
        "get_system_health": {
            "status": "success",
            "source_type": "live_governed_read",
            "data": {"overall_status": "healthy", "active_services": 9},
        },
        "get_process_registry": {
            "status": "success",
            "source_type": "process_registry",
            "data": {"total": 19},
        },
        "get_runtime_execution_summary": {
            "status": "success",
            "source_type": "verified_execution_telemetry",
            "summary": {"active_count": 2, "failed_count": 0},
        },
        "get_pending_approvals": {
            "status": "success",
            "source_type": "live_governed_read",
            "data": {"count": 0},
        },
    }
    monkeypatch.setattr(
        "nexus_agent_platform.loops.runtime.execute_shared_capability",
        _fake_capability_factory(payloads, calls),
    )

    def _ai_call(_payload):
        raise AssertionError("deterministic system health should not invoke AI")

    result = runtime.run(system_health_loop_spec, {"window": "last_24_hours"}, ai_call=_ai_call)
    assert result.ai_used is False
    assert result.zero_token_execution is True
    assert result.result["summary"]["system_status"] == "healthy"
    assert _ledger_lines(ledger_path)[-1]["zero_token_execution"] is True


def test_verifier_stops_unnecessary_iteration(tmp_path):
    runtime, _, _ = _runtime(tmp_path)
    calls: list[int] = []

    def collect(trigger, previous_state):
        return {
            "deterministic_precheck": True,
            "state_version": 1,
            "records": [{"id": "x"}],
            "deterministic_output": {"status": "success"},
            "material": {"changed": True},
        }

    spec = replace(
        opportunity_discovery_loop_spec,
        loop_id="verifier_loop",
        name="Verifier Loop",
        max_ai_calls=3,
        max_input_tokens=128,
        max_output_tokens=128,
        estimated_token_budget=256,
        cost_ceiling=1.0,
        max_retries=2,
        deterministic_precheck=collect,
        ai_decider=lambda collected, reduced, previous_state: {"use_ai": True, "requested_tier": "T1_CHEAP_AI", "reason": "needed"},
        ai_context_builder=lambda collected, reduced, previous_state: {"brief": "small"},
        memory_projection=lambda result, collected, previous_state: {"result": result},
        verifier=lambda result, collected, previous_state: {"status": "pass", "reason": "already good"},
    )

    def ai_call(payload):
        calls.append(1)
        return {"status": "success", "text": "ok"}

    result = runtime.run(spec, {}, ai_call=ai_call)
    assert result.ai_used is True
    assert len(calls) == 1


def test_bounded_memory_write(tmp_path):
    runtime, state_path, _ = _runtime(tmp_path)

    def collect(trigger, previous_state):
        return {
            "deterministic_precheck": True,
            "state_version": 1,
            "records": [{"id": "x"}],
            "deterministic_output": {"status": "success", "value": trigger.get("value")},
            "material": {"value": trigger.get("value")},
        }

    spec = replace(
        system_health_loop_spec,
        loop_id="bounded_memory_loop",
        name="Bounded Memory Loop",
        deterministic_precheck=collect,
        ai_decider=lambda collected, reduced, previous_state: {"use_ai": False, "requested_tier": "T0_DETERMINISTIC", "reason": "none"},
        ai_context_builder=lambda collected, reduced, previous_state: {},
        memory_projection=lambda result, collected, previous_state: {"result": result, "summary": {"value": result.get("value")}},
    )

    for idx in range(25):
        runtime.run(spec, {"value": idx})

    state = json.loads(state_path.read_text(encoding="utf-8"))
    loop_state = state["loops"]["bounded_memory_loop"]
    assert len(loop_state["history"]) <= 20
    assert "prompt" not in json.dumps(loop_state)


def test_execution_ledger_records_deterministic_vs_ai(monkeypatch, tmp_path):
    runtime, _, ledger_path = _runtime(tmp_path)
    calls: list[tuple[str, str]] = []
    payloads = {
        "get_opportunities": {
            "status": "success",
            "source_type": "live_governed_read",
            "data": {
                "total": 2,
                "items": [
                    {"id": "opp_1", "title": "Growth", "status": "open", "revenue_potential": 5000},
                    {"id": "opp_2", "title": "Scale", "status": "open", "revenue_potential": 1500},
                ],
            },
        },
        "get_recent_research": {
            "status": "success",
            "source_type": "live_governed_read",
            "data": {"runs": {"total": 1, "items": [{"id": "r1"}]}, "results": {"total": 1, "items": [{"id": "r1"}]}},
        },
        "get_business_model_summary": {
            "status": "success",
            "source_type": "study_snapshot_artifact",
            "offers_count": 9,
            "offers": [],
        },
    }
    monkeypatch.setattr(
        "nexus_agent_platform.loops.runtime.execute_shared_capability",
        _fake_capability_factory(payloads, calls),
    )

    result = runtime.run(
        opportunity_discovery_loop_spec,
        {"window": "today"},
        ai_call=lambda payload: {"status": "success", "ai_summary": "short synthesis", "candidate_ids": ["opp_1"]},
        explicit_premium_escalation=False,
    )

    ledger = _ledger_lines(ledger_path)
    assert ledger
    last = ledger[-1]
    assert last["loop_id"] == "opportunity_discovery_loop"
    assert "deterministic_execution_share" in last
    assert "ai_execution_share" in last
    assert last["ai_used"] == result.ai_used
    assert last["zero_token_execution"] is False
    assert result.ai_used is True
