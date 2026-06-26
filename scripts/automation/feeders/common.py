"""Shared deterministic department feeder helpers.

These helpers only create internal task_requests and nexus_events proof rows. They do not
call external services, run jobs, scrape, publish, send, trade, deploy, or start schedulers.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

MAX_LIVE_LIMIT = 10
ROOT = Path(__file__).resolve().parent.parent.parent.parent

FORBIDDEN_DATA = ["customer_private", "credit_sensitive", "funding_sensitive", "auth_sensitive", "secrets"]
HIGH_RISK_TRIGGERS = {
    "sensitive_data", "external_ai_sensitive_text", "broad_scrape", "publish_send_trade_deploy",
    "scheduler_or_local_command", "raw_v1_worker", "client_facing", "high_compliance_risk",
    "risky_destination", "trade_execution",
}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def text(value: Any, fallback: str = "") -> str:
    if value is None:
        return fallback
    if isinstance(value, str):
        return value or fallback
    if isinstance(value, (int, float, bool)):
        return str(value)
    return fallback


def arr(value: Any) -> list[str]:
    if isinstance(value, list):
        return [text(v) for v in value if text(v)]
    if isinstance(value, str) and value:
        return [value]
    return []


def obj(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def metadata(row: dict[str, Any]) -> dict[str, Any]:
    return obj(row.get("metadata") or row.get("payload") or row.get("input") or row.get("output"))


def project_enrichment(row: dict[str, Any]) -> dict[str, Any]:
    data = metadata(row)
    if isinstance(data.get("project_enrichment"), dict):
        return data["project_enrichment"]
    payload = obj(row.get("payload"))
    if isinstance(payload.get("project_enrichment"), dict):
        return payload["project_enrichment"]
    return {}


def score_value(*values: Any, fallback: int = 50) -> int:
    for value in values:
        if isinstance(value, (int, float)):
            return int(value)
        if isinstance(value, str) and value.strip().isdigit():
            return int(value.strip())
    return fallback


def safe_blob(*values: Any) -> str:
    return " ".join(text(v) for v in values if text(v)).lower()


def is_public_safe(row: dict[str, Any], enrichment: dict[str, Any] | None = None) -> bool:
    e = enrichment or {}
    data = metadata(row)
    if data.get("sensitive") or data.get("customer_private") or data.get("private_customer_data"):
        return False
    blob = safe_blob(
        data.get("sensitivity"), data.get("data_scope"), data.get("classification"),
        e.get("sensitivity"), row.get("sensitivity"),
    )
    return not any(term in blob for term in FORBIDDEN_DATA)


def high_risk_reason(risk_triggers: list[str]) -> str | None:
    high = sorted(set(risk_triggers) & HIGH_RISK_TRIGGERS)
    return f"high_risk:{','.join(high)}" if high else None


def table_rows(sb, table: str, query: str) -> list[dict[str, Any]]:
    _status, rows = sb.get(table, query)
    return rows if isinstance(rows, list) else []


def duplicate_task(sb, *, feeder_id: str, task_type: str, unique_key: str) -> dict[str, Any] | None:
    query = (
        f"select=id,status,payload&task_type=eq.{sb.q(task_type)}"
        f"&payload->>feeder_id=eq.{sb.q(feeder_id)}"
        f"&payload->>unique_key=eq.{sb.q(unique_key)}"
        "&limit=1"
    )
    rows = table_rows(sb, "task_requests", query)
    return rows[0] if rows else None


def create_task_request(sb, candidate: dict[str, Any]) -> str | None:
    row = {
        "task_type": candidate["task_type"],
        "requested_by": candidate["feeder_id"],
        "sensitivity": "internal_summary",
        "allowed_data_scope": ["public", "internal_summary"],
        "forbidden_data": FORBIDDEN_DATA,
        "assigned_worker_type": candidate.get("assigned_worker_type", "department_review_worker"),
        "hermes_visibility": "summary",
        "status": candidate.get("status", "proposed"),
        "payload": candidate["payload"],
        "result_summary": text(candidate.get("recommendation"), "Department review proposed.")[:500],
    }
    _status, rows = sb.insert("task_requests", row)
    return rows[0]["id"] if isinstance(rows, list) and rows else None


def create_event(sb, candidate: dict[str, Any], task_id: str | None) -> str | None:
    payload = candidate["payload"]
    _status, rows = sb.insert("nexus_events", {
        "lane": candidate.get("lane", payload.get("owner_tab", "automation")),
        "source": candidate["feeder_id"],
        "action": candidate["proof_event_type"],
        "status": "pending",
        "title": candidate["title"][:80],
        "summary": f"score {payload.get('score')} · {text(payload.get('recommendation'))[:160]}",
        "payload": {
            "event_type": candidate["proof_event_type"],
            "feeder_id": candidate["feeder_id"],
            "unique_key": payload.get("unique_key"),
            "source_kind": payload.get("source_kind"),
            "source_id": payload.get("source_id"),
            "task_request_id": task_id,
            "score": payload.get("score"),
            "recommendation": payload.get("recommendation"),
        },
    })
    return rows[0]["id"] if isinstance(rows, list) and rows else None


def attach_event_to_task(sb, task_id: str, candidate: dict[str, Any], event_id: str | None) -> None:
    if not event_id:
        return
    payload = dict(candidate["payload"])
    payload["proof_event_id"] = event_id
    enrichment = dict(payload.get("project_enrichment") or {})
    enrichment["proof_event_id"] = event_id
    payload["project_enrichment"] = enrichment
    sb.update("task_requests", f"id=eq.{sb.q(task_id)}", {"payload": payload})


def make_candidate(
    *,
    feeder_id: str,
    task_type: str,
    proof_event_type: str,
    department: str,
    owner_tab: str,
    project_type: str,
    unique_key: str,
    source_kind: str,
    title: str,
    summary: str,
    recommendation: str,
    proposed_schedule: str,
    next_action: str,
    score: int,
    source_id: str | None = None,
    source_url: str | None = None,
    source_title: str | None = None,
    visual_url: str | None = None,
    pros: list[str] | None = None,
    cons: list[str] | None = None,
    status: str = "proposed",
    approval_required: bool = False,
    risk_triggers: list[str] | None = None,
    data_sources: list[str] | None = None,
    metadata_extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    risks = risk_triggers or []
    payload = {
        "feeder_id": feeder_id,
        "unique_key": unique_key,
        "title": title[:140],
        "department": department,
        "owner_tab": owner_tab,
        "project_type": project_type,
        "source_kind": source_kind,
        "source_id": source_id,
        "source_url": source_url,
        "source_title": source_title or title,
        "visual_url": visual_url,
        "summary": summary,
        "pros": pros or [],
        "cons": cons or [],
        "recommendation": recommendation,
        "proposed_schedule": proposed_schedule,
        "next_action": next_action,
        "score": score,
        "risk_triggers": risks,
        "approval_required": approval_required,
        "data_sources": data_sources or [source_kind],
        "source": feeder_id,
        "project_enrichment": {
            "enrichment_status": "scored",
            "enrichment_source": "deterministic",
            "summary": summary,
            "score": score,
            "pros": pros or [],
            "cons": cons or [],
            "recommendation": recommendation,
            "proposed_schedule": proposed_schedule,
            "next_action": next_action,
            "risk_triggers": risks,
            "approval_required": approval_required,
            "category": project_type,
            "destination": department,
            "confidence": 0.68,
            "enriched_at": now(),
        },
        "metadata": metadata_extra or {},
    }
    return {
        "feeder_id": feeder_id,
        "task_type": task_type,
        "proof_event_type": proof_event_type,
        "lane": owner_tab,
        "title": title[:140],
        "summary": summary[:500],
        "recommendation": recommendation[:500],
        "status": "needs_review" if approval_required else status,
        "payload": payload,
        "assigned_worker_type": f"{owner_tab}_review_worker",
    }


def run_candidates(sb, *, feeder_id: str, task_type: str, proof_event_type: str,
                   dry_run: bool, limit: int, candidates: list[dict[str, Any]]) -> dict[str, Any]:
    limit = max(1, min(limit, MAX_LIVE_LIMIT))
    results: list[dict[str, Any]] = []
    counts = {"scanned": len(candidates), "eligible": 0, "created": 0, "duplicates": 0, "skipped": 0, "failed": 0}

    for candidate in candidates:
        if counts["eligible"] >= limit:
            break
        payload = candidate["payload"]
        reason = payload.get("skip_reason")
        if reason:
            counts["skipped"] += 1
            results.append({"unique_key": payload.get("unique_key"), "title": candidate["title"], "status": "skipped", "reason": reason})
            continue
        dup = duplicate_task(sb, feeder_id=feeder_id, task_type=task_type, unique_key=text(payload.get("unique_key")))
        if dup:
            counts["duplicates"] += 1
            results.append({"unique_key": payload.get("unique_key"), "title": candidate["title"], "status": "duplicate", "task_request_id": dup.get("id")})
            continue
        counts["eligible"] += 1
        proposed = {
            "unique_key": payload.get("unique_key"),
            "title": candidate["title"],
            "score": payload.get("score"),
            "recommendation": payload.get("recommendation"),
            "proposed_schedule": payload.get("proposed_schedule"),
            "approval_required": payload.get("approval_required"),
        }
        if dry_run:
            results.append({**proposed, "status": "would_create"})
            continue
        task_id = create_task_request(sb, candidate)
        if not task_id:
            counts["failed"] += 1
            results.append({**proposed, "status": "failed_create_task_request"})
            continue
        event_id = create_event(sb, candidate, task_id)
        attach_event_to_task(sb, task_id, candidate, event_id)
        counts["created"] += 1
        results.append({**proposed, "status": "created", "task_request_id": task_id, "proof_event_id": event_id})

    return {
        "feeder_id": feeder_id,
        "dry_run": dry_run,
        "limit": limit,
        **counts,
        "results": results[: max(limit, 20)],
        "target_tables": ["task_requests", "nexus_events"],
        "proof_event_type": proof_event_type,
    }
