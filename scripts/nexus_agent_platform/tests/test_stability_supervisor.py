from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from types import SimpleNamespace

from nexus_agent_platform import stability_supervisor as supervisor
from nexus_agent_platform.durable_jobs import DurableJobStore


PROC = {"pid": "41001", "ppid": "41000", "state": "U", "elapsed": "00:00:02",
        "cpu": "0.0", "rss": "20480", "command": "/release/scripts/nexus_agent_platform/dispatcher_once.py"}


def _fast_capture(monkeypatch, tmp_path):
    monkeypatch.setattr(supervisor, "diagnostics_root", lambda: tmp_path)
    monkeypatch.setattr(supervisor, "_wait_channel", lambda pid, deadline: ("vn_read", None))
    monkeypatch.setattr(supervisor, "_dispatcher_context", lambda root, deadline: {
        "available": True, "last_dispatcher_action": "DISPATCH_TICK",
        "queue": {"ready": 2, "running": 0}, "started_this_tick": 0,
        "lease_cleanup_active": False, "resource_check_active": False,
        "receipt_write_active": False})
    monkeypatch.setattr(supervisor, "_bounded_lsof", lambda pid, deadline: (["nexus-os-v2-canonical/data/x.log"], None))
    monkeypatch.setattr(supervisor, "_kernel_log", lambda deadline: (["kernel: bounded synthetic event"], None))


def test_one_u_occurrence_writes_one_artifact_and_deduplicates(monkeypatch, tmp_path):
    _fast_capture(monkeypatch, tmp_path)
    when = datetime(2026, 10, 22, 20, 0, tzinfo=timezone.utc)
    first = supervisor.capture_uninterruptible_process(PROC, [PROC], root=tmp_path, now=when)
    second = supervisor.capture_uninterruptible_process(PROC, [PROC], root=tmp_path, now=when)
    files = list(tmp_path.glob("dispatcher_u_*.json"))
    assert first is not None and second is None
    assert len(files) == 1
    data = json.loads(files[0].read_text())
    assert data["failure_type"] == "PROCESS_UNINTERRUPTIBLE_IO"
    assert data["recovery_event"]["objective_id"] is None
    assert data["recovery_event"]["objective_termination_authorized"] is False


def test_u_occurrence_artifact_is_bounded(monkeypatch, tmp_path):
    _fast_capture(monkeypatch, tmp_path)
    monkeypatch.setattr(supervisor, "_bounded_lsof", lambda pid, deadline: (["x" * 500 for _ in range(300)], None))
    proc = {**PROC, "pid": "41002"}
    result = supervisor.capture_uninterruptible_process(proc, [proc], root=tmp_path)
    artifact = json.loads(open(result["artifact"], encoding="utf-8").read())
    assert len(artifact["open_nexus_files"]) == supervisor.MAX_OPEN_FILES_RECORDED
    assert len(open(result["artifact"], "rb").read()) <= supervisor.MAX_ARTIFACT_BYTES


def test_partial_evidence_survives_later_probe_failure(monkeypatch, tmp_path):
    _fast_capture(monkeypatch, tmp_path)
    monkeypatch.setattr(supervisor, "_bounded_lsof", lambda pid, deadline: (_ for _ in ()).throw(RuntimeError("synthetic exit")))
    proc = {**PROC, "pid": "41003"}
    try:
        supervisor.capture_uninterruptible_process(proc, [proc], root=tmp_path)
    except RuntimeError:
        pass
    files = list(tmp_path.glob("dispatcher_u_*.json"))
    assert len(files) == 1
    partial = json.loads(files[0].read_text())
    assert partial["process"]["pid"] == "41003"
    assert "recovery_event" in partial


def test_supervisor_routes_required_synthetic_incidents():
    codes = {
        "PROCESS_UNINTERRUPTIBLE_IO": "PAUSE_HEAVY_WORK",
        "READY_TOO_LONG": "RETRY_AUTHORIZED_ACTION",
        "WORKER_INTERRUPTED": "RETRY_AUTHORIZED_ACTION",
        "PROVIDER_UNAVAILABLE": "WAIT_FOR_RESOURCE",
        "CURRENT_STATE_LOOKUP_FAILED": "CREATE_SYSTEMS_RECOVERY_JOB",
        "HOST_IO_DEGRADED": "PAUSE_HEAVY_WORK",
    }
    for code, expected in codes.items():
        assert expected in supervisor.supervisor_decision({"error_code": code})


