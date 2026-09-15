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
from html.parser import HTMLParser
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

def source_adapter_for_url(url: str, *, content_hint: str = "") -> str:
    """Choose the bounded capture adapter; downstream intelligence is shared."""
    parsed = urllib.parse.urlparse(url)
    host, path = parsed.netloc.lower(), parsed.path.lower()
    if host.endswith("youtube.com") and ("/watch" in path or parsed.query): return "YOUTUBE"
    if host.endswith("github.com"): return "GITHUB"
    if path.endswith(".pdf"): return "PDF"
    if "reddit.com/r/" in host + path or "reddit.com/comments/" in host + path: return "REDDIT_THREAD"
    if any(x in host for x in ("forum.", "community.", "discourse.", "boards.")) or any(x in path for x in ("/forum/", "/discussion/", "/t/")):
        return "FORUM_THREAD"
    if any(x in content_hint.lower() for x in ("discussion", "replies", "post author")): return "FORUM_THREAD"
    if any(x in path for x in ("/blog/", "/article/", "/news/")): return "ARTICLE_OR_BLOG"
    return "STATIC_WEB_PAGE"

class _ForumHTML(HTMLParser):
    """Small Discourse-compatible parser; preserves post boundaries and metadata."""
    def __init__(self):
        super().__init__(); self.posts=[]; self.current=None; self.buf=[]; self.title=""; self.in_title=False; self.in_body=False
    def handle_starttag(self, tag, attrs):
        a=dict(attrs)
        if tag == "title": self.in_title=True
        if a.get("itemprop") == "articleBody" or "post" in (a.get("class") or ""):
            if self.current and self.buf: self.current["body"]=" ".join(self.buf).strip(); self.buf=[]
            self.current={"author":None,"date":None,"body":"","outbound_links":[]}; self.posts.append(self.current); self.in_body=True
        if self.current and tag == "a" and a.get("href","").startswith(("http://","https://")):
            self.current["outbound_links"].append(a["href"])
        if self.current and tag == "time": self.current["date"]=a.get("datetime")
        if self.current and a.get("itemprop") == "name": self.current["author"]=""
    def handle_endtag(self, tag):
        if tag == "title": self.in_title=False
        if tag in ("p","div","br","li") and self.in_body: self.buf.append(" ")
    def handle_data(self, data):
        if self.in_title: self.title += data
        if self.current and self.in_body: self.buf.append(data)
    def result(self):
        if self.current and self.buf: self.current["body"]=" ".join(self.buf).strip()
        return {"title": re.sub(r"\s+"," ",self.title).strip(), "posts":[p for p in self.posts if p.get("body")], "parser":"discourse_html"}

