"""Refresh the existing read-only Mission Control runtime snapshot."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from nexus_agent_platform.phase15.common import DATA_RUNTIME, MODERNIZATION_DIR, ROOT, atomic_write_json, load_json, utc_now

SNAPSHOT_PATH = ROOT / "public" / "runtime" / "hermes-current.json"
LOOP_IDS = ("open_source_scout_loop", "research_intake_loop", "revenue_opportunity_loop", "seo_opportunity_loop")


def refresh_mission_control_snapshot(*, scheduler_health_path: Path) -> Dict[str, Any]:
    health = load_json(scheduler_health_path, {})
    loop_state = load_json(DATA_RUNTIME / "nexus_loops" / "loop_state.json", {})
    brief = load_json(MODERNIZATION_DIR / "daily_brief.json", {})
    state = load_json(MODERNIZATION_DIR / "state.json", {})
    portfolio = load_json(ROOT / "reports" / "phase16a" / "executive_portfolio_latest.json", {})
    loop_rows = {}
    for loop_id in LOOP_IDS:
        record = ((loop_state.get("loops") or {}).get(loop_id) or {}).get("last_run") or {}
        loop_rows[loop_id] = {
            "last_result": record.get("delta_status", "UNKNOWN"),
            "last_run": record.get("completed_at", "UNKNOWN"),
            "next_run": record.get("next_run_at", "UNKNOWN"),
            "verifier": record.get("verifier_status", "UNKNOWN"),
            "provider_cost_usd": record.get("estimated_cost", 0.0),
            "retry_count": record.get("retry_count", "UNKNOWN"),
        }
    snapshot = {
        "generated_at": utc_now(),
        "source": "canonical Phase 16A runtime state",
        "runtime_status": state.get("nexus_running", "UNKNOWN"),
        "scheduler_health": {
            "status": health.get("status", "UNKNOWN"),
            "scheduler_label": health.get("scheduler_label", "UNKNOWN"),
            "scheduler_instance": health.get("scheduler_instance", "UNKNOWN"),
            "last_dispatch": health.get("last_dispatch", "UNKNOWN"),
            "next_dispatch": health.get("next_dispatch", "UNKNOWN"),
            "last_heartbeat": health.get("last_heartbeat", "UNKNOWN"),
        },
        "loops": loop_rows,
        "morning_brief": {
            "brief_id": brief.get("brief_id", "UNKNOWN"),
            "generated_at": brief.get("generated_at", "UNKNOWN"),
            "status": brief.get("status", "UNKNOWN"),
            "delivery": brief.get("delivery", "NOT_CERTIFIED"),
        },
        "provider_cost_usd": (brief.get("cost_summary") or {}).get("provider_cost_usd", 0.0),
        "blockers": brief.get("blockers", [])[:8],
        "approvals": brief.get("approvals_needed", {}),
        "highest_value_next_action": brief.get("highest_value_next_action", "UNKNOWN"),
        "executive_portfolio": {
            "generated_at": portfolio.get("generated_at", "UNKNOWN"),
            "active_objectives": [item for item in portfolio.get("objectives", []) if item.get("status") in {"READY", "ACTIVE", "RECOVERING"}],
            "waiting_human": portfolio.get("plan", {}).get("waiting_human", []),
            "blocked": portfolio.get("plan", {}).get("blocked", []),
            "recovering": [item for item in portfolio.get("objectives", []) if item.get("status") == "RECOVERING"],
            "portfolio_balance": portfolio.get("plan", {}).get("portfolio_balance", "UNKNOWN"),
            "latest_cycle": portfolio.get("cycle_id", "UNKNOWN"),
            "freshness": "UNKNOWN" if not portfolio else "PERSISTED",
        },
        "git_commit": health.get("git_commit", "UNKNOWN"),
        "freshness": {
            "scheduler_health": health.get("updated_at", "UNKNOWN"),
            "loop_state": max((row.get("last_run", "") for row in loop_rows.values()), default="UNKNOWN"),
            "morning_brief": brief.get("generated_at", "UNKNOWN"),
        },
    }
    atomic_write_json(SNAPSHOT_PATH, snapshot)
    return snapshot
