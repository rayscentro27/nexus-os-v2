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
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from nexus_agent_platform.runtime.paths import nexus_research_state_path
from nexus_agent_platform.supabase_egress_guard import mcp_read_egress_scope

from .auth import authorize_action, authorize_read
from .registry import CAPABILITY_MAP, read_canonical
from .schemas import CAPABILITY_FRESHNESS, SYSTEMS_HOST_CONTROL_TOOL_NAMES, TOOL_NAMES, unavailable

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as exc:  # pragma: no cover - exercised by deployment probe
    raise RuntimeError("MCP SDK is required to run the Nexus MCP server") from exc


RECEIPT_DIR = Path(os.getenv("NEXUS_MCP_RECEIPT_DIR") or
                    nexus_research_state_path("runtime", "nexus_mcp_receipts"))
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


def _scoped_read(fn, *args: Any, **kwargs: Any):
    """Run one MCP read inside its own bounded egress scope (same policy as canonical reads).

    The bridge is long-lived; without a scope, Supabase calls fall back to the feeder's
    process-wide identity (feeder-process-<pid>), which is sized for short-lived one-shot
    entry points and would accumulate every poll for the life of the bridge process."""
    with mcp_read_egress_scope(f"nexus-mcp-read-{uuid.uuid4().hex}"):
        return fn(*args, **kwargs)