def extract_forum_thread(raw_html: str, url: str, *, fetched_at: str) -> dict[str, Any]:
    # Prefer the explicit Discourse crawler post boundary.  The generic HTML
    # parser is retained for compatible forum pages, but must not treat
    # ``crawler-post-meta`` and other nested elements as separate posts.
    posts=[]
    blocks=re.findall(r"<div[^>]+class=['\"]post['\"][^>]*itemprop=['\"]text['\"][^>]*>(.*?)</div>\s*</div>", raw_html or "", re.I|re.S)
    if not blocks:
        parser=_ForumHTML(); parser.feed(raw_html or ""); posts=parser.result()["posts"]
    authors=re.findall(r"class=['\"]creator['\"][\s\S]{0,500}?itemprop=['\"]name['\"][^>]*>\s*([^<]+)", raw_html or "", re.I)
    dates=re.findall(r"<time[^>]+datetime=['\"]([^'\"]+)", raw_html or "", re.I)
    for i,block in enumerate(blocks):
        body=re.sub(r"<script.*?</script>|<style.*?</style>|<[^>]+>"," ",block,flags=re.I|re.S)
        body=re.sub(r"\s+"," ",html.unescape(body)).strip()
        links=re.findall(r"<a[^>]+href=['\"](https?://[^'\"]+)",block,re.I)
        posts.append({"author":re.sub(r"\s+"," ",authors[i]).strip() if i<len(authors) else None,
                      "date":dates[i] if i<len(dates) else None,"body":body,
                      "outbound_links":list(dict.fromkeys(links)),"post_order":i+1})
    for i,p in enumerate(posts):
        p.setdefault("post_order",i+1)
    title=re.search(r"<title[^>]*>(.*?)</title>",raw_html or "",re.I|re.S)
    thread_title=re.sub(r"\s+"," ",html.unescape(title.group(1))).strip() if title else url
    text=" ".join(p["body"] for p in posts)
    return {"url":url,"retrieved_at":fetched_at,"text":text,"post_count":len(posts),"posts":posts,"thread_title":thread_title,"parser":"discourse_thread_boundary"}
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
    return {"content_id": digest(canonical, "content"), "source_id": digest(canonical, "source"), "content_type": content_type, "canonical_url": canonical, "title": title[:240], "source_family": source_family(canonical), "first_seen_at": now(), "last_seen_at": now(), "status": "DISCOVERED", **extra}
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
    # ``content_id`` is the canonical identity (derived from the canonical
    # source locator).  A changed title/excerpt must not create a second
    # intelligence item or inflate the Research "new" counter.
    prior = next((r for r in read_records("alpha_content") if r.get("content_id") == record["content_id"]), None)
    if prior:
        prior_spans = len(prior.get("evidence_spans") or [])
        new_spans = len(record.get("evidence_spans") or [])
        richer = (new_spans > prior_spans
                  or record.get("transcript_hash") != prior.get("transcript_hash")
                  or record.get("transcript_method") != prior.get("transcript_method")
                  or record.get("review_status") != prior.get("review_status"))
        if not richer:
            return {"stored": False, "duplicate": True}
        revised = {**record, "revision": int(prior.get("revision", 1)) + 1, "supersedes": record["content_id"]}
        append_record("alpha_content", revised)
        return {"stored": True, "duplicate": False, "revision": revised["revision"]}
    append_record("alpha_content", record); return {"stored": True, "duplicate": False}
def persist_claim(record: dict[str, Any]) -> dict[str, Any]:
    prior = next((r for r in read_records("alpha_claims") if r.get("claim_id") == record["claim_id"]), None)
    if prior and prior.get("verification_status") == record.get("verification_status") and prior.get("evidence_score") == record.get("evidence_score") and prior.get("source_transcript_path") == record.get("source_transcript_path") and prior.get("validation_result") == record.get("validation_result"): return {"stored": False, "duplicate": True}
    record = {**record, "revision": int(prior.get("revision", 0)) + 1 if prior else 1, "supersedes": prior.get("claim_id") if prior else None}
    append_record("alpha_claims", record); return {"stored": True, "duplicate": False, "revision": record["revision"]}

def extract_evidence_spans(text: str, *, source_id: str, source_url: str, title: str, fetched_at: str, content_hash: str) -> list[dict[str, Any]]:
    """Return bounded, real character spans from extracted page text."""
    spans = []
    for match in re.finditer(r"[^.!?]{35,500}[.!?]", text or ""):
        evidence = match.group(0).strip()
        if len(evidence) < 35:
            continue
        spans.append({"span_id": digest({source_id, match.start(), evidence}, "span"), "source_id": source_id,
                      "source_url": source_url, "source_title": title, "evidence_text": evidence,
                      "evidence_start": match.start(), "evidence_end": match.end(), "section_or_heading": None,
                      "fetched_at": fetched_at, "content_hash": content_hash})
        if len(spans) >= 6:
            break
    return spans

