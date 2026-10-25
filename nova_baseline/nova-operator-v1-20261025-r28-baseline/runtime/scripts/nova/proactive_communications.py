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
from notification_policy import classify_event, event_fingerprint, event_type as policy_event_type, executive_message, material_state  # noqa: E402

STATE_PATH = ROOT / "data/runtime/nova_proactive_communications.json"
HEARTBEAT_PATH = ROOT / "data/runtime/research_heartbeat.json"
OPERATOR_PATH = ROOT / "reports/runtime/active_operator_latest.json"
RECEIPT_DIR = ROOT / "reports/runtime/nexus_active_operator_receipts"
MATERIAL_EVENTS_PATH = ROOT / "data/runtime/nova_material_events.jsonl"
# Recurring executive reports are a separate, explicitly approved product
# surface.  They must never be enabled merely because the worker is alive.
AUTOMATIC_REPORTS_APPROVED = os.getenv("NOVA_APPROVED_MORNING_REPORT", "0").strip().lower() in {"1", "true", "yes"}


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


def _material_state(event: dict[str, Any]) -> dict[str, Any]:
    return material_state(event)


def _material_state_hash(event: dict[str, Any]) -> str:
    return event_fingerprint(event)


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
    # Resource alarms are sourced from the canonical governed incident ledger,
    # never reconstructed from conversational state.
    try:
        sys.path.insert(0,str(ROOT / "scripts"))
        from nexus_agent_platform.feeder_runtime import _request
        rows=_request("nexus_resource_incidents?provider=eq.NOTEBOOKLM&code=eq.BUDGET_HARD_LIMIT&select=job_id,code,threshold,observed,created_at&order=created_at.desc&limit=1") or []
        if rows:
            incident=rows[0]
            policies=_request("nexus_resource_policies?provider=eq.NOTEBOOKLM&service=eq.research_discovery&job_type=eq.NEXUS_NOTEBOOKLM_DISCOVERY_V5_6FB82FD9%3ANOTEBOOKLM_DISCOVERY&budget_period=eq.DAILY&select=state,hard_limits,updated_at") or []
            policy=policies[0] if policies else {}
            events.append({"kind":"RESOURCE_ALARM","event_type":"RESOURCE_ALARM",
                "severity":"CRITICAL","affected_system":"NOTEBOOKLM/research_discovery",
                "material_status":policy.get("state","UNKNOWN"),"status":policy.get("state","UNKNOWN"),
                "summary":"NotebookLM research discovery reached its configured daily internal resource limit. That Research branch is paused. Independent V5 work is continuing, and the same job will resume when the resource policy returns to NORMAL.",
                "why_it_matters":"Only jobs that require NotebookLM are paused; the V5 campaign remains active.",
                "required_action":"No Ray action is required unless Nexus reports that the policy needs an explicit administrative recovery.",
                "next":"Continue independent V5 jobs and recheck the same NotebookLM job when the daily resource window rolls over.",
                "source":f"nexus_resource_incidents:{incident.get('job_id')}",
                "policy_state":policy.get("state"),"limit":(policy.get("hard_limits") or {}).get("usage",{}).get("bytes")})
    except Exception:
        # Notification collection must not disrupt unrelated Nova operations.
        pass
    try:
        rows = [json.loads(line) for line in MATERIAL_EVENTS_PATH.read_text(encoding="utf-8").splitlines() if line.strip()][-20:]
        events.extend(row for row in rows if isinstance(row, dict))
    except (OSError, ValueError):
        pass
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
        ai_plan = nested_result.get("ai_plan") if isinstance(nested_result.get("ai_plan"), dict) else {}
        goal = (receipt.get("parent_goal") or receipt.get("goal_id") or nested_result.get("parent_goal")
                or ai_plan.get("objective_id"))
        department = receipt.get("department") or nested_result.get("department", "Nexus")
        status = str(nested_result.get("status") or receipt.get("safe_internal_execution") or receipt.get("status") or "").upper()
        executor_result = nested_result.get("executor_result") if isinstance(nested_result.get("executor_result"), dict) else {}
        executed_action = str(executor_result.get("action") or nested_result.get("action") or "")
        # A healthy capability check is maintenance, not company progress.
        # Only a real bounded deliverable or specialized business action may
        # produce a material GOAL_ADVANCED notification.
        material = (
            executor_result.get("material_progress") is True
            or executed_action in {"department.research_handoff", "trading.research_cycle", "funding.readiness_review"}
        ) and status not in {"FAILED", "DEGRADED"}
        if goal and material:
            events.append({"kind": "GOAL_ADVANCED", "goal": str(goal),
                           "department": department,
                           "summary": f"{goal} received a verified internal work result.",
                           "source": receipt.get("receipt_path", "active_operator")})
        # Terminal closure is a distinct executive event.  It is emitted from
        # the canonical operator receipt only after the objective state has
        # been durably transitioned, so Ray is never told that an ordinary
        # receipt is a completed company outcome.
        for closure in receipt.get("objective_closures") or []:
            if not isinstance(closure, dict):
                continue
            closure_status = str(closure.get("status") or "").upper()
            if closure_status == "READY_FOR_HUMAN_REVIEW":
                closure_goal = closure.get("goal_id") or goal or "company objective"
                artifact = closure.get("artifact_path") or "the persisted final package"
                events.append({
                    "kind": "RAY_REQUIRED",
                    "goal": str(closure_goal),
                    "summary": (
                        f"{closure_goal} is ready for Ray review. The verified final internal "
                        f"deliverable is available at {artifact}."
                    ),
                    "source": receipt.get("receipt_path", "active_operator"),
                })
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


