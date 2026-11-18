from __future__ import annotations

import json
from pathlib import Path

import pytest

from nexus_agent_platform.research_assignment_intent import (
    INTENTS, assignment_job_type, classify_research_assignment, result_contract,
)
from nexus_agent_platform.research_only_execution import (
    HANDOFF_MAX_BYTES, compact_handoff, execute_research_only,
)


def _work(**overrides):
    return {"work_id": "work-diagnostic", "objective_id": "objective-diagnostic",
        "project_id": "project-diagnostic", "original_objective": "Bounded documentation research",
        "question": "What does the documented API return?", "research_scope": "One source read",
        "source_url": "https://docs.python.org/3/library/pathlib.html",
        "requested_intent": "RESEARCH_ONLY", **overrides}


class _Queue:
    def __init__(self, item):
        self.items = [dict(item)]
        self.settled = []

    def load(self):
        return {"items": [dict(item) for item in self.items]}

    def settle(self, work_id, status, *, result=None, blocker_type=None):
        self.settled.append((work_id, status, result, blocker_type))
        for row in self.items:
            if row.get("work_id") == work_id:
                row["status"] = status
                row["last_result"] = result
                return dict(row)
        return None

    def upsert(self, item):
        self.items = [dict(item) if row.get("work_id") == item.get("work_id") else row
                      for row in self.items]


def _case_fixtures(monkeypatch, *, waiting=False, source_text="The documented method returns False."):
    from research import research_case_engine
    opened, reads, saves = [], [], []
    monkeypatch.setattr(research_case_engine, "open_or_join_case", lambda **kw: (
        opened.append(kw) or ({"wait_for_capacity": True, "reason": "CAPACITY"} if waiting else
                              {"case": {"case_id": "rcase-diagnostic"}})))
    monkeypatch.setattr(research_case_engine, "add_source", lambda cid, source:
        {"ok": True, "case": {"case_id": cid}, "source": source})
    monkeypatch.setattr(research_case_engine, "record_research_only_result", lambda cid, **kwargs:
        {"ok": True, "case": {"case_id": cid, "continue_research": False,
             "status": "AWAITING_RAY_DECISION"}, "finding": kwargs["finding"],
         "continuation_scheduled": False})
    from nexus_agent_platform import research_parent_adapters
    monkeypatch.setattr(research_parent_adapters, "_fallback_public_page", lambda url, work:
        reads.append((url, dict(work))) or {"url": url, "title": "Official docs", "text": source_text,
                                            "bytes": 128, "status_code": 200})
    from research import proactive_research_memory
    monkeypatch.setattr(proactive_research_memory, "persist_state", lambda state:
        saves.append(dict(state)) or {**state, "memory_id": state["memory_id"], "state_v2_receipt": {"status": "PASS"}})
    from nexus_agent_platform import evidence_ingestion
    monkeypatch.setattr(evidence_ingestion, "validate_public_url", lambda url: (url, None))
    return opened, reads, saves


def test_research_only_is_an_explicit_supported_intent():
    assert "RESEARCH_ONLY" in INTENTS
    assert assignment_job_type("RESEARCH_ONLY") == "RESEARCH_INTAKE"
    assert classify_research_assignment("Research a bounded question from official docs") != "RESEARCH_ONLY"


def test_research_only_contract_requires_its_own_execution_path():
    good = result_contract(requested_intent="RESEARCH_ONLY", routed_intent="RESEARCH_ONLY",
        execution_path="BOUNDED_RESEARCH_ONLY", status="COMPLETED", result={"summary": "finding"})
    bad = result_contract(requested_intent="RESEARCH_ONLY", routed_intent="RESEARCH_ONLY",
        execution_path="RESEARCH_HANDOFF_COMPLETE", status="COMPLETED", result={"summary": "finding"})
    assert good["task_fulfilled"] is True
    assert bad["task_fulfilled"] is False


def test_handoff_schema_is_compact_and_typed():
    handoff = compact_handoff(job_id="job-1", objective_id="obj-1", project_id="proj-1",
        case_id="case-1", question="Question", summary="Finding", evidence_refs=["https://docs.example/a"])
    assert set(("summary", "key_findings", "evidence_references", "unanswered_questions",
        "recommended_next_research_action", "result_status")).issubset(handoff)
    assert handoff["schema_version"] == "nexus.research-only-handoff.v1"


