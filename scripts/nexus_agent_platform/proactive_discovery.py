"""Deterministic proactive Research discovery.

This module is a source-generation layer only.  It does not interpret evidence,
score sources, select recommendations, or create a second processing queue.
Raw discovery evidence is written to the canonical Supabase research_sources
table before a new source is appended to the existing Universal FIFO.
"""
from __future__ import annotations

import hashlib
import base64
import html
import json
import os
import re
import shutil
import ssl
import subprocess
import time
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
import sys
sys.path.insert(0, str(ROOT / "scripts" / "social"))
import _supabase as sb  # noqa: E402
from nexus_agent_platform.research_work_queue import ResearchWorkQueue  # noqa: E402

LANE_ROTATION = (
    "WEB_SEARCH", "YOUTUBE_DISCOVERY", "LAST_30_DAYS", "SEO_SEARCH_DEMAND",
    "CUSTOMER_NEEDS_COMPLAINTS", "GITHUB_DISCOVERY", "COMPETITOR_DISCOVERY",
    "AFFILIATE_PROGRAM_DISCOVERY", "FUNDING_GRANTS", "TRADING_RESEARCH",
    "DEPARTMENT_RESEARCH_REQUESTS",
)
DEFAULT_BOUNDS = {"max_queries": 4, "max_results_per_query": 5,
                  "max_new_sources": 20, "max_runtime_per_lane": 45}
HERMES_PRIMARY_PROACTIVE_LANES = frozenset({"CUSTOMER_NEEDS_COMPLAINTS", "WEB_SEARCH", "COMPETITOR_DISCOVERY",
                                            "FUNDING_GRANTS", "AFFILIATE_PROGRAM_DISCOVERY"})
SEED_SUFFIXES = {
    "WEB_SEARCH": ("", "how to", "best", "problems", "complaints", "reviews", "alternatives", "tools"),
    "YOUTUBE_DISCOVERY": ("", "how to", "best", "problems", "reviews", "latest", "2026"),
    "LAST_30_DAYS": ("", "latest", "new", "2026"),
    "SEO_SEARCH_DEMAND": ("", "how do I", "best", "problems", "complaints", "alternatives", "for beginners"),
    "CUSTOMER_NEEDS_COMPLAINTS": ("how do I", "why is", "problems with", "complaints", "denied", "without"),
}
try:
    import certifi
    _SSL = ssl.create_default_context(cafile=certifi.where())
except ImportError:  # use the host trust store when certifi is not installed
    _SSL = ssl.create_default_context()


def now() -> datetime:
    return datetime.now(timezone.utc)


def iso(value: datetime | None = None) -> str:
    return (value or now()).isoformat()


def stable(value: Any, prefix: str = "src") -> str:
    raw = json.dumps(value, sort_keys=True, default=str, separators=(",", ":"))
    return f"{prefix}_{hashlib.sha256(raw.encode()).hexdigest()[:24]}"


def normalize_url(value: str) -> str:
    value = str(value or "").strip()
    if not value:
        return ""
    parsed = urllib.parse.urlsplit(value)
    query = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
    query = [(k, v) for k, v in query if not k.lower().startswith(("utm_", "fbclid", "gclid"))]
    return urllib.parse.urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), parsed.path.rstrip("/") or "/", urllib.parse.urlencode(query), ""))


def generate_seed_queries(topic: str, lane: str, *, max_queries: int = 4) -> list[str]:
    topic = " ".join(str(topic).split()).strip()
    lane = lane.upper()
    # A natural-language Research question is already the query. Appending
    # canned fragments like "how do I" to it changes intent and can surface
    # dictionary/SEO pages that match one incidental word in the question.
    if lane == "CUSTOMER_NEEDS_COMPLAINTS" and ("?" in topic or topic.lower().startswith(("what ", "which ", "how ", "why "))):
        return [topic] if topic else []
    suffixes = SEED_SUFFIXES.get(lane, ("", "latest", "guide"))
    output: list[str] = []
    for suffix in suffixes:
        query = f"{topic} {suffix}".strip()
        if query and query not in output:
            output.append(query)
        if len(output) >= max_queries:
            break
    return output


def should_apply_lane_followup(topic: str, lane: str, enabled: bool) -> bool:
    """Keep explicit customer research questions from being overwritten by stale lane memory."""
    natural_question = (
        lane.upper() == "CUSTOMER_NEEDS_COMPLAINTS"
        and ("?" in topic or str(topic).lower().startswith(("what ", "which ", "how ", "why ")))
    )
    return bool(enabled and not natural_question)


def _governed_public_get(url: str, *, timeout: int = 12, limit: int = 400_000,
                         accept: str = "application/json") -> bytes:
    """Perform bounded public retrieval only inside the durable-job governor."""
    from urllib.parse import urlsplit
    from nexus_agent_platform.provider_enforcement import execute

    host = (urlsplit(url).hostname or "").lower()
    provider = ("GITHUB" if host.endswith("github.com") else
                "GOOGLE" if host.endswith("google.com") or host.endswith("googleapis.com") else
                "PUBLIC_WEB" if host in {"html.duckduckgo.com", "www.bing.com"} else
                "UNKNOWN_EXTERNAL_PROVIDER")
    def request() -> bytes:
        req = urllib.request.Request(url, headers={"User-Agent": "Nexus-Proactive-Research/1.0", "Accept": accept})
        with urllib.request.urlopen(req, timeout=timeout, context=_SSL) as response:
            return response.read(limit)
    return execute(provider, host or "unknown", "RESEARCH_READ",
        {"requests": 1, "api_calls": 1, "bytes": limit, "billable": False, "cost": 0},
        request, job_id=os.environ.get("NEXUS_DURABLE_JOB_ID"),
        job_type=os.environ.get("NEXUS_JOB_TYPE"),
        correlation_id=os.environ.get("NEXUS_CORRELATION_ID"))


def _public_json(url: str, timeout: int = 12) -> Any:
    return json.loads(_governed_public_get(url, timeout=timeout, limit=2_000_000).decode("utf-8", errors="replace"))


