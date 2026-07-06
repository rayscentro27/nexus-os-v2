#!/usr/bin/env python3
"""
Shared Recommendation Engine — Connects Hermes, Alpha, and Nexus into a unified recommendation system.

Provides:
- ingest_hermes(): Accept Hermes research results
- ingest_alpha(): Accept Alpha research results
- ingest_nexus(): Accept Nexus system recommendations
- get_prioritized(): Cross-source ranked list
- next_steps(): Top actionable recommendations with context
- summary(): Status overview for /report
"""

import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from recommendation_schema import (
    new_recommendation,
    score_dimensions_from_alpha,
    score_dimensions_from_hermes,
    append_recommendation,
    get_recommendations,
    get_top_recommendations,
    add_follow_up_event,
    update_recommendation,
    load_recommendations,
    VALID_STATUSES,
)


def ingest_hermes(query, search_result, advisory_answer, topic=""):
    """
    Ingest Hermes research results into the shared layer.
    Returns the created recommendation.
    """
    scores_raw = {}
    # Extract scores from advisory findings
    findings = advisory_answer.get("findings", [])
    if findings:
        # Use average of top 3 finding scores as base
        top_scores = [f.get("score", 5) for f in findings[:3]]
        base = sum(top_scores) / len(top_scores) if top_scores else 5
        scores_raw = {
            "speed_to_value": base,
            "cost_to_execute": base,
            "fit_goclear": base,
            "fit_nexus": base,
            "ease_of_execution": base,
            "proof_quality": base,
            "risk_adjustment": 0,
        }
    # Check if there's a detailed score_breakdown in the advisory
    if "score_breakdown" in advisory_answer:
        scores_raw = advisory_answer["score_breakdown"]

    scores = score_dimensions_from_hermes(scores_raw)

    why = advisory_answer.get("why_it_matters", "Hermes research finding")
    summary = advisory_answer.get("answer", query[:200])[:300]
    next_action = advisory_answer.get("next_step", "Review findings and decide on action")

    rec = new_recommendation(
        title=f"Hermes: {query[:80]}",
        source="hermes",
        topic=topic or query,
        scores=scores,
        summary=summary,
        why_it_matters=why if isinstance(why, str) else str(why),
        next_action=next_action,
        priority="auto",
        tags=_derive_tags(query, "hermes"),
        context={"query": query, "search_status": search_result.get("status", "unknown")},
    )
    return append_recommendation(rec)


def ingest_alpha(topic, ideas, avg_score, category="", source_context=None):
    """
    Ingest Alpha research results into the shared layer.
    Alpha generates multiple ideas per topic; we create one rec per top idea.
    Returns list of created recommendations.
    """
    recs = []
    for idea in ideas[:3]:  # top 3 only
        alpha_scores = idea.get("score", {}).get("dimensions", {})
        scores = score_dimensions_from_alpha(alpha_scores)
        composite = idea.get("score", {}).get("total", avg_score)

        rec = new_recommendation(
            title=f"Alpha: {idea['title'][:80]}",
            source="alpha",
            topic=topic,
            scores=scores,
            summary=idea.get("why", ""),
            why_it_matters=f"Alpha research in {category or 'general'} category. Composite: {composite}/10",
            next_action=idea.get("action", "Review idea and create work order"),
            priority="auto",
            tags=_derive_tags(topic, "alpha") + [category],
            context={
                "category": category,
                "original_score": composite,
                "source_context": source_context or {},
            },
        )
        saved = append_recommendation(rec)
        recs.append(saved)
    return recs


