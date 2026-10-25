from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from research import research_state_v2 as state
from nexus_agent_platform import supabase_egress_guard as guard


def test_timestamp_instants_normalize_and_fail_closed():
    pairs = [
        ("2026-10-25T16:12:19.290420+00:00", "2026-10-25T16:12:19.29042+00:00"),
        ("2026-10-25T16:12:19.290420Z", "2026-10-25T16:12:19.290420+00:00"),
        ("2026-10-25T09:12:19.290420-07:00", "2026-10-25T16:12:19.290420+00:00"),
    ]
    assert all(state._timestamps_equal(left, right) for left, right in pairs)
    assert not state._timestamps_equal("2026-10-25T16:12:19.290420Z", "2026-10-25T16:12:19.290421Z")
    assert not state._timestamps_equal("not-a-time", pairs[0][0])
    assert not state._timestamps_equal("2026-10-25T16:12:19", pairs[0][0])


def test_write_echo_timestamp_semantically_matches_production_failure(monkeypatch):
    class Backend:
        @staticmethod
        def configured(): return True
        @staticmethod
        def rest(*args, **kwargs):
            expected = kwargs["body"][0]["payload"]
            return 201, [{"memory_id": "case-r59", "recorded_at": "2026-10-25T16:12:19.29042+00:00",
                          "payload": expected}]
    monkeypatch.setattr(state, "_certification", lambda: False)
    monkeypatch.setattr(state, "supabase", Backend)
    assert state._upsert_current({"memory_id": "case-r59", "recorded_at":
        "2026-10-25T16:12:19.290420+00:00"})["verified"] is True


def test_write_verification_rejects_authoritative_field_mismatch(monkeypatch):
    class Backend:
        @staticmethod
        def configured(): return True
        @staticmethod
        def rest(*args, **kwargs):
            payload = dict(kwargs["body"][0]["payload"]); payload["status"] = "COMPLETE"
            return 201, [{"memory_id": "case-r59", "recorded_at": "2026-10-25T16:12:19.290420+00:00",
                          "payload": payload}]
    monkeypatch.setattr(state, "_certification", lambda: False)
    monkeypatch.setattr(state, "supabase", Backend)
    with pytest.raises(state.StateWriteFailure, match="CURRENT_STATE_WRITE_FAILED:HTTP_201"):
        state._upsert_current({"memory_id": "case-r59", "recorded_at": "2026-10-25T16:12:19.290420+00:00",
                               "status": "PROMISING"})


def test_pending_recovery_skips_matching_current_and_is_idempotent(monkeypatch, tmp_path):
    root = tmp_path / "state"
    monkeypatch.setenv("NEXUS_RESEARCH_STATE_ROOT", str(root))
    monkeypatch.setenv("NEXUS_CERTIFICATION_RESEARCH_STATE_ROOT", str(root))
    monkeypatch.delenv("NEXUS_PRODUCTION_RESEARCH_STATE_ROOT", raising=False)
    monkeypatch.setattr(state, "_certification", lambda: True)
    row = {"memory_id": "case-r59", "case_id": "case-r59", "memory_kind": "RESEARCH_CASE",
           "objective_id": "obj-r59", "project_id": "work-r59", "work_id": "work-r59", "job_id": "job-r59",
           "schema_version": "nexus.proactive-research-memory.v1", "status": "PROMISING",
           "recorded_at": "2026-10-25T16:12:19.290420+00:00"}
    event = state._event_for(row, "CASE_UPDATED")
    event_id = event["event_id"]
    expected = {**row, "last_state_event_id": event_id}
    pending = {"event_id": event_id, "current_state": row, "history_event": event}
    state._atomic_write(state._pending_path(event_id), json.dumps(pending).encode())
    monkeypatch.setattr(state, "_exact_current", lambda _identity: {
        **expected, "recorded_at": "2026-10-25T16:12:19.29042+00:00"})
    monkeypatch.setattr(state, "_upsert_current", lambda _row: pytest.fail("matching authoritative row must not be rewritten"))
    appended = []
    monkeypatch.setattr(state, "_append_event", lambda value, target_hint=None: appended.append(value["event_id"]) or "history.jsonl")
    first = state.reconcile_pending_event(event_id)
    second = state.reconcile_pending_event(event_id)
    assert first["status"] == second["status"] == "COMMITTED"
    assert appended == [event_id]
    assert not state._pending_path(event_id).exists()
    assert (root / "state_v2" / "receipts" / f"{event_id}.json").is_file()


