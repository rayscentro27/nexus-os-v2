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

from .auth import authorize_action, authorize_read
from .registry import CAPABILITY_MAP, read_canonical
from .schemas import CAPABILITY_FRESHNESS, TOOL_NAMES, unavailable

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


def _get_prior_department_result(department: str, question: str = "") -> dict[str, Any]:
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
    }


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
    return {"status": "ok", "job_id": job_id, "event_count": len(events),
            "events": events, "read_only": True, "source": str(path.relative_to(ROOT))}


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
    scoped_research_intake = tool_name == "nexus_assign_research" and (
        not previous_egress_job or previous_egress_job.startswith("feeder-process-")
    )
    scoped_controller_action = tool_name in {
        "nexus_research_controller_continue", "nexus_research_controller_advisor_request"} and (
        not previous_egress_job or previous_egress_job.startswith("feeder-process-")
    )
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

    @mcp.tool(name="nexus_get_prior_department_result", description="Read the latest receipt-verified completed Research, Alpha, or Systems result from durable Nexus completion events. This never creates or re-runs work. For Alpha, include the linked Research objective evaluation when available.")
    def nexus_get_prior_department_result(department: Literal["RESEARCH", "ALPHA", "SYSTEMS"], question: str = "") -> dict[str, Any]:
        return _get_prior_department_result(department, question)

    @mcp.tool(name="nexus_get_durable_jobs", description="VOLATILE read of current production durable-job records. Supply job_id to retrieve one exact record. Returns safe job metadata and, for Research jobs, correlated work status/blocker/result summary; never creates or changes work.")
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
            "and workers. It cannot publish, spend, approve, or create a company cycle."
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


_register()
_register_google_read_tools()


if __name__ == "__main__":
    mcp.run(transport="stdio")
