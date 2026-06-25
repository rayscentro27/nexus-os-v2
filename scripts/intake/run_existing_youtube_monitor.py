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

It NEVER: starts a scheduler, scrapes broadly, downloads private/unlisted media, bypasses logins/
captcha/paywalls, or sends private data to external AI. Real capture (yt-dlp shell-out to the legacy
collector) is gated behind --no-dry-run AND --allow-capture and is intentionally NOT enabled here.

Usage (safe demo):
  python3 scripts/intake/run_existing_youtube_monitor.py --once --limit 1 --dry-run --no-external-ai \
      --source-url https://www.youtube.com/watch?v=EXAMPLE
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "social"))
import _supabase as sb  # noqa: E402

RATING_MODEL_VERSION = "v1"
LEGACY_COLLECTOR = Path.home() / "nexus-ai" / "research-engine" / "collector.py"
RUNTIME = ROOT / "reports" / "runtime" / "nexus_youtube_monitor_latest.md"
MANUAL = ROOT / "reports" / "manual_publish" / "nexus_youtube_monitor_latest.md"

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


def build_record(url: str, title: str | None, text: str, no_external_ai: bool) -> dict:
    vid = youtube_id(url)
    title = title or (f"YouTube {vid}" if vid else (url or "manual idea"))
    rating = score_source(title, text)
    return {
        "source_id": vid or url,
        "source_type": source_type_for(url),
        "source_url": url,
        "title": title,
        "creator": None,
        "published_at": None,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "transcript_status": "missing" if not text else "captured",
        "review_status": "needs_ray_review" if rating["ray_decision_needed"] else "reviewed",
        "external_ai_used": (not no_external_ai),
        "plain_english_summary": (title[:200]),
        "why_it_matters": f"Auto-categorized as {rating['primary_category']} → {rating['recommended_destination']}.",
        "recommended_next_action": "Review in Source Intake & Review; route to destination on Ray approval.",
        "smallest_low_cost_test": "Skim transcript, confirm category, draft one safe next step.",
        "required_assets": [],
        "rating": rating,
        "video_id": vid,
    }


def write_supabase(rec: dict, run_id: str | None) -> dict:
    """Insert into research_sources + intake_events + transcript_reviews (dedup by url). Live only."""
    refs = {}
    existing = sb.get("research_sources", f"select=id&url=eq.{sb.q(rec['source_url'])}&limit=1")[1]
    if isinstance(existing, list) and existing:
        return {"dedup": True, "research_source_id": existing[0]["id"]}
    st, src = sb.insert("research_sources", {
        "research_run_id": run_id, "source_type": rec["source_type"], "title": rec["title"],
        "url": rec["source_url"], "author": rec["creator"], "accessed_at": rec["captured_at"],
        "snippet": rec["plain_english_summary"], "why_it_matters": rec["why_it_matters"],
        "confidence": rec["rating"]["scores"]["confidence"],
        "metadata": {"rating_model_version": RATING_MODEL_VERSION, "video_id": rec["video_id"],
                     "transcript_status": rec["transcript_status"], "review_status": rec["review_status"],
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
    sb.insert("transcript_reviews", {
        "intake_event_id": refs["intake_event_id"], "title": rec["title"],
        "core_idea": rec["plain_english_summary"], "category": r["primary_category"],
        "usefulness_score": round(r["total_opportunity_score"] / 10),
        "money_now_score": sc["money_potential"], "automation_score": sc["automation_value"],
        "risk_score": sc["compliance_risk"],
        "compliance_risk": "high" if sc["compliance_risk"] >= 7 else "medium" if sc["compliance_risk"] >= 4 else "low",
        "decision": r["priority"], "recommended_action": rec["recommended_next_action"],
        "tables_to_update": [r["recommended_destination"]],
        "claim_flags": r["reasons_against"],
        "metadata": {"rating_model_version": RATING_MODEL_VERSION, **r},
    })
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
    ap.add_argument("--no-dry-run", dest="dry_run", action="store_false")
    ap.set_defaults(dry_run=True)
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--limit", type=int, default=1)
    ap.add_argument("--source-url", default="")
    ap.add_argument("--no-external-ai", action="store_true", default=True)
    ap.add_argument("--write-events", action="store_true")
    ap.add_argument("--max-age-days", type=int, default=30)
    ap.add_argument("--allow-capture", action="store_true",
                    help="(reserved) permit real yt-dlp capture via the legacy collector; NOT used in dry-run")
    args = ap.parse_args()

    if not args.source_url:
        print("DRY-RUN demo needs --source-url (no broad scraping). Example: --source-url https://www.youtube.com/watch?v=EXAMPLE")
        return 2

    # In dry-run we do NOT fetch a transcript; deterministic scoring runs on the title/url only.
    text = ""  # real capture (yt-dlp) is intentionally not invoked here
    rec = build_record(args.source_url, None, text, args.no_external_ai)
    records = [rec][: max(1, args.limit)]

    run_id = None
    if not args.dry_run and sb.configured():
        st, run = sb.insert("research_runs", {
            "requested_by": "youtube_monitor_wrapper", "question": "YouTube source intake",
            "research_type": "youtube_monitor", "status": "completed",
            "summary": f"Processed {len(records)} source(s)", "payload": {"rating_model_version": RATING_MODEL_VERSION}})
        run_id = run[0]["id"] if isinstance(run, list) and run else None
        for r in records:
            refs = write_supabase(r, run_id)
            if args.write_events:
                sb.event("research", "youtube_source_reviewed", "success",
                         f"Reviewed: {r['title']}", f"score {r['rating']['total_opportunity_score']} → {r['rating']['recommended_destination']}",
                         payload={"source_url": r["source_url"], "dedup": refs.get("dedup", False)})

    write_report(records, args.dry_run)
    print(json.dumps({"ok": True, "dry_run": args.dry_run, "no_external_ai": args.no_external_ai,
                      "processed": len(records), "run_id": run_id,
                      "report": str(RUNTIME),
                      "sample": {"title": rec["title"], "category": rec["rating"]["primary_category"],
                                 "score": rec["rating"]["total_opportunity_score"],
                                 "priority": rec["rating"]["priority"],
                                 "destination": rec["rating"]["recommended_destination"]}}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