def test_handoff_caps_summary():
    row = compact_handoff(job_id="j", objective_id="o", project_id="p", case_id="c",
        question="q", summary="x" * 10000, evidence_refs=[])
    assert len(row["summary"]) == 1200


def test_handoff_has_no_source_body_or_transcript_fields():
    row = compact_handoff(job_id="j", objective_id="o", project_id="p", case_id="c",
        question="q", summary="finding", evidence_refs=[])
    assert not ({"source_body", "transcript", "conversation", "full_source"} & row.keys())


def test_handoff_limits_evidence_references():
    row = compact_handoff(job_id="j", objective_id="o", project_id="p", case_id="c",
        question="q", summary="finding", evidence_refs=[f"https://x/{i}" for i in range(20)])
    assert len(row["evidence_references"]) == 5


def test_handoff_limits_unanswered_questions():
    row = compact_handoff(job_id="j", objective_id="o", project_id="p", case_id="c",
        question="q", summary="finding", evidence_refs=[],
        unanswered_questions=[f"q{i}" for i in range(20)])
    assert len(row["unanswered_questions"]) == 5


def test_handoff_payload_is_below_egress_budget():
    row = compact_handoff(job_id="j", objective_id="o", project_id="p", case_id="c",
        question="q", summary="x" * 1200, evidence_refs=[f"https://example.org/{i}" for i in range(5)])
    assert len(json.dumps(row, ensure_ascii=False).encode()) < HANDOFF_MAX_BYTES < 2_000_000


def test_missing_source_fails_closed_before_case_open(monkeypatch):
    opened, reads, saves = _case_fixtures(monkeypatch)
    result = execute_research_only(_work(source_url=""), job_id="job-1")
    assert result["status"] == "BLOCKED"
    assert result["reason"] == "RESEARCH_ONLY_PUBLIC_SOURCE_URL_REQUIRED"
    assert result["research_result"]["result_status"] == "SOURCE_UNAVAILABLE"
    assert opened == reads == [] and len(saves) == 1


def test_rejected_public_url_fails_closed_before_case_open(monkeypatch):
    opened, reads, saves = _case_fixtures(monkeypatch)
    from nexus_agent_platform import evidence_ingestion
    monkeypatch.setattr(evidence_ingestion, "validate_public_url", lambda _url: (None, "PRIVATE_ADDRESS"))
    result = execute_research_only(_work(), job_id="job-1")
    assert result["status"] == "BLOCKED" and "SOURCE_REJECTED" in result["reason"]
    assert opened == reads == [] and saves[-1]["result_status"] == "SOURCE_REJECTED"


def test_case_engine_opens_real_case_contract(monkeypatch):
    opened, _, _ = _case_fixtures(monkeypatch)
    result = execute_research_only(_work(), job_id="job-1")
    assert result["case_id"] == "rcase-diagnostic"
    assert opened[0]["objective_id"] == "objective-diagnostic"
    assert opened[0]["project_id"] == "project-diagnostic"
    assert opened[0]["primary_question"] == "What does the documented API return?"


def test_execution_performs_exactly_one_bounded_source_read(monkeypatch):
    _, reads, _ = _case_fixtures(monkeypatch)
    result = execute_research_only(_work(), job_id="job-1")
    assert result["status"] == "COMPLETED"
    assert result["source_read_count"] == 1
    assert len(reads) == 1


def test_success_persists_research_case_source_finding_and_handoff(monkeypatch):
    opened, _, saves = _case_fixtures(monkeypatch)
    result = execute_research_only(_work(), job_id="job-1")
    assert result["status"] == "COMPLETED"
    assert result["downstream_jobs_created"] == 0
    assert result["research_result"]["summary"] == "The documented method returns False."
    assert saves[0]["memory_kind"] == "RESEARCH_ONLY_RESULT"
    assert saves[0]["case_id"] == "rcase-diagnostic"
    assert opened


def test_result_uses_question_relevant_source_passage(monkeypatch):
    _case_fixtures(monkeypatch, source_text=(
        "The pathlib module provides object-oriented filesystem paths. "
        "Path.is_dir() returns False if the path does not exist or is not a directory."
    ))
    result = execute_research_only(_work(question="What does Path.is_dir() return when the path does not exist?"),
                                   job_id="job-1")
    assert result["status"] == "COMPLETED"
    assert "Path.is_dir() returns False" in result["research_result"]["summary"]


