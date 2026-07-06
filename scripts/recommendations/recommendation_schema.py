#!/usr/bin/env python3
"""
Shared Recommendation Schema — Unified structure for Hermes, Alpha, and Nexus recommendations.

Single source of truth for:
- Recommendation structure (JSON)
- Scoring dimensions (7 dimensions)
- Source attribution (hermes, alpha, nexus)
- Follow-up tracking (status, history, next action)
- Persistence (data/recommendations/)
"""

import os
from datetime import datetime, timezone

RECOMMENDATIONS_DIR = "data/recommendations"
RECOMMENDATIONS_FILE = os.path.join(RECOMMENDATIONS_DIR, "recommendations_latest.json")
RECOMMENDATIONS_HISTORY_DIR = os.path.join(RECOMMENDATIONS_DIR, "history")

SCORING_DIMENSIONS = {
    "speed_to_value": {"min": 0, "max": 10, "description": "How fast can this produce measurable results?"},
    "cost_to_execute": {"min": 0, "max": 10, "description": "How affordable is the initial attempt? (10=free)"},
    "fit_goclear":     {"min": 0, "max": 10, "description": "How well does this serve the GoClear credit readiness business?"},
    "fit_nexus":       {"min": 0, "max": 10, "description": "How well does this serve the Nexus platform vision?"},
    "ease_of_execution": {"min": 0, "max": 10, "description": "How straightforward is implementation? (10=no-code/one-click)"},
    "proof_quality":   {"min": 0, "max": 10, "description": "How strong is the evidence or source?"},
    "risk_adjustment": {"min": -3, "max": 3, "description": "Risk penalty or bonus (-3=high risk, +3=very safe)"},
}

VALID_STATUSES = ["new", "acknowledged", "in_progress", "approved", "completed", "rejected", "superseded"]
VALID_SOURCES = ["hermes", "alpha", "nexus", "manual"]
VALID_PRIORITIES = ["low", "medium", "high", "critical"]


def new_recommendation(
    title,
    source,
    topic="",
    scores=None,
    summary="",
    why_it_matters="",
    next_action="",
    priority="medium",
    tags=None,
    context=None,
):
    """
    Create a new recommendation with unified schema.
    Returns a dict matching the canonical format.
    """
    now = datetime.now(timezone.utc)
    ts = now.strftime("%Y%m%dT%H%M%SZ")
    source_prefix = source[:3].upper()
    rec_id = f"rec_{source_prefix}_{ts}"

    if scores is None:
        scores = {}

    # Validate and normalize scores
    normalized_scores = {}
    for dim, spec in SCORING_DIMENSIONS.items():
        raw = scores.get(dim, 5)
        clamped = max(spec["min"], min(spec["max"], raw))
        normalized_scores[dim] = clamped

    # Calculate composite score
    composite = _calculate_composite(normalized_scores)

    # Auto-derive priority from composite
    if priority == "auto":
        priority = _priority_from_composite(composite)

    return {
        "id": rec_id,
        "title": title,
        "source": source,
        "topic": topic,
        "created_at": now.isoformat(),
        "status": "new",
        "priority": priority,
        "composite_score": composite,
        "scores": normalized_scores,
        "summary": summary,
        "why_it_matters": why_it_matters,
        "next_action": next_action,
        "tags": tags or [],
        "context": context or {},
        "follow_up": {
            "last_checked": now.isoformat(),
            "next_check": None,
            "attempts": 0,
            "history": [],
        },
    }


def _calculate_composite(scores):
    """Weighted composite: (speed + cost + fit_goclear + fit_nexus + ease + proof + risk) / 7"""
    weights = {
        "speed_to_value": 1.0,
        "cost_to_execute": 1.0,
        "fit_goclear": 1.5,
        "fit_nexus": 1.0,
        "ease_of_execution": 0.8,
        "proof_quality": 0.7,
        "risk_adjustment": 1.0,
    }
    total_weight = sum(weights.values())
    weighted_sum = sum(scores[k] * weights[k] for k in scores)
    return round(weighted_sum / total_weight, 1)


def _priority_from_composite(composite):
    """Map composite score to priority label."""
    if composite >= 7.5:
        return "high"
    elif composite >= 5.0:
        return "medium"
    else:
        return "low"


