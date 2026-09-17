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
from zoneinfo import ZoneInfo

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
    local_zone = ZoneInfo("America/Phoenix")
    local_today = datetime.now(local_zone).date().isoformat()
    alpha_status_path = ROOT / "data/runtime/alpha_telegram_status.json"
    metadata_path = ROOT / "reports/runtime/supabase_ready/youtube_video_metadata_latest.json"
    transcript_path = ROOT / "reports/runtime/supabase_ready/youtube_transcript_imports_latest.json"
    alpha_records = _jsonl(ROOT / "data/governed/alpha_research.jsonl")
    queue_records = _jsonl(ROOT / "data/governed/alpha_discovery_queue.jsonl")
    work_orders = _jsonl(ROOT / "data/governed/work_orders.jsonl")
    metadata = _json(metadata_path, [])
    transcripts = _json(transcript_path, [])
    v2_sources = _jsonl(ROOT / "data/governed/research_v2_sources.jsonl")
    v2_questions = _jsonl(ROOT / "data/governed/research_v2_questions.jsonl")
    v2_follow_ups = _jsonl(ROOT / "data/governed/research_v2_follow_ups.jsonl")
    v2_alpha_reviews = _jsonl(ROOT / "data/governed/research_v2_alpha_reviews.jsonl")
    v2_plans = _jsonl(ROOT / "data/governed/research_v2_plans.jsonl")
    v2_strategies = _jsonl(ROOT / "data/governed/research_v2_strategies.jsonl")
    v2_handoffs = _jsonl(ROOT / "data/governed/research_v2_handoffs.jsonl")
    v2_reputations = _jsonl(ROOT / "data/governed/research_v2_reputations.jsonl")
    v2_review_queue = _jsonl(ROOT / "data/governed/research_v2_review_queue.jsonl")
    scheduler_plist = Path.home() / "Library/LaunchAgents/com.nexus.continuous-loop.plist"
    scheduler_loaded = False
    try:
        import subprocess
        scheduler_loaded = subprocess.run(
            ["launchctl", "print", f"gui/{__import__('os').getuid()}/com.nexus.continuous-loop"],
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

    def local_date_for(row: dict[str, Any]) -> str | None:
        stamp = next((row.get(key) for key in ("recorded_at", "updated_at", "created_at", "completed_at") if row.get(key)), None)
        try:
            return datetime.fromisoformat(str(stamp).replace("Z", "+00:00")).astimezone(local_zone).date().isoformat()
        except (TypeError, ValueError):
            return None

    latest_queue = latest_by("content_id", queue_records)
    latest_research = latest_by("research_id", alpha_records)
    active_jobs = sum(1 for row in latest_research.values() if str(row.get("status", "")).upper() in {"RUNNING", "IN_PROGRESS"})
    queued_jobs = sum(1 for row in latest_queue.values() if str(row.get("state", "")).upper() in {"QUEUED", "ROUTED", "ASSIGNED"})
    blocked_jobs = sum(1 for row in list(latest_research.values()) + list(latest_queue.values()) if str(row.get("status", row.get("state", ""))).upper() in {"BLOCKED", "FAILED", "REJECTED"})
    open_objectives = len(latest_research)
    latest = max((row for row in alpha_records if row.get("updated_at") or row.get("created_at")), key=lambda row: str(row.get("updated_at") or row.get("created_at")), default={})
    today_records = []
    for row in alpha_records:
        stamp = row.get("updated_at") or row.get("created_at")
        try:
            if datetime.fromisoformat(str(stamp).replace("Z", "+00:00")).astimezone(local_zone).date().isoformat() == local_today:
                today_records.append(row)
        except (TypeError, ValueError):
            continue
    mission_rows = list(latest_research.values())
    mission_state = {
        "active": [row.get("research_id") for row in mission_rows if str(row.get("status", "")).upper() in {"RUNNING", "IN_PROGRESS", "QUEUED", "ROUTED", "ASSIGNED"}],
        "completed": [row.get("research_id") for row in mission_rows if str(row.get("status", "")).upper() in {"COMPLETED", "SUCCEEDED", "CHALLENGED"}],
        "blocked": [row.get("research_id") for row in mission_rows if str(row.get("status", "")).upper() in {"BLOCKED", "FAILED", "REJECTED"}],
        "other": [row.get("research_id") for row in mission_rows if str(row.get("status", "")).upper() not in {"RUNNING", "IN_PROGRESS", "QUEUED", "ROUTED", "ASSIGNED", "COMPLETED", "SUCCEEDED", "CHALLENGED", "BLOCKED", "FAILED", "REJECTED"}],
        "source": "data/governed/alpha_research.jsonl",
    }
    latest_reviews = latest_by("review_item_id", v2_review_queue)
    human_review_count = sum(1 for row in latest_reviews.values() if row.get("status") == "DRAFT_REVIEW_REQUIRED")
    if active_jobs:
        work_state = "WORKING"
    elif queued_jobs:
        work_state = "QUEUED"
    elif blocked_jobs:
        work_state = "BLOCKED"
    else:
        work_state = "NO_CURRENT_WORK"
    if work_state == "NO_CURRENT_WORK" and any(row.get("status") == "OPEN" for row in v2_questions):
        work_state = "WORKING_V2_INVESTIGATIONS"
    v2_today_sources = [row for row in v2_sources if local_date_for(row) == local_today]
    v2_today_reviews = [row for row in v2_alpha_reviews if local_date_for(row) == local_today]
    v2_today_questions = [row for row in v2_questions if local_date_for(row) == local_today]
    v2_findings: list[dict[str, Any]] = []
    for row in sorted(v2_today_reviews, key=lambda item: str(item.get("recorded_at", "")), reverse=True):
        for fact in (row.get("facts") or []):
            if fact:
                v2_findings.append({"finding": str(fact), "assessment": row.get("alpha_assessment", "UNKNOWN"), "recorded_at": row.get("recorded_at"), "source": "research_v2_alpha_reviews"})
    for row in sorted(v2_strategies, key=lambda item: str(item.get("recorded_at", "")), reverse=True):
        if row.get("title"):
            v2_findings.append({"finding": row.get("title"), "evidence": (row.get("known_evidence") or [])[:2], "status": row.get("status", "UNKNOWN"), "recorded_at": row.get("recorded_at"), "source": "research_v2_strategies"})
    v2_findings = v2_findings[:8]
    current_work = {
        "state": work_state,
        "legacy_active_jobs": active_jobs,
        "open_research_v2_investigations": sum(1 for row in v2_questions if row.get("status") == "OPEN"),
        "today_sources": [{"title": row.get("source_title"), "source_type": row.get("source_type"), "processing_status": row.get("processing_status"), "recorded_at": row.get("recorded_at")} for row in v2_today_sources[:8]],
        "today_questions": len(v2_today_questions),
        "next_action": "Continue bounded evidence selection for open Research V2 investigations." if v2_questions else "No open Research V2 investigations are recorded.",
        "source": "research_v2_sources.jsonl + research_v2_questions.jsonl + research_v2_alpha_reviews.jsonl",
    }
    machine_work_remains = bool(sum(1 for row in v2_questions if row.get("status") == "OPEN") or v2_follow_ups or v2_sources)
    alpha_available = alpha_status_path.exists()
    web_ready = bool((ROOT / "scripts/alpha/alpha_discovery.py").exists())
    health = "HEALTHY" if web_ready and alpha_available else "DEGRADED" if web_ready else "UNKNOWN"
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
        "research_v2_metrics": {
            "knowledge_items_acquired": sum(1 for row in v2_sources if row.get("source_type") != "EXISTING_IDEA"),
            "active_investigations": sum(1 for row in v2_questions if row.get("status") == "OPEN"),
            "follow_up_research_requests": len(v2_follow_ups),
            "follow_up_research_completed": sum(1 for row in v2_follow_ups if row.get("status") == "COMPLETED"),
            "opportunity_theses": sum(1 for row in v2_sources if row.get("source_type") == "EXISTING_IDEA"),
            "strategy_theses": len(v2_strategies),
            "alpha_reviews": len(v2_alpha_reviews),
            "plans_created": len(v2_plans),
            "handoff_drafts": len(v2_handoffs),
            "source_reputation_warnings": sum(1 for row in v2_reputations if row.get("source_trust_status") in {"CAUTION", "UNRELIABLE", "QUARANTINED"}),
            "scam_risk_items": sum(1 for row in v2_reputations if row.get("scam_risk_findings", 0)),
            "human_review_queue_count": human_review_count,
            "machine_work_remains": machine_work_remains,
            "global_stop_required": False,
            "process_alive": scheduler_loaded,
            "productive_research": bool(v2_sources or v2_alpha_reviews or v2_plans),
        },
        "last_successful_research_activity": latest.get("updated_at") or latest.get("created_at") or "UNKNOWN",
        "today_activity": {
            "local_date": local_today,
            "records_observed": len(today_records),
            "completed_or_updated_records": sum(1 for row in today_records if str(row.get("status", "")).upper() in {"COMPLETED", "CHALLENGED", "SCREENED", "SUCCEEDED"}),
            "source": "data/governed/alpha_research.jsonl",
            "research_v2_sources_observed": len(v2_today_sources),
            "research_v2_reviews_observed": len(v2_today_reviews),
            "research_v2_questions_observed": len(v2_today_questions),
            "research_v2_processed_sources": sum(1 for row in v2_today_sources if row.get("processing_status") == "FULLY_PROCESSED"),
        },
        "current_work": current_work,
        "recent_findings": v2_findings,
        "mission_state": {
            "active_count": len(mission_state["active"]),
            "completed_count": len(mission_state["completed"]),
            "blocked_count": len(mission_state["blocked"]),
            "other_count": len(mission_state["other"]),
            "active_ids": mission_state["active"][:8],
            "completed_ids": mission_state["completed"][:8],
            "blocked_ids": mission_state["blocked"][:8],
            "source": mission_state["source"],
        },
        "current_research_objective": latest.get("question") or latest.get("theme") or (v2_today_sources[0].get("source_title") if v2_today_sources else "Continue bounded Research V2 evidence selection"),
        "research_needs_ray": False,
        "human_review_queue_count": human_review_count,
        "global_machine_work_remains": machine_work_remains,
        "global_stop_required": False,
        "youtube": {"approved_targets": 5, "metadata_records": len(metadata) if isinstance(metadata, list) else 0, "transcripts_imported": len(transcripts) if isinstance(transcripts, list) else 0, "source": str(metadata_path.relative_to(ROOT))},
        "invariants": {"idle_is_not_unavailable": True, "available_is_not_active": True, "queue_empty_is_not_unavailable": True},
        "scheduler": {"owner": "com.nexus.continuous-loop", "plist_present": scheduler_plist.exists(), "loaded": scheduler_loaded, "source": str(scheduler_plist)},
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