def _morning_digest_due(state: dict[str, Any]) -> bool:
    """Return true once per Phoenix morning; the existing worker supplies cadence."""
    local = datetime.now(ZoneInfo("America/Phoenix"))
    if local.hour < 6 or local.hour >= 12:
        return False
    return state.get("last_morning_digest_local_date") != local.date().isoformat()


def _morning_digest_message() -> str:
    """Bounded executive digest from current durable state, not a template count."""
    heartbeat = _read(HEARTBEAT_PATH, {})
    operator = _read(OPERATOR_PATH, {})
    campaign = _read(ROOT / "data/runtime/research_campaign_state.json", {})
    youtube = _read(ROOT / "reports/runtime/youtube_portfolio_recovery_20260914T181652Z.json", {})
    research = str(heartbeat.get("result_status") or "UNKNOWN").upper()
    last = heartbeat.get("last_real_output") or heartbeat.get("last_success") or "UNKNOWN"
    next_action = heartbeat.get("next_action") or "UNKNOWN"
    next_wake = heartbeat.get("next_wake") or "UNKNOWN"
    operator_status = str(operator.get("operator_health") or "UNKNOWN").upper()
    return ("Ray — Nexus morning operating digest.\n\n"
            f"What Nexus did overnight: Research heartbeat and scheduled operator checks ran; latest research state is {research}.\n"
            f"What Nexus learned: latest durable research output at {last}.\n"
            f"What moved toward revenue: {campaign.get('last_completed_campaign') or 'No newly completed revenue campaign recorded.'}.\n"
            f"What completed: {youtube.get('backfill_mode', {}).get('enabled', False) and 'YouTube watch/backfill remains enabled' or 'No completion recorded'}.\n"
            f"What failed or recovered: Active Operator is {operator_status}; retry policy remains governed.\n"
            "What needs Ray: no external action is implied by this digest.\n"
            f"What Nexus will do next: {next_action}; next wake {next_wake}.")


def _message(event: dict[str, Any], severity: str) -> str:
    if event.get("test"):
        return ("Nexus proactive communication test.\n\n"
                "I can now contact you without waiting for an inbound message.\n\n"
                "Portfolio: 23 company goals\nResearch: REAL\n"
                "This channel is limited to Ray operational updates.")
    if str(event.get("kind", "")).upper() == "TERMINAL_CERTIFICATION":
        return (
            "Ray — Nexus autonomy certification update.\n\n"
            f"Autonomy: {event.get('autonomy', 'PARTIAL')}\n"
            f"Departments proven: {event.get('departments', 'bounded internal lanes')}\n"
            f"Legitimate objectives advanced: {event.get('objectives_advanced', '0')}\n"
            f"Genuine AI workers: {event.get('ai_workforce', 'PARTIAL')}\n"
            f"Multi-cycle continuation: {event.get('multi_cycle', 'PARTIAL')}\n"
            f"Nova executive control: {event.get('nova_control', 'PARTIAL')}\n"
            f"Ray action: {event.get('ray_action', 'None; continue observing the bounded recovery.')}."
        )
    if severity == "CRITICAL":
        if str(event.get("kind", "")).upper() in {"RAY_REQUIRED", "APPROVAL_REQUIRED"}:
            return (f"Ray — Nexus needs your review.\n\n{event.get('summary', 'A finished internal deliverable is ready for review.')}\n\n"
                    "No external action has been taken. Nexus will continue unrelated safe work.\n"
                    "Ray action: review the deliverable when available.")
        return f"Ray — Nexus needs attention.\n\n{event.get('summary', 'A critical operational condition was detected.')}\n\nNexus is recording the condition and continuing safe unrelated work where possible.\nRay action: review the operational update."
    if severity == "MATERIAL":
        return f"Ray — Nexus advanced.\n\n{event.get('summary', 'A material company milestone was verified.')}\n\nNo external action was taken. Nexus is selecting the next bounded internal step.\nRay action: none."
    return "Nexus update: systems are healthy and safe internal work is continuing. Nothing needs you."