def test_result_fails_closed_when_source_has_no_relevant_passage(monkeypatch):
    _, _, saves = _case_fixtures(monkeypatch, source_text="The pathlib module contains filesystem path classes.")
    result = execute_research_only(_work(question="What does Path.is_dir() return for a missing path?"),
                                   job_id="job-1")
    assert result["status"] == "BLOCKED"
    assert result["research_result"]["result_status"] == "SOURCE_INSUFFICIENT"
    assert saves[-1]["unanswered_questions"] == ["What does Path.is_dir() return for a missing path?"]


def test_research_only_case_waits_for_review_without_auto_continuation(monkeypatch):
    from research import research_case_engine
    captured = {}
    monkeypatch.setattr(research_case_engine, "get_case", lambda _case_id: {
        "case_id": "case-1", "open_questions": [{"question_id": "q1", "question": "Exact question?"}],
        "answered_questions": [], "findings": []})
    monkeypatch.setattr(research_case_engine, "_save", lambda case, event, **details:
        captured.update(event=event, **details) or {**case, **details})
    result = research_case_engine.record_research_only_result("case-1", question="Exact question?",
        answer="Bounded grounded answer", evidence_ids=["https://docs.example"], finding={"finding_id": "f1"})
    assert result["ok"] is True
    assert captured["status"] == "AWAITING_RAY_DECISION"
    assert captured["continue_research"] is False
    assert captured["open_questions"] == []
    assert captured["answered_questions"][0]["answer"] == "Bounded grounded answer"


def test_result_contract_has_official_source_evidence_reference(monkeypatch):
    _case_fixtures(monkeypatch)
    result = execute_research_only(_work(), job_id="job-1")
    assert result["research_result"]["evidence_references"] == ["https://docs.python.org/3/library/pathlib.html"]


def test_source_failure_is_an_explicit_persisted_bounded_result(monkeypatch):
    _, _, saves = _case_fixtures(monkeypatch)
    from nexus_agent_platform import research_parent_adapters
    monkeypatch.setattr(research_parent_adapters, "_fallback_public_page", lambda *_: {
        "status": "SOURCE_READ_FAILED", "reason": "HTTPError"})
    result = execute_research_only(_work(), job_id="job-1")
    assert result["status"] == "BLOCKED"
    assert result["research_result"]["result_status"] == "SOURCE_UNAVAILABLE"
    assert saves[-1]["result_status"] == "SOURCE_UNAVAILABLE"


def test_capacity_wait_is_retryable_without_downstream_work(monkeypatch):
    _case_fixtures(monkeypatch, waiting=True)
    result = execute_research_only(_work(), job_id="job-1")
    assert result["status"] == "WAITING_FOR_CAPACITY"
    assert result["retryable"] is True and result["objective_terminated"] is False


def test_normal_parent_workflow_still_contains_advisor_and_needle():
    from nexus_agent_platform.research_parent_workflow import WORKFLOW
    assert "ADVISOR_REVIEW" in WORKFLOW
    assert "NEEDLE_REVIEW" in WORKFLOW
    assert WORKFLOW.index("SOURCE_UNDERSTANDING") < WORKFLOW.index("ADVISOR_REVIEW") < WORKFLOW.index("NEEDLE_REVIEW")


def test_worker_has_distinct_research_only_dispatch_before_normal_mission():
    source = Path(__file__).parents[1].joinpath("job_worker_once.py").read_text()
    only_at = source.index('== "RESEARCH_ONLY"')
    mission_at = source.index('== "RESEARCH_MISSION"', only_at)
    assert only_at < mission_at
    assert "consume_child_result" in source


def test_mcp_entrypoint_requires_explicit_research_only_intent():
    server_source = Path(__file__).parents[3] / "certification/r54_source/services/nexus_mcp/server.py"
    text = server_source.read_text()
    assert '"RESEARCH_ONLY": "BOUNDED_RESEARCH_ONLY"' in text
    assert '"RESEARCH_ONLY": "RESEARCH_ONLY"' in text


