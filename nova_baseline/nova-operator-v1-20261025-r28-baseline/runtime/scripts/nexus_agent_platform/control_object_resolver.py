"""Deterministic object-first resolution for Hermes control messages."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Optional

from nexus_agent_platform.governed import approvals, persistence, work_orders

ROOT = Path(__file__).resolve().parents[2]
MANUAL_REPORT = ROOT / "reports/runtime/manual_e2e_latest.json"
REPAIR_ID = re.compile(r"\b([A-Z][A-Z0-9]+-[0-9]{3})\b")
WORK_ORDER_ID = re.compile(r"\b(wo_[a-f0-9]{20,})\b", re.I)
MISSION_ID = re.compile(r"\b(telegram-[0-9]{8,}-[a-f0-9]{8})\b", re.I)
RELEASE_ID = re.compile(r"\b(rel-telegram-[0-9]{8,}-[a-f0-9]{8}-[a-f0-9]{12})\b", re.I)
CONTROL_CONTEXT_PATH = ROOT / "data/runtime/nexus_operational_control_context.json"
CONTEXT_TTL_SECONDS = 900


def load_control_context(chat_id: Any) -> dict[str, Any]:
    """Load short-lived, redacted object context for one authorized chat."""
    try:
        data = json.loads(CONTROL_CONTEXT_PATH.read_text(encoding="utf-8"))
        item = data.get(str(chat_id), {})
        saved = datetime.fromisoformat(str(item.get("updated_at", "")).replace("Z", "+00:00"))
        if (datetime.now(timezone.utc) - saved).total_seconds() > CONTEXT_TTL_SECONDS:
            return {}
        return {k: item[k] for k in ("object_type", "object_id", "repair_id", "work_order_id", "run_id", "handler", "confidence") if k in item}
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return {}


def save_control_context(chat_id: Any, control: Mapping[str, Any]) -> None:
    """Persist only non-secret control identity, never message/model content."""
    try:
        data = json.loads(CONTROL_CONTEXT_PATH.read_text(encoding="utf-8")) if CONTROL_CONTEXT_PATH.exists() else {}
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        data = {}
    allowed = {k: control[k] for k in ("object_type", "object_id", "repair_id", "work_order_id", "run_id", "handler", "confidence") if control.get(k) is not None}
    allowed["updated_at"] = datetime.now(timezone.utc).isoformat()
    data[str(chat_id)] = allowed
    CONTROL_CONTEXT_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONTROL_CONTEXT_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def is_operational_control_intent(text: str, control: Optional[Mapping[str, Any]] = None) -> bool:
    """Classify operational/control questions without enumerating phrases."""
    normalized = re.sub(r"[^a-z0-9_ -]", " ", str(text).lower())
    control_words = {"status", "running", "happening", "working", "waiting", "queued", "continue", "resume", "approval", "approvals", "need", "doing", "loops", "repair"}
    object_words = {"voice", "nexus", "operator", "repair", "work", "system", "loop", "loops", "approval", "approvals"}
    return (control or {}).get("object_type") in {"REPAIR", "UNKNOWN_REPAIR", "UNKNOWN_WORK_ORDER"} or (bool(control_words & set(normalized.split())) and bool(object_words & set(normalized.split())))


def format_repair_status(repair: Mapping[str, Any]) -> str:
    return (f"{repair['repair_id']}\nWork order: {repair.get('work_order_id', 'UNKNOWN')}\n"
            f"State: {repair.get('lifecycle_state', 'UNKNOWN')}\n"
            f"Access: {repair.get('access_state', 'UNKNOWN')}\n"
            "Deployment: not authorized\nNo engineering execution started.")


def _manual_repairs() -> list[dict[str, Any]]:
    try:
        report = __import__("json").loads(MANUAL_REPORT.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return []
    return [item for item in report.get("repair_queue", []) if isinstance(item, dict) and item.get("repair_id")]


def get_repair(repair_id: str) -> Optional[dict[str, Any]]:
    """Return one repair view from canonical governed state.

    Certification JSON is evidence only. Operational identity and lineage are
    resolved from the governed work-order/approval stores plus the dedicated
    repair runtime state, all under the canonical repository root.
    """
    normalized = str(repair_id).upper()
    candidates = [item for item in work_orders.list_work_orders(limit=1000)
                  if str((item.get("inputs") or {}).get("repair_id", "")).upper() == normalized]
    if not candidates:
        # A queued manual repair may have approval evidence before a work order
        # exists; only expose it when it is explicitly present in the active
        # certification queue, never from an arbitrary fuzzy string.
        if not any(str(item.get("repair_id", "")).upper() == normalized for item in _manual_repairs()):
            return None
    order = candidates[0] if candidates else {}
    inputs = order.get("inputs") or {}
    run_id = inputs.get("run_id")
    state: dict[str, Any] = {}
    if normalized == "VOICE-001":
        try:
            state = __import__("json").loads((ROOT / "reports/runtime/voice_repair_latest.json").read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            state = {}
        run_id = run_id or state.get("run_id")
    approval = approvals.get_approval(order.get("approval_id")) if order.get("approval_id") else None
    return {
        "repair_id": normalized,
        "run_id": run_id,
        "work_order_id": order.get("work_order_id") or state.get("work_order_id"),
        "approval_state": (approval or {}).get("status") or ("PRESERVED" if normalized in {"VOICE-001"} else "UNKNOWN"),
        "authority_scope": [normalized] if normalized == "VOICE-001" else [],
        "lifecycle_state": state.get("state") or order.get("status") or "UNKNOWN",
        "current_stage": state.get("runtime_pickup_state") or state.get("executor") or "UNKNOWN",
        "worker_state": state.get("worker_state") or state.get("executor") or "NONE",
        "access_state": state.get("access_state") or "AVAILABLE_REMOTE_NETLIFY" if normalized == "VOICE-001" else "UNKNOWN",
        "human_gate": state.get("deployment") or "SEPARATE_APPROVAL_REQUIRED" if normalized == "VOICE-001" else "UNKNOWN",
        "retry_state": state.get("failure") or "NONE",
        "created_at": order.get("created_at"),
        "updated_at": state.get("updated_at") or order.get("created_at"),
        "evidence_refs": ["reports/runtime/manual_e2e_latest.json", "reports/runtime/voice_repair_latest.json"] if normalized == "VOICE-001" else [],
        "values_included": False,
    }


def resolve_control_object(text: str, chat_context: Optional[Mapping[str, Any]] = None) -> dict[str, Any]:
    """Resolve explicit persisted objects before subsystem/fuzzy intent."""
    repair_match = REPAIR_ID.search(text.upper())
    work_match = WORK_ORDER_ID.search(text)
    mission_match = MISSION_ID.search(text)
    release_match = RELEASE_ID.search(text)
    if repair_match:
        repair_id = repair_match.group(1).upper()
        repair = get_repair(repair_id)
        if not repair:
            return {"object_type": "UNKNOWN_REPAIR", "object_id": repair_id, "confidence": "EXPLICIT_IDENTIFIER"}
        return {"object_type": "REPAIR", "object_id": repair_id, "work_order_id": repair.get("work_order_id"),
                "run_id": repair.get("run_id"), "handler": "GOVERNED_REPAIR_CONTROL",
                "confidence": "EXPLICIT_IDENTIFIER"}
    if work_match:
        order = work_orders.get_work_order(work_match.group(1))
        if not order:
            return {"object_type": "UNKNOWN_WORK_ORDER", "object_id": work_match.group(1), "confidence": "EXPLICIT_IDENTIFIER"}
        inputs = order.get("inputs") or {}
        return {"object_type": "REPAIR" if inputs.get("repair_id") else "WORK_ORDER", "object_id": work_match.group(1),
                "repair_id": inputs.get("repair_id"), "work_order_id": work_match.group(1),
                "run_id": inputs.get("run_id"), "handler": "GOVERNED_REPAIR_CONTROL" if inputs.get("repair_id") else "GOVERNED_WORK_ORDER_CONTROL",
                "confidence": "EXPLICIT_IDENTIFIER"}
    if mission_match:
        return {"object_type": "MISSION", "object_id": mission_match.group(1), "handler": "PRODUCT_EVOLUTION_CONTROL", "confidence": "EXPLICIT_IDENTIFIER"}
    if release_match:
        return {"object_type": "RELEASE", "object_id": release_match.group(1), "handler": "PRODUCT_EVOLUTION_CONTROL", "confidence": "EXPLICIT_IDENTIFIER"}
    context = chat_context or {}
    if context.get("object_type") in {"REPAIR", "WORK_ORDER", "MISSION", "RELEASE"}:
        return dict(context)
    # If the user names a unique active repair domain but has no saved context,
    # recover only the canonical active object; never create from fuzzy text.
    words = set(re.sub(r"[^a-z0-9 -]", " ", str(text).lower()).split())
    if words & {"voice"} and words & {"status", "running", "happening", "working", "waiting", "queued", "continue", "resume", "repair", "doing"}:
        repair = get_repair("VOICE-001")
        if repair and str(repair.get("lifecycle_state", "")).upper() not in {"PASS", "COMPLETED", "CANCELLED"}:
            return {"object_type": "REPAIR", "object_id": "VOICE-001", "repair_id": "VOICE-001",
                    "work_order_id": repair.get("work_order_id"), "run_id": repair.get("run_id"),
                    "handler": "GOVERNED_REPAIR_CONTROL", "confidence": "ACTIVE_OBJECT_CONTEXT"}
    return {"object_type": "NONE", "handler": "FUZZY_INTENT", "confidence": "NONE"}
