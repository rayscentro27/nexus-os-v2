"""Idempotently normalize known Research backlog sources into the one FIFO queue."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from nexus_agent_platform.research_work_queue import default_queue

ROOT = Path(__file__).resolve().parents[2]


def _json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return default


def _source_key(source_type: str, source_id: str, question: str) -> str:
    return f"{source_type}:{source_id}:{question}"


def migrate() -> dict[str, Any]:
    queue = default_queue()
    queue.migrate_fifo()
    existing = queue.load().get("items", [])
    pending_keys = {str(row.get("dedup_key")) for row in existing if row.get("dedup_key") and row.get("status") in {"QUEUED", "WAITING", "IN_PROGRESS"}}
    created: list[dict[str, Any]] = []

    channels = (_json(ROOT / "configs/youtube_research_channels.json", {}) or {}).get("channels", [])
    for channel in channels:
        if not channel.get("enabled") or not channel.get("approved_by_ray"):
            continue
        channel_id = str(channel.get("channel_id"))
        question = "inventory channel, discover unseen videos, and continue historical backfill"
        key = _source_key("YOUTUBE_CHANNEL", channel_id, question)
        if key in pending_keys:
            continue
        created.append(queue.enqueue(
            work_id=f"youtube-channel:{channel_id}:inventory",
            request_type="YOUTUBE_CHANNEL", category="YOUTUBE_CONTENT", work_class="MONITORED",
            source_type="YOUTUBE_CHANNEL", source_name=channel.get("name"), source_id=channel_id,
            source_url=channel.get("url"), channel_id=channel_id, channel_name=channel.get("name"),
            channel_url=channel.get("url"), objective=", ".join(channel.get("categories", [])),
            research_question=question, question=question, research_instructions="Enumerate one bounded page and enqueue unseen videos.",
            required_tool="YOUTUBE", required_capability="YOUTUBE", expected_output="channel inventory and video queue items",
            requested_by="monitored_source", dedup_key=key, lifecycle="MONITORED", alpha_eligible=False,
        ))
        pending_keys.add(key)

    registry = _json(ROOT / "data/runtime/alpha_source_registry.json", [])
    if isinstance(registry, list):
        for source in registry:
            source_type = str(source.get("source_type") or "WEB_PAGE").upper()
            url = source.get("source_url") or source.get("canonical_url") or source.get("url")
            if not url:
                continue
            if source_type == "YOUTUBE_CHANNEL":
                continue  # channel watchlist above is canonical and de-duplicated
            source_id = str(source.get("source_id") or source.get("id") or url)
            if source_type == "YOUTUBE_VIDEO":
                request_type, required_tool = "YOUTUBE_VIDEO", "YOUTUBE"
            elif "TRADINGVIEW" in source_type or "tradingview.com" in url:
                request_type, required_tool, source_type = "TRADINGVIEW_STRATEGY", "TRADINGVIEW", "TRADINGVIEW_STRATEGY"
            elif "GITHUB" in source_type or "github.com" in url:
                request_type, required_tool, source_type = "GITHUB_REPO", "GITHUB", "GITHUB_REPO"
            else:
                request_type, required_tool = "WEB_PAGE", "WEB"
            question = source.get("objective") or source.get("purpose") or f"Research assigned source {source.get('source_name') or source_id}."
            key = _source_key(source_type, source_id, question)
            if key in pending_keys:
                continue
            created.append(queue.enqueue(
                work_id=f"source-refresh:{source_id}", request_type=request_type, category=source.get("primary_category") or "OTHER",
                work_class="MONITORED", source_type=source_type, source_name=source.get("source_name") or source_id,
                source_id=source_id, source_url=url, objective=source.get("objective") or source.get("purpose") or source_id,
                research_question=question, question=question, research_instructions=f"Research the assigned source itself: {url}",
                required_tool=required_tool, required_capability=required_tool, expected_output="learning record",
                requested_by="source_registry", dedup_key=key, lifecycle="MONITORED", alpha_eligible=True,
                department_target=(source.get("allowed_destination_departments") or [None])[0],
            ))
            pending_keys.add(key)

    return {"created": len(created), "created_work_ids": [row.get("work_id") for row in created],
            "queue": queue.migrate_fifo()}


if __name__ == "__main__":
    print(json.dumps(migrate(), indent=2, default=str))
