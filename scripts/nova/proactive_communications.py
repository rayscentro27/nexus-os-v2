#!/usr/bin/env python3
"""Governed proactive operational messages for the existing Nova worker.

This module is deliberately deterministic.  It consumes existing receipts and
runtime state, sends only to the trusted configured Ray chat, and persists
event/delivery state so a worker restart cannot turn routine activity into
spam.  It is not a scheduler or a second Telegram worker.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from nova_telegram_worker import get_env, tg_send_message  # noqa: E402

STATE_PATH = ROOT / "data/runtime/nova_proactive_communications.json"
HEARTBEAT_PATH = ROOT / "data/runtime/research_heartbeat.json"
OPERATOR_PATH = ROOT / "reports/runtime/active_operator_latest.json"
RECEIPT_DIR = ROOT / "reports/runtime/nexus_active_operator_receipts"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return default


def _write(value: dict[str, Any]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    temp = STATE_PATH.with_suffix(".tmp")
    temp.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temp.replace(STATE_PATH)


def _hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()[:24]


def trusted_ray_chat() -> str | None:
    """Resolve only the existing canonical single-chat configuration."""
    env = get_env()
    raw = (env.get("HERMES_NOVA_CHAT_ID") or env.get("TELEGRAM_CHAT_ID") or "").strip()
    if not raw or "," in raw or not raw.lstrip("-").isdigit():
        return None
    return raw


def classify_event(event: dict[str, Any]) -> str:
    kind = str(event.get("kind", "")).upper()
    if event.get("test") is True:
        return "MATERIAL"
    if kind in {"SUPERVISOR_UNHEALTHY", "RESEARCH_NOT_REAL", "REQUIRED_PATH_FAILED",
                "RAY_REQUIRED", "APPROVAL_REQUIRED", "SAFETY_EVENT", "RECOVERY"}:
        return "CRITICAL"
    if kind in {"GOAL_ADVANCED", "GOAL_COMPLETED", "BLOCKER_REPAIRED",
                "CAPABILITY_PROVEN", "DEPARTMENT_MILESTONE"}:
        return "MATERIAL"
    if kind in {"CYCLE", "HEARTBEAT", "REFRESH", "UNCHANGED"}:
        return "ROUTINE"
    return "SUPPRESSED"


def _latest_receipt() -> dict[str, Any] | None:
    paths = sorted(RECEIPT_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime if p.exists() else 0)
    for path in reversed(paths):
        item = _read(path, {})
        if isinstance(item, dict):
            item["_receipt_path"] = str(path.relative_to(ROOT))
            return item
    return None


def collect_events() -> list[dict[str, Any]]:
    heartbeat = _read(HEARTBEAT_PATH, {})
    operator = _read(OPERATOR_PATH, {})
    events: list[dict[str, Any]] = []
    mode = str(heartbeat.get("execution_mode") or "").upper()
    if not mode and heartbeat.get("heartbeat") == "ACTIVE" and heartbeat.get("result_status") == "PASS":
        mode = "REAL"
    if mode != "REAL":
        events.append({"kind": "RESEARCH_NOT_REAL", "state": mode,
                       "summary": f"Research execution mode is {mode}.", "source": "research_heartbeat"})
    receipt = _latest_receipt()
    if receipt:
        nested = receipt.get("safe_action_results") or []
        nested_result = nested[-1].get("result", {}) if isinstance(nested, list) and nested and isinstance(nested[-1], dict) else {}
        goal = receipt.get("parent_goal") or receipt.get("goal_id") or nested_result.get("parent_goal")
        department = receipt.get("department") or nested_result.get("department", "Nexus")
        status = str(nested_result.get("status") or receipt.get("safe_internal_execution") or receipt.get("status") or "").upper()
        if goal and status not in {"FAILED", "DEGRADED"}:
            events.append({"kind": "GOAL_ADVANCED", "goal": str(goal),
                           "department": department,
                           "summary": f"{goal} received a verified internal work result.",
                           "source": receipt.get("receipt_path", "active_operator")})
        if status in {"FAILED", "DEGRADED"}:
            events.append({"kind": "SUPERVISOR_UNHEALTHY", "summary": "The latest autonomous work cycle needs recovery.", "source": "active_operator"})
    if str(operator.get("operator_health", "HEALTHY")).upper() not in {"HEALTHY", "UNKNOWN", ""}:
        events.append({"kind": "SUPERVISOR_UNHEALTHY", "summary": "Active Operator is degraded.", "source": "active_operator"})
    return events or [{"kind": "ROUTINE", "summary": "Nexus is operating normally.", "source": "runtime"}]


def _digest_due(state: dict[str, Any]) -> bool:
    last = state.get("last_digest_at")
    if not last:
        state["last_digest_at"] = now()
        return False
    try:
        return datetime.now(timezone.utc) - datetime.fromisoformat(str(last).replace("Z", "+00:00")) >= timedelta(hours=2)
    except ValueError:
        return True


def _digest_message() -> str:
    local = datetime.now(ZoneInfo("America/Phoenix"))
    heartbeat = _read(HEARTBEAT_PATH, {})
    mode = str(heartbeat.get("execution_mode") or ("REAL" if heartbeat.get("heartbeat") == "ACTIVE" and heartbeat.get("result_status") == "PASS" else "UNKNOWN")).upper()
    return (f"Ray — Nexus update ({local.strftime('%-I:%M %p')}).\n\n"
            "Company: operating normally.\n"
            "Research: " + mode + ".\n"
            "Nexus is continuing bounded internal work across the company portfolio.\n"
            "No material milestone since the last update.\n"
            "Need Ray: Nothing.")


def _message(event: dict[str, Any], severity: str) -> str:
    if event.get("test"):
        return ("Nexus proactive communication test.\n\n"
                "I can now contact you without waiting for an inbound message.\n\n"
                "Portfolio: 23 company goals\nResearch: REAL\n"
                "This channel is limited to Ray operational updates.")
    if severity == "CRITICAL":
        return f"Ray — Nexus needs attention.\n\n{event.get('summary', 'A critical operational condition was detected.')}\n\nNexus is recording the condition and continuing safe unrelated work where possible.\nRay action: review the operational update."
    if severity == "MATERIAL":
        return f"Ray — Nexus advanced.\n\n{event.get('summary', 'A material company milestone was verified.')}\n\nNo external action was taken. Nexus is selecting the next bounded internal step.\nRay action: none."
    return "Nexus update: systems are healthy and safe internal work is continuing. Nothing needs you."


def process_once(*, force_test: bool = False, force_digest: bool = False) -> dict[str, Any]:
    state = _read(STATE_PATH, {"schema_version": "nexus.proactive-communications.v1", "events": {}, "deliveries": {}, "last_notification_at": None, "last_digest_at": None})
    state.setdefault("events", {})
    state.setdefault("deliveries", {})
    chat = trusted_ray_chat()
    if not chat:
        state["last_suppression_reason"] = "TRUSTED_RAY_CHAT_NOT_PROVEN"
        _write(state)
        return {"status": "SUPPRESSED", "reason": "TRUSTED_RAY_CHAT_NOT_PROVEN"}
    events = [{"kind": "DEPARTMENT_MILESTONE", "test": True, "summary": "Explicit transport proof."}] if force_test else collect_events()
    results = []
    for event in events:
        severity = classify_event(event)
        key = _hash({k: v for k, v in event.items() if not str(k).startswith("_")})
        if key in state["events"] and state["events"][key].get("status", state["events"][key].get("delivery_state")) == "SENT":
            results.append({"event": key, "severity": severity, "status": "SUPPRESSED_DUPLICATE"})
            continue
        if not force_test and severity in {"ROUTINE", "SUPPRESSED"}:
            state["events"][key] = {"severity": severity, "delivery_state": "SUPPRESSED", "suppression_reason": "routine_or_insufficient_evidence", "observed_at": now()}
            results.append({"event": key, "severity": severity, "status": "SUPPRESSED"})
            continue
        text = _message(event, severity)
        delivery = {"event_id": key, "severity": severity, "status": "PENDING", "attempts": int(state["deliveries"].get(key, {}).get("attempts", 0)) + 1, "message_hash": _hash(text), "parent_goal": event.get("goal"), "source_receipt": event.get("source"), "created_at": now()}
        state["deliveries"][key] = delivery
        _write(state)
        ids = tg_send_message(chat, text)
        delivery.update({"status": "SENT" if ids else "FAILED", "message_ids": ids, "delivered_at": now() if ids else None})
        state["events"][key] = delivery
        state["last_notification_at"] = delivery.get("delivered_at")
        state["last_notified_event"] = key
        state["last_event_severity"] = severity
        _write(state)
        results.append({"event": key, "severity": severity, "status": delivery["status"], "message_ids": ids})
    if not force_test and (force_digest or _digest_due(state)):
        digest_key = _hash({"kind": "DIGEST", "period": datetime.now(timezone.utc).strftime("%Y%m%d%H")})
        if digest_key not in state["events"]:
            text = _digest_message()
            ids = tg_send_message(chat, text)
            state["events"][digest_key] = {"event_id": digest_key, "severity": "ROUTINE", "status": "SENT" if ids else "FAILED", "message_hash": _hash(text), "message_ids": ids, "created_at": now()}
            state["last_digest_at"] = now()
            _write(state)
            results.append({"event": digest_key, "severity": "ROUTINE", "status": "SENT" if ids else "FAILED", "message_ids": ids})
    try:
        state_ref = str(STATE_PATH.relative_to(ROOT))
    except ValueError:
        state_ref = str(STATE_PATH)
    return {"status": "PASS" if any(x.get("status") == "SENT" for x in results) else "NO_SEND", "results": results, "state_path": state_ref}


if __name__ == "__main__":
    print(json.dumps(process_once(force_test="--send-test" in sys.argv, force_digest="--send-digest" in sys.argv), indent=2))
