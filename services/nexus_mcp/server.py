"""Local stdio MCP server for canonical, read-only Nexus state.

The MCP layer is an interface. It does not grant authority and never bypasses
the shared Nexus permission/canonical-read boundary.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from .auth import authorize_read
from .registry import CAPABILITY_MAP, read_canonical
from .schemas import TOOL_NAMES, unavailable

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as exc:  # pragma: no cover - exercised by deployment probe
    raise RuntimeError("MCP SDK is required to run the Nexus MCP server") from exc


RECEIPT_DIR = Path(os.getenv("NEXUS_MCP_RECEIPT_DIR", str(ROOT / "data/runtime/nexus_mcp_receipts")))
mcp = FastMCP("nexus")


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
        "data": data,
        "items": _items(result),
        "metadata": {
            "read_only": True,
            "canonical": True,
            "freshness": freshness,
            "item_count": len(_items(result)),
            "source_commit": provenance.get("source_commit"),
            "currentness": currentness,
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
    try:
        payload = _public_result(tool_name, read_canonical(tool_name, arguments))
    except Exception as exc:  # explicit unavailable result; never fabricate state
        payload = unavailable(tool_name, f"canonical read failed: {type(exc).__name__}")
    receipt = {
        "schema_version": "nexus.mcp-receipt.v1",
        "request_id": request_id,
        "tool_name": tool_name,
        "started_at": started,
        "completed_at": _now(),
        "canonical_source": CAPABILITY_MAP[tool_name],
        "result_status": payload.get("status"),
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
    return payload


def _register() -> None:
    @mcp.tool(name="nexus_get_reviews", description="Fresh volatile read: return only active Ray approvals requiring a decision. Call this for current review questions; do not reuse prior review context.")
    def nexus_get_reviews() -> dict[str, Any]:
        return _call("nexus_get_reviews")

    @mcp.tool(name="nexus_get_work_items", description="Fresh volatile read: return only current governed queued, running, blocked, or waiting work items.")
    def nexus_get_work_items() -> dict[str, Any]:
        return _call("nexus_get_work_items")

    @mcp.tool(name="nexus_get_blockers", description="Fresh volatile read: return only blockers proven by current governed approvals or blocked work orders. Historical reports are excluded.")
    def nexus_get_blockers() -> dict[str, Any]:
        return _call("nexus_get_blockers")

    @mcp.tool(name="nexus_get_opportunities", description="Fresh read: return only current eligible opportunities; accumulated research history and synthetic records are excluded.")
    def nexus_get_opportunities() -> dict[str, Any]:
        return _call("nexus_get_opportunities")

    @mcp.tool(name="nexus_get_business_state", description="Fresh composite read: return business components with independent source, timestamp, and currentness metadata.")
    def nexus_get_business_state() -> dict[str, Any]:
        return _call("nexus_get_business_state")

    @mcp.tool(name="nexus_get_system_health", description="Fresh live health read: distinguish runtime, process, service, worker capacity, and component status; do not infer Nexus outage from zero active process entries.")
    def nexus_get_system_health() -> dict[str, Any]:
        return _call("nexus_get_system_health")


_register()


if __name__ == "__main__":
    mcp.run(transport="stdio")
