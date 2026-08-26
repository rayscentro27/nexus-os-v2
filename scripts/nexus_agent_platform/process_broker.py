"""Truthful process status adapter; registry presence is never running proof."""
from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = ROOT / "data/operations/nexus_process_registry.json"


def _age(value: Any) -> float | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return max(0.0, (datetime.now(timezone.utc) - dt).total_seconds())
    except ValueError:
        return None


def _pid_alive(pid: Any) -> bool:
    if not isinstance(pid, int) or pid <= 0:
        return False
    try:
        result = subprocess.run(["ps", "-p", str(pid), "-o", "pid="], capture_output=True, text=True, timeout=5, check=False)
        return str(pid) in result.stdout.split()
    except (OSError, subprocess.SubprocessError):
        return False


def read_processes(path: Path = REGISTRY_PATH, *, heartbeat_max_seconds: int = 300) -> Dict[str, Any]:
    try:
        rows = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        rows = []
    if not isinstance(rows, list):
        rows = []
    result = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        age = _age(row.get("last_heartbeat") or row.get("heartbeat_at"))
        alive = _pid_alive(row.get("pid"))
        proven = alive and age is not None and age <= heartbeat_max_seconds
        result.append({"process_id": row.get("process_id"), "owner": row.get("owner"),
                       "job_id": row.get("job_id"), "pid": row.get("pid"),
                       "heartbeat_age_seconds": age, "runtime_state": "RUNNING" if proven else "UNKNOWN",
                       "health": "HEALTHY" if proven else "STALE", "proof_refs": row.get("proof_refs", [])})
    return {"schema_version": "nexus.process-status.v1", "generated_at": datetime.now(timezone.utc).isoformat(),
            "processes": result, "running_count": sum(p["runtime_state"] == "RUNNING" for p in result)}
