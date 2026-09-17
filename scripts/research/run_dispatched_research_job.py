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
from research_v2 import parent_links_for_item  # noqa: E402
from bounded_research_missions import claim_item, record_item_result  # noqa: E402


# Bounded, read-only scheduled source selection.  These are existing public
# research sources; the scheduler still owns lane fairness and this worker
# only resolves the selected lane to one real item for the canonical router.
SOURCE_POOLS = {
    "BUSINESS_MARKET": [
        ("WEB_PAGE", "sba-business-guide", "https://www.sba.gov/business-guide", "SBA business guide"),
        ("WEB_PAGE", "mobile-detailing-academy-phoenix", "https://mobiledetailingacademy.com/mobile-detailing/phoenix-az", "Phoenix mobile detailing market example"),
    ],
    "FUNDING_LENDER": [("WEB_PAGE", "sba-loans", "https://www.sba.gov/loans", "SBA loans and funding")],
    "GRANTS_GOVERNMENT": [("WEB_PAGE", "sba-grants", "https://www.sba.gov/funding-programs/grants", "SBA grants")],
    "AFFILIATE_REVENUE": [("WEB_PAGE", "hubspot-affiliate", "https://www.hubspot.com/partners/affiliates", "HubSpot affiliate program")],
    "SEO_SEARCH_DEMAND": [("SEO_RESEARCH", "google-seo-starter", "https://developers.google.com/search/docs/fundamentals/seo-starter-guide", "Google SEO Starter Guide")],
    "SOCIAL_CONTENT": [("WEB_PAGE", "reddit-smallbusiness", "https://www.reddit.com/r/smallbusiness/", "Small business community signals")],
    "YOUTUBE_CONTENT": [("YOUTUBE_VIDEO", "zbAmmnMh5ew", "https://www.youtube.com/watch?v=zbAmmnMh5ew", "Ray-approved YouTube research video")],
    "COMPETITOR_INTELLIGENCE": [("WEB_PAGE", "shopify-partners", "https://www.shopify.com/partners", "Shopify partner ecosystem")],
    "TRADING_MARKETS": [("WEB_PAGE", "investor-investing-basics", "https://www.investor.gov/introduction-investing", "Investor.gov investing basics")],
    "GITHUB_TECHNOLOGY": [("GITHUB_REPO", "mvanhorn/last30days-skill", "https://github.com/mvanhorn/last30days-skill", "last30days-skill repository")],
    "PLATFORM_CAPABILITY_INTELLIGENCE": [("GITHUB_REPO", "sushantkarn/SEO-engine", "https://github.com/sushantkarn/SEO-engine", "SEO-engine repository")],
}


def select_scheduled_item(lane_id: str, execution_id: str) -> dict:
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
        return {"source_type": "YOUTUBE_VIDEO", "source_id": video["video_id"], "source_url": video["url"],
                "title": video.get("title", video["video_id"]), "author": channel["name"],
                "channel_id": channel.get("channel_id"), "channel_url": channel["url"],
                "discovery_method": video.get("discovery_method", "YOUTUBE_RSS"),
                "category": "YOUTUBE_CONTENT", "selection_reason": "approved_channel_watchlist"}
    pool = SOURCE_POOLS.get(lane_id) or SOURCE_POOLS["BUSINESS_MARKET"]
    index = int(hashlib.sha256(execution_id.encode("utf-8")).hexdigest()[:8], 16) % len(pool)
    source_type, source_id, source_url, title = pool[index]
    return {"source_type": source_type, "source_id": source_id, "source_url": source_url,
            "title": title, "category": lane_id, "selection_reason": "scheduled_lane_source_pool"}


