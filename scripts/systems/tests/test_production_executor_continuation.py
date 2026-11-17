from __future__ import annotations

import hashlib
import importlib
import json
import sqlite3
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


S1_RELEASE = Path.home() / ".nexus/releases/nexus-systems-engine-s1-20261028"
sys.path.insert(0, str(S1_RELEASE))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
s1 = importlib.import_module("systems_engine_s1_batch_d.service")
managed = importlib.import_module("managed_work")
tick = importlib.import_module("maintenance_tick")


def test_upgrade_executor_uses_fixed_homebrew_argv_and_validates_fixture(monkeypatch, tmp_path):
    manifest = json.loads((Path(__file__).resolve().parents[3] / "docs/systems/NEXUS_LIVING_MANIFEST.v1.json").read_text())
    manifest["systems_managed_work"]["action_targets"]["UPGRADE"]["typed_action"]["payload"]["current_version"] = "1.18.9"
    manifest["systems_managed_work"]["action_targets"]["UPGRADE"]["typed_action"]["payload"]["approved_target_version"] = "1.19.0"
    monkeypatch.setattr(s1, "_systems_manifest", lambda: manifest)
    spec = manifest["systems_managed_work"]["action_targets"]["UPGRADE"]["typed_action"]["payload"]
    payload = {**spec, "dry_run": False}
    calls = []

    def runner(argv, **kwargs):
        calls.append(argv)
        if argv[0] == "/usr/local/bin/opencode" and argv[-1] == "--version":
            version = "1.18.9" if len(calls) == 1 else "1.19.0"
            return SimpleNamespace(returncode=0, stdout=version, stderr="")
        if argv[:4] == ["/usr/local/bin/brew", "info", "--json=v2", "--formula"]:
            return SimpleNamespace(returncode=0, stdout=json.dumps({"formulae": [{"versions": {"stable": "1.19.0"}}]}), stderr="")
        if argv[:4] == ["/usr/local/bin/brew", "upgrade", "--formula", "opencode"]:
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        raise AssertionError("unregistered subprocess argv")

    result = s1._run_registered_upgrade(payload, runner=runner, backup_root=tmp_path / "backup")
    assert result["status"] == "VERIFIED"
    assert result["mutation_performed"] is True
    assert [x[:4] for x in calls if x[0].endswith("brew")] == [
        ["/usr/local/bin/brew", "info", "--json=v2", "--formula"],
        ["/usr/local/bin/brew", "upgrade", "--formula", "opencode"],
    ]
    assert (tmp_path / "backup/opencode.jsonc").is_file()


def test_upgrade_rejects_unregistered_target(monkeypatch):
    monkeypatch.setattr(s1, "_systems_manifest", lambda: {"systems_managed_work": {"action_targets": {}}})
    with pytest.raises(ValueError, match="UPGRADE_TARGET_NOT_REGISTERED"):
        s1._run_registered_upgrade({})


def test_cleanup_deletes_only_exact_registered_fixture(tmp_path):
    target = tmp_path / "safe.tmp"
    target.write_text("fixture")
    result = s1._run_registered_cleanup({"targets": [{"target_id": "fixture", "classification": "SAFE_DELETE", "disposition": "DELETE"}]},
        target_registry=[{"target_id": "fixture", "classification": "SAFE_DELETE", "disposition": "DELETE", "path": str(target)}])
    assert result["status"] == "VERIFIED"
    assert not target.exists()


def test_cleanup_rejects_unsafe_registry_classification(tmp_path):
    target = tmp_path / "keep.tmp"
    target.write_text("fixture")
    with pytest.raises(PermissionError, match="CLEANUP_TARGET_NOT_REGISTERED_SAFE"):
        s1._run_registered_cleanup({"targets": [{"target_id": "fixture", "classification": "SAFE_DELETE", "disposition": "DELETE"}]},
            target_registry=[{"target_id": "fixture", "classification": "UNKNOWN", "disposition": "DELETE", "path": str(target)}])
    assert target.exists()


