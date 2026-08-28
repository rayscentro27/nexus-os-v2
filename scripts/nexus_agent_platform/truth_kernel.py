"""Small local operational-truth kernel.

The kernel records claims and evidence; it does not execute business actions.
Definitions are descriptive and can never make a process operational by
themselves. SQLite keeps the state durable, inspectable, and independent of
Supabase, Hermes, Oracle, and external models.
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import subprocess
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB_PATH = ROOT / "data/runtime/nexus_operational_truth.db"
REALNESS = {"REAL", "SAFE_SYNTHETIC", "DRY_RUN", "SIMULATION"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class TruthKernel:
    def __init__(self, db_path: str | Path = DEFAULT_DB_PATH):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _init_db(self) -> None:
        with self._connect() as db:
            db.executescript(
                """
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS process_definitions (
                    process_id TEXT PRIMARY KEY,
                    definition_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS process_runs (
                    run_id TEXT PRIMARY KEY,
                    process_id TEXT NOT NULL,
                    trigger_type TEXT NOT NULL,
                    trigger_id TEXT,
                    git_sha TEXT,
                    requested_at TEXT NOT NULL,
                    started_at TEXT,
                    completed_at TEXT,
                    execution_host TEXT,
                    entrypoint TEXT,
                    process_started_at TEXT,
                    heartbeat_at TEXT,
                    heartbeat_interval_seconds INTEGER,
                    last_successful_cycle_at TEXT,
                    cycle_count INTEGER,
                    shutdown_reason TEXT,
                    expected_running INTEGER,
                    scheduler_supervision TEXT,
                    authority_result TEXT,
                    dependency_result TEXT,
                    exit_status TEXT,
                    exit_code INTEGER,
                    output_artifacts TEXT,
                    output_hashes TEXT,
                    side_effect_expected TEXT,
                    side_effect_observed TEXT,
                    verification_result TEXT,
                    freshness_result TEXT,
                    recovery_used INTEGER NOT NULL DEFAULT 0,
                    final_state TEXT,
                    FOREIGN KEY(process_id) REFERENCES process_definitions(process_id)
                );
                CREATE TABLE IF NOT EXISTS evidence (
                    evidence_id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    evidence_type TEXT NOT NULL,
                    source TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    artifact TEXT,
                    artifact_hash TEXT,
                    scope TEXT,
                    real_or_simulated TEXT NOT NULL,
                    verification_status TEXT NOT NULL,
                    FOREIGN KEY(run_id) REFERENCES process_runs(run_id)
                );
                CREATE TABLE IF NOT EXISTS human_gates (
                    gate_id TEXT PRIMARY KEY,
                    run_id TEXT,
                    work_package_id TEXT,
                    exact_action TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    risk TEXT NOT NULL,
                    authority_requested TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT,
                    status TEXT NOT NULL,
                    approved_by TEXT,
                    approved_at TEXT
                );
                """
            )
            existing = {row[1] for row in db.execute("PRAGMA table_info(process_runs)").fetchall()}
            additions = {
                "process_started_at": "TEXT",
                "heartbeat_at": "TEXT",
                "heartbeat_interval_seconds": "INTEGER",
                "last_successful_cycle_at": "TEXT",
                "cycle_count": "INTEGER",
                "shutdown_reason": "TEXT",
                "expected_running": "INTEGER",
                "scheduler_supervision": "TEXT",
            }
            for name, sql_type in additions.items():
                if name not in existing:
                    db.execute(f"ALTER TABLE process_runs ADD COLUMN {name} {sql_type}")

    def register_process(self, definition: dict[str, Any]) -> dict[str, Any]:
        required = {"process_id", "canonical_entrypoint", "purpose", "execution_mode"}
        missing = required - set(definition)
        if missing:
            raise ValueError(f"process definition missing: {sorted(missing)}")
        if definition["execution_mode"] not in {"RUN_ONCE", "ON_DEMAND", "SCHEDULED", "CONTINUOUS"}:
            raise ValueError("invalid execution_mode")
        now = utc_now()
        with self._connect() as db:
            db.execute(
                "INSERT INTO process_definitions VALUES (?, ?, ?, ?) "
                "ON CONFLICT(process_id) DO UPDATE SET definition_json=excluded.definition_json, updated_at=excluded.updated_at",
                (definition["process_id"], _json(definition), now, now),
            )
        return definition

    def start_run(self, process_id: str, *, trigger_type: str, trigger_id: str | None = None,
                  git_sha: str | None = None, entrypoint: str | None = None,
                  execution_host: str | None = None, requested_at: str | None = None) -> str:
        definition = self.get_process_definition(process_id)
        if not definition:
            raise KeyError(f"unknown process: {process_id}")
        run_id = f"run_{uuid.uuid4().hex}"
        with self._connect() as db:
            db.execute(
                "INSERT INTO process_runs (run_id, process_id, trigger_type, trigger_id, git_sha, requested_at, execution_host, entrypoint, process_started_at, heartbeat_at, heartbeat_interval_seconds, last_successful_cycle_at, cycle_count, shutdown_reason, expected_running, scheduler_supervision) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (run_id, process_id, trigger_type, trigger_id, git_sha, requested_at or utc_now(), execution_host or os.uname().nodename, entrypoint or definition["canonical_entrypoint"], None, None, None, None, 0, None, int(bool(definition.get("expected_running", False))), _json(definition.get("scheduler_supervision", {}))),
            )
        return run_id

    def record_heartbeat(self, run_id: str, *, heartbeat_at: str | None = None,
                         cycle_count: int | None = None, successful_cycle_at: str | None = None) -> None:
        self._update_run(run_id, heartbeat_at=heartbeat_at or utc_now(), cycle_count=cycle_count,
                         last_successful_cycle_at=successful_cycle_at or heartbeat_at or utc_now())

    def record_dependency_result(self, run_id: str, result: dict[str, Any]) -> None:
        self._update_run(run_id, dependency_result=_json(result))

    def record_authority_result(self, run_id: str, result: dict[str, Any]) -> None:
        self._update_run(run_id, authority_result=_json(result))

    def record_output(self, run_id: str, artifacts: Iterable[str | Path]) -> dict[str, str]:
        hashes: dict[str, str] = {}
        for artifact in artifacts:
            path = Path(artifact)
            if path.exists() and path.is_file():
                hashes[str(path)] = _hash_file(path)
        self._update_run(run_id, output_artifacts=_json(list(hashes)), output_hashes=_json(hashes))
        return hashes

    def record_evidence(self, run_id: str, *, evidence_type: str, source: str,
                        artifact: str | None = None, scope: str | None = None,
                        real_or_simulated: str = "REAL",
                        verification_status: str = "VERIFIED",
                        artifact_hash: str | None = None) -> str:
        if real_or_simulated not in REALNESS:
            raise ValueError("invalid evidence realness")
        evidence_id = f"evidence_{uuid.uuid4().hex}"
        with self._connect() as db:
            db.execute(
                "INSERT INTO evidence VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (evidence_id, run_id, evidence_type, source, utc_now(), artifact, artifact_hash, scope, real_or_simulated, verification_status),
            )
        return evidence_id

    def complete_run(self, run_id: str, *, exit_status: str, exit_code: int,
                     verification_result: dict[str, Any], freshness_result: dict[str, Any],
                     output_artifacts: Iterable[str | Path] = (),
                     side_effect_expected: dict[str, Any] | None = None,
                     side_effect_observed: dict[str, Any] | None = None,
                     recovery_used: bool = False, completed_at: str | None = None) -> str:
        run = self.get_run(run_id)
        if not run:
            raise KeyError(run_id)
        hashes = self.record_output(run_id, output_artifacts)
        evidence = self.get_evidence(run_id)
        real_verified = any(e["real_or_simulated"] == "REAL" and e["verification_status"] == "VERIFIED" for e in evidence)
        output_verified = verification_result.get("output_verified") is True
        fresh = freshness_result.get("fresh") is True
        verified = exit_code == 0 and output_verified and fresh and real_verified and verification_result.get("verification_failed") is not True
        final_state = "SUCCEEDED_VERIFIED" if verified else ("FAILED" if exit_code != 0 or verification_result.get("verification_failed") is True else "SUCCEEDED_UNVERIFIED")
        completed = completed_at or utc_now()
        self._update_run(run_id, completed_at=completed, exit_status=exit_status, exit_code=exit_code,
                         output_artifacts=_json(list(hashes)), output_hashes=_json(hashes),
                         side_effect_expected=_json(side_effect_expected or {}), side_effect_observed=_json(side_effect_observed or {}),
                         verification_result=_json(verification_result), freshness_result=_json(freshness_result),
                         recovery_used=int(recovery_used), final_state=final_state)
        return final_state

    def verify_freshness(self, created_at: str, *, max_age_seconds: int) -> dict[str, Any]:
        parsed = datetime.fromisoformat(created_at)
        age = (datetime.now(timezone.utc) - parsed).total_seconds()
        return {"fresh": age <= max_age_seconds, "age_seconds": round(age, 3), "max_age_seconds": max_age_seconds}

    def derive_process_state(self, process_id: str, *, now: str | None = None) -> str:
        definition = self.get_process_definition(process_id)
        if not definition:
            return "NOT_CONFIGURED"
        runs = self._runs_for(process_id)
        if not runs:
            if definition.get("execution_mode") == "CONTINUOUS" and definition.get("expected_running"):
                return "STALE"
            if definition.get("dependencies_ready") is False:
                return "BLOCKED_DEPENDENCY"
            return "READY" if definition.get("enabled", True) else "NOT_CONFIGURED"
        latest = runs[0]
        if latest["completed_at"] is None:
            return "RUNNING"
        if latest["final_state"] == "FAILED":
            return "FAILED"
        if latest["final_state"] != "SUCCEEDED_VERIFIED":
            if latest["final_state"] == "SUCCEEDED_UNVERIFIED" and json.loads(latest["freshness_result"] or "{}").get("fresh") is False:
                return "STALE"
            return "SUCCEEDED_UNVERIFIED"
        freshness = json.loads(latest["freshness_result"] or "{}")
        if freshness.get("fresh") is not True:
            return "STALE"
        return "SUCCEEDED_VERIFIED"

    def get_process_status(self, process_id: str) -> dict[str, Any]:
        definition = self.get_process_definition(process_id)
        runs = self._runs_for(process_id)
        latest = dict(runs[0]) if runs else None
        return {"process_id": process_id, "state": self.derive_process_state(process_id), "definition": definition, "latest_run": latest}

    def get_process_definition(self, process_id: str) -> dict[str, Any] | None:
        with self._connect() as db:
            row = db.execute("SELECT definition_json FROM process_definitions WHERE process_id=?", (process_id,)).fetchone()
        return json.loads(row[0]) if row else None

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        with self._connect() as db:
            row = db.execute("SELECT * FROM process_runs WHERE run_id=?", (run_id,)).fetchone()
        return dict(row) if row else None

    def get_evidence(self, run_id: str) -> list[dict[str, Any]]:
        with self._connect() as db:
            return [dict(row) for row in db.execute("SELECT * FROM evidence WHERE run_id=? ORDER BY created_at", (run_id,)).fetchall()]

    def create_human_gate(self, *, gate_id: str, exact_action: str, reason: str, risk: str,
                          authority_requested: str, run_id: str | None = None,
                          work_package_id: str | None = None, expires_at: str | None = None) -> str:
        with self._connect() as db:
            db.execute("INSERT INTO human_gates VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                       (gate_id, run_id, work_package_id, exact_action, reason, risk, authority_requested, utc_now(), expires_at, "PENDING", None, None))
        return gate_id

    def approve_human_gate(self, gate_id: str, action: str, *, approved_by: str) -> bool:
        with self._connect() as db:
            row = db.execute("SELECT exact_action, status FROM human_gates WHERE gate_id=?", (gate_id,)).fetchone()
            if not row or row[1] != "PENDING" or row[0] != action:
                return False
            db.execute("UPDATE human_gates SET status='APPROVED', approved_by=?, approved_at=? WHERE gate_id=?", (approved_by, utc_now(), gate_id))
            return True

    def _update_run(self, run_id: str, **values: Any) -> None:
        if not values:
            return
        fields = ", ".join(f"{key}=?" for key in values)
        with self._connect() as db:
            db.execute(f"UPDATE process_runs SET {fields} WHERE run_id=?", (*values.values(), run_id))

    def _runs_for(self, process_id: str) -> list[sqlite3.Row]:
        with self._connect() as db:
            return db.execute("SELECT * FROM process_runs WHERE process_id=? ORDER BY COALESCE(started_at, requested_at) DESC", (process_id,)).fetchall()


DAILY_MONITOR_DEFINITION = {
    "process_id": "daily_monitor",
    "canonical_entrypoint": "scripts/operations/nexus_daily_monitor.py",
    "purpose": "Bounded diagnostic report generation; business health is a separate measured result.",
    "execution_mode": "RUN_ONCE",
    "dependencies": ["process registry", "runtime report inputs"],
    "authority_contract": {"authority": "internal_read_only", "external_mutation": False},
    "input_contract": {"source": "local runtime artifacts"},
    "output_contract": {"artifacts": ["reports/runtime/nexus_daily_monitor_latest.json", "reports/runtime/nexus_daily_monitor_latest.md"]},
    "side_effect_contract": {"allowed": ["write diagnostic reports"], "mutations": 0},
    "verification_contract": {"fresh_report_required": True, "business_health_inferred": False},
    "receipt_contract": {"kernel_receipt": True},
    "freshness_contract": {"max_age_seconds": 300},
    "health_contract": {"report_health_is_not_execution_health": True},
    "recovery_contract": {"policy": "report and review"},
    "enabled": True,
    "dependencies_ready": True,
}


def current_git_sha() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True, timeout=5).stdout.strip()
    except Exception:
        return "UNKNOWN"
