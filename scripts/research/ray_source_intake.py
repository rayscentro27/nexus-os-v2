"""Ray-curated source intake over the canonical Alpha source registry.

This is an adapter, not a second source database.  It provides idempotent
ADD/LIST/STATUS/PAUSE/RESUME/priority/lane/backfill operations while keeping
claims subject to the existing Research and Alpha evidence path.
"""
from __future__ import annotations

import hashlib
import re
import urllib.parse
from datetime import datetime, timezone
from typing import Any

from nexus_agent_platform.governed import persistence

SOURCE_TYPES = {
    "YOUTUBE_CHANNEL", "YOUTUBE_VIDEO", "WEB_PAGE", "DIRECT_URL", "GITHUB_REPO",
    "FORUM_COMMUNITY", "NEWS", "ACADEMIC", "SEO_QUERY", "COMPETITOR",
    "FUNDING_SOURCE", "AFFILIATE_SOURCE", "BUSINESS_OPPORTUNITY_SOURCE",
    "TRADING_SOURCE", "BROKER_EVIDENCE", "MARKET_DATA_SOURCE",
}
LANES = {
    "AI_NEXUS", "SYSTEMS", "CREATIVE", "MARKETING", "SEO", "CREDIT", "FUNDING",
    "FINANCE", "BUSINESS_OPPORTUNITY", "TRADING", "GENERAL_BUSINESS",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _key(url: str) -> str:
    return hashlib.sha256(_canonical_url(url).encode()).hexdigest()[:24]

def _canonical_url(url: str) -> str:
    parsed=urllib.parse.urlsplit(url.strip())
    query=[(k,v) for k,v in urllib.parse.parse_qsl(parsed.query,keep_blank_values=True)
           if not (k.lower().startswith("utm_") or k.lower() in {"fbclid","gclid","ref","referrer"})]
    path=parsed.path.rstrip("/") or "/"
    if parsed.netloc.lower().endswith("youtube.com") and path.startswith("/@"):
        path=re.sub(r"/videos$|/featured$|/streams$","",path)
        query=[]
    return urllib.parse.urlunsplit((parsed.scheme.lower(),parsed.netloc.lower(),path,"&".join(f"{k}={v}" for k,v in query),""))

def _cadence(source_type: str, intent: str, cadence: str) -> tuple[str,str|None]:
    if intent=="ONE_TIME": return "NONE",None
    cadence=cadence.upper()
    if cadence not in {"AUTO","DAILY","WEEKLY","MONTHLY","EVENT_DRIVEN"}: raise ValueError("invalid_cadence")
    chosen={"YOUTUBE_CHANNEL":"WEEKLY","FORUM_COMMUNITY":"DAILY","GITHUB_REPO":"WEEKLY","NEWS":"DAILY","SEO_QUERY":"WEEKLY"}.get(source_type,"MONTHLY") if cadence=="AUTO" else cadence
    from datetime import timedelta,datetime,timezone
    delta={"DAILY":1,"WEEKLY":7,"MONTHLY":30,"EVENT_DRIVEN":7}[chosen]
    return chosen,(datetime.now(timezone.utc)+timedelta(days=delta)).isoformat()


def _latest() -> list[dict[str, Any]]:
    seen: set[str] = set()
    rows: list[dict[str, Any]] = []
    for row in persistence.read_records("alpha_source_registry"):
        source_id = str(row.get("source_id") or row.get("source_url") or "")
        if source_id and source_id not in seen:
            seen.add(source_id)
            rows.append(row)
    return rows


def add_source(url: str, *, source_type: str, lanes: list[str], priority: str = "P0_RAY_DIRECT", title: str = "", processing_intent: str = "ONE_TIME", cadence: str = "AUTO", question: str = "", notes: str = "") -> dict[str, Any]:
    normalized_type = source_type.upper()
    normalized_lanes = sorted({lane.upper() for lane in lanes})
    if normalized_type not in SOURCE_TYPES:
        raise ValueError("unsupported_source_type")
    if not normalized_lanes or not set(normalized_lanes) <= LANES:
        raise ValueError("invalid_source_lanes")
    normalized_url = _canonical_url(url)
    if not normalized_url.startswith(("https://", "http://")):
        raise ValueError("source_url_must_be_http")
    intent=processing_intent.upper()
    if intent not in {"ONE_TIME","CONTINUOUS"}: raise ValueError("invalid_processing_intent")
    source_id = f"ray_{_key(normalized_url)}"
    existing = next((row for row in _latest() if row.get("source_id") == source_id or _canonical_url(str(row.get("source_url", ""))) == normalized_url), None)
    if existing:
        if intent=="CONTINUOUS" and existing.get("processing_intent")!="CONTINUOUS":
            chosen,next_refresh=_cadence(normalized_type,intent,cadence)
            updated={**existing,"processing_intent":"CONTINUOUS","persistent":True,"role":"PERSISTENT","cadence":chosen,"next_refresh_at":next_refresh,"status":"ACTIVE","mode_reconciled":"ONE_TIME_TO_CONTINUOUS","updated_at":_now()}
            persistence.append_record("alpha_source_registry",updated); return updated
        if intent=="ONE_TIME":
            request={"request_id":"once_"+_key(normalized_url),"source_id":existing.get("source_id"),"url":normalized_url,"processing_intent":"ONE_TIME","status":"QUEUED","question":question,"created_at":_now()}
            persistence.append_record("research_requests",request)
            return {**existing,"status":"ONE_TIME_REQUEST_QUEUED","one_time_request_id":request["request_id"],"idempotent":True}
        return {**existing,"status":"DUPLICATE_SUPPRESSED","idempotent":True}
    chosen,next_refresh=_cadence(normalized_type,intent,cadence)
    record = {
        "source_id": source_id, "source_url": normalized_url, "canonical_url": normalized_url, "title": title or normalized_url,
        "source_type": normalized_type, "lanes": normalized_lanes, "priority": priority,
        "added_by": "RAY_CURATED", "origin": "RAY_SEED", "role": "PERSISTENT" if intent=="CONTINUOUS" else "ONE_TIME", "processing_intent":intent,"persistent":intent=="CONTINUOUS","cadence":chosen,"next_refresh_at":next_refresh,"status": "ACTIVE", "enabled": True,
        "question":question,"notes":notes,
        "initial_backfill": {"status": "PENDING", "bounded_depth": 10 if normalized_type in {"YOUTUBE_CHANNEL", "YOUTUBE_VIDEO"} else 1, "processed_ids": []},
        "incremental_monitoring": {"status": "READY", "last_checked_at": None, "last_seen_fingerprint": None},
        "claim_verification": "RESEARCH_AND_ALPHA_REQUIRED", "created_at": _now(), "updated_at": _now(),
    }
    persistence.append_record("alpha_source_registry", record)
    return record


def list_sources(*, lane: str | None = None, status: str | None = None) -> list[dict[str, Any]]:
    rows = _latest()
    if lane:
        rows = [row for row in rows if lane.upper() in set(row.get("lanes", []))]
    if status:
        rows = [row for row in rows if row.get("status") == status.upper()]
    return rows


def source_status(source_id: str) -> dict[str, Any] | None:
    return next((row for row in _latest() if row.get("source_id") == source_id), None)


def set_source_state(source_id: str, state: str) -> dict[str, Any]:
    current = source_status(source_id)
    if not current:
        raise ValueError("source_not_found")
    state = state.upper()
    if state not in {"ACTIVE", "PAUSED", "ARCHIVED"}:
        raise ValueError("invalid_source_state")
    updated = {**current, "status": state, "enabled": state == "ACTIVE", "updated_at": _now()}
    persistence.append_record("alpha_source_registry", updated)
    return updated


def update_source(source_id: str, *, priority: str | None = None, lanes: list[str] | None = None) -> dict[str, Any]:
    current = source_status(source_id)
    if not current:
        raise ValueError("source_not_found")
    normalized_lanes = sorted({lane.upper() for lane in (lanes or current.get("lanes", []))})
    if not set(normalized_lanes) <= LANES:
        raise ValueError("invalid_source_lanes")
    updated = {**current, "priority": priority or current.get("priority", "P1_ACTIVE_OBJECTIVE"), "lanes": normalized_lanes, "updated_at": _now()}
    persistence.append_record("alpha_source_registry", updated)
    return updated


def record_backfill(source_id: str, processed_ids: list[str], *, last_fingerprint: str | None = None) -> dict[str, Any]:
    current = source_status(source_id)
    if not current:
        raise ValueError("source_not_found")
    prior = set(current.get("initial_backfill", {}).get("processed_ids", []))
    merged = sorted(prior | set(processed_ids))
    updated = {**current, "initial_backfill": {**current.get("initial_backfill", {}), "status": "COMPLETE", "processed_ids": merged}, "incremental_monitoring": {**current.get("incremental_monitoring", {}), "last_checked_at": _now(), "last_seen_fingerprint": last_fingerprint}, "updated_at": _now()}
    persistence.append_record("alpha_source_registry", updated)
    return updated
