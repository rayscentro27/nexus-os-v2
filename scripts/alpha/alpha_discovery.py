"""Bounded Alpha discovery, retrieval, verification, and memory contracts.

This module deliberately keeps discovery metadata and bounded evidence in the
canonical governed store. It does not grant external-write authority and does
not replace Nexus work-order or loop control.
"""
from __future__ import annotations

import hashlib
import html
import json
import os
import re
import subprocess
import tempfile
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[2]
from nexus_agent_platform.governed.persistence import append_record, read_records  # noqa: E402

RECENCY_WINDOWS = {"LAST_24_HOURS": 1, "LAST_7_DAYS": 7, "LAST_30_DAYS": 30, "LAST_90_DAYS": 90, "EVERGREEN": None}
DEFAULT_BUDGET = {"MAX_SEARCH_QUERIES": 4, "MAX_DISCOVERY_RESULTS": 12, "MAX_YOUTUBE_TRANSCRIPTS": 1, "MAX_PAGE_FETCHES": 4, "MAX_GITHUB_REPOS": 4, "MAX_FORUM_THREADS": 2, "MAX_RESEARCH_CALLS": 8, "MAX_AI_CALLS": 1, "MAX_RUNTIME_SECONDS": 180}
SOURCE_REGISTRY = [
    ("NEXUS_INTERNAL_RESEARCH", "internal", "authoritative_for_nexus_research", True),
    ("NEXUS_EXPERIMENT_MEMORY", "internal", "authoritative_for_nexus_experiments", True),
    ("NEXUS_BUSINESS_OUTCOMES", "internal", "authoritative_for_nexus_outcomes", True),
    ("YOUTUBE", "discovery", "idea_claim_source", True), ("PUBLIC_WEB", "verification", "secondary_evidence", True),
    ("DIRECT_URL", "verification", "retrieved_source", True), ("FORUM", "discovery", "community_experience", True),
    ("REDDIT_OR_COMMUNITY", "discovery", "community_experience", True), ("GITHUB", "verification", "repository_contents", True),
    ("ACADEMIC_RESEARCH", "verification", "methodology_evidence", True), ("NEWS", "discovery", "reported_event", True),
    ("SEO_SEARCH_INTELLIGENCE", "discovery", "demand_discovery_not_truth", True), ("OANDA_MARKET_DATA", "verification", "market_observation", True),
    ("OANDA_BROKER_EVIDENCE", "verification", "broker_truth", True), ("VIBE_MCP", "research", "optional_quant_research", True),
]
THEMES = {
    "TRADING": ["forex strategies", "risk management", "backtesting", "algorithmic trading", "portfolio risk"],
    "BUSINESS": ["new business models", "local service opportunities", "AI-enabled services", "funding", "small-business pain points"],
    "MARKETING": ["SEO", "content strategy", "YouTube growth", "lead generation", "conversion optimization", "local SEO"],
    "AI_NEXUS": ["agent frameworks", "MCP", "open-source AI", "automation", "RAG", "observability", "workflow systems"],
}
CLAIM_STATUSES = ("UNVERIFIED", "WEAKLY_SUPPORTED", "PARTIALLY_SUPPORTED", "SUPPORTED", "CONTRADICTED", "MIXED", "OUTDATED", "NOT_TESTABLE_YET")

def now() -> str: return datetime.now(timezone.utc).isoformat()
def cutoff(window: str = "LAST_30_DAYS") -> str:
    days = RECENCY_WINDOWS[window]
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat() if days is not None else ""
def digest(value: Any, prefix: str) -> str: return f"{prefix}_{hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()[:20]}"
def source_family(url: str) -> str:
    host = urllib.parse.urlparse(url).netloc.lower().removeprefix("www.")
    return host.split(":", 1)[0]
def source_registry_records() -> list[dict[str, Any]]:
    return [{"source_id": sid, "source_type": typ, "authority_level": auth, "access_method": "bounded_read", "read_only": ro, "provenance_required": True, "allowed_for_alpha": True, "health": "configured", "updated_at": now()} for sid, typ, auth, ro in SOURCE_REGISTRY]
def persist_registry() -> None:
    existing = {r.get("source_id") for r in read_records("alpha_source_registry")}
    for record in source_registry_records():
        if record["source_id"] not in existing: append_record("alpha_source_registry", record)
    for theme, terms in THEMES.items():
        if not any(r.get("theme_id") == theme for r in read_records("alpha_theme_registry")):
            append_record("alpha_theme_registry", {"theme_id": theme, "terms": terms, "default_window": "LAST_30_DAYS", "bounded": True, "created_at": now()})

