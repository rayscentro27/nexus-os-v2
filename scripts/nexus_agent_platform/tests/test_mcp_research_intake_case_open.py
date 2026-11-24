from __future__ import annotations

from types import SimpleNamespace

from nexus_agent_platform import job_worker_once
from research import research_case_engine


def _work_item() -> dict:
    return {"requested_intent": "RESEARCH_MISSION", "routed_intent": "RESEARCH_MISSION",
        "objective": "Disposable intake lineage contract test", "title": "Disposable intake lineage contract test",
        "question": "Use only supplied facts to compare two pickup windows.",
        "research_scope": "Use only supplied facts to compare two pickup windows.",
        "work_id": "project-contract-test", "objective_id": "objective-contract-test",
        "source_type": "NOVA_OBJECTIVE", "requested_by": "hermes_nova"}


def test_mcp_intake_opens_case_engine_case_before_continuation(monkeypatch):
    calls = []
    case = {"case_id": "rcase-contract-test", "case_schema_version": "nexus.research-case.v1"}

    def open_case(**kwargs):
        calls.append(kwargs)
        return {"opened": True, "case": case}

    monkeypatch.setattr(research_case_engine, "open_or_join_case", open_case)
    monkeypatch.setattr(research_case_engine, "get_case", lambda case_id: case if case_id == case["case_id"] else None)
    result = job_worker_once.open_mcp_research_intake_case(_work_item())

    assert result["status"] == "CASE_OPENED"
    assert result["case_id"] == "rcase-contract-test"
    assert result["case_created"] is True
    assert len(calls) == 1
    assert calls[0]["objective"] == "Disposable intake lineage contract test"
    assert calls[0]["project_id"] == "project-contract-test"
    assert calls[0]["objective_id"] == "objective-contract-test"


def test_mcp_intake_waits_when_execution_capacity_is_full(monkeypatch):
    monkeypatch.setattr(research_case_engine, "open_or_join_case", lambda **kwargs: {
        "opened": False, "reason": "MAX_ACTIVE_DEEP_CASES_REACHED", "wait_for_capacity": True,
        "retryable": True, "objective_terminated": False})
    result = job_worker_once.open_mcp_research_intake_case(_work_item())

    assert result["status"] == "WAITING_FOR_CAPACITY"
    assert result["retryable"] is True
    assert result["objective_terminated"] is False
    assert result["case_created"] is False


def test_case_engine_persists_exact_objective_and_project_lineage(monkeypatch):
    monkeypatch.setattr(research_case_engine, "_latest_cases", lambda **kwargs: [])
    monkeypatch.setattr(research_case_engine, "active_deep_execution_case_ids", lambda cases=None: set())
    monkeypatch.setattr(research_case_engine, "persist_state", lambda case: case)
    result = research_case_engine.open_or_join_case(
        objective="Lineage field contract", objective_family="RESEARCH_INTAKE",
        business_or_nexus_goal="RESEARCH_INTAKE", owner_department="RESEARCH",
        primary_question="Compare two supplied options from local fixture text.",
        project_id="project-contract-test", objective_id="objective-contract-test",
        originating_goal_id="objective-contract-test")
    assert result["opened"] is True
    assert result["case"]["project_id"] == "project-contract-test"
    assert result["case"]["objective_id"] == "objective-contract-test"
