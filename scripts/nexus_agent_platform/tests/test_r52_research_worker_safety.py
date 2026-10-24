from __future__ import annotations

import io
import json
import os
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit

import pytest

from nexus_agent_platform import job_worker_once, supabase_egress_guard as guard
from nexus_agent_platform.durable_jobs import DurableJobStore


def _egress_env(monkeypatch, tmp_path, job_id="job-r52-test"):
    monkeypatch.setattr(guard, "JOB_EGRESS_DIR", tmp_path / "egress")
    monkeypatch.setenv("NEXUS_DURABLE_JOB_ID", job_id)
    monkeypatch.setenv("NEXUS_DURABLE_EXECUTION_ID", "attempt-1")
    monkeypatch.setenv("NEXUS_JOB_BUDGET", json.dumps({"max_requests": 10, "max_response_bytes": 100}))


def test_case_discovery_uses_compact_state_projection(monkeypatch):
    from research import research_case_engine as engine
    calls = {}
    monkeypatch.setattr(engine.state_v2, "list_current", lambda **kwargs: calls.update(kwargs) or [])
    engine._latest_cases(include_full_payload=False)
    assert calls["include_payload"] is False
    assert calls["limit"] == 100
    assert calls["fields"] == ("memory_id", "memory_kind", "recorded_at",
        "case_id:payload->>case_id", "objective_key:payload->>objective_key",
        "status:payload->>status", "case_schema_version:payload->>case_schema_version")


def test_case_detail_can_still_request_payload_when_explicit(monkeypatch):
    from research import research_case_engine as engine
    calls = {}
    monkeypatch.setattr(engine.state_v2, "list_current", lambda **kwargs: calls.update(kwargs) or [])
    engine._latest_cases(include_full_payload=True)
    assert calls["include_payload"] is True


def test_compact_state_query_is_one_bounded_projection(monkeypatch):
    from research import research_state_v2 as state
    monkeypatch.delenv("NEXUS_CERTIFICATION_RESEARCH_STATE_ROOT", raising=False)
    requests = []
    class Supabase:
        @staticmethod
        def configured(): return True
        @staticmethod
        def rest(method, path):
            requests.append((method, path))
            return 200, [{"memory_id": f"m{index}", "memory_kind": "RESEARCH_CASE",
                          "recorded_at": "2026-10-23"} for index in range(100)]
    monkeypatch.setattr(state, "supabase", Supabase())
    fields = ("memory_id", "memory_kind", "recorded_at", "case_id:payload->>case_id",
              "objective_key:payload->>objective_key", "status:payload->>status",
              "case_schema_version:payload->>case_schema_version")
    rows = state.list_current(kinds=("RESEARCH_CASE", "PROACTIVE_RESEARCH_CASE"),
                              limit=100, include_payload=False, fields=fields)
    assert len(rows) == 100
    assert len(requests) == 1
    method, path = requests[0]
    query = parse_qs(urlsplit(path).query)
    assert method == "GET" and query["limit"] == ["100"]
    assert query["select"][0].split(",") == list(fields)


def test_large_response_read_stops_at_remaining_budget(monkeypatch, tmp_path):
    _egress_env(monkeypatch, tmp_path)
    state = {"attempts": {"attempt-1": {"request_count": 1, "response_bytes": 90}}}
    guard.JOB_EGRESS_DIR.mkdir()
    (guard.JOB_EGRESS_DIR / "job-r52-test.json").write_text(json.dumps(state))

    class Response:
        status = 200
        requested = None
        def read(self, size=-1):
            self.requested = size
            return b"x" * size

    response = Response()
    with pytest.raises(guard.JobEgressBudgetExceeded, match="JOB_RESPONSE_BYTES_LIMIT_EXCEEDED"):
        guard.read_bounded_response(response, "GET", "research_proactive_memory?select=payload&limit=4")
    assert response.requested == 11


def test_response_shape_trace_is_bounded_and_value_free(monkeypatch, tmp_path):
    _egress_env(monkeypatch, tmp_path)
    guard.preflight_request("GET", "nexus_durable_jobs?job_id=eq.job-r52-test&select=job_id,state&limit=1")
    state = guard.job_egress_snapshot("job-r52-test")
    item = state["request_trace"][-1]
    assert item["selected_columns"] == ["job_id", "state"]
    assert item["limit"] == "1"
    assert item["filters"] == [{"field": "job_id", "operator": "eq"}]
    assert "job-r52-test" not in json.dumps(item)