def _get_directive_events(since: str = "", limit: int = 20) -> dict[str, Any]:
    """Recent DEPARTMENT_DIRECTIVE rows (directive projection only) for Nova's proactive notifier."""
    import urllib.parse
    from datetime import datetime, timedelta, timezone
    from nexus_agent_platform.durable_jobs import default_store
    store = default_store()
    since = since or (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    n = max(1, min(int(limit or 20), 50))
    rows = store._request("nexus_durable_jobs?job_type=eq.DEPARTMENT_DIRECTIVE&created_at=gte." + urllib.parse.quote(since, safe="")
                          + f"&select=job_id,directive:governance_context->directive&order=created_at.asc&limit={n}") or []
    return {"tool_name": "nexus_get_directive_events", "status": "OK" if rows else "EMPTY", "rows": rows, "since": since,
            "metadata": {"read_only": True, "canonical": True, "source": "nexus_durable_jobs.governance_context.directive", "freshness": "live"}}


def _create_department_directive(target_department: str, objective: str, task: str, required_output: list[str],
                                 project_id: str = "", evidence_references: list[str] | None = None,
                                 inputs: dict[str, Any] | None = None, restrictions: list[str] | None = None,
                                 success_criteria: list[str] | None = None, parent_request_id: str = "",
                                 business_id: str = "") -> dict[str, Any]:
    """Create ONE durable department directive (generic). Creates work; never executes it."""
    from nexus_agent_platform import department_directive as directive_mod
    from nexus_agent_platform.durable_jobs import default_store
    try:
        d = directive_mod.build_directive(target_department=target_department, objective=objective, task=task,
                                          required_output=required_output, project_id=project_id, source_department="NOVA",
                                          inputs=inputs, evidence_references=evidence_references, restrictions=restrictions,
                                          success_criteria=success_criteria, business_id=business_id)
    except ValueError as exc:
        return {"status": "rejected", "error": str(exc)}
    job, d = directive_mod.create_directive(default_store(), d, correlation_id=parent_request_id or None)
    return {"status": "queued", "directive_id": d["directive_id"], "project_id": d["project_id"], "business_id": d.get("business_id"),
            "target_department": d["target_department"], "directive_status": d["status"], "job_state": job.state,
            "execution": "durable dispatcher executes it; continuation to the next department is automatic",
            "spend_allowed": False, "publication_allowed": False}


def _get_department_directive(directive_id: str) -> dict[str, Any]:
    from nexus_agent_platform.durable_jobs import default_store
    store = default_store()
    job = store.get(str(directive_id or "").strip())
    d = ((job.governance_context or {}).get("directive") if job else None) or None
    if not d:
        return {"tool_name": "nexus_get_department_directive", "status": "NOT_FOUND", "data": {"directive_id": directive_id}, "items": [],
                "metadata": {"read_only": True}, "error": "directive_not_found"}
    children = []
    for ev in d.get("events") or []:
        if ev.get("child_directive_id"):
            cj = store.get(ev["child_directive_id"])
            cd = ((cj.governance_context or {}).get("directive") if cj else None) or {}
            children.append({"directive_id": ev["child_directive_id"], "department": cd.get("target_department"), "status": cd.get("status"),
                             "next_action": cd.get("next_action"), "last_event": (cd.get("events") or [{}])[-1]})
    data = {k: d.get(k) for k in ("directive_id", "project_id", "business_id", "parent_directive_id", "source_department", "target_department", "objective",
                                  "status", "created_at", "started_at", "completed_at", "next_department", "next_action", "approval_requirement")}
    data.update({"job_state": job.state, "result": d.get("result"), "events": d.get("events"), "children": children})
    return {"tool_name": "nexus_get_department_directive", "status": "OK", "data": data, "items": children,
            "metadata": {"read_only": True, "canonical": True, "source": "nexus_durable_jobs.governance_context.directive", "freshness": "live"}, "error": None}


def _project_read(tool_name: str, fn, **kwargs: Any) -> dict[str, Any]:
    """Read-only project-store call with the standard read receipt (no cache: project state is volatile)."""
    from services.nexus_mcp import project_reader
    authorize_read(tool_name)
    request_id = f"nexus-mcp-{uuid.uuid4().hex}"
    started = _now()
    try:
        payload = _scoped_read(getattr(project_reader, fn), **kwargs)
    except Exception as exc:  # explicit unavailable result; never fabricate state
        payload = unavailable(tool_name, f"project read failed: {type(exc).__name__}")
    receipt = {"schema_version": "nexus.mcp-receipt.v1", "request_id": request_id, "tool_name": tool_name,
               "turn_id": os.getenv("NEXUS_MCP_TURN_ID") or None, "update_id": os.getenv("NEXUS_MCP_UPDATE_ID") or None,
               "started_at": started, "completed_at": _now(), "canonical_source": "business_loop_project_store",
               "result_status": payload.get("status"), "item_count": payload.get("metadata", {}).get("item_count", 0),
               "error": payload.get("error"), "read_only": True, "authority_owner": "Nexus"}
    receipt["receipt_hash"] = hashlib.sha256(json.dumps(receipt, sort_keys=True).encode()).hexdigest()
    RECEIPT_DIR.mkdir(parents=True, exist_ok=True)
    (RECEIPT_DIR / f"{request_id}.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return payload


def _research_room_read(tool_name: str, fn, **kwargs: Any) -> dict[str, Any]:
    """Read-only research-room call with standard read receipt."""
    authorize_read(tool_name)
    request_id = f"nexus-mcp-{uuid.uuid4().hex}"
    started = _now()
    try:
        payload = _scoped_read(fn, **kwargs)
    except Exception as exc:
        payload = unavailable(tool_name, f"research room read failed: {type(exc).__name__}")
    receipt = {
        "schema_version": "nexus.mcp-receipt.v1",
        "request_id": request_id,
        "tool_name": tool_name,
        "turn_id": os.getenv("NEXUS_MCP_TURN_ID") or None,
        "update_id": os.getenv("NEXUS_MCP_UPDATE_ID") or None,
        "started_at": started,
        "completed_at": _now(),
        "canonical_source": "research_room_store",
        "result_status": payload.get("status"),
        "item_count": payload.get("metadata", {}).get("item_count", len(payload.get("rooms", [])) if "rooms" in payload else 1),
        "error": payload.get("error"),
        "read_only": True,
        "authority_owner": "Nexus",
    }
    receipt["receipt_hash"] = hashlib.sha256(json.dumps(receipt, sort_keys=True).encode()).hexdigest()
    RECEIPT_DIR.mkdir(parents=True, exist_ok=True)
    (RECEIPT_DIR / f"{request_id}.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return payload


def _list_research_rooms(status: str = "", query: str = "", limit: int = 20) -> dict[str, Any]:
    from nexus_agent_platform.research_room.room_manager import ResearchRoomManager
    mgr = ResearchRoomManager()
    rooms = mgr.list_rooms(status=status or None, query=query or None, limit=limit)
    return {
        "tool_name": "nexus_list_research_rooms",
        "status": "OK" if rooms else "EMPTY",
        "rooms": rooms,
        "count": len(rooms),
        "metadata": {"read_only": True, "canonical": True, "source": "research_room_store", "freshness": "live", "item_count": len(rooms)},
        "error": None,
    }


def _get_research_room(room_id: str) -> dict[str, Any]:
    from nexus_agent_platform.research_room.room_manager import ResearchRoomManager
    mgr = ResearchRoomManager()
    room = mgr.get_room(room_id)
    if not room:
        return {
            "tool_name": "nexus_get_research_room",
            "status": "NOT_FOUND",
            "room_id": room_id,
            "metadata": {"read_only": True, "item_count": 0},
            "error": "research_room_not_found",
        }
    return {
        "tool_name": "nexus_get_research_room",
        "status": "OK",
        "room": room,
        "metadata": {"read_only": True, "canonical": True, "source": "research_room_store", "freshness": "live", "item_count": 1},
        "error": None,
    }


def _create_research_room(title: str, source_content: str = "", source_type: str = "TEXT", source_title: str = "") -> dict[str, Any]:
    from nexus_agent_platform.research_room.room_manager import ResearchRoomManager
    mgr = ResearchRoomManager()
    room = mgr.create_room(title=title)
    if source_content:
        room = mgr.add_source(room["room_id"], source_type=source_type or "TEXT", content_or_url=source_content, title=source_title or None)
    return {
        "tool_name": "nexus_create_research_room",
        "status": "CREATED",
        "room_id": room["room_id"],
        "room": room,
        "read_only": False,
        "authority_owner": "Nexus",
    }


def _add_room_source(room_id: str, source_type: str, content_or_url: str, title: str = "") -> dict[str, Any]:
    from nexus_agent_platform.research_room.room_manager import ResearchRoomManager
    mgr = ResearchRoomManager()
    room = mgr.add_source(room_id=room_id, source_type=source_type, content_or_url=content_or_url, title=title or None)
    return {
        "tool_name": "nexus_add_room_source",
        "status": "OK",
        "room_id": room_id,
        "room": room,
        "read_only": False,
        "authority_owner": "Nexus",
    }


def _ask_alpha_research_room(room_id: str, question: str) -> dict[str, Any]:
    from nexus_agent_platform.research_room.room_manager import ResearchRoomManager
    mgr = ResearchRoomManager()
    room = mgr.get_room(room_id)
    if not room:
        raise LookupError(f"RESEARCH_ROOM_NOT_FOUND: {room_id}")
    # Public reads inherit the existing room/workflow execution scope. The
    # bounded MCP action identity remains the provider-governance job id.
    fields = ("NEXUS_CORRELATION_ID", "NEXUS_DEPARTMENT", "NEXUS_JOB_TYPE",
              "NEXUS_PROJECT_ID", "NEXUS_RESEARCH_ROOM_CALL_ID")
    previous = {key: os.environ.get(key) for key in fields}
    try:
        metadata = room.get("metadata") if isinstance(room.get("metadata"), dict) else {}
        workflow_id = str(room.get("workflow_id") or metadata.get("workflow_id") or "").strip()
        invocation_job = str(os.environ.get("NEXUS_DURABLE_JOB_ID") or "")
        if invocation_job.startswith("nexus-mcp-"):
            os.environ["NEXUS_CORRELATION_ID"] = workflow_id or room_id
            os.environ["NEXUS_DEPARTMENT"] = "RESEARCH"
            os.environ["NEXUS_JOB_TYPE"] = "RESEARCH_ROOM_CHAT"
        else:
            os.environ.setdefault("NEXUS_CORRELATION_ID", workflow_id or room_id)
            os.environ.setdefault("NEXUS_DEPARTMENT", "RESEARCH")
            os.environ.setdefault("NEXUS_JOB_TYPE", "RESEARCH_ROOM_CHAT")
        if workflow_id:
            os.environ.setdefault("NEXUS_PROJECT_ID", workflow_id)
        os.environ["NEXUS_RESEARCH_ROOM_CALL_ID"] = f"{room_id}:{os.environ.get('NEXUS_DURABLE_JOB_ID', 'unscoped')}"
        res = mgr.chat_with_alpha(room_id=room_id, question=question)
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
    return {
        "tool_name": "nexus_ask_alpha_research_room",
        "status": "OK",
        "room_id": room_id,
        "user_message": res.get("user_message"),
        "alpha_message": res.get("alpha_message"),
        "read_only": False,
        "authority_owner": "Nexus",
    }


def _score_research_room(room_id: str) -> dict[str, Any]:
    from nexus_agent_platform.research_room.room_manager import ResearchRoomManager
    mgr = ResearchRoomManager()
    room = mgr.score_room(room_id=room_id)
    return {
        "tool_name": "nexus_score_research_room",
        "status": "OK",
        "room_id": room_id,
        "preliminary_score": room.get("preliminary_score"),
        "score_basis": room.get("score_basis"),
        "room": room,
        "read_only": False,
        "authority_owner": "Nexus",
    }


def _promote_research_room(room_id: str, requested_objective: str = "") -> dict[str, Any]:
    from nexus_agent_platform.research_room.room_manager import ResearchRoomManager
    mgr = ResearchRoomManager()
    promotion_package = mgr.promote_to_nova(room_id=room_id, requested_objective=requested_objective)
    return {
        "tool_name": "nexus_promote_research_room",
        "status": "PROMOTED",
        "room_id": room_id,
        "promotion_package": promotion_package,
        "read_only": False,
        "authority_owner": "Nexus",
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
            with mcp_read_egress_scope(request_id):
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


def _get_prior_department_result_impl(department: str, question: str = "") -> dict[str, Any]:
    """Resolve the latest receipt-backed completion for an explicitly named department.

    This is a read of durable completion events, never a job creator. Each
    candidate must still point to a completed durable job with the same
    receipt reference before its summary is returned. Alpha additionally
    re-reads its evidence through the canonical objective-scoped Alpha reader.
    """
    from nexus_agent_platform.durable_jobs import default_store

    dept = str(department or "").strip().upper()
    event_types = {
        "ALPHA": {"ALPHA_RESULT"},
        "RESEARCH": {"SIGNIFICANT_RESEARCH"},
        "SYSTEMS": {"SYSTEMS_RESULT"},
    }
    if dept not in event_types:
        return {"status": "rejected", "error": "department_not_supported", "allowed_departments": sorted(event_types)}

    path = ROOT / "data/runtime/nova_material_events.jsonl"
    rows: list[dict[str, Any]] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                row = json.loads(line)
            except ValueError:
                continue
            if isinstance(row, dict) and row.get("event_type") in event_types[dept]:
                rows.append(row)
    except OSError:
        return {"status": "unavailable", "error": "durable_completion_events_unavailable", "department": dept}

    store = default_store()
    for event in reversed(rows):
        job_id = str(event.get({"ALPHA": "alpha_job_id", "RESEARCH": "research_job_id", "SYSTEMS": "systems_job_id"}[dept]) or "")
        receipt_id = str(event.get("durable_receipt_id") or event.get("source") or "")
        job = store.get(job_id) if job_id else None
        if not job or job.department.upper() != dept or job.state != "COMPLETED":
            continue
        if not receipt_id or job.receipt_ref != receipt_id:
            continue

        result: dict[str, Any] = {
            "status": "ok", "department": dept, "event_type": event.get("event_type"),
            "title": event.get("title"), "summary": str(event.get("summary") or "")[:12000],
            "completed_at": event.get("created_at") or event.get("observed_at") or job.completed_at,
            "job_id": job.job_id, "receipt_id": job.receipt_ref,
            "source_research_job_id": event.get("source_research_job_id"),
            "source": "receipt_verified_nova_material_event", "read_only": True,
        }
        if dept == "ALPHA":
            research_job_id = str(event.get("source_research_job_id") or "")
            if not research_job_id:
                continue
            alpha = _call("nexus_get_alpha_review", {"objective_id": research_job_id})
            data = alpha.get("data") if isinstance(alpha.get("data"), dict) else {}
            evaluation = data.get("evaluation")
            if not isinstance(evaluation, dict):
                continue
            result["source_research_job_id"] = research_job_id
            result["alpha_evaluation"] = evaluation
            result["alpha_read_status"] = alpha.get("status")
            result["alpha_read_receipt_id"] = alpha.get("request_id")
        request_id = f"nexus-prior-work-{uuid.uuid4().hex}"
        receipt = {
            "schema_version": "nexus.prior-work-read-receipt.v1", "request_id": request_id,
            "department": dept, "job_id": job.job_id, "durable_receipt_id": job.receipt_ref,
            "source_research_job_id": result.get("source_research_job_id"),
            "question": str(question or "")[:500], "completed_at": _now(),
            "read_only": True, "authority_owner": "Nexus",
        }
        receipt["receipt_hash"] = hashlib.sha256(json.dumps(receipt, sort_keys=True).encode()).hexdigest()
        RECEIPT_DIR.mkdir(parents=True, exist_ok=True)
        (RECEIPT_DIR / f"{request_id}.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        result["request_id"] = request_id
        result["read_receipt_hash"] = receipt["receipt_hash"]
        return result
    return {"status": "not_found", "department": dept, "error": "no_receipt_verified_prior_result", "read_only": True}


def _get_prior_department_result(department: str, question: str = "") -> dict[str, Any]:
    request_id = f"nexus-mcp-prior-{uuid.uuid4().hex}"
    with mcp_read_egress_scope(request_id):
        return _get_prior_department_result_impl(department, question)


def _research_source_metadata(text: str) -> dict[str, str | None]:
    explicit = re.search(r"https?://[^\s)>,]+", text, re.I)
    bare_domain = re.search(r"\b(?:www\.)?[a-z0-9][a-z0-9.-]*\.(?:com|org|net|io|co|ai)(?:/[^\s)>,]*)?", text, re.I)
    source_url = (explicit.group(0).rstrip(".,;!") if explicit else
                  "https://" + bare_domain.group(0).rstrip(".,;!") if bare_domain else None)
    lowered = (source_url or "").lower()
    if re.search(r"youtube\.com/(?:@|channel/|c/|user/)|/videos(?:\b|$)", lowered):
        source_type = "YOUTUBE_CHANNEL"
    elif "youtube.com/watch?" in lowered or "youtu.be/" in lowered:
        source_type = "YOUTUBE_VIDEO"
    elif re.search(r"\.pdf(?:$|[?#])", lowered):
        source_type = "PDF"
    elif source_url:
        source_type = "WEB_PAGE"
    else:
        source_type = "UNKNOWN"
    return {"source_url": source_url, "source_type": source_type}


def _assign_research(objective: str, question: str = "", priority: int = 0,
                     parent_request_id: str = "", followup_department: str = "",
                     requested_intent: str = "") -> dict[str, Any]:
    """Create one idempotent, internal Nova assignment in the existing queue.

    This is intentionally narrower than generic Nova writes.  Research owns
    planning, capability selection, acquisition, and interpretation after the
    queue item is created.  Nova only records the objective and provenance.
    """
    import hashlib
    from nexus_agent_platform.research_assignment_intent import (
        INTENTS, assignment_job_type, classify_research_assignment, research_objective_type,
    )
    from nexus_agent_platform.research_work_queue import ResearchWorkQueue

    objective_text = str(objective or "").strip()
    question_text = str(question or objective_text).strip()
    source_metadata = _research_source_metadata(question_text)
    supplied_intent = str(requested_intent or "").strip().upper()
    if supplied_intent and supplied_intent not in INTENTS:
        return {"status": "rejected", "requested_intent": supplied_intent,
                "error": "unsupported_research_intent", "job_created": False}
    # Prefer Nova's existing semantic decision. Reclassify the prose only for
    # legacy callers that cannot yet send that decision.
    requested_intent = supplied_intent or classify_research_assignment(objective_text, question_text)
    if requested_intent == "RESEARCH_STATUS_QUERY":
        match = re.search(r"\bjob(?:[_ -]id)?\s*[:=]?\s*([a-z0-9_-]+)\b", question_text, re.I)
        if not match:
            return {"status": "read_only_query_required", "requested_intent": requested_intent,
                    "task_fulfilled": False, "blocker": "RESEARCH_STATUS_QUERY_REQUIRES_JOB_ID",
                    "job_created": False}
        from nexus_agent_platform.durable_jobs import default_store
        existing_job = default_store().get(match.group(1))
        if not existing_job:
            return {"status": "not_found", "requested_intent": requested_intent,
                    "job_id": match.group(1), "job_created": False, "read_only": True}
        return {"status": "read_only_result", "requested_intent": requested_intent,
                "job_id": existing_job.job_id, "job_type": existing_job.job_type,
                "final_status": existing_job.state, "created_at": existing_job.created_at,
                "claimed_at": existing_job.claimed_at, "completed_at": existing_job.completed_at,
                "worker": existing_job.claimed_by, "attempt_count": existing_job.attempt_count,
                "receipt_ref": existing_job.receipt_ref, "job_created": False, "read_only": True}
    job_type = assignment_job_type(requested_intent)
    if not job_type:
        return {"status": "rejected", "requested_intent": requested_intent,
                "error": "unsupported_or_ambiguous_research_intent", "job_created": False}
    followup = str(followup_department or "").strip().upper()
    if followup not in {"", "ALPHA"}:
        if requested_intent == "RESEARCH_MISSION":
            # A downstream destination is advisory context, not another
            # assignment or a precondition for entering Research intake.
            followup = ""
        else:
            return {"status": "rejected", "error": "unsupported_followup_department"}
    if len(objective_text) < 12 or len(question_text) < 12:
        return {"status": "rejected", "error": "objective_and_question_required"}
    if len(objective_text) > 1000 or len(question_text) > 1600:
        return {"status": "rejected", "error": "objective_or_question_too_long"}
    if requested_intent == "RESEARCH_EXECUTION":
        return {"status": "rejected", "requested_intent": requested_intent,
                "error": "research_scope_unresolved", "job_created": False}
    bounded_priority = max(-10, min(int(priority or 0), 20))
    objective_type = research_objective_type(objective_text, question_text) if requested_intent == "RESEARCH_MISSION" else ""
    execution_path = {
        "RESEARCH_MISSION": "RESEARCH_INTAKE",
        "RESEARCH_ONLY": "BOUNDED_RESEARCH_ONLY",
        "RESEARCH_RUNTIME_INSPECTION": "READ_ONLY_RESEARCH_RUNTIME_INSPECTOR",
        "NOTEBOOKLM_OPERATION": "NOTEBOOKLM_GOVERNED_ADAPTER",
        "PUBLIC_RESEARCH_SEARCH": "GOVERNED_PUBLIC_RESEARCH_SEARCH",
        "RESEARCH_GAP_VERIFY": "TARGETED_EVIDENCE_GAP",
    }.get(requested_intent, "NO_EXECUTION")
    from nexus_agent_platform.durable_jobs import default_store
    campaign_context={}
    campaign_parent=None
    if followup == "ALPHA":
        from nexus_agent_platform.durable_objective_control import ACTIVE_CAMPAIGN_PATH, load_active_campaign
        campaign=load_active_campaign() if ACTIVE_CAMPAIGN_PATH.exists() else {}
        if campaign.get("CAMPAIGN_STATUS") in {"ACTIVE","IN_PROGRESS"}:
            campaign_context={"campaign_id":campaign.get("CAMPAIGN_ID"),
                "owner_objective_id":campaign.get("OWNER_OBJECTIVE_ID"),
                "objective_version":campaign.get("OBJECTIVE_VERSION"),
                "independent_job":False,"parent_mission_id":str(parent_request_id or "")}
            campaign_parent=campaign.get("CURRENT_JOB_ID")

    def ensure_worker_job(work_id: str, objective_id: str) -> dict[str, Any]:
        store = default_store()
        job = store.enqueue(
            "RESEARCH", job_type, priority=max(1, bounded_priority + 50),
            payload_ref=work_id, correlation_id=objective_id, max_attempts=3,
            parent_job_id=campaign_parent,
            idempotency_key=f"nova-research-work:{work_id}",
            governance_context={**campaign_context,"source": "NOVA_MCP_RESEARCH_ASSIGNMENT", "objective_id": objective_id,
                                "requested_intent": requested_intent, "routed_intent": requested_intent,
                                "execution_path": execution_path, "objective_type": objective_type or None,
                                "research_scope": question_text,
                                "original_objective": objective_text,
                                "original_source_url": source_metadata["source_url"],
                                "original_source_type": source_metadata["source_type"],
                                "current_research_context": {"stage": "RESEARCH_INTAKE",
                                    "source_acquired": False, "classification_required": False},
                                "external_actions_authorized": False, "external_actions_allowed": False,
                                "followup_department": followup,
                                "spend_allowed": False, "paid_provider_authorized": False},
        )
        if followup:
            current=store.get(job.job_id)
            context=dict(current.governance_context or {}) if current else {}
            context.update({"followup_department":followup,**campaign_context})
            store.set_governance_context(job.job_id,context)
            if campaign_parent and current and not current.parent_job_id:
                store.bind_parent_job(job.job_id,str(campaign_parent))
        return {"durable_job_id": job.job_id, "durable_job_state": job.state}

    fingerprint = hashlib.sha256(
        (objective_text + "\n" + question_text + "\nhermes_nova\n" + str(parent_request_id) + "\n" + followup).encode("utf-8")
    ).hexdigest()[:20]
    objective_id = f"nova_research_{fingerprint}"
    work_id = f"nova_research_work_{fingerprint}"
    queue = ResearchWorkQueue()
    existing = next((row for row in queue.load().get("items", []) if row.get("work_id") == work_id), None)
    if existing:
        worker_job = ensure_worker_job(work_id, str(existing.get("objective_id") or objective_id))
        if followup and existing.get("followup_department") != followup:
            existing=queue.upsert({**existing, "followup_department": followup})
        return {
            "status": "idempotent_existing",
            "requested_intent": requested_intent,
            "job_type": job_type,
            "objective_id": existing.get("objective_id") or objective_id,
            "work_id": work_id,
            "queue_class": existing.get("work_class"),
            "queue_status": existing.get("status"),
            "requested_by": existing.get("requested_by"),
            "parent_request_id": existing.get("parent_request_id"),
            **worker_job,
            **_record_research_assignment_usage(
                objective_id=str(existing.get("objective_id") or objective_id), work_id=work_id,
                durable_job_id=str(worker_job.get("durable_job_id") or ""), requested_intent=requested_intent),
        }
    item = queue.enqueue(
        work_id=work_id,
        work_class="ASSIGNED",
        source_type="NOVA_OBJECTIVE",
        lane_id="NOVA_EXECUTIVE_RESEARCH",
        title=objective_text[:180],
        question=question_text,
        objective_id=objective_id,
        requested_by="hermes_nova",
        priority=bounded_priority,
        status="QUEUED",
        parent_request_id=str(parent_request_id or "nova_mcp_assignment"),
        selection_reason="Nova executive assignment; Research AI owns capability selection.",
        followup_department=followup,
        lifecycle="ASSIGNED", requested_intent=requested_intent,
        request_type={"RESEARCH_MISSION": "RESEARCH_INTAKE",
                      "RESEARCH_ONLY": "RESEARCH_ONLY",
                      "NOTEBOOKLM_OPERATION": "NOTEBOOKLM_OPERATION",
                      "PUBLIC_RESEARCH_SEARCH": "PUBLIC_RESEARCH_SEARCH",
                      "RESEARCH_GAP_VERIFY": "RESEARCH_GAP_VERIFY",
                      "RESEARCH_RUNTIME_INSPECTION": "RESEARCH_RUNTIME_INSPECTION"}.get(requested_intent, "RESEARCH_EXECUTION"),
        routed_intent=requested_intent, execution_path=execution_path,
        objective_type=objective_type or None, research_scope=question_text,
        original_objective=objective_text,
        original_source_url=source_metadata["source_url"],
        original_source_type=source_metadata["source_type"],
        current_research_context={"stage": "RESEARCH_INTAKE", "source_acquired": False,
                                  "classification_required": False},
        notebook_id=(re.search(r"\b([0-9a-f]{8}-[0-9a-f-]{27,})\b", question_text, re.I).group(1)
                     if re.search(r"\b([0-9a-f]{8}-[0-9a-f-]{27,})\b", question_text, re.I) else None),
        notebook_operation=("ADD_SOURCE" if requested_intent == "NOTEBOOKLM_OPERATION" and
                            re.search(r"\b(add|import|attach)\b", question_text, re.I) else
                            "ASK" if requested_intent == "NOTEBOOKLM_OPERATION" else None),
        source_url=source_metadata["source_url"],
    )
    worker_job = ensure_worker_job(work_id, objective_id)
    return {
        "status": "queued",
        "objective_id": objective_id,
        "work_id": work_id,
        "queue_class": item.get("work_class"),
        "queue_status": item.get("status"),
        "requested_by": item.get("requested_by"),
        "parent_request_id": item.get("parent_request_id"),
        "research_owner": "Research AI investigator",
        "requested_intent": requested_intent,
        "job_type": job_type,
        "external_action": False,
        **worker_job,
        **_record_research_assignment_usage(
            objective_id=objective_id, work_id=work_id,
            durable_job_id=str(worker_job.get("durable_job_id") or ""), requested_intent=requested_intent),
    }


def _record_research_assignment_usage(*, objective_id: str, work_id: str,
                                      durable_job_id: str, requested_intent: str) -> dict[str, Any]:
    """Bounded, non-fatal AI-usage accounting at the Research assignment boundary.

    Research owns its own model routing (unchanged here).  At the attributable
    assignment boundary we record a request-level AI_USAGE event (tokens are not
    known until the worker runs -> TOKEN_DATA=UNAVAILABLE) and consult the
    provider-safety guard so an exhausted Codex is not blindly re-hit.
    """
    try:
        from nexus_agent_platform.runtime import ai_usage_ledger as led
    except ImportError:
        return {"ai_usage_recorded": False}
    try:
        guard = led.should_defer_retry(durable_job_id or work_id, "openai-codex",
                                       prior_failure_reason="codex_capacity_prior")
        provider_blocked = guard.get("defer", False)
        led.record_ai_usage(
            department="RESEARCH", agent="RESEARCH_INVESTIGATOR",
            job_id=durable_job_id or work_id, work_item_id=work_id,
            provider="openai-codex", model="gpt-6.1-sol",
            routing_reason=requested_intent or "RESEARCH_ASSIGNMENT",
            token_data="UNAVAILABLE", success=True,
            provider_status="USAGE_LIMIT_REACHED" if provider_blocked else "UNKNOWN",
            quota_state="UNKNOWN",
        )
        safety = {"PROVIDER_BLOCKED": True, "ACTION": "RETRY_DEFERRED",
                  "CASE_PRESERVED": True, "RESUME_AFTER": guard.get("resume_after")} if provider_blocked else {
                  "PROVIDER_BLOCKED": False, "ACTION": "PROCEED"}
        return {"ai_usage_recorded": True, "provider_safety": safety}
    except Exception:
        return {"ai_usage_recorded": False}


def _continue_research(objective_id: str, project_id: str, job_id: str,
                       instruction: str, parent_request_id: str = "") -> dict[str, Any]:
    """Continue one exact Research project using its existing queue lineage."""
    import hashlib
    from nexus_agent_platform.research_work_queue import ResearchWorkQueue
    from nexus_agent_platform.durable_jobs import default_store

    objective = str(objective_id or "").strip()
    project = str(project_id or "").strip()
    prior_job_id = str(job_id or "").strip()
    task = " ".join(str(instruction or "").split())[:1000]
    if not objective or not project or not prior_job_id or len(task) < 8:
        return {"status": "rejected", "error": "exact_research_lineage_required", "job_created": False}
    queue = ResearchWorkQueue()
    items = queue.load().get("items", [])
    current = next((row for row in items if str(row.get("work_id") or "") == project
                    and str(row.get("objective_id") or "") == objective), None)
    if not current:
        return {"status": "not_found", "error": "CURRENT_PROJECT_NOT_FOUND", "job_created": False,
                "objective_id": objective, "project_id": project, "job_id": prior_job_id}
    latest = default_store().get(prior_job_id)
    queue_state = str(current.get("status") or "UNKNOWN").upper()
    latest_state = latest.get("state") if isinstance(latest, dict) else getattr(latest, "state", None)
    job_state = str(latest_state or "UNKNOWN").upper()
    if queue_state in {"QUEUED", "READY", "IN_PROGRESS", "RUNNING", "ASSIGNED"} or job_state in {"READY", "QUEUED", "RUNNING", "CLAIMED"}:
        return {"status": "already_active", "objective_id": objective, "project_id": project,
                "job_id": prior_job_id, "job_state": job_state if job_state != "UNKNOWN" else queue_state,
                "job_created": False, "continuation_owned_by": "existing Research queue worker"}

    followup_question = f"Continue the existing Research project {project}. {task}"[:1600]
    work_id = "nova_research_continue_" + hashlib.sha256(
        (objective + "\n" + project + "\n" + prior_job_id + "\n" + task).encode("utf-8")
    ).hexdigest()[:20]
    existing_followup = next((row for row in items if str(row.get("work_id") or "") == work_id), None)
    if existing_followup:
        worker = next((row for row in items if str(row.get("work_id") or "") == work_id), existing_followup)
        return {"status": "idempotent_existing", "objective_id": objective, "project_id": project,
                "work_id": work_id, "job_id": str(worker.get("durable_job_id") or ""),
                "job_state": str(worker.get("durable_job_state") or worker.get("status") or "UNKNOWN"),
                "job_created": False}

    followup = queue.enqueue(
        work_id=work_id, work_class="ASSIGNED", source_type="NOVA_OBJECTIVE",
        lane_id="NOVA_EXECUTIVE_RESEARCH", title=("Continue: " + str(current.get("title") or task))[:180],
        question=followup_question, objective_id=objective, requested_by="hermes_nova",
        priority=max(1, int(current.get("priority", 0) or 0)), status="QUEUED",
        parent_request_id=objective, parent_work_id=project, followup_department="",
        lifecycle="ASSIGNED", requested_intent="RESEARCH_MISSION", routed_intent="RESEARCH_MISSION",
        request_type="RESEARCH_INTAKE", execution_path="RESEARCH_INTAKE",
        objective_type=current.get("objective_type"), research_scope=followup_question,
        original_objective=followup_question, spend_allowed=False, paid_provider_authorized=False,
        external_actions_allowed=False, external_actions_authorized=False,
        continuation_of={"objective_id": objective, "project_id": project, "job_id": prior_job_id},
    )
    store = default_store()
    worker_job = store.enqueue(
        "RESEARCH", "RESEARCH_INTAKE", priority=max(1, int(current.get("priority", 0) or 0) + 50),
        payload_ref=work_id, correlation_id=str(parent_request_id or objective), max_attempts=3,
        idempotency_key=f"nova-research-work:{work_id}",
        governance_context={"source": "NOVA_RESEARCH_CONTINUATION", "objective_id": objective,
            "project_id": project, "parent_work_id": project, "continuation_of_job_id": prior_job_id,
            "requested_intent": "RESEARCH_MISSION", "routed_intent": "RESEARCH_MISSION",
            "execution_path": "RESEARCH_INTAKE", "research_scope": followup_question,
            "external_actions_authorized": False, "external_actions_allowed": False,
            "spend_allowed": False, "paid_provider_authorized": False},
    )
    followup.update({"durable_job_id": worker_job.job_id, "durable_job_state": worker_job.state})
    queue.upsert(followup)
    return {"status": "continued", "objective_id": objective, "project_id": project,
            "work_id": work_id, "job_id": worker_job.job_id, "job_state": worker_job.state,
            "job_created": True, "continuation_of_job_id": prior_job_id}


def _continue_research_case(case_id: str, objective_id: str, project_id: str,
                            durable_job_id: str) -> dict[str, Any]:
    """Run one bounded normal Research Case Engine turn against an exact case.

    The existing project-level intake adapter intentionally stops at
    CONTINUATION_REQUIRED. This adapter connects Nova to the already-installed
    case continuation engine, while retaining its provider governor and exact
    case/job lineage.
    """
    from nexus_agent_platform.durable_jobs import default_store
    from research.research_case_engine import continue_case_once, get_case

    case_id = str(case_id or "").strip()
    objective_id = str(objective_id or "").strip()
    project_id = str(project_id or "").strip()
    durable_job_id = str(durable_job_id or "").strip()
    case = get_case(case_id)
    if not case or str(case.get("case_id") or "") != case_id:
        return {"status": "not_found", "case_id": case_id, "error": "EXACT_RESEARCH_CASE_NOT_FOUND"}
    case_project_id = str(case.get("project_id") or "")
    case_objective_id = str(case.get("objective_id") or case.get("originating_goal_id") or "")
    project_matches = (case_project_id == project_id if case_project_id else
        bool(project_id and project_id in str(case.get("primary_question") or "")))
    objective_matches = not case_objective_id or case_objective_id == objective_id
    if not project_matches or not objective_matches:
        return {"status": "rejected", "case_id": case_id, "error": "RESEARCH_CASE_PROJECT_MISMATCH"}

    store = default_store()
    job = store.get(durable_job_id) if durable_job_id else None
    if not job:
        return {"status": "rejected", "case_id": case_id, "error": "DURABLE_JOB_REQUIRED"}
    value = (lambda key: job.get(key) if isinstance(job, dict) else getattr(job, key, None))
    if str(value("correlation_id") or "") != objective_id:
        return {"status": "rejected", "case_id": case_id, "error": "JOB_OBJECTIVE_LINEAGE_MISMATCH"}
    if str(value("department") or "").upper() != "RESEARCH":
        return {"status": "rejected", "case_id": case_id, "error": "JOB_DEPARTMENT_MISMATCH"}
    job_type = str(value("job_type") or "").upper()
    if job_type not in {"RESEARCH_INTAKE", "RESEARCH_CASE_CONTINUATION"}:
        return {"status": "rejected", "case_id": case_id, "error": "JOB_TYPE_NOT_AUTHORIZED_FOR_CASE_CONTINUATION"}

    keys = ("NEXUS_DURABLE_JOB_ID", "NEXUS_CORRELATION_ID", "NEXUS_DEPARTMENT",
            "NEXUS_JOB_TYPE", "NEXUS_PROJECT_ID")
    previous = {key: os.environ.get(key) for key in keys}
    os.environ.update({"NEXUS_DURABLE_JOB_ID": durable_job_id,
        "NEXUS_CORRELATION_ID": objective_id, "NEXUS_DEPARTMENT": "RESEARCH",
        "NEXUS_JOB_TYPE": job_type, "NEXUS_PROJECT_ID": project_id})
    try:
        result = continue_case_once(case_id)
    finally:
        for key, old in previous.items():
            if old is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = old
    latest = get_case(case_id) or case
    return {"status": str(result.get("status") or "unknown").lower(),
        "case_id": case_id, "objective_id": objective_id, "project_id": project_id,
        "durable_job_id": durable_job_id, "execution": result,
        "case_state": {key: latest.get(key) for key in (
            "status", "primary_question", "open_questions", "answered_questions", "sources",
            "findings", "syntheses", "next_action", "next_research_action", "continue_research",
            "provider_attempts", "missing_information", "updated_at")}}


def _exact_research_case(case_id: str, objective_id: str, project_id: str,
                         durable_job_id: str) -> tuple[dict[str, Any] | None, dict[str, Any] | None, dict[str, Any] | None]:
    """Resolve and lineage-check one existing case without creating work."""
    from nexus_agent_platform.durable_jobs import default_store
    from research.research_case_engine import get_case

    case_id, objective_id = str(case_id or "").strip(), str(objective_id or "").strip()
    project_id, durable_job_id = str(project_id or "").strip(), str(durable_job_id or "").strip()
    case = get_case(case_id)
    if not case or str(case.get("case_id") or "") != case_id:
        return None, None, {"status": "not_found", "error": "EXACT_RESEARCH_CASE_NOT_FOUND"}
    case_project_id = str(case.get("project_id") or "")
    case_objective_id = str(case.get("objective_id") or case.get("originating_goal_id") or "")
    project_matches = (case_project_id == project_id if case_project_id else
        bool(project_id and project_id in str(case.get("primary_question") or "")))
    objective_matches = not case_objective_id or case_objective_id == objective_id
    if not project_matches or not objective_matches:
        return None, None, {"status": "rejected", "error": "RESEARCH_CASE_PROJECT_MISMATCH"}
    store = default_store()
    job = store.get(durable_job_id) if durable_job_id else None
    if not job:
        return None, None, {"status": "rejected", "error": "DURABLE_JOB_REQUIRED"}
    value = lambda key: job.get(key) if isinstance(job, dict) else getattr(job, key, None)
    if str(value("correlation_id") or "") != objective_id:
        return None, None, {"status": "rejected", "error": "JOB_OBJECTIVE_LINEAGE_MISMATCH"}
    if str(value("department") or "").upper() != "RESEARCH":
        return None, None, {"status": "rejected", "error": "JOB_DEPARTMENT_MISMATCH"}
    if str(value("job_type") or "").upper() not in {"RESEARCH_INTAKE", "RESEARCH_CASE_CONTINUATION"}:
        return None, None, {"status": "rejected", "error": "JOB_TYPE_NOT_AUTHORIZED_FOR_CASE"}
    return case, job, None


def _research_case_projection(case: dict[str, Any], *, objective_id: str,
                              project_id: str, durable_job_id: str) -> dict[str, Any]:
    sources = [{key: row.get(key) for key in ("source_id", "url", "title", "source_class", "added_at") if row.get(key) is not None}
               for row in case.get("sources") or [] if isinstance(row, dict)]
    findings = [{key: row.get(key) for key in ("finding_id", "claim", "summary", "evidence_ids", "evidence_source_ids", "recorded_at") if row.get(key) is not None}
                for row in case.get("findings") or [] if isinstance(row, dict)]
    syntheses = [{key: row.get(key) for key in ("claims", "agreements", "disagreements", "uncertainties", "source_ids", "source_classes", "recorded_at") if row.get(key) is not None}
                 for row in case.get("syntheses") or [] if isinstance(row, dict)]
    fields = ("status", "primary_question", "open_questions", "answered_questions",
              "next_action", "next_research_action", "continue_research", "updated_at")
    state = {key: case.get(key) for key in fields}
    state.update({"sources": sources, "findings": findings, "syntheses": syntheses,
                  "source_count": len(sources), "finding_count": len(findings),
                  "synthesis_count": len(syntheses)})
    return {"status": "ok", "case_id": case.get("case_id"), "objective_id": objective_id,
            "project_id": project_id, "durable_job_id": durable_job_id,
            "read_only": True, "no_mutation": True,
            "case_state": state}


def _get_research_case(case_id: str, objective_id: str, project_id: str,
                       durable_job_id: str) -> dict[str, Any]:
    case, _, error = _exact_research_case(case_id, objective_id, project_id, durable_job_id)
    if error:
        return {**error, "case_id": case_id, "read_only": True, "no_mutation": True}
    return _research_case_projection(case, objective_id=objective_id,
                                     project_id=project_id, durable_job_id=durable_job_id)


def _research_controller_read(operation: str, case_id: str, objective_id: str,
                              project_id: str, durable_job_id: str) -> dict[str, Any]:
    from nexus_agent_platform.research_room import production_controller
    # Exact controller reads use the append-only local mirror. The MCP and
    # durable worker share this state root, so readback is local control-plane
    # I/O and must not consume the feeder's accumulated external egress budget.
    with production_controller._local_case_read_scope():
        case, _, error = _exact_research_case(case_id, objective_id, project_id, durable_job_id)
        if error:
            return {**error, "case_id": case_id, "read_only": True, "no_mutation": True}
        reader = {"status": production_controller.status,
            "open_questions": production_controller.open_questions,
            "results": production_controller.results}.get(operation)
        if reader is None:
            return {"status": "rejected", "error": "UNKNOWN_RESEARCH_CONTROLLER_READ"}
        return reader(case_id, objective_id, project_id, durable_job_id)


def _research_controller_continue(case_id: str, objective_id: str, project_id: str,
                                  durable_job_id: str, instruction: str) -> dict[str, Any]:
    from nexus_agent_platform.research_room import production_controller
    with production_controller._local_case_read_scope():
        _, _, error = _exact_research_case(case_id, objective_id, project_id, durable_job_id)
        if error:
            return {**error, "case_id": case_id, "new_case_created": False}
        return production_controller.continue_case(case_id, objective_id, project_id, durable_job_id, instruction)


def _research_controller_advisor_request(case_id: str, objective_id: str, project_id: str,
        durable_job_id: str, question: str, review_role: str = "PRIMARY_ADVISOR") -> dict[str, Any]:
    from nexus_agent_platform.research_room import production_controller
    with production_controller._local_case_read_scope():
        _, _, error = _exact_research_case(case_id, objective_id, project_id, durable_job_id)
        if error:
            return {**error, "case_id": case_id, "mission_complete": False}
    return production_controller.advisor_request(case_id, objective_id, project_id, durable_job_id, question, review_role)


def _record_research_synthesis(case_id: str, objective_id: str, project_id: str,
                               durable_job_id: str, claims: list[dict[str, Any]],
                               agreements: list[str], disagreements: list[str],
                               uncertainties: list[str], source_ids: list[str]) -> dict[str, Any]:
    """Append an evidence-linked synthesis to one already-existing exact case."""
    from research.research_case_engine import get_case, record_synthesis
    case, _, error = _exact_research_case(case_id, objective_id, project_id, durable_job_id)
    if error:
        return {**error, "case_id": case_id, "objective_id": objective_id,
                "project_id": project_id, "durable_job_id": durable_job_id}
    if not isinstance(claims, list) or not claims or not isinstance(source_ids, list) or not source_ids:
        return {"status": "rejected", "case_id": case_id, "error": "EVIDENCE_LINKED_SYNTHESIS_REQUIRED"}
    known = {str(row.get("source_id") or row.get("url") or row.get("source_url"))
             for row in case.get("sources") or [] if isinstance(row, dict)}
    selected = {str(value) for value in source_ids}
    if not selected.issubset(known):
        return {"status": "rejected", "case_id": case_id, "error": "SYNTHESIS_SOURCE_NOT_ATTACHED_TO_CASE"}
    for claim in claims:
        if not isinstance(claim, dict) or not str(claim.get("claim") or "").strip():
            return {"status": "rejected", "case_id": case_id, "error": "SYNTHESIS_CLAIM_INVALID"}
        refs = {str(value) for value in claim.get("evidence_ids") or []}
        if not refs or not refs.issubset(selected):
            return {"status": "rejected", "case_id": case_id, "error": "SYNTHESIS_CLAIM_EVIDENCE_MISMATCH"}
    for prior in case.get("syntheses") or []:
        if (isinstance(prior, dict) and prior.get("claims") == claims
                and set(map(str, prior.get("source_ids") or [])) == selected):
            return {"status": "already_recorded", "case_id": case_id, "objective_id": objective_id,
                "project_id": project_id, "durable_job_id": durable_job_id,
                "synthesis": prior, "case_state": _research_case_projection(case,
                    objective_id=objective_id, project_id=project_id,
                    durable_job_id=durable_job_id)["case_state"]}
    result = record_synthesis(case_id, claims=claims, agreements=agreements,
        disagreements=disagreements, uncertainties=uncertainties, source_ids=source_ids)
    if not result.get("ok"):
        return {"status": "rejected", "case_id": case_id,
                "error": str(result.get("reason") or "SYNTHESIS_NOT_PERSISTED")}
    latest = get_case(case_id) or case
    return {"status": "recorded", "case_id": case_id, "objective_id": objective_id,
        "project_id": project_id, "durable_job_id": durable_job_id,
        "synthesis": result.get("synthesis"),
        "case_state": _research_case_projection(latest, objective_id=objective_id,
            project_id=project_id, durable_job_id=durable_job_id)["case_state"]}


def _record_research_recommendation(case_id: str, objective_id: str, project_id: str,
        durable_job_id: str, kind: str, reason: str, source_ids: list[str],
        contradictory_evidence: list[str], uncertainties: list[str],
        missing_evidence: list[str], confidence: float, next_action: str) -> dict[str, Any]:
    """Record a decision-ready recommendation against one exact evidence-backed case."""
    from research.research_case_engine import get_case, recommendation
    case, _, error = _exact_research_case(case_id, objective_id, project_id, durable_job_id)
    if error:
        return {**error, "case_id": case_id, "objective_id": objective_id,
                "project_id": project_id, "durable_job_id": durable_job_id}
    if not isinstance(source_ids, list) or not source_ids:
        return {"status": "rejected", "case_id": case_id, "error": "RECOMMENDATION_SOURCE_REQUIRED"}
    known = {str(row.get("source_id") or row.get("url") or row.get("source_url"))
             for row in case.get("sources") or [] if isinstance(row, dict)}
    selected = [str(value) for value in source_ids]
    if len(set(selected)) != len(selected) or not set(selected).issubset(known):
        return {"status": "rejected", "case_id": case_id, "error": "RECOMMENDATION_SOURCE_NOT_ATTACHED_TO_CASE"}
    for prior in case.get("recommendations") or []:
        if (isinstance(prior, dict)
                and str(prior.get("recommendation") or "").upper() == str(kind).upper()
                and prior.get("recommendation_reason") == reason
                and prior.get("supporting_evidence") == selected):
            return {"status": "already_recorded", "case_id": case_id,
                    "objective_id": objective_id, "project_id": project_id,
                    "durable_job_id": durable_job_id, "recommendation": prior}
    result = recommendation(case_id, kind=kind, reason=reason,
        supporting_evidence=selected, contradictory_evidence=contradictory_evidence,
        uncertainties=uncertainties, missing_evidence=missing_evidence,
        confidence=confidence, next_action=next_action)
    if not result.get("ok"):
        return {"status": "rejected", "case_id": case_id,
                "error": str(result.get("reason") or "RECOMMENDATION_NOT_PERSISTED")}
    latest = get_case(case_id) or case
    return {"status": "recorded", "case_id": case_id, "objective_id": objective_id,
        "project_id": project_id, "durable_job_id": durable_job_id,
        "recommendation": result.get("recommendation"),
        "case_state": {key: latest.get(key) for key in
            ("status", "final_decision", "continue_research", "next_action", "next_research_action", "updated_at")}}


def _get_research_execution_trace(job_id: str) -> dict[str, Any]:
    """Read bounded, secret-filtered execution events for one exact Research job."""
    job_id = str(job_id or "").strip()
    if not re.fullmatch(r"job_[A-Za-z0-9_-]{8,80}", job_id):
        return {"status": "rejected", "error": "EXACT_DURABLE_JOB_ID_REQUIRED", "job_id": None}
    path = nexus_research_state_path("runtime", "research_execution_jobs.jsonl")
    if not path.is_file():
        return {"status": "unavailable", "job_id": job_id, "event_count": 0,
                "error": "RESEARCH_EXECUTION_LEDGER_NOT_FOUND"}
    allowed = {
        "at", "recorded_at", "status", "attempt_count", "worker_id", "timeout_seconds",
        "error", "failure_class", "ingestion_status", "supabase_source_id", "lane_id",
        "source_type", "source_id", "selected_executor_id", "execution_class",
        "routing_status", "routing_reason", "programs", "tasks_created", "registry_channels",
        "assignment_status", "model_call_required", "model_calls", "required_capabilities",
    }
    secret_patterns = (
        (re.compile(r"(?i)Bearer\s+[^\s,;]+"), "Bearer [REDACTED]"),
        (re.compile(r"(?i)(api[_ -]?key|access[_ -]?token|refresh[_ -]?token|password|secret)(\s*[:=]\s*)[^\s,;]+"), r"\1\2[REDACTED]"),
    )
    events: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            try:
                row = json.loads(line)
            except (TypeError, ValueError):
                continue
            if not isinstance(row, dict) or str(row.get("execution_id") or "") != job_id:
                continue
            safe = {key: row[key] for key in allowed if key in row}
            if isinstance(safe.get("error"), str):
                value = safe["error"][:500]
                for pattern, replacement in secret_patterns:
                    value = pattern.sub(replacement, value)
                safe["error"] = value
            digest = hashlib.sha256(json.dumps(row, sort_keys=True, default=str).encode()).hexdigest()[:20]
            safe["evidence_id"] = f"research_execution_event:{job_id}:{digest}"
            events.append(safe)
    try:
        source_ref = str(path.relative_to(ROOT))
    except ValueError:
        source_ref = "external_research_state:runtime/research_execution_jobs.jsonl"
    return {"status": "ok", "job_id": job_id, "event_count": len(events),
            "events": events, "read_only": True, "source": source_ref}


def _assign_codex(parent_objective_id: str, blocking_work_id: str, defect_id: str,
                  defect_summary: str, affected_component: str,
                  acceptance_criteria: list[str], test_requirements: list[str],
                  allowed_scope: list[str], prohibited_actions: list[str],
                  risk_class: str = "LOW") -> dict[str, Any]:
    from nexus_agent_platform.nova_codex_bridge import create_assignment
    return create_assignment(parent_objective_id=parent_objective_id, blocking_work_id=blocking_work_id,
                             defect_id=defect_id, defect_summary=defect_summary,
                             affected_component=affected_component, acceptance_criteria=acceptance_criteria,
                             test_requirements=test_requirements, allowed_scope=allowed_scope,
                             prohibited_actions=prohibited_actions, risk_class=risk_class)


def _assign_department_query(department: str, question: str, parent_request_id: str = "") -> dict[str, Any]:
    """Queue one safe Research or Systems query for the existing department worker."""
    from nexus_agent_platform.department_router import classify_intent
    from nexus_agent_platform.durable_jobs import default_store

    department_key = str(department or "").strip().upper()
    question_text = str(question or "").strip()
    if department_key == "ALPHA":
        return _assign_alpha_review(question_text, parent_request_id)
    if not question_text or len(question_text) > 240:
        return {"status": "rejected", "error": "question_must_be_1_to_240_characters"}
    intent = classify_intent(question_text)
    # Some deployed intent classifiers label an explicit health-check command
    # as a generic SYSTEM_COMMAND or STATE_QUERY when the message also asks
    # for current status fields. Preserve the MCP write guard while recognizing
    # this narrowly bounded, read-only Systems operation deterministically.
    if (department_key == "SYSTEMS"
            and re.search(r"\b(run|perform|execute|check)\b", question_text, re.I)
            and re.search(r"\b(system|systems|nexus)\b", question_text, re.I)
            and re.search(r"\b(health check|system health|health)\b", question_text, re.I)):
        intent = "SYSTEM_HEALTH"
    allowed = {"RESEARCH": {"RESEARCH"}, "SYSTEMS": {"SYSTEM_HEALTH", "SYSTEM_OPERATIONS"}}
    if intent not in allowed.get(department_key, set()):
        return {"status": "rejected", "error": "department_intent_mismatch", "intent": intent}
    from nexus_agent_platform.durable_objective_control import ACTIVE_CAMPAIGN_PATH, load_active_campaign
    campaign = load_active_campaign() if ACTIVE_CAMPAIGN_PATH.exists() else {}
    context = {"source": "NOVA_MCP_DEPARTMENT_QUERY", "paid_provider_authorized": False,
               "external_actions_authorized": False, "external_actions_allowed": False, "spend_allowed": False,
               "resource_dependencies": []}
    parent_job_id = None
    correlation_id = str(parent_request_id or "nova-mcp-department-query")
    if campaign.get("CAMPAIGN_STATUS") in {"ACTIVE", "IN_PROGRESS"}:
        context.update({"campaign_id": campaign.get("CAMPAIGN_ID"),
                        "owner_objective_id": campaign.get("OWNER_OBJECTIVE_ID"),
                        "objective_version": campaign.get("OBJECTIVE_VERSION"),
                        "independent_job": True})
        parent_job_id = campaign.get("CURRENT_JOB_ID")
        correlation_id = str(campaign.get("CORRELATION_ID") or campaign.get("CAMPAIGN_ID"))
    import hashlib
    fingerprint = hashlib.sha256((department_key + "\n" + question_text + "\n" + str(parent_request_id)).encode()).hexdigest()[:24]
    payload_path = nexus_research_state_path("runtime", "nexus_mcp_jobs", f"{fingerprint}.json")
    payload_path.parent.mkdir(parents=True, exist_ok=True)
    payload_path.write_text(json.dumps({"schema_version": "nexus.department-query.v1",
        "department": department_key, "question": question_text,
        "parent_request_id": str(parent_request_id or ""), "created_by": "hermes_nova"}, indent=2) + "\n", encoding="utf-8")
    job = default_store().enqueue(department_key, "NEXUS_DEPARTMENT_QUERY", priority=100,
        payload_ref=str(payload_path), parent_job_id=parent_job_id,
        correlation_id=correlation_id, max_attempts=2,
        idempotency_key=f"nova-department-query:{fingerprint}", governance_context=context)
    return {"status": "queued", "job_id": job.job_id, "job_state": job.state,
            "department": department_key, "intent": intent,
            "receipt_boundary": "existing durable Nexus worker", "external_action": False,
            "objective_created": False}


def _assign_nova_control_action(job_type: str, department: str, task: str,
                                parent_request_id: str = "") -> dict[str, Any]:
    """Queue one bounded Creative or isolated coding-worker action."""
    from nexus_agent_platform.durable_jobs import default_store
    text = " ".join(str(task or "").split())
    if not 12 <= len(text) <= 1200:
        return {"status": "rejected", "error": "bounded_task_must_be_12_to_1200_characters"}
    if _requests_external_or_production_action(text):
        return {"status": "rejected", "error": "external_or_production_action_not_supported"}
    fingerprint = hashlib.sha256((job_type + "\n" + text + "\n" + str(parent_request_id)).encode()).hexdigest()[:24]
    path = nexus_research_state_path("runtime", "nexus_mcp_jobs", f"{job_type.lower()}_{fingerprint}.json")
    payload_ref = str(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"schema_version": "nexus.nova-control-action.v1",
        "task": text, "parent_request_id": str(parent_request_id or ""),
        "external_actions_allowed": False, "spend_allowed": False}, indent=2) + "\n", encoding="utf-8")
    context = {"source": "NOVA_BOUNDED_CONTROL_ACTION", "parent_request_id": str(parent_request_id or ""),
        "external_actions_allowed": False, "external_actions_authorized": False,
        "spend_allowed": False, "paid_provider_authorized": False, "resource_class": "LIGHTWEIGHT_INTERNAL"}
    job = default_store().enqueue(department, job_type, priority=100, payload_ref=payload_ref,
        correlation_id=str(parent_request_id or fingerprint), max_attempts=1,
        idempotency_key=f"nova-control-action:{job_type}:{fingerprint}",
        governance_context=context)
    return {"status": "queued", "job_id": job.job_id, "job_state": job.state,
        "department": department, "job_type": job_type, "external_action": False,
        "spend_allowed": False, "receipt_boundary": "existing durable Nexus worker"}


def _requests_external_or_production_action(text: str) -> bool:
    """Reject requested side effects while allowing clear negative constraints."""
    forbidden = ("publish", "publishing", "post publicly", "send to customers", "purchase", "purchasing",
                 "live trade", "deploy", "deployment", "commit", "committing", "push", "pushing")
    value = str(text or "").casefold()
    for term in forbidden:
        pattern = re.compile(r"\b" + r"\s+".join(re.escape(part) for part in term.split()) + r"\b")
        for match in pattern.finditer(value):
            clause_start = max(value.rfind(mark, 0, match.start()) for mark in (".", "!", "?", ";", "\n")) + 1
            prefix = value[clause_start:match.start()]
            if re.search(r"\b(?:do\s+not|don't|never|no|without)\b(?:(?![.!?;]).){0,80}$", prefix):
                continue
            return True
    return False


def _assign_creative_asset(task: str, parent_request_id: str = "") -> dict[str, Any]:
    return _assign_nova_control_action("NOVA_CREATIVE_ASSET", "CREATIVE", task, parent_request_id)


def _assign_bounded_coding_task(task: str, parent_request_id: str = "") -> dict[str, Any]:
    return _assign_nova_control_action("NOVA_BOUNDED_CODING_TASK", "SYSTEMS", task, parent_request_id)


def _assign_alpha_review(request: str, parent_request_id: str = "") -> dict[str, Any]:
    """Queue Alpha to evaluate an already completed Research artifact."""
    from nexus_agent_platform.durable_jobs import default_store

    if not request or len(request) > 240 or not re.search(r"\b(alpha|review|evaluate)\b", request, re.I):
        return {"status": "rejected", "error": "bounded_alpha_review_request_required"}
    store = default_store()
    # Resolve the exact prior Microsoft Project Research result from the
    # persisted completion event, then require its durable job and receipt to
    # be complete before passing that lineage to Alpha.
    event_path = nexus_research_state_path("runtime", "nova_material_events.jsonl")
    matches = []
    try:
        for line in event_path.read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            if (isinstance(row, dict) and row.get("event_type") == "SIGNIFICANT_RESEARCH"
                    and "microsoft project" in json.dumps(row, ensure_ascii=False).casefold()
                    and row.get("research_job_id")):
                matches.append(row)
    except (OSError, ValueError):
        pass
    job_ids = list(dict.fromkeys(str(row["research_job_id"]) for row in matches))
    source_job = next((store.get(job_id) for job_id in reversed(job_ids)
                       if store.get(job_id) and store.get(job_id).department.upper() == "RESEARCH"
                       and store.get(job_id).state == "COMPLETED" and store.get(job_id).receipt_ref), None)
    if source_job is None:
        return {"status": "rejected", "error": "completed_matching_research_evidence_not_found"}
    event = next((row for row in reversed(matches)
                  if str(row.get("research_job_id")) == source_job.job_id
                  and row.get("durable_receipt_id") == source_job.receipt_ref), None)
    if event is None:
        return {"status": "rejected", "error": "research_event_receipt_lineage_mismatch"}
    receipt_ref = str(event.get("department_receipt_id") or "")
    receipt_path = ROOT / "reports/rebuild/nexus_loop_receipts" / f"{Path(receipt_ref).name}.json"
    if not receipt_ref or not receipt_path.is_file():
        return {"status": "rejected", "error": "source_research_artifact_missing"}
    fingerprint = hashlib.sha256(("ALPHA\n" + source_job.job_id + "\n" + str(parent_request_id)).encode()).hexdigest()[:24]
    payload_path = nexus_research_state_path("runtime", "nexus_mcp_jobs", f"{fingerprint}.json")
    payload_ref = str(payload_path)
    payload_path.parent.mkdir(parents=True, exist_ok=True)
    payload_path.write_text(json.dumps({
        "schema_version": "nexus.alpha-existing-research-review.v1",
        "department": "ALPHA", "source_research_job_id": source_job.job_id,
        "source_durable_receipt_id": source_job.receipt_ref,
        "source_department_receipt_id": receipt_ref,
        "source_artifact_ref": str(receipt_path.relative_to(ROOT)),
        "request": request, "question": "Review Microsoft Project using the linked Research evidence.",
        "parent_request_id": str(parent_request_id or ""),
        "created_by": "NOVA_NEXUS", "research_creation_authorized": False,
    }, indent=2) + "\n", encoding="utf-8")
    campaign_context={}
    parent_job_id=None
    correlation_id=str(parent_request_id or fingerprint)
    try:
        from nexus_agent_platform.durable_objective_control import ACTIVE_CAMPAIGN_PATH,load_active_campaign
        state=load_active_campaign() if ACTIVE_CAMPAIGN_PATH.exists() else {}
        if state.get("CAMPAIGN_STATUS") in {"ACTIVE","IN_PROGRESS"}:
            campaign_context={"campaign_id":state.get("CAMPAIGN_ID"),
                "owner_objective_id":state.get("OWNER_OBJECTIVE_ID"),
                "objective_version":state.get("OBJECTIVE_VERSION"),"independent_job":True}
            parent_job_id=state.get("CURRENT_JOB_ID")
            correlation_id=str(state.get("CORRELATION_ID") or state.get("CAMPAIGN_ID") or correlation_id)
    except (ImportError,OSError,ValueError):
        campaign_context={}
    alpha_context={**campaign_context,"source":"NOVA_MCP_ALPHA_ASSIGNMENT",
        "spend_allowed":False,"paid_provider_authorized":False,"external_actions_allowed":False,
        "external_actions_authorized":False,"research_creation_authorized":False,
        "source_research_job_id":source_job.job_id}
    job = store.enqueue("ALPHA", "NEXUS_DEPARTMENT_QUERY", priority=100,
        payload_ref=payload_ref, parent_job_id=parent_job_id, correlation_id=correlation_id,
        max_attempts=2, idempotency_key=f"nova-alpha-existing-research-review:{fingerprint}",
        governance_context=alpha_context)
    # Parent and governance fields are part of the atomic enqueue contract.
    # Do not post-mutate an idempotent existing job: it may already be complete
    # and attached to the original parent objective.
    event={"event_id":f"alpha-assigned-{job.job_id}","kind":"ALPHA_ASSIGNED","event_type":"ALPHA_ASSIGNED",
        "title":"Nexus Alpha accepted the Microsoft Project review",
        "department":"ALPHA","status":job.state,"source":job.job_id,
        "alpha_job_id":job.job_id,"source_research_job_id":source_job.job_id,
        "summary":f"ALPHA_JOB_ID={job.job_id}\nJOB_STATUS={job.state}\nEXECUTING_DEPARTMENT=ALPHA\nSOURCE_RESEARCH_JOB_ID={source_job.job_id}",
        "why_it_matters":"The existing Research evidence is queued for the actual Nexus Alpha evaluator.",
        "next":"Alpha will evaluate the linked artifact; no new Research job or objective was created."}
    from nova.proactive_communications import MATERIAL_EVENTS_PATH
    MATERIAL_EVENTS_PATH.parent.mkdir(parents=True,exist_ok=True)
    prior=[]
    try:
        prior=[json.loads(line).get("event_id") for line in MATERIAL_EVENTS_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]
    except (OSError,ValueError):
        pass
    if event["event_id"] not in prior:
        with MATERIAL_EVENTS_PATH.open("a",encoding="utf-8") as stream:
            stream.write(json.dumps(event,sort_keys=True)+"\n")
    return {"status": "queued", "job_id": job.job_id, "job_state": job.state,
        "department": "ALPHA", "source_research_job_id": source_job.job_id,
        "source_research_receipt_id": source_job.receipt_ref,
        "notice_job_id": None,
        "receipt_boundary": "existing durable Nexus worker", "objective_created": False,
        "research_job_created": False}


def _assign_notebooklm_runtime_canary(parent_request_id: str = "") -> dict[str, Any]:
    """Queue one isolated Research-owned NotebookLM runtime canary.

    The canary creates a small NotebookLM workspace, imports one public MCP
    documentation page, asks one source-scoped question, and verifies the
    persisted turn. It creates no owner objective and authorizes no spending.
    """
    from nexus_agent_platform.durable_jobs import default_store
    from nexus_agent_platform.durable_objective_control import ACTIVE_CAMPAIGN_PATH, load_active_campaign

    campaign = load_active_campaign() if ACTIVE_CAMPAIGN_PATH.exists() else {}
    context = {
        "source": "NOVA_MCP_NOTEBOOKLM_CANARY",
        "runtime_restoration_canary": True,
        "spend_allowed": False,
        "paid_provider_authorized": False,
        "external_actions_allowed": False,
        "external_actions_authorized": False,
        "resource_dependencies": ["NOTEBOOKLM"],
    }
    parent_job_id = None
    correlation_id = str(parent_request_id or "nexus-runtime-notebooklm-canary")
    if campaign.get("CAMPAIGN_STATUS") in {"ACTIVE", "IN_PROGRESS"}:
        context.update({"campaign_id": campaign.get("CAMPAIGN_ID"),
                        "owner_objective_id": campaign.get("OWNER_OBJECTIVE_ID"),
                        "objective_version": campaign.get("OBJECTIVE_VERSION"),
                        "independent_job": True})
        parent_job_id = campaign.get("CURRENT_JOB_ID")
        correlation_id = str(campaign.get("CORRELATION_ID") or correlation_id)
    import hashlib
    fingerprint = hashlib.sha256(str(parent_request_id or "nexus-runtime-notebooklm-canary").encode()).hexdigest()[:24]
    payload_path = nexus_research_state_path("runtime", "nexus_mcp_jobs",
        f"notebooklm_runtime_canary_{fingerprint}.json")
    payload_path.parent.mkdir(parents=True, exist_ok=True)
    payload_path.write_text(json.dumps({
        "schema_version": "nexus.notebooklm-runtime-canary.v1",
        "operation": "RUNTIME_CANARY",
        "case_id": f"nexus_runtime_canary_{fingerprint}",
        "notebook_title": "Nexus runtime restoration NotebookLM canary",
        "source_url": "https://modelcontextprotocol.io/introduction",
        "source_title": "Model Context Protocol introduction",
        "question": "Based only on this source, explain in one sentence what a Model Context Protocol server provides. Cite the source.",
        "created_by": "hermes_nova",
    }, indent=2) + "\n", encoding="utf-8")
    job = default_store().enqueue("RESEARCH", "NEXUS_NOTEBOOKLM_RUNTIME_CANARY", priority=1000,
        payload_ref=str(payload_path.relative_to(ROOT)), parent_job_id=parent_job_id,
        correlation_id=correlation_id, max_attempts=2,
        idempotency_key=f"nexus-runtime-notebooklm-canary:{fingerprint}",
        governance_context=context)
    return {"status": "queued", "job_id": job.job_id, "job_state": job.state,
            "department": "RESEARCH", "intent": "NOTEBOOKLM_RUNTIME_CANARY",
            "receipt_boundary": "existing durable Nexus Research worker",
            "objective_created": False, "external_action": False}


def _resume_research() -> dict[str, Any]:
    from nexus_agent_platform.nova_codex_bridge import resume_parent_objective
    return resume_parent_objective()


def _action_call(tool_name: str, operation, arguments: dict[str, Any]) -> dict[str, Any]:
    authorize_action(tool_name)
    request_id = f"nexus-mcp-{uuid.uuid4().hex}"
    started = _now()
    previous_egress_job = os.environ.get("NEXUS_DURABLE_JOB_ID")
    previous_execution_id = os.environ.get("NEXUS_DURABLE_EXECUTION_ID")
    previous_job_budget = os.environ.get("NEXUS_JOB_BUDGET")
    # Every governed action invoked through the long-lived bridge gets its own bounded
    # invocation budget (32 requests / 1 MB) instead of the feeder's process-lifetime
    # fallback identity. Exact durable-job identities keep their job-wide budgets.
    scoped_invocation = not previous_egress_job or previous_egress_job.startswith("feeder-process-")
    scoped_research_intake = scoped_controller_action = scoped_invocation
    try:
        if scoped_research_intake or scoped_controller_action:
            # A long-lived MCP bridge can inherit the feeder's process-wide
            # fallback identity. Scope governed writes to this bounded MCP
            # invocation; controller status reads use the local mirror above.
            os.environ["NEXUS_DURABLE_JOB_ID"] = request_id
            os.environ["NEXUS_DURABLE_EXECUTION_ID"] = request_id
            try:
                budget = json.loads(previous_job_budget or "{}")
            except (TypeError, ValueError):
                budget = {}
            budget["max_requests"] = min(32, max(1, int(budget.get("max_requests", 32))))
            budget["max_response_bytes"] = min(1_000_000, max(1, int(budget.get("max_response_bytes", 1_000_000))))
            os.environ["NEXUS_JOB_BUDGET"] = json.dumps(budget, separators=(",", ":"))
        try:
            result = operation(**arguments)
        finally:
            if scoped_research_intake or scoped_controller_action:
                if previous_egress_job is None:
                    os.environ.pop("NEXUS_DURABLE_JOB_ID", None)
                else:
                    os.environ["NEXUS_DURABLE_JOB_ID"] = previous_egress_job
                if previous_execution_id is None:
                    os.environ.pop("NEXUS_DURABLE_EXECUTION_ID", None)
                else:
                    os.environ["NEXUS_DURABLE_EXECUTION_ID"] = previous_execution_id
                if previous_job_budget is None:
                    os.environ.pop("NEXUS_JOB_BUDGET", None)
                else:
                    os.environ["NEXUS_JOB_BUDGET"] = previous_job_budget
    except Exception as exc:
        result = {"status": "error", "error": f"{type(exc).__name__}: {exc}"}
    receipt = {
        "schema_version": "nexus.mcp-action-receipt.v1",
        "request_id": request_id,
        "tool_name": tool_name,
        "started_at": started,
        "completed_at": _now(),
        "result_status": result.get("status"),
        "read_only": False,
        "authority_owner": "Nexus",
        "requested_by": "hermes_nova",
        "external_action": False,
    }
    receipt["receipt_hash"] = hashlib.sha256(json.dumps(receipt, sort_keys=True).encode()).hexdigest()
    RECEIPT_DIR.mkdir(parents=True, exist_ok=True)
    (RECEIPT_DIR / f"{request_id}.json").write_text(json.dumps({**receipt, "result": result}, indent=2) + "\n", encoding="utf-8")
    return {**result, "request_id": request_id, "receipt": receipt["receipt_hash"]}


_SYSTEMS_HOST_CONTROL_TOOLS = {
    "systems_oracle_release_inspect": ("systems.oracle.release.inspect", "READ"),
    "systems_oracle_release_stage": ("systems.oracle.release.stage", "WRITE"),
    "systems_oracle_nova_snapshot": ("systems.oracle.nova.snapshot", "READ_WITH_SNAPSHOT_STATE_WRITE"),
    "systems_oracle_nova_snapshot_validate": ("systems.oracle.nova.snapshot_validate", "READ"),
    "systems_oracle_nova_poller_status": ("systems.oracle.nova.poller_status", "READ"),
    "systems_oracle_nova_activate": ("systems.oracle.nova.activate", "WRITE"),
    "systems_oracle_nova_verify": ("systems.oracle.nova.verify", "READ"),
    "systems_oracle_nova_rollback": ("systems.oracle.nova.rollback", "WRITE"),
    "systems_oracle_receipt_read": ("systems.oracle.receipt.read", "READ"),
}

def _systems_host_control_call(tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Route one MCP operation through the registered Systems typed adapter."""
    entry = _SYSTEMS_HOST_CONTROL_TOOLS.get(tool_name)
    if entry is None:
        raise PermissionError("SYSTEMS_HOST_CONTROL_TOOL_NOT_REGISTERED")
    capability, operation_class = entry
    if operation_class == "READ":
        authorize_read(tool_name)
    else:
        # This is only MCP surface authorization. Host Control independently
        # validates Ray approval for stage, activation, and rollback.
        authorize_action(tool_name)
    request_id = f"nexus-mcp-{uuid.uuid4().hex}"
    started = _now()
    try:
        from nexus_agent_platform.systems_consumer import invoke_oracle_host_control
        transport_result = invoke_oracle_host_control(capability, arguments, request_id)
        result_status = str(transport_result.get("status") or "unknown")
        error = (transport_result.get("result") or {}).get("error")
        payload = {"status": result_status, "capability": capability,
                   "correlation_id": transport_result.get("correlation_id"),
                   "host_result": transport_result.get("result"),
                   "response_sha256": transport_result.get("response_sha256"),
                   "operation_class": operation_class,
                   "approval_required": operation_class == "WRITE"}
    except Exception as exc:
        result_status = "error"
        error = type(exc).__name__
        payload = {"status": result_status, "capability": capability,
                   "operation_class": operation_class, "error": error}
    receipt = {"schema_version": "nexus.mcp-systems-host-control-receipt.v1",
        "request_id": request_id, "correlation_id": request_id,
        "tool_name": tool_name, "capability": capability,
        "operation_class": operation_class, "started_at": started,
        "completed_at": _now(), "result_status": result_status,
        "error": error, "read_only": operation_class == "READ",
        "authority_owner": "SYSTEMS", "host_id": "nexus-llm-worker"}
    receipt["receipt_hash"] = hashlib.sha256(json.dumps(receipt, sort_keys=True).encode()).hexdigest()
    RECEIPT_DIR.mkdir(parents=True, exist_ok=True)
    (RECEIPT_DIR / f"{request_id}.json").write_text(json.dumps({**receipt, "result": payload}, indent=2) + "\n", encoding="utf-8")
    return {**payload, "request_id": request_id, "receipt": receipt["receipt_hash"]}

_WORKSPACE_READ_ROOTS = (ROOT.resolve(),)
_WORKSPACE_ARTIFACT_ROOT = Path(os.getenv("NEXUS_REPO_ROOT", str(ROOT))).expanduser().resolve()
# data/runtime is deliberately read-only in the active workspace. Both NOTE and
# FILE entities use the writable, bounded reports namespace until a dedicated
# artifact root is provisioned with its own verified permissions.
_WORKSPACE_WRITE_PREFIXES = ("reports/nova_internal/",)
_WORKSPACE_DENIED_PARTS = {".ssh", ".aws", ".oci", ".config", "credentials", "keychain", "secrets", "secret", "private_keys"}
_WORKSPACE_DENIED_NAMES = {".env", "runtime.env", "id_rsa", "id_ed25519", "credentials.json", "token.json"}
_WORKSPACE_UPDATE_LOCK = threading.Lock()


def _workspace_path(relative_path: str, *, write: bool = False) -> Path:
    rel = str(relative_path or "").replace("\\", "/").strip().lstrip("/")
    if not rel or ".." in Path(rel).parts or Path(rel).is_absolute():
        raise ValueError("workspace_relative_path_required")
    parts = tuple(part.casefold() for part in Path(rel).parts)
    if any(part in _WORKSPACE_DENIED_PARTS or part in _WORKSPACE_DENIED_NAMES or part.startswith(".env")
           or part.endswith((".pem", ".key", ".p12", ".pfx"))
           or any(word in part for word in ("credential", "secret", "token", "private_key"))
           for part in parts):
        raise PermissionError("sensitive_workspace_path_denied")
    artifact_prefix = next((prefix for prefix in _WORKSPACE_WRITE_PREFIXES if rel.startswith(prefix)), None)
    if write and artifact_prefix is None:
        raise PermissionError("workspace_write_root_not_allowlisted")
    if artifact_prefix:
        # Immutable releases cannot hold generated artifacts. Map only the two
        # declared artifact namespaces to the canonical writable Nexus repo.
        scope = (_WORKSPACE_ARTIFACT_ROOT / artifact_prefix.rstrip("/")).resolve()
        candidate = (_WORKSPACE_ARTIFACT_ROOT / rel).resolve()
        if candidate != scope and scope not in candidate.parents:
            raise PermissionError("workspace_artifact_path_outside_approved_scope")
        return candidate
    candidate = (ROOT / rel).resolve()
    if not any(candidate == root or root in candidate.parents for root in _WORKSPACE_READ_ROOTS):
        raise PermissionError("workspace_path_outside_approved_roots")
    return candidate


def _read_workspace_file(relative_path: str) -> dict[str, Any]:
    authorize_read("nexus_read_workspace_file")
    request_id = f"nexus-mcp-{uuid.uuid4().hex}"
    try:
        path = _workspace_path(relative_path)
        if not path.is_file():
            result = {"status": "not_found", "error": "workspace_file_not_found"}
        elif path.stat().st_size > 1_000_000:
            result = {"status": "rejected", "error": "workspace_file_exceeds_1mb_bound"}
        else:
            data = path.read_bytes()
            try:
                content = data.decode("utf-8")
            except UnicodeDecodeError:
                result = {"status": "rejected", "error": "binary_workspace_file_not_readable"}
            else:
                result = {"status": "ok", "path": str(relative_path),
                          "content": content[:100_000], "truncated": len(content) > 100_000,
                          "size_bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
    except Exception as exc:
        result = {"status": "rejected", "error": f"{type(exc).__name__}:{exc}"}
    receipt = {"schema_version": "nexus.mcp-receipt.v1", "request_id": request_id,
               "tool_name": "nexus_read_workspace_file", "completed_at": _now(),
               "result_status": result.get("status"), "read_only": True,
               "path": result.get("path"), "authority_owner": "Nexus"}
    receipt["receipt_hash"] = hashlib.sha256(json.dumps(receipt, sort_keys=True).encode()).hexdigest()
    RECEIPT_DIR.mkdir(parents=True, exist_ok=True)
    (RECEIPT_DIR / f"{request_id}.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return {**result, "request_id": request_id, "receipt": receipt["receipt_hash"]}


def _write_workspace_artifact(relative_path: str, content: str) -> dict[str, Any]:
    path = _workspace_path(relative_path, write=True)
    payload = str(content)
    if len(payload.encode("utf-8")) > 100_000:
        return {"status": "rejected", "error": "artifact_exceeds_100kb_bound", "created": False}
    if path.exists():
        return {"status": "conflict", "error": "refusing_to_overwrite_existing_artifact", "created": False}
    path.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation makes retries unable to overwrite an existing artifact.
    with path.open("x", encoding="utf-8") as stream:
        stream.write(payload)
    return {"status": "created", "path": str(relative_path),
            "sha256": hashlib.sha256(payload.encode("utf-8")).hexdigest(),
            "size_bytes": len(payload.encode("utf-8")), "created": True}


def _update_workspace_artifact(relative_path: str, content: str, expected_sha256: str,
                               note_id: str = "", file_id: str = "") -> dict[str, Any]:
    """Update one existing allowlisted artifact with exact-entity and hash preconditions."""
    rel = str(relative_path or "").replace("\\", "/").strip().lstrip("/")
    entity_ids = [str(value) for value in (note_id, file_id) if value]
    if len(entity_ids) != 1 or entity_ids[0] != rel:
        return {"status": "rejected", "error": "workspace_entity_path_mismatch", "updated": False}
    if not re.fullmatch(r"[0-9a-fA-F]{64}", str(expected_sha256 or "")):
        return {"status": "rejected", "error": "expected_sha256_invalid", "updated": False}
    payload = str(content)
    data = payload.encode("utf-8")
    if len(data) > 100_000:
        return {"status": "rejected", "error": "artifact_exceeds_100kb_bound", "updated": False}
    try:
        path = _workspace_path(rel, write=True)
        root = _WORKSPACE_ARTIFACT_ROOT.resolve()
        unresolved = root / rel
        current = root
        for part in Path(rel).parts:
            current = current / part
            if current.is_symlink():
                return {"status": "rejected", "error": "workspace_symlink_update_denied", "updated": False}
        if unresolved.resolve() != path or path == root:
            return {"status": "rejected", "error": "workspace_artifact_path_outside_approved_scope", "updated": False}
    except Exception as exc:
        return {"status": "rejected", "error": f"{type(exc).__name__}:{exc}", "updated": False}

    temporary = path.with_name(f".{path.name}.update-{uuid.uuid4().hex}.tmp")
    try:
        with _WORKSPACE_UPDATE_LOCK:
            if not path.is_file():
                return {"status": "not_found", "error": "workspace_artifact_not_found", "updated": False}
            old_stat = path.stat()
            if old_stat.st_size > 100_000:
                return {"status": "rejected", "error": "existing_artifact_exceeds_100kb_bound", "updated": False}
            old_data = path.read_bytes()
            try:
                old_data.decode("utf-8")
            except UnicodeDecodeError:
                return {"status": "rejected", "error": "binary_workspace_file_not_updateable", "updated": False}
            previous_hash = hashlib.sha256(old_data).hexdigest()
            if previous_hash != str(expected_sha256).lower():
                return {"status": "conflict", "error": "workspace_artifact_hash_mismatch",
                        "updated": False, "current_sha256": previous_hash}
            mode = old_stat.st_mode & 0o777
            fd = os.open(str(temporary), os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
            try:
                view = memoryview(data)
                while view:
                    written = os.write(fd, view)
                    view = view[written:]
                os.fsync(fd)
                os.fchmod(fd, mode)
            finally:
                os.close(fd)
            os.replace(str(temporary), str(path))
            dir_fd = os.open(str(path.parent), os.O_RDONLY)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)
            return {"status": "updated", "path": rel, "created": False, "updated": True,
                    "previous_sha256": previous_hash, "sha256": hashlib.sha256(data).hexdigest(),
                    "size_bytes": len(data)}
    except Exception as exc:
        return {"status": "error", "error": f"{type(exc).__name__}:{exc}", "updated": False}
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass


def _delete_workspace_artifact(relative_path: str, expected_sha256: str,
                               note_id: str = "", file_id: str = "") -> dict[str, Any]:
    """Delete one exact existing bounded artifact after entity and hash checks."""
    rel = str(relative_path or "").replace("\\", "/").strip().lstrip("/")
    entity_ids = [str(value) for value in (note_id, file_id) if value]
    if len(entity_ids) != 1 or entity_ids[0] != rel:
        return {"status": "rejected", "error": "workspace_entity_path_mismatch", "deleted": False}
    if not re.fullmatch(r"[0-9a-fA-F]{64}", str(expected_sha256 or "")):
        return {"status": "rejected", "error": "expected_sha256_invalid", "deleted": False}
    try:
        path = _workspace_path(rel, write=True)
        root = _WORKSPACE_ARTIFACT_ROOT.resolve()
        current = root
        for part in Path(rel).parts:
            current = current / part
            if current.is_symlink():
                return {"status": "rejected", "error": "workspace_symlink_delete_denied", "deleted": False}
        if path == root or path != root / rel or not any(
                prefix and rel.startswith(prefix) for prefix in _WORKSPACE_WRITE_PREFIXES):
            return {"status": "rejected", "error": "workspace_artifact_path_outside_approved_scope", "deleted": False}
    except Exception as exc:
        return {"status": "rejected", "error": f"{type(exc).__name__}:{exc}", "deleted": False}

    try:
        with _WORKSPACE_UPDATE_LOCK:
            if not path.exists():
                return {"status": "not_found", "error": "workspace_artifact_not_found", "deleted": False}
            if not path.is_file():
                return {"status": "rejected", "error": "workspace_artifact_not_regular_file", "deleted": False}
            before = path.stat()
            if before.st_size > 100_000:
                return {"status": "rejected", "error": "existing_artifact_exceeds_100kb_bound", "deleted": False}
            old_data = path.read_bytes()
            try:
                old_data.decode("utf-8")
            except UnicodeDecodeError:
                return {"status": "rejected", "error": "binary_workspace_file_not_deletable", "deleted": False}
            old_hash = hashlib.sha256(old_data).hexdigest()
            if old_hash != str(expected_sha256).lower():
                return {"status": "conflict", "error": "workspace_artifact_hash_mismatch",
                        "deleted": False, "current_sha256": old_hash}
            current = path.stat()
            if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
                    current.st_dev, current.st_ino, current.st_size, current.st_mtime_ns):
                return {"status": "conflict", "error": "workspace_artifact_changed_during_delete",
                        "deleted": False}
            path.unlink()
            dir_fd = os.open(str(path.parent), os.O_RDONLY)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)
            return {"status": "deleted", "path": rel, "deleted": True,
                    "created": False, "previous_sha256": old_hash}
    except Exception as exc:
        return {"status": "error", "error": f"{type(exc).__name__}:{exc}", "deleted": False}


def _register() -> None:
    @mcp.tool(name="nexus_read_workspace_file", description="READ ONLY bounded Nexus workspace read. Allows UTF-8 files under the Nexus repository, denies credentials/private keys, and caps reads at 1 MB; external_effect=no; production_effect=no.")
    def nexus_read_workspace_file(relative_path: str) -> dict[str, Any]:
        return _read_workspace_file(relative_path)

    @mcp.tool(name="nexus_write_workspace_artifact", description="GOVERNED internal write: create a new UTF-8 artifact only under reports/nova_internal/. Never overwrites; 100 KB maximum; credential paths are denied; write_allowed=yes; cost=zero; external_effect=no; production_effect=no; reversible=yes by exact-path delete after independent verification.")
    def nexus_write_workspace_artifact(relative_path: str, content: str) -> dict[str, Any]:
        return _action_call("nexus_write_workspace_artifact", _write_workspace_artifact,
                            {"relative_path": relative_path, "content": content})

    @mcp.tool(name="nexus_update_workspace_artifact", description="GOVERNED bounded internal update: modifies one existing UTF-8 artifact only under reports/nova_internal/. Requires its exact NOTE_ID or FILE_ID to equal the relative path and the current SHA-256; rejects missing, stale, oversized, sensitive, or symlinked targets. Never creates a file; 100 KB maximum; write_allowed=yes; cost=zero; external_effect=no; production_effect=no; reversible=yes.")
    def nexus_update_workspace_artifact(relative_path: str, content: str, expected_sha256: str,
                                        note_id: str = "", file_id: str = "") -> dict[str, Any]:
        return _action_call("nexus_update_workspace_artifact", _update_workspace_artifact,
            {"relative_path": relative_path, "content": content, "expected_sha256": expected_sha256,
             "note_id": note_id, "file_id": file_id})

    @mcp.tool(name="nexus_delete_workspace_artifact", description="GOVERNED bounded internal delete: removes one existing UTF-8 artifact only under reports/nova_internal/. Requires its exact NOTE_ID or FILE_ID to equal the relative path and current SHA-256; rejects missing, stale, oversized, sensitive, directory, or symlinked targets. Never creates files; write_allowed=yes; cost=zero; external_effect=no; production_effect=no; reversible=yes only with the persisted exact pre-delete snapshot and lineage.")
    def nexus_delete_workspace_artifact(relative_path: str, expected_sha256: str,
                                        note_id: str = "", file_id: str = "") -> dict[str, Any]:
        return _action_call("nexus_delete_workspace_artifact", _delete_workspace_artifact,
            {"relative_path": relative_path, "expected_sha256": expected_sha256,
             "note_id": note_id, "file_id": file_id})

    @mcp.tool(name="nexus_create_department_directive", description="GOVERNED bounded internal action: create ONE durable Nexus department directive (target MARKETING, CREATIVE, or REA) when a completed Nexus result or project justifies a concrete next business action within policy. Provide objective, task, required_output, evidence_references (e.g. the Research job id) and restrictions. Creates durable work only; the Nexus dispatcher executes it and automatically continues to the next department (e.g. Marketing -> Creative). Never executes work, publishes, or spends; cost=zero; external_effect=no. For REA, inputs must include target and authorization_ref (owner-authorized clean-room analysis); REA runs on the Contabo harness. Pass business_id (venture id) when known. Do not use for casual conversation.")
    def nexus_create_department_directive(target_department: Literal["MARKETING", "CREATIVE", "REA"], objective: str, task: str,
                                          required_output: list[str], project_id: str = "", evidence_references: list[str] | None = None,
                                          inputs: dict[str, Any] | None = None, restrictions: list[str] | None = None,
                                          success_criteria: list[str] | None = None, parent_request_id: str = "",
                                          business_id: str = "") -> dict[str, Any]:
        return _action_call("nexus_create_department_directive", _create_department_directive, {
            "business_id": business_id,
            "target_department": target_department, "objective": objective, "task": task, "required_output": required_output,
            "project_id": project_id, "evidence_references": evidence_references, "inputs": inputs, "restrictions": restrictions,
            "success_criteria": success_criteria, "parent_request_id": parent_request_id})

    @mcp.tool(name="nexus_get_directive_events", description="VOLATILE read for Nova's proactive notifier: recent department-directive rows with their lifecycle events (DIRECTIVE_CREATED, WORK_STARTED, WORK_COMPLETED, WORK_FAILED, APPROVAL_REQUIRED, PROJECT_BLOCKED, PROJECT_CONTINUED, CREATIVE_CREATED, CAMPAIGN_CREATED, COMMERCE_OFFER_CREATED, REA_WORK_STARTED, REA_WORK_COMPLETED, REA_WORK_FAILED). Read-only.")
    def nexus_get_directive_events(since: str = "", limit: int = 20) -> dict[str, Any]:
        authorize_read("nexus_get_directive_events")
        return _scoped_read(_get_directive_events, since, limit)

    @mcp.tool(name="nexus_get_department_directive", description="VOLATILE read of one durable department directive by DIRECTIVE_ID (job_...): status, result, event history, and automatically created child directives (continuation). Read-only.")
    def nexus_get_department_directive(directive_id: str) -> dict[str, Any]:
        authorize_read("nexus_get_department_directive")
        return _scoped_read(_get_department_directive, directive_id)

    @mcp.tool(name="nexus_get_project", description="VOLATILE current-state read of ONE existing Nexus project by exact PROJECT_ID (proj_...): status, current department/stage, next action, blockers, approvals waiting (with live approval-card status), commerce offer, metrics, creative assets, recent handoffs. Use whenever the owner names a project id or asks to resume/continue/check an existing project. Read-only: never resumes, approves, or publishes.")
    def nexus_get_project(project_id: str) -> dict[str, Any]:
        return _project_read("nexus_get_project", "get_project", project_id=project_id)

    @mcp.tool(name="nexus_get_project_approvals", description="VOLATILE current-state read of the approvals linked to ONE existing Nexus project by exact PROJECT_ID (proj_...): each approval's live state (WAITING_FOR_RAY, APPROVED, CONSUMED, SUPERSEDED), what it covers, and the owner command that would act on it. Use when the owner asks which approvals are waiting for a specific project. Read-only: never approves, publishes, or activates anything.")
    def nexus_get_project_approvals(project_id: str) -> dict[str, Any]:
        return _project_read("nexus_get_project_approvals", "get_project_approvals", project_id=project_id)

    @mcp.tool(name="nexus_get_projects", description="VOLATILE read: list existing Nexus projects (id, opportunity name, venture, status, current department), optionally filtered by words such as a product or venture name. Use to find a project id before nexus_get_project. Read-only.")
    def nexus_get_projects(query: str = "") -> dict[str, Any]:
        return _project_read("nexus_get_projects", "list_projects", query=query)

    @mcp.tool(name="nexus_list_research_rooms", description="VOLATILE read: list persistent Research Rooms (room_id, title, status, preliminary score, source count, updated_at). Read-only.")
    def nexus_list_research_rooms(status: str = "", query: str = "", limit: int = 20) -> dict[str, Any]:
        return _research_room_read("nexus_list_research_rooms", _list_research_rooms, status=status, query=query, limit=limit)

    @mcp.tool(name="nexus_get_research_room", description="VOLATILE read: get one persistent Research Room by room_id, including its sources, compact research brief, preliminary score, and Alpha conversation history. Read-only.")
    def nexus_get_research_room(room_id: str) -> dict[str, Any]:
        return _research_room_read("nexus_get_research_room", _get_research_room, room_id=room_id)

    @mcp.tool(name="nexus_create_research_room", description="GOVERNED bounded internal action: create a persistent Research Room with an initial title and optional source. Zero spend; no autonomous research loops.")
    def nexus_create_research_room(title: str, source_content: str = "", source_type: str = "TEXT", source_title: str = "") -> dict[str, Any]:
        return _action_call("nexus_create_research_room", _create_research_room, {
            "title": title, "source_content": source_content, "source_type": source_type, "source_title": source_title,
        })

    @mcp.tool(name="nexus_add_room_source", description="GOVERNED bounded internal action: add a source (TEXT, URL, YOUTUBE, or EXISTING_RESEARCH) to an existing Research Room. Automatically updates the Compact Research Brief. Zero spend; no autonomous continuation loops.")
    def nexus_add_room_source(room_id: str, source_type: str, content_or_url: str, title: str = "") -> dict[str, Any]:
        return _action_call("nexus_add_room_source", _add_room_source, {
            "room_id": room_id, "source_type": source_type, "content_or_url": content_or_url, "title": title,
        })

    @mcp.tool(name="nexus_ask_alpha_research_room", description="GOVERNED bounded internal action: converse with Alpha inside a Research Room. Alpha checks room evidence and may use existing governed public search/read tools when evidence is insufficient. User-initiated only; does not trigger autonomous ingestion or directives.")
    def nexus_ask_alpha_research_room(room_id: str, question: str) -> dict[str, Any]:
        return _action_call("nexus_ask_alpha_research_room", _ask_alpha_research_room, {
            "room_id": room_id, "question": question,
        })

    @mcp.tool(name="nexus_score_research_room", description="GOVERNED bounded internal action: calculate or update the preliminary room score (0-100 across 5 dimensions: Nexus relevance, revenue/business potential, evidence quality, ease of execution, automation potential) without triggering deep research.")
    def nexus_score_research_room(room_id: str) -> dict[str, Any]:
        return _action_call("nexus_score_research_room", _score_research_room, {
            "room_id": room_id,
        })

    @mcp.tool(name="nexus_promote_research_room", description="GOVERNED bounded internal action: promote a Research Room into a governed Nexus project candidate for Nova on explicit request. Produces a promotion package; does not spend or publish.")
    def nexus_promote_research_room(room_id: str, requested_objective: str = "") -> dict[str, Any]:
        return _action_call("nexus_promote_research_room", _promote_research_room, {
            "room_id": room_id, "requested_objective": requested_objective,
        })

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

    @mcp.tool(name="nexus_get_research_state", description="Read-only bounded Research Room status from existing durable queue state. Supply objective_id only for exact objective lineage. Global status never recovers leases, mutates queues, materializes reports, or triggers research.")
    def nexus_get_research_state(objective_id: str = "") -> dict[str, Any]:
        return _call("nexus_get_research_state", {"objective_id": objective_id} if objective_id else {})

    @mcp.tool(name="nexus_get_research_queue", description="Read-only bounded Research queue summary from existing durable queue state. Never recovers leases, mutates queues, materializes reports, or triggers research.")
    def nexus_get_research_queue() -> dict[str, Any]:
        return _call("nexus_get_research_queue")

    @mcp.tool(name="nexus_get_alpha_review", description="VOLATILE bounded Alpha read. Supply objective_id to resolve the latest Alpha evaluation/receipt tied to that objective lineage; never substitute unrelated historical records.")
    def nexus_get_alpha_review(objective_id: str = "") -> dict[str, Any]:
        return _call("nexus_get_alpha_review", {"objective_id": objective_id} if objective_id else {})

    @mcp.tool(name="nexus_get_prior_department_result", description="Retrieve prior department results for cross-department or Nexus-wide investigation. For ordinary Research results, use the dedicated Research provider.")
    def nexus_get_prior_department_result(department: Literal["RESEARCH", "ALPHA", "SYSTEMS"], question: str = "") -> dict[str, Any]:
        return _get_prior_department_result(department, question)

    @mcp.tool(name="nexus_get_durable_jobs", description="Inspect durable jobs across Nexus for cross-engine operational diagnostics, queue investigation, or exact job lookup. For ordinary Research-engine status, use the dedicated Research provider.")
    def nexus_get_durable_jobs(state: str = "", limit: int = 30, job_id: str = "") -> dict[str, Any]:
        bounded_limit = max(1, min(int(limit or 30), 100))
        arguments = {"state": state, "limit": bounded_limit} if state else {"limit": bounded_limit}
        if job_id:
            arguments["job_id"] = job_id
        return _call("nexus_get_durable_jobs", arguments)

    @mcp.tool(name="nexus_get_research_execution_trace", description=(
        "Read sanitized, exact-job Research execution events from the canonical ledger. "
        "Requires one durable Research job ID; returns only matching operational metadata, "
        "never changes jobs, queues, cases, or budgets."
    ))
    def nexus_get_research_execution_trace(job_id: str) -> dict[str, Any]:
        return _get_research_execution_trace(job_id)

    @mcp.tool(name="nexus_get_codex_assignment", description="VOLATILE current Nova-to-Codex assignment and completion receipt read. Returns the existing governed coding-worker handoff only; no historical substitution.")
    def nexus_get_codex_assignment() -> dict[str, Any]:
        from nexus_agent_platform.nova_codex_bridge import read_assignment
        return {"status": "ok", "data": read_assignment(), "metadata": {"read_only": True, "canonical": True, "freshness": "live"}}


    @mcp.tool(name="systems_oracle_release_inspect", description="SYSTEMS operational read: inspect one exact immutable Oracle release by name and expected manifest hash. Fixed Oracle host and release root; no arbitrary path.")
    def systems_oracle_release_inspect(release_name: str, expected_hash: str) -> dict[str, Any]:
        return _systems_host_control_call("systems_oracle_release_inspect", {"release_name": release_name, "expected_hash": expected_hash})

    @mcp.tool(name="systems_oracle_release_stage", description="SYSTEMS governed write: stage one approved immutable Oracle artifact. Host Control independently requires hash-bound approval; fixed release root and no arbitrary destination.")
    def systems_oracle_release_stage(artifact_id: str, release_name: str, expected_release_hash: str,
                                    expected_manifest_hash: str, approval_id: str) -> dict[str, Any]:
        return _systems_host_control_call("systems_oracle_release_stage", {"artifact_id": artifact_id,
            "release_name": release_name, "expected_release_hash": expected_release_hash,
            "expected_manifest_hash": expected_manifest_hash, "approval_id": approval_id})

    @mcp.tool(name="systems_oracle_nova_snapshot", description="SYSTEMS scoped Nova configuration snapshot. Persists Host Control snapshot state but does not activate or restart Nova.")
    def systems_oracle_nova_snapshot() -> dict[str, Any]:
        return _systems_host_control_call("systems_oracle_nova_snapshot", {})

    @mcp.tool(name="systems_oracle_nova_snapshot_validate", description="SYSTEMS read-only validation of one exact previously captured Nova snapshot ID.")
    def systems_oracle_nova_snapshot_validate(snapshot_id: str) -> dict[str, Any]:
        return _systems_host_control_call("systems_oracle_nova_snapshot_validate", {"snapshot_id": snapshot_id})

    @mcp.tool(name="systems_oracle_nova_poller_status", description="SYSTEMS read-only poller status for the fixed Oracle Nova service cgroup. No process scanning or mutation.")
    def systems_oracle_nova_poller_status() -> dict[str, Any]:
        return _systems_host_control_call("systems_oracle_nova_poller_status", {})

    @mcp.tool(name="systems_oracle_nova_activate", description="SYSTEMS production Nova activation. Host Control requires single-use Ray approval bound to release, dependency, snapshot, and drop-in hashes. No arbitrary service or command.")
    def systems_oracle_nova_activate(deployment_id: str, target_release_name: str,
                                    target_release_hash: str, shared_release_hash: str,
                                    dependency_lock_hash: str, current_snapshot_hash: str,
                                    target_dropin_hash: str, expected_effective_dropin_count: int,
                                    automatic_rollback_on_failure: bool, approval_id: str) -> dict[str, Any]:
        return _systems_host_control_call("systems_oracle_nova_activate", {
            "deployment_id": deployment_id, "target_release_name": target_release_name,
            "target_release_hash": target_release_hash, "shared_release_hash": shared_release_hash,
            "dependency_lock_hash": dependency_lock_hash, "current_snapshot_hash": current_snapshot_hash,
            "target_dropin_hash": target_dropin_hash,
            "expected_effective_dropin_count": expected_effective_dropin_count,
            "automatic_rollback_on_failure": automatic_rollback_on_failure,
            "approval_id": approval_id})

    @mcp.tool(name="systems_oracle_nova_verify", description="SYSTEMS read-only verification of the exact expected immutable Nova release and hash.")
    def systems_oracle_nova_verify(expected_release_name: str, expected_release_hash: str) -> dict[str, Any]:
        return _systems_host_control_call("systems_oracle_nova_verify", {
            "expected_release_name": expected_release_name, "expected_release_hash": expected_release_hash})

    @mcp.tool(name="systems_oracle_nova_rollback", description="SYSTEMS production Nova rollback to one exact captured snapshot. Host Control requires Ray approval unless automatic rollback was pre-authorized by activation.")
    def systems_oracle_nova_rollback(snapshot_id: str, snapshot_hash: str,
                                    approval_id: str) -> dict[str, Any]:
        return _systems_host_control_call("systems_oracle_nova_rollback", {
            "snapshot_id": snapshot_id, "snapshot_hash": snapshot_hash, "approval_id": approval_id})

    @mcp.tool(name="systems_oracle_receipt_read", description="SYSTEMS read-only lookup of one exact Host Control receipt ID. No receipt enumeration or arbitrary path access.")
    def systems_oracle_receipt_read(receipt_id: str) -> dict[str, Any]:
        return _systems_host_control_call("systems_oracle_receipt_read", {"receipt_id": receipt_id})

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

    @mcp.tool(
        name="nexus_assign_research",
        description=(
            "Create one bounded internal Research assignment from Nova. "
            "This queues existing Research work only; Research AI selects tools "
            "and workers. Explicit requested_intent=RESEARCH_ONLY requires an approved "
            "source URL, performs one bounded public read, records a compact State v2 "
            "result, and stops before Advisor/Needle continuation. It cannot publish, "
            "spend, approve, or create a company cycle."
        ),
    )
    def nexus_assign_research(objective: str, question: str = "", priority: int = 0,
                              parent_request_id: str = "", followup_department: str = "",
                              requested_intent: str = "") -> dict[str, Any]:
        return _action_call("nexus_assign_research", _assign_research, {
            "objective": objective, "question": question, "priority": priority,
            "parent_request_id": parent_request_id, "followup_department": followup_department,
            "requested_intent": requested_intent,
        })

    @mcp.tool(name="nexus_continue_research", description="Continue one exact existing Research project by its objective_id, project_id, and current job_id. Reuses an active assignment or creates an idempotent child work item under the same project; never substitutes historical work, spends, or authorizes external actions.")
    def nexus_continue_research(objective_id: str, project_id: str, job_id: str,
                                instruction: str, parent_request_id: str = "") -> dict[str, Any]:
        return _action_call("nexus_continue_research", _continue_research, {
            "objective_id": objective_id, "project_id": project_id, "job_id": job_id,
            "instruction": instruction, "parent_request_id": parent_request_id,
        })

    @mcp.tool(name="nexus_get_research_case", description=(
        "READ ONLY exact existing Research case inspection. Requires the exact case, objective, project, and linked durable job IDs. "
        "Returns bounded case status, question/evidence identifiers, findings, and synthesis lineage; creates no work and performs no mutation."
    ))
    def nexus_get_research_case(case_id: str, objective_id: str, project_id: str,
                                durable_job_id: str) -> dict[str, Any]:
        return _get_research_case(case_id, objective_id, project_id, durable_job_id)

    @mcp.tool(name="nexus_record_research_synthesis", description=(
        "GOVERNED internal Research write; write_allowed=yes; cost=zero; external_effect=no; production_effect=no; reversible=yes. Append one evidence-linked synthesis to an existing exact case only, "
        "after verifying its objective, project, durable Research job, and attached source IDs. Zero spend; no new job, "
        "case, project, or external action. Every claim must cite one or more supplied source IDs."
    ))
    def nexus_record_research_synthesis(case_id: str, objective_id: str, project_id: str,
            durable_job_id: str, claims: list[dict[str, Any]], agreements: list[str],
            disagreements: list[str], uncertainties: list[str], source_ids: list[str]) -> dict[str, Any]:
        return _action_call("nexus_record_research_synthesis", _record_research_synthesis, {
            "case_id": case_id, "objective_id": objective_id, "project_id": project_id,
            "durable_job_id": durable_job_id, "claims": claims, "agreements": agreements,
            "disagreements": disagreements, "uncertainties": uncertainties, "source_ids": source_ids,
        })

    @mcp.tool(name="nexus_record_research_recommendation", description=(
        "GOVERNED internal Research transition; write_allowed=yes; cost=zero; external_effect=no; production_effect=no; reversible=yes. "
        "Record a source-backed decision-ready recommendation on one existing exact case. Requires exact case/objective/project/job lineage and attached case source IDs. "
        "Creates no objective, project, job, case, or external action."
    ))
    def nexus_record_research_recommendation(case_id: str, objective_id: str, project_id: str,
            durable_job_id: str, kind: Literal["TEST", "BUILD", "INTEGRATE", "AFFILIATE", "PARTNER", "SERVICE", "EDUCATION", "MONITOR", "GET_MORE_EVIDENCE", "PARK", "REJECT_WITH_EVIDENCE"],
            reason: str, source_ids: list[str], contradictory_evidence: list[str],
            uncertainties: list[str], missing_evidence: list[str], confidence: float,
            next_action: str) -> dict[str, Any]:
        return _action_call("nexus_record_research_recommendation", _record_research_recommendation, {
            "case_id": case_id, "objective_id": objective_id, "project_id": project_id,
            "durable_job_id": durable_job_id, "kind": kind, "reason": reason,
            "source_ids": source_ids, "contradictory_evidence": contradictory_evidence,
            "uncertainties": uncertainties, "missing_evidence": missing_evidence,
            "confidence": confidence, "next_action": next_action,
        })

    @mcp.tool(name="nexus_continue_research_case", description=(
        "Continue one exact existing Research case through the canonical Research Case Engine. "
        "Requires case_id, objective_id, project_id, and a durable job_id whose work item is "
        "already linked to that exact case/project/objective. Runs one bounded normal case turn "
        "under the existing provider governor; it cannot create or replace objectives, projects, "
        "cases, or jobs, and cannot publish or spend money."
    ))
    def nexus_continue_research_case(case_id: str, objective_id: str, project_id: str,
                                     durable_job_id: str) -> dict[str, Any]:
        return _action_call("nexus_continue_research_case", _continue_research_case, {
            "case_id": case_id, "objective_id": objective_id,
            "project_id": project_id, "durable_job_id": durable_job_id,
        })

    @mcp.tool(name="nexus_get_research_controller_status", description=(
        "READ ONLY exact Research Room controller status for an existing production Research case. "
        "Requires objective_id, project_id, case_id, and durable_job_id; creates no room/case/job and mutates no state."))
    def nexus_get_research_controller_status(case_id: str, objective_id: str, project_id: str,
                                              durable_job_id: str) -> dict[str, Any]:
        return _research_controller_read("status", case_id, objective_id, project_id, durable_job_id)

    @mcp.tool(name="nexus_get_research_controller_open_questions", description=(
        "READ ONLY exact open Research questions from the production case bound to Research Room; "
        "requires all four exact lineage IDs and creates or mutates nothing."))
    def nexus_get_research_controller_open_questions(case_id: str, objective_id: str, project_id: str,
                                                      durable_job_id: str) -> dict[str, Any]:
        return _research_controller_read("open_questions", case_id, objective_id, project_id, durable_job_id)

    @mcp.tool(name="nexus_get_research_controller_results", description=(
        "READ ONLY exact production-case evidence, answers, synthesis, recommendations, and Advisor results; "
        "requires all four exact lineage IDs and creates or mutates nothing."))
    def nexus_get_research_controller_results(case_id: str, objective_id: str, project_id: str,
                                               durable_job_id: str) -> dict[str, Any]:
        return _research_controller_read("results", case_id, objective_id, project_id, durable_job_id)

    @mcp.tool(name="nexus_research_controller_continue", description=(
        "GOVERNED bounded Research Room continuation on one exact existing production case. "
        "Requires objective_id, project_id, case_id, durable_job_id, and instruction. Executes one bounded Room participant turn, "
        "writes any supported evidence through the existing Research Case Engine, and stores controller state on that same case. "
        "Never creates a case/objective/project/job; no external consequential action; Advisor uses the existing ChatGPT plan connector."))
    def nexus_research_controller_continue(case_id: str, objective_id: str, project_id: str,
            durable_job_id: str, instruction: str) -> dict[str, Any]:
        return _action_call("nexus_research_controller_continue", _research_controller_continue, {
            "case_id": case_id, "objective_id": objective_id, "project_id": project_id,
            "durable_job_id": durable_job_id, "instruction": instruction})

    @mcp.tool(name="nexus_research_controller_advisor_request", description=(
        "GOVERNED bounded Advisor/Challenger request for one exact existing production Research case. "
        "Persists the usable response as a review record on that same case; creates no case/objective/project/job. "
        "Only PRIMARY_ADVISOR, CHALLENGER, or SECOND_OPINION roles are accepted; the existing ChatGPT plan connector is used."))
    def nexus_research_controller_advisor_request(case_id: str, objective_id: str, project_id: str,
            durable_job_id: str, question: str,
            review_role: Literal["PRIMARY_ADVISOR", "CHALLENGER", "SECOND_OPINION"] = "PRIMARY_ADVISOR") -> dict[str, Any]:
        return _action_call("nexus_research_controller_advisor_request", _research_controller_advisor_request, {
            "case_id": case_id, "objective_id": objective_id, "project_id": project_id,
            "durable_job_id": durable_job_id, "question": question, "review_role": review_role})

    @mcp.tool(name="nexus_assign_department_query", description="Queue one read-only Research or Systems query as a durable department job. Only Research or Systems intent is accepted; no owner objective, campaign, publication, spending authorization, or external action is created.")
    def nexus_assign_department_query(department: Literal["RESEARCH", "SYSTEMS", "ALPHA"], question: str,
                                     parent_request_id: str = "") -> dict[str, Any]:
        return _action_call("nexus_assign_department_query", _assign_department_query, {
            "department": department, "question": question, "parent_request_id": parent_request_id,
        })

    @mcp.tool(name="nexus_assign_creative_asset", description="Queue one disposable internal Creative asset through the existing Creative worker. No publishing, campaign launch, external posting, or spend is authorized.")
    def nexus_assign_creative_asset(task: str, parent_request_id: str = "") -> dict[str, Any]:
        return _action_call("nexus_assign_creative_asset", _assign_creative_asset, locals())

    @mcp.tool(name="nexus_assign_bounded_coding_task", description="Queue one bounded OpenCode task in an isolated temporary worktree. The worker may create and run files only in its temporary task workspace; it cannot modify production, commit, push, deploy, or spend.")
    def nexus_assign_bounded_coding_task(task: str, parent_request_id: str = "") -> dict[str, Any]:
        return _action_call("nexus_assign_bounded_coding_task", _assign_bounded_coding_task, locals())

    @mcp.tool(name="nexus_assign_notebooklm_runtime_canary", description="Queue one bounded Research-owned NotebookLM runtime canary: create a small notebook, import one public MCP documentation source, ask one source-scoped question, and verify the visible turn. No business research, owner objective, spend, or external action is created.")
    def nexus_assign_notebooklm_runtime_canary(parent_request_id: str = "") -> dict[str, Any]:
        return _action_call("nexus_assign_notebooklm_runtime_canary", _assign_notebooklm_runtime_canary, {
            "parent_request_id": parent_request_id,
        })

    @mcp.tool(name="nexus_assign_codex", description="Create one bounded internal Nova-to-existing-Codex assignment for a low-risk software defect. Requires scope, tests, prohibited actions, and parent objective. Does not authorize publication, spend, credentials, security weakening, or destructive production changes.")
    def nexus_assign_codex(parent_objective_id: str, blocking_work_id: str, defect_id: str,
                           defect_summary: str, affected_component: str,
                           acceptance_criteria: list[str], test_requirements: list[str],
                           allowed_scope: list[str], prohibited_actions: list[str],
                           risk_class: str = "LOW") -> dict[str, Any]:
        return _action_call("nexus_assign_codex", _assign_codex, locals())

    @mcp.tool(name="nexus_resume_research", description="Resume the same parent Research objective after a completed bounded Codex repair. Idempotently creates one existing-queue ASSIGNED checkpoint; never creates a replacement objective or publishes externally.")
    def nexus_resume_research() -> dict[str, Any]:
        return _action_call("nexus_resume_research", _resume_research, {})


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
    """Expose the canonical Google adapter and bounded writes via Nexus MCP."""
    @mcp.tool(name="google_get_authority", description="READ ONLY: inspect granted canonical Google OAuth scope names and service implications without returning credentials.")
    def google_get_authority() -> dict[str, Any]:
        authorize_read("google_get_authority")
        from services.google_mcp import server as google_server
        return google_server.google_get_authority()

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

    @mcp.tool(name="gmail_create_draft", description="GOVERNED Gmail write through the canonical Google credential. Creates an unsent draft to the authenticated owner only; never sends email. Requires gmail.modify scope.")
    def gmail_create_draft(subject: str, body: str, to_self: bool = True) -> dict[str, Any]:
        authorize_action("gmail_create_draft")
        from services.google_mcp import server as google_server
        return google_server.gmail_create_draft(subject, body, to_self)

    @mcp.tool(name="gmail_modify_message", description="GOVERNED Gmail organization only: archive or mark read/unread. No send, forward, delete, or external communication. Requires gmail.modify scope.")
    def gmail_modify_message(message_id: str, operation: str) -> dict[str, Any]:
        authorize_action("gmail_modify_message")
        from services.google_mcp import server as google_server
        return google_server.gmail_modify_message(message_id, operation)

    @mcp.tool(name="calendar_create_private_event", description="GOVERNED Calendar write: create one private event, without guests or external invitations, in the primary calendar.")
    def calendar_create_private_event(title: str, start_time: str, end_time: str,
                                      description: str = "", location: str = "") -> dict[str, Any]:
        authorize_action("calendar_create_private_event")
        from services.google_mcp import server as google_server
        return google_server.calendar_create_private_event(title, start_time, end_time, description, location)

    @mcp.tool(name="calendar_update_event", description="GOVERNED Calendar write: update fields on one exact event. Does not add guests or delete events.")
    def calendar_update_event(event_id: str, title: str | None = None, description: str | None = None,
                              location: str | None = None, start_time: str | None = None,
                              end_time: str | None = None) -> dict[str, Any]:
        authorize_action("calendar_update_event")
        from services.google_mcp import server as google_server
        return google_server.calendar_update_event(event_id, title, description, location, start_time, end_time)

    @mcp.tool(name="drive_create_nexus_file", description="GOVERNED Drive write: create a Nexus-owned text artifact inside NEXUS_GOOGLE_DRIVE_FOLDER_ID. Limited to drive.file and no sharing/deletion.")
    def drive_create_nexus_file(name: str, content: str, mime_type: str = "text/plain") -> dict[str, Any]:
        authorize_action("drive_create_nexus_file")
        from services.google_mcp import server as google_server
        return google_server.drive_create_nexus_file(name, content, mime_type)


def _register_systems_tools() -> None:
    """Expose only typed Systems operations through the existing governed MCP."""
    from .systems_bridge import request as systems_request
    from .gateway_receipts import record as record_gateway_receipt
    from .auth import authorize_action, authorize_read

    def call(tool_name: str, operation: str, **kwargs: Any) -> dict[str, Any]:
        # Give every Systems MCP operation the common gateway identifiers. A
        # caller may supply the root IDs; otherwise the gateway creates a
        # request/correlation pair for direct Hermes tool invocations.
        gateway_request_id = kwargs.pop("gateway_request_id", None) or ("nova-gateway-" + uuid.uuid4().hex)
        correlation_id = kwargs.pop("correlation_id", None) or gateway_request_id
        started_at = datetime.now(timezone.utc).isoformat()
        if operation in {"systems.restart_safe", "systems.rollback", "systems.technology_handoff", "systems.upgrade_component", "systems.safe_cleanup", "systems.rotate_credential", "systems.prepare_kaggle_job", "systems.approval_request", "systems.approval_decide"}:
            authorize_action(tool_name)
            authorization = "APPROVAL_REQUIRED" if operation in {"systems.restart_safe", "systems.rollback", "systems.rotate_credential", "systems.approval_decide"} else "SAFE_ACTION"
        else:
            authorize_read(tool_name)
            authorization = "READ_ONLY"
        result = systems_request(operation, gateway_request_id=gateway_request_id,
                                 correlation_id=correlation_id, **kwargs)
        receipt = record_gateway_receipt(
            request_id=gateway_request_id, correlation_id=correlation_id,
            engine="SYSTEMS_S1", operation=operation, authorization=authorization,
            result=result, started_at=started_at,
        )
        result["engine_receipt_id"] = result.get("receipt_id")
        result["receipt_id"] = receipt["receipt_id"]
        result["gateway_receipt"] = receipt
        result["status"] = result.get("status") or "COMPLETED"
        return result

    @mcp.tool(name="nexus_systems_health", description="Read current deterministic Nexus Systems health across registered environments. No repair or restart is performed.")
    def nexus_systems_health(include_oracle: bool = True, gateway_request_id: str = "", correlation_id: str = "") -> dict[str, Any]:
        return call("nexus_systems_health", "systems.health", gateway_request_id=gateway_request_id or None, correlation_id=correlation_id or None, payload={"include_oracle": bool(include_oracle)})

    @mcp.tool(name="nexus_systems_status", description="Read bounded current Systems service and incident status. Read only.")
    def nexus_systems_status(gateway_request_id: str = "", correlation_id: str = "") -> dict[str, Any]:
        return call("nexus_systems_status", "systems.status", gateway_request_id=gateway_request_id or None, correlation_id=correlation_id or None)

    @mcp.tool(name="nexus_systems_incidents", description="List bounded Systems incidents. Read only; does not diagnose or repair.")
    def nexus_systems_incidents(status: str = "", limit: int = 30, gateway_request_id: str = "", correlation_id: str = "") -> dict[str, Any]:
        return call("nexus_systems_incidents", "systems.incidents", gateway_request_id=gateway_request_id or None, correlation_id=correlation_id or None, payload={"status": status or None, "limit": max(1, min(int(limit), 100))})

    @mcp.tool(name="nexus_systems_incident", description="Read one exact Systems incident by ID. Read only.")
    def nexus_systems_incident(incident_id: str, gateway_request_id: str = "", correlation_id: str = "") -> dict[str, Any]:
        if not incident_id or len(incident_id) > 80:
            raise ValueError("SYSTEMS_INCIDENT_ID_INVALID")
        return call("nexus_systems_incident", "systems.incident", gateway_request_id=gateway_request_id or None, correlation_id=correlation_id or None, payload={"incident_id": incident_id})

    @mcp.tool(name="nexus_systems_version_status", description="Read active and rollback release records. Read only.")
    def nexus_systems_version_status(release_id: str = "", gateway_request_id: str = "", correlation_id: str = "") -> dict[str, Any]:
        return call("nexus_systems_version_status", "systems.version_status", gateway_request_id=gateway_request_id or None, correlation_id=correlation_id or None, payload={"id": release_id or None, "limit": 100})

    @mcp.tool(name="nexus_systems_environment_status", description="Read registered environments and their observed status. Read only.")
    def nexus_systems_environment_status(environment_id: str = "", gateway_request_id: str = "", correlation_id: str = "") -> dict[str, Any]:
        return call("nexus_systems_environment_status", "systems.environment_status", gateway_request_id=gateway_request_id or None, correlation_id=correlation_id or None, payload={"id": environment_id or None, "limit": 100})

    @mcp.tool(name="nexus_systems_technology_status", description="Read technology lifecycle records from the Systems registry. Read only.")
    def nexus_systems_technology_status(technology_id: str = "", gateway_request_id: str = "", correlation_id: str = "") -> dict[str, Any]:
        return call("nexus_systems_technology_status", "systems.technology_status", gateway_request_id=gateway_request_id or None, correlation_id=correlation_id or None, payload={"id": technology_id or None, "limit": 100})

    @mcp.tool(name="nexus_systems_service_status", description="Read registered service status. Read only.")
    def nexus_systems_service_status(service_id: str = "", gateway_request_id: str = "", correlation_id: str = "") -> dict[str, Any]:
        return call("nexus_systems_service_status", "systems.service_status", gateway_request_id=gateway_request_id or None, correlation_id=correlation_id or None, payload={"id": service_id or None})

    @mcp.tool(name="nexus_systems_release_status", description="Read registered release status. Read only.")
    def nexus_systems_release_status(release_id: str = "", gateway_request_id: str = "", correlation_id: str = "") -> dict[str, Any]:
        return call("nexus_systems_release_status", "systems.release_status", gateway_request_id=gateway_request_id or None, correlation_id=correlation_id or None, payload={"id": release_id or None})

    @mcp.tool(name="nexus_systems_receipt", description="Read bounded Systems receipts. Read only.")
    def nexus_systems_receipt(gateway_request_id: str = "", correlation_id: str = "") -> dict[str, Any]:
        return call("nexus_systems_receipt", "systems.receipt", gateway_request_id=gateway_request_id or None, correlation_id=correlation_id or None)

    @mcp.tool(name="nexus_systems_restart_safe", description="Request the fixed Systems safe-restart operation. Production targets remain held for approval; no arbitrary command is accepted.")
    def nexus_systems_restart_safe(environment_id: str, service_id: str, idempotency_key: str, reason: str, gateway_request_id: str = "", correlation_id: str = "") -> dict[str, Any]:
        return call("nexus_systems_restart_safe", "systems.restart_safe", environment_id=environment_id,
                               service_id=service_id, idempotency_key=idempotency_key, reason=reason, gateway_request_id=gateway_request_id or None, correlation_id=correlation_id or None)

    @mcp.tool(name="nexus_systems_rollback", description="Request the fixed Systems certified-rollback operation. Production targets remain held for approval; no path or command is accepted.")
    def nexus_systems_rollback(environment_id: str, service_id: str, idempotency_key: str, reason: str, gateway_request_id: str = "", correlation_id: str = "") -> dict[str, Any]:
        return call("nexus_systems_rollback", "systems.rollback", environment_id=environment_id,
                               service_id=service_id, idempotency_key=idempotency_key, reason=reason, gateway_request_id=gateway_request_id or None, correlation_id=correlation_id or None)

    @mcp.tool(name="nexus_systems_workload_placement", description="Read-only placement evaluation against verified environment capabilities and resource limits. Does not create infrastructure or start workloads.")
    def nexus_systems_workload_placement(workload: str, required_capabilities: list[str] | None = None,
                                         minimum_ram_gib: float = 0, requires_gpu: bool = False,
                                         trust_requirement: str = "", gateway_request_id: str = "",
                                         correlation_id: str = "") -> dict[str, Any]:
        payload = {"workload": workload, "required_capabilities": required_capabilities or [],
                   "minimum_ram_gib": minimum_ram_gib, "requires_gpu": requires_gpu,
                   "trust_requirement": trust_requirement}
        return call("nexus_systems_workload_placement", "systems.workload_placement", gateway_request_id=gateway_request_id or None, correlation_id=correlation_id or None, payload=payload)

    @mcp.tool(name="nexus_systems_technology_handoff", description="Record one typed Research TECHNOLOGY_EVALUATION for Systems review. Candidate is marked RECEIVED_NOT_EXECUTED; no sandbox, installation, or production change is performed.")
    def nexus_systems_technology_handoff(directive_id: str, technology: str, problem_addressed: str,
                                         current_capability: str, potential_improvement: str,
                                         evidence_refs: list[str], recommended_test: str,
                                         risk_flags: list[str], approval_requirements: list[str],
                                         source_job: str, gateway_request_id: str = "",
                                         correlation_id: str = "") -> dict[str, Any]:
        payload = {"directive_id": directive_id, "technology": technology,
                   "problem_addressed": problem_addressed, "current_capability": current_capability,
                   "potential_improvement": potential_improvement, "evidence_refs": evidence_refs,
                   "recommended_test": recommended_test, "risk_flags": risk_flags,
                   "approval_requirements": approval_requirements, "source_job": source_job}
        return call("nexus_systems_technology_handoff", "systems.technology_handoff",
                    environment_id="MAC_MINI", idempotency_key=directive_id,
                    reason="Ingest typed Research technology evaluation; no execution", payload=payload,
                    gateway_request_id=gateway_request_id or None, correlation_id=correlation_id or None)

    @mcp.tool(name="nexus_systems_approval_request", description="Create a durable pending Systems approval request bound to one allowlisted operation, component, environment, and exact scope. Creates no mutation and does not approve it.")
    def nexus_systems_approval_request(operation: str, target_component: str, target_environment: str,
                                       target_scope: str, reason_or_summary: str,
                                       gateway_request_id: str = "", correlation_id: str = "") -> dict[str, Any]:
        payload = {"operation": operation, "target_component": target_component,
                   "target_environment": target_environment, "target_scope": target_scope,
                   "requested_by": "ray_via_nova", "reason_or_summary": reason_or_summary}
        return call("nexus_systems_approval_request", "systems.approval_request",
                    environment_id=target_environment, reason=reason_or_summary,
                    payload=payload, gateway_request_id=gateway_request_id or None,
                    correlation_id=correlation_id or None)

    @mcp.tool(name="nexus_systems_approval_decide", description="Approve or deny one exact pending Systems approval only after Ray explicitly directs that decision in the current authenticated operator conversation. Never infer or self-approve.")
    def nexus_systems_approval_decide(approval_reference: str, decision: str,
                                     gateway_request_id: str = "", correlation_id: str = "") -> dict[str, Any]:
        if decision not in {"APPROVE", "DENY"}:
            raise ValueError("APPROVAL_DECISION_INVALID")
        return call("nexus_systems_approval_decide", "systems.approval_decide",
                    environment_id="MAC_MINI", reason="Explicit Ray decision through authenticated Nova operator path",
                    approval_context={"ray_explicit_decision": True},
                    payload={"approval_reference": approval_reference, "decision": decision},
                    gateway_request_id=gateway_request_id or None,
                    correlation_id=correlation_id or None)

    @mcp.tool(name="nexus_systems_approval_status", description="Read one exact Systems approval reference, including its binding and state. No decision or mutation is performed.")
    def nexus_systems_approval_status(approval_reference: str, gateway_request_id: str = "",
                                      correlation_id: str = "") -> dict[str, Any]:
        return call("nexus_systems_approval_status", "systems.approval_status",
                    environment_id="MAC_MINI", payload={"approval_reference": approval_reference},
                    gateway_request_id=gateway_request_id or None,
                    correlation_id=correlation_id or None)

    @mcp.tool(name="nexus_systems_approval_validate", description="Validate that one approved Systems reference matches the exact operation, target component, environment, and scope. Validation is read-only and single-use references remain unconsumed.")
    def nexus_systems_approval_validate(approval_reference: str, operation: str,
                                        target_component: str, target_environment: str,
                                        target_scope: str, gateway_request_id: str = "",
                                        correlation_id: str = "") -> dict[str, Any]:
        return call("nexus_systems_approval_validate", "systems.approval_validate",
                    environment_id=target_environment,
                    payload={"approval_reference": approval_reference, "operation": operation,
                             "target_component": target_component, "target_environment": target_environment,
                             "target_scope": target_scope},
                    gateway_request_id=gateway_request_id or None,
                    correlation_id=correlation_id or None)


def _register_r10_tools() -> None:
    from .research_r10_bridge import register
    register(mcp)


def _register_engine_bridge_tools() -> None:
    """Expose one generic engine operation family; no engine-specific Nova routing."""
    bridge_release = Path(os.environ.get(
        "NEXUS_ENGINE_BRIDGE_RELEASE",
        str(Path.home() / ".nexus/releases/nexus-engine-bridge-r1-20261029-candidate-v4"),
    )).expanduser().resolve()
    if str(bridge_release) not in sys.path:
        sys.path.insert(0, str(bridge_release))
    from engine_bridge.mcp_tools import register
    from .auth import authorize_action, authorize_read
    register(mcp, authorize_read=authorize_read, authorize_action=authorize_action)


_register()
_register_google_read_tools()
_register_systems_tools()
_register_r10_tools()
_register_engine_bridge_tools()

from .systems_operator import register_systems_operator_tools
register_systems_operator_tools(mcp)

from .opportunities_operator import register_opportunities_tools
register_opportunities_tools(mcp)

from .github_remote_operator import GITHUB_REMOTE_TOOL_NAMES, register_github_remote_tools  # noqa: E402

register_github_remote_tools(mcp)


if __name__ == "__main__":
    mcp.run(transport="stdio")


# NOVA_OBJECTIVE_INTAKE_AND_NATIVE_ROUTING_REPAIR_R1: advertise a SEP-2549 cache TTL on
# tools/list. Hermes caches MCP tool schemas on disk and, without a TTL, serves a stale
# manifest forever, so newly added Nexus tools never reach Nova. With ttlMs, Hermes
# re-probes the live server once the entry is older than the TTL.
TOOLS_LIST_TTL_MS = int(os.getenv("NEXUS_MCP_TOOLS_LIST_TTL_MS") or 300000)


def _advertise_tools_list_ttl(ttl_ms: int = TOOLS_LIST_TTL_MS) -> None:
    import mcp.types as _types
    handlers = mcp._mcp_server.request_handlers
    original = handlers.get(_types.ListToolsRequest)
    if original is None or getattr(original, "_nexus_ttl", False):
        return

    async def _list_tools_with_ttl(request):
        result = await original(request)
        root = getattr(result, "root", result)
        if isinstance(root, _types.ListToolsResult) and getattr(root, "ttlMs", None) is None:
            stamped = _types.ListToolsResult(**root.model_dump(by_alias=True, exclude_none=True), ttlMs=ttl_ms)
            return _types.ServerResult(stamped) if hasattr(result, "root") else stamped
        return result

    _list_tools_with_ttl._nexus_ttl = True
    handlers[_types.ListToolsRequest] = _list_tools_with_ttl


_advertise_tools_list_ttl()
