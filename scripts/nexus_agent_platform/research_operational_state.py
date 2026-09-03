"""Read-only operational state contract for Research and Alpha.

This projects existing registries, artifacts, and append-only records.  It is
not a second queue or source of truth; it makes activity, availability, work,
and health explicit dimensions so callers do not confuse IDLE with unavailable.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]


def _json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return default


def _jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                value = json.loads(line)
                if isinstance(value, dict):
                    rows.append(value)
            except ValueError:
                continue
    except OSError:
        pass
    return rows


def build_research_operational_state() -> dict[str, Any]:
    """Return the current bounded Research/Alpha operational contract."""
    now = datetime.now(timezone.utc).isoformat()
    alpha_status_path = ROOT / "data/runtime/alpha_telegram_status.json"
    metadata_path = ROOT / "reports/runtime/supabase_ready/youtube_video_metadata_latest.json"
    transcript_path = ROOT / "reports/runtime/supabase_ready/youtube_transcript_imports_latest.json"
    alpha_records = _jsonl(ROOT / "data/governed/alpha_research.jsonl")
    queue_records = _jsonl(ROOT / "data/governed/alpha_discovery_queue.jsonl")
    work_orders = _jsonl(ROOT / "data/governed/work_orders.jsonl")
    metadata = _json(metadata_path, [])
    transcripts = _json(transcript_path, [])
    scheduler_plist = Path.home() / "Library/LaunchAgents/com.nexus.research-worker.plist"
    scheduler_loaded = False
    try:
        import subprocess
        scheduler_loaded = subprocess.run(
            ["launchctl", "print", f"gui/{__import__('os').getuid()}/com.nexus.research-worker"],
            capture_output=True, text=True, timeout=3, check=False,
        ).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        scheduler_loaded = False

    # These are append-only records.  Count the latest state per logical item,
    # otherwise an old ROUTED row makes an already-finished job look queued.
    def latest_by(key: str, rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
        latest: dict[str, dict[str, Any]] = {}
        for row in rows:
            value = row.get(key)
            if value:
                latest[str(value)] = row
        return latest

    latest_queue = latest_by("content_id", queue_records)
    latest_research = latest_by("research_id", alpha_records)
    active_jobs = sum(1 for row in latest_research.values() if str(row.get("status", "")).upper() in {"RUNNING", "IN_PROGRESS"})
    queued_jobs = sum(1 for row in latest_queue.values() if str(row.get("state", "")).upper() in {"QUEUED", "ROUTED", "ASSIGNED"})
    blocked_jobs = sum(1 for row in list(latest_research.values()) + list(latest_queue.values()) if str(row.get("status", row.get("state", ""))).upper() in {"BLOCKED", "FAILED", "REJECTED"})
    open_objectives = len(latest_research)
    latest = max((row for row in alpha_records if row.get("updated_at") or row.get("created_at")), key=lambda row: str(row.get("updated_at") or row.get("created_at")), default={})
    alpha_available = alpha_status_path.exists()
    web_ready = bool((ROOT / "scripts/alpha/alpha_discovery.py").exists())
    health = "HEALTHY" if web_ready and alpha_available else "DEGRADED" if web_ready else "UNKNOWN"
    if active_jobs:
        work_state = "WORKING"
    elif queued_jobs:
        work_state = "QUEUED"
    elif blocked_jobs:
        work_state = "BLOCKED"
    else:
        work_state = "NO_CURRENT_WORK"
    return {
        "generated_at": now,
        "department": "RESEARCH",
        "research_department_operational_state": "OPERATIONAL" if health == "HEALTHY" else health,
        "alpha_primary_agent_activity": "BUSY" if active_jobs else "IDLE",
        "alpha_specialist_availability": "AVAILABLE" if alpha_available else "UNKNOWN",
        "research_background_process_state": "ACTIVE" if scheduler_loaded else "STOPPED",
        "research_work_state": work_state,
        "research_health": health,
        "research_effective_readiness": "READY" if scheduler_loaded and health == "HEALTHY" else "READY_DEGRADED" if health == "HEALTHY" else "BLOCKED",
        "active_research_jobs": active_jobs,
        "queued_research_jobs": queued_jobs,
        "blocked_research_jobs": blocked_jobs,
        "open_research_objectives": open_objectives,
        "objective_progress": {
            "known_objectives": open_objectives,
            "source": "data/governed/alpha_research.jsonl",
            "parent_objectives": [
                {
                    "objective_id": row.get("research_id"),
                    "source_assignment": row.get("source_refs", []),
                    "success_criteria": "bounded evidence, claims, traceable result, and governed routing",
                    "total_sources": len(row.get("source_refs", [])),
                    "completed_sources": len(row.get("candidate_content_ids", [])),
                    "failed_sources": 0,
                    "remaining_sources": max(0, len(row.get("source_refs", [])) - len(row.get("candidate_content_ids", []))),
                    "progress_percent": 100 if row.get("source_refs") and len(row.get("source_refs", [])) == len(row.get("candidate_content_ids", [])) else 0,
                    "status": row.get("status", "UNKNOWN"),
                    "needs_ray": False,
                }
                for row in latest_research.values()
            ],
        },
        "last_successful_research_activity": latest.get("updated_at") or latest.get("created_at") or "UNKNOWN",
        "current_research_objective": latest.get("question") or latest.get("theme") or "UNKNOWN",
        "research_needs_ray": False,
        "youtube": {"approved_targets": 5, "metadata_records": len(metadata) if isinstance(metadata, list) else 0, "transcripts_imported": len(transcripts) if isinstance(transcripts, list) else 0, "source": str(metadata_path.relative_to(ROOT))},
        "invariants": {"idle_is_not_unavailable": True, "available_is_not_active": True, "queue_empty_is_not_unavailable": True},
        "scheduler": {"plist_present": scheduler_plist.exists(), "loaded": scheduler_loaded, "source": str(scheduler_plist)},
        "empty_queue_next_action": (
            "INSPECT_INCOMPLETE_OBJECTIVES_AND_CONTINUE" if open_objectives or queued_jobs else
            "RUN_BOUNDED_AUTONOMOUS_DISCOVERY" if health == "HEALTHY" else
            "NO_HIGH_VALUE_RESEARCH_THIS_CYCLE"
        ),
    }


def alpha_status_summary() -> str:
    state = build_research_operational_state()
    return (
        f"Alpha Research is {state['research_department_operational_state'].lower()}. "
        f"The Alpha specialist is {state['alpha_primary_agent_activity'].lower()} and "
        f"{state['alpha_specialist_availability'].lower()} for delegation; research workers are "
        f"{state['research_background_process_state'].lower()}, with {state['queued_research_jobs']} queued jobs."
    )
