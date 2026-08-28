"""Deterministic object-first resolution for Hermes control messages."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Mapping, Optional

from nexus_agent_platform.governed import work_orders

ROOT = Path(__file__).resolve().parents[2]
MANUAL_REPORT = ROOT / "reports/runtime/manual_e2e_latest.json"
REPAIR_ID = re.compile(r"\b([A-Z][A-Z0-9]+-[0-9]{3})\b")
WORK_ORDER_ID = re.compile(r"\b(wo_[a-f0-9]{20,})\b", re.I)
MISSION_ID = re.compile(r"\b(telegram-[0-9]{8,}-[a-f0-9]{8})\b", re.I)
RELEASE_ID = re.compile(r"\b(rel-telegram-[0-9]{8,}-[a-f0-9]{8}-[a-f0-9]{12})\b", re.I)


def _manual_repairs() -> list[dict[str, Any]]:
    try:
        report = __import__("json").loads(MANUAL_REPORT.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return []
    return [item for item in report.get("repair_queue", []) if isinstance(item, dict) and item.get("repair_id")]


def resolve_control_object(text: str, chat_context: Optional[Mapping[str, Any]] = None) -> dict[str, Any]:
    """Resolve explicit persisted objects before subsystem/fuzzy intent."""
    repair_match = REPAIR_ID.search(text.upper())
    work_match = WORK_ORDER_ID.search(text)
    mission_match = MISSION_ID.search(text)
    release_match = RELEASE_ID.search(text)
    repairs = _manual_repairs()
    if repair_match:
        repair_id = repair_match.group(1).upper()
        repair = next((item for item in repairs if str(item.get("repair_id", "")).upper() == repair_id), None)
        if not repair:
            return {"object_type": "UNKNOWN_REPAIR", "object_id": repair_id, "confidence": "EXPLICIT_IDENTIFIER"}
        state = next((item for item in work_orders.list_work_orders(limit=1000)
                      if item.get("inputs", {}).get("repair_id") == repair_id), {})
        return {"object_type": "REPAIR", "object_id": repair_id, "work_order_id": state.get("work_order_id"),
                "run_id": state.get("inputs", {}).get("run_id"), "handler": "GOVERNED_REPAIR_CONTROL",
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
    return {"object_type": "NONE", "handler": "FUZZY_INTENT", "confidence": "NONE"}
