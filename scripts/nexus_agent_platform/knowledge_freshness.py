"""Context-sensitive freshness and refresh receipts for canonical Alpha knowledge.

The Alpha content/claim collections remain the source of truth.  This module
adds only the policy and immutable refresh ledger needed to revalidate claims;
it never silently promotes a refreshed claim or treats missing timestamps as
fresh.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

from alpha.alpha_discovery import claim_record, content_record, persist_claim, persist_content
from nexus_agent_platform.governed.persistence import append_record, new_id, read_records

TTL_DAYS = {
    "SOFTWARE": 7,
    "MARKET": 2,
    "SEO": 3,
    "FUNDING": 7,
    "TRADING": 1,
    "GENERAL": 30,
    "HISTORICAL": 3650,
}


def _parse(value: Any) -> datetime | None:
    if not value or not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def _kind(record: dict[str, Any]) -> str:
    text = " ".join(str(record.get(k, "")) for k in ("category", "theme", "source_type", "content_type")).upper()
    for key in TTL_DAYS:
        if key in text:
            return key
    return "GENERAL"


def classify_freshness(record: dict[str, Any], *, as_of: datetime | None = None) -> dict[str, Any]:
    """Classify a record without coercing an unknown timestamp to zero age."""
    now = as_of or datetime.now(timezone.utc)
    observed = next((_parse(record.get(k)) for k in ("last_seen_at", "retrieved_at", "verified_at", "updated_at", "created_at") if _parse(record.get(k))), None)
    if observed is None:
        return {"status": "WAITING_SOURCE", "observed_at": None, "age_seconds": None, "ttl_days": TTL_DAYS[_kind(record)], "reason": "no trusted observation timestamp"}
    age = max(0.0, (now - observed).total_seconds())
    ttl = TTL_DAYS[_kind(record)] * 86400
    ratio = age / ttl if ttl else 1.0
    status = "FRESH" if ratio < 0.75 else "AGING" if ratio < 1.0 else "STALE"
    return {"status": status, "observed_at": observed.isoformat(), "age_seconds": round(age, 3), "ttl_days": TTL_DAYS[_kind(record)], "reason": f"{_kind(record)} policy"}


def refresh_due(record: dict[str, Any], *, as_of: datetime | None = None) -> bool:
    return classify_freshness(record, as_of=as_of)["status"] in {"STALE", "REFRESH_REQUIRED", "WAITING_SOURCE"}


def refresh_mission(record: dict[str, Any], *, as_of: datetime | None = None) -> dict[str, Any]:
    freshness = classify_freshness(record, as_of=as_of)
    source = record.get("canonical_url") or record.get("source_url")
    fingerprint = hashlib.sha256(json.dumps({"content_id": record.get("content_id"), "source": source, "status": freshness["status"]}, sort_keys=True).encode()).hexdigest()[:20]
    return {"refresh_id": f"refresh_{fingerprint}", "content_id": record.get("content_id"), "source": source,
            "status": "QUEUED", "freshness_before": freshness, "created_at": datetime.now(timezone.utc).isoformat()}


def refresh_once(record: dict[str, Any], retrieve: Callable[[str], dict[str, Any]], *, as_of: datetime | None = None) -> dict[str, Any]:
    mission = refresh_mission(record, as_of=as_of)
    prior = next((x for x in read_records("knowledge_refreshes") if x.get("refresh_id") == mission["refresh_id"] and x.get("status") == "COMPLETED"), None)
    if prior:
        return {"status": "DUPLICATE_SUPPRESSED", "mission": mission, "receipt": prior}
    result = retrieve(mission["source"])
    if not result.get("ok"):
        receipt = {**mission, "status": "WAITING_SOURCE", "error": result.get("error", "retrieval_failed"), "completed_at": datetime.now(timezone.utc).isoformat()}
        append_record("knowledge_refreshes", receipt)
        return {"status": "WAITING_SOURCE", "mission": mission, "receipt": receipt}
    refreshed = content_record(mission["source"], record.get("content_type", "web_page"), result.get("title", record.get("title", mission["source"])),
                               canonical_url=mission["source"], source_family=record.get("source_family"),
                               excerpt=result.get("excerpt", ""), content_hash=result.get("text_hash"),
                               retrieval_status="RETRIEVED", retrieved_at=result.get("retrieved_at"),
                               refreshed_from=record.get("content_id"), evidence_class="REFRESHED_SOURCE")
    stored_content = persist_content(refreshed)
    claim_text = result.get("excerpt", "")[:1200] or "Source was rechecked; no specific claim extracted."
    claim = claim_record(refreshed["content_id"], claim_text, "freshness_refresh", source_id=record.get("source_id"),
                         supporting_sources=[{"url": mission["source"], "retrieved_at": result.get("retrieved_at"), "source_family": record.get("source_family")}],
                         verification_status="UNVERIFIED", evidence_score=0.0)
    stored_claim = persist_claim(claim)
    receipt = {**mission, "status": "COMPLETED", "completed_at": datetime.now(timezone.utc).isoformat(),
               "freshness_after": classify_freshness(refreshed), "content_id": refreshed["content_id"],
               "claim_id": claim["claim_id"], "content_stored": stored_content["stored"], "claim_stored": stored_claim["stored"],
               "source_traceability": True, "alpha_evaluation_required": True}
    append_record("knowledge_refreshes", receipt)
    return {"status": "COMPLETED", "mission": mission, "receipt": receipt}
