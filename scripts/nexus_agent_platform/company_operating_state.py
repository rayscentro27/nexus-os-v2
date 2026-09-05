"""Canonical, read-only executive operating-state projection.

This composes existing runtime owners; it is not a second queue, goal store,
or department scheduler.  Unknown and stale values remain explicit.
"""
from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]


def _read(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return default


def _age(value: Any) -> float | None:
    if not value:
        return None
    try:
        return max(0.0, (datetime.now(timezone.utc) - datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(timezone.utc)).total_seconds())
    except (TypeError, ValueError):
        return None


def _loaded_supervisor() -> bool:
    try:
        return subprocess.run(["launchctl", "print", f"gui/{__import__('os').getuid()}/com.nexus.continuous-loop"], capture_output=True, timeout=3, check=False).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def build_company_operating_state() -> dict[str, Any]:
    heartbeat = _read(ROOT / "data/runtime/research_heartbeat.json", {})
    kernel = _read(ROOT / "reports/runtime/continuous_operating_kernel_latest.json", {})
    operator = _read(ROOT / "reports/runtime/active_operator_latest.json", {})
    operator_hb = _read(ROOT / "reports/runtime/active_operator_heartbeat.json", {})
    portfolio = _read(ROOT / "data/runtime/company_goal_portfolio.json", [])
    runtime = _read(ROOT / "reports/hermes_modernization/live_runtime_status.json", {})
    alpha = _read(ROOT / "data/runtime/alpha_telegram_status.json", {})
    activity = _read(ROOT / "reports/runtime/alpha_research_activity_latest.json", {})
    source_activity_age = _age(activity.get("generated_at"))
    cycle_at = heartbeat.get("last_success") or kernel.get("completed_at")
    real_mode = str(heartbeat.get("execution_mode") or kernel.get("heartbeat", {}).get("execution_mode") or "").upper()
    # The canonical continuous runner invokes Active Operator with
    # dry_run=False and writes result_status=PASS.  Older heartbeats omitted
    # execution_mode; the fresh cycle/result pair is stronger evidence than
    # the legacy registry's historical DRY_RUN row.
    if not real_mode and heartbeat.get("heartbeat") == "ACTIVE" and heartbeat.get("result_status") == "PASS":
        real_mode = "REAL"
    if not real_mode:
        real_mode = "UNKNOWN"
    dry_run = real_mode == "DRY_RUN"
    goals = [g for g in portfolio if isinstance(g, dict)] if isinstance(portfolio, list) else []
    today = datetime.now(timezone.utc).date()
    advanced = []
    departments: dict[str, dict[str, Any]] = {}
    for goal in goals:
        department = str(goal.get("department") or "UNKNOWN")
        last = goal.get("last_progress")
        if last and str(last)[:10] == today.isoformat():
            advanced.append({"goal_id": goal.get("goal_id"), "department": department, "at": last, "work": (goal.get("active_workstreams") or [])[-1:]})
            departments[department] = {"state": "ACTIVE", "goal": goal.get("goal_id"), "last_progress": last, "source": "company_goal_portfolio"}
    safe_results = operator.get("safe_action_results") or []
    latest_result = safe_results[-1].get("result", {}) if safe_results and isinstance(safe_results[-1], dict) else {}
    latest_artifact = latest_result.get("artifact", {}) if isinstance(latest_result, dict) else {}
    current_work = []
    latest_goal = latest_result.get("parent_goal") or latest_artifact.get("goal_id")
    if latest_goal and str(latest_result.get("status", "")).upper() == "RUNNING":
        current_work.append({"goal_id": latest_goal, "department": latest_result.get("department") or latest_artifact.get("department", "UNKNOWN"), "action": latest_result.get("action", "research.refresh"), "status": latest_result.get("status"), "source": "active_operator_latest"})
    research_activity_state = "STALE" if source_activity_age is None or source_activity_age > 6 * 3600 else "AVAILABLE"
    if heartbeat.get("worker_state") in {"RUNNING", "PROCESSING", "BUSY"}:
        research_state = "ACTIVE"
    else:
        research_state = "IDLE_BETWEEN_CYCLES"
    departments.setdefault("Research", {"state": research_state, "last_cycle": cycle_at, "source": "research_heartbeat"})
    departments["Alpha"] = {"state": "AVAILABLE", "activity": research_activity_state, "last_verified": alpha.get("heartbeat"), "source": "alpha_telegram_status"}
    health_contract = runtime.get("contract", {}) if isinstance(runtime, dict) else {}
    stale_health = [name for name, row in health_contract.items() if isinstance(row, dict) and row.get("status") in {"STALE", "DEGRADED"}]
    blockers = []
    if stale_health:
        blockers.append({"summary": "Some legacy telemetry/read-model sources are stale.", "impact": "Executive visibility is degraded for those sources; the canonical supervisor and Research heartbeat remain separately readable.", "sources": stale_health})
    next_work = heartbeat.get("next_action") or operator_hb.get("next_scheduled_run") or "UNKNOWN"
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "system_health": {"state": "OPERATIONAL_WITH_TELEMETRY_DEGRADED" if stale_health else "OPERATIONAL", "supervisor": "RUNNING" if _loaded_supervisor() else "UNKNOWN", "stale_sources": stale_health, "source": "live_runtime_status+launchd"},
        "research": {"state": research_state, "execution_mode": real_mode, "dry_run": dry_run, "last_cycle": cycle_at, "next_wake": heartbeat.get("next_wake"), "queue_state": "NO_ASSIGNED_QUEUE_ITEM" if not current_work else "WORKING", "recent_activity_state": research_activity_state, "activity": {"sources_checked": activity.get("sources_checked"), "items_processed": activity.get("items_processed"), "new_items": activity.get("new_items_discovered"), "observed_at": activity.get("generated_at")}, "source": "research_heartbeat+continuous_kernel"},
        "alpha": departments["Alpha"],
        "current_work": current_work,
        "recent_completions": sorted(advanced, key=lambda x: str(x.get("at") or ""), reverse=True)[:6],
        "departments": departments,
        "queued_next": {"action": next_work, "next_wake": heartbeat.get("next_wake"), "source": "research_heartbeat"},
        "blockers": blockers,
        "ray_action": "UNKNOWN" if not operator else "NONE_EVIDENCED",
        "provenance": "COMPOSED_CURRENT_READ_MODEL",
    }
