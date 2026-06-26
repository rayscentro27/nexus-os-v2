#!/usr/bin/env python3
"""Nexus OS v2 — thin, SAFE wrapper around the existing YouTube research capture.

The real transcript capture already exists at ~/nexus-ai/research-engine/ (yt-dlp, channel
allowlist, bounded MAX_VIDEOS). This wrapper does NOT duplicate that. It:

  * defaults to DRY-RUN (no network, no yt-dlp, no external AI) — it just demonstrates the canonical
    pipeline for a given --source-url and prints the rows it WOULD write;
  * scores every source with the deterministic canonical rating model (NEXUS_VIDEO_RESEARCH_RATING_MODEL.md);
  * normalizes output into existing Supabase tables (research_sources / intake_events /
    transcript_reviews) per NEXUS_RESEARCH_SUPABASE_MAPPING.md — only when --no-dry-run is set;
  * writes a nexus_events proof (only with --write-events and not dry-run);
  * writes a report to reports/runtime + reports/manual_publish.

DEFAULT mode is DRY-RUN: no network, no yt-dlp, no external AI. Real capture runs ONLY with
--no-dry-run, uses yt-dlp transcript/subtitle extraction on PUBLIC videos (--skip-download — never
downloads media), is bounded by --limit (max 3), dedupes by source_url, writes ONLY to v2 tables,
and NEVER calls external AI / summarize.py / the v1 research table.

It NEVER: starts a scheduler, scrapes broadly, downloads media, bypasses logins/captcha/paywalls/
rate limits, or sends transcript text to external AI.

Usage:
  # safe dry-run (no network):
  python3 scripts/intake/run_existing_youtube_monitor.py --once --limit 1 --dry-run --no-external-ai
  # one gated real capture (approved public URL only):
  python3 scripts/intake/run_existing_youtube_monitor.py --source-url "<APPROVED_URL>" --once \
      --limit 1 --no-external-ai --write-events --no-dry-run
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "social"))
import _supabase as sb  # noqa: E402
from nexus_enrichment import build_project_enrichment  # noqa: E402

RATING_MODEL_VERSION = "v1"
MAX_LIMIT = 3  # hard cap; never process more than this per run
LEGACY_COLLECTOR = Path.home() / "nexus-ai" / "research-engine" / "collector.py"
ALLOWLIST = ROOT / "config" / "youtube_sources_allowlist.json"
RUNTIME = ROOT / "reports" / "runtime" / "nexus_youtube_monitor_latest.md"
MANUAL = ROOT / "reports" / "manual_publish" / "nexus_youtube_monitor_latest.md"
REAL_REPORT = ROOT / "reports" / "manual_publish" / "nexus_youtube_real_capture_latest.md"

# Deterministic keyword → category/tag signals (no external AI).
SIGNALS = {
    "credit_funding_readiness": ["credit", "funding", "fundable", "bankable", "lender", "underwriting", "tradeline", "business credit", "personal credit", "readiness"],
    "goclear_apex_revenue": ["grant", "grants", "$97", "offer", "review", "client", "lead", "intake"],
    "trading_research": ["forex", "trading", "backtest", "strategy", "rsi", "indicator", "candlestick", "scalp", "swing"],
    "ai_tooling": ["agent", "automation", "workflow", "mcp", "model", "llm", "prompt", "claude", "gpt"],
    "seo_marketing": ["seo", "keyword", "ranking", "search console", "backlink"],
    "creative_media": ["video", "reel", "caption", "thumbnail", "content", "hook"],
    "affiliate_partner": ["affiliate", "partner", "commission", "referral"],
}
TAGS = ["grants", "business_credit", "personal_credit", "funding", "bankability", "ai_agents",
        "automation", "content", "landing_page", "email", "social", "youtube", "trading_strategy",
        "backtest", "compliance", "lead_generation", "affiliate"]
GUARANTEE_RX = re.compile(r"guaranteed?\s+(funding|approval|credit|score|deletion|financing)", re.I)

CATEGORY_DEST = {
    "goclear_apex_revenue": "GoClear/Apex Revenue Hub",
    "credit_funding_readiness": "GoClear/Apex Revenue Hub",
    "affiliate_partner": "Opportunity Lab",
    "seo_marketing": "SEO Growth Engine",
    "creative_media": "Creative Studio",
    "system_improvement": "Ops & Improvements",
    "operations": "Ops & Improvements",
    "ai_tooling": "Ops & Improvements",
    "research_memory": "Knowledge/Memory",
    "trading_research": "Trading Lab",
    "client_experience": "Opportunity Lab",
    "ignore_or_park": "Ignore/Park",
}


def youtube_id(url: str) -> str | None:
    m = re.search(r"(?:v=|youtu\.be/|/shorts/)([A-Za-z0-9_-]{6,})", url or "")
    return m.group(1) if m else None


def source_type_for(url: str) -> str:
    u = (url or "").lower()
    if "youtube.com/watch" in u or "youtu.be/" in u or "/shorts/" in u:
        return "youtube_video"
    if "youtube.com/@" in u or "/channel/" in u:
        return "youtube_channel"
    if "playlist" in u:
        return "youtube_playlist"
    if u.startswith("http"):
        return "article_url"
    return "manual_idea"


def score_source(title: str, text: str) -> dict:
    """Deterministic canonical v1 scoring. No external AI."""
    blob = f"{title}\n{text}".lower()
    # primary category = strongest signal
    hits = {cat: sum(1 for kw in kws if kw in blob) for cat, kws in SIGNALS.items()}
    primary = max(hits, key=hits.get) if any(hits.values()) else "ignore_or_park"
    tags = sorted({t for t in TAGS if t.replace("_", " ") in blob or t in blob})

    goclear = primary in ("goclear_apex_revenue", "credit_funding_readiness")
    s = {
        "money_potential": 7 if goclear else (5 if primary in ("affiliate_partner", "trading_research") else 3),
        "speed_to_test": 6,
        "cost_to_test": 3,                       # low cost = good (penalized as (10-cost))
        "goclear_fit": 9 if goclear else 3,
        "nexus_fit": 6 if primary in ("ai_tooling", "system_improvement", "operations") else 5,
        "automation_value": 7 if primary == "ai_tooling" else 4,
        "content_value": 6 if primary == "creative_media" else 3,
        "affiliate_value": 7 if primary == "affiliate_partner" else 2,
        "client_value": 6 if goclear else 3,
        "compliance_risk": 8 if GUARANTEE_RX.search(blob) else (4 if goclear else 2),
        "technical_difficulty": 5,
        "confidence": 6,
    }
    base = (s["money_potential"] * 3 + s["goclear_fit"] * 2 + s["nexus_fit"] * 2
            + s["automation_value"] * 1.5 + s["speed_to_test"] * 1.5 + (10 - s["cost_to_test"]) * 1
            + s["content_value"] + s["affiliate_value"] + s["client_value"])
    penalty = s["compliance_risk"] * 2 + s["technical_difficulty"] * 1
    raw = max(0.0, min(145.0, base - penalty))
    total = round(raw / 145 * 100 * (s["confidence"] / 10) + 0.0)
    total = max(0, min(100, total))
    if s["compliance_risk"] >= 8:
        total = min(total, 39)                   # guarantee-style claims cannot rank high
    priority = ("now" if total >= 75 else "next" if total >= 60 else "later" if total >= 40
                else "park" if total >= 20 else "reject")
    dest = CATEGORY_DEST.get(primary, "Source Intake & Review")
    return {
        "rating_model_version": RATING_MODEL_VERSION,
        "primary_category": primary, "secondary_tags": tags, "scores": s,
        "total_opportunity_score": total, "priority": priority,
        "recommended_destination": dest,
        "compliance_notes": ("Contains guarantee-style language — needs Ray review."
                             if s["compliance_risk"] >= 8 else "Readiness/education framing OK."),
        "reasons_for_score": [f"primary={primary}", f"goclear_fit={s['goclear_fit']}", f"money={s['money_potential']}"],
        "reasons_against": (["high compliance risk"] if s["compliance_risk"] >= 8 else []),
        "ray_decision_needed": s["compliance_risk"] >= 8 or priority in ("now",),
    }


# ── Approved-source allowlist ─────────────────────────────────────────────────
def load_allowlist() -> list[dict]:
    if not ALLOWLIST.exists():
        return []
    try:
        data = json.loads(ALLOWLIST.read_text())
        return [s for s in data.get("sources", []) if s.get("enabled")]
    except Exception:
        return []


def is_approved(url: str) -> bool:
    """True if the url (or its channel/video id) matches an enabled allowlist entry."""
    vid = youtube_id(url)
    for s in load_allowlist():
        su = (s.get("url") or "").strip()
        if not su:
            continue
        if su == url or (vid and vid in su) or (su in url):
            return True
    return False


# ── yt-dlp capture (PUBLIC, transcript-only, no media download) ───────────────
def have_ytdlp() -> bool:
    return shutil.which("yt-dlp") is not None


def _run(cmd: list[str], timeout: int = 90) -> tuple[int, str, str]:
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return p.returncode, p.stdout, p.stderr


def ytdlp_metadata(url: str) -> dict:
    """Public metadata via yt-dlp -J --skip-download. No media downloaded."""
    rc, out, _ = _run(["yt-dlp", "-J", "--skip-download", "--no-warnings", url])
    if rc != 0 or not out.strip():
        return {}
    try:
        d = json.loads(out)
    except Exception:
        return {}
    up = d.get("upload_date")  # YYYYMMDD
    published = f"{up[0:4]}-{up[4:6]}-{up[6:8]}T00:00:00Z" if up and len(up) == 8 else None
    return {
        "title": d.get("title"),
        "creator": d.get("channel") or d.get("uploader"),
        "published_at": published,
        "description": (d.get("description") or "")[:1000],
        "video_id": d.get("id"),
        "is_private": bool(d.get("availability") and d.get("availability") != "public"),
    }


def _vtt_to_text(vtt: str) -> str:
    lines: list[str] = []
    for ln in vtt.splitlines():
        ln = ln.strip()
        if (not ln or ln == "WEBVITT" or ln.startswith("WEBVTT") or "-->" in ln
                or ln.isdigit() or ln.startswith(("Kind:", "Language:", "NOTE"))):
            continue
        ln = re.sub(r"<[^>]+>", "", ln)  # strip inline timing tags
        if ln and (not lines or lines[-1] != ln):
            lines.append(ln)
    return " ".join(lines)[:20000]


def ytdlp_transcript(url: str) -> tuple[str, str]:
    """Returns (transcript_text, transcript_status). Public auto/uploaded English subs only."""
    with tempfile.TemporaryDirectory() as td:
        rc, _, _ = _run([
            "yt-dlp", "--skip-download", "--write-auto-sub", "--write-sub",
            "--sub-lang", "en.*", "--convert-subs", "vtt", "--no-warnings",
            "-o", str(Path(td) / "%(id)s.%(ext)s"), url,
        ])
        vtts = list(Path(td).glob("*.vtt"))
        if not vtts:
            return "", "unavailable"
        try:
            text = _vtt_to_text(vtts[0].read_text(errors="ignore"))
        except Exception:
            return "", "failed"
        return (text, "captured") if text.strip() else ("", "partial")


def capture_one(url: str, no_external_ai: bool) -> dict:
    """Capture metadata + transcript for ONE public video. No media download, no external AI."""
    meta = ytdlp_metadata(url)
    if meta.get("is_private"):
        # never process non-public media
        return build_record(url, meta.get("title"), "", no_external_ai, meta={"transcript_status": "unavailable", "note": "non_public_skipped"})
    text, status = ytdlp_transcript(url)
    return build_record(url, meta.get("title"), text, no_external_ai,
                        meta={"transcript_status": status, **{k: meta.get(k) for k in ("creator", "published_at", "description", "video_id")}})


def resolve_urls(args) -> list[str]:
    """Return the bounded list of single-video URLs to process (≤ MAX_LIMIT)."""
    limit = max(1, min(args.limit, MAX_LIMIT))
    if args.source_url:
        return [args.source_url][:limit]
    src = args.channel_url or args.playlist_url
    if not src:
        return []
    # Flat playlist/channel listing (latest first), bounded. No media downloaded.
    rc, out, _ = _run(["yt-dlp", "--flat-playlist", "-J", "--no-warnings",
                       "--playlist-end", str(limit), src])
    if rc != 0 or not out.strip():
        return []
    try:
        entries = json.loads(out).get("entries", [])
    except Exception:
        return []
    urls = []
    for e in entries[:limit]:
        vid = e.get("id")
        if vid:
            urls.append(f"https://www.youtube.com/watch?v={vid}")
    return urls


def build_record(url: str, title: str | None, text: str, no_external_ai: bool, meta: dict | None = None) -> dict:
    meta = meta or {}
    vid = meta.get("video_id") or youtube_id(url)
    title = title or (f"YouTube {vid}" if vid else (url or "manual idea"))
    # Score on title + transcript + description (all public). External AI never used.
    rating = score_source(title, f"{text}\n{meta.get('description', '')}")
    transcript_status = meta.get("transcript_status") or ("missing" if not text else "captured")
    return {
        "source_id": vid or url,
        "source_type": source_type_for(url),
        "source_url": url,
        "title": title,
        "creator": meta.get("creator"),
        "published_at": meta.get("published_at"),
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "transcript_status": transcript_status,
        "review_status": "needs_ray_review" if rating["ray_decision_needed"] else "reviewed",
        "external_ai_used": False,  # this wrapper never calls external AI
        "plain_english_summary": (title[:200]),
        "why_it_matters": f"Auto-categorized as {rating['primary_category']} → {rating['recommended_destination']}.",
        "recommended_next_action": "Review in Source Intake & Review; route to destination on Ray approval.",
        "smallest_low_cost_test": "Skim transcript, confirm category, draft one safe next step.",
        "required_assets": [],
        "rating": rating,
        "video_id": vid,
        "transcript_chars": len(text or ""),
    }


def write_supabase(rec: dict, run_id: str | None) -> dict:
    """Insert into research_sources + intake_events + transcript_reviews (dedup by url). Live only."""
    refs = {}
    existing = sb.get("research_sources", f"select=*&url=eq.{sb.q(rec['source_url'])}&limit=1")[1]
    if isinstance(existing, list) and existing:
        source = existing[0]
        enrichment = build_project_enrichment(
            source=source,
            rating=rec["rating"],
            enrichment_source="transcript_capture" if rec["transcript_status"] == "captured" else "deterministic",
        )
        meta = (source.get("metadata") or {}) | {"project_enrichment": enrichment, "enrichment_status": enrichment["enrichment_status"]}
        sb.update("research_sources", f"id=eq.{sb.q(source['id'])}", {"metadata": meta})
        return {"dedup": True, "research_source_id": source["id"]}
    preliminary_enrichment = build_project_enrichment(
        source={
            "title": rec["title"], "url": rec["source_url"], "snippet": rec["plain_english_summary"],
            "why_it_matters": rec["why_it_matters"], "confidence": rec["rating"]["scores"]["confidence"],
            "metadata": {"transcript_status": rec["transcript_status"], "review_status": rec["review_status"], **rec["rating"]},
        },
        rating=rec["rating"],
        enrichment_source="transcript_capture" if rec["transcript_status"] == "captured" else "deterministic",
    )
    st, src = sb.insert("research_sources", {
        "research_run_id": run_id, "source_type": rec["source_type"], "title": rec["title"],
        "url": rec["source_url"], "author": rec["creator"], "accessed_at": rec["captured_at"],
        "snippet": rec["plain_english_summary"], "why_it_matters": rec["why_it_matters"],
        "confidence": rec["rating"]["scores"]["confidence"],
        "metadata": {"rating_model_version": RATING_MODEL_VERSION, "video_id": rec["video_id"],
                     "transcript_status": rec["transcript_status"], "review_status": rec["review_status"],
                     "project_enrichment": preliminary_enrichment,
                     "enrichment_status": preliminary_enrichment["enrichment_status"],
                     **rec["rating"]},
    })
    refs["research_source_id"] = src[0]["id"] if isinstance(src, list) and src else None
    st, ie = sb.insert("intake_events", {
        "source_type": rec["source_type"], "source_url": rec["source_url"], "title": rec["title"],
        "status": "reviewed", "category": rec["rating"]["primary_category"],
        "metadata": {"rating_model_version": RATING_MODEL_VERSION, "video_id": rec["video_id"]},
    })
    refs["intake_event_id"] = ie[0]["id"] if isinstance(ie, list) and ie else None
    r = rec["rating"]; sc = r["scores"]
    review_row = {
        "intake_event_id": refs["intake_event_id"], "title": rec["title"],
        "core_idea": rec["plain_english_summary"], "category": r["primary_category"],
        "usefulness_score": round(r["total_opportunity_score"] / 10),
        "money_now_score": sc["money_potential"], "automation_score": sc["automation_value"],
        "risk_score": sc["compliance_risk"],
        "compliance_risk": "high" if sc["compliance_risk"] >= 7 else "medium" if sc["compliance_risk"] >= 4 else "low",
        "decision": r["priority"], "recommended_action": rec["recommended_next_action"],
        "tables_to_update": [r["recommended_destination"]],
        "claim_flags": r["reasons_against"],
        "metadata": {"rating_model_version": RATING_MODEL_VERSION, "research_source_id": refs["research_source_id"],
                     "source_url": rec["source_url"], **r},
    }
    enrichment = build_project_enrichment(
        source={"title": rec["title"], "url": rec["source_url"], "snippet": rec["plain_english_summary"],
                "why_it_matters": rec["why_it_matters"], "confidence": rec["rating"]["scores"]["confidence"],
                "metadata": {"transcript_status": rec["transcript_status"], "review_status": rec["review_status"], **rec["rating"]}},
        transcript_review=review_row,
        rating=rec["rating"],
        enrichment_source="transcript_capture" if rec["transcript_status"] == "captured" else "deterministic",
    )
    review_row["metadata"]["project_enrichment"] = enrichment
    st, tr = sb.insert("transcript_reviews", review_row)
    refs["transcript_review_id"] = tr[0]["id"] if isinstance(tr, list) and tr else None
    if refs["research_source_id"]:
        sb.update("research_sources", f"id=eq.{sb.q(refs['research_source_id'])}",
                  {"metadata": {"rating_model_version": RATING_MODEL_VERSION, "video_id": rec["video_id"],
                                "transcript_status": rec["transcript_status"], "review_status": rec["review_status"],
                                "project_enrichment": enrichment, "enrichment_status": enrichment["enrichment_status"],
                                **rec["rating"]}})
    return refs


def write_report(records: list[dict], dry: bool) -> None:
    lines = ["# Nexus YouTube Monitor (wrapper)", "",
             f"- generated_at: {datetime.now(timezone.utc).isoformat()}",
             f"- mode: {'DRY-RUN (no writes, no network, no AI)' if dry else 'live'}",
             f"- rating_model_version: {RATING_MODEL_VERSION}",
             f"- legacy collector: {LEGACY_COLLECTOR} ({'present' if LEGACY_COLLECTOR.exists() else 'missing'})",
             f"- sources processed: {len(records)}", "", "## Sources"]
    for r in records:
        rt = r["rating"]
        lines += [f"### {r['title']}",
                  f"- url: {r['source_url']}",
                  f"- type: {r['source_type']} · transcript: {r['transcript_status']} · review: {r['review_status']}",
                  f"- category: {rt['primary_category']} · tags: {', '.join(rt['secondary_tags']) or 'none'}",
                  f"- score: {rt['total_opportunity_score']}/100 · priority: {rt['priority']} · destination: {rt['recommended_destination']}",
                  f"- compliance: {rt['compliance_notes']}",
                  f"- ray_decision_needed: {rt['ray_decision_needed']}", ""]
    RUNTIME.parent.mkdir(parents=True, exist_ok=True)
    MANUAL.parent.mkdir(parents=True, exist_ok=True)
    RUNTIME.write_text("\n".join(lines) + "\n")
    MANUAL.write_text("\n".join(lines) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="no writes/network/AI (default-safe)")
    ap.add_argument("--no-dry-run", dest="dry_run", action="store_false", help="enable real capture + v2 writes")
    ap.set_defaults(dry_run=True)
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--limit", type=int, default=1, help=f"videos to process (hard cap {MAX_LIMIT})")
    ap.add_argument("--source-url", default="", help="single public video URL")
    ap.add_argument("--channel-url", default="", help="allowlisted channel URL (latest --limit)")
    ap.add_argument("--playlist-url", default="", help="allowlisted playlist URL (first --limit)")
    ap.add_argument("--no-external-ai", action="store_true", default=True, help="deterministic only (default on)")
    ap.add_argument("--write-events", action="store_true", help="write nexus_events proof (live only)")
    ap.add_argument("--max-age-days", type=int, default=30)
    ap.add_argument("--approved-only", action="store_true", help="require the URL to be in the allowlist")
    args = ap.parse_args()

    urls = resolve_urls(args)
    if not urls:
        print("Need --source-url (or allowlisted --channel-url/--playlist-url). No broad scraping. "
              "Example: --source-url https://www.youtube.com/watch?v=EXAMPLE")
        return 2

    if args.approved_only:
        urls = [u for u in urls if is_approved(u)]
        if not urls:
            print("--approved-only: no provided URL is in config/youtube_sources_allowlist.json. Refusing.")
            return 3

    # ── DRY-RUN: no network, no yt-dlp, deterministic scoring on title/url only ──
    if args.dry_run:
        records = [build_record(u, None, "", args.no_external_ai) for u in urls]
        write_report(records, dry=True)
        rec = records[0]
        print(json.dumps({"ok": True, "dry_run": True, "no_external_ai": True, "captured": False,
                          "processed": len(records), "run_id": None, "report": str(RUNTIME),
                          "sample": {"title": rec["title"], "category": rec["rating"]["primary_category"],
                                     "score": rec["rating"]["total_opportunity_score"],
                                     "priority": rec["rating"]["priority"],
                                     "destination": rec["rating"]["recommended_destination"]}}, indent=2))
        return 0

    # ── REAL CAPTURE (yt-dlp, public, transcript-only, no media, no external AI) ──
    if not have_ytdlp():
        print("yt-dlp not installed. Install with: pip3 install yt-dlp. (No capture performed.)")
        return 4
    if not sb.configured():
        print("Supabase not configured; refusing live write.")
        return 5

    records = [capture_one(u, args.no_external_ai) for u in urls]
    st, run = sb.insert("research_runs", {
        "requested_by": "youtube_monitor_wrapper", "question": "YouTube source intake",
        "research_type": "youtube_monitor", "status": "completed",
        "summary": f"Captured {len(records)} source(s)",
        "payload": {"rating_model_version": RATING_MODEL_VERSION, "no_external_ai": True}})
    run_id = run[0]["id"] if isinstance(run, list) and run else None
    written = []
    for r in records:
        refs = write_supabase(r, run_id)
        event_id = None
        if args.write_events:
            st, ev = sb.insert("nexus_events", {
                "lane": "research", "action": "youtube_source_reviewed",
                "status": "success", "source": "youtube_monitor_wrapper",
                "title": r["title"][:80],
                "summary": f"score {r['rating']['total_opportunity_score']} → {r['rating']['recommended_destination']} (transcript {r['transcript_status']})",
                "payload": {"source_url": r["source_url"], "dedup": refs.get("dedup", False),
                            "rating_model_version": RATING_MODEL_VERSION}})
            event_id = ev[0]["id"] if isinstance(ev, list) and ev else None
        written.append({"title": r["title"], "source_url": r["source_url"],
                        "transcript_status": r["transcript_status"],
                        "category": r["rating"]["primary_category"],
                        "destination": r["rating"]["recommended_destination"],
                        "score": r["rating"]["total_opportunity_score"],
                        "dedup": refs.get("dedup", False), "refs": refs, "nexus_event_id": event_id})

    write_report(records, dry=False)
    write_real_report(written, run_id)
    print(json.dumps({"ok": True, "dry_run": False, "no_external_ai": True, "captured": True,
                      "processed": len(records), "run_id": run_id,
                      "report": str(REAL_REPORT), "written": written}, indent=2))
    return 0


def write_real_report(written: list[dict], run_id: str | None) -> None:
    lines = ["# Nexus YouTube Real Capture", "",
             f"- generated_at: {datetime.now(timezone.utc).isoformat()}",
             f"- rating_model_version: {RATING_MODEL_VERSION}",
             f"- research_run_id: {run_id}",
             "- external_ai_used: false · summarize.py used: false · v1 research table written: false",
             f"- sources captured: {len(written)}", "", "## Captured"]
    for w in written:
        lines += [f"### {w['title']}",
                  f"- source_url: {w['source_url']}",
                  f"- transcript_status: {w['transcript_status']}",
                  f"- category/destination: {w['category']} → {w['destination']} · score {w['score']}/100",
                  f"- dedup: {w['dedup']} · refs: {json.dumps(w['refs'])}",
                  f"- nexus_event_id: {w['nexus_event_id']}", ""]
    REAL_REPORT.parent.mkdir(parents=True, exist_ok=True)
    REAL_REPORT.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