def event(execution_id: str, status: str, **values) -> None:
    JOBS.parent.mkdir(parents=True, exist_ok=True)
    row = {"execution_id": execution_id, "status": status, "at": datetime.now(timezone.utc).isoformat(), **values}
    with JOBS.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")
        handle.flush()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execution-id", required=True)
    parser.add_argument("--timeout-seconds", type=int, default=180)
    args = parser.parse_args()
    execution_id = args.execution_id
    event(execution_id, "CLAIMED", worker_id="research_operator_worker", attempt_count=1)
    event(execution_id, "RUNNING", worker_id="research_operator_worker", timeout_seconds=args.timeout_seconds)
    lane_id = os.environ.get("NEXUS_SELECTED_LANE_ID", "BUSINESS_MARKET")
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
    try:
        item = select_scheduled_item(lane_id, execution_id)
    except TimeoutError as exc:
        event(execution_id, "FAILED_RETRYABLE", worker_id="research_operator_worker",
              error=str(exc)[:500], failure_class="SOURCE_SELECTION_TIMEOUT",
              retry_after="next scheduled wake")
        if mission_item:
            record_item_result(mission_item_id, status="FAILED_RETRYABLE",
                               result={"error": str(exc)[:500], "failure_class": "SOURCE_SELECTION_TIMEOUT"},
                               next_action="retry after bounded source backoff")
        return 124
    except Exception as exc:
        event(execution_id, "FAILED_RETRYABLE", worker_id="research_operator_worker",
              error=str(exc)[:500], failure_class="SOURCE_SELECTION_FAILURE",
              retry_after="next scheduled wake")
        if mission_item:
            record_item_result(mission_item_id, status="FAILED_RETRYABLE",
                               result={"error": str(exc)[:500], "failure_class": "SOURCE_SELECTION_FAILURE"},
                               next_action="retry after bounded source backoff")
        return 1
    item["v2_parent_links"] = parent_links_for_item(item)
    event(execution_id, "SOURCE_SELECTED", worker_id="research_operator_worker", lane_id=lane_id,
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
        # The normal worker must use the same unified source router as the
        # proven scheduled Research path. Alpha is intentionally not part of
        # base acquisition; it is reserved for mature packages/requested review.
        result = process_scheduled_item(item)
        signal.alarm(0)
    except TimeoutError as exc:
        signal.alarm(0)
        event(execution_id, "FAILED_RETRYABLE", worker_id="research_operator_worker", error=str(exc), failure_class="PROVIDER_OR_ALPHA_TIMEOUT", retry_after="next scheduled wake")
        return 124
    except Exception as exc:
        signal.alarm(0)
        event(execution_id, "FAILED_RETRYABLE", worker_id="research_operator_worker", error=str(exc)[:500], failure_class="RESEARCH_WORKER_FAILURE", retry_after="next scheduled wake")
        if mission_item:
            record_item_result(mission_item_id, status="FAILED_RETRYABLE", result={"error": str(exc)[:500]}, next_action="retry bounded mission item")
        return 1
    final_status = result.get("final_status", "FAILED_RETRYABLE")
    if mission_item:
        mission_status = "COMPLETED" if final_status in {"FULLY_PROCESSED", "DUPLICATE_UNCHANGED"} else "FAILED_RETRYABLE"
        record_item_result(mission_item_id, status=mission_status, result={"final_status": final_status, "source_id": item.get("source_id"), "research_package_id": (result.get("v2") or {}).get("research_package_id")}, next_action="continue next mission item" if mission_status == "COMPLETED" else "retry after backoff")
    # Refresh bookkeeping is advisory scheduling state.  A serialization or
    # filesystem fault here must never turn a completed Research result into a
    # dead worker; the next selector wake can recover the state from this
    # execution ledger.
    try:
        mark_source_result(lane_id, item.get("source_id", ""), final_status, source_class=item.get("source_type", ""))
    except Exception as exc:
        event(execution_id, "SOURCE_REFRESH_STATE_DEGRADED", worker_id="research_operator_worker",
              error=str(exc)[:500], next_action="continue; hydrate refresh state from execution history")
    event(execution_id, "EVIDENCE_READY", worker_id="research_operator_worker",
          result_status="PASS" if final_status in {"FULLY_PROCESSED", "DUPLICATE_UNCHANGED"} else "DEGRADED",
          content_count=1 if result.get("raw_acquired") else 0, final_status=final_status,
          processor=result.get("processor"), summary_created=result.get("summary_created", False),
          extraction_created=result.get("extraction_created", False), scored=result.get("scored", False),
          provenance_created=result.get("provenance_created", False), stored=result.get("stored", False),
          disposition=result.get("disposition"), research_id=(result.get("result") or {}).get("research_item_id"))
    if final_status.startswith("FAILED"):
        mark_lane_backoff(lane_id, result.get("error", "scheduled processor failed"))
        event(execution_id, "FAILED_RETRYABLE", worker_id="research_operator_worker",
              error=result.get("error", "scheduled processor failed"), failure_class="SCHEDULED_PROCESSOR_FAILURE",
              retry_after="next scheduled wake")
        return 1
    event(execution_id, "COMPLETED", worker_id="research_operator_worker", alpha_status="NOT_INVOKED",
          next_action="continue next scheduled research wake")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
