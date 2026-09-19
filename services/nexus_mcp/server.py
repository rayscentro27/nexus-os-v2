"""Local stdio MCP server for canonical, read-only Nexus state.

The MCP layer is an interface. It does not grant authority and never bypasses
the shared Nexus permission/canonical-read boundary.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from .auth import authorize_read
from .registry import CAPABILITY_MAP, read_canonical
from .schemas import CAPABILITY_FRESHNESS, TOOL_NAMES, unavailable

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as exc:  # pragma: no cover - exercised by deployment probe
    raise RuntimeError("MCP SDK is required to run the Nexus MCP server") from exc


RECEIPT_DIR = Path(os.getenv("NEXUS_MCP_RECEIPT_DIR", str(ROOT / "data/runtime/nexus_mcp_receipts")))
mcp = FastMCP("nexus")

# Hermes may ask the same capability repeatedly while completing one model
# turn.  Reuse only successful current results within the explicit turn scope;
# never reuse across turns and never cache failures.
_TURN_RESULTS: dict[str, dict[str, dict[str, Any]]] = {}
_MAX_TURN_SCOPES = 32


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _items(result: dict[str, Any]) -> list[Any]:
    data = result.get("data")
    if isinstance(data, dict):
        for key in ("items", "pending_approvals", "work_orders", "blockers", "processes", "loops", "decisions"):
            value = data.get(key)
            if isinstance(value, list):
                return value
    return []


def _public_result(tool_name: str, result: dict[str, Any]) -> dict[str, Any]:
    """Normalize the shared envelope without exposing credentials or prose."""
    provenance = result.get("provenance") if isinstance(result.get("provenance"), dict) else {}
    data = result.get("data") if isinstance(result.get("data"), dict) else {}
    metadata = result.get("metadata") if isinstance(result.get("metadata"), dict) else {}
    filtered = data.get("filtered_counts") if isinstance(data.get("filtered_counts"), dict) else {}
    status = str(result.get("status", "UNKNOWN")).upper()
    freshness = result.get("freshness") or provenance.get("freshness") or "UNKNOWN"
    if tool_name == "nexus_get_business_state":
        currentness = "PARTIAL" if status in {"PARTIAL", "ERROR"} else "CURRENT"
        eligible = status in {"OK", "SUCCESS", "PARTIAL", "EMPTY"}
    elif tool_name == "nexus_get_system_health":
        currentness = "CURRENT" if freshness.lower() in {"live", "fresh"} else "UNKNOWN"
        eligible = currentness == "CURRENT"
    else:
        currentness = result.get("currentness") or ("CURRENT" if status in {"OK", "SUCCESS", "EMPTY"} else "UNKNOWN")
        eligible = result.get("live_response_eligible", currentness == "CURRENT")
    return {
        "status": "ok" if status in {"OK", "SUCCESS"} else status.lower(),
        "as_of": result.get("as_of") or provenance.get("source_timestamp") or _now(),
        "source": result.get("source_path") or result.get("source") or provenance.get("source") or "nexus_canonical_read_layer",
        "source_type": result.get("source_type") or provenance.get("source_type") or "canonical_nexus_read",
        "capability": tool_name,
        "currentness": currentness,
        "volatility": CAPABILITY_FRESHNESS.get(tool_name, "UNKNOWN"),
        "live_response_eligible": eligible,
        "data": data,
        "items": _items(result),
        "metadata": {
            "read_only": True,
            "canonical": True,
            "freshness": freshness,
            "item_count": len(_items(result)),
            "source_commit": provenance.get("source_commit"),
            "currentness": currentness,
            "volatility": CAPABILITY_FRESHNESS.get(tool_name, "UNKNOWN"),
            "live_response_eligible": eligible,
            "filtered_historical_count": data.get("filtered_historical_count", filtered.get("REAL_HISTORICAL", 0)),
            "filtered_synthetic_count": data.get("filtered_synthetic_count", filtered.get("SYNTHETIC", 0)),
            "filtered_other_noncurrent_count": sum(value for key, value in filtered.items() if key not in {"REAL_CURRENT", "REAL_HISTORICAL", "SYNTHETIC"}),
            **metadata,
        },
        "error": result.get("error") or (result.get("errors") or [None])[0],
    }


def _call(tool_name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    authorize_read(tool_name)
    request_id = f"nexus-mcp-{uuid.uuid4().hex}"
    started = _now()
    turn_id = os.getenv("NEXUS_MCP_TURN_ID") or None
    update_id = os.getenv("NEXUS_MCP_UPDATE_ID") or None
    trace_id = os.getenv("NOVA_LANGFUSE_TRACE_ID") or None
    # Objective-scoped reads must not collide with an earlier global read in
    # the same Hermes turn.  The argument fingerprint is part of the cache
    # key; successful reads remain deduplicated only for the exact request.
    cache_key = tool_name + (":" + json.dumps(arguments or {}, sort_keys=True) if arguments else "")
    cached = _TURN_RESULTS.get(turn_id, {}).get(cache_key) if turn_id else None
    deduplicated = cached is not None
    try:
        if cached is not None:
            payload = json.loads(json.dumps(cached))
            payload["metadata"]["deduplicated"] = True
        else:
            payload = _public_result(tool_name, read_canonical(tool_name, arguments))
            if turn_id and payload.get("status") in {"ok", "empty", "partial"}:
                if turn_id not in _TURN_RESULTS:
                    if len(_TURN_RESULTS) >= _MAX_TURN_SCOPES:
                        _TURN_RESULTS.pop(next(iter(_TURN_RESULTS)))
                    _TURN_RESULTS[turn_id] = {}
                _TURN_RESULTS[turn_id][cache_key] = payload
    except Exception as exc:  # explicit unavailable result; never fabricate state
        payload = unavailable(tool_name, f"canonical read failed: {type(exc).__name__}")
    receipt = {
        "schema_version": "nexus.mcp-receipt.v1",
        "request_id": request_id,
        "tool_name": tool_name,
        "turn_id": turn_id,
        "update_id": update_id,
        "trace_id": trace_id,
        "started_at": started,
        "completed_at": _now(),
        "canonical_source": CAPABILITY_MAP[tool_name],
        "result_status": payload.get("status"),
        "deduplicated": deduplicated,
        "item_count": payload.get("metadata", {}).get("item_count", 0),
        "currentness_result": payload.get("metadata", {}).get("currentness", "UNKNOWN"),
        "eligible_item_count": payload.get("metadata", {}).get("item_count", 0),
        "filtered_historical_count": payload.get("metadata", {}).get("filtered_historical_count", 0),
        "filtered_synthetic_count": payload.get("metadata", {}).get("filtered_synthetic_count", 0),
        "filtered_other_noncurrent_count": payload.get("metadata", {}).get("filtered_other_noncurrent_count", 0),
        "error": payload.get("error"),
        "read_only": True,
        "authority_owner": "Nexus",
    }
    receipt["receipt_hash"] = hashlib.sha256(json.dumps(receipt, sort_keys=True).encode()).hexdigest()
    RECEIPT_DIR.mkdir(parents=True, exist_ok=True)
    (RECEIPT_DIR / f"{request_id}.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    payload["request_id"] = request_id
    payload["turn_id"] = turn_id
    payload["update_id"] = update_id
    payload["trace_id"] = trace_id
    payload.setdefault("metadata", {})["started_at"] = started
    payload["metadata"]["completed_at"] = receipt["completed_at"]
    return payload


def _register() -> None:
    @mcp.tool(name="nexus_get_reviews", description="VOLATILE current-state read: return only active Ray approvals requiring a decision. For present/current questions, call again; prior answers are not authoritative.")
    def nexus_get_reviews() -> dict[str, Any]:
        return _call("nexus_get_reviews")

    @mcp.tool(name="nexus_get_work_items", description="VOLATILE current-state read: return only current governed queued, running, blocked, or waiting work items. Re-read for present state.")
    def nexus_get_work_items() -> dict[str, Any]:
        return _call("nexus_get_work_items")

    @mcp.tool(name="nexus_get_blockers", description="VOLATILE current-state read: return only blockers proven by current governed approvals or blocked work orders; historical reports are excluded. Re-read for present state.")
    def nexus_get_blockers() -> dict[str, Any]:
        return _call("nexus_get_blockers")

    @mcp.tool(name="nexus_get_opportunities", description="VOLATILE Nexus operational-state read: return only current eligible opportunity records already present in Nexus; history and synthetic records are excluded. This does not generate ideas, evaluate hypothetical businesses, provide market research, or give general strategy advice. Re-read for present state.")
    def nexus_get_opportunities() -> dict[str, Any]:
        return _call("nexus_get_opportunities")

    @mcp.tool(name="nexus_get_business_state", description="VOLATILE composite Nexus operational-state read: return current governed company components with independent source, timestamp, and currentness metadata. Use only when the user asks about what Nexus/company operations currently contain or report; this is not general business advice, strategy, market research, or hypothetical idea evaluation. Re-read present state.")
    def nexus_get_business_state() -> dict[str, Any]:
        return _call("nexus_get_business_state")

    @mcp.tool(name="nexus_get_system_health", description="VOLATILE live health read: distinguish runtime, process, service, worker capacity, and component status. Re-read for present health; do not infer outage from zero process entries.")
    def nexus_get_system_health() -> dict[str, Any]:
        return _call("nexus_get_system_health")

    @mcp.tool(name="nexus_get_research_state", description="VOLATILE current Research read. Supply objective_id for objective-first lineage resolution; without it returns bounded global operational state. Historical briefs never satisfy an objective-scoped read.")
    def nexus_get_research_state(objective_id: str = "") -> dict[str, Any]:
        return _call("nexus_get_research_state", {"objective_id": objective_id} if objective_id else {})

    @mcp.tool(name="nexus_get_alpha_review", description="VOLATILE bounded Alpha read. Supply objective_id to resolve the latest Alpha evaluation/receipt tied to that objective lineage; never substitute unrelated historical records.")
    def nexus_get_alpha_review(objective_id: str = "") -> dict[str, Any]:
        return _call("nexus_get_alpha_review", {"objective_id": objective_id} if objective_id else {})

    @mcp.tool(
        name="nexus_delegate_specialist",
        description=(
            "Use when Nova needs one bounded specialist perspective on a current "
            "Nexus question. Provide the specialist enum and a concrete objective; "
            "returns one current governed read plus a delegation receipt. Read-only: "
            "no shell, writes, publication, payment, trading, or authority changes."
        ),
    )
    def nexus_delegate_specialist(
        specialist: Literal["SYSTEM", "RESEARCH", "ALPHA", "FINANCE", "GROWTH", "CREATIVE", "JAX", "TRADING"],
        objective: str,
        conversation_id: str = "",
    ) -> dict[str, Any]:
        return _delegate_specialist(specialist, objective, conversation_id=conversation_id)


def _delegate_specialist(specialist: str, objective: str, *, conversation_id: str = "") -> dict[str, Any]:
    specialist_key = str(specialist or "").strip().upper()
    objective_text = str(objective or "").strip()[:500]
    routes = {
        "SYSTEM": "nexus_get_system_health",
        "RESEARCH": "nexus_get_research_state",
        "ALPHA": "nexus_get_alpha_review",
        "FINANCE": "nexus_get_business_state",
        "GROWTH": "nexus_get_opportunities",
        "CREATIVE": "nexus_get_business_state",
        "JAX": "nexus_get_system_health",
        "TRADING": "nexus_get_business_state",
    }
    if specialist_key not in routes or not objective_text:
        return {
            "status": "rejected",
            "error": "specialist/objective_not_allowlisted_or_missing",
            "allowed_specialists": sorted(routes),
            "authority": "Nexus",
            "read_only": True,
        }

    underlying = routes[specialist_key]
    objective_match = re.search(r"(?:objective_id|objective)\s*[=:]\s*([A-Za-z0-9_.:-]{3,160})", objective_text, re.I)
    result = (_call(underlying, {"objective_id": objective_match.group(1)}
                    if objective_match else {}) if objective_match
              else _call(underlying))
    delegation_id = f"nexus-delegation-{uuid.uuid4().hex}"
    conversation_id = str(conversation_id or os.getenv("NEXUS_MCP_CONVERSATION_ID") or "").strip()[:120] or None
    data = result.get("data") if isinstance(result.get("data"), dict) else {}
    successful = result.get("status") in {"ok", "success", "partial", "empty"}
    if specialist_key == "SYSTEM":
        execution_type = "FRESH_EXECUTION"
        source_type = "LIVE_RUNTIME"
        next_action = "Use the timestamped health result for the current request."
    elif specialist_key == "RESEARCH":
        execution_type = "CURRENT_READ"
        source_type = "GOVERNED_STATE"
        next_action = "Continue bounded evidence selection for open Research V2 investigations."
    elif specialist_key == "ALPHA":
        execution_type = "ANALYSIS"
        source_type = "GOVERNED_STATE"
        next_action = data.get("evaluation", {}).get("next_action") or "Resolve evidence gaps before consequential action."
    else:
        execution_type = "CURRENT_READ"
        source_type = "GOVERNED_STATE"
        next_action = "No further action is recorded by this read-only delegation."
    alpha_receipt_id = data.get("alpha_receipt_id")
    evidence_refs = [
        value for value in (
            result.get("source"),
            result.get("request_id"),
            data.get("finding_reference"),
            alpha_receipt_id,
        ) if value
    ]
    delegation_status = "COMPLETED" if successful else "BLOCKED"
    receipt = {
        "schema_version": "nexus.department-delegation-receipt.v1",
        "department": "SYSTEMS_ENGINEERING" if specialist_key == "SYSTEM" else specialist_key,
        "request_id": delegation_id,
        "conversation_id": conversation_id,
        "work_order_id": data.get("work_order_id"),
        "objective_id": data.get("objective_id"),
        "started_at": result.get("metadata", {}).get("started_at") or _now(),
        "completed_at": _now(),
        "execution_type": execution_type,
        "source_type": source_type,
        "freshness": "FRESH" if specialist_key in {"SYSTEM", "RESEARCH", "ALPHA"} and successful else (result.get("metadata", {}).get("freshness") or result.get("currentness") or "UNKNOWN"),
        "status": delegation_status,
        "result_summary": {
            "objective": objective_text,
            "result_status": result.get("status"),
            "overall_status": data.get("overall_status"),
            "research_work_state": data.get("research_work_state"),
            "finding_reference": data.get("finding_reference"),
            "alpha_receipt_id": alpha_receipt_id,
            "error": result.get("error"),
        },
        "evidence_refs": evidence_refs,
        "receipt_id": delegation_id,
        "next_action": next_action,
        "underlying_tool": underlying,
        "underlying_request_id": result.get("request_id"),
        "session_id": conversation_id,
        "read_only": True,
        "authority_owner": "Nexus",
    }
    receipt["receipt_hash"] = hashlib.sha256(json.dumps(receipt, sort_keys=True).encode()).hexdigest()
    RECEIPT_DIR.mkdir(parents=True, exist_ok=True)
    (RECEIPT_DIR / f"{delegation_id}.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return {
        "status": "delegated",
        "delegation_id": delegation_id,
        "specialist": specialist_key,
        "objective": objective_text,
        "result": result,
        "delegation_receipt": json.loads((RECEIPT_DIR / f"{delegation_id}.json").read_text(encoding="utf-8")),
        "provenance": {"source": "nexus_canonical_read_layer", "read_only": True},
    }


def _register_google_read_tools() -> None:
    """Expose the existing Google read bridge through the canonical MCP tunnel."""
    @mcp.tool(name="gmail_search", description="READ ONLY Gmail search through the governed Google bridge; never sends or mutates mail.")
    def gmail_search(query: str, max_results: int = 10) -> dict[str, Any]:
        from services.google_mcp import server as google_server
        return google_server.gmail_search(query, max_results)

    @mcp.tool(name="gmail_read_message", description="READ ONLY Gmail message metadata/snippet through the governed Google bridge.")
    def gmail_read_message(message_id: str) -> dict[str, Any]:
        from services.google_mcp import server as google_server
        return google_server.gmail_read_message(message_id)

    @mcp.tool(name="gmail_read_thread", description="READ ONLY Gmail thread metadata/snippets through the governed Google bridge.")
    def gmail_read_thread(thread_id: str) -> dict[str, Any]:
        from services.google_mcp import server as google_server
        return google_server.gmail_read_thread(thread_id)

    @mcp.tool(name="calendar_search_events", description="READ ONLY Calendar event search through the governed Google bridge.")
    def calendar_search_events(start_time: str, end_time: str, query: str | None = None, max_results: int = 50) -> dict[str, Any]:
        from services.google_mcp import server as google_server
        return google_server.calendar_search_events(start_time, end_time, query, max_results)

    @mcp.tool(name="calendar_read_event", description="READ ONLY Calendar event lookup through the governed Google bridge.")
    def calendar_read_event(event_id: str, calendar_id: str = "primary") -> dict[str, Any]:
        from services.google_mcp import server as google_server
        return google_server.calendar_read_event(event_id, calendar_id)

    @mcp.tool(name="calendar_get_availability", description="READ ONLY Calendar availability projection through the governed Google bridge.")
    def calendar_get_availability(start_time: str, end_time: str, calendar_ids: list[str] | None = None) -> dict[str, Any]:
        from services.google_mcp import server as google_server
        return google_server.calendar_get_availability(start_time, end_time, calendar_ids)

    @mcp.tool(name="drive_search", description="READ ONLY Drive metadata search through the governed Google bridge; never uploads, edits, moves, shares, or deletes.")
    def drive_search(query: str | None = None, max_results: int = 25) -> dict[str, Any]:
        from services.google_mcp import server as google_server
        return google_server.drive_search(query, max_results)

    @mcp.tool(name="drive_read_file", description="READ ONLY Drive metadata and bounded text read through the governed Google bridge.")
    def drive_read_file(file_id: str, include_text: bool = False) -> dict[str, Any]:
        from services.google_mcp import server as google_server
        return google_server.drive_read_file(file_id, include_text)


_register()
_register_google_read_tools()


if __name__ == "__main__":
    mcp.run(transport="stdio")