def content_record(url: str, content_type: str, title: str, **extra: Any) -> dict[str, Any]:
    canonical = extra.pop("canonical_url", url)
    return {"content_id": digest(canonical, "content"), "content_type": content_type, "canonical_url": canonical, "title": title[:240], "source_family": source_family(canonical), "first_seen_at": now(), "last_seen_at": now(), "status": "DISCOVERED", **extra}
def claim_record(content_id: str, claim: str, claim_type: str = "general", **extra: Any) -> dict[str, Any]:
    return {"claim_id": digest({"content_id": content_id, "claim": claim}, "claim"), "content_id": content_id, "claim": claim[:1200], "claim_type": claim_type, "verification_status": "UNVERIFIED", "supporting_sources": [], "contrary_sources": [], **extra}
def evidence_score(*, authority: float, independence: float, currentness: float, directness: float, methodology: float = .5, conflict: float = 0.0) -> float:
    return round(max(0.0, min(1.0, .25*authority + .2*independence + .15*currentness + .2*directness + .15*methodology - .05*conflict)), 3)
def discovery_score(*, recency: float, relevance: float, novelty: float, diversity: float, commercial_intent: float, nexus_fit: float, testability: float) -> float:
    return round(max(0.0, min(1.0, .18*recency + .2*relevance + .12*novelty + .12*diversity + .12*commercial_intent + .16*nexus_fit + .1*testability)), 3)
def classify_claim(claim: dict[str, Any], support: Iterable[dict[str, Any]], contrary: Iterable[dict[str, Any]]) -> str:
    s, c = list(support), list(contrary)
    if c and s: return "MIXED"
    if c: return "CONTRADICTED"
    if len({x.get("source_family") for x in s}) >= 2 and claim.get("evidence_score", 0) >= .65: return "SUPPORTED"
    if s: return "PARTIALLY_SUPPORTED"
    return "UNVERIFIED"
def persist_content(record: dict[str, Any]) -> dict[str, Any]:
    if any(r.get("content_id") == record["content_id"] and r.get("content_hash") == record.get("content_hash") for r in read_records("alpha_content")): return {"stored": False, "duplicate": True}
    append_record("alpha_content", record); return {"stored": True, "duplicate": False}
def persist_claim(record: dict[str, Any]) -> dict[str, Any]:
    prior = next((r for r in read_records("alpha_claims") if r.get("claim_id") == record["claim_id"]), None)
    if prior and prior.get("verification_status") == record.get("verification_status") and prior.get("evidence_score") == record.get("evidence_score"): return {"stored": False, "duplicate": True}
    record = {**record, "revision": int(prior.get("revision", 0)) + 1 if prior else 1, "supersedes": prior.get("claim_id") if prior else None}
    append_record("alpha_claims", record); return {"stored": True, "duplicate": False, "revision": record["revision"]}
