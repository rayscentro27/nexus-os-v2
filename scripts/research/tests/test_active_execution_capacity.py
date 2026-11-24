from __future__ import annotations

from types import SimpleNamespace

import pytest

from research import research_case_engine as engine


def _case(case_id: str, status: str = "PROMISING", *, continue_research: bool = True) -> dict:
    return {"case_id": case_id, "case_schema_version": "nexus.research-case.v1",
        "status": status, "continue_research": continue_research}


def _job(case_id: str, state: str = "RUNNING", *, department: str = "RESEARCH") -> SimpleNamespace:
    return SimpleNamespace(state=state, department=department,
        governance_context={"case_id": case_id})


def test_terminal_certification_case_does_not_consume_execution_slot():
    assert engine.active_deep_execution_case_ids(
        [_job("cert")], [_case("cert", "RAY_DENIAL_RECORDED", continue_research=False)]) == set()


def test_dormant_persisted_research_case_does_not_consume_slot_but_remains_resumable():
    dormant = _case("dormant", "MORE_RESEARCH_REQUIRED")
    assert engine.active_deep_execution_case_ids([], [dormant]) == set()
    assert dormant["status"] in engine.ACTIVE_STATES
    assert dormant["continue_research"] is True


def test_actively_executing_research_case_consumes_slot():
    assert engine.active_deep_execution_case_ids(
        [_job("running")], [_case("running", "RESEARCHING")]) == {"running"}


def test_no_more_than_max_active_deep_cases_can_execute_concurrently(monkeypatch):
    jobs = [_job(f"case-{index}") for index in range(engine.MAX_ACTIVE_DEEP_CASES)]
    cases = [_case(f"case-{index}") for index in range(engine.MAX_ACTIVE_DEEP_CASES)]
    ids = engine.active_deep_execution_case_ids(jobs, cases)
    assert len(ids) == engine.MAX_ACTIVE_DEEP_CASES == 3
    monkeypatch.setattr(engine, "_latest_cases", lambda **kwargs: cases)
    monkeypatch.setattr(engine, "active_deep_execution_case_ids", lambda cases=None: ids)
    result = engine.open_or_join_case(objective="fourth", objective_family="BUSINESS_OPPORTUNITIES",
        business_or_nexus_goal="test", owner_department="RESEARCH", primary_question="question")
    assert result["reason"] == "MAX_ACTIVE_DEEP_CASES_REACHED"
    assert result["wait_for_capacity"] is True
    assert result["objective_terminated"] is False


def test_open_case_uses_compact_remote_case_controls(monkeypatch):
    projected = {"case_id": "existing-case", "memory_kind": "RESEARCH_CASE",
        "objective_key": "different-key", "case_schema_version": "nexus.research-case.v1",
        "status": "PROMISING", "continue_research": True}
    calls = []
    monkeypatch.setattr(engine, "_read_recent_states",
        lambda **kwargs: calls.append(kwargs) or [projected])
    monkeypatch.setattr(engine, "active_deep_execution_case_ids", lambda cases=None: set())
    monkeypatch.setattr(engine, "persist_state", lambda case: case)
    result = engine.open_or_join_case(objective="new objective for compact read",
        objective_family="BUSINESS_OPPORTUNITIES", business_or_nexus_goal="test",
        owner_department="RESEARCH", primary_question="Compare supplied fixture options.")
    assert result["opened"] is True
    assert calls == [{"max_bytes": 8_000_000, "max_records": 100, "include_full_payload": False}]


def test_resuming_dormant_case_reacquires_slot_when_execution_job_starts():
    dormant = _case("resume", "MORE_RESEARCH_REQUIRED")
    assert engine.active_deep_execution_case_ids([], [dormant]) == set()
    resumed_job = _job("resume", "RUNNING")
    assert engine.active_deep_execution_case_ids([resumed_job], [dormant]) == {"resume"}


def test_waiting_for_capacity_preserves_objective_for_retry(monkeypatch):
    active = {f"case-{index}" for index in range(3)}
    monkeypatch.setattr(engine, "_latest_cases", lambda **kwargs: [])
    monkeypatch.setattr(engine, "active_deep_execution_case_ids", lambda cases=None: active)
    result = engine.open_or_join_case(objective="queued objective", objective_family="BUSINESS_OPPORTUNITIES",
        business_or_nexus_goal="test", owner_department="RESEARCH", primary_question="question")
    assert result["wait_for_capacity"] and result["retryable"]
    assert result["objective_terminated"] is False


def test_actual_objective_termination_requires_ray_stop_approval(monkeypatch, tmp_path):
    monkeypatch.setenv("NEXUS_GOVERNED_DATA_DIR", str(tmp_path))
    from nexus_agent_platform.governed.approvals import create_approval_request, resolve_approval
    from nexus_agent_platform.project_stop_policy import ray_stop_authorized
    assert not ray_stop_authorized(actor="RAY", approval_id="missing", decision="REJECT", project_id="case")
    receipt = create_approval_request(action_id="project.stop", requested_by="ray", requested_for="ray",
        input_summary={"project_id": "case", "decision": "REJECT"})
    resolve_approval(receipt["id"], "approve", resolved_by="Ray")
    assert ray_stop_authorized(actor="RAY", approval_id=receipt["id"], decision="REJECT", project_id="case")


def test_stop_receipt_for_disposable_case_cannot_authorize_phase5():
    from nexus_agent_platform.project_stop_policy import ray_stop_authorized
    from nexus_agent_platform.governed.approvals import create_approval_request, resolve_approval
    from nexus_agent_platform.governed import persistence
    # Keep this proof isolated from the user's real governed approval ledger.
    original = persistence.governed_data_dir
    try:
        import tempfile
        from pathlib import Path
        directory = tempfile.TemporaryDirectory()
        persistence.governed_data_dir = lambda: Path(directory.name)
        receipt = create_approval_request(action_id="project.stop", requested_by="ray", requested_for="ray",
            input_summary={"project_id": "approved-cert-case", "decision": "REJECT"})
        resolve_approval(receipt["id"], "approve", resolved_by="Ray")
        assert ray_stop_authorized(actor="RAY", approval_id=receipt["id"], decision="REJECT",
            project_id="approved-cert-case")
        assert not ray_stop_authorized(actor="RAY", approval_id=receipt["id"], decision="REJECT",
            project_id="rcase_f6c19e2c0afe9c44ea")
        directory.cleanup()
    finally:
        persistence.governed_data_dir = original


def test_case_engine_retains_three_slot_limit():
    assert engine.MAX_ACTIVE_DEEP_CASES == 3
