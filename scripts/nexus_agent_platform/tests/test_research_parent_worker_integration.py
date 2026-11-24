from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from nexus_agent_platform.durable_jobs import DurableJobStore


class _Queue:
    def __init__(self, item):
        self.items = [dict(item)]
        self.settled = []

    def load(self):
        return {"items": [dict(item) for item in self.items]}

    def upsert(self, item):
        self.items = [dict(item) if row.get("work_id") == item.get("work_id") else row
                      for row in self.items]

    def settle(self, work_id, status, *, result=None, blocker_type=None):
        self.settled.append((work_id, status, result, blocker_type))
        for row in self.items:
            if row.get("work_id") == work_id:
                row["status"] = status
                row["last_result"] = result
                return dict(row)
        return None


def _install_worker_dependencies(tmp_path, monkeypatch):
    from nexus_agent_platform import job_worker_once, stability_supervisor, supabase_egress_guard
    from nexus_agent_platform.resource_spend_governor import LocalGovernorStore

    governor_path = tmp_path / "governor.sqlite3"
    monkeypatch.setenv("NEXUS_GOVERNOR_DB", str(governor_path))
    governor = LocalGovernorStore(governor_path)
    governor.set_policy("SUPABASE", "durable_worker", "*", "DAILY", autonomous_usage_allowed=True,
        hard_limits={"rate": {}, "usage": {"requests": 120, "bytes": 2_000_000},
                     "money": {"per_job": 0, "per_day": 0, "per_month": 0}})
    monkeypatch.setattr(supabase_egress_guard, "job_egress_snapshot",
                        lambda _job: {"request_count": 0, "response_bytes": 0})
    monkeypatch.setattr(job_worker_once, "_footprint", lambda *a, **k: "fixture-footprint")
    # Worker lifecycle tests isolate the host policy seam; dedicated R53 tests
    # exercise fresh host and State v2 readiness decisions.
    monkeypatch.setattr(stability_supervisor, "get_host_execution_gate", lambda: {
        "heavy_work_allowed": True, "research_execution_allowed": True, "reason_codes": []})
    return governor


def test_systems_job_status_projection_preserves_real_result_content():
    from nexus_agent_platform.job_worker_once import _bounded_result_summary

    projected = _bounded_result_summary({"answer": "MCP is reachable; dispatcher is active.",
        "evidence": [{"check": "mcp", "status": "PASS"}],
        "department_receipt_id": "systems-receipt-1"}, completed_at="2026-10-15T00:00:00Z")
    assert projected["answer"] == "MCP is reachable; dispatcher is active."
    assert projected["evidence"][0]["status"] == "PASS"
    assert projected["department_receipt_id"] == "systems-receipt-1"
    assert projected["completed_at"] == "2026-10-15T00:00:00Z"


def test_real_worker_creative_control_job_persists_artifact_and_readback(tmp_path, monkeypatch):
    from nexus_agent_platform import job_worker_once

    _install_worker_dependencies(tmp_path, monkeypatch)
    monkeypatch.setattr(job_worker_once, "ROOT", tmp_path)
    monkeypatch.setenv("NEXUS_GOVERNED_DATA_DIR", str(tmp_path / "governed"))
    monkeypatch.setenv("NEXUS_CREATIVE_ARTIFACT_DIR", str(tmp_path / "creative-assets"))
    payload = tmp_path / "inputs" / "creative.json"
    payload.parent.mkdir(parents=True)
    payload.write_text(json.dumps({"task": "Create a simple test logo for Nexus Test.",
        "spend_allowed": False, "external_actions_allowed": False}), encoding="utf-8")
    store = DurableJobStore(tmp_path / "creative-jobs.sqlite3")
    job = store.enqueue("CREATIVE", "NOVA_CREATIVE_ASSET", payload_ref="inputs/creative.json",
        correlation_id="root-creative-test", idempotency_key="nova-creative-test",
        governance_context={"source": "NOVA_BOUNDED_CONTROL_ACTION", "spend_allowed": False,
            "external_actions_allowed": False, "resource_class": "LIGHTWEIGHT_INTERNAL"})
    assert store.claim_by_id(job.job_id, "creative-test-worker")
    result = job_worker_once.run(job.job_id, "creative-test-worker", store)
    completed = store.get(job.job_id)
    summary = completed.governance_context["result_summary"]
    assert result["status"] == "COMPLETED"
    assert completed.state == "COMPLETED"
    assert result["asset_type"] == "SVG_LOGO_CONCEPT"
    assert __import__("pathlib").Path(result["artifact_path"]).is_file()
    assert "Nexus Test" in summary["answer"]


