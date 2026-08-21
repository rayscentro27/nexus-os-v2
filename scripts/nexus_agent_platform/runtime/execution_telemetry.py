"""Verified Nexus runtime execution telemetry.

This module records actual runtime boundary events, then reduces the append-only
event log into read-only operational facts for Nova. It intentionally does not
classify process registry configuration or simulated state as execution proof.
"""

from __future__ import annotations

import json
import os
import re
import time
import uuid
from contextvars import ContextVar
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional

from nexus_agent_platform.runtime.paths import nexus_data_path

EVENT_TYPES = frozenset({"started", "heartbeat", "completed", "failed", "skipped", "blocked"})
STATUSES = frozenset({"running", "completed", "failed", "skipped", "blocked"})
TERMINAL_EVENT_TYPES = frozenset({"completed", "failed", "skipped", "blocked"})
SOURCE_TYPE = "verified_execution_telemetry"
DEFAULT_STALE_SECONDS = 15 * 60
DEFAULT_RETENTION_DAYS = 30
DEFAULT_MAX_BYTES = 10 * 1024 * 1024
STORE_ENV = "NEXUS_EXECUTION_TELEMETRY_PATH"

_CURRENT_PARENT_RUN_ID: ContextVar[Optional[str]] = ContextVar("nexus_execution_parent_run_id", default=None)
_CURRENT_STAGE_METADATA: ContextVar[Dict[str, Any]] = ContextVar("nexus_execution_stage_metadata", default={})

