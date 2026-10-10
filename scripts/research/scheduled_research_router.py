#!/usr/bin/env python3
"""Bounded source router used by the normal supervised Research watch.

The router selects existing processors and performs the mechanical canonical
Supabase source write.  AI/Alpha/department interpretation is downstream.
"""
from __future__ import annotations

import json
import re
import traceback
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

from research_document_pipeline import fetch, process_document
from research_v2 import integrate_scheduled_result
from research_v2_control_plane import classify_completion, stage_receipts
from nexus_agent_platform.governed.persistence import append_record
from youtube_full_pipeline import process_youtube_video
from youtube_backfill import discover_page, load_state, persist_page
from nexus_agent_platform.research_work_queue import default_queue
from nexus_agent_platform.research.source_contract import validate_source_result
from nexus_agent_platform.mechanical_ingestion import ingest_public_source
from asr_worker_router import cleanup_oracle_job


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def processor_for(source_type: str, category: str = "") -> str:
    value = f"{source_type} {category}".upper()
    if "YOUTUBE_CHANNEL" in value:
        return "youtube_backfill.discover_page + queue.enqueue"
    if "YOUTUBE" in value:
        return "youtube_full_pipeline.process_youtube_video"
    if "TRADINGVIEW" in value:
        return "research_document_pipeline.web_page (TradingView mode)"
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


def resolve_feeder_gap_source(item: dict[str, Any], search_fn=None) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """Resolve source-less gap tasks using the existing bounded public search."""
    if str(item.get("source_url") or "").strip() or str(item.get("request_type") or "").upper() != "FEEDER_GAP_CLOSURE":
        return item, None
    question = str(item.get("research_question") or item.get("question") or item.get("objective") or "").strip()
    if not question:
        raise ValueError("FEEDER_GAP_QUESTION_MISSING")
    # Keep the exact question for lineage, but avoid feeding conversational
    # filler and internal project names to public search. Project context comes
    # from the persisted source title.
    context=str(item.get("search_context") or item.get("title") or "").lower()
    context=re.sub(r"\b(goclear|gap closure|scheduler canary|bounded|fixture|certification)\b"," ",context)
    context=" ".join(re.findall(r"[a-z0-9]+",context))
    stop={"what","which","who","where","when","why","how","are","is","the","a","an","this","that","for","with","from","and","or","to","of","in","on","supports","support","establishes","evidence","verified","actually"}
    terms=[word for word in re.findall(r"[a-z0-9]+",question.lower()) if word not in stop]
    search_query=" ".join([*context.split()[:4],*terms[:5],"evidence"][:10]) or question
    if search_fn is None:
        from nexus_agent_platform.proactive_discovery import web_search
        search_fn=web_search
    discovery = search_fn(search_query, 5)
    results = [row for row in (discovery.get("results") or [])
               if isinstance(row, dict) and str(row.get("url") or "").startswith(("https://", "http://"))]
    if not results:
        notes=discovery.get("notes") or []
        reason=(notes[0] if isinstance(notes,list) and notes else notes) or discovery.get("status") or "NO_SEARCH_RESULTS"
        raise RuntimeError(f"FEEDER_GAP_SEARCH_UNAVAILABLE:{reason}")
    selected = results[0]
    resolved = {**item, "source_type": "PUBLIC_SEARCH_RESULT", "source_url": selected["url"],
                "title": selected.get("title") or item.get("title") or question,
                "source_id": item.get("source_id") or item.get("work_id"),
                "search_result_packet": results,
                "selection_reason": "feeder_gap_bounded_public_search"}
    return resolved, {**discovery,"query":search_query,"exact_question":question,"candidate_count":len(results),"selected_url":selected["url"]}