def web_search(query: str, limit: int) -> dict[str, Any]:
    params = urllib.parse.urlencode({"q": query})
    body = _governed_public_get(f"https://html.duckduckgo.com/html/?{params}", timeout=12,
                                limit=400_000, accept="text/html").decode("utf-8", errors="replace")
    links = re.findall(r'<a[^>]+class="[^"]*result__a[^"]*"[^>]+href="([^"]+)"[^>]*>(.*?)</a>', body, re.I | re.S)
    snippets = re.findall(r'<a[^>]+class="[^"]*result__snippet[^"]*"[^>]*>(.*?)</a>', body, re.I | re.S)
    clean = lambda value: re.sub(r"<[^>]+>|\s+", " ", html.unescape(value)).strip()
    rows = []
    for rank, (raw_url, raw_title) in enumerate(links[:limit], 1):
        url = urllib.parse.parse_qs(urllib.parse.urlsplit(raw_url).query).get("uddg", [raw_url])[0]
        rows.append({"query": query, "rank_position": rank, "title": clean(raw_title)[:240], "url": url,
                     "domain": urllib.parse.urlsplit(url).netloc, "snippet": clean(snippets[rank - 1])[:800] if rank <= len(snippets) else "",
                     "published_at": None, "updated_at": None, "discovered_at": iso(), "result_type": "ORGANIC_RESULT", "source_engine": "duckduckgo_html"})
    if rows:
        accepted, rejected = _screen_search_rows(rows, query)
        return {"results": accepted, "rejected_results": rejected, "provider": "duckduckgo_html"}
    # Credential-free fallback already used by the existing Hermes web-search
    # capability.  This remains raw SERP collection, not an AI selector.
    bing = _governed_public_get(f"https://www.bing.com/search?{params}", timeout=12,
                                limit=400_000, accept="text/html").decode("utf-8", errors="replace")
    rows = []
    matches = re.findall(r'<li class="b_algo".*?<h2[^>]*><a[^>]+href="([^"]+)"[^>]*>(.*?)</a>.*?</li>', bing, re.I | re.S)
    def bing_target(value: str) -> str:
        value = html.unescape(value)
        parsed = urllib.parse.urlsplit(value)
        encoded = urllib.parse.parse_qs(parsed.query).get("u", [""])[0]
        if encoded.startswith("a1"):
            try:
                decoded = base64.urlsafe_b64decode(encoded[2:] + "=" * (-len(encoded[2:]) % 4)).decode("utf-8", errors="ignore")
                if decoded.startswith("http"):
                    return decoded
            except Exception:
                pass
        return value
    for rank, (url, title) in enumerate(matches[:limit], 1):
        url = bing_target(url)
        rows.append({"query": query, "rank_position": rank, "title": clean(title)[:240], "url": url,
                     "domain": urllib.parse.urlsplit(url).netloc, "snippet": "", "published_at": None,
                     "updated_at": None, "discovered_at": iso(), "result_type": "ORGANIC_RESULT", "source_engine": "bing_html"})
    accepted, rejected = _screen_search_rows(rows, query)
    return {"results": accepted, "rejected_results": rejected, "provider": "bing_html"}


