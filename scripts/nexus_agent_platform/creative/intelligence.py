"""Creative Intelligence layered on the existing Creative Lab and Studio.

This module is deterministic-first: it creates concept possibilities, measures
semantic repetition, stores compact creative memory, and learns only from
explicitly recorded feedback. It has no publishing or messaging authority.
"""
from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Sequence

from nexus_agent_platform.governed.persistence import append_record, emit_audit_event, read_records

CONCEPT_SCHEMA = "nexus.creative-concept.v1"
FEEDBACK_SCHEMA = "nexus.creative-feedback.v1"
PREFERENCE_SCHEMA = "nexus.creative-preference-profile.v1"
CAMPAIGN_SCHEMA = "nexus.creative-campaign.v1"
REFERENCE_TERRITORIES = {"Evidence Ledger", "Scout Brief", "Control Tower"}
DIMENSIONS = ("strategic_angle", "visual_metaphor", "narrative_structure", "emotional_direction", "hook_pattern", "visual_family", "layout_family", "cta_pattern", "audience_tension", "format")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def _tokens(value: Any) -> set[str]:
    return {x for x in "".join(ch.lower() if ch.isalnum() else " " for ch in str(value)).split() if len(x) > 2}


def _text_similarity(a: Any, b: Any) -> float:
    left, right = _tokens(a), _tokens(b)
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def creative_signature(concept: Dict[str, Any]) -> Dict[str, str]:
    return {key: str(concept.get(key, "")).strip().lower().replace(" ", "-") for key in DIMENSIONS}


def signature_fingerprint(signature: Dict[str, str]) -> str:
    return _hash(signature)


def _concepts(brief: Dict[str, Any]) -> List[Dict[str, Any]]:
    title = brief.get("title") or brief.get("opportunity", {}).get("title") or "funding readiness"
    offer = brief.get("target_offer") or brief.get("opportunity", {}).get("target_offer") or "goclear_readiness_review_97"
    audience = brief.get("audience") or brief.get("opportunity", {}).get("target_customer") or "small-business owners preparing for funding"
    common = {"brief_fit": 84, "brand_fit": 82, "evidence_score": 78, "execution_score": 78, "conversion_hypothesis": f"Connect {title} to {offer} without promising an outcome.", "audience": audience}
    specs = [
        ("Readiness Map", "diagnosis-before-action", "route-map", "diagnostic-sequence", "calm-confidence", "guided-path", "map-and-steps", "diagnostic-tool", "uncertainty-about-what-to-do-first", "utility"),
        ("The Prepared Case", "evidence-as-advantage", "case-file", "investigation-to-proof", "assured-curiosity", "editorial-evidence", "annotated-dossier", "evidence-first", "need-to-believe-preparation-is-worthwhile", "editorial"),
        ("Before the Gate", "warning-before-action", "open-gateway", "risk-to-path", "clear-eyed-confidence", "cinematic-metaphor", "minimal-center", "readiness-assessment", "fear-of-applying-too-early", "image-led"),
        ("Build the Signal", "progress-through-assembly", "signal-lights", "fragment-to-system", "energized-optimism", "modular-system", "stacked-progress", "build-your-checklist", "desire-for-visible-progress", "motion"),
        ("The Quiet Advantage", "contrarian-preparation", "quiet-room", "assumption-to-reframe", "premium-restraint", "minimal-premium", "negative-space-editorial", "see-the-gaps", "fatigue-with-loud-financial-promises", "premium"),
        ("Funding Field Notes", "practical-peer-learning", "field-notebook", "question-to-observation", "human-pragmatism", "documentary-notes", "column-and-margin", "review-your-readiness", "need-for-specific-grounded-guidance", "documentary"),
    ]
    hooks = ["Start with the path, not the application.", "A stronger case begins with what you can verify.", "Before you apply, know which gate you are approaching.", "Turn scattered preparation into a visible signal.", "The quiet advantage is knowing what still needs work.", "Useful preparation leaves field notes, not promises."]
    concepts = []
    for index, row in enumerate(specs):
        name, angle, metaphor, narrative, emotion, visual, layout, cta, tension, fmt = row
        concept = {**common, "schema_version": CONCEPT_SCHEMA, "concept_id": f"concept_{_hash((title, index))[:16]}", "creative_brief_id": brief.get("creative_brief_id") or brief.get("brief_id"), "business_id": brief.get("business_id", "goclear"), "concept_name": name, "strategic_angle": angle, "central_idea": f"{title}: {name} uses {metaphor.replace('-', ' ')} to make preparation feel actionable.", "visual_metaphor": metaphor, "narrative_structure": narrative, "emotional_direction": emotion, "audience_tension": tension, "hook": hooks[index], "hook_pattern": ["start-with-path", "proof-before-claim", "before-you-act", "assemble-signal", "quiet-reframe", "field-observation"][index], "message": f"Preparation can be made clearer without guaranteeing funding or approval.", "proof_mechanism": "public evidence and readiness checklist", "cta_strategy": cta, "cta_pattern": cta, "visual_direction": visual, "layout_direction": layout, "layout_family": layout, "typography_direction": "clear hierarchy with accessible contrast", "imagery_direction": f"{metaphor.replace('-', ' ')}; exclude generic stock finance imagery", "motion_direction": "medium-specific pacing; no automatic hook-bullets-CTA reuse", "visual_family": visual, "format_fit": fmt, "format": fmt, "source_evidence_refs": list(brief.get("evidence_refs") or brief.get("opportunity", {}).get("evidence", []))[:8], "market_reference_refs": list(brief.get("market_refs") or brief.get("market_reference_refs", []))[:4], "whitespace_used": ["avoid generic financial stock imagery", "avoid guaranteed-outcome language"], "overused_patterns_avoided": ["floating credit cards", "generic upward arrow", "hero-plus-three-bullets"], "generation_source": "nexus.creative.intelligence.deterministic.v1", "status": "CANDIDATE", "created_at": utc_now()}
        concept["creative_signature"] = creative_signature(concept)
        concept["signature_fingerprint"] = signature_fingerprint(concept["creative_signature"])
        concept["novelty_score"] = 80 - index * 2
        concept["emotional_strength"] = 78 + (index % 3)
        concept["visual_potential"] = 84 - (index % 2) * 3
        concept["production_feasibility"] = 82
        concept["exploration"] = index >= 4
        concepts.append(concept)
    return concepts