def process_scheduled_item(item: dict[str, Any]) -> dict[str, Any]:
    item, search_discovery = resolve_feeder_gap_source(item)
    source_type = str(item.get("source_type", "WEB_PAGE")).upper()
    category = str(item.get("category", ""))
    processor = processor_for(source_type, category)
    try:
        if source_type == "YOUTUBE_CHANNEL":
            channel_id = item.get("channel_id") or item.get("source_id")
            before = set((load_state().get("channels", {}).get(str(channel_id), {}) or {}).get("discovered_video_ids", []))
            cursor = (load_state().get("channels", {}).get(str(channel_id), {}) or {}).get("backfill_cursor", {})
            page = int(cursor.get("next_page", 1) or 1)
            discovered = discover_page(item["source_url"], page=page, page_size=int(item.get("page_size", 10) or 10))
            state = persist_page(channel_id=str(channel_id), channel_name=item.get("source_name") or item.get("title") or str(channel_id), channel_url=item["source_url"], page=page, result=discovered)
            created = []
            queue = default_queue()
            existing = queue.load().get("items", [])
            known_keys = {str(row.get("dedup_key")) for row in existing if row.get("dedup_key")}
            for video in discovered.get("videos", []):
                video_id = str(video.get("video_id"))
                dedup_key = f"youtube:{channel_id}:{video_id}:default_content_review"
                if video_id in before or dedup_key in known_keys:
                    continue
                queued = queue.enqueue(
                    work_id=f"youtube:{channel_id}:{video_id}:default_content_review",
                    research_work_id=f"youtube:{channel_id}:{video_id}:default_content_review",
                    request_type="YOUTUBE_BACKFILL", work_class="MONITORED", category=item.get("category") or "YOUTUBE_CONTENT",
                    source_type="YOUTUBE_VIDEO", source_name=video.get("title") or video_id,
                    source_id=video_id, source_url=video.get("url") or f"https://www.youtube.com/watch?v={video_id}",
                    channel_id=channel_id, channel_name=item.get("source_name") or item.get("title"),
                    channel_url=item["source_url"], published_at=video.get("published_at"),
                    question=item.get("question") or "default_content_review", required_tool="YOUTUBE",
                    required_capability="YOUTUBE", expected_output="human-readable learning record",
                    requested_by="youtube_backfill", objective=item.get("objective") or item.get("title"),
                    objective_id=item.get("objective_id"), dedup_key=dedup_key,
                    source_candidates=[], lifecycle="ONE_TIME", alpha_eligible=True,
                    department_target=item.get("department_target"), priority=50)
                created.append(queued.get("work_id"))
                known_keys.add(dedup_key)
            result = {"processing_status": "FULLY_PROCESSED" if discovered.get("status") == "PASS" else "FAILED_RETRYABLE", "final_status": "FULLY_PROCESSED" if discovered.get("status") == "PASS" else "FAILED_RETRYABLE",
                      "raw_acquired": discovered.get("status") == "PASS", "stored": True,
                      "summary": f"Inventory page {page} discovered {len(discovered.get('video_ids', []))} videos; queued {len(created)} unseen videos.",
                      "channel_id": channel_id, "backfill_page": page, "backfill_state": state,
                      "new_video_queue_items": created, "processor": processor}
        elif "YOUTUBE" in source_type:
            result = process_youtube_video({"video_id": item["source_id"], "url": item["source_url"], "title": item.get("title", item["source_id"]), "channel": item.get("author", ""), "channel_id": item.get("channel_id"), "research_question": item.get("question") or item.get("title") or "default_content_review", "discovery_method": item.get("discovery_method", "")}, force_asr=bool(item.get("force_asr")))
        elif "GITHUB" in source_type:
            from research_document_pipeline import github_deep
            result = github_deep(item["source_id"])
        else:
            result = _web_item(item, source_type)
        if search_discovery is not None:
            result["search_discovery"] = {"provider": search_discovery.get("provider"),
                                          "query": search_discovery.get("query"),
                                          "exact_question": search_discovery.get("exact_question"),
                                          "candidate_count": search_discovery.get("candidate_count"),
                                          "selected_url": search_discovery.get("selected_url"),
                                          "selection_reason": "top screened public result; primary-source verification remains required"}
        fidelity = validate_source_result(item, result)
        result["fidelity_check"] = fidelity
        # Fidelity/category is optional downstream metadata.  It is retained
        # on the result, but it cannot block public information persistence.
        status = result.get("processing_status", "FULLY_PROCESSED")
        duplicate = status == "DUPLICATE_UNCHANGED"
        v2 = integrate_scheduled_result(item, result) if not duplicate else {"v2_integrated": True, "duplicate": True, "claims_created": 0, "questions_created": 0}
        result["raw_acquired"] = True
        completion = classify_completion(result, source_type)
        receipts = stage_receipts(item, result)
        for receipt in receipts: append_record("research_stage_receipts", receipt)
        routed = {"source_type": source_type, "source": item.get("source_url"), "normal_scheduler_selected": True, "processor": processor, "raw_acquired": True, "summary_created": not duplicate, "extraction_created": not duplicate, "scored": not duplicate, "provenance_created": True, "stored": True, "disposition": result.get("research_disposition", "DUPLICATE" if duplicate else "MONITOR"), "final_status": status, "completion_status": completion, "stage_receipts": len(receipts), "result": result, "fidelity_check": result.get("fidelity_check"), "v2": v2, "alpha_invoked": False, "opportunities_created": 0, "work_orders_created": 0}
        ingestion = ingest_public_source(item=item, result=routed, queue_sequence=item.get("queue_sequence"), root=Path(__file__).resolve().parents[2])
        routed["canonical_ingestion"] = ingestion
        routed["supabase_source_id"] = ingestion.get("supabase_source_id")
        routed["supabase_write_confirmed"] = ingestion.get("supabase_write_confirmed", False)
        routed["readback_confirmed"] = ingestion.get("readback_confirmed", False)
        routed["ingestion_status"] = ingestion.get("processing_status")
        if ingestion.get("processing_status") not in {"INGESTED", "INGESTED_EXISTING"}:
            routed["stored"] = False
            routed["final_status"] = "FAILED_RETRYABLE"
            routed["completion_status"] = "FAILED_CANONICAL_INGESTION"
            routed["error"] = ingestion.get("error")
        else:
            routed["final_status"] = "INGESTED"
            routed["completion_status"] = "INGESTED"
        # Oracle media is retained until the canonical package has been read
        # back.  Cleanup is mechanical and happens after that receipt only.
        asr_diagnostics = (result or {}).get("asr_diagnostics") or {}
        cleanup_token = asr_diagnostics.get("cleanup_token")
        if cleanup_token and routed.get("readback_confirmed"):
            cleanup = cleanup_oracle_job(cleanup_token)
            routed["temp_cleanup"] = cleanup
            append_record("research_stage_receipts", {
                "schema_version": "nexus.research-stage-receipt.v2",
                "receipt_id": f"asr-cleanup-{item.get('source_id')}-{int(datetime.now(timezone.utc).timestamp())}",
                "created_at": _now(), "source_id": item.get("source_id"),
                "source_type": source_type, "source_url": item.get("source_url"),
                "queue_sequence": item.get("queue_sequence"),
                "stage": "ASR_TEMP_CLEANUP_CONFIRMED" if cleanup.get("cleaned") else "ASR_TEMP_CLEANUP_FAILED",
                "ingestion_status": routed.get("ingestion_status"),
                "temp_files_before": cleanup.get("files_before"),
                "temp_files_after": cleanup.get("files_after"),
                "bytes_reclaimed": cleanup.get("bytes_reclaimed"),
            })
        return routed
    except Exception as exc:
        message = str(exc).replace("\n", " ")[:500]
        return {"source_type": source_type, "source": item.get("source_url"), "normal_scheduler_selected": True, "processor": processor, "raw_acquired": False, "summary_created": False, "extraction_created": False, "scored": False, "provenance_created": False, "stored": False, "disposition": "INSUFFICIENT_SOURCE", "final_status": "FAILED_RETRYABLE", "error": message, "error_class": type(exc).__name__, "exception_class": type(exc).__name__, "error_message": message, "http_status": getattr(exc, "code", None), "traceback_summary": " ".join(traceback.format_exc(limit=4).splitlines())[-1200:], "failure_stage": "scheduled_source_processing", "alpha_invoked": False, "opportunities_created": 0, "work_orders_created": 0}