def test_exact_job_get_uses_narrow_projection_inside_cleanup(monkeypatch):
    from nexus_agent_platform.durable_jobs import Job, SupabaseJobStore
    store = SupabaseJobStore()
    row = asdict(Job(job_id="job-exact", department="RESEARCH", job_type="RESEARCH_INTAKE",
                     state="RUNNING", attempt_count=1, max_attempts=3, claimed_by="worker-exact"))
    requests = []
    monkeypatch.setattr(store, "_request", lambda path, *args: requests.append(path) or [row])
    with job_worker_once._worker_cleanup_scope("job-exact", "worker-exact"):
        assert store.get("job-exact").job_id == "job-exact"
    assert "job_id=eq.job-exact" in requests[0]
    assert "&limit=1" in requests[0]
    assert "select=job_id,state,attempt_count,max_attempts,claimed_by,claimed_at,lease_until,scheduled_at,receipt_ref,result_hash" in requests[0]


def test_exhausted_egress_allows_bounded_exact_job_cleanup(monkeypatch, tmp_path):
    _egress_env(monkeypatch, tmp_path, "job-cleanup")
    guard.JOB_EGRESS_DIR.mkdir()
    (guard.JOB_EGRESS_DIR / "job-cleanup.json").write_text(json.dumps({
        "attempts": {"attempt-1": {"request_count": 2, "response_bytes": 100, "budget_exceeded": True}}
    }))
    with pytest.raises(guard.JobEgressBudgetExceeded):
        guard.preflight_request("GET", "nexus_durable_jobs?job_id=eq.job-cleanup&select=job_id,state&limit=1")
    with job_worker_once._worker_cleanup_scope("job-cleanup", "worker-cleanup"):
        guard.preflight_request("GET", "nexus_durable_jobs?job_id=eq.job-cleanup&select=job_id,state&limit=1")
        guard.record_request("GET", "nexus_durable_jobs?job_id=eq.job-cleanup&select=job_id,state&limit=1", 200, 30, rows=1)
    state = guard.job_egress_snapshot("job-cleanup")
    assert state["cleanup_request_count"] == 1
    assert state["cleanup_response_bytes"] == 30


def test_exhausted_budget_allows_failed_retryable_transition(monkeypatch, tmp_path):
    from dataclasses import asdict
    from nexus_agent_platform.durable_jobs import Job, SupabaseJobStore
    _egress_env(monkeypatch, tmp_path, "job-cleanup-transition")
    guard.JOB_EGRESS_DIR.mkdir()
    (guard.JOB_EGRESS_DIR / "job-cleanup-transition.json").write_text(json.dumps({
        "attempts": {"attempt-1": {"request_count": 3, "response_bytes": 100, "budget_exceeded": True}}
    }))
    row = asdict(Job(job_id="job-cleanup-transition", department="RESEARCH", job_type="RESEARCH_INTAKE",
        state="RUNNING", attempt_count=1, max_attempts=3, claimed_by="worker-cleanup-transition"))
    requests = []
    store = SupabaseJobStore()
    def request(path, method="GET", body=None, prefer="return=minimal"):
        guard.preflight_request(method, path, body)
        guard.record_request(method, path, 200, 30, rows=1)
        requests.append((method, path, body))
        if method == "PATCH":
            row.update(body)
        return [dict(row)]
    monkeypatch.setattr(store, "_request", request)
    with job_worker_once._worker_cleanup_scope("job-cleanup-transition", "worker-cleanup-transition"):
        result = store.transition("job-cleanup-transition", "FAILED_RETRYABLE",
            worker_id="worker-cleanup-transition", error_code="EGRESS_LIMIT", error_summary="bounded")
    assert result.state == "FAILED_RETRYABLE"
    assert result.lease_until is None and result.claimed_by is None
    assert [item[0] for item in requests] == ["GET", "PATCH"]
    assert requests[-1][2]["last_error_code"] == "EGRESS_LIMIT"


def test_cleanup_scope_cannot_read_research_payload(monkeypatch, tmp_path):
    _egress_env(monkeypatch, tmp_path, "job-cleanup-deny")
    with job_worker_once._worker_cleanup_scope("job-cleanup-deny", "worker-cleanup"):
        with pytest.raises(guard.JobEgressBudgetExceeded, match="WORKER_CLEANUP_SCOPE_REJECTED"):
            guard.preflight_request("GET", "research_proactive_memory?select=payload&memory_id=eq=x&limit=1")


def test_cleanup_scope_cannot_be_entered_from_untrusted_caller():
    with pytest.raises(PermissionError, match="WORKER_CLEANUP_CALLER_NOT_AUTHORIZED"):
        with guard.worker_cleanup_scope("job-test", "worker-test"):
            pass