_SECRET_KEYS = {
    "token", "secret", "api_key", "apikey", "authorization", "cookie",
    "password", "ssn", "dob", "credit_report", "raw_message", "message_body",
    "prompt", "full_prompt", "bank_account", "card_number",
}
_PROCESS_NAMES = {
    "daily_monitor": "Daily Monitor",
    "system_health": "System Health Check",
    "system_health_check": "System Health Check",
    "supabase_verification": "Supabase Verification",
    "command_center_health": "Command Center Health",
    "client_portal_status": "Client Portal Status",
    "ray_review_queue": "Ray Review Queue",
    "hermes_router": "Hermes Work Router",
    "hermes_work_router": "Hermes Work Router",
    "alpha_intake": "Alpha Research Intake",
    "alpha_research_intake": "Alpha Research Intake",
    "research_intelligence": "Research Intelligence",
    "creative_quality_loop": "Creative Quality Loop",
    "work_orders": "Work Orders",
    "recovery": "Recovery Check",
    "recovery_check": "Recovery Check",
    "telegram_operator": "Telegram Operator",
    "notebooklm_import_status": "NotebookLM Import Status",
    "repo_intelligence": "Repo Intelligence",
    "marketing_content_pipeline": "Marketing Content Pipeline",
    "credit_business_funding_readiness": "Credit/Business/Funding Readiness",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_run_id(prefix: str = "run") -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def telemetry_store_path() -> Path:
    configured = os.environ.get(STORE_ENV)
    if configured:
        return Path(configured).expanduser()
    return nexus_data_path("runtime", "execution_telemetry", "events.jsonl")


def canonical_process_name(process_id: str, fallback: str = "") -> str:
    return _PROCESS_NAMES.get(process_id, fallback or process_id.replace("_", " ").title())


def _sanitize_metadata(value: Any) -> Any:
    if isinstance(value, dict):
        result: Dict[str, Any] = {}
        for key, item in value.items():
            if key.lower() in _SECRET_KEYS:
                result[key] = "REDACTED"
            else:
                result[key] = _sanitize_metadata(item)
        return result
    if isinstance(value, list):
        return [_sanitize_metadata(item) for item in value[:50]]
    if isinstance(value, str):
        text = re.sub(r"\d{9,10}:[A-Za-z0-9_-]{35}", "REDACTED_BOT_TOKEN", value)
        text = re.sub(r"sk-or-v1-[A-Za-z0-9]{20,}", "REDACTED_OPENROUTER", text)
        text = re.sub(r"\b\d{3}-\d{2}-\d{4}\b", "REDACTED_SSN", text)
        return text[:500]
    return value


def build_event(
    *,
    process_id: str,
    event_type: str,
    status: str,
    run_id: Optional[str] = None,
    process_name: Optional[str] = None,
    worker_id: str = "",
    agent_id: str = "",
    execution_type: str = "",
    started_at: Optional[str] = None,
    event_at: Optional[str] = None,
    completed_at: Optional[str] = None,
    duration_ms: Optional[int] = None,
    exit_code: Optional[int] = None,
    error_type: Optional[str] = None,
    error_message: Optional[str] = None,
    source: str = "",
    trace_id: Optional[str] = None,
    parent_run_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    if event_type not in EVENT_TYPES:
        raise ValueError(f"invalid event_type: {event_type}")
    if status not in STATUSES:
        raise ValueError(f"invalid status: {status}")
    if event_type == "started" and status != "running":
        raise ValueError("started events must use status=running")
    if event_type in TERMINAL_EVENT_TYPES and status != event_type:
        raise ValueError("terminal event status must match event_type")
    now = event_at or utc_now()
    run = run_id or new_run_id(process_id)
    return {
        "event_id": f"evt_{uuid.uuid4().hex}",
        "run_id": run,
        "process_id": process_id,
        "process_name": process_name or canonical_process_name(process_id),
        "worker_id": worker_id,
        "agent_id": agent_id,
        "execution_type": execution_type,
        "event_type": event_type,
        "status": status,
        "started_at": started_at or now,
        "event_at": now,
        "completed_at": completed_at,
        "duration_ms": duration_ms,
        "exit_code": exit_code,
        "error_type": error_type,
        "error_message": (error_message or "")[:500] if error_message else None,
        "source": source,
        "source_type": SOURCE_TYPE,
        "trace_id": trace_id,
        "parent_run_id": parent_run_id,
        "metadata": _sanitize_metadata(metadata or {}),
    }


def validate_event(event: Dict[str, Any]) -> bool:
    required = {"event_id", "run_id", "process_id", "event_type", "status", "event_at", "source_type"}
    if not required.issubset(event):
        return False
    if event.get("event_type") not in EVENT_TYPES:
        return False
    if event.get("status") not in STATUSES:
        return False
    return event.get("source_type") == SOURCE_TYPE


def _prepare_store(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)
    if not path.exists():
        path.touch(mode=0o600)
    os.chmod(path, 0o600)


def append_event(event: Dict[str, Any], path: Optional[Path] = None) -> Dict[str, Any]:
    if not validate_event(event):
        raise ValueError("invalid execution telemetry event")
    target = path or telemetry_store_path()
    _prepare_store(target)
    line = json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n"
    with target.open("a", encoding="utf-8") as fh:
        fh.write(line)
        fh.flush()
        os.fsync(fh.fileno())
    _enforce_retention(target)
    return event


def emit_event(**kwargs: Any) -> Dict[str, Any]:
    return append_event(build_event(**kwargs))


@contextmanager
def telemetry_context(
    *,
    parent_run_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Iterator[None]:
    """Attach safe parent metadata to nested runtime telemetry in this context."""
    parent_token = _CURRENT_PARENT_RUN_ID.set(parent_run_id)
    metadata_token = _CURRENT_STAGE_METADATA.set(_sanitize_metadata(metadata or {}))
    try:
        yield
    finally:
        _CURRENT_STAGE_METADATA.reset(metadata_token)
        _CURRENT_PARENT_RUN_ID.reset(parent_token)


def current_parent_run_id() -> Optional[str]:
    return _CURRENT_PARENT_RUN_ID.get()


def current_stage_metadata() -> Dict[str, Any]:
    return dict(_CURRENT_STAGE_METADATA.get() or {})


@contextmanager
def stage_execution(
    *,
    stage: str,
    process_id: str = "telegram_operator",
    process_name: Optional[str] = "Telegram Operator",
    worker_id: str = "nova_telegram_worker",
    agent_id: str = "hermes_nova",
    source: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> Iterator[str]:
    """Record a bounded child stage under the active execution run."""
    parent_run_id = current_parent_run_id()
    if not parent_run_id:
        yield ""
        return
    base_metadata = current_stage_metadata()
    merged_metadata = {**base_metadata, **(metadata or {}), "stage": stage}
    with execution_run(
        process_id=process_id,
        process_name=process_name,
        worker_id=worker_id,
        agent_id=agent_id,
        execution_type=f"stage:{stage}",
        source=source,
        parent_run_id=parent_run_id,
        metadata=merged_metadata,
    ) as run_id:
        yield run_id


@contextmanager
def execution_run(
    *,
    process_id: str,
    worker_id: str,
    agent_id: str = "",
    execution_type: str,
    source: str,
    process_name: Optional[str] = None,
    parent_run_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Iterator[str]:
    run_id = new_run_id(process_id)
    started_at = utc_now()
    start = time.monotonic()
    emit_event(
        process_id=process_id,
        process_name=process_name,
        worker_id=worker_id,
        agent_id=agent_id,
        execution_type=execution_type,
        event_type="started",
        status="running",
        run_id=run_id,
        started_at=started_at,
        source=source,
        parent_run_id=parent_run_id,
        metadata=metadata,
    )
    try:
        yield run_id
    except Exception as exc:
        emit_event(
            process_id=process_id,
            process_name=process_name,
            worker_id=worker_id,
            agent_id=agent_id,
            execution_type=execution_type,
            event_type="failed",
            status="failed",
            run_id=run_id,
            started_at=started_at,
            completed_at=utc_now(),
            duration_ms=round((time.monotonic() - start) * 1000),
            error_type=exc.__class__.__name__,
            error_message=str(exc),
            source=source,
            parent_run_id=parent_run_id,
            metadata=metadata,
        )
        raise
    else:
        emit_event(
            process_id=process_id,
            process_name=process_name,
            worker_id=worker_id,
            agent_id=agent_id,
            execution_type=execution_type,
            event_type="completed",
            status="completed",
            run_id=run_id,
            started_at=started_at,
            completed_at=utc_now(),
            duration_ms=round((time.monotonic() - start) * 1000),
            source=source,
            parent_run_id=parent_run_id,
            metadata=metadata,
        )


def read_events(path: Optional[Path] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    target = path or telemetry_store_path()
    if not target.exists():
        return []
    events: List[Dict[str, Any]] = []
    with target.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if validate_event(event):
                events.append(event)
    return events[-limit:] if limit else events


def _parse_dt(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _event_key(event: Dict[str, Any]) -> datetime:
    return _parse_dt(event.get("event_at")) or datetime.min.replace(tzinfo=timezone.utc)


def reduce_events(
    events: Iterable[Dict[str, Any]],
    *,
    stale_seconds: int = DEFAULT_STALE_SECONDS,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    current_time = now or datetime.now(timezone.utc)
    by_run: Dict[str, List[Dict[str, Any]]] = {}
    for event in sorted(events, key=_event_key):
        by_run.setdefault(event["run_id"], []).append(event)

    runs: List[Dict[str, Any]] = []
    by_process: Dict[str, Dict[str, Any]] = {}
    for run_id, run_events in by_run.items():
        first = run_events[0]
        terminal = next((e for e in reversed(run_events) if e["event_type"] in TERMINAL_EVENT_TYPES), None)
        last = run_events[-1]
        started_at = first.get("started_at") or first.get("event_at")
        started_dt = _parse_dt(started_at)
        last_event_dt = _parse_dt(last.get("event_at"))
        stale = False
        current_state = "idle"
        if terminal is None:
            age_anchor = last_event_dt or started_dt or current_time
            stale = (current_time - age_anchor).total_seconds() > stale_seconds
            current_state = "unknown" if stale else "running"
        terminal_status = terminal.get("status") if terminal else "unknown"
        record = {
            "run_id": run_id,
            "process_id": first.get("process_id"),
            "process_name": first.get("process_name"),
            "worker_id": first.get("worker_id"),
            "agent_id": first.get("agent_id"),
            "execution_type": first.get("execution_type"),
            "source_type": first.get("source_type"),
            "source": first.get("source"),
            "current_state": current_state,
            "last_terminal_status": terminal_status,
            "status": terminal_status if terminal else ("stale" if stale else "running"),
            "started_at": started_at,
            "completed_at": terminal.get("completed_at") if terminal else None,
            "duration_ms": terminal.get("duration_ms") if terminal else None,
            "exit_code": terminal.get("exit_code") if terminal else None,
            "error_type": terminal.get("error_type") if terminal else None,
            "error_message": terminal.get("error_message") if terminal else None,
            "last_event_at": last.get("event_at"),
            "stale": stale,
            "event_count": len(run_events),
            "metadata": first.get("metadata", {}),
        }
        runs.append(record)
        process_id = record["process_id"]
        existing = by_process.get(process_id)
        if existing is None or (record.get("last_event_at") or "") > (existing.get("last_event_at") or ""):
            by_process[process_id] = {
                "process_id": process_id,
                "process_name": record.get("process_name"),
                "current_state": record["current_state"],
                "last_terminal_status": record["last_terminal_status"],
                "last_run_id": run_id,
                "last_started_at": record["started_at"],
                "last_completed_at": record["completed_at"],
                "last_duration_ms": record["duration_ms"],
                "last_worker_id": record["worker_id"],
                "last_error": record["error_message"],
                "telemetry_available": True,
                "stale": stale,
                "source_type": SOURCE_TYPE,
            }

    runs.sort(key=lambda r: r.get("last_event_at") or "", reverse=True)
    return {"runs": runs, "processes": list(by_process.values())}


def _window_start(window: str, now: Optional[datetime] = None) -> Optional[datetime]:
    current = now or datetime.now(timezone.utc)
    lower = (window or "").lower()
    if lower in ("latest", "most_recent", "all", ""):
        return None
    if lower in ("last_hour", "hour"):
        return current - timedelta(hours=1)
    if lower in ("today", "since_midnight"):
        phoenix = current.astimezone(timezone(timedelta(hours=-7)))
        midnight = phoenix.replace(hour=0, minute=0, second=0, microsecond=0)
        return midnight.astimezone(timezone.utc)
    if lower in ("last_24_hours", "24h"):
        return current - timedelta(hours=24)
    return None


def query_runtime_telemetry(
    *,
    operation: str = "overview",
    conditions: Optional[List[Dict[str, Any]]] = None,
    window: str = "all",
    limit: int = 50,
) -> Dict[str, Any]:
    events = read_events()
    now_dt = datetime.now(timezone.utc)
    start = _window_start(window, now_dt)
    if start:
        events = [e for e in events if (_parse_dt(e.get("event_at")) or now_dt) >= start]
    reduced = reduce_events(events, now=now_dt)
    runs = _apply_conditions(reduced["runs"], conditions or [])
    if conditions:
        run_processes = {r.get("process_id") for r in runs}
        process_records = [
            p for p in reduced["processes"]
            if p.get("process_id") in run_processes
        ]
    else:
        process_records = reduced["processes"]

    if operation == "count":
        records: List[Dict[str, Any]] = []
    elif operation == "lookup":
        records = runs[:1]
    elif operation == "filter":
        records = runs[:limit]
    elif operation == "summarize":
        records = runs[:limit]
    else:
        records = runs[:limit]

    active = [r for r in reduced["runs"] if r["current_state"] == "running"]
    failed = [r for r in reduced["runs"] if r["last_terminal_status"] == "failed"]
    completed = [r for r in reduced["runs"] if r["last_terminal_status"] == "completed"]
    skipped = [r for r in reduced["runs"] if r["last_terminal_status"] == "skipped"]
    blocked = [r for r in reduced["runs"] if r["last_terminal_status"] == "blocked"]
    stale = [r for r in reduced["runs"] if r["stale"]]
    covered = sorted({r["process_id"] for r in reduced["runs"] if r.get("process_id")})
    enabled_without_verified = _enabled_without_verified_run(covered_process_ids={
        r.get("process_id") for r in reduced["runs"] if r.get("process_id")
    })

    coverage_status = "unavailable"
    if covered:
        coverage_status = "partial"

    return {
        "status": "success",
        "source_type": SOURCE_TYPE,
        "coverage": {
            "coverage_status": coverage_status,
            "covered_processes": covered,
            "uncovered_processes": [],
            "window_start": start.isoformat() if start else None,
            "window_end": now_dt.isoformat(),
            "source_count": len(events),
        },
        "summary": {
            "event_count": len(events),
            "run_count": len(reduced["runs"]),
            "active_count": len(active),
            "completed_count": len(completed),
            "failed_count": len(failed),
            "skipped_count": len(skipped),
            "blocked_count": len(blocked),
            "stale_count": len(stale),
        },
        "processes": process_records,
        "enabled_processes_without_verified_run": enabled_without_verified,
        "runs": records,
        "total_count": len(runs),
        "returned_count": len(records),
        "truncated": len(records) < len(runs),
        "telemetry_health": telemetry_health(events=events, reduced=reduced, now=now_dt),
    }


def _enabled_without_verified_run(covered_process_ids: set) -> List[Dict[str, Any]]:
    try:
        from nexus_agent_platform.capabilities.nexus_knowledge import get_process_registry_live

        registry = get_process_registry_live()
        processes = registry.get("processes", [])
    except Exception:
        return []
    missing = []
    for process in processes:
        if process.get("configuration_state") != "enabled":
            continue
        if process.get("process_id") in covered_process_ids:
            continue
        missing.append({
            "process_id": process.get("process_id"),
            "name": process.get("name"),
            "configuration_state": process.get("configuration_state"),
            "execution_mode": process.get("execution_mode"),
            "runtime_state": process.get("runtime_state"),
            "telemetry_available": False,
        })
    return missing


def _apply_conditions(records: List[Dict[str, Any]], conditions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    result = list(records)
    for cond in conditions:
        field = cond.get("field")
        operator = cond.get("operator", "eq")
        value = cond.get("value")
        filtered = []
        for record in result:
            rv = record.get(field)
            if operator == "eq" and rv == value:
                filtered.append(record)
            elif operator == "neq" and rv != value:
                filtered.append(record)
            elif operator == "in" and isinstance(value, list) and rv in value:
                filtered.append(record)
            elif operator == "not_in" and isinstance(value, list) and rv not in value:
                filtered.append(record)
            elif operator == "contains" and isinstance(rv, str) and isinstance(value, str) and value.lower() in rv.lower():
                filtered.append(record)
            elif operator == "exists" and rv is not None:
                filtered.append(record)
        result = filtered
    return result


def telemetry_health(
    *,
    events: Optional[List[Dict[str, Any]]] = None,
    reduced: Optional[Dict[str, Any]] = None,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    current = now or datetime.now(timezone.utc)
    loaded_events = events if events is not None else read_events()
    reduced_data = reduced if reduced is not None else reduce_events(loaded_events, now=current)
    last_event = max((e.get("event_at") for e in loaded_events), default=None)
    day_start = current - timedelta(hours=24)
    events_24h = [e for e in loaded_events if (_parse_dt(e.get("event_at")) or current) >= day_start]
    covered = sorted({p["process_id"] for p in reduced_data.get("processes", []) if p.get("process_id")})
    status = "unavailable"
    if loaded_events:
        status = "healthy" if events_24h else "partial"
    return {
        "status": status,
        "last_event_at": last_event,
        "event_count_24h": len(events_24h),
        "covered_process_count": len(covered),
        "uncovered_process_count": 0,
        "covered_processes": covered,
        "writer_errors": 0,
        "parse_errors": 0,
    }


def _enforce_retention(path: Path, retention_days: int = DEFAULT_RETENTION_DAYS, max_bytes: int = DEFAULT_MAX_BYTES) -> None:
    try:
        if not path.exists() or path.stat().st_size <= max_bytes * 2:
            return
        cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
        kept = []
        for event in read_events(path):
            event_dt = _parse_dt(event.get("event_at"))
            if event_dt and event_dt >= cutoff:
                kept.append(json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n")
        tmp = path.with_suffix(".tmp")
        tmp.write_text("".join(kept), encoding="utf-8")
        os.chmod(tmp, 0o600)
        tmp.replace(path)
    except Exception:
        return
