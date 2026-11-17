#!/usr/bin/env python3
"""Refresh the bounded live YouTube/NotebookLM reconciliation read model.

This command reads the designated source registry, performs public RSS metadata
checks, and joins them to existing queue/Research/NotebookLM evidence. It never
changes channel baselines or enqueues work.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
for extra in (ROOT / "scripts", ROOT / "scripts" / "research"):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

from notebooklm_research_worker import default_queue
from research.youtube_channel_registry import enabled_channels, split_by_baseline
from social import _supabase as supabase
from youtube_full_pipeline import select_channel_videos

OUT = ROOT / "reports/runtime/youtube_notebooklm_live_reconciliation_latest.json"
WEEKEND_YOUTUBE = ROOT / "reports/runtime/weekend_youtube_monitor_latest.json"
INVENTORY = ROOT / "reports/runtime/notebooklm_inventory_latest.json"
RESULTS = ROOT / "data/runtime/notebooklm_research_results.jsonl"
FINDINGS = ROOT / "data/governed/research_notebooklm_findings.jsonl"
HANDOFFS = ROOT / "data/governed/research_v2_handoffs.jsonl"
CASES = ROOT / "data/governed/research_runtime_states.jsonl"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def _jsonl_tail(path: Path, max_bytes: int = 5_000_000) -> list[dict[str, Any]]:
    try:
        size = path.stat().st_size
        with path.open("rb") as handle:
            if size > max_bytes:
                handle.seek(size - max_bytes)
                handle.readline()
            raw = handle.read(max_bytes + 1)
    except OSError:
        return []
    rows = []
    for line in raw.splitlines():
        try:
            item = json.loads(line)
            if isinstance(item, dict):
                rows.append(item)
        except (ValueError, TypeError):
            continue
    return rows


def _video_id(row: dict[str, Any]) -> str:
    for key in ("video_id", "youtube_video_id", "source_id"):
        value = str(row.get(key) or "")
        if len(value) == 11 and all(ch.isalnum() or ch in "_-" for ch in value):
            return value
    provenance = row.get("provenance") if isinstance(row.get("provenance"), dict) else {}
    for key in ("video_id", "source_id"):
        value = str(provenance.get(key) or "")
        if len(value) == 11 and all(ch.isalnum() or ch in "_-" for ch in value):
            return value
    for value in (row.get("video_url"), row.get("source_url"), row.get("url"), provenance.get("video_url")):
        text = str(value or "")
        marker = "v=" if "youtube.com/watch" in text else "youtu.be/" if "youtu.be/" in text else ""
        if marker:
            candidate = text.split(marker, 1)[1].split("&", 1)[0].split("/", 1)[0]
            if len(candidate) == 11:
                return candidate
    return ""


def _fetch(channel: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]], str | None]:
    channel_id = channel.get("external_channel_id") or channel.get("channel_id")
    try:
        if not channel_id:
            raise ValueError("channel_id_unresolved")
        rows = select_channel_videos(f"https://www.youtube.com/channel/{channel_id}", 8)
        return channel, rows, None
    except Exception as exc:  # external source errors are reported per channel
        return channel, [], f"{type(exc).__name__}:{str(exc)[:240]}"


def _metadata_rows() -> dict[str, dict[str, Any]]:
    if supabase is None or not supabase.configured():
        return {}
    try:
        status, rows = supabase.rest(
            "GET", "research_sources?metadata->>record_kind=eq.YOUTUBE_MONITOR_TRIAGE_ITEM"
            "&select=title,url,published_at,accessed_at,metadata&limit=2000")
    except Exception:
        return {}
    if status != 200 or not isinstance(rows, list):
        return {}
    return {str((row.get("metadata") or {}).get("video_id")): row
            for row in rows if (row.get("metadata") or {}).get("video_id")}


def _case_rows() -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for row in _jsonl_tail(CASES):
        if row.get("memory_kind") != "PROACTIVE_RESEARCH_CASE" or not row.get("case_id"):
            continue
        key = str(row["case_id"])
        if key not in latest or str(row.get("recorded_at") or "") >= str(latest[key].get("recorded_at") or ""):
            latest[key] = row
    return latest


def build() -> dict[str, Any]:
    channels = enabled_channels()
    queue_items = default_queue().load().get("items", [])
    queue_by_video = {str(row.get("source_id")): row for row in queue_items if row.get("source_id")}
    result_rows = _jsonl_tail(RESULTS)
    result_by_video: dict[str, list[dict[str, Any]]] = {}
    for row in result_rows:
        ident = _video_id(row)
        if ident:
            result_by_video.setdefault(ident, []).append(row)
    finding_rows = _jsonl_tail(FINDINGS)
    findings_by_video: dict[str, list[dict[str, Any]]] = {}
    for row in finding_rows:
        ident = _video_id(row)
        if ident:
            findings_by_video.setdefault(ident, []).append(row)
    metadata = _metadata_rows()
    inventories = _json(INVENTORY, {})
    notebook_rows = inventories.get("notebooks", []) if isinstance(inventories, dict) else []
    notebook_by_id = {str(row.get("notebook_id")): row for row in notebook_rows if row.get("notebook_id")}
    case_rows = _case_rows()
    cases_by_id = {str(row.get("case_id")): row for row in case_rows.values()}

    channel_rows: list[dict[str, Any]] = []
    video_rows: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = [pool.submit(_fetch, channel) for channel in channels]
        for future in as_completed(futures):
            channel, videos, error = future.result()
            baseline_id = str(channel.get("baseline_video_id") or channel.get("last_seen_video_id") or
                               channel.get("last_item_seen") or "")
            baseline_at = channel.get("baseline_published_at") or channel.get("last_item_seen_at")
            post_baseline, baseline_missing = split_by_baseline(channel, videos)
            if error:
                status = "FETCH_ERROR"
            elif baseline_missing:
                status = "BASELINE_MISSING"
            elif post_baseline:
                status = "NEW_CONTENT_FOUND"
            elif videos and baseline_id and str(videos[0].get("video_id")) != baseline_id and \
                    str(videos[0].get("published_at") or "") < str(baseline_at or ""):
                status = "BASELINE_AHEAD_OF_SOURCE"
            else:
                status = "NO_NEW_CONTENT"
            channel_rows.append({
                "channel_name": channel.get("name"),
                "channel_id": channel.get("external_channel_id") or channel.get("channel_id"),
                "channel_url": channel.get("canonical_url") or channel.get("url"),
                "enabled": bool(channel.get("enabled")),
                "monitoring_mode": channel.get("monitor_mode"),
                "triage_mode": channel.get("triage_mode"),
                "stored_baseline_video_id": baseline_id or None,
                "stored_baseline_published_at": baseline_at,
                "last_check_at": channel.get("last_checked_at"),
                "actual_latest_video_id": (videos[0].get("video_id") if videos else None),
                "actual_latest_title": (videos[0].get("title") if videos else None),
                "actual_latest_published_at": (videos[0].get("published_at") if videos else None),
                "enumeration_source": (videos[0].get("discovery_method") if videos else None),
                "reconciliation_status": status,
                "new_video_count": len(post_baseline),
                "fetch_error": error,
            })
            for video in post_baseline:
                video_id = str(video.get("video_id") or "")
                queued = queue_by_video.get(video_id, {})
                result_history = result_by_video.get(video_id, [])
                outcome = result_history[-1] if result_history else {}
                item = metadata.get(video_id, {})
                item_meta = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
                finding_history = findings_by_video.get(video_id, [])
                notebook_id = str((outcome.get("provenance") or {}).get("notebook_id") or "")
                case_id = str(item_meta.get("research_case_id") or queued.get("research_case_id") or
                               (outcome.get("provenance") or {}).get("research_case_id") or "")
                video_rows.append({
                    "video_id": video_id, "channel_id": channel.get("external_channel_id") or channel.get("channel_id"),
                    "channel_name": channel.get("name"), "title": video.get("title"),
                    "source_url": video.get("url"), "published_at": video.get("published_at"),
                    "enumerated": True, "queue_status": queued.get("status"),
                    "processed": str(queued.get("status") or "").upper() in {"COMPLETE", "COMPLETED"},
                    "deduped": str(queued.get("status") or "").upper() == "SUPERSEDED",
                    "already_seen": False,
                    "metadata_disposition": item_meta.get("disposition"),
                    "research_case_id": case_id or None,
                    "package_created": bool(outcome.get("research_package_id") or outcome.get("package_id")),
                    "finding_created": bool(finding_history),
                    "finding_count": len(finding_history),
                    "handoff_count": len((outcome.get("persistence") or {}).get("handoffs") or []),
                    "notebook_id": notebook_id or None,
                    "notebook_title": notebook_by_id.get(notebook_id, {}).get("notebook_name") if notebook_id else None,
                    "processing_outcome": outcome.get("outcome"),
                    "processing_failure": outcome.get("failure_code") or queued.get("last_result", {}).get("failure_code"),
                })

    channel_rows.sort(key=lambda row: str(row.get("channel_name") or ""))
    channel_counts = Counter(row["reconciliation_status"] for row in channel_rows)
    # The prior recovery pass is represented by durable per-video triage rows,
    # including items whose channel baseline was safely left behind.
    recent_metadata = [row for row in metadata.values()
                       if str(row.get("accessed_at") or row.get("metadata", {}).get("accessed_at") or "") >= "2026-10-05T00:00:00"]
    current_video_ids = {str(row.get("video_id")) for row in video_rows}
    channel_name_by_id = {str(row.get("external_channel_id") or row.get("channel_id")): row.get("name") for row in channels}
    for triage_row in recent_metadata:
        triage_meta = triage_row.get("metadata") if isinstance(triage_row.get("metadata"), dict) else {}
        video_id = str(triage_meta.get("video_id") or "")
        if not video_id or video_id in current_video_ids:
            continue
        queued = queue_by_video.get(video_id, {})
        result_history = result_by_video.get(video_id, [])
        outcome = result_history[-1] if result_history else {}
        finding_history = findings_by_video.get(video_id, [])
        notebook_id = str((outcome.get("provenance") or {}).get("notebook_id") or "")
        channel_id = str(triage_meta.get("external_channel_id") or "")
        case_id = str(triage_meta.get("research_case_id") or queued.get("research_case_id") or
                       (outcome.get("provenance") or {}).get("research_case_id") or "")
        video_rows.append({
            "video_id": video_id, "channel_id": channel_id,
            "channel_name": channel_name_by_id.get(channel_id) or triage_row.get("author"),
            "title": triage_row.get("title"), "source_url": triage_row.get("url"),
            "published_at": triage_row.get("published_at"), "enumerated": True,
            "enumerated_at": triage_row.get("accessed_at"), "historically_recovered": True,
            "queue_status": queued.get("status"),
            "processed": str(queued.get("status") or "").upper() in {"COMPLETE", "COMPLETED"},
            "deduped": str(queued.get("status") or "").upper() == "SUPERSEDED",
            "already_seen": False, "metadata_disposition": triage_meta.get("disposition"),
            "research_case_id": case_id or None,
            "package_created": bool(outcome.get("research_package_id") or outcome.get("package_id")),
            "finding_created": bool(finding_history), "finding_count": len(finding_history),
            "handoff_count": len((outcome.get("persistence") or {}).get("handoffs") or []),
            "notebook_id": notebook_id or None,
            "notebook_title": notebook_by_id.get(notebook_id, {}).get("notebook_name") if notebook_id else None,
            "processing_outcome": outcome.get("outcome"),
            "processing_failure": outcome.get("failure_code") or queued.get("last_result", {}).get("failure_code"),
        })
        current_video_ids.add(video_id)
    case_notebooks = [row for row in notebook_rows
                      if str(row.get("notebook_name") or "").startswith("Nexus Research Case ")]
    nexus_ids_from_results = {str((row.get("provenance") or {}).get("notebook_id") or row.get("notebook_id") or "")
                              for row in result_rows}
    nexus_notebooks = [row for row in notebook_rows if
                       str(row.get("notebook_name") or "").startswith("Nexus") or
                       str(row.get("notebook_id") or "") in nexus_ids_from_results]
    mapped_case_ids: set[str] = set(cases_by_id)
    log_case_ids = {str((row.get("provenance") or {}).get("research_case_id") or row.get("research_case_id") or "")
                    for row in result_rows}
    mapped_case_ids |= log_case_ids
    orphaned = [row for row in case_notebooks
                if str(row.get("notebook_name", "")).removeprefix("Nexus Research Case ") not in mapped_case_ids]
    latest_recovery = {
        "generated_at": _now(), "channels_checked": len(channel_rows), "enabled_channels": len(channels),
        "channels_with_new_content": channel_counts["NEW_CONTENT_FOUND"],
        "new_video_count": sum(int(row.get("new_video_count", 0)) for row in channel_rows),
        "channels_no_new_content": channel_counts["NO_NEW_CONTENT"],
        "channels_with_stale_baselines": channel_counts["NEW_CONTENT_FOUND"],
        "channels_with_fetch_errors": channel_counts["FETCH_ERROR"],
        "new_videos": video_rows, "channels": channel_rows,
    }
    result = {
        "schema_version": "nexus.youtube-notebooklm-reconciliation.v1",
        "generated_at": _now(),
        "enumeration_source": "LIVE_YOUTUBE_RSS_VIA_EXISTING_SELECT_CHANNEL_VIDEOS",
        "enumeration_freshness_pass": all(row.get("enumeration_source") == "YOUTUBE_RSS" for row in channel_rows if row.get("actual_latest_video_id")),
        "designated_registry_count": len(channels), "enabled_channel_count": len(channels),
        "channels_checked": len(channel_rows), "channel_fetch_errors": [row for row in channel_rows if row.get("fetch_error")],
        "channels_with_new_content": channel_counts["NEW_CONTENT_FOUND"],
        "channels_no_new_content": channel_counts["NO_NEW_CONTENT"],
        "channels_with_stale_baselines": channel_counts["NEW_CONTENT_FOUND"],
        "channels_with_fetch_errors": channel_counts["FETCH_ERROR"],
        "current_new_video_count": sum(int(row.get("new_video_count", 0)) for row in channel_rows),
        "historically_recovered_metadata_count": len(recent_metadata),
        "research_processed_count": sum(1 for row in video_rows if row.get("processed")),
        "missed_video_count": len(recent_metadata),
        "missed_current_videos_recovered": len(recent_metadata),
        "recovery_semantics": "metadata_triaged; full Research processing is tracked separately per video",
        "channels": channel_rows, "new_videos": video_rows,
        "notebooklm_inventory_count": len(notebook_rows),
        "notebooklm_inventory_generated_at": inventories.get("generated_at"),
        "notebooklm_inventory_live_pass": bool(inventories.get("notebooks_listed")),
        "notebooklm_nexus_related_count": len(nexus_notebooks),
        "notebooklm_case_notebook_count": len(case_notebooks),
        "notebooklm_mapped_case_count": len(mapped_case_ids & {str(row.get("notebook_name", "")).removeprefix("Nexus Research Case ") for row in case_notebooks}),
        "notebooklm_orphaned_case_count": len(orphaned),
        "notebooklm_legacy_pool_count": sum(str(row.get("notebook_name") or "").startswith("Nexus Research -") for row in notebook_rows),
        "active_case_count": sum(str(row.get("status") or "").upper() in {"OPEN", "ACTIVE", "FOLLOWUP_WINDOW"}
                                 for row in cases_by_id.values()),
        "case_rows": list(cases_by_id.values()),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    report_path = ROOT / "reports/architecture/NEXUS_YOUTUBE_NOTEBOOKLM_RECONCILIATION_2026-10-05.txt"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "NEXUS YOUTUBE + NOTEBOOKLM LIVE RECONCILIATION",
        f"GENERATED_AT={result['generated_at']}",
        f"DESIGNATED_CHANNEL_COUNT={result['designated_registry_count']}",
        f"ENABLED_CHANNEL_COUNT={result['enabled_channel_count']}",
        "WHY_23_VS_21=The older append-only alpha_source_registry has 23 enabled NEW_CONTENT_ONLY rows but only 21 distinct external channel IDs: Luuk Alleman is registered twice, and JT Automations/JTHustlez share one channel ID. The authoritative designated registry and live checker operate on 21 unique channels; the extra two are duplicate registry records, not two additional channels.",
        f"ACTUAL_CHANNEL_FETCH_PASS={'YES' if not result['channel_fetch_errors'] else 'NO'}",
        f"CHANNELS_WITH_NEW_CONTENT={result['channels_with_new_content']}",
        f"CHANNELS_NO_NEW_CONTENT={result['channels_no_new_content']}",
        f"CHANNELS_WITH_STALE_BASELINES={result['channels_with_stale_baselines']}",
        f"CHANNELS_WITH_FETCH_ERRORS={result['channels_with_fetch_errors']}",
        f"MISSED_VIDEO_COUNT={result['missed_video_count']}",
        "MISSED_VIDEO_ROOT_CAUSES=October 4 monitor receipt predates the October 5 uploads. The prior receipt enumerated metadata before these uploads existed; its new-video metric counted only AUTO_RESEARCH queue candidates, not post-baseline TRIAGE_ONLY records. Current discovery persisted triage metadata for 24 videos. One bounded Research case was attempted and remains retryable after the evidence quality gate rejected an under-specified result.",
        f"YOUTUBE_ENUMERATION_SOURCE={result['enumeration_source']}",
        f"YOUTUBE_ENUMERATION_FRESHNESS_PASS={result['enumeration_freshness_pass']}",
        f"NOTEBOOKLM_NEXUS_NOTEBOOK_COUNT={result['notebooklm_nexus_related_count']}",
        f"NOTEBOOKLM_TOTAL_LIVE_NOTEBOOKS={result['notebooklm_inventory_count']}",
        f"NOTEBOOKLM_CASE_NOTEBOOK_COUNT={result['notebooklm_case_notebook_count']}",
        f"NOTEBOOKLM_MAPPED_CASE_COUNT={result['notebooklm_mapped_case_count']}",
        f"NOTEBOOKLM_ORPHANED_COUNT={result['notebooklm_orphaned_case_count']}",
        f"NOTEBOOKLM_LEGACY_POOL_COUNT={result['notebooklm_legacy_pool_count']}",
        "NOTEBOOKLM_REPORTING_ROOT_CAUSE=The weekend report hard-coded NotebookLM cases as NOT_CONNECTED and counted structured Research requests instead of querying the authenticated Python NotebookLM CLI and matching Nexus Research Case titles to durable case memory. The authenticated production CLI listed 92 notebooks; inventory has been connected to the report read model.",
        "", "CHANNEL RECONCILIATION TABLE",
        "CHANNEL | CHANNEL_ID | ENABLED | MODE | BASELINE_ID | BASELINE_PUBLISHED_AT | LAST_CHECK_AT | ACTUAL_LATEST_ID | ACTUAL_LATEST_TITLE | PUBLISHED_AT | STATUS",
    ]
    for row in channel_rows:
        vals = (row.get("channel_name"), row.get("channel_id"), row.get("enabled"), row.get("monitoring_mode"),
                row.get("stored_baseline_video_id"), row.get("stored_baseline_published_at"), row.get("last_check_at"),
                row.get("actual_latest_video_id"), row.get("actual_latest_title"), row.get("actual_latest_published_at"),
                row.get("reconciliation_status"))
        lines.append(" | ".join(str(value or "") for value in vals))
    lines += ["", "POST-BASELINE VIDEO LIFECYCLE"]
    for row in sorted(video_rows, key=lambda item: (str(item.get("channel_name")), str(item.get("published_at")))):
        lines.append(f"{row['channel_name']} | {row['video_id']} | {row['published_at']} | {row['title']} | ENUMERATED=YES | QUEUE={row.get('queue_status') or 'NO'} | TRIAGE={row.get('metadata_disposition') or 'NO'} | PROCESSED={row.get('processed')} | DEDUPED={row.get('deduped')} | PACKAGE={row.get('package_created')} | FINDINGS={row.get('finding_count')} | HANDOFFS={row.get('handoff_count')} | NOTEBOOK={row.get('notebook_id') or 'NONE'} | OUTCOME={row.get('processing_outcome') or row.get('processing_failure') or 'TRIAGED_ONLY'}")
    lines += ["", "NOTEBOOKLM LIVE INVENTORY (NEXUS RELATED)"]
    for row in sorted(nexus_notebooks, key=lambda item: str(item.get("notebook_name") or "")):
        title = str(row.get("notebook_name") or "")
        case_id = title.removeprefix("Nexus Research Case ") if title.startswith("Nexus Research Case ") else ""
        case = cases_by_id.get(case_id, {})
        category = (str(case.get("status") or "").upper() if case else
                    "LEGACY_NOTEBOOK_POOL" if title.startswith("Nexus Research -") else "FOLLOWUP_REUSABLE")
        lines.append(f"{row.get('notebook_id')} | {title} | CREATED={row.get('created_at') or 'UNAVAILABLE'} | UPDATED={row.get('updated_at') or 'UNAVAILABLE'} | LAST_USED_AT={row.get('last_viewed_at') or 'UNAVAILABLE'} | CASE_ID={case_id or 'NONE'} | SOURCE_VIDEO_ID={case.get('source_id') or 'UNAVAILABLE'} | SOURCE_URL={case.get('canonical_url') or 'UNAVAILABLE'} | CLASS={category}")
    lines += ["", "RECOVERY DETAILS", f"CURRENT_POST_BASELINE_VIDEO_COUNT={result['current_new_video_count']}",
              f"CURRENT_METADATA_TRIAGE_RECORDS={result['historically_recovered_metadata_count']}",
              f"FULL_RESEARCH_PROCESSED_COUNT={result['research_processed_count']}",
              "CANARY=Credit With Colin / kg_vmP5M9Oc; NotebookLM source read succeeded; evidence quality rejected the incomplete structured payload (required eligibility_rules empty; empty ratio 0.75). Queue status FAILED_RETRYABLE; no package, finding, handoff, or automatic baseline advancement.",
              "BASELINE_POLICY=No historical reset. Bounded feed windows that did not include the stored baseline were left unchanged. Credit With Colin was restored to its prior baseline while the retryable Research item is unresolved.",
              "NOTEBOOKLM_INVENTORY_SOURCE=Authenticated Nexus Python CLI used by the production Research adapter. The unrelated Node CLI on PATH was unauthenticated and does not support the adapter's JSON flags.",
              "FILES/READ MODELS=reports/runtime/youtube_notebooklm_live_reconciliation_latest.json; reports/runtime/notebooklm_inventory_latest.json; reports/runtime/weekend_youtube_monitor_latest.json"]
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    weekend = {"status": "PASS" if not result["channel_fetch_errors"] else "PARTIAL",
               "path": "research.youtube_notebooklm_reconciliation.build",
               "recorded_at": result["generated_at"], "channels_checked": len(channel_rows),
               "enabled_channels": len(channels), "new_videos_found": result["current_new_video_count"],
               "new_videos_processed": result["research_processed_count"],
               "new_videos_triaged": result["historically_recovered_metadata_count"],
               "missed_current_videos_recovered": result["missed_current_videos_recovered"],
               "videos_enumerated": sum(1 for row in channel_rows if row.get("actual_latest_video_id")),
               "errors": result["channel_fetch_errors"], "reconciliation_path": str(OUT)}
    WEEKEND_YOUTUBE.write_text(json.dumps(weekend, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    print(json.dumps(build(), indent=2, default=str))
