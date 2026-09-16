"""Productivity health and supervisor incident contracts.

Process liveness is deliberately separate from useful output.  Incidents are
append-only and notification delivery is idempotent by incident id.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[2]
INCIDENTS = ROOT / "data/runtime/nexus_supervisor_incidents.jsonl"
NOTIFICATIONS = ROOT / "data/runtime/nexus_supervisor_notifications.jsonl"
DELIVERIES = ROOT / "reports/runtime/nexus_supervisor_notification_deliveries.jsonl"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _append(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")


def _rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            value = json.loads(line)
            if isinstance(value, dict):
                rows.append(value)
        except ValueError:
            continue
    return rows


def _incident_id(worker: str, classification: str) -> str:
    return "inc_" + hashlib.sha256(f"{worker}:{classification}".encode()).hexdigest()[:20]


def _as_dt(value: Any) -> datetime | None:
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def evaluate_research(*, process_running: bool, heartbeat: dict[str, Any] | None,
                      execution_events: list[dict[str, Any]] | None = None,
                      now_dt: datetime | None = None,
                      heartbeat_stale_seconds: int = 150) -> dict[str, Any]:
    """Classify Research using recent execution evidence, not PID alone."""
    current = now_dt or datetime.now(timezone.utc)
    heartbeat = heartbeat if isinstance(heartbeat, dict) else {}
    events = execution_events or []
    wake_failures = [e for e in events if e.get("status") in {"FAILED", "FAILED_RETRYABLE", "TIMEOUT", "ERROR"}]
    successes = [e for e in events if e.get("status") in {"EVIDENCE_READY", "COMPLETED"}]
    last_hb = _as_dt(heartbeat.get("last_real_output") or heartbeat.get("generated_at") or heartbeat.get("updated_at"))
    next_wake = _as_dt(heartbeat.get("next_wake"))
    overdue = next_wake is not None and current > next_wake + timedelta(seconds=heartbeat_stale_seconds)
    stale = not last_hb or ((current - last_hb).total_seconds() > heartbeat_stale_seconds and (next_wake is None or overdue))
    consecutive_failures = 0
    for event in reversed(events):
        status = str(event.get("status", "")).upper()
        if status in {"FAILED", "FAILED_RETRYABLE", "TIMEOUT", "ERROR"}:
            consecutive_failures += 1
        elif status in {"EVIDENCE_READY", "COMPLETED"}:
            break
    if not process_running:
        process_status, productivity = "DOWN", "STALLED"
        classification = "PROCESS_DOWN"
    elif stale:
        process_status, productivity = "STALE", "STALLED"
        classification = "HEARTBEAT_STALE"
    elif consecutive_failures >= 3:
        process_status, productivity = "HEALTHY", "STALLED"
        classification = "SCHEDULED_WAKE_FAILED"
    elif consecutive_failures >= 2:
        process_status, productivity = "HEALTHY", "DEGRADED"
        classification = "SCHEDULED_WAKE_FAILED"
    else:
        process_status = "HEALTHY"
        productivity = "HEALTHY" if successes or heartbeat.get("result_status") in {"PASS", "DISPATCHED"} else "IDLE_LEGITIMATE"
        classification = None
    return {"process_health": process_status, "productivity_health": productivity,
            "classification": classification, "last_heartbeat": heartbeat.get("last_real_output"),
            "last_real_output": heartbeat.get("last_real_output"),
            "last_successful_scheduled_wake": heartbeat.get("last_real_output") if successes or heartbeat.get("result_status") == "DISPATCHED" else None,
            "consecutive_failures": consecutive_failures, "consecutive_timeouts": sum(1 for e in events[-10:] if str(e.get("status", "")).upper() == "TIMEOUT"),
            "outputs_last_1h": len(successes), "evidence": "research_heartbeat + research_execution_jobs"}


def record_incident(*, worker: str, classification: str, severity: str,
                    details: dict[str, Any], recovery_action: str,
                    ray_action_required: bool = False) -> dict[str, Any]:
    incident_id = _incident_id(worker, classification)
    existing = [r for r in _rows(INCIDENTS) if r.get("incident_id") == incident_id and r.get("state") == "OPEN"]
    if existing:
        return existing[-1]
    incident = {"incident_id": incident_id, "worker": worker, "classification": classification,
                "severity": severity, "created_at": now(), "state": "OPEN", "details": details,
                "automatic_recovery_action": recovery_action, "ray_action_required": ray_action_required}
    _append(INCIDENTS, incident)
    event = {"notification_id": "notif_" + incident_id, "incident_id": incident_id,
             "created_at": incident["created_at"], "severity": severity, "state": "PENDING",
             "destination": "trusted Telegram + Admin", "text": _format(incident)}
    if not any(r.get("notification_id") == event["notification_id"] for r in _rows(NOTIFICATIONS)):
        _append(NOTIFICATIONS, event)
    return incident


def _format(incident: dict[str, Any]) -> str:
    d = incident.get("details", {})
    return (f"Research is {str(incident.get('severity', 'degraded')).lower()}. "
            f"{incident.get('classification')}: {d.get('summary', 'productivity failure detected')}. "
            f"Nexus is taking: {incident.get('automatic_recovery_action')}. "
            f"Ray action required: {'yes' if incident.get('ray_action_required') else 'no'}. "
            f"Next retry: {d.get('next_retry', 'scheduled worker retry')}.")


def deliver_pending(send: Callable[[int, str], dict[str, Any]] | None,
                    chat_ids: set[int] | None) -> dict[str, int]:
    """Consume pending supervisor events through the existing notification worker."""
    latest: dict[str, dict[str, Any]] = {}
    for row in _rows(NOTIFICATIONS):
        notification_id = row.get("notification_id")
        if notification_id:
            latest[str(notification_id)] = row
    pending = [r for r in latest.values() if r.get("state") in {"PENDING", "FAILED_RETRYABLE"}]
    delivered = failed = 0
    if send and chat_ids:
        for event in pending:
            outcomes = []
            for chat_id in chat_ids:
                result = send(chat_id, str(event.get("text", "")))
                outcomes.append(bool(result.get("ok")))
            if outcomes and all(outcomes):
                event["state"] = "DELIVERED"; event["delivered_at"] = now(); delivered += 1
                _append(DELIVERIES, {"notification_id": event["notification_id"], "incident_id": event["incident_id"], "delivered_at": event["delivered_at"], "destination": "trusted Telegram", "status": "DELIVERED"})
            else:
                event["state"] = "FAILED_RETRYABLE"; event["last_error"] = "telegram delivery failed"; failed += 1
            _append(NOTIFICATIONS, {**event, "supersedes": event.get("notification_id")})
    return {"pending": len(pending), "delivered": delivered, "failed": failed}


def close_incident(incident_id: str, *, reason: str) -> dict[str, Any] | None:
    rows = _rows(INCIDENTS)
    matches = [r for r in rows if r.get("incident_id") == incident_id and r.get("state") == "OPEN"]
    if not matches:
        return None
    item = {**matches[-1], "state": "RECOVERED", "recovered_at": now(), "recovery_reason": reason}
    _append(INCIDENTS, item)
    recovery = {"notification_id": "recovery_" + incident_id, "incident_id": incident_id, "created_at": now(), "severity": "RECOVERY", "state": "PENDING", "destination": "trusted Telegram + Admin", "text": f"Research recovered. {reason}"}
    if not any(r.get("notification_id") == recovery["notification_id"] for r in _rows(NOTIFICATIONS)):
        _append(NOTIFICATIONS, recovery)
    return item