def test_restart_registered_healthy_service_is_noop_and_unregistered_is_rejected(monkeypatch):
    manifest = {"systems_execution_registry": {"restart_safe_services": [{"target_id": "fixture",
        "service_id": "com.nexus.fixture", "restart_safe": True, "target_environment": "MAC_MINI",
        "rollback_reference": "fixture-backup", "interval_seconds": 300}]}}
    monkeypatch.setattr(s1, "_systems_manifest", lambda: manifest)
    payload = {"restart_target_id": "fixture", "target_environment": "MAC_MINI", "rollback_reference": "fixture-backup"}
    runner = lambda argv, **kw: SimpleNamespace(returncode=0, stdout="run interval = 300 seconds\nlast exit code = 0\n", stderr="")
    result = s1._registered_restart(payload, "com.nexus.fixture", runner=runner)
    assert result["status"] == "NO_RESTART_REQUIRED"
    with pytest.raises(PermissionError, match="RESTART_TARGET_NOT_REGISTERED_SAFE"):
        s1._registered_restart({**payload, "restart_target_id": "unregistered"}, "com.nexus.fixture", runner=runner)


def test_restart_registered_fixture_runs_and_waits_for_persisted_health(monkeypatch, tmp_path):
    manifest = {"systems_execution_registry": {"restart_safe_services": [{"target_id": "fixture",
        "service_id": "com.nexus.fixture", "restart_safe": True, "target_environment": "MAC_MINI",
        "rollback_reference": "fixture-backup", "interval_seconds": 300}]}}
    monkeypatch.setattr(s1, "_systems_manifest", lambda: manifest)
    state_db = tmp_path / "systems.sqlite3"
    with sqlite3.connect(state_db) as con:
        con.execute("CREATE TABLE receipts(receipt_id TEXT,request_id TEXT,receipt_type TEXT,created_at TEXT,payload TEXT)")
    prints = 0

    def runner(argv, **kw):
        nonlocal prints
        if argv[:2] == ["launchctl", "print"]:
            prints += 1
            code = 1 if prints == 1 else 0
            return SimpleNamespace(returncode=0, stdout=f"run interval = 300 seconds\nlast exit code = {code}\n", stderr="")
        if argv[:2] == ["launchctl", "kickstart"]:
            with sqlite3.connect(state_db) as con:
                con.execute("INSERT INTO receipts VALUES('r','r','SYSTEMS_MAINTENANCE_TICK','now','{}')")
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        raise AssertionError("unexpected service command")

    result = s1._registered_restart({"restart_target_id": "fixture", "target_environment": "MAC_MINI",
        "rollback_reference": "fixture-backup"}, "com.nexus.fixture", runner=runner, sleep=lambda _: None, state_db=state_db)
    assert result["status"] == "VERIFIED"
    assert result["validation"]["maintenance_receipt_created"] is True


def test_rollback_restores_only_exact_registered_fixture(monkeypatch, tmp_path):
    target, backup = tmp_path / "tick.py", tmp_path / "tick.backup.py"
    target.write_text("value = 'new'\n")
    backup.write_text("value = 'old'\n")
    manifest_path = tmp_path / "manifest.json"
    entry = {"path": str(target), "sha256": hashlib.sha256(target.read_bytes()).hexdigest()}
    manifest = {"systems_execution_registry": {"rollback_contracts": [{"target_id": "tick", "backup_reference": "exact-backup",
        "target_path": str(target), "backup_path": str(backup), "current_sha256": entry["sha256"],
        "backup_sha256": hashlib.sha256(backup.read_bytes()).hexdigest()}]},
        "systems_current_production_hashes": {"files": [entry]}}
    manifest_path.write_text(json.dumps(manifest))
    monkeypatch.setattr(s1, "_systems_manifest_path", lambda: manifest_path)
    result = s1._registered_rollback({"rollback_target_id": "tick", "backup_reference": "exact-backup"}, backup_root=tmp_path / "rollback-receipt")
    assert result["status"] == "VERIFIED"
    assert target.read_text() == "value = 'old'\n"
    assert result["validation"]["compile"] == "PASS"


