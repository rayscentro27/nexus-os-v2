"""Contracts for in-place R10 finalization behavior."""
from __future__ import annotations

import importlib
import json
import os
import sqlite3
import sys
from pathlib import Path


R10 = Path.home() / ".nexus/releases/nexus-research-runtime-r10-codex-native-search-20261104-r14"
R16 = Path.home() / ".nexus/releases/nexus-research-runtime-r10-automated-queue-20261104-r16"
sys.path[:0] = [str(R10), str(R16)]

service = importlib.import_module("nexus_research_r10.service")


def test_final_event_supersedes_blocked_without_duplicate_and_resets_ack(tmp_path):
    db_path = tmp_path / "outbox.sqlite3"
    with sqlite3.connect(db_path) as db:
        db.execute("CREATE TABLE completion_events(event_id TEXT PRIMARY KEY, job_id TEXT UNIQUE NOT NULL, payload_json TEXT NOT NULL, delivered_at TEXT)")
        blocked = {"event_id": "blocked-1", "event": "research.blocked", "status": "BLOCKED", "job_id": "job-x"}
        service._upsert_completion_event(db, blocked)
        db.execute("UPDATE completion_events SET delivered_at='2026-01-01T00:00:00Z'")
        completed = {"event_id": "complete-1", "event": "research.completed", "status": "COMPLETED", "job_id": "job-x"}
        service._upsert_completion_event(db, completed)
        row = db.execute("SELECT event_id,payload_json,delivered_at FROM completion_events WHERE job_id='job-x'").fetchone()
        assert row[0] == "complete-1"
        assert json.loads(row[1])["event"] == "research.completed"
        assert row[2] is None
        db.execute("UPDATE completion_events SET delivered_at='2026-01-02T00:00:00Z'")
        service._upsert_completion_event(db, completed)
        row = db.execute("SELECT count(*),delivered_at FROM completion_events").fetchone()
        assert row == (1, "2026-01-02T00:00:00Z")


def test_limited_completion_requires_exhausted_cooldowns_and_no_human_boundary():
    assert service._should_complete_with_limitations({
        "status": "PAUSED_RESUMABLE",
        "continuation_state": {"autonomous_recovery": {"cooldown_windows": 3}},
        "checkpoint": {"prior_checkpoint": {"failure_kind": "PROVIDER_ERROR"}},
    }, {"failure_kind": "PROVIDER_ERROR"})
    assert not service._should_complete_with_limitations({
        "continuation_state": {"autonomous_recovery": {"cooldown_windows": 2}},
    }, {"failure_kind": "PROVIDER_ERROR"})
    assert not service._should_complete_with_limitations({
        "continuation_state": {"autonomous_recovery": {"cooldown_windows": 9}},
    }, {"error_code": "CREDENTIAL_OR_PRIVATE_DATA_BOUNDARY"})


def test_recovery_window_metadata_is_limited_to_autonomy_caller():
    payload={"job_id":"job-x","autonomous_recovery_cooldown_windows":3}
    assert service.validate_request(payload,caller="RESEARCH_AUTONOMY",capability="research_autonomy")==payload
    try:
        service.validate_request(payload,caller="NOVA_NEXUS",capability="research")
    except PermissionError as exc:
        assert str(exc)=="AUTONOMOUS_RECOVERY_METADATA_NOT_AUTHORIZED"
    else:
        raise AssertionError("ordinary Research caller must not set recovery policy state")


def test_limitation_result_is_explicit_and_does_not_claim_unverified_evidence():
    job = {"job_id": "job-x", "project_id": "project-x", "objective": "Verify a public claim", "research_type": "GENERAL"}
    result = service._limited_result(job, {"failure_kind": "PROVIDER_ERROR", "sanitized_message": "provider unavailable"})
    assert result["status"] == "COMPLETED_WITH_LIMITATIONS"
    assert result["key_findings"] == []
    assert "no claims could be verified" in result["summary"].lower()
    assert result["recommendation"]
    assert result["evidence_limitations"]


def test_bounded_failure_finalization_persists_same_job_result_and_completion_event(tmp_path, monkeypatch):
    state_db=tmp_path/"research.sqlite3"
    bridge_db=tmp_path/"bridge.sqlite3"
    monkeypatch.setattr(service,"state_db",lambda:state_db)
    monkeypatch.setattr(service,"bridge_db",lambda:bridge_db)
    store=service.JobStore(state_db)
    job=store.create("Bounded provider failure",research_type="GENERAL",idempotency_key="same-job")
    job.update(status="PAUSED_RESUMABLE",current_stage="RECOVERY",
               continuation_state={"autonomous_recovery":{"cooldown_windows":3}})
    with service.connection(state_db) as db:
        db.execute("UPDATE jobs SET payload=?,updated_at=? WHERE job_id=?",(json.dumps(job),"2026-11-04T00:00:00+00:00",job["job_id"]))
    service._ensure_bridge_db()
    runtime=object.__new__(service.ResearchRuntime)
    runtime.store=store
    runtime._finalize_with_limitations(job["job_id"],{"failure_kind":"PROVIDER_ERROR"})
    assert store.get(job["job_id"])["status"]=="COMPLETED_WITH_LIMITATIONS"
    with service.connection(bridge_db) as db:
        result=json.loads(db.execute("SELECT result_json FROM bridge_results WHERE job_id=?",(job["job_id"],)).fetchone()[0])
        event=json.loads(db.execute("SELECT payload_json FROM completion_events WHERE job_id=?",(job["job_id"],)).fetchone()[0])
    assert result["job_id"]==job["job_id"] and result["status"]=="COMPLETED_WITH_LIMITATIONS"
    assert event["event"]=="research.completed" and event["status"]=="COMPLETED_WITH_LIMITATIONS"


def test_status_reports_authoritative_counts_and_current_latest_jobs(tmp_path, monkeypatch):
    state_db=tmp_path/"research.sqlite3"
    bridge_db=tmp_path/"bridge.sqlite3"
    monkeypatch.setattr(service,"state_db",lambda:state_db)
    monkeypatch.setattr(service,"bridge_db",lambda:bridge_db)
    store=service.JobStore(state_db)
    running=store.create("Current work",research_type="GENERAL",idempotency_key="running")
    done=store.create("Latest completed work",research_type="GENERAL",idempotency_key="done")
    running.update(status="RUNNING",started_at="2026-11-04T00:00:00Z")
    done.update(status="COMPLETED_WITH_LIMITATIONS",completed_at="2026-11-04T01:00:00Z")
    with service.connection(state_db) as db:
        for job in (running,done):
            db.execute("UPDATE jobs SET payload=?,updated_at=? WHERE job_id=?",(json.dumps(job),"2026-11-04T01:00:00Z",job["job_id"]))
    service._ensure_bridge_db()
    with service.connection(bridge_db) as db:
        db.execute("INSERT INTO bridge_jobs VALUES(?,?,?,?,?)",("req-run","fp-run","NOVA_NEXUS",running["job_id"],"2026-11-04"))
        db.execute("INSERT INTO bridge_jobs VALUES(?,?,?,?,?)",("req-done","fp-done","NOVA_NEXUS",done["job_id"],"2026-11-04"))
    runtime=object.__new__(service.ResearchRuntime)
    runtime.store=store
    response=runtime.status({})
    summary=response["queue_summary"]
    assert summary["authoritative_source"]=="R10 durable jobs state"
    assert summary["status_counts"]=={"RUNNING":1,"COMPLETED_WITH_LIMITATIONS":1}
    assert summary["running_job"]["objective"]=="Current work"
    assert summary["latest_completed_job"]["objective"]=="Latest completed work"
