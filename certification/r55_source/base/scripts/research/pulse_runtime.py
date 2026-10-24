#!/usr/bin/env python3
"""Pulse trend intelligence runtime; invoked by the existing continuous daemon."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts" / "social"))
import _supabase as sb  # noqa: E402

PULSE_JOBS = {
    "PULSE_FLASH_SCAN": 7200,
    "PULSE_GENERAL_SCAN": 14400,
    "PULSE_DAILY_DEEP_REVIEW": 86400,
    "PULSE_DECAY_REVIEW": 86400,
    "PULSE_COMMERCE_REFRESH": 86400,
}
LIVE_PUBLISHING_ENABLED = False
PRINTIFY_ORDER_ENABLED = False
TZ = dt.timezone.utc


def now() -> dt.datetime:
    return dt.datetime.now(TZ)


def iso(value: dt.datetime | None = None) -> str:
    return (value or now()).isoformat()


def _id(prefix: str, text: str) -> str:
    return prefix + hashlib.sha256(text.encode()).hexdigest()[:24]


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)


def _rows(table: str, query: str) -> list[dict[str, Any]]:
    status, rows = sb.get(table, query)
    return rows if status == 200 and isinstance(rows, list) else []


def _upsert(table: str, key: str, row: dict[str, Any]) -> tuple[bool, dict[str, Any] | None]:
    # Return only the conflict key(s). The prior pattern downloaded each full
    # JSONB row a second time just to prove an upsert succeeded.
    code, saved = sb.rest("POST", f"{table}?on_conflict={key}&select={key}", [row], "resolution=merge-duplicates,return=representation")
    if code not in (200, 201) or not isinstance(saved, list) or not saved:
        return False, None
    return True, saved[0]


def bootstrap() -> dict[str, Any]:
    stamp = iso()
    for job, cadence in PULSE_JOBS.items():
        existing = _rows("pulse_schedule_registry", f"select=job_id&job_id=eq.{job}&limit=1")
        if not existing:
            ok, _ = _upsert("pulse_schedule_registry", "job_id", {
                "job_id": job, "cadence_seconds": cadence, "enabled": True,
                "next_run_at": iso(now() + dt.timedelta(seconds=cadence)), "last_status": "SCHEDULE_CONFIGURED",
                "updated_at": stamp,
            })
            if not ok: return {"status": "SUPABASE_WRITE_FAILED", "job_id": job}
    providers = _rows("pulse_provider_registry", "select=provider_name,current_status,nexus_tested")
    return {"status": "PASS" if len(providers) >= 8 else "DEGRADED", "schedule_count": len(PULSE_JOBS), "provider_count": len(providers)}


def _parse_rss(url: str, source: str, limit: int = 30) -> list[dict[str, Any]]:
    try:
        def fetch():
            request = urllib.request.Request(url, headers={"User-Agent": "NexusPulse/1.0 (public trend discovery)"})
            with urllib.request.urlopen(request, timeout=15) as response:
                return ET.fromstring(response.read(1_000_000))
        from nexus_agent_platform.provider_enforcement import execute_public_read
        root = execute_public_read("BROWSER_EXTERNAL_SERVICES", "pulse_public_research", fetch, response_bytes=1_000_000)
    except Exception:
        return []
    out = []
    for item in root.findall(".//item")[:limit]:
        title = item.findtext("title") or ""
        link = item.findtext("link") or ""
        if title and link:
            publisher = item.findtext("source") or ""
            out.append({"source": source, "platform": source, "title": title, "url": link,
                        "publisher": publisher, "published_at": item.findtext("pubDate"), "description": item.findtext("description")})
    return out


def _search_feeds(topics: list[str]) -> list[dict[str, Any]]:
    items = _parse_rss("https://trends.google.com/trending/rss?geo=US", "GOOGLE_TRENDS", 50)
    for topic in topics:
        query = urllib.parse.urlencode({"q": topic, "hl": "en-US", "gl": "US", "ceid": "US:en"})
        items.extend(_parse_rss("https://news.google.com/rss/search?" + query, "GOOGLE_NEWS", 8))
    return items


def _related(topic: str) -> list[str]:
    url = "https://suggestqueries.google.com/complete/search?" + urllib.parse.urlencode({"client": "firefox", "q": topic})
    try:
        def fetch():
            with urllib.request.urlopen(url, timeout=12) as response:
                return json.loads(response.read(200_000).decode())
        from nexus_agent_platform.provider_enforcement import execute_public_read
        payload = execute_public_read("BROWSER_EXTERNAL_SERVICES", "pulse_related_search", fetch, response_bytes=200_000)
        return [str(x) for x in payload[1][:8]] if isinstance(payload, list) and len(payload) > 1 else []
    except Exception:
        return []


def _video_signals(topics: list[str], max_results: int = 2) -> list[dict[str, Any]]:
    from nexus_agent_platform.content_intelligence import youtube_content
    output = []
    for topic in topics:
        try:
            result = youtube_content(topic, max_results=max_results, window_days=30)
            output.extend(x for x in result.get("videos", []) if x.get("readback"))
        except Exception:
            continue
    return output


def _score(signal: dict[str, Any], source_count: int) -> dict[str, Any]:
    metrics = signal.get("metrics") or {}
    vph = metrics.get("views_per_hour")
    views = signal.get("views")
    comments = signal.get("comments")
    likes = signal.get("likes")
    engagement = None
    if isinstance(views, (int, float)) and views > 0 and isinstance(likes, (int, float)):
        engagement = 100 * min(1.0, (likes + (comments or 0)) / views * 0.12)
    velocity = min(100, math.log10(max(1, float(vph or 0)) + 1) * 16.5) if vph is not None else None
    title = str(signal.get("title") or signal.get("keyword") or "").lower()
    relevance = 85 if any(k in title for k in ("business", "ai", "marketing", "automation", "credit", "funding")) else 35
    scores = {
        "VELOCITY_SCORE": round(velocity, 1) if velocity is not None else None,
        "ACCELERATION_SCORE": None,
        "CROSS_PLATFORM_SCORE": round(min(100, source_count / 3 * 100), 1),
        "SEARCH_GROWTH_SCORE": None,
        "ENGAGEMENT_SCORE": round(engagement, 1) if engagement is not None else None,
        "COMMERCIAL_INTENT_SCORE": None,
        "LOW_SATURATION_SCORE": None,
        "NEXUS_RELEVANCE_SCORE": relevance,
        "AUDIENCE_CLARITY_SCORE": None,
        "MONETIZATION_MATCH_SCORE": None,
        "SOURCE_CONFIDENCE_SCORE": 95 if signal.get("url") else 20,
        "TIMELINESS_SCORE": 90 if metrics.get("age_days") is not None and metrics["age_days"] <= 7 else 55,
    }
    observed = [x for x in scores.values() if isinstance(x, (int, float))]
    virality = round(sum(observed) / len(observed), 1) if observed else None
    commercial_inputs = [scores["NEXUS_RELEVANCE_SCORE"], scores["SOURCE_CONFIDENCE_SCORE"]]
    commercial = round(sum(commercial_inputs) / len(commercial_inputs), 1)
    opportunity = round((virality or 0) * 0.35 + commercial * 0.25 + (scores["TIMELINESS_SCORE"] or 0) * 0.2, 1)
    return {"components": scores, "virality_score": virality, "commercial_score": commercial, "opportunity_score": opportunity}


def _notebook(topic: str, video: dict[str, Any]) -> str | None:
    title = f"Pulse Trend Intelligence — {topic[:80]}"
    rows = _rows("research_notebooks", f"select=id,title&title=eq.{sb.q(title)}&owner_department=eq.PULSE&limit=1")
    if rows:
        return rows[0]["id"]
    code, created = sb.insert("research_notebooks", {"title": title,
        "description": "Trend evidence and commercial interpretation owned by PULSE. Facts, derivations, and AI inferences remain separated.",
        "owner_department": "PULSE", "status": "active"}, prefer="return=representation")
    return created[0].get("id") if code in (200, 201) and created else None


def _topic_for(video: dict[str, Any]) -> str:
    return str(video.get("query_used") or video.get("category") or "Internet trend").strip()


def _evidence_terms(text: str) -> set[str]:
    common = {"this", "that", "with", "from", "your", "what", "when", "where", "will", "have", "make", "made",
              "help", "helping", "more", "most", "best", "ways", "way", "video", "youtube", "today", "month",
              "months", "days", "week", "weeks", "year", "years", "small", "business", "businesses", "viral",
              "trend", "trending", "news", "live", "just", "about", "into", "over", "under", "from", "with", "how"}
    return {word for word in re.findall(r"[a-z0-9]+", text.lower()) if len(word) > 3 and word not in common and not word.isdigit()}


def _snapshot_delta(trend_id: str, views: Any, observed_at: dt.datetime) -> dict[str, Any]:
    previous = _rows("trend_history_bank", f"select=observed_at,views,observed_data&trend_id=eq.{trend_id}&order=observed_at.desc&limit=1")
    if not previous or not isinstance(views, (int, float)) or not isinstance(previous[0].get("views"), (int, float)):
        return {"view_growth": None, "interval_views_per_hour": None, "acceleration": None}
    try:
        previous_at = dt.datetime.fromisoformat(str(previous[0]["observed_at"]).replace("Z", "+00:00"))
        hours = (observed_at - previous_at).total_seconds() / 3600
    except (KeyError, ValueError, TypeError):
        return {"view_growth": None, "interval_views_per_hour": None, "acceleration": None}
    if hours <= 0:
        return {"view_growth": None, "interval_views_per_hour": None, "acceleration": None}
    old_views = float(previous[0]["views"])
    growth = float(views) - old_views
    interval_rate = growth / hours
    prior_rate = (previous[0].get("observed_data") or {}).get("interval_views_per_hour")
    acceleration = (interval_rate - float(prior_rate)) / hours if isinstance(prior_rate, (int, float)) else None
    return {"view_growth": growth / old_views * 100 if old_views > 0 else None,
            "interval_views_per_hour": interval_rate, "acceleration": acceleration}


def normalize_and_persist(videos: list[dict[str, Any]], rss: list[dict[str, Any]], run_id: str) -> dict[str, Any]:
    count = 0; notebooks = []; trend_ids = []; history_written = 0; bank_written = 0
    all_text = [f"{x.get('title','')} {x.get('description','')}".lower() for x in rss]
    for video in videos:
        url = str(video.get("url") or "")
        if not url.startswith("https://www.youtube.com/watch?v="):
            continue
        topic = _topic_for(video)
        title_terms = _evidence_terms(str(video.get("title") or ""))
        matching = []
        for candidate in rss:
            text = str(candidate.get("title", "")).lower() + " " + str(candidate.get("description", "")).lower()
            overlap = title_terms.intersection(_evidence_terms(text))
            if len(overlap) >= 2:
                matching.append(candidate)
        source_count = 1 + len({row.get("platform") for row in matching})
        score = _score(video, source_count)
        observed_at = now()
        trend_id = _id("trend_", topic.lower() + "|" + str(video.get("video_id")))
        cluster_id = _id("cluster_", re.sub(r"\s+", " ", topic.lower()).strip())
        delta = _snapshot_delta(trend_id, video.get("views"), observed_at)
        if delta["interval_views_per_hour"] is not None:
            score["components"]["VELOCITY_SCORE"] = round(min(100, math.log10(max(1, delta["interval_views_per_hour"]) + 1) * 16.5), 1)
        if delta["acceleration"] is not None:
            score["components"]["ACCELERATION_SCORE"] = round(max(0, min(100, 50 + math.copysign(math.log10(abs(delta["acceleration"]) + 1) * 12, delta["acceleration"]))), 1)
        component_values = [x for x in score["components"].values() if isinstance(x, (int, float))]
        score["virality_score"] = round(sum(component_values) / len(component_values), 1) if component_values else None
        score["opportunity_score"] = round((score["virality_score"] or 0) * 0.35 + score["commercial_score"] * 0.25 +
                                            (score["components"]["TIMELINESS_SCORE"] or 0) * 0.2, 1)
        row_velocity = delta["interval_views_per_hour"] if delta["interval_views_per_hour"] is not None else (video.get("metrics") or {}).get("views_per_hour")
        # Platform metrics are verified source observations; a trend claim still needs corroboration.
        state = "VERIFIED" if matching else "WATCHING"
        status = "VERIFIED" if matching else "VERIFICATION_REQUIRED"
        notebook_id = _notebook(topic, video)
        notebooks.append(notebook_id)
        published = video.get("published_at")
        row = {
            "trend_id": trend_id, "cluster_id": cluster_id, "source": "YOUTUBE", "source_url": url, "platform": "YOUTUBE",
            "topic": topic, "keyword": topic, "title": video.get("title"), "creator": video.get("channel"),
            "published_at": published, "current_views": video.get("views"), "current_likes": video.get("likes"),
            "current_comments": video.get("comments"), "view_growth": delta["view_growth"],
            "velocity": row_velocity,
            "acceleration": delta["acceleration"],
            "cross_platform_count": source_count, "region": "US", "audience": None, "audience_intent": None,
            "confidence": 0.8 if matching else 0.55, "source_quality": "PRIMARY_PLATFORM_DATA",
            "trend_class": "FLASH_TREND" if (video.get("metrics") or {}).get("age_days") is not None and video["metrics"]["age_days"] <= 3 else "SHORT_TREND",
            "expected_half_life": "HOURS_TO_DAYS" if (video.get("metrics") or {}).get("age_days", 99) <= 3 else "DAYS_TO_WEEKS",
            "urgency": "HIGH" if (video.get("metrics") or {}).get("views_per_day", 0) > 10000 else "NORMAL",
            "recheck_interval_seconds": 7200, "component_scores": score["components"],
            "observed_data": {"video": video, "matching_public_news": matching, "verification": state},
            "derived_values": {"views_per_hour": row_velocity,
                               "views_per_day": (video.get("metrics") or {}).get("views_per_day"), **delta, **score},
            "ai_inferences": {"audience_hypothesis": None, "commercial_relevance_hypothesis": "BUSINESS_TOPIC" if score["components"]["NEXUS_RELEVANCE_SCORE"] >= 80 else "GENERAL_INTEREST"},
            "status": status, "route": "WATCH", "last_observed_at": iso(observed_at), "updated_at": iso(observed_at),
        }
        ok, _ = _upsert("pulse_trends", "trend_id", row)
        if not ok:
            continue
        if not matching:
            # A weaker re-check withdraws readiness without deleting the record.
            campaigns = _rows("pulse_campaign_briefs", f"select=campaign_id,state&trend_id=eq.{trend_id}")
            for campaign in campaigns:
                sb.update("pulse_campaign_briefs", f"campaign_id=eq.{campaign['campaign_id']}", {
                    "state": "BLOCKED_BY_EVIDENCE", "publish_state": "NOT_PUBLISHED", "updated_at": iso()})
                handoff_id = _id("pulse_handoff_", campaign["campaign_id"])
                sb.update("pulse_handoffs", f"handoff_id=eq.{handoff_id}", {
                    "summary": f"Unverified trend claim held from Marketing: {row.get('title') or row.get('topic')}.",
                    "what_was_completed": ["platform source metadata recorded", "independent evidence check did not support a promotion"],
                    "status": "BLOCKED", "what_remains": ["obtain a relevant independent source with multi-term support", "recalculate trend readiness"], "updated_at": iso()})
        hist_id = _id("snap_", trend_id + "|" + iso(observed_at))
        hrow = {"snapshot_id": hist_id, "trend_id": trend_id, "observed_at": iso(observed_at), "views": video.get("views"),
                "likes": video.get("likes"), "comments": video.get("comments"), "view_growth": delta["view_growth"],
                "velocity": row.get("velocity"), "acceleration": delta["acceleration"],
                "platform_count": source_count, "status": status, "commercial_score": score["commercial_score"],
                "opportunity_score": score["opportunity_score"], "source_quality": row["source_quality"],
                "observed_data": {"source_url": url, "run_id": run_id, "verified_observation": "PLATFORM_METADATA",
                                  "interval_views_per_hour": delta["interval_views_per_hour"]}}
        history_ok, _ = _upsert("trend_history_bank", "snapshot_id", hrow)
        history_written += int(history_ok)
        bank_ok, _ = _upsert("pulse_shared_intelligence_bank", "bank_name,record_id", {"bank_name": "TREND_INTELLIGENCE_BANK", "record_id": trend_id,
            "trend_id": trend_id, "evidence_state": "CROSS_SUPPORTED" if matching else "SOURCE_CLAIM", "confidence": row["confidence"],
            "payload": {"trend": row, "run_id": run_id}})
        bank_written += int(bank_ok)
        # Link the collected platform source into this persistent trend notebook.
        src = _rows("research_sources", f"select=id&url=eq.{sb.q(url)}&limit=1")
        if src and notebook_id:
            sb.update("research_sources", f"id=eq.{sb.q(src[0]['id'])}", {"notebook_id": notebook_id})
        count += 1; trend_ids.append(trend_id)
    return {"trends_persisted": count, "history_snapshots_readback": history_written,
            "trend_bank_readback": bank_written, "trend_ids": trend_ids,
            "cluster_ids": sorted({_id("cluster_", re.sub(r"\s+", " ", _topic_for(v).lower()).strip()) for v in videos if v.get("url")}),
            "notebook_ids": sorted(set(x for x in notebooks if x))}


def _store_rss(items: list[dict[str, Any]], notebook_id: str | None = None) -> int:
    from nexus_agent_platform.content_intelligence import _source_lookup_many, persist_signals_batch
    candidates = []
    for row in items:
        identity = f"pulse-rss:{row['source']}:{row['url']}"
        quality = "OFFICIAL_TREND_SOURCE" if row["source"] == "GOOGLE_TRENDS" else (
            "HIGH_VALUE_SECONDARY" if any(org in str(row.get("publisher", "")).lower() for org in ("reuters", "associated press", "ap news", "bloomberg", "wall street journal", "financial times", "cnbc")) else "DISCOVERY_ONLY")
        payload = {**row, "source_quality": quality}
        candidates.append((row["title"], identity, row["url"], row.get("publisher") or row["source"], payload))
    existing = _source_lookup_many([candidate[1] for candidate in candidates])
    result = persist_signals_batch("PULSE_PUBLIC_TREND_SOURCE", candidates, existing_by_identity=existing)
    if notebook_id:
        # No current scheduler caller supplies a notebook. Preserve the prior
        # optional behavior for explicit callers without adding a per-item
        # readback to the normal collection path.
        for value in result.get("by_identity", {}).values():
            if value.get("readback") and value.get("source_id"):
                sb.update("research_sources", f"id=eq.{sb.q(value['source_id'])}", {"notebook_id": notebook_id})
    return sum(bool(value.get("readback")) for value in result.get("by_identity", {}).values())


def _make_campaign(trend: dict[str, Any]) -> dict[str, Any] | None:
    evidence = trend.get("observed_data") or {}
    video = evidence.get("video") or {}
    if not video.get("url") or trend.get("status") != "VERIFIED":
        return None
    cid = _id("pulse_campaign_", trend["trend_id"])
    observation = evidence.get("verification_basis") or "Live platform observations are recorded separately from inference."
    independent_sources = evidence.get("sources") or evidence.get("matching_public_news", [])
    brief = {
        "trend": trend.get("title"), "trend_id": trend["trend_id"], "trend_notebook_id": trend.get("notebook_id"),
        "audience": trend.get("audience") or "Research required; source metrics do not establish audience demographics.",
        "why_now": observation,
        "trend_class": trend.get("trend_class"), "expected_half_life": trend.get("expected_half_life"),
        "primary_hook": trend.get("title"), "secondary_hooks": [], "emotional_driver": "RESEARCH_REQUIRED",
        "curiosity_driver": "RESEARCH_REQUIRED", "offer_match": "UNVERIFIED", "affiliate_match": "UNVERIFIED",
        "product_match": "UNVERIFIED", "merch_match": "UNVERIFIED", "content_format": "SHORT_FORM_VIDEO",
        "channel": "YOUTUBE_SHORTS_OR_TIKTOK_REVIEW_REQUIRED", "cta": "No CTA selected; Marketing review required.",
        "time_window": trend.get("expected_half_life"), "risks": [
            "trend coverage and source-reported metrics do not prove commercial demand",
            "verify audio and platform usage rights before any production use",
        ],
        "source_evidence": {"video_url": video.get("url"), "views": video.get("views"), "published_at": video.get("published_at"),
                            "sources": independent_sources, "verification_basis": observation,
                            "platform_metrics_status": video.get("platform_metrics_status", "OBSERVED_IN_SOURCE")},
        "publish": False, "ray_approval_required": True,
    }
    ok, _ = _upsert("pulse_campaign_briefs", "campaign_id", {"campaign_id": cid, "trend_id": trend["trend_id"],
        "campaign_type": "RAPID_CAMPAIGN", "state": "READY_FOR_MARKETING_REVIEW", "brief": brief,
        "publish_state": "NOT_PUBLISHED", "ray_approval_required": True, "updated_at": iso()})
    if not ok: return None
    handoff_id = _id("pulse_handoff_", cid)
    hrow = {"handoff_id": handoff_id, "trend_id": trend["trend_id"], "to_department": "MARKETING", "case_id": cid,
        "notebook_id": trend.get("notebook_id"), "summary": f"Evidence-backed trend brief for Marketing review: {trend.get('title') or trend.get('topic')}.",
        "structured_data": brief, "what_was_completed": ["trend source references recorded", "trend snapshot and score persisted"],
        "what_remains": ["verify platform metrics and current velocity where available", "validate audience and commercial fit",
                          "verify audio and platform usage rights", "obtain Ray approval before external publication"],
        "recommendation": "Review as a rapid campaign candidate; no publication authorized.", "action": "MARKETING_REVIEW",
        "expected_output": "Marketing campaign decision packet", "status": "CREATED", "updated_at": iso()}
    h_ok, _ = _upsert("pulse_handoffs", "handoff_id", hrow)
    if not h_ok: return None
    from nexus_agent_platform.durable_jobs import default_store
    downstream=default_store().enqueue("MARKETING","PULSE_HANDOFF",payload_ref=handoff_id,
        parent_job_id=os.environ.get("NEXUS_DURABLE_JOB_ID") or None,
        correlation_id=os.environ.get("NEXUS_JOB_CORRELATION_ID") or cid,
        idempotency_key="workflow:"+hashlib.sha256(("pulse-handoff:"+handoff_id).encode()).hexdigest())
    _upsert("pulse_shared_intelligence_bank", "bank_name,record_id", {"bank_name": "TREND_CAMPAIGN_RESULT_BANK", "record_id": cid,
        "trend_id": trend["trend_id"], "evidence_state": "CROSS_SUPPORTED", "confidence": trend.get("confidence"),
        "payload": {"campaign_id": cid, "publish_state": "NOT_PUBLISHED", "handoff_id": handoff_id}})
    return {"campaign_id": cid, "handoff_id": handoff_id, "downstream_job_id":downstream.job_id,"state": "READY_FOR_MARKETING_REVIEW"}


def handoff_once(handoff_id: str) -> dict[str, Any]:
    """Read back one exact Pulse handoff referenced by a durable job."""
    rows=_rows("pulse_handoffs",f"select=handoff_id,to_department,status&handoff_id=eq.{urllib.parse.quote(str(handoff_id),safe='')}&limit=1")
    if not rows: raise ValueError("PULSE_HANDOFF_NOT_FOUND")
    row=rows[0]
    if row.get("to_department")!="MARKETING" or row.get("status")!="CREATED": raise ValueError("PULSE_HANDOFF_STATE_INVALID")
    return {"status":"HANDOFF_DELIVERED","handoff_id":handoff_id,"to_department":"MARKETING","workflow_status":row.get("status")}


def _record_commercial_assessment(trend: dict[str, Any]) -> int:
    """Persist explicit match assessments without inventing offers or products."""
    trend_id = str(trend.get("trend_id") or "")
    if not trend_id:
        return 0
    assessments = [
        ("TREND_TO_REVENUE_BANK", "BUSINESS_OPPORTUNITY_MATCH", "RESEARCH_REQUIRED",
         "Demand, audience, and unit economics are not established by discovery signals."),
        ("AFFILIATE_OPPORTUNITY_BANK", "AFFILIATE_MATCH", "UNVERIFIED",
         "No official affiliate program source has been verified for this trend."),
        ("PRODUCT_TREND_BANK", "PRODUCT_MATCH", "UNVERIFIED",
         "No verified product catalog match has been established."),
        ("MERCHANDISE_OPPORTUNITY_BANK", "MERCH_MATCH", "RESEARCH_REQUIRED",
         "Audience identity, portability, lifespan, saturation, and IP clearance need review."),
    ]
    persisted = 0
    for bank, match_type, state, reason in assessments:
        record_id = f"{trend_id}:{match_type}"
        ok, _ = _upsert("pulse_shared_intelligence_bank", "bank_name,record_id", {
            "bank_name": bank, "record_id": record_id, "trend_id": trend_id,
            "evidence_state": state, "confidence": 0,
            "payload": {"match_type": match_type, "match_status": state, "matched": False,
                        "why_it_matches": None, "source": None, "estimated_effort": None,
                        "estimated_speed_to_market": None, "requires_spend": None,
                        "license_or_policy_risk": "UNASSESSED", "confidence": 0,
                        "next_evidence": reason, "created_by": "PULSE_RULED_ASSESSMENT"},
            "updated_at": iso(),
        })
        persisted += int(ok)
    return persisted


def _flash_scan(run_id: str) -> dict[str, Any]:
    topics = ["viral small business", "AI automation", "small business marketing", "business funding"]
    videos = _video_signals(topics, 2)
    rss = _search_feeds(topics)
    rss_count = _store_rss(rss)
    persisted = normalize_and_persist(videos, rss, run_id)
    tested_at = iso()
    for name, fields, count in [
        ("YOUTUBE", ["url", "title", "creator", "published_at", "views", "likes", "comments"], len(videos)),
        ("GOOGLE_NEWS", ["title", "url", "published_at", "publisher"], len(rss)),
    ]:
        _upsert("pulse_provider_registry", "provider_name", {"provider_name": name,
            "source_type": "VIDEO_PLATFORM" if name == "YOUTUBE" else "NEWS_RSS", "free_or_paid": "FREE",
            "auth_required": False, "automation_mode": "EXISTING_NEXUS_COLLECTOR",
            "data_fields": fields, "current_status": "PASS" if count else "DEGRADED", "nexus_tested": True,
            "reliability": "HIGH" if count else "RETRY_REQUIRED",
            "commercial_use_notes": f"Latest scheduled canary persisted {count} public source observations.",
            "terms_risk": "LOW", "last_tested_at": tested_at, "updated_at": tested_at})
    trends = _rows("pulse_trends", "select=trend_id,notebook_id,status,title,topic,expected_half_life,trend_class,audience,confidence,observed_data&order=last_observed_at.desc&limit=50")
    commercial_assessments = sum(_record_commercial_assessment(trend) for trend in trends)
    campaigns = []
    for trend in trends:
        result = _make_campaign(trend)
        if result: campaigns.append(result)
        if len(campaigns) >= 1: break
    sb.health("PULSE_SOURCE_HEALTH", "PASS" if videos or rss else "DEGRADED",
              f"Public discovery read {len(videos)} YouTube and {len(rss)} RSS signals; recovery=PULSE_SOURCE_RECOVERY when empty.")
    sb.health("TREND_DISCOVERY", "PASS" if videos or rss else "DEGRADED",
              f"Discovery sources={len(videos) + len(rss)}; recovery=PULSE_SOURCE_RECOVERY when unavailable.")
    sb.health("TREND_NORMALIZATION", "PASS" if persisted["trends_persisted"] else "DEGRADED",
              f"Normalized trend readbacks={persisted['trends_persisted']}; recovery=PULSE_SOURCE_RECOVERY when none persist.")
    sb.health("TREND_CLUSTERING", "PASS" if persisted.get("cluster_ids") else "DEGRADED",
              f"Deterministic topic clusters={len(persisted.get('cluster_ids', []))}; recovery=PULSE_VERIFICATION_RECOVERY when clustering is empty.")
    verified = sum(1 for trend in trends if trend.get("status") == "VERIFIED")
    sb.health("TREND_VERIFICATION", "PASS" if verified else "DEGRADED",
              f"Evidence-supported trend records={verified}; unresolved claims stay in WATCH; recovery=PULSE_VERIFICATION_RECOVERY.")
    sb.health("TREND_SCORING", "PASS" if persisted["trends_persisted"] else "DEGRADED",
              "Component scores preserve unavailable growth fields as null; recovery=PULSE_VERIFICATION_RECOVERY.")
    sb.health("TREND_HISTORY", "PASS" if persisted.get("history_snapshots_readback", 0) == persisted["trends_persisted"] else "DEGRADED",
              f"Snapshot readbacks={persisted.get('history_snapshots_readback', 0)}; recovery=PULSE_HISTORY_RECOVERY.")
    sb.health("TREND_NOTEBOOK", "PASS" if persisted.get("notebook_ids") else "DEGRADED",
              f"Pulse notebook references={len(persisted.get('notebook_ids', []))}; recovery=PULSE_NOTEBOOK_RECOVERY.")
    sb.health("COMMERCIAL_MATCH", "PASS" if commercial_assessments else "DEGRADED",
              f"Explicit verified/unverified match assessments persisted={commercial_assessments}; no offer is inferred.")
    return {"sources_discovered": len(videos) + len(rss), "sources_processed": len(videos) + rss_count,
            **persisted, "rss_sources_persisted": rss_count, "campaigns": campaigns,
            "commercial_assessments_persisted": commercial_assessments,
            "status": "COMPLETED" if persisted["trends_persisted"] else "NO_MATERIAL_TREND_CHANGE"}


def _general_scan(run_id: str) -> dict[str, Any]:
    from nexus_agent_platform.content_intelligence import trend_signals
    topics = ["business funding", "small business credit", "AI automation", "small business marketing", "online business"]
    searches = trend_signals(topics, max_per_topic=5)
    rss = _search_feeds(topics)
    written = _store_rss(rss)
    return {"sources_discovered": searches.get("related_queries_found", 0) + len(rss), "sources_processed": written,
            "related_query_count": searches.get("related_queries_found", 0), "rss_sources_persisted": written,
            "status": "COMPLETED" if written or searches.get("readback") else "NO_MATERIAL_TREND_CHANGE", "run_id": run_id}


def _deep_review(run_id: str) -> dict[str, Any]:
    videos = _rows("research_sources", "select=id,title,url,metadata&source_type=eq.YOUTUBE_CONTENT_SIGNAL&order=created_at.desc&limit=100")
    news = _rows("research_sources", "select=id,title,url,metadata&source_type=eq.PULSE_PUBLIC_TREND_SOURCE&order=created_at.desc&limit=100")
    updated = 0; matching = 0
    for video in videos:
        raw = ((video.get("metadata") or {}).get("raw_signal") or {})
        topic_words = _evidence_terms(str(raw.get("title") or video.get("title") or ""))
        related_news = [x for x in news if len(topic_words.intersection(_evidence_terms(
            str(x.get("title") or "") + " " + str((x.get("metadata") or {}).get("raw_signal", {}).get("description") or "")))) >= 2]
        if not related_news:
            continue
        matching += 1
        vid = raw.get("video_id")
        matches = _rows("pulse_trends", f"select=trend_id,observed_data,component_scores&source_url=eq.{sb.q('https://www.youtube.com/watch?v='+str(vid))}&limit=1")
        if matches:
            observed = matches[0].get("observed_data") or {}; observed["matching_public_news"] = [{"title":x.get("title"),"url":x.get("url")} for x in related_news[:4]]
            sb.update("pulse_trends", f"trend_id=eq.{matches[0]['trend_id']}", {"observed_data": observed,"cross_platform_count": 2,"status":"VERIFIED","updated_at":iso()})
            updated += 1
    return {"sources_discovered": len(videos)+len(news), "sources_processed": len(videos)+len(news), "trends_updated": updated,
            "cross_source_topic_matches": matching, "status": "COMPLETED" if updated else "NO_MATERIAL_TREND_CHANGE", "run_id": run_id}


def _decay_review(run_id: str) -> dict[str, Any]:
    rows = _rows("pulse_trends", "select=trend_id,status,trend_class,last_observed_at&status=not.in.(STALE,EXPIRED,REJECTED_BY_EVIDENCE)&limit=500")
    stamp = now(); stale = expired = 0
    for row in rows:
        try: age = stamp - dt.datetime.fromisoformat(str(row["last_observed_at"]).replace("Z", "+00:00"))
        except (KeyError, ValueError): continue
        limit = dt.timedelta(days=7 if row.get("trend_class") == "FLASH_TREND" else 30)
        if age > limit * 2:
            sb.update("pulse_trends", f"trend_id=eq.{row['trend_id']}", {"status":"EXPIRED","updated_at":iso()}); expired += 1
        elif age > limit:
            sb.update("pulse_trends", f"trend_id=eq.{row['trend_id']}", {"status":"STALE","updated_at":iso()}); stale += 1
    return {"sources_discovered":len(rows),"sources_processed":len(rows),"stale_count":stale,"expired_count":expired,
            "status":"COMPLETED" if stale or expired else "NO_MATERIAL_TREND_CHANGE","run_id":run_id}


def _commerce_refresh(run_id: str) -> dict[str, Any]:
    import ssl
    try:
        import certifi
        ctx=ssl.create_default_context(cafile=certifi.where())
    except ImportError: ctx=ssl.create_default_context()
    result={"shops":"BLOCKED_BY_AUTH","blueprints":0,"providers":0,"variants":"NOT_TESTED","products_created":False,"orders_placed":False}
    p=subprocess.run(["security","find-generic-password","-a",os.environ.get("USER",""),"-s","nexus.printify.api_token","-w"],capture_output=True,text=True,timeout=10)
    token=p.stdout.strip() if p.returncode==0 else ""
    def read(path: str, auth: bool=True):
        headers={"User-Agent":"NexusOS/1.0", "Accept":"application/json"}
        if auth and token: headers["Authorization"]="Bearer "+token
        try:
            def fetch():
                req=urllib.request.Request("https://api.printify.com/v1/"+path,headers=headers)
                with urllib.request.urlopen(req,timeout=30,context=ctx) as r:return r.status,json.loads(r.read(2_000_000).decode())
            from nexus_agent_platform.provider_enforcement import execute_public_read
            return execute_public_read("PRINTIFY", "pulse_catalog_read", fetch, response_bytes=2_000_000)
        except urllib.error.HTTPError as e:return e.code,{}
        except Exception:return 0,{}
    hs,shops=read("shops.json")
    bstatus,blueprints=read("catalog/blueprints.json",auth=False)
    provstatus,providers=read("catalog/print_providers.json",auth=False)
    result.update({"token_present":bool(token),"auth":"PASS" if hs==200 else "BLOCKED_BY_AUTH" if hs==401 else "CHECK_ERROR",
                   "shops":"PASS" if hs==200 else "BLOCKED_BY_AUTH" if hs==401 else "CHECK_ERROR",
                   "shops_list":shops if hs==200 else [],"blueprints":len(blueprints) if bstatus==200 and isinstance(blueprints,list) else 0,
                   "providers":len(providers) if provstatus==200 and isinstance(providers,list) else 0,
                   "catalog_status":"PASS" if bstatus==200 and provstatus==200 else "DEGRADED",
                   "providers_status":"PASS" if provstatus==200 else "DEGRADED","run_id":run_id})
    if bstatus==200 and isinstance(blueprints,list):
        for needle in ("tee","hoodie","mug","poster","hat","sticker","tote"):
            matches=[x for x in blueprints if needle in str(x.get("title","")).lower()]
            if matches:
                bp=matches[0]; pid=bp.get("id")
                ps,plist=read(f"catalog/blueprints/{pid}/print_providers.json",auth=False)
                if ps==200 and plist:
                    provider=plist[0].get("id")
                    vs,variants=read(f"catalog/blueprints/{pid}/print_providers/{provider}/variants.json",auth=False)
                    result.setdefault("catalog_matches",[]).append({"product_type":needle,"blueprint_id":pid,
                        "blueprint_title":bp.get("title"),"provider_id":provider,"variants_read":"PASS" if vs==200 else "NO",
                        "variant_count":len(variants.get("variants",[])) if isinstance(variants,dict) else len(variants) if isinstance(variants,list) else 0})
                else:
                    result.setdefault("catalog_matches",[]).append({"product_type":needle,"blueprint_id":pid,
                        "blueprint_title":bp.get("title"),"providers_read":"BLOCKED_BY_AUTH" if ps==401 else "CHECK_ERROR",
                        "variants_read":"BLOCKED_BY_AUTH" if ps==401 else "NOT_TESTED","variant_count":0})
                break
    match_rows = result.get("catalog_matches", [])
    result["blueprints_status"] = "PASS" if bstatus == 200 and isinstance(blueprints, list) else "CHECK_ERROR"
    result["global_print_providers_status"] = "PASS" if provstatus == 200 and isinstance(providers, list) else "CHECK_ERROR"
    result["variants_status"] = next((x.get("variants_read") for x in match_rows), "NOT_TESTED")
    if match_rows and result["variants_status"] != "PASS":
        result["catalog_status"] = "DEGRADED"
    result["status"] = "COMPLETED" if hs == 200 and result["variants_status"] == "PASS" else "DEGRADED"
    result["next_workflow"] = "PRINTIFY_AUTH_RECOVERY" if hs == 401 else "PRINTIFY_CATALOG_RECOVERY" if result["variants_status"] != "PASS" else None
    if hs==200 and isinstance(shops,list):
        for shop in shops:
            sid=str(shop.get("id"))
            _upsert("pulse_printify_shops","shop_id",{"shop_id":sid,"shop_title":shop.get("title"),"sales_channel":shop.get("sales_channel"),
                "store_status":"CONNECTED" if shop.get("sales_channel") not in (None,"disconnected") else "DISCONNECTED",
                "connection_status":"PASS","popup_store":"pop" in str(shop.get("sales_channel","")).lower(),"last_tested_at":iso(),
                "safe_metadata":{"persisted_fields":["id","title","sales_channel"]}})
    # Provider metadata is safe; no token or auth response is retained.
    for name,source,status,count in [("PRINTIFY_CATALOG","MERCH_CATALOG",result.get("catalog_status"),result.get("blueprints")),
                                     ("PRINTIFY_SHOPS","MERCH_STORE",result.get("auth"),len(result.get("shops_list",[])))]:
        row={"provider_name":name,"source_type":source,"free_or_paid":"FREE","auth_required":name=="PRINTIFY_SHOPS",
             "automation_mode":"PUBLIC_API_READ_ONLY","data_fields":["blueprints","providers","variants"] if name=="PRINTIFY_CATALOG" else ["shop_id","title","sales_channel"],
             "current_status":status,"nexus_tested":True,"reliability":"HIGH" if status=="PASS" else "BLOCKED",
             "commercial_use_notes":f"Read-only canary observed {count} catalog/store records; no products or orders created.","terms_risk":"LOW","last_tested_at":iso()}
        _upsert("pulse_provider_registry","provider_name",row)
    for component, state, recovery in [
        ("PRINTIFY_AUTH", "PASS" if hs == 200 else "BLOCKED_BY_AUTH" if hs == 401 else "CHECK_ERROR", "PRINTIFY_AUTH_RECOVERY"),
        ("PRINTIFY_CONNECTIVITY", "PASS" if bstatus == 200 else "UNREACHABLE", "PRINTIFY_API_RECOVERY"),
        ("PRINTIFY_SHOP_ACCESS", "PASS" if hs == 200 else "BLOCKED_BY_AUTH" if hs == 401 else "CHECK_ERROR", "PRINTIFY_AUTH_RECOVERY"),
        ("PRINTIFY_CATALOG_ACCESS", "PASS" if bstatus == 200 and provstatus == 200 else "UNREACHABLE", "PRINTIFY_CATALOG_RECOVERY"),
    ]:
        sb.health(component, state, f"Read-only Printify check state={state}; recovery={recovery}; no product/order writes performed.")
    return result


def _run_job(job_id: str, run_id: str) -> dict[str, Any]:
    if job_id == "PULSE_FLASH_SCAN": return _flash_scan(run_id)
    if job_id == "PULSE_GENERAL_SCAN": return _general_scan(run_id)
    if job_id == "PULSE_DAILY_DEEP_REVIEW": return _deep_review(run_id)
    if job_id == "PULSE_DECAY_REVIEW": return _decay_review(run_id)
    if job_id == "PULSE_COMMERCE_REFRESH": return _commerce_refresh(run_id)
    return {"status":"BLOCKED","error":"UNREGISTERED_PULSE_JOB"}


def tick(*, force_job: str | None = None, max_jobs: int = 1) -> dict[str, Any]:
    boot=bootstrap()
    if boot.get("status")=="SUPABASE_WRITE_FAILED": return boot
    schedules=_rows("pulse_schedule_registry","select=job_id,cadence_seconds,enabled,next_run_at,last_success_at,last_status&enabled=eq.true&order=next_run_at.asc&limit=10")
    current=now()
    due=[x for x in schedules if force_job==x.get("job_id") or (force_job is None and x.get("next_run_at") and dt.datetime.fromisoformat(str(x["next_run_at"]).replace("Z","+00:00"))<=current)]
    try:
        from nexus_agent_platform.supabase_egress_guard import safe_mode_enabled
        safe_mode = safe_mode_enabled()
    except Exception:
        safe_mode = False
    if safe_mode:
        deferred={"PULSE_DAILY_DEEP_REVIEW","PULSE_DECAY_REVIEW","PULSE_COMMERCE_REFRESH"}
        due=[x for x in due if x.get("job_id") not in deferred]
        if not due:
            # Do not advance next_run_at: deferred jobs remain due for recovery.
            return {"status":"DEFERRED_SAFE_MODE","schedule_configured":len(schedules)==len(PULSE_JOBS),"due_jobs":0,"run_receipts":[]}
    if not due:
        sb.health("PULSE_SCHEDULER", "IDLE_HEALTHY", "Pulse due-time registry is active in the existing Nexus continuous daemon.")
        return {"status":"IDLE_HEALTHY","schedule_configured":len(schedules)==len(PULSE_JOBS),"due_jobs":0,"run_receipts":[]}
    receipts=[]
    for schedule in due[:max_jobs]:
        job=schedule["job_id"]; runid=_id("pulse_run_",job+iso()+str(os.getpid())); started=iso()
        sb.update("pulse_schedule_registry",f"job_id=eq.{job}",{"last_started_at":started,"last_status":"RUNNING","updated_at":started})
        try: result=_run_job(job,runid)
        except Exception as exc: result={"status":"FAILED_RETRYABLE","error":type(exc).__name__}
        finished=iso(); state=result.get("status","FAILED_RETRYABLE")
        cadence=int(schedule.get("cadence_seconds") or PULSE_JOBS[job])
        next_run=iso(now()+dt.timedelta(seconds=cadence))
        sb.update("pulse_schedule_registry",f"job_id=eq.{job}",{"last_success_at":finished if state in {"COMPLETED","NO_MATERIAL_TREND_CHANGE"} else schedule.get("last_success_at"),
            "next_run_at":next_run,"last_status":state,"last_result":result,"updated_at":finished})
        receipt={"run_id":runid,"job_id":job,"started_at":started,"completed_at":finished,"status":state,
            "sources_discovered":int(result.get("sources_discovered",0)),"sources_processed":int(result.get("sources_processed",0)),
            "trends_updated":int(result.get("trends_persisted",result.get("trends_updated",0))),"handoffs_created":len(result.get("campaigns",[])),"details":result}
        ok,_=_upsert("pulse_run_receipts","run_id",receipt)
        _,readback=sb.get("pulse_run_receipts",f"select=run_id,status&run_id=eq.{runid}&limit=1")
        sb.health(job, "PASS" if state in {"COMPLETED","NO_MATERIAL_TREND_CHANGE"} and ok and bool(readback) else "DEGRADED",
                  f"Scheduled Pulse job result: {state}; receipt readback={'PASS' if ok and bool(readback) else 'FAIL'}.")
        receipts.append({"job_id":job,"status":state,"receipt_readback":ok and bool(readback),"result":result})
    return {"status":"PASS" if all(x["status"] in {"COMPLETED","NO_MATERIAL_TREND_CHANGE"} and x["receipt_readback"] for x in receipts) else "DEGRADED",
            "schedule_configured":len(schedules)==len(PULSE_JOBS),"due_jobs":len(due),"run_receipts":receipts}


def status() -> dict[str, Any]:
    schedules=_rows("pulse_schedule_registry","select=job_id,cadence_seconds,enabled,next_run_at,last_success_at,last_status&order=next_run_at.asc&limit=10")
    trends=_rows("pulse_trends","select=trend_id,status,updated_at,route&order=updated_at.desc&limit=100")
    runs=_rows("pulse_run_receipts","select=run_id,job_id,status,completed_at&order=completed_at.desc&limit=50")
    return {"department":"TREND_AND_MARKET_INTELLIGENCE","alias":"PULSE","schedule_configured":len(schedules)==len(PULSE_JOBS),
            "schedules":schedules,"trend_count":len(trends),"recent_trends":trends[:20],"recent_runs":runs[:10],
            "handoff_count":len(_rows("pulse_handoffs","select=handoff_id&order=updated_at.desc&limit=100")),"live_publishing_enabled":False}


if __name__ == "__main__":
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument("command",choices=("tick","status","handoff-once"),default="tick",nargs="?");parser.add_argument("--force-job",choices=tuple(PULSE_JOBS));parser.add_argument("--handoff-id")
    args=parser.parse_args()
    if args.command=="tick":result=tick(force_job=args.force_job)
    elif args.command=="handoff-once":result=handoff_once(args.handoff_id or "")
    else:result=status()
    print(_json(result))