def _screen_search_rows(rows: list[dict[str, Any]], query: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Keep search execution separate from useful source evidence."""
    site_domains = re.findall(r"\bsite:([a-z0-9.-]+)", query.lower())
    stop = {"site", "the", "for", "and", "with", "what", "which", "from", "how", "where", "public", "current"}
    terms = {x for x in re.findall(r"[a-z0-9]+", query.lower()) if len(x) > 2 and x not in stop}
    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for row in rows:
        host = urllib.parse.urlsplit(str(row.get("url") or "")).hostname or ""
        if site_domains:
            matched = any(host == d or host.endswith("." + d) for d in site_domains)
            row["query_source_fit"] = "MATCH" if matched else "SITE_SCOPE_MISMATCH"
            row["query_relevance"] = 1.0 if matched else 0.0
            (accepted if matched else rejected).append(row)
            continue
        words = set(re.findall(r"[a-z0-9]+", (str(row.get("title") or "") + " " + str(row.get("snippet") or "")).lower()))
        ratio = len(terms & words) / max(1, len(terms))
        row["query_relevance"] = round(ratio, 3)
        row["query_source_fit"] = "RELEVANT" if ratio >= 0.12 else "LOW_RELEVANCE"
        (accepted if ratio >= 0.12 else rejected).append(row)
    return accepted, rejected


def classify_customer_candidates(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Classify broad customer-source leads without treating snippets as evidence."""
    from nexus_agent_platform.research_tool_layer import classify_source
    classified = []
    for row in rows:
        labels = classify_source(str(row.get("url") or ""), str(row.get("title") or ""), str(row.get("snippet") or ""))
        classified.append({**row, "source_class": labels["source_class"],
                           "firsthand_or_secondary": "UNKNOWN",
                           "extraction_status": "CANDIDATE_NOT_EXTRACTED"})
    return classified


def google_trends_provider(query: str, *, geo: str = "US") -> dict[str, Any]:
    """Provider contract for demand validation; no supported client is configured."""
    return {"provider": "google_trends", "status": "UNAVAILABLE",
            "query": query, "geo": geo, "evidence": [],
            "external_blocker": "Canonical runtime has no approved Google Trends API/client credentials or configured provider; Google Autocomplete is available separately and is not trend evidence."}


def affiliate_directory_search(provider: str, query: str, limit: int = 5) -> dict[str, Any]:
    """Search one affiliate directory through the already approved web-search route.

    The directory is a discovery scope, not a bulk-import instruction. The
    caller must still apply canonical URL de-duplication, novelty and case
    qualification before creating Research work. Directory-specific program
    terms remain unknown until their official listing is verified.
    """
    key = provider.strip().lower()
    sites = {"affiliate_watch": "affiliate.watch", "partnerstack": "partnerstack.com"}
    if key not in sites:
        return {"provider": key, "status": "UNSUPPORTED", "results": [], "error": "unknown_affiliate_directory"}
    scoped_query = f"site:{sites[key]} {query}"
    result = web_search(scoped_query, max(1, min(int(limit), 10)))
    normalized = []
    for item in result.get("results", []):
        url = normalize_url(str(item.get("url") or ""))
        if not url:
            continue
        normalized.append({**item, "url": url, "query": scoped_query, "source_class": "AFFILIATE_DIRECTORY",
                           "directory_provider": key,
                           "program_fields": {"program_name": item.get("title"), "merchant": None,
                               "category": None, "commission_model": None, "commission_amount": None,
                               "recurring_commission": None, "cookie_duration": None,
                               "affiliate_network": key, "program_url": url,
                               "target_audience": None, "verification_status": "UNVERIFIED"}})
    return {"provider": result.get("provider", "approved_web_search"), "directory": key,
            "status": "COMPLETED" if normalized else "NO_RESULTS", "results": normalized,
            "bulk_import": False, "terms_verified": False}


def discovery_provider_inventory() -> list[dict[str, Any]]:
    """Describe discovery services separately from permanent monitored sources."""
    return [
        {"provider": "approved_web_search", "purpose": "proactive web discovery",
         "enabled": True, "live_status": "DuckDuckGo HTML with Bing fallback; no Google organic-search execution"},
        {"provider": "google_trends", "purpose": "demand and trend validation",
         "enabled": False, "live_status": google_trends_provider("", geo="US")["external_blocker"]},
        {"provider": "affiliate_watch", "purpose": "affiliate directory discovery",
         "enabled": True, "live_status": "Bounded site-scoped search through approved web search; listing terms require official-page verification"},
        {"provider": "partnerstack", "purpose": "affiliate marketplace discovery",
         "enabled": True, "live_status": "Bounded site-scoped search through approved web search; member-only marketplace details may require authorization"},
        {"provider": "github_discovery", "purpose": "open-source project discovery",
         "enabled": True, "live_status": "Existing bounded GitHub discovery lane"},
        {"provider": "funding_grants", "purpose": "public funding and grant discovery",
         "enabled": True, "live_status": "Existing bounded funding/grant query lanes use approved web search"},
    ]


def ensure_discovery_provider_registry() -> dict[str, Any]:
    """Persist provider capabilities in the existing Research source table.

    Provider rows are metadata only: they are not monitored URLs, queue items,
    or instructions to bulk-import marketplace listings.
    """
    if not sb.configured():
        return {"ok": False, "reason": "SUPABASE_NOT_CONFIGURED", "written": 0}
    ids = {"approved_web_search": "https://html.duckduckgo.com/html/",
           "google_trends": "https://trends.google.com/trends/",
           "affiliate_watch": "https://affiliate.watch/",
           "partnerstack": "https://partnerstack.com/marketplace",
           "github_discovery": "https://github.com/trending",
           "funding_grants": "https://www.grants.gov/"}
    rows = []
    for item in discovery_provider_inventory():
        provider = str(item["provider"])
        row_id = str(uuid.uuid5(uuid.NAMESPACE_URL, "nexus:research-discovery-provider:" + provider))
        rows.append({"id": row_id, "source_type": "RESEARCH_DISCOVERY_PROVIDER",
                     "title": provider.replace("_", " ").title(), "url": ids[provider],
                     "metadata": {"record_kind": "DISCOVERY_PROVIDER", "provider_id": provider,
                         "purpose": item["purpose"], "enabled": bool(item["enabled"]),
                         "live_status": item["live_status"], "continuous_monitor": False,
                         "source_role": "DISCOVERY_PROVIDER", "initial_backfill": {"status": "NOT_REQUESTED"},
                         "updated_at": iso()}})
    status, body = sb.rest("POST", "research_sources?on_conflict=id", body=rows,
                           prefer="return=representation,resolution=merge-duplicates")
    if status not in (200, 201, 204):
        return {"ok": False, "status": status, "error": str(body)[:200], "written": 0}
    read_status, readback = sb.get("research_sources", "select=id,metadata&source_type=eq.RESEARCH_DISCOVERY_PROVIDER&limit=50")
    found = {((row.get("metadata") or {}).get("provider_id")) for row in readback} if isinstance(readback, list) else set()
    return {"ok": read_status == 200 and all((row["metadata"]["provider_id"] in found) for row in rows),
            "status": status, "readback_status": read_status, "written": len(rows),
            "providers_read_back": len(found), "providers": discovery_provider_inventory()}


def youtube_search(query: str, limit: int) -> list[dict[str, Any]]:
    if not shutil.which("yt-dlp"):
        raise RuntimeError("yt-dlp_unavailable")
    command = ["yt-dlp", "--no-update", "--no-warnings", "--skip-download", "--flat-playlist", "--dump-single-json", "--playlist-end", str(limit), f"ytsearch{limit}:{query}"]
    completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=30, check=False)
    if completed.returncode != 0:
        raise RuntimeError((completed.stderr or "yt-dlp_failed")[-400:])
    payload = json.loads(completed.stdout)
    rows = []
    for entry in payload.get("entries", []) or []:
        if not entry or not entry.get("id"):
            continue
        upload = entry.get("upload_date")
        published = f"{upload[:4]}-{upload[4:6]}-{upload[6:8]}T00:00:00+00:00" if upload and len(upload) == 8 else None
        rows.append({"video_id": entry["id"], "url": f"https://www.youtube.com/watch?v={entry['id']}",
                     "title": entry.get("title") or entry["id"], "channel": entry.get("channel") or entry.get("uploader"),
                     "channel_id": entry.get("channel_id"), "published_at": published, "duration": entry.get("duration"),
                     "views": entry.get("view_count"), "likes": entry.get("like_count"), "comments_count": entry.get("comment_count"),
                     "description": entry.get("description"), "query_used": query, "discovered_at": iso()})
    return rows


def github_repository_search(query: str, limit: int) -> list[dict[str, Any]]:
    """Use GitHub's public repository search API for technology objectives."""
    params = urllib.parse.urlencode({"q": query, "sort": "updated", "order": "desc", "per_page": max(1, min(limit, 10))})
    payload = json.loads(_governed_public_get("https://api.github.com/search/repositories?" + params,
        timeout=15, limit=1_500_000, accept="application/vnd.github+json").decode("utf-8", errors="replace"))
    output = []
    for item in payload.get("items", [])[:max(1, min(limit, 10))]:
        license_info = item.get("license") or {}
        output.append({"query": query, "url": item.get("html_url"), "domain": "github.com",
            "title": item.get("full_name"), "snippet": item.get("description") or "",
            "published_at": item.get("created_at"), "updated_at": item.get("updated_at"),
            "source_engine": "github_public_repository_search", "source_class": "GITHUB",
            "stars": item.get("stargazers_count"), "language": item.get("language"),
            "license": license_info.get("spdx_id") or "UNKNOWN", "forks": item.get("forks_count"),
            "firsthand_or_secondary": "FIRSTHAND_REPOSITORY_METADATA"})
    return output


def _freshness(published: str | None, discovered: str, start: datetime, end: datetime) -> str:
    if published:
        try:
            stamp = datetime.fromisoformat(published.replace("Z", "+00:00"))
            return "PUBLISHED_IN_WINDOW" if start <= stamp <= end else "HISTORICAL_RESULT"
        except ValueError:
            pass
    return "DISCOVERED_IN_WINDOW"


