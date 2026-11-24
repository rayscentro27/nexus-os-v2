from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts/systems"))
import managed_work


def _db(path: Path) -> Path:
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE receipts(receipt_id TEXT PRIMARY KEY,request_id TEXT NOT NULL,receipt_type TEXT NOT NULL,created_at TEXT NOT NULL,payload TEXT NOT NULL)")
    con.commit()
    con.close()
    return path


def test_managed_work_resolves_scope_and_records_in_existing_receipt_store(tmp_path, monkeypatch):
    db = _db(tmp_path / "systems.sqlite3")
    target = str((ROOT / "scripts/systems/workflow_integrity.py").resolve())
    scope = {"target_confirmation": "PASS", "authority_check": "PASS", "authorized_files": [target],
             "baseline_sha256": {target: "abc"}, "workspace_status_before_fingerprint": "f0", "authoritative_service": "systems-s1", "authoritative_database": "existing-db"}
    monkeypatch.setattr(managed_work, "resolve_target", lambda *args: scope)
    manifest = {"change_target_registry": {"global_do_not_patch_paths": ["legacy"], "components": {"systems": {"do_not_patch_paths": ["private"], "historical_only_paths": ["old"]}}}}
    order = managed_work.create_work_order(component="systems", objective="verify probe", requested_files=[target], requested_by="ray", environment="MAC", change_class="CLASS_1_SMALL_PATCH", execution_agent="CODEX", approval_requirement="NONE", validation={"required": True}, rollback={"path": "backup"}, manifest=manifest, db_path=db)
    assert order["status"] == "READY_FOR_AGENT"
    assert order["expected_service"] == "systems-s1"
    assert set(order["do_not_patch_paths"]) == {"private", "old", "legacy"}
    intent = managed_work.record_agent_intent(order["systems_job_id"], [target], db_path=db)
    assert intent["status"] == "EXECUTING"
    got = managed_work.get_work(order["systems_job_id"], db_path=db)
    assert got["current_status"] == "EXECUTING"


def test_managed_work_rejects_agent_target_outside_approved_paths(tmp_path, monkeypatch):
    db = _db(tmp_path / "systems.sqlite3")
    approved = str((ROOT / "scripts/systems/workflow_integrity.py").resolve())
    monkeypatch.setattr(managed_work, "resolve_target", lambda *args: {"authorized_files": [approved], "baseline_sha256": {approved: "x"}})
    manifest = {"change_target_registry": {"global_do_not_patch_paths": [], "components": {"systems": {}}}}
    order = managed_work.create_work_order(component="systems", objective="x", requested_files=[approved], requested_by="ray", environment="MAC", change_class="CLASS_1_SMALL_PATCH", execution_agent="OPENCODE", approval_requirement="NONE", validation={}, rollback={}, manifest=manifest, db_path=db)
    denied = managed_work.record_agent_intent(order["systems_job_id"], [str(ROOT / "data/runtime/research_work_queue.json")], db_path=db)
    assert denied["status"] == "INTENT_REJECTED"


def test_managed_work_target_resolution_failure_is_not_sent_to_agent(tmp_path, monkeypatch):
    db = _db(tmp_path / "systems.sqlite3")
    monkeypatch.setattr(managed_work, "resolve_target", lambda *args: (_ for _ in ()).throw(ValueError("OUT_OF_AUTHORITY_SCOPE:/secret")))
    manifest = {"change_target_registry": {"global_do_not_patch_paths": [], "components": {"systems": {}}}}
    order = managed_work.create_work_order(component="systems", objective="x", requested_files=["bad"], requested_by="ray", environment="MAC", change_class="CLASS_1_SMALL_PATCH", execution_agent="CODEX", approval_requirement="NONE", validation={}, rollback={}, manifest=manifest, db_path=db)
    assert order["status"] == "TARGET_UNRESOLVED"
    assert order["allowed_paths"] == []