def ingest_nexus(title, description="", priority="medium", tags=None, context=None):
    """
    Ingest a Nexus system recommendation (e.g., from scorecard, monitor, recovery).
    """
    scores = {
        "speed_to_value": 5,
        "cost_to_execute": 7,
        "fit_goclear": 5,
        "fit_nexus": 8,
        "ease_of_execution": 6,
        "proof_quality": 5,
        "risk_adjustment": 0,
    }
    rec = new_recommendation(
        title=f"Nexus: {title[:80]}",
        source="nexus",
        topic=title,
        scores=scores,
        summary=description[:300],
        why_it_matters="System-level recommendation for Nexus operations",
        next_action="Review and incorporate into daily operations",
        priority=priority,
        tags=(tags or []) + ["system"],
        context=context or {},
    )
    return append_recommendation(rec)


def get_prioritized(status=None, source=None, min_score=0, limit=10):
    """
    Get cross-source prioritized recommendations.
    Returns list sorted by composite_score descending.
    """
    recs = get_recommendations(status=status, source=source, min_score=min_score)
    return recs[:limit]


def next_steps(n=3):
    """
    Get the top N actionable next steps with full context.
    Returns a formatted string suitable for Telegram display.
    """
    recs = get_top_recommendations(n=n, status="new")
    if not recs:
        return "No pending recommendations. Run Alpha research or Hermes search to generate new ones."

    lines = [f"**Top {len(recs)} Recommendations**", ""]
    for i, rec in enumerate(recs, 1):
        lines.append(f"**{i}. {rec['title'][:60]}**")
        lines.append(f"   Score: {rec['composite_score']}/10 | Priority: {rec['priority']} | Source: {rec['source']}")
        if rec.get("summary"):
            lines.append(f"   {rec['summary'][:120]}")
        if rec.get("next_action"):
            lines.append(f"   Action: {rec['next_action'][:100]}")
        lines.append("")
    return "\n".join(lines)


def summary():
    """
    Get a summary overview of all recommendations.
    Returns dict suitable for /report integration.
    """
    all_recs = load_recommendations()
    by_status = {}
    for status in VALID_STATUSES:
        by_status[status] = [r for r in all_recs if r["status"] == status]

    by_source = {}
    for source in ["hermes", "alpha", "nexus"]:
        by_source[source] = [r for r in all_recs if r["source"] == source]

    top = get_top_recommendations(n=3)
    avg_composite = 0
    if all_recs:
        avg_composite = round(sum(r["composite_score"] for r in all_recs) / len(all_recs), 1)

    return {
        "total": len(all_recs),
        "by_status": {k: len(v) for k, v in by_status.items()},
        "by_source": {k: len(v) for k, v in by_source.items()},
        "avg_composite_score": avg_composite,
        "top": [
            {"title": r["title"][:60], "score": r["composite_score"], "source": r["source"]}
            for r in top
        ],
    }


def mark_status(rec_id, status):
    """Update recommendation status with follow-up event."""
    if status not in VALID_STATUSES:
        raise ValueError(f"Invalid status: {status}. Must be one of {VALID_STATUSES}")
    rec = update_recommendation(rec_id, {"status": status})
    if rec:
        add_follow_up_event(rec_id, "status_change", f"Status changed to {status}")
    return rec


def _derive_tags(query, source):
    """Auto-tag based on query content."""
    tags = []
    q = query.lower()
    keyword_tags = {
        "credit": "credit", "readiness": "credit", "funding": "funding",
        "grant": "grant", "stripe": "payments", "email": "email",
        "social": "social", "website": "web", "client": "clients",
        "affiliate": "affiliate", "partnership": "partnerships",
    }
    for kw, tag in keyword_tags.items():
        if kw in q and tag not in tags:
            tags.append(tag)
    return tags


def format_for_telegram(rec):
    """Format a single recommendation for Telegram display."""
    lines = []
    lines.append(f"**{rec['title'][:60]}**")
    lines.append(f"Score: {rec['composite_score']}/10 | {rec['priority'].upper()} | {rec['source']}")
    if rec.get("summary"):
        lines.append(rec["summary"][:200])
    lines.append(f"Action: {rec.get('next_action', 'Review')[:100]}")
    lines.append(f"Status: {rec['status']} | ID: {rec['id'][:20]}...")
    return "\n".join(lines)