def last30_search(query: str, limit: int, start: datetime, end: datetime) -> list[dict[str, Any]]:
    # This lane is evidence collection for the current question. Search results
    # may surface any relevant site, but HN is never a preselected source.
    rows = web_search(query, limit).get("results", [])[:limit]
    for row in rows:
        row["freshness_class"] = _freshness(row.get("published_at"), row["discovered_at"], start, end)
    return rows


def seo_signals(query: str, limit: int) -> list[dict[str, Any]]:
    signals: list[dict[str, Any]] = []
    suggest_url = "https://suggestqueries.google.com/complete/search?" + urllib.parse.urlencode({"client": "firefox", "q": query})
    try:
        data = _public_json(suggest_url)
        for value in (data[1] if isinstance(data, list) and len(data) > 1 else [])[:limit]:
            signals.append({"query": query, "signal_type": "RELATED_SEARCH", "signal_value": value, "position": None,
                            "url": None, "domain": None, "title": None, "source": "google_autocomplete", "source_class": "SEARCH_SUGGESTIONS", "observed_at": iso(),
                            "volume": "UNKNOWN", "difficulty": "UNKNOWN", "trend_direction": "UNKNOWN"})
    except Exception:
        pass
    for row in web_search(query, limit).get("results", []):
        signals.append({"query": query, "signal_type": row.get("result_type", "ORGANIC_RESULT"), "signal_value": row.get("title"),
                        "position": row.get("rank_position"), "url": row.get("url"), "domain": row.get("domain"), "title": row.get("title"),
                        "source_class": row.get("source_class") or "WEB_SEARCH_RESULT",
                        "source": row.get("source_engine"), "observed_at": row.get("discovered_at"), "snippet": row.get("snippet"),
                        "volume": "UNKNOWN", "difficulty": "UNKNOWN", "trend_direction": "UNKNOWN"})
    return signals


def _existing_source(identity: str, url: str = "") -> tuple[dict[str, Any] | None, int]:
    predicate = f"url=eq.{sb.q(url)}" if url else f"metadata->>source_identity=eq.{sb.q(identity)}"
    code, data = sb.get("research_sources", f"select=id,url,metadata&{predicate}&limit=1")
    return ((data[0] if isinstance(data, list) and data else None), code)


def _write_run(row: dict[str, Any], run_id: str | None = None) -> tuple[str | None, bool, str | None]:
    if run_id:
        code, _ = sb.update("research_discovery_runs", f"id=eq.{sb.q(run_id)}", row)
        return run_id, code in (200, 204), None if code in (200, 204) else str(code)
    code, data = sb.insert("research_discovery_runs", row)
    if code not in (200, 201) or not isinstance(data, list) or not data:
        return None, False, str(code)
    return data[0].get("id"), True, None


def persist_discovered(run_id: str, lane: str, record: dict[str, Any], *, known_ids: set[str] | None = None) -> dict[str, Any]:
    stages: dict[str, float] = {}
    stage_started = time.monotonic()
    url = normalize_url(record.get("url") or record.get("source_url") or "")
    identity = url or stable({"lane": lane, "query": record.get("query"), "signal": record.get("signal_value"), "title": record.get("title")}, "signal")
    existing, lookup_code = _existing_source(identity, url)
    stages["dedupe_existing_source_lookup_seconds"] = round(time.monotonic() - stage_started, 3)
    metadata = {"discovery_run_id": run_id, "lane": lane, "raw_discovery": record,
                "normalized_url": url or None, "source_identity": identity, "last_seen_at": iso(), "discovery_status": "DISCOVERED"}
    if existing:
        old = existing.get("metadata") if isinstance(existing.get("metadata"), dict) else {}
        patch = {"metadata": {**old, **metadata}}
        stage_started = time.monotonic()
        code, _ = sb.update("research_sources", f"id=eq.{sb.q(existing['id'])}", patch)
        stages["persistence_seconds"] = round(time.monotonic() - stage_started, 3)
        return {"new": False, "duplicate": True, "fifo": False, "source_id": existing["id"], "readback": code in (200, 204), "lookup_code": lookup_code, "stage_timings": stages}
    from research.proactive_research_memory import process_discovery_result, query_tokens
    stage_started = time.monotonic()
    query_words = query_tokens(str(record.get("query") or ""))
    evidence_words = query_tokens(" ".join((str(record.get("title") or ""), str(record.get("snippet") or ""))))
    overlap = len(query_words & evidence_words) / max(1, len(query_words))
    relevance = min(1.0, max(.2, overlap))
    value = .45 if record.get("title") and url else .15
    if lane == "TRADINGVIEW_PUBLIC_SCRIPTS":
        relevance = max(relevance, float(record.get("qualification_score") or 0))
        value = .5 if record.get("qualification_status") == "QUALIFIED_FOR_INDEPENDENT_TEST" else .15
    decision = process_discovery_result(
        {"url": url, "source_id": record.get("source_id"), "title": record.get("title"),
         "content_hash": record.get("content_hash"),
         # A provider must explicitly identify workspace value. Raw SERP rows
         # do not qualify for NotebookLM by default.
         "workspace_useful": bool(record.get("workspace_useful"))},
        objective_id="objective_" + hashlib.sha256(lane.upper().encode()).hexdigest()[:16],
        objective_type=lane.upper(), topic=str(record.get("query") or lane),
        relevance=relevance, value=value, known_ids=known_ids)
    stages["novelty_case_and_notebook_gate_seconds"] = round(time.monotonic() - stage_started, 3)
    case = decision.get("case")
    metadata.update({"research_case_id": (case or {}).get("case_id"),
                     "novelty_classification": decision.get("classification"),
                     "notebook_gate_passed": bool(decision.get("create_notebook_workspace")),
                     "notebook_created": False})
    row = {"source_type": "YOUTUBE_VIDEO" if record.get("video_id") else ("TRADINGVIEW_SCRIPT" if lane == "TRADINGVIEW_PUBLIC_SCRIPTS" else "SEO_SIGNAL" if not url else "WEB_PAGE"), "title": record.get("title") or record.get("signal_value"),
           "url": url or None, "author": record.get("channel") or record.get("domain"), "published_at": record.get("published_at"),
           "snippet": record.get("snippet") or record.get("description") or record.get("signal_value"),
           "why_it_matters": "Raw deterministic discovery evidence; downstream processing is separate.", "metadata": metadata}
    stage_started = time.monotonic()
    code, data = sb.insert("research_sources", row)
    if code not in (200, 201) or not isinstance(data, list) or not data:
        stages["persistence_seconds"] = round(time.monotonic() - stage_started, 3)
        return {"new": True, "duplicate": False, "fifo": False, "readback": False, "error": f"supabase_source_write_{code}", "stage_timings": stages}
    source_id = data[0].get("id")
    queued = None
    fifo = False
    if url and decision.get("create_notebook_workspace") and case:
        queue = ResearchWorkQueue()
        queued = queue.enqueue(work_id=f"proactive:{identity}", source_id=source_id, source_url=url,
                               source_type=row["source_type"], title=row["title"], source_name=row["title"],
                               work_class="GENERAL_DISCOVERY", request_type="PROACTIVE_DISCOVERY", lane_id=lane,
                               category=lane, objective=f"Process Research case {case['case_id']}: {row['title']}",
                               required_tool="YOUTUBE" if row["source_type"] == "YOUTUBE_VIDEO" else "WEB",
                               status="QUEUED", requested_by="proactive_discovery",
                               selection_reason="novelty_and_workspace_gate_passed",
                               evidence_refs=[source_id], dedup_key=f"proactive:{identity}",
                               research_case_id=case["case_id"])
        fifo = bool(queued)
    read_code, readback = sb.get("research_sources", f"select=id,url,metadata&id=eq.{sb.q(source_id)}&limit=1")
    stages["persistence_seconds"] = round(time.monotonic() - stage_started, 3)
    return {"new": True, "duplicate": False, "fifo": fifo, "source_id": source_id,
            "research_case_id": (case or {}).get("case_id"),
            "readback": read_code == 200 and bool(readback),
            "queue_sequence": queued.get("queue_sequence") if queued else None, "queue_item": queued,
            "stage_timings": stages}


