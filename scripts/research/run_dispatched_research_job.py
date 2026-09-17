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
from youtube_full_pipeline import select_channel_videos  # noqa: E402
from nexus_agent_platform.research_lane_scheduler import mark_lane_backoff  # noqa: E402


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
        channel = channels[int(hashlib.sha256(execution_id.encode("utf-8")).hexdigest()[:8], 16) % len(channels)]
        videos = select_channel_videos(channel["url"], 1)
        if not videos:
            raise RuntimeError(f"no eligible videos discovered for channel {channel['name']}")
        video = videos[0]
        return {"source_type": "YOUTUBE_VIDEO", "source_id": video["video_id"], "source_url": video["url"],
                "title": video.get("title", video["video_id"]), "author": channel["name"],
                "channel_id": channel.get("channel_id"), "channel_url": channel["url"],
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
    item = select_scheduled_item(lane_id, execution_id)
    event(execution_id, "SOURCE_SELECTED", worker_id="research_operator_worker", lane_id=lane_id,
          source_type=item["source_type"], source_id=item["source_id"], source_url=item["source_url"],
          channel_id=item.get("channel_id"), channel_url=item.get("channel_url"),
          selection_reason=item["selection_reason"], selected_work_class=os.environ.get("NEXUS_SELECTED_WORK_CLASS", "DISCOVERY"),
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
        return 1
    final_status = result.get("final_status", "FAILED_RETRYABLE")
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