def _retry_db(path: Path, attempt: int, *, retryable: bool = True, due: bool = True) -> str:
    job_id = "sysjob_" + "a" * 24
    with sqlite3.connect(path) as con:
        con.execute("CREATE TABLE receipts(receipt_id TEXT,request_id TEXT,receipt_type TEXT,created_at TEXT,payload TEXT)")
        order = {"systems_job_id": job_id, "requested_action": "BOUNDED_UPGRADE", "typed_action_config": {"operation": "systems.upgrade_component", "payload": {}},
                 "allowed_paths": ["/tmp/example"], "authoritative_target": {"component": "systems"},
                 "maintenance_classification": "AUTONOMOUS_BOUNDED"}
        managed._append(con, job_id, "SYSTEMS_MANAGED_JOB", order)
        not_before = "2000-01-01T00:00:00+00:00" if due else "2999-01-01T00:00:00+00:00"
        managed._append(con, job_id, "SYSTEMS_MANAGED_JOB_EVENT", {"status": "FAILED_RECOVERABLE", "retry": {
            "attempt": attempt, "max_attempts": managed.SYSTEMS_RETRY_LIMIT, "retryable": retryable, "not_before": not_before}})
    return job_id


def test_same_job_retry_reuses_id_and_is_bounded(monkeypatch, tmp_path):
    db = tmp_path / "systems.sqlite3"
    job_id = _retry_db(db, 1)
    seen = []
    monkeypatch.setattr(managed, "_run_typed_s1_maintenance", lambda order, **kw: seen.append(order) or {"completion": "COMPLETED"})
    result = managed.resume_recoverable_work(job_id, typed_executor=lambda *a, **k: {}, db_path=db)
    assert result["completion"] == "COMPLETED"
    assert seen[0]["systems_job_id"] == job_id
    assert seen[0]["_systems_attempt_number"] == 2


def test_retry_not_due_or_nonretryable_is_not_dispatched(monkeypatch, tmp_path):
    db = tmp_path / "systems.sqlite3"
    job_id = _retry_db(db, 1, due=False)
    monkeypatch.setattr(managed, "_run_typed_s1_maintenance", lambda *a, **k: pytest.fail("must not dispatch"))
    assert managed.resume_recoverable_work(job_id, typed_executor=lambda *a, **k: {}, db_path=db)["status"] == "NOT_DUE"


def test_retry_limit_is_enforced(monkeypatch, tmp_path):
    db = tmp_path / "systems.sqlite3"
    job_id = _retry_db(db, managed.SYSTEMS_RETRY_LIMIT)
    monkeypatch.setattr(managed, "_run_typed_s1_maintenance", lambda *a, **k: pytest.fail("must not dispatch"))
    assert managed.resume_recoverable_work(job_id, typed_executor=lambda *a, **k: {}, db_path=db)["status"] == "RETRY_LIMIT_REACHED"


def test_ray_approval_boundary_is_never_auto_retried(monkeypatch, tmp_path):
    db = tmp_path / "systems.sqlite3"
    job_id = _retry_db(db, 1)
    with sqlite3.connect(db) as con:
        rows = managed._records(con, job_id)
        order = rows[0]
        order["maintenance_classification"] = "RAY_APPROVAL_REQUIRED"
        con.execute("UPDATE receipts SET payload=? WHERE request_id=? AND receipt_type='SYSTEMS_MANAGED_JOB'",
                    (json.dumps(order), job_id))
    monkeypatch.setattr(managed, "_run_typed_s1_maintenance", lambda *a, **k: pytest.fail("boundary must not retry"))
    assert managed.resume_recoverable_work(job_id, typed_executor=lambda *a, **k: {}, db_path=db)["status"] == "GOVERNANCE_BOUNDARY_NOT_AUTORETRIED"


def test_maintenance_tick_routes_same_job_retry_through_existing_bridge(monkeypatch, tmp_path):
    bridge = tmp_path / "existing_bridge.py"
    bridge.write_text("def request(operation, **kwargs): return {'engine_status':'VERIFIED'}\n")
    monkeypatch.setattr(tick, "ACTIVE_NEXUS_MCP_RELEASE", bridge)
    monkeypatch.setattr(tick, "_eligible_same_job_retry", lambda: {"systems_job_id": "sysjob_" + "b" * 24})
    monkeypatch.setattr(tick.subprocess, "run", lambda *a, **k: SimpleNamespace(returncode=0, stdout="fixture-token"))
    seen = {}

    def resume(job_id, **kwargs):
        seen["job_id"] = job_id
        seen["executor"] = kwargs["typed_executor"]("systems.upgrade_component")
        return {"completion": "COMPLETED"}

    monkeypatch.setattr(managed, "resume_recoverable_work", resume)
    result = tick._resume_one_same_job()
    assert result == {"status": "COMPLETED", "same_job": True, "attempted": True}
    assert seen["job_id"] == "sysjob_" + "b" * 24
    assert seen["executor"]["engine_status"] == "VERIFIED"


