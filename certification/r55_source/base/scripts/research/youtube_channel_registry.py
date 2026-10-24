"""Migration and access helpers for the canonical designated YouTube registry.

Supabase ``research_sources`` rows tagged DESIGNATED_YOUTUBE_CHANNEL are the
durable registry projection (their UUID primary key is deterministic); the
existing governed Alpha collection is the local operating mirror. Historical
content never enters the Research queue through this module.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import urllib.parse
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from nexus_agent_platform.governed import persistence
from research import ray_source_intake as intake
from social import _supabase as supabase

REGISTRY_KIND = "DESIGNATED_YOUTUBE_CHANNEL"


def canonical_channel_url(url: str, channel_id: str | None = None) -> str:
    parsed = urllib.parse.urlsplit(url.strip())
    path = re.sub(r"/(videos|featured|streams|live|shorts)/?$", "", parsed.path, flags=re.I).rstrip("/")
    if path.startswith("/@"):
        path = "/@" + path[2:].lower()
    if path:
        return urllib.parse.urlunsplit(("https", "www.youtube.com", path, "", ""))
    if channel_id:
        return "https://www.youtube.com/channel/" + channel_id
    return urllib.parse.urlunsplit(("https", "www.youtube.com", "/", "", ""))


def _handle(url: str) -> str | None:
    path = urllib.parse.urlsplit(url).path
    match = re.match(r"/@([^/]+)", path)
    return match.group(1).lower() if match else None


def legacy_designated_channels() -> list[dict[str, Any]]:
    """Read only existing monitor/config records; no repository crawl."""
    runtime_path = ROOT / "data/runtime/alpha_source_registry.json"
    config_path = ROOT / "configs/youtube_research_channels.json"
    portfolio_path = ROOT / "configs/youtube_channel_portfolio.json"
    runtime = json.loads(runtime_path.read_text(encoding="utf-8")) if runtime_path.exists() else []
    approved = json.loads(config_path.read_text(encoding="utf-8")) if config_path.exists() else {}
    portfolio = json.loads(portfolio_path.read_text(encoding="utf-8")) if portfolio_path.exists() else {}
    approved_rows = [r for r in approved.get("channels", []) if r.get("approved_by_ray") and r.get("enabled", True)]
    # The runtime Alpha registry is the previous monitor's effective active set.
    monitored = [r for r in runtime if str(r.get("source_type", "")).upper() == "YOUTUBE_CHANNEL"
                 and r.get("monitoring_enabled") and str(r.get("status", "ACTIVE")).upper() == "ACTIVE"]
    portfolio_by_handle = {_handle(str(r.get("url", ""))): r for r in portfolio.get("channels", []) if r.get("url") and _handle(str(r["url"]))}
    approved_by_id = {str(r.get("channel_id")): r for r in approved_rows if r.get("channel_id")}
    approved_by_handle = {_handle(str(r.get("url", ""))): r for r in approved_rows if r.get("url") and _handle(str(r["url"]))}
    # Combine active runtime rows and explicitly approved records. URL variants
    # collapse by channel ID first, otherwise by normalized handle URL.
    grouped: dict[str, dict[str, Any]] = {}
    for row in monitored + approved_rows:
        url = str(row.get("url") or row.get("channel_url") or row.get("source_url") or "")
        cid = str(row.get("channel_id") or "")
        if not url and cid: url = "https://www.youtube.com/channel/" + cid
        if not url: continue
        matched = approved_by_id.get(cid) or approved_by_handle.get(_handle(url)) or {}
        cid = cid or str(matched.get("channel_id") or "")
        portfolio_row = portfolio_by_handle.get(_handle(url), {})
        enriched = {**row, **matched}
        canonical = canonical_channel_url(url, cid or None)
        key = "youtube:" + cid if cid else "url:" + canonical
        old = grouped.get(key, {})
        # Prefer metadata-rich row over old /videos-shaped runtime projections.
        if len(enriched) >= len(old):
            categories = enriched.get("categories") or old.get("categories") or []
            published_items = row.get("recent_scan_items") or old.get("recent_scan_items") or []
            name = enriched.get("name") or enriched.get("channel_name")
            if not name or str(name).lower() == "videos": name = portfolio_row.get("name") or _handle(url) or cid
            raw_priority = enriched.get("priority", old.get("priority", 50))
            try: priority = int(raw_priority)
            except (ValueError, TypeError): priority = 0 if str(raw_priority).upper().startswith("P0") else 50
            target = enriched.get("target_department") or (enriched.get("target_departments") or [None])[0] or enriched.get("owner_department") or "RESEARCH"
            baseline_id = enriched.get("last_seen_video_id") or enriched.get("last_item_seen")
            baseline_at = enriched.get("last_item_seen_at")
            if not baseline_at and published_items:
                baseline_at = published_items[0].get("published_at")
            grouped[key] = {
                "source_id": "src_" + hashlib.sha256(key.encode()).hexdigest()[:24],
                "name": str(name), "source_type": "youtube_channel", "url": canonical,
                "canonical_url": canonical, "external_channel_id": cid or None,
                "category": "|".join(str(x).upper() for x in categories) if categories else "GENERAL",
                "priority": priority, "target_department": str(target).upper(),
                "enabled": bool(enriched.get("enabled", enriched.get("monitoring_enabled", True))),
                "created_at": enriched.get("created_at") or enriched.get("added_at"),
                "last_checked_at": enriched.get("last_checked_at") or enriched.get("last_checked"),
                "last_item_seen": baseline_id, "last_item_seen_at": baseline_at,
                "last_success_at": enriched.get("last_success_at") or enriched.get("last_successful_scan"),
                "last_error": enriched.get("last_error"), "notes": enriched.get("notes", ""),
                "monitor_mode": "NEW_CONTENT_ONLY", "triage_mode": "TRIAGE_ONLY",
                "baseline_status": "ESTABLISHED" if baseline_id else "PENDING_INITIAL_SNAPSHOT",
                "baseline_video_id": baseline_id, "baseline_published_at": baseline_at,
                "default_profile": enriched.get("default_profile") or (categories[0] if categories else None),
                "default_notebook": enriched.get("default_notebook"),
            }
    stored_rows = []
    try:
        stored_rows += supabase_channels()
    except Exception:
        pass
    # The local governed mirror can contain a newer scan receipt than a remote
    # row after a transient write failure, so prefer the mirror during merges.
    stored_rows += intake._latest()
    reconciled = []
    for source in grouped.values():
        stored = next((row for row in reversed(stored_rows) if
                       (source.get("external_channel_id") and
                        row.get("external_channel_id") == source.get("external_channel_id")) or
                       (row.get("canonical_url") or row.get("source_url")) == source.get("canonical_url")), {})
        if stored:
            source["source_id"] = stored.get("source_id") or source["source_id"]
            for key in ("created_at", "last_checked_at", "last_item_seen", "last_item_seen_at",
                        "last_success_at", "last_error", "baseline_video_id", "baseline_published_at",
                        "triage_mode", "priority", "target_department", "enabled"):
                if stored.get(key) is not None:
                    source[key] = stored[key]
            baseline = stored.get("monitor_baseline") if isinstance(stored.get("monitor_baseline"), dict) else {}
            source["baseline_video_id"] = source.get("baseline_video_id") or baseline.get("video_id")
            source["baseline_published_at"] = source.get("baseline_published_at") or baseline.get("published_at")
            if source.get("baseline_video_id") and source.get("baseline_published_at"):
                source["baseline_status"] = "ESTABLISHED"
        reconciled.append(source)
    return reconciled


def _db_uuid(source: dict[str, Any]) -> str:
    identity = source.get("external_channel_id") or source["canonical_url"]
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "nexus:designated-youtube:" + str(identity)))


def db_row(source: dict[str, Any]) -> dict[str, Any]:
    return {"id": _db_uuid(source), "source_type": "YOUTUBE_CHANNEL", "title": source["name"],
            "url": source["canonical_url"], "metadata": {**source, "registry_kind": REGISTRY_KIND,
                "source_id": source["source_id"], "external_channel_id": source.get("external_channel_id"),
                "monitor_mode": "NEW_CONTENT_ONLY", "initial_backfill": {"status": "NOT_REQUESTED"},
                "record_kind": "PERMANENT_MONITOR"}}


def supabase_channels(*, required: bool = False) -> list[dict[str, Any]]:
    if not supabase.configured():
        if required: raise RuntimeError("supabase_not_configured")
        return []
    status, body = supabase.rest("GET", "research_sources?metadata->>registry_kind=eq." + REGISTRY_KIND +
                                 "&select=id,title,url,metadata&limit=500")
    if status != 200 or not isinstance(body, list):
        if required: raise RuntimeError(f"supabase_registry_read_failed:{status}")
        return []
    # Old migrations and retries can leave more than one research_sources row
    # for the same permanent monitor.  Keep the freshest logical channel row
    # in the runtime projection without deleting its historical records.
    latest: dict[str, dict[str, Any]] = {}
    for row in body:
        metadata = row.get("metadata")
        if not isinstance(metadata, dict):
            continue
        identity = str(metadata.get("external_channel_id") or metadata.get("canonical_url") or row.get("url") or row.get("id") or "")
        if not identity:
            continue
        prior = latest.get(identity)
        freshness = (bool(metadata.get("baseline_video_id") or metadata.get("last_item_seen")),
                     str(metadata.get("updated_at") or metadata.get("last_checked_at") or ""))
        prior_freshness = ((bool(prior and (prior.get("baseline_video_id") or prior.get("last_item_seen"))),
                            str((prior or {}).get("updated_at") or (prior or {}).get("last_checked_at") or "")))
        if prior is None or freshness > prior_freshness:
            latest[identity] = metadata
    return list(latest.values())


def upsert_supabase(sources: list[dict[str, Any]]) -> dict[str, Any]:
    if not supabase.configured(): return {"ok": False, "reason": "supabase_not_configured", "written": 0}
    rows = [db_row(source) for source in sources]
    status, body = supabase.rest("POST", "research_sources?on_conflict=id", body=rows,
                                 prefer="return=representation,resolution=merge-duplicates")
    return {"ok": status in {200, 201}, "status": status, "written": len(body) if isinstance(body, list) else (len(rows) if status in {200, 201, 204} else 0),
            "ids": [row["id"] for row in rows], "error": body if status not in {200, 201, 204} else None}


def migrate(sources: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    from research.ray_source_intake import add_designated_source
    sources = sources if sources is not None else legacy_designated_channels()
    existing_rows = intake._latest()
    # Carry forward the existing canonical source_id when a previous local
    # registry row already represents this channel by ID or canonical URL.
    for source in sources:
        prior_match = next((r for r in existing_rows if
            (source.get("external_channel_id") and r.get("external_channel_id") == source.get("external_channel_id")) or
            (r.get("canonical_url") or r.get("source_url")) == source["canonical_url"]), None)
        if prior_match:
            source["source_id"] = prior_match["source_id"]
    prior = {row.get("source_id") for row in existing_rows}
    local_ids = []
    for source in sources:
        result = add_designated_source(name=source["name"], source_type="youtube_channel", url=source["canonical_url"],
            category=source["category"], priority=source["priority"], target_department=source["target_department"],
            enabled=source["enabled"], notes=source.get("notes", ""), external_channel_id=source.get("external_channel_id"),
            baseline_video_id=source.get("baseline_video_id"), baseline_published_at=source.get("baseline_published_at"),
            triage_mode=source.get("triage_mode", "TRIAGE_ONLY"))
        local_ids.append(result["source_id"])
    remote = upsert_supabase(sources)
    readback = supabase_channels(required=True) if remote["ok"] else []
    readback_by_id = {str(row.get("source_id")): row for row in readback}
    migrated = sum(1 for sid in local_ids if sid not in prior)
    present = len(local_ids) - migrated
    return {"channels_migrated": migrated, "channels_already_present": present,
            "channels_failed_migration": len(sources) - len(local_ids), "local_source_ids": local_ids,
            "supabase_write": remote, "supabase_readback_count": len(readback),
            "supabase_all_read_back": all(sid in readback_by_id for sid in local_ids),
            "sources": sources}


def update_monitor_state(source_id: str, *, baseline_video_id: str | None = None,
                         baseline_published_at: str | None = None,
                         last_checked_at: str | None = None, last_error: str | None = None,
                         persist_remote: bool = True) -> dict[str, Any] | None:
    row = next((r for r in intake._latest() if r.get("source_id") == source_id), None)
    if row is None:
        row = next((r for r in supabase_channels() if r.get("source_id") == source_id), None)
    if row is None: return None
    now = datetime.now(timezone.utc).isoformat()
    if baseline_video_id:
        baseline_published_at = baseline_published_at or now
        row.update({"baseline_status": "ESTABLISHED", "baseline_video_id": baseline_video_id,
                    "baseline_published_at": baseline_published_at, "last_item_seen": baseline_video_id,
                    "last_item_seen_at": baseline_published_at, "last_seen_video_id": baseline_video_id})
    if last_checked_at:
        row["last_checked_at"] = last_checked_at
        row["last_success_at"] = last_checked_at if not last_error else row.get("last_success_at")
    row["last_error"] = last_error
    row["updated_at"] = now
    persistence.append_record("alpha_source_registry", row)
    if not persist_remote:
        row["supabase_state_write"] = "PENDING_BATCH"
        return row
    remote = upsert_supabase([row])
    row["supabase_state_write"] = remote["ok"]
    return row


def enabled_channels(*, require_supabase: bool = False) -> list[dict[str, Any]]:
    rows = supabase_channels(required=True) if require_supabase else supabase_channels()
    if not rows:
        rows = [r for r in intake._latest() if r.get("monitor_mode") == "NEW_CONTENT_ONLY" and
                r.get("source_type") == "YOUTUBE_CHANNEL"]
    return [r for r in rows if r.get("enabled") and r.get("monitor_mode") == "NEW_CONTENT_ONLY"
            and r.get("source_type", "YOUTUBE_CHANNEL").upper() == "YOUTUBE_CHANNEL"]


def video_metadata_row(source: dict[str, Any], video: dict[str, Any], *, disposition: str,
                       qualification: dict[str, Any], case_id: str | None = None) -> dict[str, Any]:
    video_id = str(video.get("video_id") or "")
    stable = str(uuid.uuid5(uuid.NAMESPACE_URL, "nexus:youtube-video:" + video_id))
    return {"id": stable, "source_type": "YOUTUBE_VIDEO", "title": video.get("title") or video_id,
            "url": video.get("url") or f"https://www.youtube.com/watch?v={video_id}",
            "author": source.get("name"), "published_at": video.get("published_at"),
            "accessed_at": datetime.now(timezone.utc).isoformat(),
            "snippet": str(video.get("description") or "")[:1200] or None,
            "metadata": {"record_kind": "YOUTUBE_MONITOR_TRIAGE_ITEM", "video_id": video_id,
                         "channel_source_id": source.get("source_id"),
                         "external_channel_id": source.get("external_channel_id"),
                         "triage_mode": source.get("triage_mode", "TRIAGE_ONLY"),
                         "disposition": disposition, "qualification": qualification,
                         "research_case_id": case_id, "notebook_created": False}}


def persist_video_metadata(source: dict[str, Any], video: dict[str, Any], *, disposition: str,
                           qualification: dict[str, Any], case_id: str | None = None) -> dict[str, Any]:
    row = video_metadata_row(source, video, disposition=disposition, qualification=qualification, case_id=case_id)
    if not supabase.configured():
        return {"ok": False, "row": row, "reason": "supabase_not_configured"}
    status, body = supabase.rest("POST", "research_sources?on_conflict=id", body=[row],
                                 prefer="return=representation,resolution=merge-duplicates")
    return {"ok": status in {200, 201, 204}, "status": status, "row": row,
            "error": body if status not in {200, 201, 204} else None}


def persist_youtube_case(source: dict[str, Any], video: dict[str, Any], case: dict[str, Any]) -> dict[str, Any]:
    """Persist a bounded video investigation in the existing Research question table."""
    if not supabase.configured(): return {"ok": False, "reason": "supabase_not_configured"}
    case_id = str(case["case_id"])
    db_id = str(uuid.uuid5(uuid.NAMESPACE_URL, "nexus:youtube-research-case:" + case_id))
    prior_status, prior = supabase.rest("GET", f"research_questions?id=eq.{db_id}&select=id&limit=1")
    if prior_status == 200 and isinstance(prior, list) and prior:
        return {"ok": True, "already_present": True, "case_id": case_id, "supabase_case_id": db_id}
    source_url = video.get("url") or f"https://www.youtube.com/watch?v={video.get('video_id')}"
    row = {"id": db_id,
           "question": f"Research and validate this new YouTube item: {str(video.get('title') or video.get('video_id'))[:300]}",
           "requester": "RESEARCH_YOUTUBE_MONITOR", "parent_goal_id": source.get("source_id"),
           "department": "RESEARCH", "business_decision_supported": source.get("category", "YouTube intelligence"),
           "priority": int(source.get("priority", 50)), "status": "OPEN",
           "sources_reviewed": [{"source_type": "YOUTUBE_VIDEO", "source_id": video.get("video_id"),
                                 "source_url": source_url, "channel_source_id": source.get("source_id")}],
           "current_findings": [], "next_action": "validate evidence, then decide whether a temporary NotebookLM workspace is useful",
           "created_at": datetime.now(timezone.utc).isoformat(), "updated_at": datetime.now(timezone.utc).isoformat()}
    status, body = supabase.rest("POST", "research_questions?on_conflict=id", body=[row],
                                 prefer="return=representation,resolution=merge-duplicates")
    if status not in {200, 201, 204}:
        return {"ok": False, "status": status, "error": body}
    read_status, readback = supabase.rest("GET", f"research_questions?id=eq.{db_id}&select=id&limit=1")
    return {"ok": read_status == 200 and isinstance(readback, list) and bool(readback),
            "status": status, "readback_status": read_status, "case_id": case_id, "supabase_case_id": db_id}


def split_by_baseline(channel: dict[str, Any], videos: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    """Return only provably post-baseline videos; first observation only sets baseline."""
    baseline_id = channel.get("baseline_video_id") or channel.get("last_seen_video_id") or channel.get("last_item_seen")
    baseline_at = channel.get("baseline_published_at") or channel.get("last_item_seen_at")
    if not baseline_id or not baseline_at:
        return [], True
    baseline_time = _parse_published_at(baseline_at)
    if baseline_time is None:
        return [], True
    new = []
    for video in videos:
        stamp = _parse_published_at(video.get("published_at"))
        if stamp is None: continue
        if stamp > baseline_time and str(video.get("video_id")) != str(baseline_id):
            new.append(video)
    return new, False


def _parse_published_at(value: Any) -> datetime | None:
    if value is None: return None
    raw = str(value)
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        try: parsed = datetime.strptime(raw, "%Y%m%d").replace(tzinfo=timezone.utc)
        except ValueError: return None
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed
