from datetime import datetime, timezone
import json
import sqlite3
from pathlib import Path
from types import SimpleNamespace
import sys

import pytest

from nexus_agent_platform import job_worker_supervisor, stability_supervisor as ss, supabase_egress_guard as eg


def ready(**overrides):
    checks = {name: True for name in ss.STATE_V2_REQUIRED_CHECKS}
    checks.update(overrides)
    return {"schema": ss.STATE_V2_READINESS_SCHEMA,
            "active_release_id": "nexus-capability-actions-20261024-r53",
            "evidence_version": "cutover-v1",
            "verified_at": datetime.now(timezone.utc).isoformat(), "checks": checks}


@pytest.fixture(autouse=True)
def release_identity(monkeypatch):
    monkeypatch.setattr(ss, "_active_state_v2_release",
        lambda: ("nexus-capability-actions-20261024-r53", True))


def store_with_incident(tmp_path):
    store = ss.SupervisorStateStore(tmp_path / "stability.sqlite3")
    store.register_event({"event_id": "old", "failure_domain": "SYSTEMS_HOST",
                          "error_code": "HOST_IO_DEGRADED", "objective_id": None})
    return store


def test_old_incident_reconciles_only_after_fresh_healthy_evidence(tmp_path):
    store = store_with_incident(tmp_path)
    gate = ss.get_host_execution_gate(state_store=store, process_samples=[[], [], []],
        filesystem_responsive=True, governor_state="HEALTHY", state_v2_readiness=ready())
    assert gate["research_execution_allowed"]
    assert store.incident("old")["status"] == "RESOLVED"
    with sqlite3.connect(store.path) as db:
        row = db.execute("select observation_json from host_reconciliations where event_id='old'").fetchone()
    assert json.loads(row[0])["result"] == "HEALTHY"


def test_persistent_degradation_keeps_old_incident_blocking(tmp_path):
    store = store_with_incident(tmp_path)
    u = {"pid": "5", "state": "U", "command": "/usr/bin/mdworker"}
    gate = ss.get_host_execution_gate(state_store=store, process_samples=[[u], [u], [u]],
        filesystem_responsive=False, governor_state="DEGRADED", state_v2_readiness=ready())
    assert not gate["research_execution_allowed"]
    assert "PERSISTENT_HOST_IO_DEGRADED" in gate["reason_codes"]
    assert store.incident("old")["status"] == "ACTIVE"


def test_one_transient_u_sample_does_not_block(tmp_path):
    u = {"pid": "5", "state": "U", "command": "/usr/bin/cloudd"}
    gate = ss.get_host_execution_gate(state_store=store_with_incident(tmp_path),
        process_samples=[[u], [], []], filesystem_responsive=True,
        governor_state="HEALTHY", state_v2_readiness=ready())
    assert gate["research_execution_allowed"]


def test_state_v2_ready_record_supersedes_missing_old_flag(tmp_path):
    store = ss.SupervisorStateStore(tmp_path / "s.sqlite3")
    gate = ss.get_host_execution_gate(state_store=store, process_samples=[[], [], []],
        filesystem_responsive=True, governor_state="HEALTHY", state_v2_readiness=ready())
    assert store.get_flag("research_state_architecture_certified", False) is False
    assert gate["research_execution_allowed"]


def test_state_v2_failed_check_blocks(tmp_path):
    gate = ss.get_host_execution_gate(state_store=ss.SupervisorStateStore(tmp_path / "s.sqlite3"),
        process_samples=[[], [], []], filesystem_responsive=True, governor_state="HEALTHY",
        state_v2_readiness=ready(migration_applied=False))
    assert not gate["research_execution_allowed"]
    assert gate["state_v2_readiness"]["status"] == "NOT_READY"


def test_state_v2_unknown_blocks(tmp_path):
    gate = ss.get_host_execution_gate(state_store=ss.SupervisorStateStore(tmp_path / "s.sqlite3"),
        process_samples=[[], [], []], filesystem_responsive=True, governor_state="HEALTHY",
        state_v2_readiness={})
    assert not gate["research_execution_allowed"]
    assert "STATE_V2_READINESS_UNKNOWN" in gate["reason_codes"]


def test_r52_failure_shape_old_incident_and_missing_readiness_blocks(tmp_path):
    gate = ss.get_host_execution_gate(state_store=store_with_incident(tmp_path),
        process_samples=[[], [], []], filesystem_responsive=True, governor_state="HEALTHY",
        state_v2_readiness={})
    assert not gate["research_execution_allowed"]
    assert "STATE_V2_READINESS_UNKNOWN" in gate["reason_codes"]


def test_stale_readiness_is_unknown():
    record = ready()
    record["verified_at"] = "2020-01-01T00:00:00+00:00"
    assert ss.evaluate_state_v2_readiness(record)["status"] == "UNKNOWN"


def test_incomplete_readiness_is_unknown():
    assert ss.evaluate_state_v2_readiness({"schema": ss.STATE_V2_READINESS_SCHEMA,
        "verified_at": datetime.now(timezone.utc).isoformat(), "checks": {}})["status"] == "UNKNOWN"