def test_ready_readonly_job_is_atomically_claimed_and_completed_same_job(monkeypatch, tmp_path):
    db = tmp_path / "systems.sqlite3"
    with sqlite3.connect(db) as con:
        con.execute("CREATE TABLE receipts(receipt_id TEXT,request_id TEXT,receipt_type TEXT,created_at TEXT,payload TEXT)")
        job_id = "sysjob_" + "c" * 24
        target = str(managed._READONLY_SYSTEMS_VALIDATION[1])
        managed._append(con, job_id, "SYSTEMS_MANAGED_JOB", {
            "systems_job_id": job_id, "requested_by": "NOVA_VIA_NEXUS_MCP",
            "component": "systems", "change_class": "READ_ONLY_REVIEW", "objective": "bounded validation",
            "execution_agent": "SYSTEMS_LOCAL", "approval_requirement": "NONE_READ_ONLY",
            "status": "READY_FOR_AGENT", "allowed_paths": [target],
            "authoritative_target": {"authority_check": "PASS", "authorized_files": [target]},
        })
    fresh = {"authority_check": "PASS", "authorized_files": [target], "baseline_sha256": {target: "same"}}
    monkeypatch.setattr(managed, "resolve_target", lambda *args: fresh)
    monkeypatch.setattr(managed, "post_change_check", lambda _plan: {"post_change_drift_check": "PASS"})

    def execute(order, *, db_path):
        assert order["execution_agent"] == "SYSTEMS_LOCAL"
        assert order["systems_job_id"] == job_id
        result = {"summary": "bounded validation passed", "health_result": "PASS", "validation_pass": True}
        completed = managed.complete_work(job_id, order["authoritative_target"], result, db_path=db_path)
        return {"completion": completed["status"], "result": result}

    monkeypatch.setattr(managed, "_run_bounded_readonly", execute)
    assert managed.next_ready_readonly_job(db_path=db) == job_id
    first = managed.resume_ready_readonly_work(job_id, db_path=db)
    second = managed.resume_ready_readonly_work(job_id, db_path=db)
    assert first == {"status": "COMPLETED", "same_job": True, "attempted": True, "ai_usage": "NONE"}
    assert second["status"] == "NOT_ELIGIBLE"
    work = managed.get_work(job_id, db_path=db)
    assert work["current_status"] == "COMPLETED"
    assert [event.get("stage") for event in work["events"] if event.get("stage")] == ["READY_JOB_CLAIM"]
    assert len({row[0] for row in sqlite3.connect(db).execute(
        "SELECT request_id FROM receipts WHERE receipt_type LIKE 'SYSTEMS_MANAGED_JOB%'")}) == 1


def test_ready_selector_rejects_unresolved_or_mutative_jobs(tmp_path):
    db = tmp_path / "systems.sqlite3"
    with sqlite3.connect(db) as con:
        con.execute("CREATE TABLE receipts(receipt_id TEXT,request_id TEXT,receipt_type TEXT,created_at TEXT,payload TEXT)")
        target = str(managed._READONLY_SYSTEMS_VALIDATION[1])
        for suffix, action, authority in (("d", "VALIDATION", "FAIL"), ("e", "SAFE_CLEANUP", "PASS")):
            job_id = "sysjob_" + suffix * 24
            managed._append(con, job_id, "SYSTEMS_MANAGED_JOB", {
                "systems_job_id": job_id, "requested_action": action, "component": "systems",
                "execution_agent": "SYSTEMS_LOCAL", "approval_requirement": "NONE_READ_ONLY",
                "status": "READY_FOR_AGENT", "allowed_paths": [target],
                "authoritative_target": {"authority_check": authority},
            })
    assert managed.next_ready_readonly_job(db_path=db) is None


