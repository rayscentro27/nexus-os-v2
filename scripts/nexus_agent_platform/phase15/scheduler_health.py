"""Persistent health record for the canonical Phase 15 scheduler."""
from __future__ import annotations

import json
import os
import socket
import subprocess
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from nexus_agent_platform.phase15.common import ROOT, atomic_write_json, utc_now

SCHEDULER_LABEL = "com.nexus.continuous-loop"
HEALTH_PATH = ROOT / "reports" / "phase16a" / "scheduler_health.json"
CADENCE_SECONDS = 3600
REGISTERED_LOOPS = [
    "open_source_scout_loop",
    "research_intake_loop",
    "revenue_opportunity_loop",
    "seo_opportunity_loop",
]
LEGACY_LABELS = {
    "com.nexus.activation.continuous-loop",
    "com.nexus.continuous-ops-daily",
}


def _git_commit() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        ).stdout.strip()
    except Exception:  # noqa: BLE001
        return "UNKNOWN"


def _launchd_labels() -> set[str]:
    try:
        output = subprocess.run(["launchctl", "list"], capture_output=True, text=True, timeout=5).stdout
    except Exception:  # noqa: BLE001
        return set()
    return {parts[2] for line in output.splitlines() if len(parts := line.split()) >= 3}


def _next_dispatch(now: str) -> str:
    parsed = datetime.fromisoformat(now.replace("Z", "+00:00"))
    return (parsed + timedelta(seconds=CADENCE_SECONDS)).isoformat()


def _load() -> Dict[str, Any]:
    try:
        return json.loads(HEALTH_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return {}


def _base(now: str, instance: str, prior: Dict[str, Any]) -> Dict[str, Any]:
    labels = _launchd_labels()
    return {
        "status": prior.get("status", "STARTING"),
        "scheduler_label": SCHEDULER_LABEL,
        "scheduler_instance": instance,
        "host": socket.gethostname(),
        "started_at": prior.get("started_at", now),
        "last_heartbeat": now,
        "last_dispatch": prior.get("last_dispatch"),
        "next_dispatch": _next_dispatch(now),
        "successful_dispatches": int(prior.get("successful_dispatches", 0)),
        "failed_dispatches": int(prior.get("failed_dispatches", 0)),
        "registered_loops": REGISTERED_LOOPS,
        "duplicate_detected": bool(labels & LEGACY_LABELS),
        "last_exit_code": prior.get("last_exit_code"),
        "updated_at": now,
        "git_commit": _git_commit(),
        "cadence_seconds": CADENCE_SECONDS,
        "health_path": str(HEALTH_PATH.relative_to(ROOT)),
    }


def begin_dispatch() -> Dict[str, Any]:
    now = utc_now()
    instance = f"{SCHEDULER_LABEL}:{uuid.uuid4().hex}"
    health = _base(now, instance, _load())
    health["status"] = "RUNNING"
    health["last_dispatch"] = now
    atomic_write_json(HEALTH_PATH, health)
    return {"scheduler_instance": instance, "started_at": now}


def complete_dispatch(context: Dict[str, Any], *, success: bool, error: Optional[str] = None) -> Dict[str, Any]:
    now = utc_now()
    health = _base(now, str(context.get("scheduler_instance", "UNKNOWN")), _load())
    health["status"] = "HEALTHY" if success else "FAIL"
    health["last_dispatch"] = health.get("last_dispatch") or context.get("started_at")
    health["last_heartbeat"] = now
    health["last_exit_code"] = 0 if success else 1
    health["successful_dispatches"] += 1 if success else 0
    health["failed_dispatches"] += 0 if success else 1
    if error:
        health["last_error"] = str(error)[:500]
    atomic_write_json(HEALTH_PATH, health)
    return health