def run_lane(topic: str, lane: str, *, window_days: int = 30, bounds: dict[str, int] | None = None,
             use_lane_followup: bool = True, objective_family: str | None = None,
             source_strategy: dict[str, Any] | None = None, research_case_id: str | None = None,
             originating_goal_id: str | None = None) -> dict[str, Any]:
    bounds = {**DEFAULT_BOUNDS, **(bounds or {})}
    lane_started = time.monotonic()
    started = now(); run_id, created, create_error = _write_run({"lane": lane, "trigger": "PROACTIVE_V1", "status": "STARTED", "started_at": iso(started), "metadata": {"topic": topic, "seed_query": None, "time_window": "LAST_30_DAYS" if window_days == 30 else f"LAST_{window_days}_DAYS"}})
    if not run_id:
        return {"lane": lane, "topic": topic, "status": "FAILED_RETRYABLE", "error": f"run_receipt_create:{create_error}", "supabase_readback": False}
    query_generation_started = time.monotonic()
    queries = generate_seed_queries(topic, lane, max_queries=bounds["max_queries"])
    query_generation_seconds = round(time.monotonic() - query_generation_started, 3)
    objective_started = time.monotonic()
    records: list[dict[str, Any]] = []; screened_out: list[dict[str, Any]] = []; failed_queries = []; failed_fetches = 0
    from research.proactive_research_memory import query_guard, record_query, next_query, _latest
    objective_id = "objective_" + hashlib.sha256(lane.upper().encode()).hexdigest()[:16]
    source_strategy_id = ("hermes-governed-tool-layer-v1" if lane in HERMES_PRIMARY_PROACTIVE_LANES
                          else lane.lower() + "-default-v1")
    prior_queries = [row for row in _latest("PROACTIVE_QUERY") if row.get("objective_id") == objective_id]
    # A caller-supplied research question is the active objective. A stale
    # generated-query direction from prior lane memory must not replace it;
    # structured Research follow-up contracts are handled by their own path.
    if prior_queries and should_apply_lane_followup(topic, lane, use_lane_followup):
        prior_queries.sort(key=lambda row: str(row.get("run_at") or ""))
        direction = str(prior_queries[-1].get("next_query_direction") or "").strip()
        if direction and direction not in queries:
            queries = [direction, *queries][:bounds["max_queries"]]
    objective_seconds = round(time.monotonic() - objective_started, 3)
    executed_queries: list[str] = []
    query_result_counts: dict[str, int] = {}
    query_source_ids: dict[str, list[str]] = {}
    deadline = time.monotonic() + bounds["max_runtime_per_lane"]
    start_window = started - timedelta(days=window_days)
    provider_seconds = 0.0
    hermes_research: dict[str, Any] | None = None
    hermes_primary_lane = lane in HERMES_PRIMARY_PROACTIVE_LANES
    for query in queries:
        if time.monotonic() >= deadline:
            break
        # A designated monitored source is checked by stable source identity;
        # query novelty must not silently suppress its scheduled refresh.
        guard = ({"allowed": True, "reason": "DESIGNATED_SOURCE_REFRESH"}
                 if lane == "TRADINGVIEW_PUBLIC_SCRIPTS"
                 else query_guard(query, repeat_reason="FRESHNESS_EXPIRED", freshness_hours=24,
                                  source_strategy_id=source_strategy_id))
        if not guard.get("allowed"):
            continue
        try:
            provider_started = time.monotonic()
            if hermes_primary_lane:
                from nexus_agent_platform.research_tool_layer import execute_research_question, plan_source_strategy
                planned = source_strategy or plan_source_strategy(topic)
                hermes_research = execute_research_question(
                    topic, objective_family or lane, planned,
                    research_case_id=research_case_id, originating_goal_id=originating_goal_id,
                    mode="autonomous", timeout_seconds=min(240, max(30, bounds["max_runtime_per_lane"])),
                    max_searches=max(1, bounds["max_queries"]), max_pages=max(1, bounds["max_new_sources"]),
                )
                if hermes_research.get("execution_status") == "PROVIDER_FAILURE":
                    # The local HTML adapter is deliberately a recorded resilience fallback,
                    # never the primary path. Search rows remain candidates, not evidence.
                    if lane == "FUNDING_GRANTS":
                        payload = web_search(f"site:sba.gov {query}", bounds["max_results_per_query"])
                        rows = payload.get("results", [])
                    elif lane == "AFFILIATE_PROGRAM_DISCOVERY":
                        payload = {"results": [], "rejected_results": []}
                        for directory in ("affiliate_watch", "partnerstack"):
                            payload["results"].extend(affiliate_directory_search(directory, query, bounds["max_results_per_query"])["results"])
                        rows = payload["results"]
                    else:
                        payload = web_search(query, bounds["max_results_per_query"])
                        rows = classify_customer_candidates(payload.get("results", [])) if lane == "CUSTOMER_NEEDS_COMPLAINTS" else payload.get("results", [])
                    for row in rows:
                        row["extraction_status"] = "CANDIDATE_NOT_EXTRACTED"
                        row["provider"] = "LOCAL_HTML_FALLBACK"
                    screened_out.extend(payload.get("rejected_results", []))
                    hermes_research["fallback_used"] = True
                    hermes_research["fallback_reason"] = hermes_research.get("provider_error")
                    hermes_research["records"] = rows
                    hermes_research["queries"] = [query]
                    hermes_research["searches"] = [{"query": query, "tool": "local_html_search", "provider": "LOCAL_HTML_FALLBACK"}]
                    hermes_research["status"] = "COMPLETED" if rows else "FAILED_RETRYABLE"
                    hermes_research["research_conclusion"] = "RESEARCH_INCONCLUSIVE"
                    hermes_research["next_research_action"] = "RETRY_GOVERNED_HERMES_TOOL_LAYER"
                    hermes_research["tool_layer_receipt"]["fallback_used"] = True
                    hermes_research["tool_layer_receipt"]["created_at"] = now().isoformat()
                    hermes_research["tool_layer_receipt"]["fallback_reason"] = hermes_research.get("fallback_reason")
                    hermes_research["tool_layer_receipt"]["fallback_tool"] = "local_html_search"
                    hermes_research["tool_layer_receipt"]["engine"] = "LOCAL_HTML_FALLBACK"
                    hermes_research["tool_layer_receipt"]["searches"] = hermes_research["searches"]
                    hermes_research["tool_layer_receipt"]["search_count"] = 1
                    hermes_research["tool_layer_receipt"]["candidate_source_urls"] = [r.get("url") for r in rows if r.get("url")]
                    hermes_research["tool_layer_receipt"]["sources_opened"] = []
                    hermes_research["tool_layer_receipt"]["source_fit"] = "POOR"
                    hermes_research["tool_layer_receipt"]["evidence_quality"] = "NO_EXTRACTED_EVIDENCE"
                    hermes_research["tool_layer_receipt"]["research_conclusion"] = "RESEARCH_INCONCLUSIVE"
                    hermes_research["tool_layer_receipt"]["why_concluded"] = "Fallback returned candidate URLs only; results were not extracted and do not establish evidence."
                    from nexus_agent_platform.research_tool_layer import _persist_run
                    _persist_run({**hermes_research["tool_layer_receipt"], "run_id": hermes_research["tool_layer_receipt"]["run_id"] + "_fallback"})
                rows = hermes_research.get("records", [])
                screened_out.extend([{**row, "query_source_fit": "CANDIDATE_SOURCE_NOT_EXTRACTED"}
                                     for row in hermes_research.get("search_candidates", [])])
                screened_out.extend(hermes_research.get("rejected_sources", []))
                executed_queries.extend(hermes_research.get("queries", []))
                query_result_counts[query] = len(rows)
                query_source_ids[query] = [normalize_url(r.get("url", "")) for r in rows if r.get("url")]
                records.extend(rows)
                # The governed executor performs bounded adaptive research in one Hermes session.
                break
            elif lane == "TRADINGVIEW_PUBLIC_SCRIPTS":
                from nexus_agent_platform.tradingview_public_source import discover
                rows = discover(bounds["max_results_per_query"]).get("items", [])
                for item in rows:
                    desc = str(item.get("description") or "")
                    open_source = item.get("access_type") == "OPEN_SOURCE"
                    recency_known = bool(item.get("updated_at") or item.get("published_at"))
                    observations = set((item.get("source_logic_inspection") or {}).get("observations", []))
                    criteria = {
                        "NOVELTY": 0.0,  # cross-run similarity is evaluated after durable identity lookup
                        "CLEAR_RULES": 0.15 if open_source and len(desc) >= 250 else 0.0,
                        "TESTABILITY": 0.2 if open_source and item.get("script_type") in {"STRATEGY", "INDICATOR"} else 0.0,
                        "MARKET_RELEVANCE": 0.15 if item.get("market") != "UNKNOWN" else 0.0,
                        "RISK_MODEL": 0.15 if "defines_strategy_exits" in observations and "contains_explicit_stop_or_risk_terms" in observations else 0.1 if "contains_explicit_stop_or_risk_terms" in observations else 0.0,
                        "SOURCE_TRANSPARENCY": 0.15 if open_source else 0.0,
                        "UPDATE_RECENCY": 0.05 if recency_known else 0.0,
                        "ENGAGEMENT": 0.05 if (item.get("engagement_signal", {}).get("likes") or 0) >= 100 else 0.0,
                        "NEXUS_TEST_FIT": 0.1 if item.get("script_type") in {"STRATEGY", "INDICATOR"} else 0.0,
                    }
                    item["qualification_criteria"] = criteria
                    item["qualification_score"] = round(sum(criteria.values()), 3)
                    item["qualification_threshold"] = 0.7
                    item["qualification_status"] = ("QUALIFIED_FOR_INDEPENDENT_TEST" if open_source and item["qualification_score"] >= 0.7 else "RESEARCH_INCONCLUSIVE" if item.get("access_type") == "UNKNOWN" else "LOW_VALUE_OR_NOT_TESTABLE")
                    item["qualification_reason"] = ("Threshold met; verify novelty against local/durable strategy inventory before handoff." if item["qualification_status"] == "QUALIFIED_FOR_INDEPENDENT_TEST" else "Not enough verified criteria; missing market, novelty, open logic, or risk evidence remains inconclusive." if item["qualification_status"] == "RESEARCH_INCONCLUSIVE" else "Public source does not meet the evidence and testability threshold.")
                    item["workspace_useful"] = item["qualification_status"] == "QUALIFIED_FOR_INDEPENDENT_TEST"
            elif lane == "YOUTUBE_DISCOVERY": rows = youtube_search(query, bounds["max_results_per_query"])
            elif lane == "GITHUB_DISCOVERY": rows = github_repository_search(query, bounds["max_results_per_query"])
            elif lane == "LAST_30_DAYS": rows = last30_search(query, bounds["max_results_per_query"], start_window, started)
            elif lane == "SEO_SEARCH_DEMAND": rows = seo_signals(query, bounds["max_results_per_query"])
            elif lane == "FUNDING_GRANTS":
                scoped = f"site:sba.gov {query}"
                payload = web_search(scoped, bounds["max_results_per_query"])
                rows = payload.get("results", [])
                screened_out.extend(payload.get("rejected_results", []))
            elif lane == "CUSTOMER_NEEDS_COMPLAINTS":
                # Customer discussion is an evidence preference, not a domain
                # lock. A Reddit-only query was producing empty source access
                # whenever Reddit was unindexed/blocked and excluded reviews,
                # forums, and complaint sources that could answer the same
                # question. Discover broadly, classify candidate URLs, then
                # let the existing FIFO/page pipeline inspect the actual page.
                payload = web_search(query, bounds["max_results_per_query"])
                rows = payload.get("results", [])
                screened_out.extend(payload.get("rejected_results", []))
                rows = classify_customer_candidates(rows)
            elif lane == "AFFILIATE_PROGRAM_DISCOVERY":
                rows = []
                for directory in ("affiliate_watch", "partnerstack"):
                    rows.extend(affiliate_directory_search(directory, query, bounds["max_results_per_query"])["results"])
            else:
                payload = web_search(query, bounds["max_results_per_query"])
                rows = payload.get("results", [])
                screened_out.extend(payload.get("rejected_results", []))
            provider_seconds += time.monotonic() - provider_started
            records.extend(rows)
            executed_queries.append(query)
            query_result_counts[query] = len(rows)
            query_source_ids[query] = [normalize_url(r.get("url", "")) for r in rows if r.get("url")]
        except Exception as exc:
            failed_queries.append({"query": query, "error": str(exc)[:300]})
    records = records[: bounds["max_queries"] * bounds["max_results_per_query"]]
    new_sources = duplicates = appended = readbacks = readback_failures = 0
    novel_by_query: dict[str, int] = {}
    duplicate_by_query: dict[str, int] = {}
    cases_by_query: dict[str, int] = {}
    seen: set[str] = set()
    # Load duplicate history once per lane. Previously the case classifier
    # repeated its two Supabase history reads for every individual result.
    from research.proactive_research_memory import known_research_identities
    novelty_started = time.monotonic()
    known_ids = known_research_identities()
    identity_history_seconds = time.monotonic() - novelty_started
    result_stage_seconds: dict[str, float] = {"dedupe_existing_source_lookup_seconds": 0.0,
        "novelty_case_and_notebook_gate_seconds": 0.0, "persistence_seconds": 0.0}
    for record in records:
        identity = normalize_url(record.get("url") or record.get("video_id") or record.get("signal_value") or "")
        if identity and identity in seen:
            duplicates += 1; continue
        seen.add(identity)
        if lane == "SEO_SEARCH_DEMAND":
            if not record.get("url"): continue
        result = persist_discovered(run_id, lane, record, known_ids=known_ids)
        record["persistence_disposition"] = "DUPLICATE" if result.get("duplicate") else "NEW_SOURCE" if result.get("new") else "NOT_PERSISTED"
        record["queue_work_id"] = ((result.get("queue_item") or {}).get("work_id") if isinstance(result.get("queue_item"), dict) else None)
        record["research_case_id"] = result.get("research_case_id")
        if result.get("duplicate"):
            record["qualification_status"] = "DUPLICATE"
            record["qualification_reason"] = "Canonical source identity already exists in the durable/local Research source registry; no new Trading handoff is created."
        for key, duration in (result.get("stage_timings") or {}).items():
            result_stage_seconds[key] = result_stage_seconds.get(key, 0.0) + float(duration or 0)
        result_query = str(record.get("query") or "")
        if result.get("new"): novel_by_query[result_query] = novel_by_query.get(result_query, 0) + 1
        if result.get("duplicate"): duplicate_by_query[result_query] = duplicate_by_query.get(result_query, 0) + 1
        if result.get("research_case_id"): cases_by_query[result_query] = cases_by_query.get(result_query, 0) + 1
        if result.get("duplicate"): duplicates += 1
        if result.get("new"): new_sources += 1
        if result.get("fifo"): appended += 1
        if result.get("readback"): readbacks += 1
        elif result.get("new") or result.get("duplicate"): readback_failures += 1
        if result.get("error"): failed_fetches += 1
        if result.get("new"):
            from research.proactive_research_memory import canonical_result_id
            known_ids.add(canonical_result_id({"url": record.get("url"), "youtube_video_id": record.get("video_id"),
                "content_hash": record.get("content_hash"), "source_id": result.get("source_id"), "title": record.get("title")}))
        if new_sources >= bounds["max_new_sources"]: break
    for query in executed_queries:
        question = f"What evidence confirms or contradicts results for {topic}?"
        direction = next_query(previous_query=query, open_questions=[question], topic=topic)
        record_query(objective_id=objective_id, objective_type=lane.upper(), topic=topic,
                     query=query, results_seen=query_result_counts.get(query, 0),
                     new_results=novel_by_query.get(query, 0),
                     duplicate_results=duplicate_by_query.get(query, 0),
                     sources_seen=len(set(query_source_ids.get(query, []))),
                     findings_created=cases_by_query.get(query, 0),
                     novel_findings=cases_by_query.get(query, 0),
                     open_questions=[question], next_query_direction=direction,
                     result_ids=query_source_ids.get(query, []), repeat_reason="FRESHNESS_EXPIRED",
                     source_strategy_id=source_strategy_id)
    completed = now()
    if hermes_primary_lane:
        from nexus_agent_platform.research_tool_layer import single_primary_engine_guard
        active_engine = "LOCAL_HTML_FALLBACK" if (hermes_research or {}).get("fallback_used") else "HERMES_TOOL_LAYER"
        if not single_primary_engine_guard(active_engine, bool((hermes_research or {}).get("fallback_used")),
                                           (hermes_research or {}).get("fallback_reason")):
            raise RuntimeError("SINGLE_PRIMARY_RESEARCH_ENGINE_REGRESSION")
    stage_timings = {"objective_selection_seconds": objective_seconds,
        "query_generation_seconds": query_generation_seconds,
        "provider_request_and_result_parsing_seconds": round(provider_seconds, 3),
        "dedupe_existing_source_lookup_seconds": round(result_stage_seconds["dedupe_existing_source_lookup_seconds"], 3),
        "novelty_identity_history_seconds": round(identity_history_seconds, 3),
        "novelty_case_and_notebook_decision_seconds": round(result_stage_seconds["novelty_case_and_notebook_gate_seconds"], 3),
        "source_and_readback_persistence_seconds": round(result_stage_seconds["persistence_seconds"], 3),
        "handoff_seconds": 0.0,
        "handoff_note": "No department handoff is created during raw discovery collection.",
        "total_run_lane_seconds": round(time.monotonic() - lane_started, 3)}
    receipt = {"lane": lane, "status": "COMPLETED" if not failed_queries else "FAILED_RETRYABLE", "completed_at": iso(completed),
               "sources_discovered": len(records), "sources_processed": new_sources + duplicates, "metadata": {
                   "discovery_run_id": run_id, "topic": topic, "seed_query": executed_queries[0] if executed_queries else None,
                   "time_window": {"start": iso(start_window), "end": iso(started)}, "queries": executed_queries,
                   "queries_run": len(executed_queries), "queries_skipped_repeat": len(queries) - len(executed_queries), "results_found": len(records), "new_sources": new_sources,
                   "duplicates": duplicates, "failed_queries": failed_queries, "failed_fetches": failed_fetches,
                   "sources_appended_to_fifo": appended, "supabase_readback": readback_failures == 0,
                   "readback_failures": readback_failures,
                   "runtime_seconds": round((completed - started).total_seconds(), 3),
                   "stage_timings": stage_timings,
                   "result_type": "RAW_DISCOVERY_ONLY", "ai_required_for_collection": False,
                   "research_execution_engine": "HERMES_TOOL_LAYER" if hermes_primary_lane else "SPECIALIZED_SOURCE_ADAPTER",
                   "fallback_used": bool((hermes_research or {}).get("fallback_used", False)),
                   "fallback_reason": (hermes_research or {}).get("fallback_reason"),
                   "research_question": topic if hermes_primary_lane else None,
                   "source_strategy": (hermes_research or {}).get("tool_layer_receipt", {}).get("source_strategy") if hermes_primary_lane else None,
                   "tools_considered": (hermes_research or {}).get("tools_considered", []),
                   "tools_selected": (hermes_research or {}).get("tools_selected", []),
                   "searches": (hermes_research or {}).get("searches", []),
                   "sources_opened": len((hermes_research or {}).get("records", [])),
                   "research_conclusion": (hermes_research or {}).get("research_conclusion"),
                   "why_concluded": (hermes_research or {}).get("why_concluded"),
                   "next_research_action": (hermes_research or {}).get("next_research_action")}}
    _, update_ok, update_error = _write_run(receipt, run_id)
    heartbeat_code, _ = sb.insert("research_heartbeat_telemetry", {
        "lane": lane, "window_start": iso(start_window), "window_end": iso(completed),
        "sources_registered": new_sources + duplicates, "sources_processed": new_sources + duplicates,
        "claims_extracted": 0, "supported_claims": 0, "cross_checked_claims": 0,
        "contradictions_found": 0, "handoffs_created": 0, "department_actions": 0,
    }, prefer="return=minimal")
    observed_source_classes = sorted({str(row.get("source_class") or ("TRADINGVIEW_PUBLIC_SCRIPTS" if lane == "TRADINGVIEW_PUBLIC_SCRIPTS" else "SEO_SEARCH_DEMAND" if lane == "SEO_SEARCH_DEMAND" else "WEB_SEARCH")) for row in records})
    return {"discovery_run_id": run_id, "lane": lane, "topic": topic, "status": receipt["status"], "queries_run": len(executed_queries),
            "results_found": len(records), "new_sources": new_sources, "duplicates": duplicates, "failed_queries": failed_queries,
            "queries": executed_queries, "result_ids": sorted({identity for values in query_source_ids.values() for identity in values}),
            "qualified_findings_created": sum(cases_by_query.values()),
            "failed_fetches": failed_fetches, "sources_appended_to_fifo": appended, "supabase_readback": readback_failures == 0,
            "receipt_updated": update_ok, "receipt_error": update_error, "runtime_seconds": receipt["metadata"]["runtime_seconds"],
            "stage_timings": stage_timings, "source_classes_used": observed_source_classes,
            "screened_out_results": screened_out, "search_results_returned": len(records) + len(screened_out),
            "heartbeat_persisted": heartbeat_code in (200, 201, 204), "records": records, "run_created": created,
            "research_execution_engine": "HERMES_TOOL_LAYER" if hermes_primary_lane and not (hermes_research or {}).get("fallback_used") else "LOCAL_HTML_FALLBACK" if (hermes_research or {}).get("fallback_used") else "SPECIALIZED_SOURCE_ADAPTER",
            "fallback_used": bool((hermes_research or {}).get("fallback_used", False)),
            "fallback_reason": (hermes_research or {}).get("fallback_reason"),
            "research_question": topic if hermes_primary_lane else None,
            "source_strategy": (hermes_research or {}).get("tool_layer_receipt", {}).get("source_strategy"),
            "tools_considered": (hermes_research or {}).get("tools_considered", []),
            "tools_selected": (hermes_research or {}).get("tools_selected", []),
            "research_conclusion": (hermes_research or {}).get("research_conclusion"),
            "why_concluded": (hermes_research or {}).get("why_concluded"),
            "next_research_action": (hermes_research or {}).get("next_research_action"),
            "hermes_research": hermes_research}


def heartbeat_next_lane(last_lane: str | None = None) -> str:
    if not last_lane or last_lane.upper() not in LANE_ROTATION:
        return LANE_ROTATION[0]
    return LANE_ROTATION[(LANE_ROTATION.index(last_lane.upper()) + 1) % len(LANE_ROTATION)]


def capability_inventory() -> dict[str, Any]:
    return {"existing_discovery_engine": "last30days_adapter + bounded research router", "existing_web_search": "hermes_web_search._search_duckduckgo_html", "existing_youtube_discovery": "youtube_full_pipeline + yt-dlp", "existing_seo_engine": "demand_discovery/governed question surfaces; no raw SERP collector", "existing_last30_logic": "last30days_adapter", "existing_dedup_logic": "open_source_scout normalization + Universal FIFO upsert", "existing_source_registry": "research_sources + research_work_queue", "existing_supabase_tables_reused": ["research_sources", "research_discovery_runs", "research_work_queue.json projection"]}
