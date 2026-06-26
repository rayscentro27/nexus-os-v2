#!/usr/bin/env python3
"""Backfill deterministic project_enrichment for historical research_sources rows.

SAFE manual metadata-only backfill:
- reads existing research_sources and matching transcript_reviews
- computes deterministic project_enrichment with nexus_enrichment.py
- updates only metadata.project_enrichment / metadata.enrichment_status / metadata proof markers
- writes nexus_events proof for live updates

It never runs capture, yt-dlp, external AI, schedulers, v1 workers, publish/send/trade/deploy, or
broad scraping. Dry-run is the default.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "social"))
import _supabase as sb  # noqa: E402
from nexus_enrichment import build_project_enrichment  # noqa: E402

MAX_LIMIT = 50
DEFAULT_LIMIT = 10
RUNTIME = ROOT / "reports" / "runtime" / "nexus_project_enrichment_backfill_latest.md"
MANUAL = ROOT / "reports" / "manual_publish" / "nexus_project_enrichment_backfill_latest.md"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def has_enrichment(row: dict[str, Any] | None) -> bool:
    meta = (row or {}).get("metadata") or {}
    return bool(meta.get("project_enrichment"))


def fetch_sources(args, limit: int) -> list[dict[str, Any]]:
    if args.source_id:
        query = f"select=*&id=eq.{sb.q(args.source_id)}&limit=1"
    elif args.source_url:
        query = f"select=*&url=eq.{sb.q(args.source_url)}&limit=1"
    else:
        query = f"select=*&order=created_at.desc&limit={limit}"
    st, rows = sb.get("research_sources", query)
    return rows if isinstance(rows, list) else []


def fetch_review(source: dict[str, Any]) -> dict[str, Any]:
    source_id = source.get("id")
    url = source.get("url")
    title = source.get("title")
    if source_id:
        st, rows = sb.get("transcript_reviews",
                          f"select=*&metadata->>research_source_id=eq.{sb.q(source_id)}&order=created_at.desc&limit=1")
        if isinstance(rows, list) and rows:
            return rows[0]
    if url:
        st, rows = sb.get("transcript_reviews",
                          f"select=*&metadata->>source_url=eq.{sb.q(url)}&order=created_at.desc&limit=1")
        if isinstance(rows, list) and rows:
            return rows[0]
    if title:
        st, rows = sb.get("transcript_reviews", f"select=*&title=eq.{sb.q(title)}&order=created_at.desc&limit=1")
        if isinstance(rows, list) and rows:
            return rows[0]
    return {}


def update_metadata(table: str, row_id: str, current: dict[str, Any], enrichment: dict[str, Any],
                    proof_event_id: str | None) -> tuple[int, Any]:
    meta = dict(current.get("metadata") or {})
    enriched = dict(enrichment)
    if proof_event_id:
        enriched["proof_event_id"] = proof_event_id
    meta.update({
        "project_enrichment": enriched,
        "enrichment_status": enriched.get("enrichment_status"),
        "enrichment_backfilled_at": now(),
        "enrichment_backfill_source": "deterministic_manual_backfill",
    })
    if proof_event_id:
        meta["proof_event_id"] = proof_event_id
    return sb.update(table, f"id=eq.{sb.q(row_id)}", {"metadata": meta})


def proof_event(source: dict[str, Any], review: dict[str, Any], enrichment: dict[str, Any]) -> str | None:
    st, ev = sb.insert("nexus_events", {
        "lane": "research",
        "action": "project_enrichment_backfilled",
        "status": "success",
        "source": "project_enrichment_backfill",
        "title": (source.get("title") or source.get("url") or "research source")[:80],
        "summary": f"{enrichment['enrichment_status']} · {enrichment['category']} -> {enrichment['destination']} · score {enrichment['score']}",
        "payload": {
            "event_type": "project_enrichment_backfilled",
            "research_source_id": source.get("id"),
            "transcript_review_id": review.get("id"),
            "source_url": source.get("url"),
            "project_enrichment": enrichment,
        },
    })
    return ev[0]["id"] if isinstance(ev, list) and ev else None


def process_source(source: dict[str, Any], args) -> dict[str, Any]:
    review = fetch_review(source)
    source_needs = args.force or not has_enrichment(source)
    review_needs = bool(review) and (args.force or not has_enrichment(review))
    enrichment_source = "transcript_capture" if review else "deterministic"
    enrichment = build_project_enrichment(
        source=source,
        transcript_review=review,
        enrichment_source=enrichment_source,
    )
    result = {
        "source_id": source.get("id"),
        "title": source.get("title"),
        "source_url": source.get("url"),
        "transcript_review_id": review.get("id"),
        "would_update_source": source_needs,
        "would_update_transcript_review": review_needs,
        "enrichment_status": enrichment.get("enrichment_status"),
        "category": enrichment.get("category"),
        "destination": enrichment.get("destination"),
        "score": enrichment.get("score"),
        "dry_run": args.dry_run,
    }
    if not source_needs and not review_needs:
        return {**result, "status": "skipped_existing"}
    if args.dry_run:
        return {**result, "status": "would_update"}

    event_id = proof_event(source, review, enrichment)
    failures: list[str] = []
    if source_needs:
        st, body = update_metadata("research_sources", source["id"], source, enrichment, event_id)
        if st not in (200, 204):
            failures.append(f"research_sources:{st}:{str(body)[:120]}")
    if review_needs:
        st, body = update_metadata("transcript_reviews", review["id"], review, enrichment, event_id)
        if st not in (200, 204):
            failures.append(f"transcript_reviews:{st}:{str(body)[:120]}")
    if failures:
        return {**result, "status": "failed", "errors": failures, "proof_event_id": event_id}
    return {**result, "status": "updated", "proof_event_id": event_id}


def write_report(report: dict[str, Any]) -> None:
    lines = [
        "# Nexus Project Enrichment Backfill",
        "",
        f"- generated_at: {now()}",
        f"- mode: {'DRY-RUN (no Supabase writes)' if report['dry_run'] else 'LIVE metadata-only'}",
        f"- limit: {report['limit']}",
        f"- candidates: {report['candidates']} · updated: {report['updated']} · skipped: {report['skipped']} · failed: {report['failed']}",
        "- capture: not run · yt-dlp: not run · external_ai: false · v1 workers: not touched",
        "",
        "## Results",
    ]
    for item in report["results"]:
        lines.append(f"- {json.dumps(item, sort_keys=True)}")
    for path in (RUNTIME, MANUAL):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", dest="dry_run", action="store_true")
    ap.add_argument("--no-dry-run", dest="dry_run", action="store_false")
    ap.set_defaults(dry_run=True)
    ap.add_argument("--limit", type=int, default=DEFAULT_LIMIT, help=f"max rows (hard cap {MAX_LIMIT})")
    ap.add_argument("--source-id", default="")
    ap.add_argument("--source-url", default="")
    ap.add_argument("--force", action="store_true", help="overwrite existing project_enrichment")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--report-path", default="")
    ap.add_argument("--no-external-ai", action="store_true", default=True)
    args = ap.parse_args()

    if not sb.configured():
        print(json.dumps({"ok": False, "error": "supabase_not_configured"}))
        return 2

    limit = max(1, min(args.limit, MAX_LIMIT))
    sources = fetch_sources(args, limit)
    results = [process_source(source, args) for source in sources[:limit]]
    updated = sum(1 for r in results if r["status"] == "updated")
    skipped = sum(1 for r in results if r["status"] == "skipped_existing")
    failed = sum(1 for r in results if r["status"] == "failed")
    would_update = sum(1 for r in results if r["status"] == "would_update")
    report = {
        "ok": failed == 0,
        "dry_run": args.dry_run,
        "force": args.force,
        "no_external_ai": True,
        "limit": limit,
        "candidates": len(sources),
        "updated": updated,
        "would_update": would_update,
        "skipped": skipped,
        "failed": failed,
        "results": results,
    }
    write_report(report)
    if args.report_path:
        Path(args.report_path).write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
