from types import SimpleNamespace

from nexus_agent_platform import durable_jobs
from nexus_agent_platform.durable_jobs import Job, JobError, SupabaseJobStore


def test_resource_guard_defers_under_memory_swap_or_load_pressure(monkeypatch):
    fake = SimpleNamespace(
        virtual_memory=lambda: SimpleNamespace(available=1_000, percent=92),
        swap_memory=lambda: SimpleNamespace(percent=51),
        getloadavg=lambda: (0.1, 0.1, 0.1),
        cpu_count=lambda: 8,
        process_iter=lambda attrs: [],
        Error=OSError,
    )
    monkeypatch.setitem(__import__("sys").modules, "psutil", fake)
    monkeypatch.delenv("NEXUS_RESOURCE_PRESSURE", raising=False)
    assert durable_jobs.resource_pressure()


def test_resource_guard_fails_closed_when_telemetry_is_missing(monkeypatch):
    monkeypatch.setitem(__import__("sys").modules, "psutil", None)
    monkeypatch.delenv("NEXUS_RESOURCE_PRESSURE", raising=False)
    assert durable_jobs.resource_pressure()


def test_supabase_worker_start_uses_claimed_state_compare_and_set(monkeypatch):
    store = object.__new__(SupabaseJobStore)
    current = Job(job_id="job-1", department="SYSTEMS", job_type="TEST", state="CLAIMED", claimed_by="worker-1")
    monkeypatch.setattr(store, "get", lambda job_id: current)
    calls = []
    monkeypatch.setattr(store, "_request", lambda path, *args: calls.append(path) or [])
    try:
        store.transition("job-1", "RUNNING", worker_id="worker-1")
    except JobError as exc:
        assert str(exc) == "JOB_TRANSITION_REJECTED"
    else:
        raise AssertionError("a missing CAS update must reject the second worker")
    assert "claimed_by=eq.worker-1&state=eq.CLAIMED" in calls[0]
