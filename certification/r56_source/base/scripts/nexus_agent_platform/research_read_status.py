"""Bounded, read-only Research Room status projection for the MCP surface."""

from __future__ import annotations

import json
import threading
import time
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
QUEUE_PATH = ROOT / "data/runtime/research_work_queue.json"
MAX_QUEUE_BYTES = 16 * 1024 * 1024
HARD_TIMEOUT_SECONDS = 9.0
ACTIVE_STATUSES = {"QUEUED", "IN_PROGRESS", "BLOCKED_EXTERNAL", "FAILED_RETRYABLE", "MONITORING"}


def _read_existing_queue() -> dict[str, Any]:
    """Read one bounded durable file; never instantiate the mutating queue API."""
    size = QUEUE_PATH.stat().st_size
    if size > MAX_QUEUE_BYTES:
        raise ValueError("queue_source_exceeds_read_limit")
    with QUEUE_PATH.open("rb") as source:
        raw = source.read(MAX_QUEUE_BYTES + 1)
    if len(raw) > MAX_QUEUE_BYTES:
        raise ValueError("queue_source_exceeds_read_limit")
    value = json.loads(raw)
    if not isinstance(value, dict) or not isinstance(value.get("items"), list):
        raise ValueError("queue_source_invalid")
    return value


def _project(queue: dict[str, Any], elapsed: float) -> dict[str, Any]:
    items = [item for item in queue["items"] if isinstance(item, dict)]
    counts = Counter(str(item.get("status") or "UNKNOWN").upper() for item in items)
    active_ids = {
        str(item.get("objective_id") or item.get("research_case_id") or item.get("work_id") or "")
        for item in items
        if str(item.get("status") or "").upper() in ACTIVE_STATUSES
    }
    active_ids.discard("")
    completed = [item for item in items if str(item.get("status") or "").upper() == "COMPLETE"]
    latest = max(completed, key=lambda item: str(item.get("completed_at") or ""), default=None)
    timestamp = latest.get("completed_at") if latest else None
    try:
        if timestamp:
            datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
    except ValueError:
        timestamp = None
    return {
        "research_available": "YES",
        "research_room_mode": "UNKNOWN",
        "active_case_count": len(active_ids),
        "last_completed_case": (latest.get("research_case_id") or latest.get("objective_id") or latest.get("work_id")) if latest else "UNKNOWN",
        "last_completed_timestamp": timestamp or "UNKNOWN",
        "queue_summary": {"total_items": len(items), "by_status": dict(sorted(counts.items())),
                          "updated_at": queue.get("updated_at") or "UNKNOWN"},
        "current_health": "READABLE",
        "source": "data/runtime/research_work_queue.json",
        "read_only": True,
        "maintenance_performed": False,
        "elapsed_seconds": round(elapsed, 3),
    }


def read_research_status() -> dict[str, Any]:
    """Return durable queue facts or a partial UNKNOWN result within 9 seconds."""
    started = time.monotonic()
    done = threading.Event()
    result: dict[str, Any] = {}
    error: list[str] = []

    def read() -> None:
        try:
            result.update(_project(_read_existing_queue(), time.monotonic() - started))
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
            error.append(type(exc).__name__)
        finally:
            done.set()

    threading.Thread(target=read, name="research-read-status", daemon=True).start()
    if done.wait(HARD_TIMEOUT_SECONDS):
        if result:
            result["elapsed_seconds"] = round(time.monotonic() - started, 3)
            return {"status": "success", "data": result, "error": None,
                    "provenance": {"handler": "research_read_status.read_research_status", "freshness": "live"}}
        return {"status": "partial", "data": {
            "research_available": "UNKNOWN", "research_room_mode": "UNKNOWN",
            "active_case_count": "UNKNOWN", "last_completed_case": "UNKNOWN",
            "last_completed_timestamp": "UNKNOWN", "queue_summary": "UNKNOWN",
            "current_health": "UNKNOWN", "read_only": True,
            "maintenance_performed": False, "elapsed_seconds": round(time.monotonic() - started, 3),
        }, "error": "research_status_source_unavailable" + (":" + error[0] if error else ""),
            "provenance": {"handler": "research_read_status.read_research_status", "freshness": "unknown"}}
    return {"status": "partial", "data": {
        "research_available": "UNKNOWN", "research_room_mode": "UNKNOWN",
        "active_case_count": "UNKNOWN", "last_completed_case": "UNKNOWN",
        "last_completed_timestamp": "UNKNOWN", "queue_summary": "UNKNOWN",
        "current_health": "UNKNOWN", "read_only": True,
        "maintenance_performed": False, "elapsed_seconds": round(time.monotonic() - started, 3),
    }, "error": "research_status_hard_timeout",
        "provenance": {"handler": "research_read_status.read_research_status", "freshness": "unknown"}}