def test_cleanup_scope_rejects_other_job_id(monkeypatch, tmp_path):
    _egress_env(monkeypatch, tmp_path, "job-one")
    with job_worker_once._worker_cleanup_scope("job-one", "worker-one"):
        with pytest.raises(guard.JobEgressBudgetExceeded, match="WORKER_CLEANUP_SCOPE_REJECTED"):
            guard.preflight_request("GET", "nexus_durable_jobs?job_id=eq.job-two&select=job_id,state&limit=1")


def test_capacity_response_is_not_a_case_open_failure(monkeypatch):
    monkeypatch.setattr("nexus_agent_platform.research_assignment_executor.execute_assignment",
                        lambda _work: {"status": "WAITING_FOR_CAPACITY", "reason": "CAPACITY_FULL"})
    opened = job_worker_once.open_mcp_research_intake_case({"objective_id": "objective-diagnostic"})
    assert opened == {"status": "WAITING_FOR_CAPACITY", "reason": "CAPACITY_FULL",
                      "retryable": True, "objective_terminated": False, "case_created": False}


def test_capacity_wait_settles_work_item_and_releases_job_lease(monkeypatch, tmp_path):
    store = DurableJobStore(tmp_path / "capacity.sqlite")
    job = store.enqueue("RESEARCH", "RESEARCH_INTAKE", payload_ref="work-capacity",
                        max_attempts=3, governance_context={"objective_id": "objective-capacity"})
    claimed = store.claim("worker-capacity")
    assert claimed is not None
    store.transition(job.job_id, "RUNNING", worker_id="worker-capacity")
    settled = {}
    monkeypatch.setattr("nexus_agent_platform.research_work_queue.default_queue",
                        lambda: SimpleNamespace(settle=lambda *args, **kwargs: settled.update(args=args, kwargs=kwargs)))
    class Governor:
        def release(self, reservation_id):
            settled["reservation_released"] = reservation_id
    reservation = {"reservation_id": "reservation-capacity"}
    job_worker_once._settle_capacity_wait(store.get(job.job_id), "worker-capacity", store,
                                          reservation, Governor(), "CAPACITY_FULL")
    result = store.get(job.job_id)
    assert result.state == "FAILED_RETRYABLE"
    assert result.lease_until is None and result.claimed_by is None
    assert settled["args"][1] == "WAITING"
    assert settled["reservation_released"] == "reservation-capacity"


