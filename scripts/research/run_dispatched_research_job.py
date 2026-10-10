#!/usr/bin/env python3
"""Worker-side Research execution for a non-blocking scheduled wake."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import signal
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
JOBS = ROOT / "data/runtime/research_execution_jobs.jsonl"
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts" / "research"))
from scheduled_research_router import process_scheduled_item  # noqa: E402
from youtube_full_pipeline import _http_caption_tracks, select_channel_videos  # noqa: E402
from nexus_agent_platform.research_lane_scheduler import mark_lane_backoff, mark_source_result  # noqa: E402
from nexus_agent_platform.research_work_queue import default_queue  # noqa: E402
from nexus_agent_platform.demand_discovery import discover_from_governed_questions  # noqa: E402
from nexus_agent_platform.research_alpha_pipeline import review_assigned_research_output  # noqa: E402
from nexus_agent_platform.research_ai_orchestrator import investigate, route, interpret, write_monitor_snapshot  # noqa: E402
from nexus_agent_platform.research_continuation import evaluate_goal_result  # noqa: E402
from nexus_agent_platform.research.last30days_adapter import run_demand_radar_sources  # noqa: E402
from nexus_agent_platform.research_v2_bridge import build_research_package  # noqa: E402
from nexus_agent_platform.governed import persistence  # noqa: E402
from nexus_agent_platform.research.source_semantics import annotate, autonomous_discovery_allowed  # noqa: E402
from nexus_agent_platform.research.source_contract import source_category, TRADING, FUNDING  # noqa: E402
from research_v2 import parent_links_for_item  # noqa: E402
from bounded_research_missions import claim_item, record_item_result  # noqa: E402
from research_v2_control_plane import planner_tick  # noqa: E402
from research_v2_control_plane import stage_receipts  # noqa: E402


# Bounded, read-only scheduled source selection.  These are existing public
# research sources; the scheduler still owns lane fairness and this worker
# only resolves the selected lane to one real item for the canonical router.
SOURCE_POOLS = {
    "BUSINESS_MARKET": [
        ("WEB_PAGE", "sba-business-guide", "https://www.sba.gov/business-guide", "SBA business guide"),
    ],
    "FUNDING_LENDER": [("WEB_PAGE", "sba-loans", "https://www.sba.gov/loans", "SBA loans and funding")],
    "GRANTS_GOVERNMENT": [("WEB_PAGE", "sba-grants", "https://www.sba.gov/funding-programs/grants", "SBA grants")],
    "AFFILIATE_REVENUE": [("WEB_PAGE", "reddit-smallbusiness", "https://www.reddit.com/r/smallbusiness/", "Current small-business customer signals")],
    "SEO_SEARCH_DEMAND": [
        ("SEO_RESEARCH", "google-seo-starter", "https://developers.google.com/search/docs/fundamentals/seo-starter-guide", "Google SEO Starter Guide"),
        ("SEO_RESEARCH", "google-ai-search-features", "https://developers.google.com/search/docs/appearance/ai-features", "Google Search AI features guidance"),
    ],
    "GITHUB_TECHNOLOGY": [("GITHUB_REPOSITORY", "openai/openai-cookbook", "https://github.com/openai/openai-cookbook", "OpenAI Cookbook automation and agent examples")],
    "PLATFORM_CAPABILITY_INTELLIGENCE": [("GITHUB_REPOSITORY", "openai/openai-cookbook", "https://github.com/openai/openai-cookbook", "OpenAI Cookbook automation and agent examples")],
    "SOCIAL_CONTENT": [("WEB_PAGE", "reddit-smallbusiness", "https://www.reddit.com/r/smallbusiness/", "Small business community signals")],
    "YOUTUBE_CONTENT": [("YOUTUBE_VIDEO", "zbAmmnMh5ew", "https://www.youtube.com/watch?v=zbAmmnMh5ew", "Ray-approved YouTube research video")],
    "COMPETITOR_INTELLIGENCE": [("WEB_PAGE", "reddit-smallbusiness", "https://www.reddit.com/r/smallbusiness/", "Current small-business customer signals")],
    "TRADING_MARKETS": [("WEB_PAGE", "investor-investing-basics", "https://www.investor.gov/introduction-investing", "Investor.gov investing basics")],
    # Installed capabilities are invoked through their adapters, never
    # scheduled as GitHub source material.
}
SOURCE_CATALOG = {source_id: (source_type, source_url, title)
                  for values in SOURCE_POOLS.values() for source_type, source_id, source_url, title in values}


def select_scheduled_item(lane_id: str, execution_id: str) -> dict:
    queued_payload = os.environ.get("NEXUS_WORK_ITEM_JSON", "")
    if queued_payload and not (lane_id == "YOUTUBE_CONTENT" and "mission_item_id" in json.loads(queued_payload)):
        queued = json.loads(queued_payload)
        known = SOURCE_CATALOG.get(str(queued.get("source_id")), (None, None, None))
        candidates = [row for row in (queued.get("source_candidates") or []) if isinstance(row, dict) and row.get("source_url")]
        if str(queued.get("source_type", "")).upper() == "RESEARCH_OBJECTIVE" and candidates:
            index = int(hashlib.sha256(execution_id.encode("utf-8")).hexdigest()[:8], 16) % len(candidates)
            candidate = candidates[index]
            return {"source_type": candidate.get("source_type", "WEB_PAGE"),
                    "source_id": candidate.get("source_id") or queued.get("objective_id") or queued.get("work_id"),
                    "source_url": candidate["source_url"],
                    "title": candidate.get("title") or queued.get("title") or queued.get("objective_id"),
                    "question": queued.get("question") or queued.get("title") or queued.get("objective_id"),
                    "author": queued.get("requested_by", "Nexus Research"),
                    "category": lane_id, "selection_reason": "governed_objective_source_candidate",
                    "work_id": queued.get("work_id"), "work_class": queued.get("work_class"),
                    "objective_id": queued.get("objective_id"), "mission_id": queued.get("mission_id"),
                    "mission_item_id": queued.get("mission_item_id"), "parent_request_id": queued.get("parent_request_id"),
                    "source_candidates": candidates,
                    "required_capabilities": queued.get("required_capabilities", []),
                    "ai_plan_id": queued.get("ai_plan_id"),
                    "alpha_followup_required": queued.get("alpha_followup_required", False),
                    "department_target": queued.get("department_target"), "lifecycle": queued.get("lifecycle", "MONITORED"),
                    "research_mode": queued.get("research_mode"), "alpha_eligible": queued.get("alpha_eligible", False),
                    "alpha_review_required": queued.get("alpha_review_required", False), "WHY_THIS_RESEARCH": queued.get("WHY_THIS_RESEARCH"),
                    "TRIGGER": queued.get("TRIGGER"), "DEPARTMENT": queued.get("DEPARTMENT"), "BUSINESS_OR_NEXUS": queued.get("BUSINESS_OR_NEXUS"),
                    "PARENT_GOAL": queued.get("PARENT_GOAL"), "PROJECT": queued.get("PROJECT"), "QUESTION": queued.get("QUESTION"),
                    "EXPECTED_VALUE": queued.get("EXPECTED_VALUE"), "SOURCE_PLAN": queued.get("SOURCE_PLAN", [])}
        return {"source_type": queued.get("source_type") or "WEB_PAGE",
                "source_id": queued.get("source_id") or queued.get("work_id"),
                "source_url": queued.get("source_url") or queued.get("url") or known[1] or "",
                "title": queued.get("title") or queued.get("question") or known[2] or queued.get("source_id") or queued.get("work_id"),
                "question": queued.get("question") or queued.get("title") or queued.get("source_id") or queued.get("work_id"),
                "author": queued.get("requested_by", "Nexus Research"),
                "category": lane_id, "selection_reason": queued.get("selection_reason") or "assigned_request",
                "work_id": queued.get("work_id"), "work_class": queued.get("work_class"),
                "objective_id": queued.get("objective_id"), "mission_id": queued.get("mission_id"),
                "mission_item_id": queued.get("mission_item_id"), "parent_request_id": queued.get("parent_request_id"),
                "source_candidates": candidates,
                "required_capabilities": queued.get("required_capabilities", []),
                "ai_plan_id": queued.get("ai_plan_id"),
                "alpha_followup_required": queued.get("alpha_followup_required", False),
                "department_target": queued.get("department_target"),
                "lifecycle": queued.get("lifecycle", "MONITORED"),
                "research_mode": queued.get("research_mode"), "alpha_eligible": queued.get("alpha_eligible", False),
                "alpha_review_required": queued.get("alpha_review_required", False),
                "WHY_THIS_RESEARCH": queued.get("WHY_THIS_RESEARCH"), "TRIGGER": queued.get("TRIGGER"),
                "DEPARTMENT": queued.get("DEPARTMENT"), "BUSINESS_OR_NEXUS": queued.get("BUSINESS_OR_NEXUS"),
                "PARENT_GOAL": queued.get("PARENT_GOAL"), "PROJECT": queued.get("PROJECT"),
                "QUESTION": queued.get("QUESTION"), "EXPECTED_VALUE": queued.get("EXPECTED_VALUE"),
                "SOURCE_PLAN": queued.get("SOURCE_PLAN", [])}
    if lane_id == "YOUTUBE_CONTENT":
        from research.youtube_channel_registry import enabled_channels
        channels = enabled_channels()
        if not channels:
            raise RuntimeError("canonical designated YouTube source registry is empty")
        mission_target = os.environ.get("NEXUS_MISSION_TARGET_ID", "")
        channel = next((row for row in channels
                        if str(row.get("external_channel_id") or row.get("channel_id")) == mission_target), None)
        channel = channel or channels[int(hashlib.sha256(execution_id.encode("utf-8")).hexdigest()[:8], 16) % len(channels)]
        # Use the durable channel id for the bounded RSS fallback.  Handle
        # pages remain the canonical display URL but are not required for
        # metadata discovery.
        channel_id = channel.get("external_channel_id") or channel.get("channel_id")
        discovery_url = f"https://www.youtube.com/channel/{channel_id}"
        videos = select_channel_videos(discovery_url, 3)
        if not videos:
            raise RuntimeError(f"no eligible videos discovered for channel {channel['name']}")
        video = videos[0]
        # Prefer a recent captioned candidate.  A no-caption video is an
        # item-level ASR_REQUIRED/FAILED_RETRYABLE result, not a reason to
        # stop the bounded channel mission when another recent candidate is
        # processable.
        for candidate in videos:
            try:
                _http_caption_tracks(candidate["url"], candidate["video_id"])
                video = candidate
                break
            except Exception:
                continue
        return annotate({"source_type": "YOUTUBE_VIDEO", "source_id": video["video_id"], "source_url": video["url"],
                "title": video.get("title", video["video_id"]), "author": channel["name"],
                "channel_id": channel_id, "channel_url": channel.get("canonical_url") or channel.get("url"),
                "discovery_method": video.get("discovery_method", "YOUTUBE_RSS"),
                "category": "YOUTUBE_CONTENT", "selection_reason": "approved_channel_watchlist",
                "lifecycle": "ONE_TIME" if os.environ.get("NEXUS_MISSION_ITEM_ID") else "MONITORED"})
    pool = SOURCE_POOLS.get(lane_id) or SOURCE_POOLS["BUSINESS_MARKET"]
    index = int(hashlib.sha256(execution_id.encode("utf-8")).hexdigest()[:8], 16) % len(pool)
    source_type, source_id, source_url, title = pool[index]
    return annotate({"source_type": source_type, "source_id": source_id, "source_url": source_url,
            "title": title, "category": lane_id, "selection_reason": "scheduled_lane_source_pool"}
            )


def event(execution_id: str, status: str, **values) -> None:
    JOBS.parent.mkdir(parents=True, exist_ok=True)
    context = {
        "work_id": os.environ.get("NEXUS_WORK_ID") or None,
        "objective_id": os.environ.get("NEXUS_OBJECTIVE_ID") or None,
        "parent_request_id": os.environ.get("NEXUS_PARENT_REQUEST_ID") or None,
        "marketing_objective_id": os.environ.get("NEXUS_MARKETING_OBJECTIVE_ID") or None,
    }
    context = {key: value for key, value in context.items() if value}
    row = {"execution_id": execution_id, "status": status, "at": datetime.now(timezone.utc).isoformat(), **context, **values}
    with JOBS.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")
        handle.flush()


def return_department_request(item: dict, *, package_id: str | None, alpha_result: dict) -> None:
    """Close a durable department request without creating a second objective.

    Research evidence is append-only; this record is the state transition that
    lets the requesting department resume from the returned package.
    """
    request_id = str(item.get("parent_request_id") or item.get("work_id") or "")
    if not request_id or not item.get("department_target"):
        return
    persistence.append_record("research_requests", {
        "schema_version": "nexus.marketing-research-request.v1",
        "request_id": request_id,
        "status": "RETURNED",
        "marketing_objective_id": item.get("marketing_objective_id") or item.get("objective_id"),
        "research_package_id": package_id,
        "alpha_receipt_id": alpha_result.get("receipt_id"),
        "alpha_decision": alpha_result.get("decision") or alpha_result.get("status"),
        "returned_work_id": item.get("work_id"),
        "returned_at": datetime.now(timezone.utc).isoformat(),
        "return_to": str(item.get("department_target") or "RESEARCH").upper(),
    })
    persistence.append_record("research_v2_handoffs", {
        "schema_version": "nexus.research-v2-handoff.v1", "handoff_id": f"handoff_{request_id}_{package_id}",
        "request_id": request_id, "department_target": str(item.get("department_target") or "RESEARCH").upper(),
        "research_package_id": package_id, "alpha_receipt_id": alpha_result.get("receipt_id"),
        "alpha_decision": alpha_result.get("decision") or alpha_result.get("status"),
        "status": "RETURNED", "returned_at": datetime.now(timezone.utc).isoformat(),
    })


def strategy_changing_fallback(item: dict, *, failure_class: str, error: str, attempt: int = 1) -> dict | None:
    """Queue the next evidence source instead of repeating a failed strategy."""
    candidates = [row for row in (item.get("source_candidates") or [])
                  if isinstance(row, dict) and row.get("source_url")
                  and str(row.get("source_id")) != str(item.get("source_id"))]
    if not candidates or not item.get("work_id"):
        return None
    alternate = candidates[0]
    fallback = default_queue().enqueue(
        work_id=f"{item['work_id']}:strategy-change:{attempt}",
        work_class=item.get("work_class") or "ASSIGNED", priority=max(0, int(item.get("priority", 50)) - 1),
        lane_id=item.get("lane_id") or item.get("category") or "GENERAL_DISCOVERY",
        source_type=alternate.get("source_type") or "WEB_PAGE", source_id=alternate.get("source_id"),
        source_url=alternate.get("source_url"), title=alternate.get("title") or item.get("title"),
        source_candidates=candidates[1:], requested_by="research_failure_router",
        objective_id=item.get("objective_id"), parent_request_id=item.get("parent_request_id"),
        project_id=item.get("project_id"), parent_goal_id=item.get("parent_goal_id"),
        parent_finding_id=item.get("parent_finding_id"), parent_alpha_receipt_id=item.get("parent_alpha_receipt_id"),
        parent_alpha_request_id=item.get("parent_alpha_request_id"), parent_handoff_id=item.get("parent_handoff_id"),
        owner=item.get("owner") or "RESEARCH", department=item.get("department") or item.get("department_target"),
        department_target=item.get("department_target") or item.get("department"), mission=item.get("mission"),
        research_mode=item.get("research_mode"), state="OWNED", return_target=item.get("return_target"),
        why_this_research=item.get("why_this_research") or item.get("WHY_THIS_RESEARCH"),
        missing_evidence=item.get("missing_evidence"), source_classes=item.get("source_classes"),
        preferred_sources=item.get("preferred_sources"), fallback_sources=item.get("fallback_sources"),
        next_action=item.get("next_action"), alpha_followup_required=item.get("alpha_followup_required", False),
        alpha_eligible=item.get("alpha_eligible", False), alpha_review_required=item.get("alpha_review_required", False), lifecycle="ONE_TIME",
        selection_reason=f"strategy_change_after_{failure_class}", evidence_refs=item.get("evidence_refs") or [],
    )
    return {"work_id": fallback.get("work_id"), "source_id": alternate.get("source_id"),
            "source_url": alternate.get("source_url"), "failure_class": failure_class,
            "objective_continues": True, "strategy_changed": True, "prior_error": str(error)[:500]}


def run_selected_capability(item: dict, route_result: dict, execution_id: str) -> dict | None:
    """Execute the certified capability selected by the Research investigator.

    Existing source processors remain the default.  Objective work without a
    source URL must, however, be dispatched to the selected certified adapter;
    otherwise the plan is merely metadata and the worker silently falls back
    to deterministic source processing.
    """
    # Source semantics outrank a broad model capability preference. A GitHub
    # repository must reach github_deep and SEO_RESEARCH must reach the SEO web
    # processor; otherwise a valid source can be silently reclassified as a
    # Last30Days demand task and the lane's evidence contract is not met.
    source_type = str(item.get("source_type") or "").upper()
    if source_type in {"GITHUB_REPOSITORY", "SEO_RESEARCH"}:
        return None
    # A broad demand adapter is never a valid fallback for a governed
    # TradingView or funding item.  The post-acquisition fidelity gate remains
    # authoritative, but refusing this route here prevents source identity
    # from being overwritten before that gate can inspect the evidence.
    governed_category = source_category(item)
    if governed_category in {TRADING, FUNDING}:
        return None
    selected = (route_result.get("selected_executor") or {}).get("executor_id", "")
    if "last30days" not in str(selected).lower() and "demand_radar" not in str(selected).lower():
        return None
    query = str(item.get("question") or item.get("title") or "").strip()
    if not query:
        raise ValueError("selected Last30Days capability requires an investigation question")
    radar = run_demand_radar_sources({
        "request_id": execution_id,
        "work_id": item.get("work_id"),
        "objective_id": item.get("objective_id"),
        "query": query,
        "work_class": "DEMAND_DISCOVERY",
        "time_window": "LAST_30_DAYS",
        "max_runtime_seconds": 90,
        "requested_sources": ["reddit", "hackernews", "github", "grounding"],
    })
    signals = radar.get("signals") or []
    source_rows = [{
        "title": row.get("source_title") or row.get("topic") or row.get("source_url"),
        "url": row.get("source_url"), "source_type": row.get("source_type") or "PUBLIC_WEB",
        "snippet": row.get("excerpt") or row.get("problem_signal") or "",
    } for row in signals if row.get("source_url")]
    if source_rows:
        item["source_id"] = str(signals[0].get("signal_id") or source_rows[0].get("url"))
        item["source_type"] = source_rows[0].get("source_type") or "PUBLIC_WEB"
        item["source_url"] = source_rows[0].get("url")
        item["title"] = source_rows[0].get("title") or item.get("title")
    package = None
    if item.get("objective_id") and source_rows:
        package = build_research_package(
            objective_id=str(item["objective_id"]), query=query, sources=source_rows,
            radar=radar, cycle_id=str(item.get("company_cycle_id") or ""),
        )
    # Last30Days has its own durable governed Research source/package store.
    # Confirm the source rows by URL and the objective package before the
    # common worker accepts that persistence route; do not mislabel it as a
    # Supabase write.
    durable_rows = {str(row.get("source_url")): row for row in persistence.read_records("research_v2_sources") if row.get("source_url")}
    durable_source_urls = [str(row.get("url")) for row in source_rows if row.get("url")]
    durable_sources_confirmed = bool(durable_source_urls) and all(url in durable_rows for url in durable_source_urls)
    durable_package_confirmed = bool(package and any(row.get("research_package_id") == package.get("research_package_id")
                                                    for row in persistence.read_records("research_v2_packages")))
    durable_memory_write_confirmed = durable_sources_confirmed and durable_package_confirmed
    return {
        "final_status": "FULLY_PROCESSED" if signals else "PARTIAL_EVIDENCE",
        "processor": "last30days_demand_radar",
        "raw_acquired": bool(signals), "stored": bool(signals),
        "summary_created": bool(package), "extraction_created": bool(signals),
        "scored": False, "provenance_created": bool(signals),
        "disposition": "NEW_DEMAND_EVIDENCE" if signals else "NO_NEW_SIGNAL",
        "v2": {"research_package_id": (package or {}).get("research_package_id"),
               "source": source_rows[0] if source_rows else {}},
        "result": {"research_item_id": (package or {}).get("research_package_id")},
        "radar": radar, "ingestion_status": "DURABLE_MEMORY" if durable_memory_write_confirmed else None,
        "durable_memory_write_confirmed": durable_memory_write_confirmed,
        "durable_source_count": len(durable_source_urls) if durable_sources_confirmed else 0,
        "durable_package_id": (package or {}).get("research_package_id") if durable_package_confirmed else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execution-id", required=True)
    parser.add_argument("--timeout-seconds", type=int, default=180)
    args = parser.parse_args()
    execution_id = args.execution_id
    # Hydrate lineage before the first lifecycle event.  CLAIMED/RUNNING are
    # part of the durable execution trace too; emitting them before reading
    # the queue item made otherwise objective-backed work appear unlinked.
    work_id = os.environ.get("NEXUS_WORK_ID", "")
    queued_context = {}
    if work_id:
        queued_context = next((row for row in default_queue().load().get("items", []) if row.get("work_id") == work_id), {})
        for env_key, field in (("NEXUS_OBJECTIVE_ID", "objective_id"), ("NEXUS_PARENT_REQUEST_ID", "parent_request_id"), ("NEXUS_MARKETING_OBJECTIVE_ID", "marketing_objective_id")):
            if queued_context.get(field) and not os.environ.get(env_key):
                os.environ[env_key] = str(queued_context[field])
    if work_id and queued_context.get("request_type") == "FEEDER_GAP_CLOSURE":
        # Notebook-backed public-source gaps use the existing dispatched Research
        # worker and authenticated NotebookLM CLI. The operator enforces source
        # quality, dedupe, import/index confirmation, and durable feeder return.
        event(execution_id, "CLAIMED", worker_id="research_operator_worker", work_id=work_id,
              research_method=queued_context.get("recommended_research_method"))
        event(execution_id, "RUNNING", worker_id="research_operator_worker", processor="notebook_source_expansion")
        try:
            if not queued_context.get("notebook_reference"):
                # Older queue records may predate notebook routing metadata.
                # Rehydrate that immutable reference from authoritative feeder state.
                from nexus_agent_platform import feeder_runtime as feeder_module
                source_id = str(queued_context.get("source_id") or queued_context.get("parent_request_id") or "")
                # Feeder source records store the external NotebookLM reference
                # in notebook_reference. notebook_id belongs to the research
                # gap table, not nexus_feeder_sources.
                source_rows = feeder_module._request(f"nexus_feeder_sources?source_id=eq.{source_id}&select=notebook_reference")
                if source_rows:
                    queued_context["notebook_reference"] = source_rows[0].get("notebook_reference")
                    queued_context["notebook_id"] = queued_context["notebook_reference"]
            if not queued_context.get("notebook_reference"):
                raise RuntimeError("NOTEBOOK_REFERENCE_MISSING")
            from notebook_source_expansion import run_notebook_gap_operator
            result = run_notebook_gap_operator(queued_context)
            complete = result.get("gap_state") == "COMPLETED" and result.get("supabase_persistence_pass") is True
            queue_status = "COMPLETE" if complete else ("BLOCKED_EXTERNAL" if result.get("recovery_workflow") else "FAILED_RETRYABLE")
            default_queue().settle(work_id, queue_status,
                                   result={**result, "final_status": "NOTEBOOK_RESEARCH_COMPLETE" if complete else "NOTEBOOK_RESEARCH_INCOMPLETE"},
                                   blocker_type=None if complete else "NOTEBOOK_EVIDENCE_INSUFFICIENT")
            event(execution_id, "COMPLETED" if complete else "FAILED_RETRYABLE", worker_id="research_operator_worker",
                  work_id=work_id, **{k: result.get(k) for k in ("research_session_id", "research_method", "sources_imported", "indexing_pass", "notebook_reanalysis_pass", "gap_state", "evidence_state", "return_to_feeder")})
            print(json.dumps(result, indent=2, default=str))
            return 0 if complete else 1
        except Exception as exc:
            error = str(exc)[:500]
            recovery = ("NOTEBOOK_CLI_RECOVERY" if "NOTEBOOKLM_CLI" in error or "doctor" in error.lower() else
                        "NOTEBOOK_RESEARCH_RECOVERY" if "PASS_LIMIT_REACHED" in error else
                        "NOTEBOOK_IMPORT_RECOVERY" if "SOURCE_IMPORT" in error else
                        "NOTEBOOK_INDEXING_RECOVERY" if "SOURCE_WAIT" in error or "INDEX" in error else
                        "RESEARCH_RETURN_RECOVERY" if "PERSISTENCE" in error or "READBACK" in error else
                        "NOTEBOOK_RESEARCH_RECOVERY")
            blocked = "PASS_LIMIT_REACHED" in error or "NOTEBOOK_REFERENCE_MISSING" in error
            queue_status = "BLOCKED_EXTERNAL" if blocked else "FAILED_RETRYABLE"
            default_queue().settle(work_id, queue_status, result={"error": error, "recovery_workflow": recovery}, blocker_type="NOTEBOOK_RESEARCH_FAILURE")
            event(execution_id, queue_status, worker_id="research_operator_worker", work_id=work_id,
                  error=error, recovery_workflow=recovery)
            return 1
    if work_id and queued_context.get("research_processor") == "notebooklm_research_worker":
        # Proactive sources use the same NotebookLM worker, quality checks,
        # persistence, and handoff lifecycle as assigned Research items.
        # The FIFO scheduler already owns the claim. Process that lease rather
        # than asking the worker to claim it a second time.
        from research.notebooklm_research_adapter import get_adapter
        from research.notebooklm_research_worker import process_claim
        result = process_claim(work_item=queued_context, adapter=get_adapter(), queue=default_queue())
        event(execution_id, "NOTEBOOKLM_PROACTIVE_PROCESSOR", worker_id="research_operator_worker",
              work_id=work_id, result_status="PASS" if result.get("queue_status") == "COMPLETE" else "DEGRADED",
              processor="notebooklm_research_worker.process_claim",
              outcome=result.get("outcome"), queue_status=result.get("queue_status"),
              failure_code=result.get("failure_code"))
        print(json.dumps(result, indent=2, default=str))
        return 0 if result.get("queue_status") == "COMPLETE" else 1
    event(execution_id, "CLAIMED", worker_id="research_operator_worker", attempt_count=1)
    event(execution_id, "RUNNING", worker_id="research_operator_worker", timeout_seconds=args.timeout_seconds)
    try:
        v2_plan = planner_tick(worker_id="research_operator_worker")
        v2_plan.pop("worker_id", None)
        v2_plan.pop("status", None)
        event(execution_id, "RESEARCH_V2_PLANNER", worker_id="research_operator_worker", **v2_plan)
    except Exception as exc:
        # V2 planning is isolated from the proven acquisition path; a planner
        # failure cannot strand the claimed work or stop the Research wake.
        event(execution_id, "RESEARCH_V2_PLANNER_DEGRADED", worker_id="research_operator_worker", error=str(exc)[:500])
    lane_id = os.environ.get("NEXUS_SELECTED_LANE_ID", "BUSINESS_MARKET")
    selected_work_class = os.environ.get("NEXUS_SELECTED_WORK_CLASS", "GENERAL_DISCOVERY")
    mission_item_id = os.environ.get("NEXUS_MISSION_ITEM_ID", "")
    mission_item = None
    if mission_item_id:
        mission_item = claim_item(mission_item_id, worker_id="research_operator_worker")
        if mission_item is None:
            event(execution_id, "FAILED_RETRYABLE", worker_id="research_operator_worker", error="mission item already claimed or terminal", failure_class="MISSION_ITEM_ALREADY_CLAIMED", retry_after="next scheduled wake")
            return 1
        os.environ["NEXUS_MISSION_TARGET_ID"] = str(mission_item.get("target_id", ""))
    # Selection is part of the bounded mission attempt.  A discovery timeout
    # must settle the claimed item instead of leaving it IN_PROGRESS forever.
    def settle_queue(status: str, *, result=None, blocker_type=None):
        if work_id:
            try:
                default_queue().settle(work_id, status, result=result, blocker_type=blocker_type)
            except Exception as exc:
                event(execution_id, "QUEUE_SETTLE_DEGRADED", worker_id="research_operator_worker", error=str(exc)[:300])

    if work_id and selected_work_class == "DEMAND_DISCOVERY":
        try:
            needs = discover_from_governed_questions(queue=default_queue())
            result = {"needs_created": len(needs), "selection_reason": "customer_demand_discovery"}
            event(execution_id, "EVIDENCE_READY", worker_id="research_operator_worker",
                  result_status="PASS", demand_needs_created=len(needs), selected_work_class=selected_work_class)
            settle_queue("COMPLETE", result=result)
            event(execution_id, "COMPLETED", worker_id="research_operator_worker", alpha_status="PENDING_REVIEW",
                  next_action="Alpha review of structured customer need")
            return 0
        except Exception as exc:
            event(execution_id, "FAILED_RETRYABLE", worker_id="research_operator_worker",
                  error=str(exc)[:500], failure_class="DEMAND_DISCOVERY_FAILURE")
            settle_queue("FAILED_RETRYABLE", result={"error": str(exc)[:500]}, blocker_type="DEMAND_DISCOVERY_FAILURE")
            return 1

    try:
        item = select_scheduled_item(lane_id, execution_id)
        if queued_context.get("queue_sequence") is not None:
            item["queue_sequence"] = queued_context.get("queue_sequence")
        # Preserve the capability chosen by the durable objective planner.
        # The generic source selector has no source URL for an objective, so
        # downgrading it to RESEARCH_OBJECTIVE here previously discarded its
        # required_tool and failed with an empty-URL ingestion attempt.
        for field in ("required_tool", "required_capability", "required_capabilities",
                      "expected_output", "source_candidates", "objective_id", "parent_goal_id",
                      "work_id", "question", "why_it_matters", "unknown_to_resolve", "evidence_gaps"):
            if queued_context.get(field) not in (None, "", []):
                item[field] = queued_context[field]
    except TimeoutError as exc:
        event(execution_id, "FAILED_RETRYABLE", worker_id="research_operator_worker",
              error=str(exc)[:500], failure_class="SOURCE_SELECTION_TIMEOUT",
              retry_after="next scheduled wake")
        settle_queue("FAILED_RETRYABLE", result={"error": str(exc)[:500]}, blocker_type="SOURCE_SELECTION_TIMEOUT")
        if mission_item:
            record_item_result(mission_item_id, status="FAILED_RETRYABLE",
                               result={"error": str(exc)[:500], "failure_class": "SOURCE_SELECTION_TIMEOUT"},
                               next_action="retry after bounded source backoff")
        return 124
    except Exception as exc:
        event(execution_id, "FAILED_RETRYABLE", worker_id="research_operator_worker",
              error=str(exc)[:500], failure_class="SOURCE_SELECTION_FAILURE",
              retry_after="next scheduled wake")
        queued = json.loads(queued_payload) if queued_payload else {}
        fallback = strategy_changing_fallback(queued, failure_class="SOURCE_SELECTION_FAILURE", error=str(exc))
        if fallback:
            event(execution_id, "STRATEGY_CHANGED", worker_id="research_operator_worker", **fallback)
        settle_queue("WAITING" if fallback else "FAILED_RETRYABLE", result={"error": str(exc)[:500], "fallback": fallback}, blocker_type="SOURCE_SELECTION_FAILURE")
        if mission_item:
            record_item_result(mission_item_id, status="FAILED_RETRYABLE",
                               result={"error": str(exc)[:500], "failure_class": "SOURCE_SELECTION_FAILURE"},
                               next_action="retry after bounded source backoff")
        return 1
    item["v2_parent_links"] = parent_links_for_item(item)
    item = annotate(item)
    for env_key, field in (("NEXUS_OBJECTIVE_ID", "objective_id"), ("NEXUS_PARENT_REQUEST_ID", "parent_request_id"), ("NEXUS_MARKETING_OBJECTIVE_ID", "marketing_objective_id")):
        if item.get(field):
            os.environ[env_key] = str(item[field])
    # FIFO queue assignments are complete before dispatch. The worker must not
    # ask an AI planner to choose a different project, source, or capability.
    # Keep the legacy investigator available for non-FIFO compatibility calls,
    # but make the production queue path a direct assignment execution.
    fifo_assignment = os.environ.get("NEXUS_FIFO_QUEUE") == "1"
    if fifo_assignment:
        required_tool = item.get("required_tool") or item.get("required_capability") or item.get("source_type")
        ai_plan_result = {"status": "FIFO_ASSIGNMENT", "plan_id": None, "model_calls": 0,
                          "plan": {"required_tool": required_tool, "source_locked": True}}
        ai_route_result = {"status": "FIFO_ASSIGNMENT", "required_capabilities": [required_tool] if required_tool else [],
                           "selected_executor": {"executor_id": required_tool or "assigned_processor"},
                           "why_selected": "durable_fifo_assignment"}
    else:
        # The legacy investigator is deliberately retained for compatibility
        # callers outside the production FIFO path.
        ai_plan_result = investigate(item)
        ai_route_result = route(item, ai_plan_result.get("plan", {})) if ai_plan_result.get("status") == "PASS_REAL" else {"status": "FAILED_REAL", "why_selected": ai_plan_result.get("reason")}
    item["ai_plan_id"] = ai_plan_result.get("plan_id")
    item["required_capabilities"] = ai_route_result.get("required_capabilities", [])
    item["selected_executor_id"] = (ai_route_result.get("selected_executor") or {}).get("executor_id")
    item["ai_investigation_status"] = ai_plan_result.get("status")
    write_monitor_snapshot(item=item, stage="AI_INVESTIGATION_PLAN", plan=ai_plan_result.get("plan"), route_result=ai_route_result)
    event(execution_id, "AI_INVESTIGATION_PLAN", worker_id="research_operator_worker",
          ai_plan_id=item.get("ai_plan_id"), ai_model=ai_plan_result.get("model"),
          ai_model_calls=ai_plan_result.get("model_calls", 0), ai_status=ai_plan_result.get("status"),
          required_capabilities=item.get("required_capabilities"), selected_executor_id=item.get("selected_executor_id"),
          routing_status=ai_route_result.get("status"), routing_reason=ai_route_result.get("why_selected"))
    # A missing model is a bounded orchestration degradation. Preserve the
    # established processor path so one provider outage does not erase the
    # underlying worker's evidence opportunity.
    event(execution_id, "SOURCE_SELECTED", worker_id="research_operator_worker", lane_id=lane_id,
          work_id=item.get("work_id"), objective_id=item.get("objective_id"), parent_request_id=item.get("parent_request_id"),
          source_type=item["source_type"], source_id=item["source_id"], source_url=item["source_url"],
          channel_id=item.get("channel_id"), channel_url=item.get("channel_url"),
          selection_reason=item["selection_reason"], selected_work_class=os.environ.get("NEXUS_SELECTED_WORK_CLASS", "DISCOVERY"),
          mission_id=mission_item.get("mission_id") if mission_item else None,
          mission_item_id=mission_item_id or None,
          v2_parent_links=item["v2_parent_links"],
          why_selected=os.environ.get("NEXUS_SELECTED_LANE_WHY", ""))
    def timeout_handler(signum, frame):
        raise TimeoutError(f"per-job timeout after {args.timeout_seconds}s")
    try:
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(args.timeout_seconds)
        # A known unchanged source is settled before any network fetch or
        # expensive processor. Assigned work may explicitly override this.
        refresh_state = {}
        try:
            from nexus_agent_platform.research_lane_scheduler import _source_refresh_snapshot
            from datetime import datetime, timezone
            refresh_state = _source_refresh_snapshot(item.get("lane_id") or lane_id, item.get("source_id", ""), datetime.now(timezone.utc))
        except Exception:
            refresh_state = {}
        if (refresh_state.get("cooling_down") or refresh_state.get("terminal")) and selected_work_class not in {"ASSIGNED", "DEMAND_DISCOVERY"} and not item.get("alpha_followup_required"):
            final_status = "DUPLICATE_UNCHANGED"
            event(execution_id, "EVIDENCE_READY", worker_id="research_operator_worker", result_status="PASS",
                  content_count=0, final_status=final_status, processor="pre_process_duplicate_check",
                  summary_created=False, extraction_created=False, scored=False, provenance_created=True,
                  stored=True, disposition="DUPLICATE", source_purpose=item.get("source_purpose"))
            for receipt in stage_receipts(item, {"processing_status": "DUPLICATE_UNCHANGED", "raw_acquired": False}):
                persistence.append_record("research_stage_receipts", receipt)
            settle_queue("MONITORING", result={"final_status": final_status, "source_id": item.get("source_id")})
            event(execution_id, "COMPLETED", worker_id="research_operator_worker", alpha_status="SKIPPED_DUPLICATE",
                  next_action="select new work after pre-process duplicate check")
            return 0
        # The normal worker must use the same unified source router as the
        # proven scheduled Research path. Alpha is intentionally not part of
        # base acquisition; it is reserved for mature packages/requested review.
        result = run_selected_capability(item, ai_route_result, execution_id)
        if result is None:
            result = process_scheduled_item(item)
        signal.alarm(0)
    except TimeoutError as exc:
        signal.alarm(0)
        event(execution_id, "FAILED_RETRYABLE", worker_id="research_operator_worker", error=str(exc), failure_class="PROVIDER_OR_ALPHA_TIMEOUT", retry_after="next scheduled wake")
        settle_queue("FAILED_RETRYABLE", result={"error": str(exc)}, blocker_type="PROVIDER_OR_ALPHA_TIMEOUT")
        return 124
    except Exception as exc:
        signal.alarm(0)
        event(execution_id, "FAILED_RETRYABLE", worker_id="research_operator_worker", error=str(exc)[:500], failure_class="RESEARCH_WORKER_FAILURE", retry_after="next scheduled wake")
        settle_queue("FAILED_RETRYABLE", result={"error": str(exc)[:500]}, blocker_type="RESEARCH_WORKER_FAILURE")
        if mission_item:
            record_item_result(mission_item_id, status="FAILED_RETRYABLE", result={"error": str(exc)[:500]}, next_action="retry bounded mission item")
        return 1
    final_status = result.get("final_status", "FAILED_RETRYABLE")
    ingestion_status = result.get("ingestion_status")
    durable_memory_confirmed = result.get("durable_memory_write_confirmed") is True and ingestion_status == "DURABLE_MEMORY"
    supabase_confirmed = ingestion_status in {"INGESTED", "INGESTED_EXISTING"} and (result.get("supabase_write_confirmed") or ingestion_status == "INGESTED_EXISTING")
    if not (durable_memory_confirmed or supabase_confirmed):
        error = result.get("error") or (result.get("canonical_ingestion") or {}).get("error") or "canonical Supabase ingestion was not verified"
        event(execution_id, "FAILED_RETRYABLE", worker_id="research_operator_worker",
              error=str(error)[:500], failure_class="CANONICAL_INGESTION_NOT_VERIFIED",
              supabase_source_id=result.get("supabase_source_id"), ingestion_status=ingestion_status)
        settle_queue("FAILED_RETRYABLE", result={"final_status": "FAILED_RETRYABLE", "error": str(error)[:500], "ingestion_status": ingestion_status}, blocker_type="CANONICAL_INGESTION_NOT_VERIFIED")
        return 1
    # Queue completion is now tied to the verified canonical source write.
    # Interpretation, Alpha, and department work are downstream of this point.
    if work_id:
        settle_queue("COMPLETE", result={"final_status": "INGESTED" if supabase_confirmed else "DURABLE_MEMORY",
                                          "ingestion_status": ingestion_status,
                                          "supabase_source_id": result.get("supabase_source_id"),
                                          "durable_package_id": result.get("durable_package_id")})
    try:
        for receipt in stage_receipts(item, result):
            persistence.append_record("research_stage_receipts", receipt)
    except Exception as exc:
        event(execution_id, "RESEARCH_V2_RECEIPTS_DEGRADED", worker_id="research_operator_worker", error=str(exc)[:300])
    ai_interpretation = interpret(item, ai_plan_result.get("plan", {}), result)
    item["ai_interpretation"] = ai_interpretation
    write_monitor_snapshot(item=item, stage="AI_RESULT_INTERPRETATION", plan=ai_plan_result.get("plan"), route_result=ai_route_result, interpretation=ai_interpretation)
    event(execution_id, "AI_RESULT_INTERPRETATION", worker_id="research_operator_worker",
          ai_status=ai_interpretation.get("status"), ai_model=ai_interpretation.get("model"),
          ai_model_calls=ai_interpretation.get("model_calls", 0), information_gain=ai_interpretation.get("information_gain"),
          objective_progress=ai_interpretation.get("objective_progress"), remaining_gaps=ai_interpretation.get("remaining_gaps"),
          recommended_followup=ai_interpretation.get("recommended_followup"), ready_for_alpha=ai_interpretation.get("ready_for_alpha"))
    learning = {
        "what_was_researched": item.get("question") or item.get("title") or item.get("source_url"),
        "what_nexus_learned": ai_interpretation.get("information_gain") or ai_interpretation.get("objective_progress"),
        "key_findings": (result.get("result") or {}).get("key_findings") or (result.get("result") or {}).get("findings") or result.get("summary"),
        "new_information": ai_interpretation.get("information_gain"),
        "duplicate_status": result.get("duplicate_status") or ("DUPLICATE_SKIPPED" if final_status == "DUPLICATE_UNCHANGED" else "NEW"),
        "why_it_matters": ai_interpretation.get("objective_progress") or (result.get("result") or {}).get("executive_summary"),
        "unresolved_questions": ai_interpretation.get("remaining_gaps"),
        "next_action": ai_interpretation.get("recommended_followup"),
        "current_pipeline_stage": "DUPLICATE" if final_status == "DUPLICATE_UNCHANGED" else "READY_FOR_ALPHA" if ai_interpretation.get("ready_for_alpha") else "EVIDENCE_READY",
    }
    event(execution_id, "RESEARCH_LEARNING_RECORD", worker_id="research_operator_worker", **learning)
    if mission_item:
        mission_status = "COMPLETED" if final_status in {"INGESTED", "INGESTED_EXISTING", "FULLY_PROCESSED", "PARTIAL_EVIDENCE", "DUPLICATE_UNCHANGED"} else "FAILED_RETRYABLE"
        record_item_result(mission_item_id, status=mission_status, result={"final_status": final_status, "source_id": item.get("source_id"), "research_package_id": (result.get("v2") or {}).get("research_package_id")}, next_action="continue next mission item" if mission_status == "COMPLETED" else "retry after backoff")
    # Refresh bookkeeping is advisory scheduling state.  A serialization or
    # filesystem fault here must never turn a completed Research result into a
    # dead worker; the next selector wake can recover the state from this
    # execution ledger.
    try:
        mark_source_result(lane_id, item.get("source_id", ""), final_status,
                           source_class=item.get("lifecycle") or item.get("source_type", ""))
    except Exception as exc:
        event(execution_id, "SOURCE_REFRESH_STATE_DEGRADED", worker_id="research_operator_worker",
              error=str(exc)[:500], next_action="continue; hydrate refresh state from execution history")
    event(execution_id, "EVIDENCE_READY", worker_id="research_operator_worker",
          result_status="PASS" if final_status in {"FULLY_PROCESSED", "DUPLICATE_UNCHANGED", "INGESTED", "INGESTED_EXISTING"} else "DEGRADED",
          content_count=1 if result.get("raw_acquired") else 0, final_status=final_status,
          processor=result.get("processor"), summary_created=result.get("summary_created", False),
          extraction_created=result.get("extraction_created", False), scored=result.get("scored", False),
          provenance_created=result.get("provenance_created", False), stored=result.get("stored", False),
          disposition=result.get("disposition"), research_id=(result.get("result") or {}).get("research_item_id"),
          work_id=item.get("work_id"), objective_id=item.get("objective_id"), parent_request_id=item.get("parent_request_id"),
          research_package_id=(result.get("v2") or {}).get("research_package_id"), research_mode=item.get("research_mode"),
          alpha_eligible=item.get("alpha_eligible", False), department_target=item.get("department_target"),
          project_id=item.get("project_id") or item.get("PROJECT"))
    if final_status == "CATEGORY_MISMATCH":
        mark_lane_backoff(lane_id, result.get("category_mismatch", "source/objective category mismatch"))
        fallback = strategy_changing_fallback(item, failure_class="CATEGORY_MISMATCH", error=result.get("category_mismatch", "source/objective category mismatch"), attempt=int(os.environ.get("NEXUS_ATTEMPT_COUNT", "1")))
        event(execution_id, "CATEGORY_MISMATCH", worker_id="research_operator_worker",
              category_mismatch=result.get("category_mismatch"), fallback=fallback)
        settle_queue("SUPERSEDED" if fallback else "FAILED_RETRYABLE",
                     result={**result, "fallback": fallback}, blocker_type="CATEGORY_MISMATCH")
        return 1
    if final_status.startswith("FAILED"):
        mark_lane_backoff(lane_id, result.get("error", "scheduled processor failed"))
        fallback = strategy_changing_fallback(item, failure_class="SCHEDULED_PROCESSOR_FAILURE", error=result.get("error", "scheduled processor failed"), attempt=int(os.environ.get("NEXUS_ATTEMPT_COUNT", "1")))
        event(execution_id, "FAILED_RETRYABLE", worker_id="research_operator_worker",
              error=result.get("error", "scheduled processor failed"), failure_class="SCHEDULED_PROCESSOR_FAILURE",
              retry_after="next scheduled wake")
        if fallback:
            event(execution_id, "STRATEGY_CHANGED", worker_id="research_operator_worker", **fallback)
        # Once a deterministic alternate exists, the failed source is
        # superseded so the same failing URL cannot compete on every wake.
        settle_queue("SUPERSEDED" if fallback else "FAILED_RETRYABLE",
                     result={**result, "fallback": fallback}, blocker_type="SCHEDULED_PROCESSOR_FAILURE")
        return 1
    alpha_result = {"status": "NOT_STARTED", "reason": "downstream_after_mechanical_ingestion"}
    event(execution_id, "COMPLETED", worker_id="research_operator_worker",
          work_id=item.get("work_id"), objective_id=item.get("objective_id"), parent_request_id=item.get("parent_request_id"),
          research_package_id=(result.get("v2") or {}).get("research_package_id"),
          alpha_status=alpha_result.get("decision") or alpha_result.get("status", "SKIPPED"),
          alpha_receipt_id=alpha_result.get("receipt_id"), alpha_evaluation_id=alpha_result.get("evaluation_id"),
          alpha_followup_work_id=alpha_result.get("followup_work_id"), alpha_handoff_id=alpha_result.get("handoff_id"),
          research_mode=item.get("research_mode"), alpha_eligible=item.get("alpha_eligible", False),
          department_target=item.get("department_target"), project_id=item.get("project_id") or item.get("PROJECT"),
          next_action="continue next scheduled research wake")
    try:
        from nexus_agent_platform.supabase_knowledge import persist_finding_and_route
        information_route = persist_finding_and_route(item=item, result={**result, "ai_interpretation": ai_interpretation}, alpha=alpha_result)
        event(execution_id, "DEPARTMENT_INFORMATION_ROUTED", worker_id="research_operator_worker",
              information_route_status=information_route.get("status"), finding_id=information_route.get("finding_id"),
              classification=information_route.get("classification"), inboxes=information_route.get("inboxes"))
        from nexus_agent_platform.supabase_knowledge import process_expert_information_item
        for inbox in information_route.get("inboxes") or []:
            if inbox.get("status", "PENDING") == "PENDING":
                expert_result = process_expert_information_item(
                    information_item_id=inbox.get("information_item_id"),
                    disposition="LEARN_ONLY",
                    reason="Expert reviewed canonical Research evidence and stored domain learning.",
                )
                event(execution_id, "DEPARTMENT_EXPERT_ASSESSMENT", worker_id="research_operator_worker",
                      expert_id=inbox.get("expert_id"), information_item_id=inbox.get("information_item_id"),
                      expert_status=expert_result.get("status"), assessment_id=expert_result.get("assessment_id"),
                      memory_records_loaded=expert_result.get("memory_records_loaded"))
    except Exception as exc:
        event(execution_id, "DEPARTMENT_INFORMATION_ROUTING_DEGRADED", worker_id="research_operator_worker", error=str(exc)[:300])
    try:
        return_department_request(item, package_id=(result.get("v2") or {}).get("research_package_id"), alpha_result=alpha_result)
    except Exception as exc:
        event(execution_id, "DEPARTMENT_RETURN_DEGRADED", worker_id="research_operator_worker",
              error=str(exc)[:300], next_action="department may re-read the completed package")
    if item.get("parent_goal_id"):
        try:
            evaluate_goal_result(
                goal_id=str(item.get("parent_goal_id")), objective_id=str(item.get("objective_id")),
                result={**result, "ai_interpretation": ai_interpretation}, alpha=alpha_result,
            )
        except Exception as exc:
            event(execution_id, "GOAL_FEEDBACK_DEGRADED", worker_id="research_operator_worker", error=str(exc)[:300])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