def _history() -> List[Dict[str, Any]]:
    return read_records("creative_concepts")


def similarity(a: Dict[str, Any], b: Dict[str, Any]) -> float:
    sa, sb = creative_signature(a), creative_signature(b)
    weights = {key: 2.0 if key in {"visual_metaphor", "narrative_structure", "layout_family", "strategic_angle"} else 1.0 for key in DIMENSIONS}
    exact = sum(weights[key] for key in DIMENSIONS if sa[key] and sa[key] == sb[key])
    total = sum(weights.values())
    text = _text_similarity(a.get("central_idea"), b.get("central_idea"))
    return min(1.0, (exact / total) * 0.85 + text * 0.15)


def similarity_class(value: float) -> str:
    if value >= 0.85: return "NEAR_DUPLICATE"
    if value >= 0.65: return "HIGH"
    if value >= 0.4: return "MODERATE"
    return "LOW"


def score_concept(concept: Dict[str, Any], history: Sequence[Dict[str, Any]] = ()) -> Dict[str, Any]:
    recent = list(history)[:40]
    max_similarity = max((similarity(concept, old) for old in recent), default=0.0)
    recency_penalty = round(max_similarity * 28)
    score = max(0, min(100, round((concept.get("novelty_score", 0) + concept.get("brief_fit", 0) + concept.get("brand_fit", 0) + concept.get("evidence_score", 0) + concept.get("execution_score", 0)) / 5 - recency_penalty)))
    return {**concept, "historical_similarity_score": round(max_similarity, 3), "historical_similarity": similarity_class(max_similarity), "novelty_score": max(0, concept.get("novelty_score", 0) - recency_penalty), "overall_rank_score": score, "critic": {"originality": concept.get("novelty_score", 0), "brief_fit": concept.get("brief_fit", 0), "brand_fit": concept.get("brand_fit", 0), "evidence_safety": concept.get("evidence_score", 0), "emotional_strength": concept.get("emotional_strength", 0), "visual_potential": concept.get("visual_potential", 0), "conversion_hypothesis": concept.get("brief_fit", 0), "production_feasibility": concept.get("production_feasibility", 0)}}


def evaluate_concept_set(concepts: Sequence[Dict[str, Any]], history: Sequence[Dict[str, Any]] = ()) -> Dict[str, Any]:
    if not 5 <= len(concepts) <= 7:
        return {"status": "CREATIVE_DIVERSITY_INSUFFICIENT", "reason": "concept-count-out-of-bounds", "distinct_concepts": 0}
    scored = [score_concept(c, history) for c in concepts]
    pairs = [similarity(scored[i], scored[j]) for i in range(len(scored)) for j in range(i + 1, len(scored))]
    high = sum(value >= 0.65 for value in pairs)
    distinct = len({c["signature_fingerprint"] for c in scored})
    return {"status": "PASS" if distinct == len(scored) and high == 0 else "CREATIVE_DIVERSITY_INSUFFICIENT", "concept_count": len(scored), "distinct_concepts": distinct, "pairwise_max_similarity": round(max(pairs, default=0), 3), "pairwise_mean_similarity": round(sum(pairs) / len(pairs), 3) if pairs else 0, "high_similarity_pairs": high, "concepts": scored}