def _install_external_fixtures(monkeypatch, *, negative=False):
    from nexus_agent_platform import alpha_research, evidence_ingestion
    from research import needle_research_readiness

    monkeypatch.setattr(evidence_ingestion, "ingest_url", lambda url, **kwargs: {
        "status": "SUCCESS", "artifact_ref": "evidence-artifact-1", "receipt_ref": "evidence-receipt-1",
        "receipt_id": "evidence-1", "source": {"original_reference": url},
        "integrity": {"source_hash": "hash-1"},
        "content": {"title": "Trading strategy", "normalized_text_or_markdown": "A bounded strategy source fixture."}})
    monkeypatch.setattr(alpha_research, "execute_alpha_request", lambda **kwargs: {
        "status": "COMPLETE", "request_id": "alpha-request-1", "execution": {"executed": True},
        "report": "Fixture advisor and follow-up evidence.",
        "plan": {"key_questions": ["What is the exact entry and exit rule?"]},
        "pack": {"claims": ["Claim to verify"], "sources": [{"evidence_id": "alpha-evidence-1",
            "source": {"original_reference": "https://example.test/evidence"}}],
            "opportunities": [], "plan": {"stopping_conditions": ["Bounded evidence collected"]}},
        "artifact_id": "alpha-pack-1", "result_id": "alpha-result-1",
        "test_result": "NEGATIVE" if negative else None})
    monkeypatch.setattr(needle_research_readiness, "verify_readiness", lambda *a, **k: {
        "status": "READY_FOR_DEPARTMENT", "ok": True, "summary": "Question coverage is sufficient with uncertainty preserved.",
        "receipt_id": "needle-receipt-1", "unresolved_items_safe": True})

    # Keep the existing Nexus handoff client intact; replace only its HTTP
    # transport with an in-memory representation of the existing table.
    from operations import nexus_handoff
    rows = {}
    monkeypatch.setattr(nexus_handoff, "configured", lambda: True)
    monkeypatch.setattr(nexus_handoff, "find_by_dedupe_key", lambda _key: None)

    def rest(method, path, *, body=None, **kwargs):
        if method == "POST":
            row = dict((body or [{}])[0])
            rows[row["handoff_id"]] = row
            return 201, [row]
        handoff_id = path.split("handoff_id=eq.", 1)[1].split("&", 1)[0] if "handoff_id=eq." in path else ""
        if method == "GET":
            return 200, ([rows[handoff_id]] if handoff_id in rows else [])
        if method == "PATCH" and handoff_id in rows:
            rows[handoff_id].update(body or {})
            return 200, [rows[handoff_id]]
        return 200, []

    monkeypatch.setattr(nexus_handoff, "rest", rest)
    return rows


def test_nova_research_continuation_uses_case_intake_without_public_source_replay(tmp_path, monkeypatch):
    from nexus_agent_platform import job_worker_once, research_assignment_executor, research_work_queue

    _install_worker_dependencies(tmp_path, monkeypatch)
    item = {"work_id": "nova_research_continue_existing", "source_type": "NOVA_OBJECTIVE",
        "requested_intent": "RESEARCH_MISSION", "routed_intent": "RESEARCH_MISSION",
        "execution_path": "RESEARCH_INTAKE", "objective_id": "objective-existing",
        "followup_of": "objective-existing", "question": "Continue this exact Research objective",
        "status": "FAILED_RETRYABLE"}
    queue = _Queue(item)
    monkeypatch.setattr(research_work_queue, "default_queue", lambda: queue)
    monkeypatch.setattr(job_worker_once, "ROOT", tmp_path)
    calls = []
    def execute_assignment(work_item):
        calls.append(dict(work_item))
        return {"status": "CONTINUATION_REQUIRED", "case_id": "rcase-existing-lineage",
            "execution_path": "RESEARCH_INTAKE", "requested_intent": "RESEARCH_MISSION",
            "routed_intent": "RESEARCH_MISSION", "next_action": "RESEARCH_SOURCE_ACQUISITION_AND_EVIDENCE_GATHERING"}
    monkeypatch.setattr(research_assignment_executor, "execute_assignment", execute_assignment)
    monkeypatch.setattr(job_worker_once, "subprocess", SimpleNamespace(run=
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("generic source runner must not run"))))

    store = DurableJobStore(tmp_path / "jobs.sqlite3")
    job = store.enqueue("RESEARCH", "RESEARCH_INTAKE", payload_ref=item["work_id"],
        correlation_id="objective-existing", idempotency_key="same-existing-job",
        governance_context={"source": "NOVA_RESEARCH_CONTINUATION", "objective_id": "objective-existing",
            "requested_intent": "RESEARCH_MISSION", "routed_intent": "RESEARCH_MISSION",
            "execution_path": "RESEARCH_INTAKE", "spend_allowed": False,
            "external_actions_allowed": False})
    assert store.claim_by_id(job.job_id, "continuation-test-worker")
    result = job_worker_once.run(job.job_id, "continuation-test-worker", store)

    assert result["status"] == "COMPLETED"
    assert result["case_id"] == "rcase-existing-lineage"
    assert result["research_stage"] == "RESEARCH_CASE_OPENED"
    assert result["new_research_job_created"] is False
    assert store.get(job.job_id).state == "COMPLETED"
    assert len(calls) == 1 and calls[0]["objective_id"] == "objective-existing"
    assert queue.items[0]["research_case_id"] == "rcase-existing-lineage"
    assert queue.settled[-1][0:2] == (item["work_id"], "COMPLETE")
    assert store.list_ready(20) == []