def score_dimensions_from_alpha(alpha_scores):
    """
    Convert Alpha's 5-dimension scores to the unified 7-dimension schema.
    Alpha dimensions: speed_to_value, cost, difficulty, risk, relevance
    """
    speed = alpha_scores.get("speed_to_value", 5)
    cost = alpha_scores.get("cost", 5)
    difficulty = alpha_scores.get("difficulty", 5)
    risk_raw = alpha_scores.get("risk", 3)
    relevance = alpha_scores.get("relevance", 7)

    # Map risk: Alpha 10=safe, 1=dangerous → unified: -3 to +3
    # Alpha risk=10 → +3, risk=1 → -3, risk=5 → 0
    risk_adj = round((risk_raw - 5.5) * (6 / 9), 1)  # rough linear map
    risk_adj = max(-3, min(3, risk_adj))

    return {
        "speed_to_value": speed,
        "cost_to_execute": cost,
        "fit_goclear": relevance,  # relevance ≈ fit
        "fit_nexus": 5,  # neutral if not specified
        "ease_of_execution": difficulty,
        "proof_quality": 5,  # neutral — no proof data in Alpha
        "risk_adjustment": risk_adj,
    }


def score_dimensions_from_hermes(hermes_scores):
    """
    Convert Hermes's 7-dimension scores to the unified schema.
    Hermes dimensions: speed_to_money, cost_to_try, fit_for_goclear,
                      fit_for_nexus, ease_of_execution, proof_source_quality, risk_adjustment
    """
    return {
        "speed_to_value": hermes_scores.get("speed_to_money", 5),
        "cost_to_execute": hermes_scores.get("cost_to_try", 5),
        "fit_goclear": hermes_scores.get("fit_for_goclear", 5),
        "fit_nexus": hermes_scores.get("fit_for_nexus", 5),
        "ease_of_execution": hermes_scores.get("ease_of_execution", 5),
        "proof_quality": hermes_scores.get("proof_source_quality", 5),
        "risk_adjustment": hermes_scores.get("risk_adjustment", 0),
    }


def save_recommendations(recs, path=None):
    """Save recommendations list to disk (atomic write)."""
    import json
    path = path or RECOMMENDATIONS_FILE
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(recs, f, indent=2)
    os.replace(tmp, path)
    return path


def load_recommendations(path=None):
    """Load recommendations from disk."""
    import json
    path = path or RECOMMENDATIONS_FILE
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return json.load(f)


def append_recommendation(rec):
    """Add a recommendation, dedup by title+source (skip if identical title+source exists within 24h)."""
    recs = load_recommendations()
    from datetime import timedelta
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    for existing in recs:
        if existing["title"] == rec["title"] and existing["source"] == rec["source"]:
            existing_created = datetime.fromisoformat(existing["created_at"])
            if existing_created.tzinfo is None:
                from datetime import timezone as tz
                existing_created = existing_created.replace(tzinfo=tz.utc)
            if existing_created > cutoff:
                return existing  # dedup
    recs.append(rec)
    save_recommendations(recs)
    _archive_snapshot(recs)
    return rec


def update_recommendation(rec_id, updates):
    """Update a recommendation by ID. Returns updated rec or None."""
    recs = load_recommendations()
    for i, rec in enumerate(recs):
        if rec["id"] == rec_id:
            recs[i].update(updates)
            # Recalculate composite if scores changed
            if "scores" in updates:
                recs[i]["composite_score"] = _calculate_composite(recs[i]["scores"])
            save_recommendations(recs)
            return recs[i]
    return None


def get_recommendations(status=None, source=None, min_score=None, sort_by="composite_score"):
    """Filter and sort recommendations."""
    recs = load_recommendations()
    if status:
        recs = [r for r in recs if r["status"] == status]
    if source:
        recs = [r for r in recs if r["source"] == source]
    if min_score is not None:
        recs = [r for r in recs if r["composite_score"] >= min_score]
    recs.sort(key=lambda r: r.get(sort_by, 0), reverse=True)
    return recs


def get_top_recommendations(n=5, status=None):
    """Get top N recommendations by composite score."""
    return get_recommendations(status=status or "new")[:n]


def add_follow_up_event(rec_id, event_type, note=""):
    """Record a follow-up event on a recommendation."""
    recs = load_recommendations()
    for rec in recs:
        if rec["id"] == rec_id:
            now = datetime.now(timezone.utc)
            event = {
                "type": event_type,
                "timestamp": now.isoformat(),
                "note": note,
            }
            rec["follow_up"]["history"].append(event)
            rec["follow_up"]["last_checked"] = now.isoformat()
            rec["follow_up"]["attempts"] = rec["follow_up"].get("attempts", 0) + 1
            save_recommendations(recs)
            return rec
    return None


def _archive_snapshot(recs):
    """Write a timestamped snapshot for historical tracking."""
    os.makedirs(RECOMMENDATIONS_HISTORY_DIR, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = os.path.join(RECOMMENDATIONS_HISTORY_DIR, f"snapshot_{ts}.json")
    import json
    with open(path, "w") as f:
        json.dump(recs, f, indent=2)
    # Prune to last 100 snapshots
    snaps = sorted(os.listdir(RECOMMENDATIONS_HISTORY_DIR))
    while len(snaps) > 100:
        os.remove(os.path.join(RECOMMENDATIONS_HISTORY_DIR, snaps.pop(0)))