def test_interruption_after_current_write_recovers_history_and_receipt_once(monkeypatch, tmp_path):
    root = tmp_path / "state"
    monkeypatch.setenv("NEXUS_RESEARCH_STATE_ROOT", str(root))
    monkeypatch.setenv("NEXUS_CERTIFICATION_RESEARCH_STATE_ROOT", str(root))
    monkeypatch.delenv("NEXUS_PRODUCTION_RESEARCH_STATE_ROOT", raising=False)
    monkeypatch.setattr(state, "_certification", lambda: True)
    row = {"memory_id": "case-interrupt", "case_id": "case-interrupt", "memory_kind": "RESEARCH_CASE",
           "objective_id": "obj", "project_id": "work", "work_id": "work", "job_id": "job",
           "schema_version": "nexus.proactive-research-memory.v1", "status": "PROMISING",
           "recorded_at": "2026-10-25T16:12:19.290420+00:00"}
    monkeypatch.setattr(state, "_append_event", lambda *_a, **_k: (_ for _ in ()).throw(state.HistoryPartitionFailure("simulated interruption")))
    monkeypatch.setattr(state, "_emit_failure", lambda *_a, **_k: None)
    with pytest.raises(state.HistoryPartitionFailure):
        state.persist_state(row)
    pending_path = next((root / "state_v2" / "pending").glob("*.json"))
    event_id = pending_path.stem
    with __import__("sqlite3").connect(root / "current" / "research_state_v2.sqlite3") as db:
        assert db.execute("select count(*) from current_state").fetchone()[0] == 1
    appends = []
    monkeypatch.setattr(state, "_append_event", lambda event, target_hint=None: appends.append(event["event_id"]) or "history.jsonl")
    state.reconcile_pending_event(event_id)
    state.reconcile_pending_event(event_id)
    assert appends == [event_id]
    assert not pending_path.exists()
    assert (root / "state_v2" / "receipts" / f"{event_id}.json").is_file()


def _invoke_as_packaged_worker(*, argv_tail, main_path, code_path, env_values):
    import os
    expected = Path(guard.__file__).resolve().with_name("job_worker_once.py")
    old_argv, old_main = sys.argv[:], sys.modules.get("__main__")
    keys = ("NEXUS_DURABLE_JOB_ID", "NEXUS_WORKER_ID", "NEXUS_JOB_ATTEMPT_COUNT")
    previous = {key: os.environ.get(key) for key in keys}
    try:
        os.environ.update(env_values)
        sys.argv[:] = [str(expected), *argv_tail]
        sys.modules["__main__"] = SimpleNamespace(__file__=str(main_path))
        namespace = {"__name__": "__main__", "worker_cleanup_scope": guard.worker_cleanup_scope}
        code = "with worker_cleanup_scope('job-r59','worker-r59', attempt=3):\n    pass\n"
        exec(compile(code, str(code_path), "exec"), namespace)
        return True
    finally:
        for key, value in previous.items():
            if value is None: os.environ.pop(key, None)
            else: os.environ[key] = value
        sys.argv[:] = old_argv
        if old_main is not None: sys.modules["__main__"] = old_main


def test_exact_packaged_main_worker_identity_is_authorized():
    expected = Path(guard.__file__).resolve().with_name("job_worker_once.py")
    args = ["--job-id", "job-r59", "--worker-id", "worker-r59", "--attempt", "3"]
    env = {"NEXUS_DURABLE_JOB_ID": "job-r59", "NEXUS_WORKER_ID": "worker-r59", "NEXUS_JOB_ATTEMPT_COUNT": "3"}
    assert _invoke_as_packaged_worker(argv_tail=args, main_path=expected, code_path=expected, env_values=env)