@pytest.mark.parametrize("negative", [False, True])
def test_real_worker_entrypoint_consumes_parent_until_trading_handoff(tmp_path, monkeypatch, negative):
    from nexus_agent_platform import job_worker_once
    from nexus_agent_platform.research_parent_workflow import recover_orphaned_parents

    _install_worker_dependencies(tmp_path, monkeypatch)
    handoff_rows = _install_external_fixtures(monkeypatch, negative=negative)
    item = {"work_id": "work-trading-1", "objective_id": "nova_research_work-1",
        "parent_request_id": "root-trading-1",
        "original_objective": "Research this TradingView strategy and determine useful next experiments.",
        "original_source_url": "https://example.test/strategy", "source_url": "https://example.test/strategy",
        "original_source_type": "TRADING_STRATEGY", "source_type": "TRADING_STRATEGY",
        "objective_type": "TRADING_INTELLIGENCE", "requested_intent": "RESEARCH_MISSION",
        "routed_intent": "RESEARCH_MISSION", "execution_path": "RESEARCH_INTAKE",
        "research_scope": "Understand and evaluate the strategy", "status": "QUEUED"}
    queue = _Queue(item)
    monkeypatch.setattr("nexus_agent_platform.research_work_queue.default_queue", lambda: queue)
    store = DurableJobStore(tmp_path / "durable-jobs.sqlite3")
    root = store.enqueue("RESEARCH", "RESEARCH_INTAKE", payload_ref=item["work_id"],
        correlation_id=item["parent_request_id"], idempotency_key="root-trading-1",
        governance_context={"source": "NOVA_MCP_RESEARCH_ASSIGNMENT", "objective_id": item["objective_id"],
            "original_objective": item["original_objective"], "original_source_url": item["source_url"],
            "original_source_type": item["source_type"], "requested_intent": "RESEARCH_MISSION",
            "routed_intent": "RESEARCH_MISSION", "execution_path": "RESEARCH_INTAKE",
            "research_scope": item["research_scope"]})

    current = store.claim_by_id(root.job_id, "integration-worker")
    assert current
    first = job_worker_once.run(root.job_id, "integration-worker", store)
    assert first["status"] == "COMPLETED"
    assert first["research_parent"]["status"] == "CONTINUATION_SCHEDULED"
    assert first["research_parent"]["next_action"] == "SOURCE_UNDERSTANDING"
    parent_state = store.get(root.job_id).governance_context["research_parent_state"]
    assert parent_state["objective_id"] == item["parent_request_id"]
    assert parent_state["root_objective_id"] == item["parent_request_id"]
    assert parent_state["research_parent_id"] == item["objective_id"]
    assert queue.items[0]["status"] == "IN_PROGRESS"
    root_state=store.get(root.job_id).governance_context["research_parent_state"]
    children=[job for job in store.list_ready(50)
        if (job.governance_context or {}).get("source")=="RESEARCH_PARENT_CONTINUATION"]
    assert len(children)==1
    assert children[0].job_id==first["research_parent"]["next_job_id"]
    assert store.get(root.job_id).state=="COMPLETED"
    from nexus_agent_platform.research_parent_workflow import create_continuation_job
    duplicate=create_continuation_job(store,state=root_state,parent_job_id=root.job_id,payload_ref=item["work_id"])
    assert duplicate.job_id==children[0].job_id
    assert len([job for job in store.list_ready(50)
        if (job.governance_context or {}).get("source")=="RESEARCH_PARENT_CONTINUATION"])==1

    # The worker, durable claim/transition/receipt path, real parent selector,
    # durable continuation enqueue, production adapters, and existing
    # handoff client are exercised together. External provider responses are
    # deterministic fixtures; no production work or network call occurs.
    for _ in range(12):
        ready = [job for job in store.list_ready(50)
                 if (job.governance_context or {}).get("source") == "RESEARCH_PARENT_CONTINUATION"]
        if not ready:
            break
        child = ready[0]
        claimed = store.claim_by_id(child.job_id, "integration-worker")
        assert claimed
        result = job_worker_once.run(child.job_id, "integration-worker", store)
        assert result["status"] == "COMPLETED"
        if result.get("research_parent", {}).get("root_objective_status") == "COMPLETE":
            break

    completed = store.list_research_parent_jobs()
    state = max((job.governance_context["research_parent_state"] for job in completed),
                key=lambda value: (int(value.get("continuation_sequence", 0)),
                                   bool(value.get("handoff"))))
    assert state["status"] == "COMPLETE"
    assert state["next_department"] == "TRADING"
    assert state["handoff"]["handoff_id"]
    assert state["test_results"] == (["NEGATIVE"] if negative else [])
    assert any(row.get("target_department") == "TRADING" and row.get("status") == "DELIVERED"
               for row in handoff_rows.values())
    assert queue.settled and queue.settled[-1][1] == "COMPLETE"

    before = len(store.list_ready(100))
    recovery = recover_orphaned_parents(store)
    after = len(store.list_ready(100))
    assert recovery["recovered"] == 0
    assert after == before
    assert len({job.idempotency_key for job in completed}) == len(completed)