def run_as_main(source_file, argv_file):
    namespace = {"__name__": "__main__", "worker_cleanup_scope": eg.worker_cleanup_scope}
    old_argv, old_main = sys.argv[:], sys.modules.get("__main__")
    sys.argv[:] = [str(argv_file)]
    sys.modules["__main__"] = SimpleNamespace(__file__=str(argv_file))
    try:
        code = "with worker_cleanup_scope('job_exact','worker_exact'):\n    pass\n"
        exec(compile(code, str(source_file), "exec"), namespace)
    finally:
        sys.argv[:] = old_argv
        if old_main is not None:
            sys.modules["__main__"] = old_main


def test_exact_direct_supervisor_identity_is_authorized():
    trusted = Path(eg.__file__).resolve().with_name("job_worker_supervisor.py")
    run_as_main(trusted, trusted)
    assert eg.worker_cleanup_identity() is None


def test_untrusted_main_is_denied(tmp_path):
    bad = tmp_path / "generic.py"
    bad.write_text("")
    with pytest.raises(PermissionError, match="WORKER_CLEANUP_CALLER_NOT_AUTHORIZED"):
        run_as_main(bad, bad)


def test_cleanup_limits_remain_three_requests_and_32k():
    assert eg.WORKER_CLEANUP_MAX_REQUESTS == 3
    assert eg.WORKER_CLEANUP_MAX_RESPONSE_BYTES == 32 * 1024


def test_research_read_is_outside_cleanup_allowlist():
    from nexus_agent_platform.supabase_egress_guard import _validate_cleanup_request
    with pytest.raises(RuntimeError, match="WORKER_CLEANUP_SCOPE_REJECTED"):
        _validate_cleanup_request({"job_id": "j", "worker_id": "w"}, "GET",
            "research_proactive_memory?select=payload&limit=1")


def test_cleanup_failure_metadata_is_bounded():
    try:
        raise PermissionError("WORKER_CLEANUP_CALLER_NOT_AUTHORIZED")
    except PermissionError as exc:
        value = job_worker_supervisor._cleanup_failure(exc)
    assert value["error_type"] == "PermissionError"
    assert value["caller_identity"] == "CALLER_REJECTED"
    assert value["operation"] == "EXACT_JOB_POST_EXIT_READ_OR_TRANSITION"
    assert len(value["error_summary"]) <= 300


def test_settled_blocked_job_exit_recovery_is_idempotent(monkeypatch):
    class Store:
        def get(self, job_id):
            return SimpleNamespace(state="BLOCKED", claimed_by=None)
        def transition(self, *args, **kwargs):
            raise AssertionError("settled job must not transition again")
    monkeypatch.setattr("nexus_agent_platform.durable_jobs.default_store", lambda: Store())
    result = job_worker_supervisor._exact_exit_recovery("job_exact", "worker_exact")
    assert result == {"status": "BLOCKED", "active_slot_released": True}


def test_running_job_exit_uses_exact_retry_recovery(monkeypatch):
    class Store:
        def __init__(self):
            self.transitions = []
        def get(self, job_id):
            return SimpleNamespace(state="RUNNING", claimed_by="worker_exact")
        def transition(self, *args, **kwargs):
            self.transitions.append((args, kwargs))
            return SimpleNamespace(state="FAILED_RETRYABLE", attempt_count=1)
    store = Store()
    monkeypatch.setattr("nexus_agent_platform.durable_jobs.default_store", lambda: store)
    result = job_worker_supervisor._exact_exit_recovery("job_exact", "worker_exact")
    assert result["status"] == "FAILED_RETRYABLE"
    assert result["active_slot_released"] is True
    assert store.transitions[0][0][:2] == ("job_exact", "FAILED_RETRYABLE")


def test_r52_compact_discovery_and_capacity_path_preserved():
    source = (Path(__file__).resolve().parents[2] / "research" / "research_case_engine.py").read_text()
    worker = Path(__file__).resolve().parents[1] / "job_worker_once.py"
    assert "include_payload=include_full_payload" in source
    assert '"case_id:payload->>case_id"' in source
    assert 'if case_open["status"] == "WAITING_FOR_CAPACITY"' in worker.read_text()


def test_global_expired_lease_recovery_source_preserved(tmp_path):
    from datetime import timedelta
    from nexus_agent_platform.durable_jobs import DurableJobStore
    store = DurableJobStore(tmp_path / "jobs.sqlite3")
    job = store.enqueue("RESEARCH", "RESEARCH_INTAKE", max_attempts=3)
    now = datetime.now(timezone.utc)
    claimed = store.claim("worker-global-recovery", now=now, lease_seconds=15)
    assert claimed and claimed.job_id == job.job_id
    store.transition(job.job_id, "RUNNING", worker_id="worker-global-recovery", lease_seconds=15)
    assert store.recover_expired(now + timedelta(seconds=30)) == 1
    assert store.get(job.job_id).state == "FAILED_RETRYABLE"