def generate_concept_round(brief: Dict[str, Any], *, generation_round: int = 1, history: Sequence[Dict[str, Any]] | None = None) -> Dict[str, Any]:
    history = list(history) if history is not None else _history()
    concepts = _concepts(brief)
    evaluation = evaluate_concept_set(concepts, history)
    if evaluation["status"] != "PASS":
        return {"status": "CREATIVE_DIVERSITY_INSUFFICIENT", "generation_round": generation_round, "concepts": evaluation.get("concepts", concepts), "evaluation": evaluation, "model_assisted_ideation": "NOT_AVAILABLE", "ai_calls": 0, "estimated_cost_usd": 0.0}
    return {"status": "PASS", "generation_round": generation_round, "round_id": f"round_{_hash((brief.get('creative_brief_id'), generation_round))[:16]}", "concepts": evaluation["concepts"], "evaluation": evaluation, "model_assisted_ideation": "NOT_AVAILABLE", "ai_calls": 0, "estimated_cost_usd": 0.0, "request_fingerprint": _hash({"brief": brief.get("creative_brief_id"), "history": [x.get("signature_fingerprint") for x in history[:40]], "round": generation_round})}


def persist_concept_round(round_result: Dict[str, Any]) -> Dict[str, Any]:
    if round_result.get("status") != "PASS":
        return {**round_result, "persistence": "NOT_PERSISTED"}
    existing = next((r for r in read_records("creative_concepts") if r.get("round_id") == round_result.get("round_id")), None)
    if existing:
        return {**existing, "persistence": "DUPLICATE_SUPPRESSED"}
    for concept in round_result["concepts"]:
        append_record("creative_concepts", {**concept, "round_id": round_result["round_id"], "generation_round": round_result["generation_round"]})
    emit_audit_event({"event": "creative_concept_round_created", "round_id": round_result["round_id"], "concept_count": len(round_result["concepts"]), "external_action_performed": False})
    return {**round_result, "persistence": "CREATED"}


def build_feedback(*, concept_id: str, decision: str, positive_tags: Sequence[str] = (), negative_tags: Sequence[str] = (), comments: str = "", synthetic_fixture: bool = False, asset_id: str | None = None) -> Dict[str, Any]:
    if decision not in {"APPROVE", "REVISION_MINOR", "REVISION_MAJOR", "REJECT", "PARK"}:
        raise ValueError("invalid-feedback-decision")
    return {"schema_version": FEEDBACK_SCHEMA, "feedback_id": f"feedback_{_hash((concept_id, decision, list(positive_tags), list(negative_tags), comments))[:16]}", "concept_id": concept_id, "asset_id": asset_id, "reviewer": "synthetic_fixture" if synthetic_fixture else "ray", "decision": decision, "ratings": {}, "comments": comments, "positive_tags": list(positive_tags), "negative_tags": list(negative_tags), "freeform_feedback": comments, "synthetic_fixture": synthetic_fixture, "created_at": utc_now()}


def persist_feedback(feedback: Dict[str, Any]) -> Dict[str, Any]:
    if feedback.get("schema_version") != FEEDBACK_SCHEMA or not feedback.get("concept_id"):
        raise ValueError("invalid-feedback")
    existing = next((r for r in read_records("creative_feedback") if r.get("feedback_id") == feedback.get("feedback_id")), None)
    if existing: return {**existing, "persistence": "DUPLICATE_SUPPRESSED"}
    append_record("creative_feedback", feedback)
    emit_audit_event({"event": "creative_feedback_recorded", "feedback_id": feedback["feedback_id"], "synthetic_fixture": bool(feedback.get("synthetic_fixture")), "external_action_performed": False})
    return {**feedback, "persistence": "CREATED"}


def build_preference_profile(feedback_rows: Sequence[Dict[str, Any]] | None = None) -> Dict[str, Any]:
    rows = list(feedback_rows) if feedback_rows is not None else read_records("creative_feedback")
    positive, negative = Counter(), Counter()
    for row in rows:
        positive.update(row.get("positive_tags", [])); negative.update(row.get("negative_tags", []))
    qualities = {tag: {"preference": "preferred", "confidence": round(min(0.99, 0.5 + count / 10), 2), "sample_count": count} for tag, count in positive.items()}
    qualities.update({tag: {"preference": "disliked", "confidence": round(min(0.99, 0.5 + count / 10), 2), "sample_count": count} for tag, count in negative.items()})
    return {"schema_version": PREFERENCE_SCHEMA, "profile_id": "goclear_ray_creative_preferences", "business_id": "goclear", "preferred_qualities": qualities, "source": "explicit_feedback_only", "feedback_count": len(rows), "synthetic_feedback_count": sum(bool(r.get("synthetic_fixture")) for r in rows), "last_updated": utc_now()}


