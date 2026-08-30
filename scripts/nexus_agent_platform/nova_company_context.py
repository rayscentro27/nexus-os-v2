"""Small, read-only company context projection for Nova.

This is a view over canonical reports/runtime state, not a second state store.
It deliberately exposes source references and freshness so Nova can distinguish
briefing context from current TruthKernel evidence.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[2]


def _read(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return default


def _timestamp(value: Any, path: Path) -> str:
    if isinstance(value, dict):
        for key in ("generated_at", "completed_at", "updated_at", "retrieved_at"):
            if value.get(key):
                return str(value[key])
    try:
        return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()
    except OSError:
        return "UNKNOWN"


def _age_seconds(timestamp: str) -> Any:
    try:
        when = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        return max(0, int((datetime.now(timezone.utc) - when).total_seconds()))
    except (TypeError, ValueError):
        return None


def _governed_review_items() -> list[dict[str, Any]]:
    """Read the current governed approval store, never the legacy dashboard."""
    try:
        from nexus_agent_platform.governed.approvals import get_pending_approvals
        return get_pending_approvals(requested_for="ray", include_self=False)
    except Exception:
        return []


def build_company_context() -> Dict[str, Any]:
    brief_path = ROOT / "reports/hermes_modernization/daily_brief.json"
    program_path = ROOT / "data/runtime/nexus_rebuild_program.json"
    review_path = ROOT / "reports/runtime/ray_review_queue_latest.json"
    operator_path = ROOT / "reports/runtime/active_operator_latest.json"
    brief = _read(brief_path, {})
    program = _read(program_path, {})
    review = _read(review_path, {})
    operator = _read(operator_path, {})
    brief_timestamp = _timestamp(brief, brief_path)
    operator_timestamp = _timestamp(operator, operator_path)
    brief_age = _age_seconds(brief_timestamp)
    brief_is_current = brief_age is not None and brief_age <= 48 * 60 * 60
    review_items = _governed_review_items()
    safety = program.get("safety") if isinstance(program.get("safety"), dict) else {}
    return {
        "context_type": "NOVA_COMPANY_CONTEXT_VIEW",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "freshness": "MIXED_REPORT_AND_RUNTIME",
        "current_status": {
            "program_configuration_state": program.get("state", "UNKNOWN"),
            "current_work_package": program.get("current_work_package", "UNKNOWN"),
            "active_operator_runtime": operator.get("status", operator.get("run_status", "UNKNOWN")),
            "active_operator_mode": operator.get("mode", "UNKNOWN"),
            "active_operator_last_cycle": operator.get("completed_at", operator.get("started_at", "UNKNOWN")),
            "active_operator_policy_paused": safety.get("active_operator_paused", "UNKNOWN"),
            "source": "reports/runtime/active_operator_latest.json + canonical program policy",
            "source_freshness": operator_timestamp,
        },
        "overnight_activity": brief.get("loop_updates", {}) if brief_is_current else {"status": "UNKNOWN", "reason": "The available daily brief is stale."},
        "what_changed": brief.get("opportunity_updates", []) if brief_is_current else [],
        "research": brief.get("research_updates", {}) if brief_is_current else {"status": "UNKNOWN", "reason": "The available daily brief is stale; use current research artifacts."},
        "operations": brief.get("system_health", {}) if brief_is_current else {"status": "UNKNOWN", "reason": "The available daily brief is stale; use current runtime evidence."},
        "business": {
            "top_priority": brief.get("top_priority", {}) if brief_is_current else {},
            "revenue_status": brief.get("revenue_status", {}) if brief_is_current else {},
            "confidence": brief.get("confidence", "UNKNOWN") if brief_is_current else "UNKNOWN",
        },
        "ray_attention": {"pending_count": len(review_items), "items": review_items, "source": "governed.approvals"},
        "active_work": program.get("active_work_packages", []),
        "completed_work": program.get("completed_work_packages", []),
        "failed_work": program.get("blocked_work_packages", []),
        "risks": brief.get("revenue_risks", []) if brief_is_current else [],
        "blockers": brief.get("blockers", []) if brief_is_current else [{"reason": "Daily brief stale; current blockers not established."}],
        "unknown": [{"daily_brief_age_seconds": brief_age, "daily_brief_timestamp": brief_timestamp}, "Current company context is a bounded view; revalidate consequential facts."],
        "recommended_priorities": brief.get("recommended_actions", []) if brief_is_current else [],
        "sources": [str(path.relative_to(ROOT)) for path in (program_path, operator_path) if path.exists()] + ([str(brief_path.relative_to(ROOT))] if brief_is_current else []),
        "authority": "CONTEXT_ONLY_TRUTHKERNEL_REVALIDATES",
        "data_quality": {"daily_brief_current": brief_is_current, "daily_brief_timestamp": brief_timestamp, "review_source": "governed.approvals"},
    }


def context_for_prompt(context: Dict[str, Any]) -> str:
    """Return a compact, non-secret prompt projection."""
    status = context.get("current_status", {})
    business = context.get("business", {})
    return json.dumps({
        "current_status": status,
        "operations": context.get("operations", {}),
        "research": context.get("research", {}),
        "ray_attention": context.get("ray_attention", {}),
        "top_priority": business.get("top_priority", {}),
        "blockers": context.get("blockers", [])[:5],
        "unknown": context.get("unknown", []),
        "authority": context.get("authority"),
        "data_quality": context.get("data_quality", {}),
    }, sort_keys=True, default=str)