@pytest.mark.parametrize("bad", ["different_script", "different_job", "different_attempt", "different_root", "forged_main"])
def test_packaged_worker_cleanup_rejects_mismatched_identity(tmp_path, bad):
    expected = Path(guard.__file__).resolve().with_name("job_worker_once.py")
    args = ["--job-id", "job-r59", "--worker-id", "worker-r59", "--attempt", "3"]
    env = {"NEXUS_DURABLE_JOB_ID": "job-r59", "NEXUS_WORKER_ID": "worker-r59", "NEXUS_JOB_ATTEMPT_COUNT": "3"}
    main = expected; code = expected
    if bad in {"different_script", "different_root", "forged_main"}:
        fake = tmp_path / "job_worker_once.py"; fake.write_text("")
        if bad == "different_script": code = fake
        elif bad == "different_root": main = fake
        else: main = code = fake
    if bad == "different_job": args[1] = "job-other"
    if bad == "different_attempt": args[-1] = "2"
    with pytest.raises(PermissionError, match="WORKER_CLEANUP_CALLER_NOT_AUTHORIZED"):
        _invoke_as_packaged_worker(argv_tail=args, main_path=main, code_path=code, env_values=env)


def test_arbitrary_main_is_denied(tmp_path):
    fake = tmp_path / "arbitrary.py"; fake.write_text("")
    with pytest.raises(PermissionError, match="WORKER_CLEANUP_CALLER_NOT_AUTHORIZED"):
        _invoke_as_packaged_worker(argv_tail=["--job-id", "job-r59", "--worker-id", "worker-r59", "--attempt", "3"],
            main_path=fake, code_path=fake, env_values={"NEXUS_DURABLE_JOB_ID": "job-r59",
            "NEXUS_WORKER_ID": "worker-r59", "NEXUS_JOB_ATTEMPT_COUNT": "3"})


def test_direct_main_worker_failure_cleans_exact_attempt_and_reservation(monkeypatch, tmp_path):
    import os
    from nexus_agent_platform import job_worker_once

    job_id, worker_id, attempt = "job-r59-direct", "worker-r59-direct", 2
    worker_script = Path(job_worker_once.__file__).resolve()
    class Store:
        job = SimpleNamespace(job_id=job_id, state="RUNNING", attempt_count=attempt,
                              claimed_by=worker_id, lease_until="lease")
        def get(self, identity):
            assert identity == job_id
            return self.job
        def transition(self, identity, state_name, **kwargs):
            assert identity == job_id and kwargs.get("worker_id") == worker_id
            self.job.state = state_name
            self.job.lease_until = None
            self.job.claimed_by = None
            self.job.last_error_code = kwargs.get("error_code")
            return self.job
    class Governor:
        calls = []
        def reconcile(self, reservation_id, usage): self.calls.append((reservation_id, usage))
    store, governor = Store(), Governor()
    monkeypatch.setattr(job_worker_once, "default_store", lambda: store)
    monkeypatch.setattr(job_worker_once, "_lifecycle", lambda *_a, **_k: None)
    monkeypatch.setattr("nexus_agent_platform.supabase_egress_guard.job_egress_snapshot",
                        lambda _identity: {"request_count": 2, "response_bytes": 128})
    def fail_after_reservation(*_args):
        job_worker_once.ACTIVE_RESERVATIONS[job_id] = (
            governor, "reservation-r59-direct", {"request_count": 1, "response_bytes": 64})
        raise RuntimeError("controlled retryable failure")
    monkeypatch.setattr(job_worker_once, "run", fail_after_reservation)
    old_argv, old_main = sys.argv[:], sys.modules.get("__main__")
    previous_job = os.environ.get("NEXUS_DURABLE_JOB_ID")
    os.environ["NEXUS_DURABLE_JOB_ID"] = job_id
    sys.argv[:] = [str(worker_script), "--job-id", job_id, "--worker-id", worker_id, "--attempt", str(attempt)]
    sys.modules["__main__"] = SimpleNamespace(__file__=str(worker_script))
    try:
        namespace = {"__name__": "__main__", "worker_main": job_worker_once.main}
        exec(compile("worker_main()", str(worker_script), "exec"), namespace)
    finally:
        sys.argv[:] = old_argv
        if old_main is not None: sys.modules["__main__"] = old_main
        if previous_job is None: os.environ.pop("NEXUS_DURABLE_JOB_ID", None)
        else: os.environ["NEXUS_DURABLE_JOB_ID"] = previous_job
    assert store.job.state == "FAILED_RETRYABLE"
    assert store.job.lease_until is None and store.job.claimed_by is None
    assert governor.calls == [("reservation-r59-direct", {"requests": 1, "bytes": 64, "cost": 0})]
    assert job_id not in job_worker_once.ACTIVE_RESERVATIONS