def test_readonly_health_evidence_reconciles_direct_and_stored_tick(tmp_path, monkeypatch):
    db = tmp_path / "systems.sqlite3"
    with sqlite3.connect(db) as con:
        con.execute("CREATE TABLE receipts(receipt_id TEXT,request_id TEXT,receipt_type TEXT,created_at TEXT,payload TEXT)")
        con.execute("INSERT INTO receipts VALUES(?,?,?,?,?)", ("r", "r", "SYSTEMS_MAINTENANCE_TICK", "now",
            json.dumps({"checks": {"systems_s1": {"status": "PASS"}}})))

    class Response:
        status = 200
        def __enter__(self): return self
        def __exit__(self, *_): return None
        def read(self, _size): return b'{"status":"HEALTHY"}'

    monkeypatch.setattr(managed, "urlopen", lambda *a, **kw: Response())
    evidence = managed._read_only_health_evidence({"checked_at": "2026-11-04T00:00:00Z",
        "checks": {"r10_http_health": {"status": "PASS"}}}, db)
    assert evidence["systems_s1_health"]["status"] == "PASS"
    assert evidence["research_r10_health"]["status"] == "PASS"
    assert evidence["stored_vs_direct_health_reconciliation"]["status"] == "PASS"
    assert all(item.get("observed_at") for item in evidence["findings"])


def test_tick_prefers_ready_local_validation_without_bridge_or_ai(monkeypatch):
    job_id = "sysjob_" + "d" * 24
    monkeypatch.setattr(tick, "_eligible_ready_job", lambda: {"systems_job_id": job_id})
    monkeypatch.setattr(managed, "resume_ready_readonly_work", lambda received, **kw: {
        "status": "COMPLETED", "same_job": True, "attempted": received == job_id, "ai_usage": "NONE"})
    monkeypatch.setattr(tick.subprocess, "run", lambda *a, **kw: pytest.fail("READY validation must not use credentials/AI"))
    assert tick._resume_one_same_job() == {"status": "COMPLETED", "same_job": True,
        "attempted": True, "ai_usage": "NONE"}


def test_s1_idempotency_cache_replays_completed_mutation_without_repeating():
    db = sqlite3.connect(":memory:")
    request = {"operation": "systems.safe_cleanup", "idempotency_key": "same-job-key",
               "payload": {"target_scope": "registered-fixture"}, "request_id": "job-fixture"}
    calls = []
    action = lambda: calls.append("run") or {"status": "VERIFIED", "receipt": {"receipt_id": "receipt-fixture"},
                                              "data": {"mutation_performed": True}}
    first = s1._dispatch_idempotent_typed_action(db, request, action)
    second = s1._dispatch_idempotent_typed_action(db, request, action)
    assert first == second
    assert calls == ["run"]


def test_s1_idempotency_cache_releases_only_explicit_no_mutation_transient_failure():
    db = sqlite3.connect(":memory:")
    request = {"operation": "systems.upgrade_component", "idempotency_key": "same-job-retry",
               "payload": {"authoritative_target": "opencode-cli-homebrew"}, "request_id": "job-fixture"}
    calls = []
    action = lambda: calls.append("run") or {"status": "FAILED_RECOVERABLE", "data": {
        "mutation_performed": False, "retry_evidence": "TRANSIENT_RESOURCE_BUSY"}}
    s1._dispatch_idempotent_typed_action(db, request, action)
    s1._dispatch_idempotent_typed_action(db, request, action)
    assert calls == ["run", "run"]


def test_s1_idempotency_cache_fails_closed_on_ambiguous_in_progress_action():
    db = sqlite3.connect(":memory:")
    request = {"operation": "systems.safe_cleanup", "idempotency_key": "ambiguous-job-key",
               "payload": {"target_scope": "registered-fixture"}, "request_id": "job-fixture"}

    def failed_action():
        raise RuntimeError("outcome lost")

    with pytest.raises(RuntimeError):
        s1._dispatch_idempotent_typed_action(db, request, failed_action)
    with pytest.raises(RuntimeError, match="ACTION_OUTCOME_UNKNOWN_REQUIRES_RECOVERY"):
        s1._dispatch_idempotent_typed_action(db, request, lambda: pytest.fail("must not replay"))
