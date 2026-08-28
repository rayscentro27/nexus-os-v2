"""Canonical, bounded broker for approved repository engineering tasks.

This module is deliberately a broker, not a new coding-agent subsystem.  It
uses the existing Builder registry (which in turn uses the canonical worker
supervisor adapters), keeps one persisted lease for a repair, and treats
capacity/authentication failures as retryable worker conditions.
"""
from __future__ import annotations

import json
import os
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from nexus_agent_platform.builders.runtime import BuildTaskSpec, build_coding_worker_registry, run_builder_task

ROOT = Path(__file__).resolve().parents[3]
POOL_PATH = ROOT / "reports/runtime/voice_repair_worker_pool_latest.json"
LEASE_PATH = ROOT / "reports/runtime/voice_repair_worker_lease.json"
HANDOFF_PATH = ROOT / "reports/runtime/voice_repair_handoffs.jsonl"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write(path: Path, value: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as fh:
        json.dump(value, fh, indent=2, sort_keys=True)
        fh.write("\n")
        temporary = Path(fh.name)
    os.replace(temporary, path)


def _read(path: Path) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return {}


def _append(path: Path, value: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(value, sort_keys=True) + "\n")


def worker_matrix(task: BuildTaskSpec) -> list[Dict[str, Any]]:
    rows = []
    for worker in build_coding_worker_registry():
        health = worker.health_check()
        state = health.get("classification") or ("AVAILABLE" if worker.available else "UNAVAILABLE")
        if state == "UNAVAILABLE" and "timed out" in str(health.get("reason", "")).lower():
            state = "BUSY"
        rows.append({
            "worker": worker.worker_id,
            "installed": bool(health.get("installed", worker.installed)),
            "adapter_exists": worker._execute_fn is not None,  # internal registry fact, not a new contract
            "isolated_worktree": bool(worker.supports_worktrees),
            "repo_edit": bool(worker.supports_repo_edit),
            "tests": bool(worker.supports_tests),
            "state": state,
            "available": bool(worker.available),
            "reason": worker.availability_reason or health.get("reason", ""),
            "capabilities": list(worker.capabilities),
        })
    _write(POOL_PATH, {"checked_at": _now(), "required": ["repo_edit", "tests", "isolated_worktree"], "workers": rows})
    return rows


def _eligible(row: Dict[str, Any]) -> bool:
    return row.get("state") == "AVAILABLE" and row.get("adapter_exists") and row.get("repo_edit") and row.get("tests") and row.get("isolated_worktree")


def acquire_lease(*, repair_id: str, work_order_id: str, run_id: str, worker: str, engineering_run_id: str) -> Dict[str, Any]:
    existing = _read(LEASE_PATH)
    if existing.get("active") and existing.get("work_order_id") != work_order_id:
        raise RuntimeError("another repair already owns the engineering worker lease")
    if existing.get("active") and existing.get("work_order_id") == work_order_id and existing.get("worker") != worker:
        raise RuntimeError("repair already has an active worker lease")
    lease = {"active": True, "lease_id": existing.get("lease_id") or f"lease-{uuid.uuid4().hex[:12]}",
             "repair_id": repair_id, "work_order_id": work_order_id, "run_id": run_id,
             "worker": worker, "engineering_run_id": engineering_run_id, "acquired_at": existing.get("acquired_at") or _now()}
    _write(LEASE_PATH, lease)
    return lease


def release_lease(work_order_id: str) -> None:
    existing = _read(LEASE_PATH)
    if existing.get("work_order_id") == work_order_id:
        _write(LEASE_PATH, {"active": False, "released_at": _now(), "previous": existing})


def run_voice_task(*, task: BuildTaskSpec, repair_id: str, work_order_id: str, run_id: str,
                   engineering_run_id: str, previous_worker: Optional[str] = None) -> Dict[str, Any]:
    rows = worker_matrix(task)
    selected = next((row for row in rows if row["worker"] == "codex" and _eligible(row)), None)
    if selected is None:
        selected = next((row for row in rows if row["worker"] == "opencode" and _eligible(row)), None)
    if selected is None:
        return {"_execution_status": "WAITING_WORKER", "state": "WAITING_WORKER", "failure": "NO_CERTIFIED_WORKER_AVAILABLE", "worker_matrix": rows}

    worker = selected["worker"]
    lease = acquire_lease(repair_id=repair_id, work_order_id=work_order_id, run_id=run_id, worker=worker, engineering_run_id=engineering_run_id)
    if previous_worker and previous_worker != worker:
        _append(HANDOFF_PATH, {"repair_id": repair_id, "work_order_id": work_order_id, "previous_worker": previous_worker,
                               "previous_worker_state": "BUSY", "new_worker": worker, "reason": "CODEX_BUSY",
                               "handoff_at": _now(), "checkpoint_sha": task.metadata.get("source_commit"),
                               "authority_scope": [repair_id], "attempt_number": task.metadata.get("attempt_number", 1)})
    workers = build_coding_worker_registry()
    chosen = next(worker_obj for worker_obj in workers if worker_obj.worker_id == worker)
    result = run_builder_task(task, [chosen], max_retries=0)
    report = result.get("worker_report") or {}
    if result.get("status") != "pass" and (report.get("status") in {"UNAVAILABLE", "worker_unavailable"} or report.get("failure_class") in {"UNAVAILABLE", "AUTH_BLOCKED", "RATE_LIMITED"}):
        release_lease(work_order_id)
        return {"_execution_status": "WAITING_WORKER", "state": "WAITING_WORKER", "failure": report.get("failure_class", "WORKER_CAPACITY"),
                "worker": worker, "worker_matrix": rows, "worker_result": result, "lease": lease}
    release_lease(work_order_id)
    return {"_execution_status": "PATCH_READY" if result.get("status") == "pass" else "REPAIR_FAILED",
            "state": "ENGINEERING" if result.get("status") != "pass" else "PATCH_READY", "worker": worker,
            "worker_matrix": rows, "worker_result": result, "lease": lease}