def test_waiting_capacity_worker_exit_is_successfully_handled(monkeypatch):
    import sys
    monkeypatch.setattr(job_worker_once, "run", lambda *_args: {"status": "WAITING_FOR_CAPACITY"})
    monkeypatch.setattr(job_worker_once, "default_store", lambda: object())
    monkeypatch.setattr(job_worker_once, "_lifecycle", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(sys, "argv", ["job_worker_once.py", "--job-id", "job-capacity", "--worker-id", "worker-capacity"])
    assert job_worker_once.main() == 0


def test_supervisor_captures_pid_streams_exit_and_recovers_orphan(monkeypatch, tmp_path):
    from nexus_agent_platform import job_worker_supervisor as supervisor
    monkeypatch.setattr(supervisor, "_metadata_root", lambda _job: tmp_path / "metadata")
    monkeypatch.setattr(supervisor, "_exact_exit_recovery", lambda *_: {
        "status": "FAILED_RETRYABLE", "active_slot_released": True})
    from nexus_agent_platform import worker_lifecycle
    monkeypatch.setattr(worker_lifecycle, "emit", lambda *args, **kwargs: None)
    monkeypatch.setattr(worker_lifecycle, "last_stage", lambda _path: "CASE_OPEN_START")
    class Process:
        pid = 43210
        returncode = 1
        stdout = io.BytesIO(b"worker stdout evidence\n")
        stderr = io.BytesIO(b"RuntimeError: bounded failure\n")
        def wait(self, timeout=None): return self.returncode
    monkeypatch.setattr(supervisor.subprocess, "Popen", lambda *args, **kwargs: Process())
    result = supervisor.supervise("job-supervisor-test", "worker-supervisor-test", 1, 30)
    assert result["child_pid"] == 43210
    assert result["exit_code"] == 1
    assert result["last_lifecycle_stage"] == "CASE_OPEN_START"
    assert result["recovery"]["active_slot_released"] is True
    assert (tmp_path / "metadata/attempt-1/stdout.log").read_text().strip() == "worker stdout evidence"
    assert "bounded failure" in (tmp_path / "metadata/attempt-1/stderr.log").read_text()


def test_supervisor_checks_exact_job_even_after_zero_exit(monkeypatch, tmp_path):
    from nexus_agent_platform import job_worker_supervisor as supervisor
    from nexus_agent_platform import worker_lifecycle
    monkeypatch.setattr(supervisor, "_metadata_root", lambda _job: tmp_path / "metadata-zero")
    monkeypatch.setattr(worker_lifecycle, "emit", lambda *args, **kwargs: None)
    monkeypatch.setattr(worker_lifecycle, "last_stage", lambda _path: "WORKER_PROCESS_EXIT")
    observed = []
    monkeypatch.setattr(supervisor, "_exact_exit_recovery", lambda *args: observed.append(args) or {
        "status": "FAILED_RETRYABLE", "active_slot_released": True})
    class Process:
        pid = 43211
        returncode = 0
        stdout = io.BytesIO(b"")
        stderr = io.BytesIO(b"")
        def wait(self, timeout=None): return self.returncode
    monkeypatch.setattr(supervisor.subprocess, "Popen", lambda *args, **kwargs: Process())
    result = supervisor.supervise("job-zero-active", "worker-zero-active", 1, 30)
    assert observed == [("job-zero-active", "worker-zero-active")]
    assert result["recovery"]["active_slot_released"] is True


def test_supervisor_exact_exit_recovery_releases_only_orphaned_job(monkeypatch, tmp_path):
    from nexus_agent_platform import job_worker_supervisor as supervisor
    store = DurableJobStore(tmp_path / "orphan.sqlite")
    job = store.enqueue("RESEARCH", "RESEARCH_INTAKE", max_attempts=3)
    assert store.claim("worker-orphan")
    store.transition(job.job_id, "RUNNING", worker_id="worker-orphan")
    monkeypatch.setattr("nexus_agent_platform.durable_jobs.default_store", lambda: store)
    result = supervisor._exact_exit_recovery(job.job_id, "worker-orphan")
    current = store.get(job.job_id)
    assert result["status"] == "FAILED_RETRYABLE"
    assert result["active_slot_released"] is True
    assert current.state == "FAILED_RETRYABLE" and current.attempt_count == 1
    assert current.claimed_by is None and current.lease_until is None


def test_worker_logs_are_hard_capped(monkeypatch, tmp_path):
    from nexus_agent_platform import job_worker_supervisor as supervisor
    monkeypatch.setattr(supervisor, "MAX_STREAM_BYTES", 1024)
    path = tmp_path / "stdout.log"
    supervisor._capture(io.BytesIO(b"x" * 4096), path, __import__("threading").Lock(), ())
    assert path.stat().st_size <= 1024
    assert b"OUTPUT_TRUNCATED" in path.read_bytes()


def test_lifecycle_markers_capture_last_stage_and_cap(monkeypatch, tmp_path):
    from nexus_agent_platform import worker_lifecycle as lifecycle
    monkeypatch.setenv("NEXUS_WORKER_LIFECYCLE_PATH", str(tmp_path / "life.jsonl"))
    for index in range(500):
        lifecycle.emit("job-life", f"STEP_{index}", note="x" * 400)
    target = tmp_path / "life.jsonl"
    assert target.stat().st_size <= lifecycle.MAX_LIFECYCLE_BYTES
    assert lifecycle.last_stage(target) == "STEP_499"


def test_existing_global_expired_lease_recovery_remains_available(tmp_path):
    from datetime import timedelta
    from nexus_agent_platform.durable_jobs import utcnow
    store = DurableJobStore(tmp_path / "global-recovery.sqlite")
    job = store.enqueue("RESEARCH", "RESEARCH_INTAKE", max_attempts=3)
    assert store.claim("worker-global", lease_seconds=15)
    store.transition(job.job_id, "RUNNING", worker_id="worker-global", lease_seconds=15)
    assert store.recover_expired(utcnow() + timedelta(seconds=20)) == 1
    assert store.get(job.job_id).state == "FAILED_RETRYABLE"


def test_state_v2_case_discovery_does_not_change_state_or_touch_legacy(monkeypatch):
    from research import research_case_engine as engine
    monkeypatch.setattr(engine.state_v2, "list_current", lambda **_kwargs: [])
    assert engine._latest_cases(include_full_payload=False) == []
    source = Path(engine.__file__).read_text()
    assert "research_runtime_states.jsonl" not in source


def test_phase5_contract_constants_and_protected_ids_are_not_rewritten():
    source = Path(job_worker_once.__file__).read_text()
    assert "nova_research_16a764a4c75b65d81e46" not in source
    assert "PROMISING" not in source
    assert "phase5" not in source.lower()


def test_r51_failure_reproduction_and_r52_guard_resolution():
    from certification.r52_worker_failure_reproduction import reproduce
    result = reproduce()
    assert result["r51_over_budget"] is True
    assert result["r51_cleanup_blocked"] is True
    assert result["r52_cleanup_allowed"] is True
    assert result["r52_research_after_budget_denied"] is True
    assert result["r52_failure_resolved"] is True