def retrieve_page(url: str, timeout: int = 20) -> dict[str, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": "NexusAlphaResearch/1.0", "Accept": "text/html,application/xhtml+xml"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response: raw = response.read(1_500_000).decode("utf-8", "replace"); final = response.geturl()
        title = re.search(r"<title[^>]*>(.*?)</title>", raw, re.I | re.S)
        text = re.sub(r"<script.*?</script>|<style.*?</style>|<[^>]+>", " ", raw, flags=re.I | re.S)
        text = re.sub(r"\s+", " ", html.unescape(text)).strip()
        return {"ok": True, "url": final, "title": (title.group(1).strip() if title else final)[:240], "text_hash": hashlib.sha256(text.encode()).hexdigest(), "excerpt": text[:1600], "retrieved_at": now(), "content_length": len(text)}
    except Exception as first_exc:
        # macOS installations can have a Python CA bundle mismatch even when
        # the governed curl/browser path is healthy. Use curl only as a
        # bounded public-read fallback; never pass credentials or cookies.
        try:
            proc = subprocess.run(["curl", "-L", "--fail", "--max-time", str(timeout), "-A", "NexusAlphaResearch/1.0", "-sS", url], capture_output=True, timeout=timeout + 5, check=False)
            if proc.returncode != 0: raise RuntimeError("curl_failed")
            raw = proc.stdout.decode("utf-8", "replace")[:1_500_000]
            title = re.search(r"<title[^>]*>(.*?)</title>", raw, re.I | re.S)
            text = re.sub(r"<script.*?</script>|<style.*?</style>|<[^>]+>", " ", raw, flags=re.I | re.S)
            text = re.sub(r"\s+", " ", html.unescape(text)).strip()
            return {"ok": True, "url": url, "title": (title.group(1).strip() if title else url)[:240], "text_hash": hashlib.sha256(text.encode()).hexdigest(), "excerpt": text[:1600], "retrieved_at": now(), "content_length": len(text), "retrieval_provider": "curl_fallback"}
        except Exception:
            return {"ok": False, "url": url, "error": first_exc.__class__.__name__, "retrieved_at": now()}
def youtube_transcript(url: str, timeout: int = 90) -> dict[str, Any]:
    video_id = urllib.parse.parse_qs(urllib.parse.urlparse(url).query).get("v", [""])[0] or url.rsplit("/", 1)[-1]
    with tempfile.TemporaryDirectory(prefix="nexus-alpha-youtube-") as tmp:
        output = str(Path(tmp) / "caption.%(ext)s")
        command = ["/usr/local/bin/yt-dlp", "--skip-download", "--write-auto-subs", "--write-subs", "--sub-langs", "en,en-US,en-GB", "--sub-format", "vtt", "--no-warnings", "--no-progress", "-o", output, url]
        try: proc = subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)
        except Exception as exc: return {"ok": False, "video_id": video_id, "status": "TRANSCRIPT_UNAVAILABLE", "error": exc.__class__.__name__}
        files = list(Path(tmp).glob("caption*.vtt"))
        if proc.returncode != 0 or not files: return {"ok": False, "video_id": video_id, "status": "TRANSCRIPT_UNAVAILABLE", "error": "captions_not_available"}
        raw = files[0].read_text(errors="replace")
        lines = [re.sub(r"<[^>]+>", "", x).strip() for x in raw.splitlines() if x.strip() and not x.strip().isdigit() and "-->" not in x]
        text = re.sub(r"\s+", " ", html.unescape(" ".join(lines))).strip()
        return {"ok": True, "video_id": video_id, "status": "TRANSCRIPT_RETRIEVED", "language": "en", "transcript_hash": hashlib.sha256(text.encode()).hexdigest(), "excerpt": text[:2400], "retrieved_at": now(), "media_downloaded": False, "audio_downloaded": False}
def route_finding(theme: str, research_id: str, finding: str) -> str:
    route = {"TRADING": "trading_research", "BUSINESS": "business_opportunity", "MARKETING": "growth_experiment_candidate", "AI_NEXUS": "nexus_capability_improvement"}.get(theme, "alpha_review")
    append_record("alpha_outcomes", {"outcome_id": digest({"research_id": research_id, "route": route}, "route"), "research_id": research_id, "route": route, "finding": finding[:800], "status": "CANDIDATE", "authority": "Nexus_review_required", "created_at": now()})
    return route
def create_research(theme: str, question: str, contents: list[dict[str, Any]], claims: list[dict[str, Any]], window: str = "LAST_30_DAYS") -> dict[str, Any]:
    research_id = digest({"theme": theme, "question": question, "contents": [x.get("content_id") for x in contents]}, "research")
    record = {"research_id": research_id, "theme": theme, "question": question[:500], "discovery_source": "bounded_alpha_discovery", "discovery_window": window, "candidate_content_ids": [x.get("content_id") for x in contents], "claims": [x.get("claim_id") for x in claims], "source_refs": [x.get("canonical_url") for x in contents], "support": [], "contrary_evidence": [], "evidence_quality": round(sum(x.get("evidence_score", 0) for x in claims) / len(claims), 3) if claims else 0.0, "status": "CHALLENGED" if claims else "SCREENED", "recommendation": "ROUTE_FOR_NEXUS_REVIEW", "routing": None, "created_at": now(), "updated_at": now()}
    if not any(r.get("research_id") == research_id for r in read_records("alpha_research")): append_record("alpha_research", record)
    return record
def bounded_budget(overrides: dict[str, int] | None = None) -> dict[str, int]:
    budget = {**DEFAULT_BUDGET, **(overrides or {})}
    return {k: max(0, int(v)) for k, v in budget.items()}