def test_worker_research_only_branch_is_scoped_to_owner_research_assignment():
    source = Path(__file__).parents[1].joinpath("job_worker_once.py").read_text()
    start = source.index('== "RESEARCH_ONLY"')
    branch = source[start - 260:start + 1500]
    assert 'job.job_type == "RESEARCH_INTAKE"' in branch
    assert 'research_parent_source == "NOVA_MCP_RESEARCH_ASSIGNMENT"' in branch


def test_research_only_executor_has_no_legacy_ledger_dependency():
    source = Path(__file__).parents[1].joinpath("research_only_execution.py").read_text()
    assert "research_runtime_states.jsonl" not in source
    assert "allow_bounded_local_recovery" not in source


def test_real_durable_worker_completes_research_only_without_parent_children(tmp_path, monkeypatch):
    from nexus_agent_platform import job_worker_once, research_work_queue, stability_supervisor
    from nexus_agent_platform.durable_jobs import DurableJobStore
    from nexus_agent_platform.resource_spend_governor import LocalGovernorStore

    monkeypatch.setenv("NEXUS_GOVERNOR_DB", str(tmp_path / "governor.sqlite3"))
    governor = LocalGovernorStore(tmp_path / "governor.sqlite3")
    governor.set_policy("SUPABASE", "durable_worker", "*", "DAILY", autonomous_usage_allowed=True,
        hard_limits={"rate": {}, "usage": {"requests": 120, "bytes": 2_000_000},
                     "money": {"per_job": 0, "per_day": 0, "per_month": 0}})
    from nexus_agent_platform import supabase_egress_guard
    monkeypatch.setattr(supabase_egress_guard, "job_egress_snapshot",
        lambda _job: {"request_count": 0, "response_bytes": 0})
    monkeypatch.setattr(job_worker_once, "_footprint", lambda *args, **kwargs: "fixture-footprint")
    monkeypatch.setattr(job_worker_once, "_lifecycle", lambda *args, **kwargs: None)
    monkeypatch.setattr(job_worker_once, "ROOT", tmp_path)
    monkeypatch.setattr(stability_supervisor, "get_host_execution_gate", lambda: {
        "heavy_work_allowed": True, "research_execution_allowed": True, "reason_codes": []})

    queue = _Queue(_work())
    monkeypatch.setattr(research_work_queue, "default_queue", lambda: queue)
    from nexus_agent_platform import research_only_execution
    handoff = {"schema_version": "nexus.research-only-handoff.v1", "summary": "Grounded finding",
        "result_status": "RESEARCH_COMPLETE", "evidence_references": ["https://docs.python.org/"]}
    monkeypatch.setattr(research_only_execution, "execute_research_only", lambda work_item, **kwargs: {
        "status": "COMPLETED", "case_id": "rcase-diagnostic", "research_result": handoff,
        "requested_intent": "RESEARCH_ONLY", "routed_intent": "RESEARCH_ONLY",
        "execution_path": "BOUNDED_RESEARCH_ONLY",
        "downstream_jobs_created": 0, "source_read_count": 1})
    store = DurableJobStore(tmp_path / "jobs.sqlite3")
    job = store.enqueue("RESEARCH", "RESEARCH_INTAKE", payload_ref="work-diagnostic",
        correlation_id="objective-diagnostic", idempotency_key="research-only-diagnostic",
        governance_context={"source": "NOVA_MCP_RESEARCH_ASSIGNMENT", "objective_id": "objective-diagnostic",
            "project_id": "project-diagnostic", "requested_intent": "RESEARCH_ONLY",
            "routed_intent": "RESEARCH_ONLY", "execution_path": "BOUNDED_RESEARCH_ONLY",
            "original_objective": "Bounded documentation research", "research_scope": "One source read",
            "original_source_url": "https://docs.python.org/3/library/pathlib.html",
            "external_actions_allowed": False, "spend_allowed": False})
    assert store.claim_by_id(job.job_id, "research-only-worker")
    result = job_worker_once.run(job.job_id, "research-only-worker", store)
    assert result["status"] == "COMPLETED"
    assert result["task_fulfillment"]["task_fulfilled"] is True
    assert store.get(job.job_id).state == "COMPLETED"
    assert store.get(job.job_id).lease_until is None
    assert queue.items[0]["status"] == "COMPLETE"
    assert store.list_ready(20) == []
    assert store.active() == []