def test_orphan_watchdog_schedules_exactly_one_durable_continuation(tmp_path):
    from nexus_agent_platform.research_parent_workflow import new_parent, recover_orphaned_parents

    store = DurableJobStore(tmp_path / "orphan-jobs.sqlite3")
    state = new_parent(objective_id="root-orphan-1", original_objective="Research the supplied source",
        source_url="https://example.test/source")
    state["continuation_sequence"] = 4
    root = store.enqueue("RESEARCH", "RESEARCH_INTAKE", payload_ref="work-orphan-1",
        correlation_id="root-orphan-1", idempotency_key="orphan-root",
        governance_context={"source": "RESEARCH_PARENT_CONTINUATION",
            "objective_id": "root-orphan-1", "research_parent_action": "SOURCE_UNDERSTANDING",
            "research_parent_state": state})
    assert store.claim_by_id(root.job_id, "orphan-test-worker")
    store.transition(root.job_id, "RUNNING", worker_id="orphan-test-worker")
    store.complete(root.job_id, "orphan-test-worker", {"status": "COMPLETED"})

    first = recover_orphaned_parents(store)
    second = recover_orphaned_parents(store)
    children = [job for job in store.list_ready(50)
        if (job.governance_context or {}).get("source") == "RESEARCH_PARENT_CONTINUATION"]
    assert first["recovered"] == 1
    assert second["recovered"] == 0
    assert len(children) == 1
    assert children[0].governance_context["research_parent_action"] == "SOURCE_UNDERSTANDING"


