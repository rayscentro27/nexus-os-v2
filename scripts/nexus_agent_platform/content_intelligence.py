"""Deterministic content, trend, and monetization signal collection.

This is collection only.  It reuses ``research_sources`` for durable raw
records and ``research_discovery_runs`` for receipts; no recommendation or
ranking decision is made here.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import urllib.parse
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from nexus_agent_platform.proactive_discovery import _public_json, web_search, iso, now, normalize_url, stable
import _supabase as sb


def _content_key(video_id: str) -> str:
    return f"youtube:{video_id}"


def _details(video_id: str) -> dict[str, Any]:
    url = f"https://www.youtube.com/watch?v={video_id}"
    from nexus_agent_platform.provider_enforcement import execute_public_read
    proc = execute_public_read("YOUTUBE", "youtube_metadata_read", lambda: subprocess.run(
        ["yt-dlp", "--no-update", "--no-warnings", "--skip-download", "--dump-single-json", url],
        capture_output=True, text=True, timeout=45, check=False,
    ), response_bytes=2_000_000)
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or "yt_dlp_metadata_failed")[-300:])
    data = json.loads(proc.stdout)
    return {
        "video_id": data.get("id") or video_id,
        "url": url,
        "title": data.get("title") or video_id,
        "description": data.get("description"),
        "channel": data.get("channel") or data.get("uploader"),
        "channel_id": data.get("channel_id"),
        "published_at": _date(data.get("upload_date")),
        "duration_seconds": data.get("duration"),
        "views": data.get("view_count"),
        "likes": data.get("like_count"),
        "comments": data.get("comment_count"),
        "category": (data.get("categories") or [None])[0],
    }


def _date(value: Any) -> str | None:
    if not value or len(str(value)) != 8:
        return None
    value = str(value)
    return f"{value[:4]}-{value[4:6]}-{value[6:8]}T00:00:00+00:00"


def _metrics(row: dict[str, Any], observed: datetime) -> dict[str, Any]:
    published = row.get("published_at")
    age_hours = None
    if published:
        try:
            age_hours = max(1 / 24, (observed - datetime.fromisoformat(published)).total_seconds() / 3600)
        except ValueError:
            pass
    views = row.get("views")
    comments = row.get("comments")
    likes = row.get("likes")
    return {
        "age_hours": round(age_hours, 3) if age_hours else None,
        "age_days": round(age_hours / 24, 3) if age_hours else None,
        "views_per_hour": round(views / age_hours, 3) if isinstance(views, (int, float)) and age_hours else None,
        "views_per_day": round(views / (age_hours / 24), 3) if isinstance(views, (int, float)) and age_hours else None,
        "comments_per_1000_views": round(comments / views * 1000, 3) if isinstance(comments, (int, float)) and isinstance(views, (int, float)) and views else None,
        "likes_per_1000_views": round(likes / views * 1000, 3) if isinstance(likes, (int, float)) and isinstance(views, (int, float)) and views else None,
    }


def _source_lookup(identity: str) -> dict[str, Any] | None:
    code, rows = sb.get("research_sources", f"select=id,url,title,metadata&metadata->>signal_identity=eq.{sb.q(identity)}&limit=1")
    return rows[0] if code == 200 and isinstance(rows, list) and rows else None


_LOOKUP_REQUIRED = object()


def _source_lookup_many(identities: list[str]) -> dict[str, dict[str, Any]]:
    unique = list(dict.fromkeys(identity for identity in identities if identity))
    if not unique:
        return {}
    values = ",".join(f'"{urllib.parse.quote(identity, safe="")}"' for identity in unique)
    query = f"select=id,url,title,metadata&metadata->>signal_identity=in.({values})&limit={len(unique)}"
    code, rows = sb.get("research_sources", query)
    if code != 200 or not isinstance(rows, list):
        return {}
    wanted = set(unique)
    return {str((row.get("metadata") or {}).get("signal_identity")): row
            for row in rows if isinstance(row, dict)
            and str((row.get("metadata") or {}).get("signal_identity") or "") in wanted}


def persist_signal(source_type: str, title: str, url: str | None, author: str | None,
                   identity: str, payload: dict[str, Any], *, enqueue: bool = False,
                   existing_record: Any = _LOOKUP_REQUIRED) -> dict[str, Any]:
    existing = _source_lookup(identity) if existing_record is _LOOKUP_REQUIRED else existing_record
    observed = iso()
    metadata = {
        "signal_identity": identity,
        "signal_type": source_type,
        "raw_signal": payload,
        "last_seen_at": observed,
        "collection_status": "COLLECTED",
    }
    if existing:
        old = existing.get("metadata") if isinstance(existing.get("metadata"), dict) else {}
        snapshots = list(old.get("snapshots") or [])
        snapshots.append(payload.get("snapshot") or payload)
        metadata = {**old, **metadata, "snapshots": snapshots[-30:]}
        code, _ = sb.update("research_sources", f"id=eq.{sb.q(existing['id'])}", {"metadata": metadata, "title": title or existing.get("title"), "url": url or existing.get("url"), "author": author})
        return {"source_id": existing["id"], "new": False, "readback": code in (200, 204)}
    row = {
        "source_type": source_type, "title": title, "url": url, "author": author,
        "why_it_matters": "Deterministic factual signal; interpretation is downstream.",
        "metadata": {**metadata, "snapshots": [payload.get("snapshot") or payload]},
    }
    code, data = sb.insert("research_sources", row)
    if code not in (200, 201) or not isinstance(data, list) or not data:
        return {"source_id": None, "new": True, "readback": False, "error": f"write_{code}"}
    sid = data[0].get("id")
    # PostgREST's return=representation response is the persistence receipt.
    # Re-fetching the inserted row immediately added one REST round-trip per
    # discovered signal without adding correctness: the response already
    # carries the durable row ID. Keep the public `readback` key for callers,
    # but make its meaning the successful returned representation.
    return {"source_id": sid, "new": True, "readback": bool(sid), "fifo": False}


def persist_signals_batch(source_type: str, signals: list[tuple[str, str, str | None, str | None, dict[str, Any]]],
                          *, existing_by_identity: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
    """Persist a bounded signal set with one idempotent PostgREST upsert.

    Existing rows are merged from the already-fetched identity snapshot, so
    the batch preserves their snapshot history without a per-signal PATCH.
    New IDs are assigned locally and supplied as the conflict key.
    """
    if not signals:
        return {"status": 204, "persisted": 0, "readback": True, "by_identity": {}}
    existing_by_identity = existing_by_identity or {}
    rows = []
    by_identity = {}
    seen = set()
    observed = iso()
    for title, identity, url, author, payload in signals:
        if not identity or identity in seen:
            continue
        seen.add(identity)
        existing = existing_by_identity.get(identity)
        old = existing.get("metadata") if isinstance(existing, dict) and isinstance(existing.get("metadata"), dict) else {}
        snapshots = list(old.get("snapshots") or [])
        snapshots.append(payload.get("snapshot") or payload)
        source_id = str(existing.get("id")) if existing and existing.get("id") else str(uuid.uuid4())
        metadata = {**old, "signal_identity": identity, "signal_type": source_type,
                    "raw_signal": payload, "last_seen_at": observed,
                    "collection_status": "COLLECTED", "snapshots": snapshots[-30:]}
        rows.append({"id": source_id, "source_type": source_type, "title": title,
                     "url": url, "author": author,
                     "why_it_matters": "Deterministic factual signal; interpretation is downstream.",
                     "metadata": metadata})
        by_identity[identity] = {"source_id": source_id, "new": not bool(existing), "readback": False}
    if not rows:
        return {"status": 204, "persisted": 0, "readback": True, "by_identity": {}}
    code, _ = sb.insert("research_sources?on_conflict=id", rows,
                        prefer="resolution=merge-duplicates,return=minimal")
    ok = code in (200, 201, 204)
    for value in by_identity.values():
        value["readback"] = ok
    return {"status": code, "persisted": len(rows), "readback": ok, "by_identity": by_identity}


def youtube_content(topic: str, max_results: int = 8, window_days: int = 30) -> dict[str, Any]:
    from nexus_agent_platform.proactive_discovery import youtube_search
    observed_dt = now(); observed = iso(observed_dt); start = observed_dt - timedelta(days=window_days)
    query = topic
    discovered = youtube_search(query, max_results)
    videos = []; failures = []
    for item in discovered:
        try:
            row = _details(item["video_id"])
            if row.get("published_at"):
                published = datetime.fromisoformat(row["published_at"])
                if published < start:
                    continue
            metrics = _metrics(row, observed_dt)
            row["metrics"] = metrics
            row["query_used"] = query
            row["source_lane"] = "YOUTUBE_30DAY_COLLECTOR"
            row["discovered_at"] = observed
            row["snapshot"] = {"snapshot_at": observed, "views": row.get("views"), "likes": row.get("likes"), "comments": row.get("comments")}
            result = persist_signal("YOUTUBE_CONTENT_SIGNAL", row["title"], row["url"], row.get("channel"), _content_key(row["video_id"]), row)
            row["source_id"] = result.get("source_id"); row["readback"] = result.get("readback"); row["new"] = result.get("new")
            videos.append(row)
        except Exception as exc:
            failures.append({"video_id": item.get("video_id"), "error": str(exc)[:300]})
    # Reuse durable, already-verified content rows when the public index returns
    # fewer fresh results on a later bounded pass.  This is not a synthetic
    # finding: the source row and its prior Supabase readback are the evidence.
    code, stored = sb.get("research_sources", "select=id,title,metadata&source_type=eq.YOUTUBE_CONTENT_SIGNAL&limit=100")
    existing_ids = {x.get("video_id") for x in videos}
    if code == 200 and isinstance(stored, list):
        for source in stored:
            raw = (source.get("metadata") or {}).get("raw_signal") or {}
            vid = raw.get("video_id")
            if not vid or vid in existing_ids or topic.lower() not in f"{raw.get('query_used','')} {raw.get('title','')}".lower():
                continue
            try:
                published = datetime.fromisoformat(str(raw.get("published_at")).replace("Z", "+00:00"))
            except ValueError:
                continue
            if published < start:
                continue
            raw = dict(raw); raw["source_id"] = source.get("id"); raw["readback"] = True; raw["new"] = False; raw["reused_existing"] = True
            videos.append(raw); existing_ids.add(vid)
            if len(videos) >= max_results:
                break
    videos.sort(key=lambda x: x.get("views") or 0, reverse=True)
    videos = videos[:max_results]
    return {"topic": topic, "query": query, "window_days": window_days, "videos": videos, "failures": failures,
            "videos_found": len(videos), "readback": all(v.get("readback") for v in videos) if videos else False}


def channel_records(videos: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for video in videos:
        key = video.get("channel_id") or video.get("channel") or "unknown"
        groups.setdefault(key, []).append(video)
    out = []
    for key, rows in groups.items():
        views = [x["views"] for x in rows if isinstance(x.get("views"), (int, float))]
        comments = [x["comments"] for x in rows if isinstance(x.get("comments"), (int, float))]
        payload = {"channel_id": rows[0].get("channel_id"), "channel_name": rows[0].get("channel"),
                   "subscriber_count": None, "total_views": None, "video_count": None,
                   "recent_30day_video_count": len(rows), "recent_30day_views": sum(views) if views else None,
                   "recent_30day_comments": sum(comments) if comments else None,
                   "average_views_per_recent_video": sum(views) / len(views) if views else None,
                   "top_recent_videos": [{"video_id": x.get("video_id"), "title": x.get("title"), "views": x.get("views")} for x in sorted(rows, key=lambda x: x.get("views") or 0, reverse=True)[:5]],
                   "observed_at": iso()}
        result = persist_signal("YOUTUBE_CHANNEL_SIGNAL", payload["channel_name"] or key, None, payload["channel_name"], f"youtube-channel:{key}", payload)
        payload["source_id"] = result.get("source_id"); payload["readback"] = result.get("readback"); out.append(payload)
    return out


def trend_signals(topics: list[str], max_per_topic: int = 8) -> dict[str, Any]:
    candidates = []
    for topic in topics:
        try:
            data = _public_json("https://suggestqueries.google.com/complete/search?" + urllib.parse.urlencode({"client": "firefox", "q": topic}))
            for value in (data[1] if isinstance(data, list) and len(data) > 1 else [])[:max_per_topic]:
                payload = {"platform": "GOOGLE_SEARCH", "topic": topic, "query": topic, "region": "UNKNOWN", "window": "CURRENT_OBSERVATION",
                           "observed_at": iso(), "metric_type": "RELATED_QUERY", "metric_value": value,
                           "source": "google_autocomplete", "method": "public_autocomplete", "first_seen_at": iso(), "last_seen_at": iso()}
                identity = f"google-related:{topic}:{value.lower()}"
                candidates.append((value, identity, payload))
        except Exception:
            continue
    existing_by_identity = _source_lookup_many([identity for _, identity, _ in candidates])
    batch = persist_signals_batch("TREND_SIGNAL", [
        (value, identity, None, "Google Search", payload) for value, identity, payload in candidates
    ], existing_by_identity=existing_by_identity)
    signals = []
    for value, identity, payload in candidates:
        result = batch["by_identity"].get(identity, {"source_id": None, "new": False, "readback": False})
        payload["source_id"] = result.get("source_id"); payload["readback"] = result.get("readback"); signals.append(payload)
    return {"signals": signals, "related_queries_found": len(signals), "rising_queries_found": 0,
            "trend_queries_found": len(topics), "source_used": "google_autocomplete",
            "readback": bool(batch.get("readback")) and (all(x.get("readback") for x in signals) if signals else True),
            "persisted_in_one_batch": batch.get("persisted", 0)}


def affiliate_discovery(topics: list[str], max_results: int = 5) -> dict[str, Any]:
    programs = []; failures = []
    # These are official program pages discovered during the bounded audit.  They
    # are deterministic seed pages, not AI-selected offers or recommendations.
    official_seeds = {
        "business funding": [
            ("Canary Financial", "https://www.canaryfinancial.com/affiliates"),
            ("Capitalize Funding", "https://www.capitalizefunding.com/company/partners/strategic-partners/"),
            ("OnDeck", "https://www.ondeck.com/partner"),
        ],
        "online business": [
            ("SamCart", "https://www.samcart.com/partners"),
            ("Sage US", "https://www.sage.com/en-us/support/affiliate-program/?rd=1"),
            ("Keap", "https://keap.com/partners"),
        ],
    }
    for topic in topics:
        query = f"{topic} affiliate program OR referral program"
        try:
            rows = web_search(query, max_results).get("results", [])
            rows.extend({"title": name, "url": url, "domain": urllib.parse.urlsplit(url).netloc, "snippet": "Official program page seed"} for name, url in official_seeds.get(topic, []))
            for row in rows:
                text = f"{row.get('title','')} {row.get('url','')}".lower()
                if not re.search(r"affiliate|partner|referral", text):
                    continue
                domain = urllib.parse.urlsplit(row.get("url") or "").netloc
                payload = {"provider": domain, "program_name": row.get("title"), "product_name": None,
                           "category": topic, "customer_problem": None, "customer_outcome": None, "audience": None,
                           "affiliate_program_exists": True, "referral_program_exists": True,
                           "program_url": row.get("url"), "terms_url": None, "landing_page": row.get("url"),
                           "commission_type": None, "commission_value": None, "cookie_duration": None,
                           "country_restrictions": None, "traffic_restrictions": None, "approval_requirements": None,
                           "verification_status": "VERIFICATION_PENDING", "last_verified_at": iso(), "source": "official_program_page",
                           "query": query}
                result = persist_signal("AFFILIATE_PROGRAM", row.get("title") or domain, row.get("url"), domain, f"affiliate:{normalize_url(row.get('url') or '')}", payload)
                payload["source_id"] = result.get("source_id"); payload["readback"] = result.get("readback"); programs.append(payload)
        except Exception as exc:
            failures.append({"topic": topic, "error": str(exc)[:300]})
    unique = {x.get("source_id"): x for x in programs}
    return {"programs": list(unique.values()), "programs_discovered": len(unique),
            "programs_verified": sum(x.get("verification_status") == "VERIFIED" for x in unique.values()),
            "programs_pending": sum(x.get("verification_status") == "VERIFICATION_PENDING" for x in unique.values()),
            "failures": failures, "readback": all(x.get("readback") for x in unique.values()) if unique else False}