def test_recovery_job_is_idempotent_and_preserves_original_lineage(tmp_path):
    store = supervisor.SupervisorStateStore(tmp_path / "supervisor.sqlite3")
    event = {"event_id": "event-123", "error_code": "HOST_IO_DEGRADED",
             "failure_domain": "SYSTEMS_HOST", "objective_id": "objective-original",
             "project_id": "project-original", "job_id": "job_original",
             "evidence_references": ["/diagnostics/event.json"]}
    first = supervisor.route_recovery_event(event, store)
    second = supervisor.route_recovery_event(event, store)
    assert first["recovery_job_id"] == second["recovery_job_id"]
    assert first["original_objective_id"] == "objective-original"
    assert first["original_job_id"] == "job_original"
    assert first["recovery_job_plan_state"] == "PLANNED"
    assert first["recovery_job_state"] == "BLOCKED_FOR_EXECUTION"
    assert store.blocks_for_event("event-123")[0]["project_id"] == "project-original"


def test_forbidden_actions_never_appear():
    for code in ("PROCESS_UNINTERRUPTIBLE_IO", "LEASE_EXPIRED", "PROVIDER_UNAVAILABLE", "EXPECTED_ARTIFACT_MISSING"):
        actions = supervisor.supervisor_decision({"error_code": code})
        assert "TERMINATE_OBJECTIVE" not in actions
        assert "UNAPPROVED_SPEND" not in actions
        assert "AUTOMATIC_RESTART" not in actions


def test_resume_requires_all_recovery_gates_and_keeps_objective_id():
    event = {"objective_id": "objective-1"}
    evidence = {key: True for key in (
        "no_persistent_u_state", "host_health_gate_pass", "current_state_lookups_bounded",
        "full_ledger_scan_absent", "state_v2_focused_tests_pass", "mcp_healthy",
        "dispatcher_healthy", "runtime_contract_pass")}
    assert supervisor.resume_action(event, {}) == "WAIT_FOR_RESOURCE"
    assert supervisor.resume_action(event, evidence) == "RESUME_BLOCKED_OBJECTIVE"
    assert supervisor.resume_action({"objective_id": None}, evidence) == "REQUEST_RAY_APPROVAL"


def test_process_monitor_ignores_non_nexus_u_rows(monkeypatch):
    monkeypatch.setattr(supervisor, "_read_process_table", lambda: ([{"pid": "7", "ppid": "1", "state": "U", "elapsed": "00:00:01", "cpu": "0", "rss": "1", "command": "rg --files /tmp"}], None))
    assert supervisor.monitor_uninterruptible_processes() == []


def test_diagnostics_are_outside_release_and_research_ledger(tmp_path, monkeypatch):
    monkeypatch.setattr(supervisor, "diagnostics_root", lambda: tmp_path / "data" / "diagnostics" / "runtime_events")
    assert "research_runtime_states.jsonl" not in str(supervisor.diagnostics_root())
    assert "releases" not in str(supervisor.diagnostics_root())


def test_host_event_without_objective_blocks_heavy_work(tmp_path):
    store = supervisor.SupervisorStateStore(tmp_path / "supervisor.sqlite3")
    event = {"event_id": "global-host", "error_code": "HOST_IO_DEGRADED",
             "failure_domain": "SYSTEMS_HOST", "objective_id": None}
    store.register_event(event)
    gate = supervisor.get_host_execution_gate(state_store=store, process_rows=[],
                                               filesystem_responsive=True, governor_state="HEALTHY")
    assert gate["host_health"] == "BLOCKED"
    assert gate["heavy_work_allowed"] is False
    assert gate["research_execution_allowed"] is False


def test_blocked_by_relationship_is_durable(tmp_path):
    path = tmp_path / "supervisor.sqlite3"
    store = supervisor.SupervisorStateStore(path)
    event = {"event_id": "host-event", "error_code": "HOST_IO_DEGRADED",
             "failure_domain": "SYSTEMS_HOST", "objective_id": None}
    store.register_event(event)
    store.add_dependent_objective("host-event", objective_id="obj", project_id="proj",
                                  job_id="job", case_id="case", department="RESEARCH")
    reopened = supervisor.SupervisorStateStore(path)
    block = reopened.blocks_for_event("host-event")[0]
    assert (block["objective_id"], block["project_id"], block["job_id"], block["case_id"]) == ("obj", "proj", "job", "case")
    assert block["status"] == "BLOCKED"
    assert block["relationship_type"] == "BLOCKED_BY"


def test_recovery_certification_requires_all_host_gates():
    assert not supervisor.recovery_verified({"mcp_healthy": True, "dispatcher_healthy": True})
    assert supervisor.recovery_verified({key: True for key in (
        "no_persistent_u_state", "host_health_gate_pass", "mcp_healthy",
        "dispatcher_healthy", "runtime_contract_pass")})


def test_recovery_certification_requires_state_v2_for_research():
    evidence = {key: True for key in ("no_persistent_u_state", "host_health_gate_pass",
        "mcp_healthy", "dispatcher_healthy", "runtime_contract_pass")}
    assert not supervisor.recovery_verified(evidence, research_required=True)


def test_resume_uses_same_job_and_never_duplicates_completed_work(tmp_path):
    store = supervisor.SupervisorStateStore(tmp_path / "supervisor.sqlite3")
    event = {"event_id": "host-e", "error_code": "HOST_IO_DEGRADED",
             "failure_domain": "SYSTEMS_HOST", "objective_id": None}
    store.register_event(event)
    store.add_dependent_objective("host-e", objective_id="obj", project_id="proj",
                                  job_id="job", department="SYSTEMS")
    class Jobs:
        def get(self, job_id):
            return SimpleNamespace(state="COMPLETED", governance_context={
                "owner_objective_id": "obj", "project_id": "proj"})
    evidence = {key: True for key in ("no_persistent_u_state", "host_health_gate_pass",
        "mcp_healthy", "dispatcher_healthy", "runtime_contract_pass")}
    result = supervisor.certify_recovery("host-e", evidence, state_store=store, job_store=Jobs())
    assert result["verified"] is True
    assert result["resumed"]["obj"] == "COMPLETED_NO_REGENERATION"


def test_global_host_incident_is_idempotent_and_recovery_job_is_blocked(tmp_path):
    store = supervisor.SupervisorStateStore(tmp_path / "supervisor.sqlite3")
    event = {"event_id": "global", "error_code": "HOST_IO_DEGRADED",
             "failure_domain": "SYSTEMS_HOST", "objective_id": None}
    one = store.register_event(event, title="Research State Architecture v2 / Host I/O Stabilization")
    two = store.register_event(event, title="Research State Architecture v2 / Host I/O Stabilization")
    assert one["recovery_job_id"] == two["recovery_job_id"]
    assert one["execution_state"] == "BLOCKED_FOR_EXECUTION"


def test_research_gate_remains_closed_without_state_v2_certification(tmp_path):
    store = supervisor.SupervisorStateStore(tmp_path / "supervisor.sqlite3")
    gate = supervisor.get_host_execution_gate(state_store=store, process_rows=[],
                                               filesystem_responsive=True, governor_state="HEALTHY")
    assert gate["research_execution_allowed"] is False


def test_current_host_incident_event_shape_and_stable_identity(tmp_path, monkeypatch):
    monkeypatch.setattr(supervisor, "diagnostics_root", lambda: tmp_path / "diagnostics" / "runtime_events")
    store = supervisor.SupervisorStateStore(tmp_path / "diagnostics" / "stability.sqlite3")
    first = supervisor.create_current_host_incident(state_store=store)
    second = supervisor.create_current_host_incident(state_store=store)
    assert first["event_id"] == second["event_id"] == supervisor.CURRENT_HOST_INCIDENT_ID
    assert first["recovery_job_id"] == second["recovery_job_id"]
    artifact = json.loads(open(first["artifact"], encoding="utf-8").read())
    assert artifact["FAILURE_DOMAIN"] == "SYSTEMS_HOST"
    assert artifact["HOST_EXECUTION_GATE"] == "BLOCKED"