def persist_preference_profile(profile: Dict[str, Any]) -> Dict[str, Any]:
    append_record("creative_preference_profiles", profile)
    return profile


def rank_with_preferences(concepts: Sequence[Dict[str, Any]], profile: Dict[str, Any]) -> List[Dict[str, Any]]:
    qualities = profile.get("preferred_qualities", {})
    ranked = []
    for concept in concepts:
        adjustment = 0
        if "LOVE_METAPHOR" in qualities and concept.get("visual_metaphor"): adjustment += 6
        if "LOVE_LAYOUT" in qualities and concept.get("layout_family"): adjustment += 4
        if "TOO_MUCH_TEXT" in qualities and concept.get("format") not in {"editorial", "utility"}: adjustment += 2
        ranked.append({**concept, "preference_fit": adjustment, "preference_adjusted_score": concept.get("overall_rank_score", concept.get("novelty_score", 0)) + adjustment, "exploration_preserved": bool(concept.get("exploration"))})
    return sorted(ranked, key=lambda c: c.get("preference_adjusted_score", 0), reverse=True)


def build_campaign_packet(concept: Dict[str, Any], brief: Dict[str, Any]) -> Dict[str, Any]:
    central = concept["central_idea"]
    return {"schema_version": CAMPAIGN_SCHEMA, "creative_campaign_id": f"campaign_{_hash((concept.get('concept_id'), brief.get('creative_brief_id')))[:16]}", "creative_brief_id": brief.get("creative_brief_id"), "selected_concept_id": concept.get("concept_id"), "central_idea": central, "audience": concept.get("audience"), "offer": brief.get("target_offer"), "message": concept.get("message"), "hook_family": concept.get("hook_pattern"), "visual_system": concept.get("visual_family"), "evidence_refs": concept.get("source_evidence_refs", []), "asset_plan": ["LANDING_PAGE_COPY", "REMOTION_VIDEO", "IMAGE_PROMPT"], "landing_page_direction": {"structure": concept.get("layout_family"), "execution": "adapt the central idea into an accessible page without default hero-plus-three-bullets repetition"}, "video_direction": {"story": concept.get("narrative_structure"), "rhythm": concept.get("motion_direction"), "execution": "medium-specific scene pacing; preserve central idea"}, "image_direction": {"metaphor": concept.get("visual_metaphor"), "composition": concept.get("visual_direction"), "prompt": concept.get("imagery_direction"), "negative_prompt": "generic stock finance imagery, floating credit cards, guaranteed outcomes"}, "measurement_metric": brief.get("measurement_metric") or "readiness_review_leads", "review_state": "NEEDS_RAY_REVIEW", "created_at": utc_now(), "external_action_performed": False}


def creative_intelligence_portfolio() -> Dict[str, Any]:
    concepts = read_records("creative_concepts")
    feedback = read_records("creative_feedback")
    profile = build_preference_profile(feedback)
    return {"status": "HEALTHY" if concepts else "IDLE", "concepts_generated": len(concepts), "distinct_concepts": len({r.get("signature_fingerprint") for r in concepts}), "historical_concepts_indexed": len(concepts), "feedback_count": len(feedback), "preference_profile_confidence": round(sum(v.get("confidence", 0) for v in profile.get("preferred_qualities", {}).values()) / max(1, len(profile.get("preferred_qualities", {}))), 2), "experimental_concepts": sum(bool(r.get("exploration")) for r in concepts), "model_assisted_ideation": "NOT_AVAILABLE", "gpu": "DEFERRED", "public_actions": "BLOCKED"}


def answer_creative_intelligence_question(question: str) -> Dict[str, Any]:
    q = question.lower(); concepts = read_records("creative_concepts"); portfolio = creative_intelligence_portfolio()
    if "different" in q or "directions" in q: return {"answer": f"{len(concepts)} canonical creative directions are available; concept signatures and similarity scores distinguish them.", "portfolio": portfolio}
    if "original" in q: return {"answer": "The most original direction is ranked by novelty after historical-similarity penalties.", "concept": max(concepts, key=lambda c: c.get("novelty_score", 0), default=None), "portfolio": portfolio}
    if "preference" in q: return {"answer": "Preference state is derived from explicit feedback only; performance data remains separate.", "profile": build_preference_profile(), "portfolio": portfolio}
    if "repeat" in q or "done this" in q: return {"answer": "Creative history compares semantic signatures, not only exact text.", "history_count": len(concepts), "portfolio": portfolio}
    return {"answer": "Creative Intelligence state is available from canonical concept history.", "portfolio": portfolio}
