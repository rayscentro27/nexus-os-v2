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


def build_company_context() -> Dict[str, Any]:
    brief_path = ROOT / "reports/hermes_modernization/daily_brief.json"
    program_path = ROOT / "data/runtime/nexus_rebuild_program.json"
    review_path = ROOT / "reports/runtime/ray_review_queue_latest.json"
    operator_path = ROOT / "reports/runtime/active_operator_latest.json"
    brief = _read(brief_path, {})
    program = _read(program_path, {})
    review = _read(review_path, {})
    operator = _read(operator_path, {})
    safety = program.get("safety") if isinstance(program.get("safety"), dict) else {}
    return {
        "context_type": "NOVA_COMPANY_CONTEXT_VIEW",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "freshness": "MIXED_REPORT_AND_RUNTIME",
        "current_status": {
            "program_state": program.get("state", "UNKNOWN"),
            "current_work_package": program.get("current_work_package", "UNKNOWN"),
            "active_operator": operator.get("status", operator.get("run_status", "UNKNOWN")),
            "active_operator_mode": operator.get("mode", program.get("wp6_active_operator_mode", "UNKNOWN")),
            "active_operator_paused": safety.get("active_operator_paused", "UNKNOWN"),
        },
        "overnight_activity": brief.get("loop_updates", {}),
        "what_changed": brief.get("opportunity_updates", []),
        "research": brief.get("research_updates", {}),
        "operations": brief.get("system_health", {}),
        "business": {
            "top_priority": brief.get("top_priority", {}),
            "revenue_status": brief.get("revenue_status", {}),
            "confidence": brief.get("confidence", "UNKNOWN"),
        },
        "ray_attention": brief.get("approvals_needed", {}),
        "active_work": program.get("active_work_packages", []),
        "completed_work": program.get("completed_work_packages", []),
        "failed_work": program.get("blocked_work_packages", []),
        "risks": brief.get("revenue_risks", []),
        "blockers": brief.get("blockers", []),
        "unknown": [brief.get("freshness", {}), "Current company context is a bounded view; revalidate consequential facts."],
        "recommended_priorities": brief.get("recommended_actions", []),
        "sources": [str(path.relative_to(ROOT)) for path in (brief_path, program_path, review_path, operator_path) if path.exists()],
        "authority": "CONTEXT_ONLY_TRUTHKERNEL_REVALIDATES",
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
    }, sort_keys=True, default=str)
