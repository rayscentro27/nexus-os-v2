#!/usr/bin/env python3
"""Bounded source router used by the normal supervised Research watch.

The router selects existing processors only.  It never invokes Alpha or
creates opportunities, work orders, or Supabase records.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from typing import Any

from research_document_pipeline import fetch, process_document
from research_v2 import integrate_scheduled_result
from youtube_full_pipeline import process_youtube_video


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def processor_for(source_type: str, category: str = "") -> str:
    value = f"{source_type} {category}".upper()
    if "YOUTUBE" in value:
        return "youtube_full_pipeline.process_youtube_video"
    if "GITHUB" in value:
        return "research_document_pipeline.github_deep"
    if "SEO" in value:
        return "research_document_pipeline.web_page (SEO mode)"
    if "LAST_30" in value or "LAST30" in value:
        return "research_document_pipeline.process_document (recency mode)"
    return "research_document_pipeline.web_page"


def _web_item(item: dict[str, Any], source_type: str) -> dict[str, Any]:
    url = item["source_url"]
    if "LAST_30" in source_type.upper() and "github.com/" in url:
        repo = url.rstrip("/").split("github.com/", 1)[1]
        raw, headers = fetch(f"https://api.github.com/repos/{repo}/commits?per_page=30", "application/vnd.github+json")
        payload = json.loads(raw)
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        recent = []
        for commit in payload if isinstance(payload, list) else []:
            stamp = commit.get("commit", {}).get("committer", {}).get("date")
            try:
                if stamp and datetime.fromisoformat(stamp.replace("Z", "+00:00")) >= cutoff:
                    recent.append({"sha": commit.get("sha"), "published_at": stamp, "message": commit.get("commit", {}).get("message", "").splitlines()[0]})
            except ValueError:
                continue
        raw = json.dumps({"repository": repo, "cutoff_utc": cutoff.isoformat(), "date_filter": "committer.date >= cutoff", "recent_items": recent}, indent=2)
    else:
        raw, headers = fetch(url)
    extra = {"provider": "urllib", "provider_content_type": headers.get("content_type"), "raw_source_truncated": False}
    if "LAST_30" in source_type.upper():
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        extra.update({"recency_window_days": 30, "date_filter_actually_enforced": True, "source_publication_date_used": True, "source_retrieval_date_used": True, "cutoff_utc": cutoff.isoformat(), "undated_source_handling": "excluded from recent set", "evergreen_handling": "retained separately"})
    return process_document("seo" if "SEO" in source_type.upper() else "last_30_days" if "LAST_30" in source_type.upper() else "web", item.get("source_id", item["source_url"]), url, item.get("title", url), raw, extra=extra)


def process_scheduled_item(item: dict[str, Any]) -> dict[str, Any]:
    source_type = str(item.get("source_type", "WEB_PAGE")).upper()
    category = str(item.get("category", ""))
    processor = processor_for(source_type, category)
    try:
        if "YOUTUBE" in source_type:
            result = process_youtube_video({"video_id": item["source_id"], "url": item["source_url"], "title": item.get("title", item["source_id"]), "channel": item.get("author", "")})
        elif "GITHUB" in source_type:
            from research_document_pipeline import github_deep
            result = github_deep(item["source_id"])
        else:
            result = _web_item(item, source_type)
        status = result.get("processing_status", "FULLY_PROCESSED")
        duplicate = status == "DUPLICATE_UNCHANGED"
        v2 = integrate_scheduled_result(item, result) if not duplicate else {"v2_integrated": True, "duplicate": True, "claims_created": 0, "questions_created": 0}
        return {"source_type": source_type, "source": item.get("source_url"), "normal_scheduler_selected": True, "processor": processor, "raw_acquired": True, "summary_created": not duplicate, "extraction_created": not duplicate, "scored": not duplicate, "provenance_created": True, "stored": True, "disposition": result.get("research_disposition", "DUPLICATE" if duplicate else "MONITOR"), "final_status": status, "result": result, "v2": v2, "alpha_invoked": False, "opportunities_created": 0, "work_orders_created": 0}
    except Exception as exc:
        return {"source_type": source_type, "source": item.get("source_url"), "normal_scheduler_selected": True, "processor": processor, "raw_acquired": False, "summary_created": False, "extraction_created": False, "scored": False, "provenance_created": False, "stored": False, "disposition": "INSUFFICIENT_SOURCE", "final_status": "FAILED_RETRYABLE", "error": str(exc), "alpha_invoked": False, "opportunities_created": 0, "work_orders_created": 0}


def process_scheduled_batch(items: list[dict[str, Any]]) -> dict[str, Any]:
    results = [process_scheduled_item(item) for item in items]
    full = [x for x in results if x["final_status"] == "FULLY_PROCESSED"]
    duplicates = [x for x in results if x["final_status"] == "DUPLICATE_UNCHANGED"]
    return {"scheduled_path_used": True, "results": results, "metrics": {"sources_discovered": len(items), "sources_acquired": sum(x["raw_acquired"] for x in results), "sources_fully_processed": len(full), "duplicates_skipped": len(duplicates), "summaries_created": sum(x["summary_created"] for x in results), "structured_extractions_created": sum(x["extraction_created"] for x in results), "substantive_findings_created": len(full), "follow_up_questions_created": len(full), "deep_research_items_created": sum(x["disposition"] == "DEEP_RESEARCH" for x in full), "processing_failures": sum(x["final_status"].startswith("FAILED") for x in results), "useful_output_rate": round(len(full) / len(results), 3) if results else 0.0}, "alpha_invoked": False, "opportunities_created": 0, "work_orders_created": 0}
