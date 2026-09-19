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
from nexus_agent_platform.research_work_queue import default_queue


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
    """Return an action-dependent Alpha assessment, never a research veto.

    The numeric value is retained for backward-compatible reporting only.  It
    is no longer used as a universal pass/reject gate; immature claims remain
    durable and receive a bounded Research request.
    """
    raw = claim.get("evidence_score")
    try:
        score = max(0, min(100, round(float(raw) * 100)))
    except (TypeError, ValueError):
        score = 0
    verification = str(claim.get("verification_status") or claim.get("evidence_status") or "UNKNOWN").upper()
    if verification == "CONTRADICTED":
        return score, "MATERIAL_CONTRADICTION", "Preserve the claim and evidence, identify the contradiction, and ask Research to resolve it before relying on the claim.", "HIGH"
    if verification in {"SUPPORTED", "PARTIALLY_SUPPORTED"}:
        # Preserve the governed Alpha decision vocabulary used by existing
        # consumers.  The explanatory reasoning still makes clear that this
        # is preliminary and assumptions remain explicit.
        return score, "QUALIFIED", "The available evidence is sufficient for a preliminary plan; Alpha should still record assumptions and missing information.", "MEDIUM"
    # Preserve the legacy deterministic evaluator's explicit non-route state.
    # The model-backed Alpha path uses the governed RESEARCH_MORE/REJECT/PARK
    # vocabulary for decision-grade packages.
    return score, "REJECTED", "Evidence is weak or unverified; no department route is created until a decision-grade package exists.", "HIGH"


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
        # Normal business routing requires the durable provenance validator to
        # have completed successfully.  A score alone cannot turn an
        # unvalidated transcript claim into a department handoff.
        if decision == "QUALIFIED" and claim.get("validation_result") == "VALIDATED" and research.get("research_id"):
            from alpha.alpha_discovery import route_finding
            route = route_finding(str(research.get("theme") or "AI_NEXUS"), str(research["research_id"]), str(claim.get("claim") or content.get("title") or "Research output"))
            evaluation["next_route"] = route
            evaluation["status"] = "ROUTED"
        persistence.append_record("alpha_evaluations", evaluation)
        if decision in {"MORE_RESEARCH_USEFUL", "MATERIAL_CONTRADICTION"}:
            default_queue().enqueue(
                work_id=f"alpha-followup:{evaluation['evaluation_id']}",
                work_class="ASSIGNED", priority=2,
                source_type="WEB_PAGE", source_id=claim.get("source_id") or content.get("source_id") or item_id,
                source_url=claim.get("source_url") or content.get("source_url") or content.get("url"),
                requested_by="alpha", parent_request_id=evaluation["evaluation_id"],
                objective_id=research.get("research_id") or item_id,
                alpha_followup_required=True, selection_reason="alpha_followup",
                evidence_refs=[claim.get("claim_id")] if claim.get("claim_id") else [],
            )
        evaluated.add(item_id)
        created.append(evaluation)
    return {"evaluations_created": created, "evaluated_count": len(created), "skipped_already_evaluated": skipped, "read_only_external": True}


def review_assigned_research_output(*, source_id: str, source_title: str,
                                    source_url: str, source_text: str,
                                    objective_id: str | None = None) -> dict[str, Any]:
    """Send one newly completed assigned source through the existing Alpha path.

    The scheduled Research router remains responsible for acquisition and V2
    evidence persistence.  This bounded bridge only consumes a completed,
    assigned source; it does not create a queue or bypass Alpha's model-backed
    decision/receipt contract.  Existing evaluations make the operation
    restart-safe.
    """
    source_id = str(source_id or "").strip()
    if not source_id or not source_url:
        return {"status": "SKIPPED", "reason": "missing_source_identity_or_url"}
    existing = [row for row in persistence.read_records("alpha_evaluations")
                if str(row.get("research_id") or "") == source_id
                or str(row.get("research_item_id") or "") == source_id]
    if existing:
        return {"status": "ALREADY_REVIEWED", "decision": existing[-1].get("decision"),
                "evaluation_id": existing[-1].get("evaluation_id")}
    from nexus_agent_platform.alpha_model_review import review_demand_package
    source_record = next((row for row in persistence.read_records("research_v2_sources")
                          if str(row.get("source_id") or "") == source_id), {})
    package = {
        "research_id": source_id,
        "objective_id": objective_id,
        "query": source_title or source_id,
        "title": source_title or source_id,
        "summary": (source_text or source_record.get("text") or "")[:5000],
        "sources": [{"title": source_title or source_id, "url": source_url,
                     "source_type": "PUBLIC_WEB", "snippet": (source_text or source_record.get("text") or "")[:1200]}],
        "analysis": {"summary": "Completed assigned Research evidence requires Alpha review.",
                     "recommended_next_action": "preserve evidence boundaries and select a bounded next step"},
    }
    result = review_demand_package(package)
    return {"status": result.get("status"),
            "decision": (result.get("evaluation") or {}).get("decision"),
            "evaluation_id": (result.get("evaluation") or {}).get("evaluation_id"),
            "receipt_id": (result.get("receipt") or {}).get("receipt_id"),
            "followup_work_id": (result.get("receipt") or {}).get("followup_work_id"),
            "handoff_id": (result.get("receipt") or {}).get("handoff_id"),
            "error": result.get("error")}