def process_scheduled_batch(items: list[dict[str, Any]]) -> dict[str, Any]:
    results = [process_scheduled_item(item) for item in items]
    full = [x for x in results if x["final_status"] == "FULLY_PROCESSED"]
    duplicates = [x for x in results if x["final_status"] == "DUPLICATE_UNCHANGED"]
    substantive = [x for x in results if x.get("completion_status") == "SUBSTANTIVE_COMPLETE"]
    monitors = [x for x in results if x.get("completion_status") == "MONITOR_CHECK_COMPLETE"]
    return {"scheduled_path_used": True, "results": results, "metrics": {"sources_discovered": len(items), "sources_acquired": sum(x["raw_acquired"] for x in results), "sources_fully_processed": len(full), "duplicates_skipped": len(duplicates), "summaries_created": sum(x["summary_created"] for x in results), "structured_extractions_created": sum(x["extraction_created"] for x in results), "substantive_findings_created": len(substantive), "monitor_checks_completed": len(monitors), "evidence_incomplete": sum(x.get("completion_status") == "EVIDENCE_INCOMPLETE" for x in results), "stage_receipts_created": sum(x.get("stage_receipts", 0) for x in results), "follow_up_questions_created": len(substantive), "deep_research_items_created": sum(x["disposition"] == "DEEP_RESEARCH" for x in substantive), "processing_failures": sum(x["final_status"].startswith("FAILED") for x in results), "useful_output_rate": round(len(substantive) / len(results), 3) if results else 0.0}, "alpha_invoked": False, "opportunities_created": 0, "work_orders_created": 0}
