#!/usr/bin/env python3
"""Direct metadata-first Source Intake enrichment.

Accepts one explicit public source and creates deterministic project_enrichment without capture,
NotebookLM, broad scraping, or external AI.
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
sys.path.insert(0, str(ROOT / "scripts" / "intake"))
import _supabase as sb  # noqa: E402
from nexus_enrichment import build_project_enrichment  # noqa: E402

RUNTIME = ROOT / "reports" / "runtime" / "direct_source_enrichment_latest.json"
MANUAL = ROOT / "reports" / "manual_publish" / "direct_source_enrichment_latest.md"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def source_type_from_url(url: str) -> str:
    lowered = url.lower()
    if "youtube.com" in lowered or "youtu.be" in lowered:
        return "youtube"
    if lowered.endswith(".pdf"):
        return "pdf"
    return "web"


def compute(source_url: str, title: str, source_type: str) -> dict[str, Any]:
    return build_project_enrichment(source={
        "title": title or source_url,
        "url": source_url,
        "source_url": source_url,
        "source_type": source_type,
        "snippet": "Saved metadata is available. Transcript/NotebookLM enrichment is pending.",
        "metadata": {
            "primary_category": "public_research",
            "recommended_destination": "Source Intake & Review",
            "tags": ["direct_source_enrichment", "metadata_first"],
        },
    })


def write_reports(report: dict[str, Any], explicit_path: str = "") -> None:
    RUNTIME.parent.mkdir(parents=True, exist_ok=True)
    RUNTIME.write_text(json.dumps(report, indent=2))
    lines = [
        "# Direct Source Enrichment",
        "",
        f"- generated_at: {report['generated_at']}",
        f"- dry_run: {report['dry_run']}",
        f"- source_url: {report['source_url']}",
        f"- title: {report['title']}",
        "- capture_run: false",
        "- notebooklm_called: false",
        "- external_ai_called: false",
        f"- supabase_write: {report['supabase_write']}",
        f"- research_source_id: {report.get('research_source_id') or 'none'}",
        f"- nexus_event_id: {report.get('nexus_event_id') or 'none'}",
    ]
    MANUAL.parent.mkdir(parents=True, exist_ok=True)
    MANUAL.write_text("\n".join(lines) + "\n")
    if explicit_path:
        path = Path(explicit_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, indent=2) if path.suffix.lower() == ".json" else "\n".join(lines) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--title", default="")
    parser.add_argument("--source-type", default="")
    parser.add_argument("--dry-run", dest="dry_run", action="store_true")
    parser.add_argument("--no-dry-run", dest="dry_run", action="store_false")
    parser.set_defaults(dry_run=True)
    parser.add_argument("--no-external-ai", action="store_true", default=True)
    parser.add_argument("--report-path", default="")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if not args.no_external_ai:
        print(json.dumps({"ok": False, "error": "no_external_ai_required"}, indent=2))
        return 2
    source_type = args.source_type or source_type_from_url(args.source_url)
    title = args.title or args.source_url
    enrichment = compute(args.source_url, title, source_type)

    source_id = None
    event_id = None
    supabase_write = False
    if not args.dry_run:
        if not sb.configured():
            print(json.dumps({"ok": False, "error": "supabase_not_configured"}, indent=2))
            return 2
        row = {
            "source_type": source_type,
            "url": args.source_url,
            "title": title,
            "snippet": "Saved metadata is available. Transcript/NotebookLM enrichment is pending.",
            "metadata": {
                "project_enrichment": enrichment,
                "enrichment_status": enrichment.get("enrichment_status"),
                "direct_source_enrichment": True,
            },
        }
        _status, rows = sb.insert("research_sources", row)
        if isinstance(rows, list) and rows:
            source_id = rows[0].get("id")
            supabase_write = True
        _status, events = sb.insert("nexus_events", {
            "lane": "intake",
            "source": "direct_source_enrichment",
            "action": "direct_source_enrichment_created",
            "status": "success",
            "title": title[:80],
            "summary": "Metadata-first source enrichment created without capture or external AI.",
            "payload": {
                "event_type": "direct_source_enrichment_created",
                "research_source_id": source_id,
                "source_url": args.source_url,
                "capture_run": False,
                "external_ai_called": False,
            },
        })
        if isinstance(events, list) and events:
            event_id = events[0].get("id")

    report = {
        "ok": True,
        "generated_at": now(),
        "dry_run": args.dry_run,
        "source_url": args.source_url,
        "title": title,
        "source_type": source_type,
        "project_enrichment": enrichment,
        "supabase_write": supabase_write,
        "research_source_id": source_id,
        "nexus_event_id": event_id,
        "safety": {
            "capture_run": False,
            "notebooklm_called": False,
            "external_ai_called": False,
            "broad_scrape": False,
        },
    }
    write_reports(report, args.report_path)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
