"""Recommendation contract.

A recommendation is NOT authority to execute. Nova may generate structured
recommendations grounded in evidence; they become executable only after Ray's
explicit approval routes through the action registry + policy gate.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from nexus_agent_platform.governed import persistence
from nexus_agent_platform.governed.action_registry import (
    action_exists,
    is_action_executable,
    list_available_actions,
)


def create_recommendation(
    *,
    title: str,
    problem: str,
    recommended_action_id: Optional[str],
    reason: str,
    evidence: List[Dict[str, Any]],
    expected_outcome: str,
    risk_level: str,
    dependencies: List[str],
    confidence: str,
    requires_approval: bool,
    source: str = "",
) -> Dict[str, Any]:
    """Create a persisted recommendation record."""
    executable = bool(recommended_action_id and action_exists(recommended_action_id))
    if recommended_action_id and not action_exists(recommended_action_id):
        # Recommendation-only: never fabricate executability.
        executable = False
    recommendation = {
        "id": persistence.new_id("rec"),
        "title": title,
        "problem": problem,
        "recommended_action_id": recommended_action_id,
        "reason": reason,
        "evidence": evidence,
        "expected_outcome": expected_outcome,
        "risk_level": risk_level,
        "dependencies": dependencies,
        "confidence": confidence,
        "requires_approval": requires_approval,
        "script_executable": executable,
        "executable_action": executable and bool(recommended_action_id and is_action_executable(recommended_action_id)),
        "source": source,
        "created_at": persistence._now(),
    }
    persistence.append_record("recommendations", recommendation)
    persistence.emit_audit_event({
        "type": "recommendation_created",
        "recommendation_id": recommendation["id"],
        "action_id": recommended_action_id,
        "executable": executable,
        "source": source,
    })
    return _mask_recommendation(recommendation)


def get_recommendation(recommendation_id: str) -> Optional[Dict[str, Any]]:
    return persistence.get_record("recommendations", recommendation_id)


def list_recommendations(limit: int = 20) -> List[Dict[str, Any]]:
    return [_mask_recommendation(r) for r in persistence.read_records("recommendations", limit=limit)]


def available_action_ids() -> List[str]:
    return [a for a in list_available_actions() if is_action_executable(a.get("action_id", ""))]


def _mask_recommendation(rec: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "recommendation_id": rec["id"],
        "title": rec.get("title"),
        "problem": rec.get("problem"),
        "recommended_action_id": rec.get("recommended_action_id"),
        "reason": rec.get("reason"),
        "evidence": rec.get("evidence"),
        "expected_outcome": rec.get("expected_outcome"),
        "risk_level": rec.get("risk_level"),
        "dependencies": rec.get("dependencies"),
        "confidence": rec.get("confidence"),
        "requires_approval": rec.get("requires_approval"),
        # Honest executability labels.
        "executable_action": rec.get("executable_action"),
        "recommendation_only": not rec.get("executable_action"),
        "created_at": rec.get("created_at"),
        "source": rec.get("source"),
    }