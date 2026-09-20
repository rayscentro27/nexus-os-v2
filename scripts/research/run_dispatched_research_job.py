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
from nexus_agent_platform.research.source_semantics import annotate, autonomous_discovery_allowed  # noqa: E402
from research_v2 import parent_links_for_item  # noqa: E402
from bounded_research_missions import claim_item, record_item_result  # noqa: E402


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
    "SEO_SEARCH_DEMAND": [("SEO_RESEARCH", "google-seo-starter", "https://developers.google.com/search/docs/fundamentals/seo-starter-guide", "Google SEO Starter Guide")],
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
                    "author": queued.get("requested_by", "Nexus Research"),
                    "category": lane_id, "selection_reason": "governed_objective_source_candidate",
                    "work_id": queued.get("work_id"), "work_class": queued.get("work_class"),
                    "objective_id": queued.get("objective_id"), "mission_id": queued.get("mission_id"),
                    "mission_item_id": queued.get("mission_item_id"), "parent_request_id": queued.get("parent_request_id"),
                    "source_candidates": candidates,
                    "required_capabilities": queued.get("required_capabilities", []),
                    "ai_plan_id": queued.get("ai_plan_id"),
                    "alpha_followup_required": queued.get("alpha_followup_required", False),
                    "department_target": queued.get("department_target"), "lifecycle": queued.get("lifecycle", "MONITORED")}
        return {"source_type": queued.get("source_type") or "WEB_PAGE",
                "source_id": queued.get("source_id") or queued.get("work_id"),
                "source_url": queued.get("source_url") or queued.get("url") or known[1] or "",
                "title": queued.get("title") or queued.get("question") or known[2] or queued.get("source_id") or queued.get("work_id"),
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
                "lifecycle": queued.get("lifecycle", "MONITORED")}
    if lane_id == "YOUTUBE_CONTENT":
        config = json.loads((ROOT / "configs/youtube_research_channels.json").read_text(encoding="utf-8"))
        channels = [row for row in config.get("channels", []) if row.get("enabled") and row.get("approved_by_ray")]
        if not channels:
            raise RuntimeError("approved YouTube channel watchlist is empty")
        mission_target = os.environ.get("NEXUS_MISSION_TARGET_ID", "")
        channel = next((row for row in channels if str(row.get("channel_id")) == mission_target), None)
        channel = channel or channels[int(hashlib.sha256(execution_id.encode("utf-8")).hexdigest()[:8], 16) % len(channels)]
        # Use the durable channel id for the bounded RSS fallback.  Handle
        # pages remain the canonical display URL but are not required for
        # metadata discovery.
        discovery_url = f"https://www.youtube.com/channel/{channel['channel_id']}"
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
                "channel_id": channel.get("channel_id"), "channel_url": channel["url"],
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
        alpha_followup_required=item.get("alpha_followup_required", False), lifecycle="ONE_TIME",
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
        "radar": radar,
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
    if work_id:
        queued_context = next((row for row in default_queue().load().get("items", []) if row.get("work_id") == work_id), {})
        for env_key, field in (("NEXUS_OBJECTIVE_ID", "objective_id"), ("NEXUS_PARENT_REQUEST_ID", "parent_request_id"), ("NEXUS_MARKETING_OBJECTIVE_ID", "marketing_objective_id")):
            if queued_context.get(field) and not os.environ.get(env_key):
                os.environ[env_key] = str(queued_context[field])
    event(execution_id, "CLAIMED", worker_id="research_operator_worker", attempt_count=1)
    event(execution_id, "RUNNING", worker_id="research_operator_worker", timeout_seconds=args.timeout_seconds)
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
    # The investigator is deliberately before acquisition. It plans against
    # the objective and certified capability registry; processors still own
    # all evidence acquisition and persistence.
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
    ai_interpretation = interpret(item, ai_plan_result.get("plan", {}), result)
    item["ai_interpretation"] = ai_interpretation
    write_monitor_snapshot(item=item, stage="AI_RESULT_INTERPRETATION", plan=ai_plan_result.get("plan"), route_result=ai_route_result, interpretation=ai_interpretation)
    event(execution_id, "AI_RESULT_INTERPRETATION", worker_id="research_operator_worker",
          ai_status=ai_interpretation.get("status"), ai_model=ai_interpretation.get("model"),
          ai_model_calls=ai_interpretation.get("model_calls", 0), information_gain=ai_interpretation.get("information_gain"),
          objective_progress=ai_interpretation.get("objective_progress"), remaining_gaps=ai_interpretation.get("remaining_gaps"),
          recommended_followup=ai_interpretation.get("recommended_followup"), ready_for_alpha=ai_interpretation.get("ready_for_alpha"))
    if mission_item:
        mission_status = "COMPLETED" if final_status in {"FULLY_PROCESSED", "PARTIAL_EVIDENCE", "DUPLICATE_UNCHANGED"} else "FAILED_RETRYABLE"
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
          result_status="PASS" if final_status in {"FULLY_PROCESSED", "DUPLICATE_UNCHANGED"} else "DEGRADED",
          content_count=1 if result.get("raw_acquired") else 0, final_status=final_status,
          processor=result.get("processor"), summary_created=result.get("summary_created", False),
          extraction_created=result.get("extraction_created", False), scored=result.get("scored", False),
          provenance_created=result.get("provenance_created", False), stored=result.get("stored", False),
          disposition=result.get("disposition"), research_id=(result.get("result") or {}).get("research_item_id"),
          work_id=item.get("work_id"), objective_id=item.get("objective_id"), parent_request_id=item.get("parent_request_id"),
          research_package_id=(result.get("v2") or {}).get("research_package_id"))
    if final_status.startswith("FAILED"):
        mark_lane_backoff(lane_id, result.get("error", "scheduled processor failed"))
        fallback = strategy_changing_fallback(item, failure_class="SCHEDULED_PROCESSOR_FAILURE", error=result.get("error", "scheduled processor failed"), attempt=int(os.environ.get("NEXUS_ATTEMPT_COUNT", "1")))
        event(execution_id, "FAILED_RETRYABLE", worker_id="research_operator_worker",
              error=result.get("error", "scheduled processor failed"), failure_class="SCHEDULED_PROCESSOR_FAILURE",
              retry_after="next scheduled wake")
        if fallback:
            event(execution_id, "STRATEGY_CHANGED", worker_id="research_operator_worker", **fallback)
        settle_queue("WAITING" if fallback else "FAILED_RETRYABLE", result={**result, "fallback": fallback}, blocker_type="SCHEDULED_PROCESSOR_FAILURE")
        return 1
    queue_status = "COMPLETE" if final_status in {"FULLY_PROCESSED", "PARTIAL_EVIDENCE"} else "MONITORING" if final_status == "DUPLICATE_UNCHANGED" else "FAILED_RETRYABLE"
    settle_queue(queue_status, result={"final_status": final_status, "source_id": item.get("source_id"),
                                       "research_package_id": (result.get("v2") or {}).get("research_package_id"),
                                       "ai_plan_id": item.get("ai_plan_id"), "selected_executor_id": item.get("selected_executor_id"),
                                       "ai_interpretation": ai_interpretation})
    alpha_result = {"status": "SKIPPED", "reason": "monitoring_or_duplicate"}
    # Assigned objective/follow-up work is an Alpha-eligible handoff.  Keep
    # routine monitoring cheap, but do not let evidence-ready assigned work
    # disappear after persistence.  The bridge is bounded and restart-safe.
    if final_status in {"FULLY_PROCESSED", "PARTIAL_EVIDENCE"} and selected_work_class in {"ASSIGNED", "DEMAND_DISCOVERY"}:
        source_row = ((result.get("v2") or {}).get("source") or {})
        try:
            alpha_result = review_assigned_research_output(
                source_id=item.get("source_id", ""), source_title=item.get("title", ""),
                source_url=item.get("source_url", ""),
                source_text=source_row.get("text", "") if isinstance(source_row, dict) else "",
                objective_id=item.get("objective_id"),
                force_rereview=bool(item.get("alpha_followup_required")),
            )
        except Exception as exc:
            alpha_result = {"status": "FAILED_RETRYABLE", "error": str(exc)[:500]}
    event(execution_id, "COMPLETED", worker_id="research_operator_worker",
          work_id=item.get("work_id"), objective_id=item.get("objective_id"), parent_request_id=item.get("parent_request_id"),
          research_package_id=(result.get("v2") or {}).get("research_package_id"),
          alpha_status=alpha_result.get("decision") or alpha_result.get("status", "SKIPPED"),
          alpha_receipt_id=alpha_result.get("receipt_id"), alpha_evaluation_id=alpha_result.get("evaluation_id"),
          alpha_followup_work_id=alpha_result.get("followup_work_id"), alpha_handoff_id=alpha_result.get("handoff_id"),
          next_action="continue next scheduled research wake")
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