def extract_related_links(raw: str, parent_source_id: str, *, lane: str = "GENERAL") -> list[dict[str, Any]]:
    """Select substantive outbound links, excluding navigation noise."""
    found = []
    seen = set()
    for href, anchor in re.findall(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', raw or "", re.I | re.S):
        url = urllib.parse.urljoin("https://placeholder.invalid/", html.unescape(href).strip())
        if "placeholder.invalid" in url or not url.startswith(("http://", "https://")):
            continue
        clean = urllib.parse.urlsplit(url)._replace(fragment="").geturl()
        host = source_family(clean)
        path = urllib.parse.urlsplit(clean).path.lower()
        label = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", anchor)).strip()[:180]
        hay = f"{label} {clean}".lower()
        if clean in seen or (host in {"youtube.com", "tv.youtube.com"} and any(path.startswith(x) for x in ("/about", "/creators", "/ads", "/howyoutubeworks", "/watch"))) or any(x in hay for x in ("privacy", "cookie", "login", "sign in", "subscribe", "facebook.com", "twitter.com")):
            continue
        if not (label or any(x in hay for x in ("sba", "grant", "fund", "credit", "github", "youtube", "research", "data", "program"))):
            continue
        seen.add(clean)
        found.append({"parent_source_id": parent_source_id, "discovered_url": clean, "discovery_reason": "outbound_link_or_named_reference",
                      "anchor_or_reference": label or host, "research_lane": lane, "relevance_score": .7 if label else .55, "status": "CANDIDATE"})
        if len(found) >= 20:
            break
    return found

def extract_named_entities(text: str) -> list[str]:
    """Extract bounded, reviewable entity candidates from real content."""
    candidates = []
    for value in re.findall(r"\b[A-Z][A-Za-z0-9&.-]{2,}(?:\s+[A-Z][A-Za-z0-9&.-]{2,}){0,2}", text or ""):
        value = value.strip(" .,:;!?()[]{}")
        if value not in candidates and value.lower() not in {"the", "this", "what", "how", "you"}:
            candidates.append(value)
        if len(candidates) >= 20:
            break
    return candidates

def generated_questions(*, content: dict[str, Any], spans: list[dict[str, Any]], related: list[dict[str, Any]], parent_goal: str = "") -> list[dict[str, Any]]:
    base = ["Which claims from this source require independent verification?", "What related source or alternative should Research inspect next?"]
    return [{"question_id": digest({content["content_id"], q}, "question"), "question": q,
             "source_or_finding_origin": content["canonical_url"], "parent_goal": parent_goal,
             "why_it_matters": "Convert source evidence into a bounded next investigation.",
             "decision_supported": "research prioritization", "priority": "P2", "status": "OPEN",
             "source_id": content["source_id"], "next_action": "research.cross_check"} for q in base[:max(1, min(2, len(spans) + len(related)))]
            ]
def retrieve_page(url: str, timeout: int = 20) -> dict[str, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": "NexusAlphaResearch/1.0", "Accept": "text/html,application/xhtml+xml"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response: raw = response.read(1_500_000).decode("utf-8", "replace"); final = response.geturl()
        title = re.search(r"<title[^>]*>(.*?)</title>", raw, re.I | re.S)
        text = re.sub(r"<script.*?</script>|<style.*?</style>|<[^>]+>", " ", raw, flags=re.I | re.S)
        text = re.sub(r"\s+", " ", html.unescape(text)).strip()
        fetched = now(); title_text = (title.group(1).strip() if title else final)[:240]; content_hash = hashlib.sha256(text.encode()).hexdigest()
        return {"ok": True, "url": final, "title": title_text, "text_hash": content_hash, "excerpt": text[:1600], "text": text[:12000], "raw_html": raw, "retrieved_at": fetched, "content_length": len(text)}
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
            fetched = now(); title_text = (title.group(1).strip() if title else url)[:240]; content_hash = hashlib.sha256(text.encode()).hexdigest()
            return {"ok": True, "url": url, "title": title_text, "text_hash": content_hash, "excerpt": text[:1600], "text": text[:12000], "raw_html": raw, "retrieved_at": fetched, "content_length": len(text), "retrieval_provider": "curl_fallback"}
        except Exception:
            return {"ok": False, "url": url, "error": first_exc.__class__.__name__, "retrieved_at": now()}
def _asr_python() -> str | None:
    """Locate the certified isolated faster-whisper runtime without adding dependencies."""
    configured = os.environ.get("NEXUS_FASTER_WHISPER_PYTHON", "").strip()
    candidates = [configured] if configured else []
    candidates += sorted(str(p) for p in Path("/tmp").glob("nexus-faster-whisper*/bin/python"))
    candidates += [str(ROOT / ".venv-faster-whisper" / "bin" / "python")]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            try:
                probe = subprocess.run([candidate, "-c", "import faster_whisper"], capture_output=True, timeout=8, check=False)
                if probe.returncode == 0:
                    return candidate
            except (OSError, subprocess.TimeoutExpired):
                continue
    return None


def _whisper_cpp_runtime() -> tuple[str, str] | None:
    """Use the already-provisioned Nexus whisper.cpp runtime as a local fallback."""
    binary = ROOT / "tools" / "voice" / "runtime" / "whisper.cpp" / "build" / "bin" / "whisper-cli"
    model = ROOT / "tools" / "voice" / "models" / "ggml-base.en.bin"
    return (str(binary), str(model)) if binary.is_file() and model.is_file() else None


def _normalize_caption_text(value: str) -> str:
    """Remove caption container noise and rolling duplicate lines."""
    lines = []
    for raw_line in (value or "").splitlines():
        line = re.sub(r"<[^>]+>", "", raw_line).strip()
        if not line or line.isdigit() or "-->" in line or line.upper().startswith("WEBVTT"):
            continue
        if lines and line == lines[-1]:
            continue
        lines.append(line)
    return re.sub(r"\s+", " ", html.unescape(" ".join(lines))).strip()


def _local_asr_fallback(*, url: str, video_id: str, caption_failure_type: str, timeout: int) -> dict[str, Any]:
    """Recover transcript after caption failure using the certified local ASR ladder."""
    asr_python = _asr_python()
    whisper_cpp = _whisper_cpp_runtime()
    if not asr_python and not whisper_cpp:
        return {"ok": False, "video_id": video_id, "status": "ASR_UNAVAILABLE", "caption_failure_type": caption_failure_type, "asr_failure": "certified_runtime_not_found"}
    with tempfile.TemporaryDirectory(prefix="nexus-alpha-youtube-media-") as tmp:
        media = Path(tmp) / "media.%(ext)s"
        manifest = subprocess.run(["/usr/local/bin/yt-dlp", "--skip-download", "--dump-single-json", "--no-warnings", "--no-progress", url], capture_output=True, text=True, timeout=min(timeout, 45), check=False)
        if manifest.returncode != 0:
            return {"ok": False, "video_id": video_id, "status": "MEDIA_FORMAT_DISCOVERY_FAILED", "caption_failure_type": caption_failure_type, "media_retrieval_error": "yt_dlp_manifest_failed"}
        try:
            info = json.loads(manifest.stdout)
        except json.JSONDecodeError:
            return {"ok": False, "video_id": video_id, "status": "MEDIA_FORMAT_DISCOVERY_FAILED", "caption_failure_type": caption_failure_type, "media_retrieval_error": "invalid_manifest"}
        formats = [x for x in info.get("formats", []) if x.get("url") and x.get("acodec") not in (None, "none")]
        audio_only = [x for x in formats if x.get("vcodec") in (None, "none")]
        progressive = [x for x in formats if x.get("vcodec") not in (None, "none")]
        selected = max(audio_only or progressive, key=lambda x: (x.get("abr") or 0, x.get("tbr") or 0, x.get("height") or 0)) if (audio_only or progressive) else None
        if not selected:
            return {"ok": False, "video_id": video_id, "status": "MEDIA_FORMAT_UNAVAILABLE", "caption_failure_type": caption_failure_type, "media_retrieval_error": "no_audio_or_progressive_format"}
        media_proc = subprocess.run(["/usr/local/bin/yt-dlp", "--no-warnings", "--no-progress", "--format", str(selected.get("format_id")), "--output", str(media), url], capture_output=True, text=True, timeout=min(max(timeout, 120), 240), check=False)
        media_files = [p for p in Path(tmp).glob("media.*") if p.is_file()]
        if media_proc.returncode != 0 or not media_files:
            return {"ok": False, "video_id": video_id, "status": "MEDIA_RETRIEVAL_FAILED", "caption_failure_type": caption_failure_type, "media_format_selected": selected.get("format_id"), "media_retrieval_error": "yt_dlp_media_failed"}
        wav = Path(tmp) / "audio.wav"
        audio_proc = subprocess.run(["/usr/local/bin/ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(media_files[0]), "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(wav)], capture_output=True, text=True, timeout=60, check=False)
        if audio_proc.returncode != 0 or not wav.exists():
            return {"ok": False, "video_id": video_id, "status": "FFMPEG_FAILED", "caption_failure_type": caption_failure_type, "media_format_selected": selected.get("format_id"), "ffmpeg_error": "audio_extraction_failed"}
        script = r'''import json, sys
from faster_whisper import WhisperModel
model = WhisperModel("tiny.en", device="cpu", compute_type="int8")
segments, info = model.transcribe(sys.argv[1], language="en", beam_size=1, vad_filter=True)
rows = [{"start": round(s.start, 2), "end": round(s.end, 2), "text": (s.text or "").strip()} for s in segments if (s.text or "").strip()]
print(json.dumps({"segments": rows}, ensure_ascii=False))
'''
        if asr_python:
            asr_proc = subprocess.run([asr_python, "-c", script, str(wav)], capture_output=True, text=True, timeout=min(max(timeout, 120), 300), check=False)
            if asr_proc.returncode != 0:
                return {"ok": False, "video_id": video_id, "status": "ASR_FAILED", "caption_failure_type": caption_failure_type, "media_format_selected": selected.get("format_id"), "asr_failure": "faster_whisper_failed"}
            try:
                decoded = json.loads(asr_proc.stdout)
                segments = decoded.get("segments") or []
            except json.JSONDecodeError:
                segments = []
            asr_engine, asr_version, asr_model = "faster-whisper", "1.2.1", "tiny.en"
        else:
            binary, model = whisper_cpp
            output_base = Path(tmp) / "whisper_result"
            asr_proc = subprocess.run([binary, "-m", model, "-f", str(wav), "-l", "en", "--no-prints", "--output-json-full", "--output-file", str(output_base)], capture_output=True, text=True, timeout=min(max(timeout, 120), 300), check=False)
            json_path = output_base.with_suffix(".json")
            if asr_proc.returncode != 0 or not json_path.exists():
                return {"ok": False, "video_id": video_id, "status": "ASR_FAILED", "caption_failure_type": caption_failure_type, "media_format_selected": selected.get("format_id"), "asr_failure": "whisper_cpp_failed"}
            try:
                decoded = json.loads(json_path.read_text(encoding="utf-8"))
                segments = decoded.get("transcription") or decoded.get("segments") or []
            except (OSError, json.JSONDecodeError):
                segments = []
            normalized = []
            for item in segments:
                stamp = item.get("timestamps") or {}
                def seconds(value: Any) -> float:
                    try:
                        if isinstance(value, (int, float)): return float(value)
                        parts = str(value).replace(",", ".").split(":")
                        return sum(float(part) * (60 ** (len(parts) - index - 1)) for index, part in enumerate(parts))
                    except (TypeError, ValueError): return 0.0
                normalized.append({"start": seconds(stamp.get("from", 0)), "end": seconds(stamp.get("to", 0)), "text": str(item.get("text") or "").strip()})
            segments = [item for item in normalized if item["text"]]
            asr_engine, asr_version, asr_model = "whisper.cpp", "repository-runtime", Path(model).name
        text = re.sub(r"\s+", " ", " ".join(x.get("text", "") for x in segments)).strip()
        if not text:
            return {"ok": False, "video_id": video_id, "status": "ASR_EMPTY", "caption_failure_type": caption_failure_type, "media_format_selected": selected.get("format_id")}
        artifact_dir = ROOT / "reports" / "runtime" / "youtube_transcripts"
        artifact_dir.mkdir(parents=True, exist_ok=True)
        artifact = artifact_dir / f"{video_id}_local_asr.txt"
        artifact.write_text(text + "\n", encoding="utf-8")
        timestamped = artifact_dir / f"{video_id}_local_asr_timestamped.txt"
        timestamped.write_text("\n".join(f"[{x['start']:.2f} - {x['end']:.2f}] {x['text']}" for x in segments) + "\n", encoding="utf-8")
        return {"ok": True, "video_id": video_id, "status": "TRANSCRIPT_RETRIEVED", "language": "en", "transcript_hash": hashlib.sha256(text.encode()).hexdigest(), "transcript": text, "excerpt": text[:2400], "transcript_artifact": str(artifact), "timestamped_artifact": str(timestamped), "retrieved_at": now(), "media_downloaded": True, "audio_downloaded": True, "media_format_selected": selected.get("format_id"), "media_format_kind": "AUDIO_ONLY" if selected in audio_only else "PROGRESSIVE_VIDEO_AUDIO", "ffmpeg_audio_extraction": "PASS_REAL", "transcript_method": "LOCAL_ASR", "asr_engine": asr_engine, "asr_version": asr_version, "asr_model": asr_model, "caption_failure_type": caption_failure_type}


def youtube_transcript(url: str, timeout: int = 90) -> dict[str, Any]:
    video_id = urllib.parse.parse_qs(urllib.parse.urlparse(url).query).get("v", [""])[0] or url.rsplit("/", 1)[-1]
    with tempfile.TemporaryDirectory(prefix="nexus-alpha-youtube-") as tmp:
        output = str(Path(tmp) / "caption.%(ext)s")
        command = ["/usr/local/bin/yt-dlp", "--skip-download", "--write-auto-subs", "--write-subs", "--sub-langs", "en,en-US,en-GB", "--sub-format", "vtt", "--no-warnings", "--no-progress", "-o", output, url]
        try: proc = subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)
        except subprocess.TimeoutExpired: return _local_asr_fallback(url=url, video_id=video_id, caption_failure_type="CAPTION_TIMEOUT", timeout=timeout)
        except Exception as exc: return _local_asr_fallback(url=url, video_id=video_id, caption_failure_type="CAPTION_OTHER_RECOVERABLE", timeout=timeout)
        files = list(Path(tmp).glob("caption*.vtt"))
        if proc.returncode != 0 or not files:
            failure = "CAPTION_HTTP_429" if "429" in ((proc.stderr or "") + (proc.stdout or "")) else "CAPTION_UNAVAILABLE"
            return _local_asr_fallback(url=url, video_id=video_id, caption_failure_type=failure, timeout=timeout)
        description = ""
        try:
            info = subprocess.run(["/usr/local/bin/yt-dlp", "--skip-download", "--print", "%(description)s", "--no-warnings", "--no-progress", url], capture_output=True, text=True, timeout=20, check=False)
            description = info.stdout[:5000]
        except Exception:
            description = ""
        raw = files[0].read_text(errors="replace")
        text = _normalize_caption_text(raw)
        metadata = {}
        try:
            info = subprocess.run(["/usr/local/bin/yt-dlp", "--skip-download", "--print", "%(title)s\\t%(channel)s\\t%(upload_date)s", "--no-warnings", "--no-progress", url], capture_output=True, text=True, timeout=20, check=False)
            parts = (info.stdout or "").strip().split("\\t")
            metadata = {"title": parts[0] if len(parts) > 0 else None, "channel": parts[1] if len(parts) > 1 else None, "upload_date": parts[2] if len(parts) > 2 else None}
        except Exception:
            metadata = {}
        return {"ok": True, "video_id": video_id, "status": "TRANSCRIPT_RETRIEVED", "language": "en", "transcript_hash": hashlib.sha256(text.encode()).hexdigest(), "transcript": text, "excerpt": text[:2400], "description": description[:5000], "retrieved_at": now(), "media_downloaded": False, "audio_downloaded": False, "transcript_method": "AUTO_CAPTION", **metadata}
def route_finding(theme: str, research_id: str, finding: str) -> str:
    route = {"TRADING": "trading_research", "BUSINESS": "business_opportunity", "MARKETING": "growth_experiment_candidate", "AI_NEXUS": "nexus_capability_improvement"}.get(theme, "alpha_review")
    work_order_id = digest({"research_id": research_id, "route": route}, "wo")
    if not any(r.get("work_order_id") == work_order_id for r in read_records("work_orders")):
        append_record("work_orders", {"work_order_id": work_order_id, "work_type": "alpha_research", "owner_specialist": "ALPHA", "required_capabilities": ["research", "verification"], "status": "ASSIGNED", "research_id": research_id, "route": route, "inputs": {"finding": finding[:800]}, "authority": "bounded_internal_research", "created_at": now()})
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
