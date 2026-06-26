"""Deterministic project-card enrichment for Nexus Source Intake.

No external AI. This normalizes available source, rating, transcript review, and task metadata into
the canonical payload consumed by NotebookLM-style department project cards.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _text(value: Any, fallback: str = "") -> str:
    if value is None:
        return fallback
    if isinstance(value, str):
        return value or fallback
    if isinstance(value, (int, float, bool)):
        return str(value)
    return fallback


def _list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [_text(v) for v in value if _text(v)]
    if isinstance(value, str) and value:
        return [value]
    return []


def _num(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _score_label(score: int | None) -> str:
    if score is None:
        return "unscored"
    if score >= 75:
        return "high"
    if score >= 50:
        return "medium"
    if score >= 30:
        return "low"
    return "very_low"


def _destination_for(category: str, existing: str = "") -> str:
    if existing:
        return existing
    return {
        "credit_funding_readiness": "GoClear/Apex Revenue Hub",
        "goclear_apex_revenue": "GoClear/Apex Revenue Hub",
        "ai_tooling": "Ops & Improvements",
        "system_improvement": "Ops & Improvements",
        "operations": "Ops & Improvements",
        "affiliate_partner": "Opportunity Lab",
        "client_experience": "Opportunity Lab",
        "seo_marketing": "SEO Growth Engine",
        "creative_media": "Creative Studio",
        "trading_research": "Trading Lab",
    }.get(category, "Source Intake & Review")


def _recommendation(category: str, destination: str, score: int | None, risks: list[str], approval_required: bool) -> str:
    if approval_required or risks:
        return "Ray should review the risk flags before routing or using this source."
    if score is not None and score < 30:
        return "Keep this as research-only or park it; the deterministic score is low."
    if category == "credit_funding_readiness":
        return "Review as GoClear/Apex funding readiness material with compliance-safe education framing."
    if category == "ai_tooling":
        return "Review as a Nexus internal improvement candidate before creating an implementation task."
    if destination == "Opportunity Lab":
        return "Send to Opportunity Lab for monetization review and smallest-test planning."
    if destination == "Ops & Improvements":
        return "Send to Ops & Improvements for system-improvement review."
    if destination == "Creative Studio":
        return "Send to Creative Studio as draft inspiration only."
    return "Keep the source available for Hermes review and choose the next safe internal action."


def build_project_enrichment(
    *,
    source: dict[str, Any] | None = None,
    transcript_review: dict[str, Any] | None = None,
    task_payload: dict[str, Any] | None = None,
    rating: dict[str, Any] | None = None,
    proof_event_id: str | None = None,
    enrichment_source: str = "deterministic",
) -> dict[str, Any]:
    source = source or {}
    task_payload = task_payload or {}
    transcript_review = transcript_review or {}
    source_meta = source.get("metadata") or {}
    review_meta = transcript_review.get("metadata") or {}
    rating = rating or source_meta or review_meta

    title = _text(transcript_review.get("title") or source.get("title") or task_payload.get("title") or source.get("url"), "Saved source")
    transcript_status = _text(source_meta.get("transcript_status") or task_payload.get("transcript_status"))
    category = _text(transcript_review.get("category") or source_meta.get("primary_category") or task_payload.get("category"), "uncategorized")
    destination = _destination_for(category, _text(source_meta.get("recommended_destination") or task_payload.get("destination")))
    raw_score = _num(source_meta.get("total_opportunity_score") or task_payload.get("score"))
    if raw_score is None and transcript_review.get("usefulness_score") is not None:
        raw_score = min(100, max(0, int(transcript_review.get("usefulness_score") or 0) * 10))
    score = int(raw_score) if raw_score is not None else None
    confidence_raw = _num(source.get("confidence") or (source_meta.get("scores") or {}).get("confidence") or task_payload.get("confidence"))
    confidence = int(confidence_raw) if confidence_raw is not None else None
    risks = _list(source_meta.get("risk_triggers") or source_meta.get("reasons_against") or transcript_review.get("claim_flags") or task_payload.get("risk_triggers"))
    approval_required = bool(source_meta.get("ray_decision_needed") or task_payload.get("approval_required") or risks)

    transcript_summary = _text(transcript_review.get("core_idea") or transcript_review.get("recommended_action"))
    source_summary = _text(source.get("snippet") or source.get("why_it_matters") or task_payload.get("snippet"))
    if transcript_summary:
        summary = transcript_summary
        status = "scored" if score is not None else "enriched"
    elif source_summary:
        summary = source_summary
        status = "pending_transcript" if transcript_status in ("enrichment_pending", "unavailable", "missing", "") else "enriched"
    else:
        summary = "Saved metadata is available. Transcript/NotebookLM enrichment is pending."
        status = "pending_transcript"

    if score is not None and score < 30:
        risks = list(dict.fromkeys([*risks, "low_score"]))

    pros = _list(review_meta.get("pros") or source_meta.get("pros"))
    cons = _list(review_meta.get("cons") or source_meta.get("cons"))
    if not pros:
        pros = [
            f"Category signal: {category}.",
            f"Recommended destination: {destination}.",
        ]
        if score is not None and score >= 50:
            pros.append(f"Deterministic score is {_score_label(score)} ({score}/100).")
    if not cons:
        cons = []
        if score is None:
            cons.append("No deterministic score is stored yet.")
        elif score < 30:
            cons.append(f"Low deterministic score ({score}/100); likely research-only or park.")
        if risks:
            cons.append(f"Risk flags: {', '.join(risks)}.")
        if status == "pending_transcript":
            cons.append("Transcript/NotebookLM enrichment is still pending.")

    recommendation = _text(
        transcript_review.get("recommended_action")
        or source_meta.get("recommendation")
        or source_meta.get("recommended_action"),
        _recommendation(category, destination, score, risks, approval_required),
    )
    proposed_schedule = _text(source_meta.get("proposed_schedule"), "Review now; run deterministic enrichment after capture; schedule automation only after approval.")
    next_action = _text(source_meta.get("next_action"), "Review with Hermes, then route safely or park.")
    if approval_required:
        next_action = "Send to Approvals or request Ray review before risky next action."
    elif destination == "Opportunity Lab":
        next_action = "Send to Opportunity Lab for smallest-test planning."
    elif destination == "Ops & Improvements":
        next_action = "Create an internal improvement task or request more research."

    memory = f"{title}: {category} -> {destination}; score={score if score is not None else 'unscored'}; next={next_action}"
    reviewed_at = now() if transcript_review else None
    enriched_at = now() if status in ("enriched", "scored", "needs_review") else None
    if approval_required:
        status = "needs_review"

    return {
        "enrichment_status": status,
        "summary": summary,
        "score": score,
        "score_label": _score_label(score),
        "category": category,
        "destination": destination,
        "pros": pros,
        "cons": cons,
        "recommendation": recommendation,
        "proposed_schedule": proposed_schedule,
        "next_action": next_action,
        "confidence": confidence,
        "risk_triggers": risks,
        "approval_required": approval_required,
        "hermes_memory_summary": memory[:600],
        "source_summary": source_summary or summary,
        "enrichment_source": enrichment_source,
        "enriched_at": enriched_at,
        "reviewed_at": reviewed_at,
        "proof_event_id": proof_event_id,
    }