def test_orphan_watchdog_advances_past_terminal_idempotency_collision(tmp_path):
    from nexus_agent_platform.research_parent_workflow import new_parent, recover_orphaned_objective, continuation_job_key

    store = DurableJobStore(tmp_path / "orphan-terminal-collision.sqlite3")
    state = new_parent(objective_id="root-terminal-collision", original_objective="Research supplied source",
        source_url="https://example.test")
    state["continuation_sequence"] = 1
    blocked = store.enqueue("RESEARCH", "RESEARCH_INTAKE", payload_ref="work-collision",
        parent_job_id="parent-collision", correlation_id=state["objective_id"],
        idempotency_key=continuation_job_key(state["objective_id"], "SOURCE_UNDERSTANDING", 2),
        governance_context={"source": "RESEARCH_PARENT_CONTINUATION", "research_parent_state": state,
            "research_parent_action": "SOURCE_UNDERSTANDING"})
    assert store.claim_by_id(blocked.job_id, "collision-test-worker")
    store.transition(blocked.job_id, "RUNNING", worker_id="collision-test-worker")
    store.transition(blocked.job_id, "BLOCKED", worker_id="collision-test-worker",
        error_code="FIXTURE_BLOCKED", error_summary="fixture failure")

    recovered = recover_orphaned_objective(store, state=state, parent_job_id=blocked.job_id,
        payload_ref="work-collision", child_states=[])
    again = recover_orphaned_objective(store, state=state, parent_job_id=blocked.job_id,
        payload_ref="work-collision", child_states=[])
    assert recovered.job_id != blocked.job_id
    assert recovered.state == "READY"
    assert again.job_id == recovered.job_id
    active = [job for job in store.list_ready(50)
        if (job.governance_context or {}).get("source") == "RESEARCH_PARENT_CONTINUATION"]
    assert len(active) == 1


def test_orphan_watchdog_advances_after_repeated_child_failure_without_ending_research(tmp_path):
    from nexus_agent_platform.research_parent_workflow import new_parent, create_continuation_job, recover_orphaned_parents

    store = DurableJobStore(tmp_path / "orphan-repeated-terminal.sqlite3")
    state = new_parent(objective_id="root-repeated-failure", original_objective="Research supplied source",
        source_url="https://example.test")
    root = store.enqueue("RESEARCH", "RESEARCH_INTAKE", payload_ref="work-repeated-failure",
        correlation_id=state["objective_id"], idempotency_key="root-repeated-failure",
        governance_context={"source": "RESEARCH_PARENT_CONTINUATION", "research_parent_state": state,
            "research_parent_action": "SOURCE_UNDERSTANDING"})
    assert store.claim_by_id(root.job_id, "repeated-failure-worker")
    store.transition(root.job_id, "RUNNING", worker_id="repeated-failure-worker")
    store.complete(root.job_id, "repeated-failure-worker", {"status": "COMPLETED"})

    def block(job):
        assert store.claim_by_id(job.job_id, "repeated-failure-worker")
        store.transition(job.job_id, "RUNNING", worker_id="repeated-failure-worker")
        store.transition(job.job_id, "BLOCKED", worker_id="repeated-failure-worker",
            error_code="JOB_BUDGET_LIMIT", error_summary="bounded test failure")

    first = create_continuation_job(store, state=state, parent_job_id=root.job_id,
        payload_ref="work-repeated-failure")
    block(first)
    recovered = recover_orphaned_parents(store)
    assert recovered["recovered"] == 1
    retry = next(job for job in store.list_ready(50)
        if (job.governance_context or {}).get("source") == "RESEARCH_PARENT_CONTINUATION")
    block(retry)

    final = recover_orphaned_parents(store)
    assert final["recovered"] == 1
    parent = store.get(retry.job_id).governance_context["research_parent_state"]
    assert parent["terminal_condition"] is None
    assert parent["continuation_required"] is True
    continuations = [job for job in store.list_ready(50)
        if (job.governance_context or {}).get("source") == "RESEARCH_PARENT_CONTINUATION"]
    assert len(continuations) == 1
    assert continuations[0].governance_context["research_parent_action"] == "KNOWLEDGE_RECONCILIATION"


def test_worker_payload_guard_accepts_canonical_state_reached_through_release_symlink(tmp_path, monkeypatch):
    from nexus_agent_platform.job_worker_once import _is_under_nexus_runtime_root

    canonical = tmp_path / "canonical"
    runtime = canonical / "data" / "runtime"
    runtime.mkdir(parents=True)
    (canonical / "scripts").mkdir()
    (canonical / "reports").mkdir()
    payload = runtime / "nexus_mcp_jobs" / "task.json"
    payload.parent.mkdir()
    payload.write_text("{}", encoding="utf-8")
    release = tmp_path / "release"
    (release / "data").mkdir(parents=True)
    (release / "scripts").mkdir()
    (release / "reports").mkdir()
    (release / "data" / "runtime").symlink_to(runtime, target_is_directory=True)
    monkeypatch.setenv("NEXUS_REPO_ROOT", str(canonical))

    assert _is_under_nexus_runtime_root(release / "data" / "runtime" / "nexus_mcp_jobs" / "task.json")
    assert not _is_under_nexus_runtime_root(tmp_path / "outside" / "task.json")
