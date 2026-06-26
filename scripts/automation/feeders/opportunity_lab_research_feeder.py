"""Opportunity Lab feeder from already-enriched research_sources.

No capture, no scraping, no external AI, no publish/send/trade/deploy. Creates bounded safe
task_requests from public/internal-summary enrichment only.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

FEEDER_ID = "opportunity_lab_research_feeder"
TASK_TYPE = "opportunity_lab_project"
MAX_LIVE_LIMIT = 10

INCLUDE_TERMS = (
    "funding", "credit", "monetization", "business", "grant", "grants", "marketing",
    "sales", "seo", "ai_tooling", "automation", "creative", "design", "lead",
    "client", "acquisition", "goclear", "apex", "affiliate", "opportunity",
)
HIGH_RISK_TRIGGERS = {
    "sensitive_data", "external_ai_sensitive_text", "broad_scrape", "publish_send_trade_deploy",
    "scheduler_or_local_command", "raw_v1_worker", "client_facing", "high_compliance_risk",
    "risky_destination",
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


def meta(row: dict[str, Any]) -> dict[str, Any]:
    return row.get("metadata") if isinstance(row.get("metadata"), dict) else {}


def enrichment(row: dict[str, Any]) -> dict[str, Any]:
    return meta(row).get("project_enrichment") if isinstance(meta(row).get("project_enrichment"), dict) else {}


def score_of(e: dict[str, Any]) -> int | None:
    raw = e.get("score")
    return int(raw) if isinstance(raw, (int, float)) else None


def public_safe(row: dict[str, Any], e: dict[str, Any]) -> bool:
    m = meta(row)
    if m.get("sensitive") or m.get("customer_private") or m.get("private_customer_data"):
        return False
    forbidden_blob = " ".join([
        text(m.get("sensitivity")),
        text(m.get("data_scope")),
        text(e.get("sensitivity")),
    ]).lower()
    return not any(term in forbidden_blob for term in ("customer_private", "credit_sensitive", "funding_sensitive", "auth_sensitive", "secrets"))


def include_by_terms(row: dict[str, Any], e: dict[str, Any]) -> bool:
    blob = " ".join([
        text(e.get("destination")),
        text(e.get("category")),
        text(row.get("title")),
        " ".join(arr(meta(row).get("secondary_tags") or meta(row).get("tags"))),
    ]).lower()
    return "opportunity lab" in blob or "goclear/apex" in blob or any(term in blob for term in INCLUDE_TERMS)


def skip_reason(row: dict[str, Any], e: dict[str, Any]) -> str | None:
    if not e:
        return "missing_project_enrichment"
    status_blob = " ".join([text(meta(row).get("review_status")), text(e.get("enrichment_status"))]).lower()
    if "reject" in status_blob or "park" in status_blob:
        return "rejected_or_parked"
    if not public_safe(row, e):
        return "sensitive_or_private"
    risks = set(arr(e.get("risk_triggers")))
    high = sorted(risks & HIGH_RISK_TRIGGERS)
    if high:
        return f"high_risk:{','.join(high)}"
    score = score_of(e)
    if score is None:
        return "missing_score"
    if score < 20 and not e.get("approval_required"):
        return "score_below_threshold"
    if not text(e.get("recommendation")):
        return "missing_recommendation"
    if not include_by_terms(row, e):
        return "not_monetization_candidate"
    return None


def duplicate_task(sb, source_id: str) -> dict[str, Any] | None:
    query = (
        f"select=id,status,payload&task_type=eq.{sb.q(TASK_TYPE)}"
        f"&payload->>feeder_id=eq.{sb.q(FEEDER_ID)}"
        f"&payload->>related_research_source_id=eq.{sb.q(source_id)}"
        "&limit=1"
    )
    st, rows = sb.get("task_requests", query)
    return rows[0] if isinstance(rows, list) and rows else None


def fetch_sources(sb, limit: int) -> list[dict[str, Any]]:
    # Read extra rows so skipped rows do not starve a bounded run.
    st, rows = sb.get("research_sources", f"select=*&order=created_at.desc&limit={max(limit * 5, limit)}")
    return rows if isinstance(rows, list) else []


def build_payload(row: dict[str, Any], e: dict[str, Any]) -> dict[str, Any]:
    risks = arr(e.get("risk_triggers"))
    approval_required = bool(e.get("approval_required"))
    status = "needs_review" if approval_required else "proposed"
    title = f"Opportunity review: {text(row.get('title') or row.get('url'), 'Research source')}"[:140]
    return {
        "task_type": TASK_TYPE,
        "requested_by": FEEDER_ID,
        "sensitivity": "internal_summary",
        "allowed_data_scope": ["public", "internal_summary"],
        "forbidden_data": ["customer_private", "credit_sensitive", "funding_sensitive", "auth_sensitive", "secrets"],
        "assigned_worker_type": "opportunity_research_worker",
        "hermes_visibility": "summary",
        "status": status,
        "payload": {
            "feeder_id": FEEDER_ID,
            "title": title,
            "department": "opportunity_lab",
            "owner_tab": "opportunities",
            "project_type": "monetization_opportunity",
            "related_research_source_id": row.get("id"),
            "source_url": row.get("url"),
            "source_title": row.get("title"),
            "summary": text(e.get("summary") or row.get("snippet")),
            "pros": arr(e.get("pros")),
            "cons": arr(e.get("cons")),
            "recommendation": text(e.get("recommendation")),
            "proposed_schedule": text(e.get("proposed_schedule"), "Review this week; choose smallest safe test after Ray review."),
            "next_action": text(e.get("next_action"), "Review in Opportunity Lab and decide whether to create a smallest-test task."),
            "score": score_of(e),
            "risk_triggers": risks,
            "approval_required": approval_required,
            "project_enrichment": {
                **e,
                "destination": "Opportunity Lab",
                "proof_event_id": e.get("proof_event_id"),
            },
            "source": FEEDER_ID,
            "created_from": "research_sources",
        },
        "summary": text(e.get("summary") or row.get("snippet") or title)[:500],
        "result_summary": text(e.get("recommendation"), "Opportunity Lab review proposed.")[:500],
        "title": title,
    }


def create_task_request(sb, payload: dict[str, Any]) -> str | None:
    row = {k: payload[k] for k in (
        "task_type", "requested_by", "sensitivity", "allowed_data_scope", "forbidden_data",
        "assigned_worker_type", "hermes_visibility", "status", "payload", "result_summary",
    )}
    st, rows = sb.insert("task_requests", row)
    return rows[0]["id"] if isinstance(rows, list) and rows else None


def create_event(sb, source: dict[str, Any], task_id: str | None, payload: dict[str, Any]) -> str | None:
    e = payload["payload"]["project_enrichment"]
    st, rows = sb.insert("nexus_events", {
        "lane": "monetization",
        "source": FEEDER_ID,
        "action": "opportunity_lab_project_created",
        "status": "pending",
        "title": payload["title"][:80],
        "summary": f"score {payload['payload'].get('score')} · {text(e.get('recommendation'))[:160]}",
        "payload": {
            "event_type": "opportunity_lab_project_created",
            "feeder_id": FEEDER_ID,
            "research_source_id": source.get("id"),
            "task_request_id": task_id,
            "score": payload["payload"].get("score"),
            "recommendation": e.get("recommendation"),
        },
    })
    return rows[0]["id"] if isinstance(rows, list) and rows else None


def attach_event_to_task(sb, task_id: str, payload: dict[str, Any], event_id: str | None) -> None:
    if not event_id:
        return
    next_payload = dict(payload["payload"])
    next_payload["proof_event_id"] = event_id
    project_enrichment = dict(next_payload.get("project_enrichment") or {})
    project_enrichment["proof_event_id"] = event_id
    next_payload["project_enrichment"] = project_enrichment
    sb.update("task_requests", f"id=eq.{sb.q(task_id)}", {"payload": next_payload})


def run(sb, *, dry_run: bool, limit: int) -> dict[str, Any]:
    limit = max(1, min(limit, MAX_LIVE_LIMIT))
    sources = fetch_sources(sb, limit)
    results: list[dict[str, Any]] = []
    counts = {"scanned": len(sources), "eligible": 0, "created": 0, "duplicates": 0, "skipped": 0, "failed": 0}

    for row in sources:
        if counts["eligible"] >= limit:
            break
        e = enrichment(row)
        reason = skip_reason(row, e)
        if reason:
            counts["skipped"] += 1
            results.append({"source_id": row.get("id"), "title": row.get("title"), "status": "skipped", "reason": reason})
            continue
        dup = duplicate_task(sb, row["id"])
        if dup:
            counts["duplicates"] += 1
            results.append({"source_id": row.get("id"), "title": row.get("title"), "status": "duplicate", "task_request_id": dup.get("id")})
            continue

        payload = build_payload(row, e)
        counts["eligible"] += 1
        proposed = {
            "source_id": row.get("id"),
            "title": payload["title"],
            "source_url": row.get("url"),
            "score": payload["payload"].get("score"),
            "recommendation": payload["payload"].get("recommendation"),
            "proposed_schedule": payload["payload"].get("proposed_schedule"),
            "approval_required": payload["payload"].get("approval_required"),
        }
        if dry_run:
            results.append({**proposed, "status": "would_create"})
            continue

        task_id = create_task_request(sb, payload)
        if not task_id:
            counts["failed"] += 1
            results.append({**proposed, "status": "failed_create_task_request"})
            continue
        event_id = create_event(sb, row, task_id, payload)
        attach_event_to_task(sb, task_id, payload, event_id)
        counts["created"] += 1
        results.append({**proposed, "status": "created", "task_request_id": task_id, "proof_event_id": event_id})

    return {
        "feeder_id": FEEDER_ID,
        "dry_run": dry_run,
        "limit": limit,
        **counts,
        "results": results[: max(limit, 20)],
        "target_tables": ["task_requests", "nexus_events"],
        "proof_event_type": "opportunity_lab_project_created",
    }
