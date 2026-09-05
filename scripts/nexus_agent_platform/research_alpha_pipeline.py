"""Restart-safe autonomous Research-output -> Alpha evaluation bridge.

The bridge consumes only already-persisted, governed Research evidence.  Its
score is a deterministic conversion of the existing Alpha evidence score; it
does not claim profitability or invent support.  Qualification routes through
the existing Alpha work-order path, while rejected/weak items remain durable
with the reason and no downstream work is created.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from nexus_agent_platform.governed import persistence


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _latest(rows: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        value = row.get(key)
        if value and str(value) not in result:
            result[str(value)] = row
    return result


def _score(claim: dict[str, Any]) -> tuple[int, str, str, str]:
    raw = claim.get("evidence_score")
    try:
        score = max(0, min(100, round(float(raw) * 100)))
    except (TypeError, ValueError):
        score = 0
    verification = str(claim.get("verification_status") or claim.get("evidence_status") or "UNKNOWN").upper()
    if score >= 70 and verification in {"SUPPORTED", "PARTIALLY_SUPPORTED"}:
        return score, "QUALIFIED", "Evidence score meets the bounded qualification threshold and the claim has recorded support.", "MEDIUM"
    if score >= 40 or verification in {"PARTIALLY_SUPPORTED", "MIXED"}:
        return score, "FOLLOW_UP_RESEARCH", "The item has a research signal but lacks sufficient independent or verified evidence for qualification.", "LOW"
    return score, "REJECTED", "The persisted evidence is unverified or too weak for downstream qualification; retain it as research evidence and do not create department work.", "HIGH"


def evaluate_pending(*, max_items: int = 20) -> dict[str, Any]:
    """Evaluate persisted eligible content exactly once per artifact."""
    contents = persistence.read_records("alpha_content")
    claims = _latest(persistence.read_records("alpha_claims"), "content_id")
    research_rows = persistence.read_records("alpha_research")
    evaluations = persistence.read_records("alpha_evaluations")
    evaluated = {str(row.get("research_item_id")) for row in evaluations if row.get("research_item_id")}
    by_claim: dict[str, dict[str, Any]] = {}
    for row in research_rows:
        for claim_id in row.get("claims") or []:
            by_claim[str(claim_id)] = row
    created: list[dict[str, Any]] = []
    skipped = 0
    for content in contents:
        item_id = str(content.get("research_item_id") or content.get("content_id") or "")
        if not item_id or item_id in evaluated or len(created) >= max_items:
            continue
        claim = claims.get(str(content.get("content_id")))
        if not claim:
            continue
        research = by_claim.get(str(claim.get("claim_id"))) or {}
        score, decision, reasoning, confidence = _score(claim)
        evaluation = {
            "schema_version": "nexus.alpha-evaluation.v1",
            "evaluation_id": persistence.new_id("alpha_eval"),
            "research_item_id": item_id,
            "content_id": content.get("content_id"),
            "research_id": research.get("research_id"),
            "score": score,
            "decision": decision,
            "reasoning": reasoning,
            "confidence": confidence,
            "dimensions": {"evidence_score": score, "verification": str(claim.get("verification_status") or "UNKNOWN").upper()},
            "evaluated_at": _now(),
            "next_route": None,
            "status": decision,
            "no_external_action": True,
        }
        if decision == "QUALIFIED" and research.get("research_id"):
            from alpha.alpha_discovery import route_finding
            route = route_finding(str(research.get("theme") or "AI_NEXUS"), str(research["research_id"]), str(claim.get("claim") or content.get("title") or "Research output"))
            evaluation["next_route"] = route
            evaluation["status"] = "ROUTED"
        persistence.append_record("alpha_evaluations", evaluation)
        evaluated.add(item_id)
        created.append(evaluation)
    return {"evaluations_created": created, "evaluated_count": len(created), "skipped_already_evaluated": skipped, "read_only_external": True}