def process_once(*, force_test: bool = False, force_digest: bool = False,
                 terminal_event: dict[str, Any] | None = None,
                 events: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    state = _read(STATE_PATH, {"schema_version": "nexus.proactive-communications.v2", "events": {}, "deliveries": {}, "last_notification_at": None, "last_digest_at": None})
    state["schema_version"] = "nexus.proactive-communications.v2"
    state.setdefault("events", {})
    state.setdefault("deliveries", {})
    state.setdefault("last_external_by_type", {})
    state.setdefault("resolved_states", {})
    chat = trusted_ray_chat()
    if not chat:
        state["last_suppression_reason"] = "TRUSTED_RAY_CHAT_NOT_PROVEN"
        _write(state)
        return {"status": "SUPPRESSED", "reason": "TRUSTED_RAY_CHAT_NOT_PROVEN"}
    if events is not None:
        events = [dict(item) for item in events if isinstance(item, dict)]
    elif terminal_event is not None:
        events = [{"kind": "TERMINAL_CERTIFICATION", **terminal_event}]
    else:
        events = [{"kind": "DEPARTMENT_MILESTONE", "test": True, "summary": "Explicit transport proof."}] if force_test else collect_events()
    results = []
    for event in events:
        severity = classify_event(event)
        event_type_fn = policy_event_type(event)
        material_state_hash = _material_state_hash(event)
        key = _hash({"event_type": event_type_fn, "material_state_hash": material_state_hash})
        prior = state["last_external_by_type"].get(event_type_fn, {})
        if prior.get("material_state_hash") == material_state_hash and prior.get("status") == "SENT":
            results.append({"event": key, "event_type": event_type_fn, "severity": severity, "status": "SUPPRESSED_NO_MATERIAL_CHANGE"})
            continue
        if not force_test and severity in {"ROUTINE", "SUPPRESSED"}:
            state["events"][key] = {"event_type": event_type_fn, "material_state_hash": material_state_hash, "severity": severity, "delivery_state": "SUPPRESSED", "suppression_reason": "routine_or_insufficient_evidence", "observed_at": now()}
            results.append({"event": key, "event_type": event_type_fn, "severity": severity, "status": "SUPPRESSED_ROUTINE"})
            continue
        text = executive_message(event, severity) if not event.get("test") else _message(event, severity)
        delivery = {"event_id": key, "event_type": event_type_fn, "material_state_hash": material_state_hash, "severity": severity, "status": "PENDING", "attempts": int(state["deliveries"].get(key, {}).get("attempts", 0)) + 1, "message_hash": _hash(text), "parent_goal": event.get("goal"), "source_receipt": event.get("source"), "created_at": now()}
        state["deliveries"][key] = delivery
        _write(state)
        ids = tg_send_message(chat, text)
        delivery.update({"status": "SENT" if ids else "FAILED", "message_ids": ids, "delivered_at": now() if ids else None})
        state["events"][key] = delivery
        state["last_external_by_type"][event_type_fn] = {
            "event_id": key,
            "material_state_hash": material_state_hash,
            "status": delivery["status"],
            "last_external_notification": delivery.get("delivered_at"),
        }
        state["last_notification_at"] = delivery.get("delivered_at")
        state["last_notified_event"] = key
        state["last_event_severity"] = severity
        _write(state)
        results.append({"event": key, "severity": severity, "status": delivery["status"], "message_ids": ids})
    # No recurring digest is permitted without explicit Ray approval recorded
    # outside this worker.  Heartbeats and internal reports continue normally.
    material_observed = any(classify_event(item) in {"MATERIAL", "CRITICAL"} for item in events)
    if terminal_event is None and not force_test and AUTOMATIC_REPORTS_APPROVED and material_observed and (force_digest or _digest_due(state)):
        digest_key = _hash({"kind": "DIGEST", "period": datetime.now(timezone.utc).strftime("%Y%m%d%H")})
        if digest_key not in state["events"]:
            text = _digest_message()
            ids = tg_send_message(chat, text)
            state["events"][digest_key] = {"event_id": digest_key, "severity": "ROUTINE", "status": "SENT" if ids else "FAILED", "message_hash": _hash(text), "message_ids": ids, "created_at": now()}
            state["last_digest_at"] = now()
            _write(state)
            results.append({"event": digest_key, "severity": "ROUTINE", "status": "SENT" if ids else "FAILED", "message_ids": ids})
    if terminal_event is None and not force_test and AUTOMATIC_REPORTS_APPROVED and material_observed and _morning_digest_due(state):
        local_date = datetime.now(ZoneInfo("America/Phoenix")).date().isoformat()
        digest_key = _hash({"kind": "MORNING_DIGEST", "local_date": local_date})
        if digest_key not in state["events"]:
            text = _morning_digest_message()
            ids = tg_send_message(chat, text)
            state["events"][digest_key] = {"event_id": digest_key, "severity": "ROUTINE", "status": "SENT" if ids else "FAILED", "message_hash": _hash(text), "message_ids": ids, "created_at": now()}
            state["last_morning_digest_local_date"] = local_date
            _write(state)
            results.append({"event": digest_key, "severity": "ROUTINE", "status": "SENT" if ids else "FAILED", "message_ids": ids})
    try:
        state_ref = str(STATE_PATH.relative_to(ROOT))
    except ValueError:
        state_ref = str(STATE_PATH)
    return {"status": "PASS" if any(x.get("status") == "SENT" for x in results) else "NO_SEND", "results": results, "state_path": state_ref}


def retry_retained_resource_alert(event_id: str) -> dict[str, Any]:
    """Retry the same persisted RESOURCE_ALARM delivery through Nova's sender."""
    state = _read(STATE_PATH, {})
    delivery = (state.get("deliveries") or {}).get(event_id)
    if not isinstance(delivery, dict):
        return {"status": "NOT_FOUND", "event_id": event_id}
    if delivery.get("event_type") != "RESOURCE_ALARM" or delivery.get("status") == "SENT":
        return {"status": "NOT_RETRYABLE", "event_id": event_id}
    chat = trusted_ray_chat()
    if not chat:
        return {"status": "SUPPRESSED", "reason": "TRUSTED_RAY_CHAT_NOT_PROVEN", "event_id": event_id}
    # The original event body was not persisted. Rebuild the notification from
    # the authoritative V5 checkpoint, preserving the original event ID/hash.
    campaign = _read(ROOT / "reports/certification/NEXUS_FULL_OWNER_REAL_WORLD_V5_STATE_20261010.json", {})
    summary = ("NotebookLM research discovery reached its configured daily internal resource limit. "
        "That Research branch is paused. Nexus is continuing independent V5 work and will resume the same "
        "Research job when the resource policy returns to NORMAL.")
    if campaign.get("CAMPAIGN_ID") != "NEXUS-OWNER-REAL-WORLD-V5-20261010-6fb82fd9":
        return {"status": "CAMPAIGN_IDENTITY_MISMATCH", "event_id": event_id}
    text = "Ray — Nexus resource alert.\n\n" + summary + "\n\nNo action is required from you."
    attempt = {"attempted_at": now(), "event_id": event_id,
        "reconstructed_from": "persisted_v5_checkpoint",
        "original_message_hash_preserved": delivery.get("message_hash"),
        "retry_message_hash": _hash(text), "destination_class": "TRUSTED_RAY_CHAT"}
    delivery.setdefault("retry_attempts", []).append(attempt)
    delivery["status"] = "RETRYING"
    delivery["attempts"] = int(delivery.get("attempts", 0)) + 1
    _write(state)
    ids = tg_send_message(chat, text)
    delivery["status"] = "SENT" if ids else "FAILED"
    delivery["message_ids"] = ids
    delivery["delivered_at"] = now() if ids else None
    delivery["last_retry_error"] = None if ids else "TELEGRAM_SEND_FAILED_OR_UNAUTHORIZED"
    state.setdefault("events", {})[event_id] = delivery
    state.setdefault("last_external_by_type", {})["RESOURCE_ALARM"] = {
        "event_id": event_id, "material_state_hash": delivery.get("material_state_hash"),
        "status": delivery["status"], "last_external_notification": delivery.get("delivered_at")}
    state["last_notification_at"] = delivery.get("delivered_at")
    state["last_notified_event"] = event_id
    _write(state)
    return {"status": delivery["status"], "event_id": event_id,
        "message_ids": ids, "attempts": delivery["attempts"],
        "reconstructed_from": "persisted_v5_checkpoint"}


if __name__ == "__main__":
    if "--retry-resource-event" in sys.argv:
        index=sys.argv.index("--retry-resource-event")
        if index+1>=len(sys.argv): raise SystemExit("--retry-resource-event requires the retained event ID")
        result=retry_retained_resource_alert(sys.argv[index+1])
    else:
        result=process_once(force_test="--send-test" in sys.argv, force_digest="--send-digest" in sys.argv)
    print(json.dumps(result, indent=2))