def test_readonly_workflow_validation_runs_only_after_resolved_target(tmp_path, monkeypatch):
    db = _db(tmp_path / "systems.sqlite3")
    target = str((ROOT / "scripts/systems/workflow_integrity.py").resolve())
    scope = {"target_confirmation": "PASS", "authority_check": "PASS", "authorized_files": [target],
             "baseline_sha256": {target: "unchanged"}, "scope_mode": "SCOPED_TARGETS"}
    monkeypatch.setattr(managed_work, "resolve_target", lambda *args: scope)
    monkeypatch.setattr(managed_work, "post_change_check", lambda plan: {
        "post_change_drift_check": "PASS", "drift_classification": "NO_SCOPED_DRIFT",
        "prohibited_target_drift": [], "unrelated_workspace_drift": {"classification": "INFORMATIONAL_NONBLOCKING"}})
    report = {"status": "DEGRADED", "pass_count": 10, "check_count": 12, "checks": {"known": {"status": "DEGRADED"}}}
    monkeypatch.setattr(managed_work.subprocess, "run", lambda *a, **k: type("Proc", (), {
        "stdout": json.dumps(report), "stderr": "", "returncode": 2})())
    manifest = {"change_target_registry": {"global_do_not_patch_paths": [],
        "components": {"systems": {"do_not_patch_paths": [], "historical_only_paths": []}}}}
    order = managed_work.create_work_order(component="systems", objective="run bounded workflow integrity validation",
        requested_files=[target], requested_by="ray", environment="MAC", change_class="READ_ONLY_REVIEW",
        execution_agent="SYSTEMS_LOCAL", approval_requirement="NONE_READ_ONLY", validation={}, rollback={},
        manifest=manifest, db_path=db)
    assert order["status"] == "COMPLETED_WITH_LIMITATIONS"
    work = managed_work.get_work(order["systems_job_id"], db_path=db)
    assert work["current_status"] == "COMPLETED_WITH_LIMITATIONS"
    assert work["events"][-1]["result"]["workflow_report"]["check_count"] == 12
    assert work["events"][-1]["post_change_drift"]["post_change_drift_check"] == "PASS"





def test_existing_s1_technology_handoff_runs_after_resolution_and_persists(tmp_path, monkeypatch):
    db = _db(tmp_path / "systems.sqlite3")
    target = str((ROOT / "docs/systems/SYSTEMS_PHASE2_CONTROL_LAYER.md").resolve())
    resolved = {"target_confirmation": "PASS", "authority_check": "PASS",
                "authorized_files": [target], "baseline_sha256": {target: "baseline"},
                "authoritative_service": "existing Systems S1/MCP only"}
    calls = []
    def resolve(*args):
        calls.append("resolved")
        return resolved
    def execute(operation, **kwargs):
        assert calls == ["resolved"]
        assert operation == "systems.technology_handoff"
        assert kwargs["idempotency_key"].startswith("systems-handoff:sysjob_")
        assert kwargs["payload"]["technology"] == "REA MCP"
        calls.append("executed")
        return {"engine_status": "RECEIVED_NOT_EXECUTED"}
    monkeypatch.setattr(managed_work, "resolve_target", resolve)
    manifest = {"change_target_registry": {"global_do_not_patch_paths": [],
        "components": {"systems": {"do_not_patch_paths": [], "historical_only_paths": []}}}}
    order = managed_work.create_work_order(
        component="systems", objective="Record REA evaluation handoff", requested_files=[target],
        requested_by="test", environment="MAC_MINI", change_class="SAFE_TYPED_HANDOFF",
        execution_agent="SYSTEMS_LOCAL", approval_requirement="NONE_TYPED_HANDOFF",
        validation={"required": ["target_resolution"]}, rollback="idempotent handoff only",
        manifest=manifest, db_path=db, requested_action="TECHNOLOGY_HANDOFF",
        typed_action_config={"operation": "systems.technology_handoff", "payload": {"technology": "REA MCP"}},
        typed_executor=execute)
    got = managed_work.get_work(order["systems_job_id"], db_path=db)
    assert calls == ["resolved", "executed"]
    assert order["status"] == "COMPLETED"
    assert got["current_status"] == "COMPLETED"
    assert got["events"][-1]["result"]["validation"]["s1_operation"] == "PASS"
