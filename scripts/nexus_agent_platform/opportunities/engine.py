"""Deterministic-first Nexus Opportunity Engine.

This module canonicalizes opportunity-like records from existing Nexus sources,
scores them deterministically, and prepares compact evidence bundles for
Hermes/Nova synthesis. It does not create a separate storage system.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Sequence

from nexus_agent_platform.governed import persistence

GOVERNED_OPPORTUNITY_SCHEMA = "nexus.opportunity.v1"
SCORING_POLICY_VERSION = "nexus.opportunity-scoring.v1"
GOVERNED_OPPORTUNITY_STATUSES = (
    "CANDIDATE", "QUALIFIED", "NEEDS_RESEARCH", "NEEDS_RAY_REVIEW",
    "APPROVED_FOR_PLANNING", "PARKED", "REJECTED", "CONVERTED_TO_WORK_ORDER",
    "STALE", "CLOSED",
)
_GOVERNED_TRANSITIONS = {
    "CANDIDATE": {"QUALIFIED", "NEEDS_RESEARCH", "NEEDS_RAY_REVIEW", "PARKED", "REJECTED", "STALE"},
    "QUALIFIED": {"NEEDS_RAY_REVIEW", "APPROVED_FOR_PLANNING", "NEEDS_RESEARCH", "STALE", "PARKED", "REJECTED"},
    "NEEDS_RESEARCH": {"CANDIDATE", "QUALIFIED", "NEEDS_RAY_REVIEW", "PARKED", "REJECTED", "STALE"},
    "NEEDS_RAY_REVIEW": {"APPROVED_FOR_PLANNING", "PARKED", "REJECTED", "NEEDS_RESEARCH", "STALE"},
    "APPROVED_FOR_PLANNING": {"CONVERTED_TO_WORK_ORDER", "PARKED", "STALE", "CLOSED"},
    "PARKED": {"CANDIDATE", "NEEDS_RESEARCH", "NEEDS_RAY_REVIEW", "CLOSED"},
    "REJECTED": {"CANDIDATE", "CLOSED"},
    "CONVERTED_TO_WORK_ORDER": {"CLOSED"},
    "STALE": {"NEEDS_RESEARCH", "CANDIDATE", "CLOSED"},
    "CLOSED": set(),
}
_SCORING_WEIGHTS = {
    "evidence_strength": 0.18, "revenue_potential": 0.16, "speed_to_value": 0.12,
    "launch_cost": 0.08, "effort": 0.08, "risk": 0.12, "client_value": 0.08,
    "business_fit": 0.08, "recurring_revenue": 0.04, "strategic_fit": 0.03,
    "confidence": 0.07, "freshness": 0.06,
}

OPPORTUNITY_CATEGORIES = (
    "SEO",
    "affiliate",
    "local lead generation",
    "YouTube/content",
    "digital products",
    "service businesses",
    "AI-enabled services",
    "microsites",
    "landing-page funnels",
    "referral programs",
    "partnerships",
    "voice-agent services",
    "research products",
    "software/tools",
    "open_source",
    "general",
)

OPPORTUNITY_STATUSES = (
    "DISCOVERED",
    "RESEARCHING",
    "VALIDATED",
    "REJECTED",
    "PILOT_PROPOSED",
    "APPROVED",
    "BUILDING",
    "LAUNCHED",
    "MEASURING",
    "SCALING",
    "PAUSED",
    "KILLED",
)

_STATUS_TRANSITIONS = {
    "DISCOVERED": {"RESEARCHING", "VALIDATED", "REJECTED", "PILOT_PROPOSED", "PAUSED"},
    "RESEARCHING": {"VALIDATED", "REJECTED", "PILOT_PROPOSED", "PAUSED"},
    "VALIDATED": {"APPROVED", "REJECTED", "PILOT_PROPOSED", "PAUSED"},
    "REJECTED": {"DISCOVERED"},
    "PILOT_PROPOSED": {"APPROVED", "REJECTED", "PAUSED"},
    "APPROVED": {"BUILDING", "PAUSED", "KILLED"},
    "BUILDING": {"LAUNCHED", "PAUSED", "KILLED"},
    "LAUNCHED": {"MEASURING", "PAUSED", "KILLED"},
    "MEASURING": {"SCALING", "PAUSED", "KILLED"},
    "SCALING": {"PAUSED", "KILLED"},
    "PAUSED": {"DISCOVERED", "RESEARCHING", "APPROVED", "KILLED"},
    "KILLED": {"DISCOVERED"},
}

_CATEGORY_KEYWORDS = {
    "SEO": ("seo", "search", "google", "rank", "keyword"),
    "affiliate": ("affiliate", "referral", "partner program", "commission"),
    "local lead generation": ("local lead", "local seo", "maps", "near me"),
    "YouTube/content": ("youtube", "content", "creator", "video", "channel"),
    "digital products": ("digital product", "template", "checklist", "guide", "ebook"),
    "service businesses": ("service business", "agency", "done-for-you", "consulting"),
    "AI-enabled services": ("ai service", "agent service", "automation service", "workflow service"),
    "microsites": ("microsite", "micro-site"),
    "landing-page funnels": ("landing page", "funnel", "sales page", "lead magnet"),
    "referral programs": ("referral", "partner", "introduction program"),
    "partnerships": ("partnership", "co-marketing", "joint venture"),
    "voice-agent services": ("voice agent", "call agent", "voice bot"),
    "research products": ("research product", "market research", "insight product"),
    "software/tools": ("software", "tool", "mcp", "plugin", "sdk"),
    "open_source": ("open source", "github", "repo", "oss"),
}

_POSITIVE_STATES = {"open", "active", "new", "ready", "approved", "validated", "pilot", "launched"}
_NEGATIVE_STATES = {"rejected", "closed", "killed", "blocked"}


class OpportunityStateTransitionError(ValueError):
    """Raised when an invalid lifecycle transition is requested."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _stable_hash(payload: Any) -> str:
    text = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def _as_number(value: Any, default: float = 0.0) -> float:
    if isinstance(value, bool):
        return float(default)
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value))
    except Exception:
        return float(default)


def _signal_to_unit(value: Any) -> float:
    number = _as_number(value, 0.0)
    if number <= 0:
        return 0.0
    if number <= 10:
        return min(number / 10.0, 1.0)
    if number <= 100:
        return min(number / 100.0, 1.0)
    return min(number / 1000.0, 1.0)


def _inverse_cost_unit(value: Any) -> float:
    number = _as_number(value, 0.0)
    if number <= 0:
        return 1.0
    if number <= 10:
        return max(0.0, 1.0 - number / 10.0)
    if number <= 100:
        return max(0.0, 1.0 - number / 100.0)
    if number <= 1000:
        return max(0.0, 1.0 - number / 1000.0)
    return 1.0 / (1.0 + number / 10000.0)


def _parse_datetime(value: Any) -> Optional[datetime]:
    if not value:
        return None
    try:
        text = str(value).replace("Z", "+00:00")
        return datetime.fromisoformat(text)
    except Exception:
        return None


def _recency_bonus(record: Dict[str, Any]) -> int:
    for field in ("updated_at", "created_at", "published_at", "last_checked"):
        parsed = _parse_datetime(record.get(field))
        if parsed:
            age_days = max(0.0, (datetime.now(timezone.utc) - parsed.astimezone(timezone.utc)).total_seconds() / 86400.0)
            if age_days <= 7:
                return 12
            if age_days <= 30:
                return 8
            if age_days <= 90:
                return 4
            return 0
    return 0


def _category_from_text(text: str) -> str:
    lower = text.lower()
    for category, keywords in _CATEGORY_KEYWORDS.items():
        if any(keyword in lower for keyword in keywords):
            return category
    return "general"


def _normalize_status(raw_status: Any, raw_action_state: Any = "") -> str:
    status = _clean_text(raw_status).lower()
    action_state = _clean_text(raw_action_state).lower()
    if status in _NEGATIVE_STATES or action_state in _NEGATIVE_STATES:
        return "REJECTED" if "reject" in status or "reject" in action_state else "KILLED"
    if status in {"researching", "review", "reviewed"} or action_state == "reviewed":
        return "RESEARCHING"
    if status in {"validated", "confirmed"}:
        return "VALIDATED"
    if status in {"pilot", "pilot_proposed", "proposal", "proposed"}:
        return "PILOT_PROPOSED"
    if status in {"approved", "approved_for_build"}:
        return "APPROVED"
    if status in {"building", "in_progress", "in-progress", "active"} or action_state == "active":
        return "BUILDING"
    if status in {"launched", "live"}:
        return "LAUNCHED"
    if status in {"measuring", "measured"}:
        return "MEASURING"
    if status in {"scaling"}:
        return "SCALING"
    if status in {"paused", "pause"}:
        return "PAUSED"
    return "DISCOVERED"


def normalize_opportunity_status(raw_status: Any, raw_action_state: Any = "") -> str:
    return _normalize_status(raw_status, raw_action_state)


def build_opportunity_evidence(
    *,
    source_id: str,
    source_type: str,
    classification: str,
    summary: str,
    retrieved_at: Optional[str] = None,
    provenance: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    if not source_id or not source_type:
        raise ValueError("evidence requires source_id and source_type")
    classification = classification.upper()
    if classification not in {"KNOWN", "INFERRED", "UNVERIFIED"}:
        raise ValueError("invalid evidence classification")
    return {
        "evidence_id": f"evidence_{_stable_hash([source_id, source_type, summary, classification])[:16]}",
        "source_id": source_id,
        "source_type": source_type,
        "classification": classification,
        "summary": _clean_text(summary),
        "retrieved_at": retrieved_at or _utc_now(),
        "provenance": json.loads(json.dumps(provenance or {}, sort_keys=True, default=str)),
    }


def _score_breakdown(record: Dict[str, Any]) -> Dict[str, int]:
    evidence_count = len(record.get("evidence", []))
    search_demand = _signal_to_unit(record.get("search_demand"))
    social_signal = _signal_to_unit(record.get("social_signal"))
    competitive_signal = _signal_to_unit(record.get("competitive_signal"))
    commercial_intent = _signal_to_unit(record.get("commercial_intent"))
    revenue_potential = _signal_to_unit(record.get("revenue_potential"))
    confidence = _signal_to_unit(record.get("confidence"))
    composite_score = _signal_to_unit(record.get("composite_score", record.get("base_score", 0)))
    startup_cost = _inverse_cost_unit(record.get("startup_cost"))
    ongoing_cost = _inverse_cost_unit(record.get("ongoing_cost"))
    difficulty = _inverse_cost_unit(record.get("difficulty"))
    time_to_test = _inverse_cost_unit(record.get("time_to_test"))
    recency = _recency_bonus(record)
    priority = {"low": 2, "medium": 5, "high": 9, "critical": 12}.get(_clean_text(record.get("priority")).lower(), 0)

    return {
        "evidence_count": min(20, evidence_count * 5),
        "search_demand": round(search_demand * 12),
        "social_signal": round(social_signal * 6),
        "competitive_signal": round(competitive_signal * 5),
        "commercial_intent": round(commercial_intent * 16),
        "revenue_potential": round(revenue_potential * 14),
        "confidence": round(confidence * 10),
        "composite_score": round(composite_score * 18),
        "startup_cost": round(startup_cost * 10),
        "ongoing_cost": round(ongoing_cost * 8),
        "difficulty": round(difficulty * 8),
        "time_to_test": round(time_to_test * 8),
        "recency": recency,
        "priority": priority,
    }


def score_opportunity_record(record: Dict[str, Any]) -> Dict[str, Any]:
    if record.get("score_breakdown") and record.get("base_score") is not None:
        base_score = int(record.get("base_score", 0))
        return {
            "base_score": base_score,
            "opportunity_score": int(record.get("opportunity_score", base_score)),
            "score_breakdown": json.loads(json.dumps(record.get("score_breakdown"), sort_keys=True, default=str)),
        }
    breakdown = _score_breakdown(record)
    base_score = sum(breakdown.values())
    base_score = max(0, min(100, int(base_score)))
    return {
        "base_score": base_score,
        "opportunity_score": base_score,
        "score_breakdown": breakdown,
    }


def _recommended_action(status: str, score: int) -> str:
    if status == "REJECTED":
        return "Document why the idea was rejected and stop."
    if status in {"DISCOVERED", "RESEARCHING"}:
        return "Collect more evidence and validate demand."
    if status in {"VALIDATED", "PILOT_PROPOSED"}:
        return "Draft a pilot plan and business case skeleton."
    if status in {"APPROVED", "BUILDING"}:
        return "Build the smallest safe pilot."
    if status in {"LAUNCHED", "MEASURING", "SCALING"}:
        return "Measure retention, conversion, and unit economics."
    return "Review evidence and decide next action."


def canonicalize_opportunity_record(
    raw: Dict[str, Any],
    *,
    source: str,
    source_type: str,
    retrieved_at: Optional[str] = None,
    provenance: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    provenance = json.loads(json.dumps(provenance or {}, sort_keys=True, default=str))
    title = _clean_text(raw.get("title") or raw.get("name") or raw.get("summary") or raw.get("topic") or "Untitled Opportunity")
    description = _clean_text(raw.get("description") or raw.get("summary") or raw.get("why_it_matters") or title)
    context_category = ""
    if isinstance(raw.get("context"), dict):
        context_category = _clean_text(raw.get("context", {}).get("category"))
    category = _clean_text(raw.get("category") or context_category) or _category_from_text(
        " ".join(
            _clean_text(piece)
            for piece in (
                title,
                description,
                raw.get("topic"),
                " ".join(raw.get("tags", [])) if isinstance(raw.get("tags"), list) else "",
            )
        )
    )
    status = _normalize_status(raw.get("status"), raw.get("action_state"))
    evidence = raw.get("evidence")
    if not isinstance(evidence, list) or not evidence:
        evidence = [
            build_opportunity_evidence(
                source_id=_clean_text(raw.get("id") or raw.get("source_id") or title),
                source_type=source_type,
                classification=_clean_text(raw.get("evidence_classification") or "UNVERIFIED").upper(),
                summary=description or title,
                retrieved_at=retrieved_at,
                provenance={
                    "source": source,
                    "source_type": source_type,
                    "source_id": raw.get("source_id") or raw.get("id"),
                },
            )
        ]
    record = {
        "id": _clean_text(raw.get("id") or raw.get("source_id") or _stable_hash([source, title, category])[:16]),
        "title": title,
        "category": category,
        "problem": _clean_text(raw.get("problem") or description),
        "target_customer": _clean_text(raw.get("target_customer") or raw.get("audience") or raw.get("client_id") or "Nexus / GoClear"),
        "evidence": evidence,
        "search_demand": raw.get("search_demand", raw.get("search_score", 0)),
        "social_signal": raw.get("social_signal", raw.get("social_score", 0)),
        "competitive_signal": raw.get("competitive_signal", raw.get("competition_score", 0)),
        "commercial_intent": raw.get("commercial_intent", raw.get("buyer_intent", raw.get("composite_score", 0))),
        "revenue_model": _clean_text(raw.get("revenue_model") or raw.get("monetization") or "unknown"),
        "revenue_potential": raw.get("revenue_potential", raw.get("potential_revenue", 0)),
        "startup_cost": raw.get("startup_cost", raw.get("cost_to_execute", raw.get("cost", 0))),
        "ongoing_cost": raw.get("ongoing_cost", raw.get("recurring_cost", 0)),
        "difficulty": raw.get("difficulty", raw.get("execution_difficulty", 0)),
        "time_to_test": raw.get("time_to_test", raw.get("speed_to_value", 0)),
        "risk": raw.get("risk", raw.get("risk_adjustment", 0)),
        "confidence": raw.get("confidence", raw.get("proof_quality", raw.get("composite_score", 0))),
        "status": status,
        "recommended_next_action": _clean_text(raw.get("recommended_next_action") or raw.get("next_action") or _recommended_action(status, 0)),
        "source": source,
        "source_type": source_type,
        "retrieved_at": retrieved_at or _utc_now(),
        "provenance": provenance,
        "tags": list(raw.get("tags", [])) if isinstance(raw.get("tags"), list) else [],
        "source_commit": raw.get("source_commit"),
        "generated_at": raw.get("generated_at"),
        "ai_rationale": _clean_text(raw.get("ai_rationale") or ""),
    }
    record.update(score_opportunity_record(record))
    if not record["recommended_next_action"]:
        record["recommended_next_action"] = _recommended_action(record["status"], record["base_score"])
    return record


def dedupe_opportunity_records(records: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    deduped: List[Dict[str, Any]] = []
    for record in records:
        key = record.get("id") or _stable_hash([
            record.get("title"),
            record.get("category"),
            record.get("target_customer"),
            record.get("source"),
        ])
        key = str(key)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(record)
    return deduped


def validate_opportunity_transition(previous_status: str, next_status: str) -> bool:
    previous_status = previous_status.upper()
    next_status = next_status.upper()
    if previous_status not in OPPORTUNITY_STATUSES:
        raise OpportunityStateTransitionError(f"unknown current status: {previous_status}")
    if next_status not in OPPORTUNITY_STATUSES:
        raise OpportunityStateTransitionError(f"unknown next status: {next_status}")
    allowed = _STATUS_TRANSITIONS.get(previous_status, set())
    if next_status == previous_status:
        return True
    if next_status not in allowed:
        raise OpportunityStateTransitionError(f"invalid transition: {previous_status} -> {next_status}")
    return True


def recommended_ai_tier(base_score: int, *, explicit_premium_escalation: bool = False) -> str:
    if base_score >= 80:
        return "T3_PREMIUM_AI" if explicit_premium_escalation else "T2_STANDARD_AI"
    if base_score >= 55:
        return "T2_STANDARD_AI"
    if base_score >= 40:
        return "T1_CHEAP_AI"
    return "T0_DETERMINISTIC"


def build_opportunity_business_case(record: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "problem": record.get("problem"),
        "target_customer": record.get("target_customer"),
        "revenue_model": record.get("revenue_model"),
        "revenue_potential": record.get("revenue_potential"),
        "cost_profile": {
            "startup_cost": record.get("startup_cost"),
            "ongoing_cost": record.get("ongoing_cost"),
        },
        "validation_plan": [
            "Confirm a real customer pain point.",
            "Validate demand with public evidence.",
            "Run the smallest safe test.",
        ],
        "recommended_next_action": record.get("recommended_next_action"),
    }


def _candidate_preview(record: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": record.get("id"),
        "title": record.get("title"),
        "category": record.get("category"),
        "status": record.get("status"),
        "base_score": record.get("base_score"),
        "opportunity_score": record.get("opportunity_score"),
        "recommended_next_action": record.get("recommended_next_action"),
        "source": record.get("source"),
        "source_type": record.get("source_type"),
    }


def merge_ai_result(reduced: Dict[str, Any], ai_result: Dict[str, Any]) -> Dict[str, Any]:
    merged = json.loads(json.dumps(reduced, sort_keys=True, default=str))
    merged.setdefault("ai_summary", "")
    merged.setdefault("ai_rationale", "")
    canonical = merged.get("canonical_record", {})
    if isinstance(canonical, dict):
        protected = {key: canonical.get(key) for key in ("base_score", "opportunity_score", "score_breakdown", "evidence", "status")}
    else:
        protected = {}
    for key, value in ai_result.items():
        if key in {"base_score", "opportunity_score", "score_breakdown", "evidence", "status"} and key in protected:
            merged[f"ai_proposed_{key}"] = value
            continue
        merged[key] = value
    if protected and isinstance(merged.get("canonical_record"), dict):
        for key, value in protected.items():
            merged["canonical_record"][key] = value
    return merged


def _previous_candidate_index(previous_state: Optional[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    if not previous_state:
        return {}
    last_result = previous_state.get("last_result", {})
    candidates = last_result.get("canonical_opportunities") or last_result.get("top_candidates") or []
    index = {}
    for item in candidates:
        if isinstance(item, dict) and item.get("id"):
            index[str(item["id"])] = item
    return index


def _build_sources(
    opportunities_payload: Dict[str, Any],
    research_payload: Dict[str, Any],
    business_payload: Dict[str, Any],
    recommendations_payload: Optional[Sequence[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    sources: List[Dict[str, Any]] = []

    opportunity_items = opportunities_payload.get("data", {}).get("items", []) if isinstance(opportunities_payload, dict) else []
    for item in opportunity_items:
        if isinstance(item, dict):
            sources.append({**item, "source": "business_opportunities", "source_type": opportunities_payload.get("source_type", "live_governed_read")})

    if recommendations_payload:
        for item in recommendations_payload:
            if isinstance(item, dict):
                sources.append({**item, "source": "recommendations", "source_type": "public_recommendation_snapshot"})

    if isinstance(research_payload, dict):
        research_items = research_payload.get("data", {}).get("results", {}).get("items", [])
        for item in research_items:
            if isinstance(item, dict):
                sources.append({
                    "id": item.get("id"),
                    "title": item.get("title") or item.get("source"),
                    "summary": item.get("title") or item.get("source"),
                    "category": "research products",
                    "status": "DISCOVERED",
                    "source": "nexus_research_results",
                    "source_type": research_payload.get("source_type", "live_governed_read"),
                    "evidence_classification": "KNOWN",
                    "evidence": [{
                        "source_id": item.get("id") or item.get("run_id") or item.get("title") or "research_result",
                        "source_type": research_payload.get("source_type", "live_governed_read"),
                        "classification": "KNOWN",
                        "summary": item.get("title") or item.get("source") or "research result",
                        "retrieved_at": item.get("created_at"),
                        "provenance": {"source": "research_results", "run_id": item.get("run_id")},
                    }],
                })

    if isinstance(business_payload, dict):
        offers = business_payload.get("offers", [])
        for item in offers:
            if isinstance(item, dict):
                sources.append({
                    **item,
                    "source": "business_model_summary",
                    "source_type": business_payload.get("source_type", "study_snapshot_artifact"),
                    "category": item.get("category") or "service businesses",
                })
    return sources


def build_opportunity_discovery_packet(
    *,
    opportunities_payload: Dict[str, Any],
    research_payload: Dict[str, Any],
    business_payload: Dict[str, Any],
    previous_state: Optional[Dict[str, Any]] = None,
    trigger: Optional[Dict[str, Any]] = None,
    recommendations_payload: Optional[Sequence[Dict[str, Any]]] = None,
    explicit_premium_escalation: bool = False,
) -> Dict[str, Any]:
    trigger = trigger or {}
    sources = _build_sources(opportunities_payload, research_payload, business_payload, recommendations_payload)
    canonical_opportunities = [canonicalize_opportunity_record(source, source=source.get("source", "unknown"), source_type=source.get("source_type", "unknown")) for source in sources]
    canonical_opportunities = dedupe_opportunity_records(canonical_opportunities)
    canonical_opportunities.sort(key=lambda item: (item.get("base_score", 0), item.get("title", "")), reverse=True)

    previous_index = _previous_candidate_index(previous_state)
    changed_candidates = []
    for item in canonical_opportunities[:5]:
        prev = previous_index.get(str(item.get("id")))
        if not prev or prev.get("base_score") != item.get("base_score") or prev.get("status") != item.get("status"):
            changed_candidates.append(item)

    top_candidate = canonical_opportunities[0] if canonical_opportunities else None
    top_score = top_candidate.get("base_score", 0) if top_candidate else 0
    materiality = {
        "new_candidates": len(changed_candidates),
        "top_score": top_score,
    }
    summary = {
        "opportunity_total": len(canonical_opportunities),
        "research_run_total": research_payload.get("data", {}).get("runs", {}).get("total", 0) if isinstance(research_payload, dict) else 0,
        "offer_total": business_payload.get("offers_count", 0) if isinstance(business_payload, dict) else 0,
    }
    if top_candidate:
        top_candidate = json.loads(json.dumps(top_candidate, sort_keys=True, default=str))
        top_candidate["business_case"] = build_opportunity_business_case(top_candidate)

    ai_context = {
        "loop_id": "opportunity_discovery_loop",
        "summary": summary,
        "top_candidates": [_candidate_preview(item) for item in canonical_opportunities[:3]],
        "changed_candidates": [_candidate_preview(item) for item in changed_candidates[:3]],
        "previous_state": {
            "last_input_hash": previous_state.get("last_input_hash") if previous_state else None,
            "last_output_hash": previous_state.get("last_output_hash") if previous_state else None,
            "last_result_summary": (previous_state.get("last_result", {}) or {}).get("summary", {}) if previous_state else {},
            "last_result_ids": [
                item.get("id")
                for item in ((previous_state.get("last_result", {}) or {}).get("canonical_opportunities", [])[:5] if previous_state else [])
                if item.get("id")
            ] if previous_state else [],
        },
        "instructions": [
            "Use only the compact delta.",
            "Do not restate the full history.",
            "Preserve deterministic base_score and evidence.",
            "Return interpretation, not a score rewrite.",
        ],
    }

    candidate_tier = recommended_ai_tier(top_score, explicit_premium_escalation=explicit_premium_escalation)
    should_use_ai = bool(changed_candidates and top_score >= 55 and candidate_tier != "T0_DETERMINISTIC")

    canonical_record = {
        "status": "success",
        "summary": summary,
        "canonical_opportunities": canonical_opportunities,
        "canonical_record": top_candidate or {},
        "changed_candidates": changed_candidates,
        "materiality": materiality,
        "business_case_skeleton": build_opportunity_business_case(top_candidate or {}),
        "recommended_ai_tier": candidate_tier,
        "should_use_ai": should_use_ai,
        "ai_context": ai_context,
        "source_commit": business_payload.get("source_commit") if isinstance(business_payload, dict) else None,
        "generated_at": _utc_now(),
        "source_types": {
            "opportunities": opportunities_payload.get("source_type", "live_governed_read"),
            "research": research_payload.get("source_type", "live_governed_read"),
            "business": business_payload.get("source_type", "study_snapshot_artifact"),
        },
    }
    canonical_record["input_hash"] = _stable_hash({
        "trigger": trigger,
        "opportunity_ids": [item.get("id") for item in canonical_opportunities],
        "summary": summary,
        "source_commit": canonical_record.get("source_commit"),
    })
    canonical_record["output_hash"] = _stable_hash(canonical_record["canonical_opportunities"])
    return canonical_record


# ---------------------------------------------------------------------------
# Phase K governed opportunity contract
# ---------------------------------------------------------------------------

def _norm_identity(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", _clean_text(value).lower()).strip()


def _bounded_score(value: Any, default: float = 0.0) -> float:
    number = _as_number(value, default)
    if number <= 1:
        return max(0.0, min(100.0, number * 100.0))
    return max(0.0, min(100.0, number))


def _freshness_status(retrieved_at: Any, requirement: str = "CURRENT", *, now: Optional[datetime] = None) -> str:
    parsed = _parse_datetime(retrieved_at)
    if not parsed:
        return "UNKNOWN"
    now = now or datetime.now(timezone.utc)
    age_days = max(0.0, (now - parsed.astimezone(timezone.utc)).total_seconds() / 86400.0)
    if requirement == "CURRENT":
        return "CURRENT" if age_days <= 7 else "AGING" if age_days <= 30 else "STALE"
    return "CURRENT" if age_days <= 30 else "AGING" if age_days <= 90 else "STALE"


def _candidate_evidence_refs(candidate: Dict[str, Any]) -> List[str]:
    refs = candidate.get("evidence_refs") or candidate.get("evidence_ids") or []
    return [str(ref) for ref in refs if str(ref).strip()]


def _pack_evidence_refs(research_pack: Optional[Dict[str, Any]]) -> set[str]:
    if not isinstance(research_pack, dict):
        return set()
    refs = set(str(ref) for ref in (research_pack.get("evidence_refs") or []) if str(ref).strip())
    for claim in research_pack.get("claims") or []:
        if isinstance(claim, dict):
            refs.update(str(ref) for ref in claim.get("evidence_refs") or [] if str(ref).strip())
    return refs


def validate_alpha_opportunity_candidate(candidate: Dict[str, Any], research_pack: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Validate an Alpha advisory candidate without granting authority."""
    if not isinstance(candidate, dict):
        return {"valid": False, "status": "FAILED", "reason": "candidate_not_object"}
    title = _clean_text(candidate.get("opportunity_title") or candidate.get("title"))
    if not title:
        return {"valid": False, "status": "FAILED", "reason": "missing_title"}
    refs = _candidate_evidence_refs(candidate)
    pack_refs = _pack_evidence_refs(research_pack)
    if not refs:
        return {"valid": False, "status": "NEEDS_RESEARCH", "reason": "missing_evidence_refs"}
    if research_pack is not None and not set(refs).issubset(pack_refs):
        return {"valid": False, "status": "NEEDS_RESEARCH", "reason": "evidence_ref_not_in_research_pack"}
    return {"valid": True, "status": "VALIDATED", "reason": "evidence_refs_present", "evidence_refs": refs}


def validate_governed_opportunity_record(record: Dict[str, Any]) -> Dict[str, Any]:
    required = ("schema_version", "opportunity_id", "fingerprint", "title", "status", "evidence_refs", "scores", "value_estimate", "freshness")
    if not isinstance(record, dict):
        return {"valid": False, "reason": "record_not_object"}
    missing = [field for field in required if field not in record]
    if missing:
        return {"valid": False, "reason": "missing_fields", "fields": missing}
    if record.get("schema_version") != GOVERNED_OPPORTUNITY_SCHEMA:
        return {"valid": False, "reason": "invalid_schema_version"}
    if record.get("status") not in GOVERNED_OPPORTUNITY_STATUSES:
        return {"valid": False, "reason": "invalid_lifecycle_status"}
    if record.get("status") == "QUALIFIED" and not record.get("evidence_refs"):
        return {"valid": False, "reason": "qualified_requires_evidence"}
    return {"valid": True, "reason": "valid"}


def score_governed_opportunity(candidate: Dict[str, Any], *, evidence_valid: bool, freshness: str) -> Dict[str, Any]:
    """Return inspectable 0-100 component scores; no model/LLM ranking."""
    scores = candidate.get("scores") if isinstance(candidate.get("scores"), dict) else {}
    evidence_count = len(_candidate_evidence_refs(candidate))
    evidence_strength = 100.0 if evidence_valid and evidence_count >= 2 else 75.0 if evidence_valid else 15.0
    freshness_score = {"CURRENT": 100.0, "AGING": 65.0, "STALE": 20.0, "UNKNOWN": 35.0}.get(freshness, 35.0)
    components = {
        "evidence_strength": evidence_strength,
        "revenue_potential": _bounded_score(scores.get("revenue_potential", candidate.get("potential_value")), 0),
        "speed_to_value": _bounded_score(scores.get("speed_to_value", candidate.get("speed_to_value")), 0),
        "launch_cost": _bounded_score(scores.get("launch_cost", candidate.get("launch_cost")), 0),
        "effort": _bounded_score(scores.get("effort", candidate.get("effort")), 0),
        "risk": _bounded_score(scores.get("risk", candidate.get("risk")), 0),
        "client_value": _bounded_score(scores.get("client_value", candidate.get("client_value")), 0),
        "business_fit": _bounded_score(scores.get("business_fit", candidate.get("business_fit")), 0),
        "recurring_revenue": _bounded_score(scores.get("recurring_revenue_potential", candidate.get("recurring_revenue_potential")), 0),
        "strategic_fit": _bounded_score(scores.get("strategic_fit", candidate.get("strategic_fit")), 0),
        "confidence": _bounded_score(scores.get("confidence", candidate.get("confidence")), 50 if evidence_valid else 15),
        "freshness": freshness_score,
    }
    # Keep opportunity quality separate from how well the opportunity is
    # evidenced.  Missing/unknown evidence should lower confidence and route
    # to research; it must not silently become a low-quality opportunity.
    quality_keys = ("revenue_potential", "speed_to_value", "launch_cost", "effort", "risk", "client_value", "business_fit", "recurring_revenue", "strategic_fit")
    quality_components = {key: components[key] for key in quality_keys if key in scores or key in candidate}
    # An absent dimension is unknown, not a negative score.  Keep it out of
    # the denominator and expose the supplied evidence separately.
    if not quality_components:
        quality_components = {key: 50.0 for key in quality_keys}
    quality_weights = {key: _SCORING_WEIGHTS[key] for key in quality_components}
    quality_weight_total = sum(quality_weights.values()) or 1.0
    quality = round(sum(quality_components[key] * quality_weights[key] for key in quality_components) / quality_weight_total)
    evidence_confidence = round((components["evidence_strength"] * 0.55) + (components["confidence"] * 0.30) + (components["freshness"] * 0.15))
    positive = sum(components[name] * weight for name, weight in _SCORING_WEIGHTS.items())
    overall = round(max(0.0, min(100.0, positive - components["risk"] * 0.10 - components["launch_cost"] * 0.06 - components["effort"] * 0.04)))
    return {"policy": SCORING_POLICY_VERSION, "overall_score": overall,
            "opportunity_quality_score": quality,
            "evidence_confidence_score": evidence_confidence,
            "components": {k: round(v, 2) for k, v in components.items()},
            "weights": _SCORING_WEIGHTS,
            "penalties": {"risk": 0.10, "launch_cost": 0.06, "effort": 0.04},
            "interpretation": "PROMISING_RESEARCH_MORE" if quality >= 55 and evidence_confidence < 60 else "QUALIFIED_CANDIDATE" if evidence_confidence >= 60 else "EARLY_SCREEN"}


def _opportunity_fingerprint(candidate: Dict[str, Any]) -> str:
    return _stable_hash({
        "title": _norm_identity(candidate.get("opportunity_title") or candidate.get("title")),
        "category": _norm_identity(candidate.get("category")),
        "business": _norm_identity(candidate.get("business") or candidate.get("business_unit") or "goclear"),
        "monetization_path": _norm_identity(candidate.get("monetization_path") or candidate.get("monetization")),
        "target": _norm_identity(candidate.get("target_audience") or candidate.get("target_customer")),
    })[:24]


def _value_estimate(candidate: Dict[str, Any]) -> Dict[str, Any]:
    raw = candidate.get("value_estimate")
    if not isinstance(raw, dict):
        return {"status": "UNKNOWN", "low": None, "expected": None, "high": None, "currency": None, "time_horizon": candidate.get("time_horizon"), "assumptions": [], "actual_revenue": None}
    status = str(raw.get("status", "ASSUMPTION")).upper()
    if status not in {"KNOWN", "EVIDENCE_BACKED_ESTIMATE", "ASSUMPTION", "UNKNOWN"}:
        status = "ASSUMPTION"
    return {"status": status, "low": raw.get("low"), "expected": raw.get("expected"), "high": raw.get("high"), "currency": raw.get("currency"), "time_horizon": raw.get("time_horizon") or candidate.get("time_horizon"), "assumptions": list(raw.get("assumptions") or []), "actual_revenue": None}


def canonicalize_governed_opportunity(candidate: Dict[str, Any], *, research_job_id: Optional[str] = None, research_pack_ref: Optional[str] = None, research_pack: Optional[Dict[str, Any]] = None, now: Optional[str] = None) -> Dict[str, Any]:
    validation = validate_alpha_opportunity_candidate(candidate, research_pack)
    refs = validation.get("evidence_refs", _candidate_evidence_refs(candidate))
    retrieved_at = candidate.get("retrieved_at") or candidate.get("freshness", {}).get("retrieved_at") if isinstance(candidate.get("freshness"), dict) else candidate.get("retrieved_at")
    freshness_requirement = str(candidate.get("freshness_requirement") or "CURRENT").upper()
    freshness = _freshness_status(retrieved_at, freshness_requirement)
    evidence_valid = bool(validation.get("valid")) and freshness not in {"STALE", "UNKNOWN"}
    score = score_governed_opportunity(candidate, evidence_valid=evidence_valid, freshness=freshness)
    status = "QUALIFIED" if evidence_valid else "NEEDS_RESEARCH"
    if candidate.get("requires_ray_review") or _bounded_score(candidate.get("risk"), 0) >= 70:
        status = "NEEDS_RAY_REVIEW" if evidence_valid else status
    title = _clean_text(candidate.get("opportunity_title") or candidate.get("title"))
    created = now or _utc_now()
    return {
        "schema_version": GOVERNED_OPPORTUNITY_SCHEMA,
        "opportunity_id": f"opp_{_opportunity_fingerprint(candidate)}",
        "fingerprint": _opportunity_fingerprint(candidate),
        "title": title,
        "summary": _clean_text(candidate.get("description") or candidate.get("summary") or title),
        "category": _clean_text(candidate.get("category") or "other"),
        "business": _clean_text(candidate.get("business") or "GoClear"),
        "business_unit": _clean_text(candidate.get("business_unit") or "opportunity_intelligence"),
        "source_type": "alpha_research_pack" if research_pack is not None else _clean_text(candidate.get("source_type") or "legacy_candidate"),
        "source_research_job_id": research_job_id,
        "source_research_pack_ref": research_pack_ref,
        "evidence_refs": refs,
        "status": status,
        "monetization_path": _clean_text(candidate.get("monetization_path") or candidate.get("monetization") or "UNKNOWN"),
        "target_audience": _clean_text(candidate.get("target_audience") or candidate.get("target_customer") or "UNKNOWN"),
        "scores": score,
        "opportunity_quality_score": score["opportunity_quality_score"],
        "evidence_confidence_score": score["evidence_confidence_score"],
        "value_estimate": _value_estimate(candidate),
        "dependencies": list(candidate.get("dependencies") or []),
        "relationships": list(candidate.get("relationships") or []),
        "risks": list(candidate.get("risks") or []),
        "unknowns": list(candidate.get("unknowns") or []),
        "contradictions": list(candidate.get("contradictions") or []),
        "recommended_next_action": _clean_text(candidate.get("recommended_next_action") or "Review evidence and determine the next bounded research or planning step."),
        "research_needed": [] if evidence_valid else [validation.get("reason", "additional evidence required")],
        "approval_required": True,
        "approval_reason": "Ray review is required before any consequential planning or external action.",
        "created_at": created,
        "updated_at": created,
        "freshness": {"requirement": freshness_requirement, "retrieved_at": retrieved_at, "status": freshness},
        "legacy_classification": None,
        "actual_outcome": {"actual_leads": None, "actual_sales": None, "actual_revenue": None, "actual_cost": None, "actual_margin": None},
        "external_action_performed": False,
    }


def _latest_opportunities() -> List[Dict[str, Any]]:
    seen: set[str] = set()
    result: List[Dict[str, Any]] = []
    for row in persistence.read_records("opportunities"):
        key = str(row.get("opportunity_id"))
        if key and key not in seen:
            seen.add(key)
            result.append(row)
    return result


def get_governed_opportunity(opportunity_id: str) -> Optional[Dict[str, Any]]:
    return next((row for row in _latest_opportunities() if row.get("opportunity_id") == opportunity_id), None)


def list_governed_opportunities(*, status: Optional[str] = None) -> List[Dict[str, Any]]:
    rows = _latest_opportunities()
    return [row for row in rows if status is None or row.get("status") == status]


def _record_opportunity_event(event: str, opportunity: Dict[str, Any], *, previous_status: Optional[str] = None, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return persistence.emit_audit_event({
        "type": "opportunity_" + event,
        "opportunity_id": opportunity.get("opportunity_id"),
        "previous_status": previous_status,
        "new_status": opportunity.get("status"),
        "score": (opportunity.get("scores") or {}).get("overall_score"),
        "research_job_id": opportunity.get("source_research_job_id"),
        "evidence_refs": opportunity.get("evidence_refs", []),
        "actor": "nexus_opportunity_engine",
        "external_action_performed": False,
        **(extra or {}),
    })


def persist_governed_opportunity(opportunity: Dict[str, Any], *, event: str = "created") -> Dict[str, Any]:
    validation = validate_governed_opportunity_record(opportunity)
    if not validation["valid"]:
        raise ValueError("invalid governed opportunity: " + validation["reason"])
    existing = get_governed_opportunity(opportunity["opportunity_id"])
    if existing:
        if existing.get("fingerprint") == opportunity.get("fingerprint"):
            _record_opportunity_event("duplicate_suppressed", existing, extra={"incoming_source": opportunity.get("source_type")})
            return {"status": "DUPLICATE_SUPPRESSED", "opportunity": existing}
        raise ValueError("opportunity identity collision")
    persistence.append_record("opportunities", opportunity)
    event = _record_opportunity_event(event, opportunity)
    return {"status": "CREATED", "opportunity": opportunity, "event": event}


def import_alpha_opportunity_candidate(candidate: Dict[str, Any], *, research_job_id: str, research_pack_ref: str, research_pack: Dict[str, Any]) -> Dict[str, Any]:
    opportunity = canonicalize_governed_opportunity(candidate, research_job_id=research_job_id, research_pack_ref=research_pack_ref, research_pack=research_pack)
    return persist_governed_opportunity(opportunity, event="imported")


def ingest_legacy_opportunity(candidate: Dict[str, Any], *, source: str = "task_requests") -> Dict[str, Any]:
    legacy = dict(candidate)
    legacy.pop("evidence_refs", None)
    opportunity = canonicalize_governed_opportunity(legacy, now=_utc_now())
    opportunity["source_type"] = "legacy_candidate"
    opportunity["legacy_classification"] = "UNVALIDATED_LEGACY"
    opportunity["status"] = "NEEDS_RESEARCH"
    opportunity["research_needed"] = [f"legacy source {source} has no canonical evidence chain"]
    opportunity["value_estimate"] = {"status": "UNKNOWN", "low": None, "expected": None, "high": None, "currency": None, "time_horizon": None, "assumptions": [], "actual_revenue": None}
    return persist_governed_opportunity(opportunity, event="legacy_imported")


def transition_governed_opportunity(opportunity_id: str, next_status: str, *, actor: str = "nexus_opportunity_engine", approval_id: Optional[str] = None, work_order_id: Optional[str] = None) -> Dict[str, Any]:
    current = get_governed_opportunity(opportunity_id)
    if not current:
        raise ValueError("opportunity not found")
    next_status = next_status.upper()
    if next_status not in GOVERNED_OPPORTUNITY_STATUSES or next_status not in _GOVERNED_TRANSITIONS[current.get("status", "")]:
        raise ValueError(f"invalid opportunity transition: {current.get('status')} -> {next_status}")
    updated = {**current, "status": next_status, "updated_at": _utc_now(), "approval_id": approval_id or current.get("approval_id"), "work_order_id": work_order_id or current.get("work_order_id")}
    persistence.append_record("opportunities", updated)
    _record_opportunity_event("status_changed", updated, previous_status=current.get("status"), extra={"actor": actor})
    return updated


def mark_stale_opportunities(*, now: Optional[datetime] = None) -> List[Dict[str, Any]]:
    changed = []
    for row in _latest_opportunities():
        if row.get("status") not in {"QUALIFIED", "NEEDS_RAY_REVIEW", "CANDIDATE"}:
            continue
        status = (row.get("freshness") or {}).get("status")
        if status == "STALE":
            changed.append(transition_governed_opportunity(row["opportunity_id"], "STALE"))
    return changed


def opportunity_rankings() -> Dict[str, List[Dict[str, Any]]]:
    rows = list_governed_opportunities()
    active = [row for row in rows if row.get("status") not in {"REJECTED", "PARKED", "CLOSED", "STALE"}]
    by = lambda key: sorted(active, key=lambda row: (row.get("scores", {}).get("components", {}).get(key, 0), row.get("scores", {}).get("overall_score", 0)), reverse=True)
    return {"best_overall": sorted(active, key=lambda row: row.get("scores", {}).get("overall_score", 0), reverse=True), "fastest_to_value": by("speed_to_value"), "lowest_risk": sorted(active, key=lambda row: row.get("scores", {}).get("components", {}).get("risk", 100)), "highest_confidence": by("confidence"), "highest_revenue_potential": by("revenue_potential"), "best_client_value": by("client_value"), "needs_ray": [row for row in rows if row.get("status") == "NEEDS_RAY_REVIEW"], "needs_research": [row for row in rows if row.get("status") == "NEEDS_RESEARCH"]}


def opportunity_portfolio() -> Dict[str, Any]:
    rows = list_governed_opportunities()
    counts = {status: sum(1 for row in rows if row.get("status") == status) for status in GOVERNED_OPPORTUNITY_STATUSES}
    estimates = [row.get("value_estimate", {}).get("expected") for row in rows if isinstance(row.get("value_estimate", {}).get("expected"), (int, float))]
    return {"total_active": sum(counts.get(status, 0) for status in ("CANDIDATE", "QUALIFIED", "NEEDS_RESEARCH", "NEEDS_RAY_REVIEW", "APPROVED_FOR_PLANNING")), "counts": counts, "pipeline_value_estimate": {"status": "ESTIMATED" if estimates else "UNKNOWN", "expected_total": sum(estimates) if estimates else None, "currency": "USD" if estimates else None}, "top_opportunity": (opportunity_rankings()["best_overall"] or [None])[0], "rankings": opportunity_rankings()}


def answer_opportunity_question(question: str) -> Dict[str, Any]:
    """Bounded Hermes-facing read helper; it never invents scores or acts."""
    text = _clean_text(question).lower()
    rankings = opportunity_rankings()
    if "approval" in text or "ray" in text:
        return {"type": "needs_ray", "opportunities": rankings["needs_ray"], "source": "canonical_opportunities"}
    if "fast" in text or "today" in text or "focus" in text:
        return {"type": "fastest_to_value", "opportunities": rankings["fastest_to_value"][:5], "source": "canonical_opportunities"}
    if "why" in text or "rank" in text:
        return {"type": "ranking_explanation", "opportunities": rankings["best_overall"][:5], "scoring_policy": SCORING_POLICY_VERSION, "source": "canonical_opportunities"}
    return {"type": "best_overall", "opportunities": rankings["best_overall"][:5], "source": "canonical_opportunities"}


def create_opportunity_review_request(opportunity_id: str) -> Dict[str, Any]:
    from nexus_agent_platform.governed.approvals import create_approval_request
    opportunity = get_governed_opportunity(opportunity_id)
    if not opportunity:
        raise ValueError("opportunity not found")
    if opportunity.get("status") not in {"QUALIFIED", "NEEDS_RESEARCH", "NEEDS_RAY_REVIEW"}:
        raise ValueError("opportunity is not reviewable")
    updated = opportunity if opportunity.get("status") == "NEEDS_RAY_REVIEW" else transition_governed_opportunity(opportunity_id, "NEEDS_RAY_REVIEW")
    approval = create_approval_request(action_id="opportunity.review", action_summary=f"Review opportunity {opportunity_id}", input_summary={"opportunity_id": opportunity_id}, evidence_refs=updated.get("evidence_refs", []), recommendation_id=opportunity_id)
    updated = {**updated, "approval_id": approval["id"], "updated_at": _utc_now()}
    persistence.append_record("opportunities", updated)
    _record_opportunity_event("review_requested", updated, extra={"approval_id": approval["id"]})
    return {"opportunity": updated, "approval": approval}


def prepare_opportunity_work_order(opportunity_id: str, approval_id: str) -> Dict[str, Any]:
    from nexus_agent_platform.governed import approvals, work_orders
    opportunity = get_governed_opportunity(opportunity_id)
    approval = approvals.get_approval(approval_id)
    if not opportunity or not approval or approval.get("status") != "approved" or opportunity.get("status") != "APPROVED_FOR_PLANNING":
        raise ValueError("approved opportunity and matching approved approval are required")
    order = work_orders.create_work_order(approval_id=approval_id, action_id="opportunity.review", requested_by="nexus_opportunity_engine", approved_by=approval.get("resolved_by") or "ray", inputs={"opportunity_id": opportunity_id, "research_job_id": opportunity.get("source_research_job_id"), "evidence_refs": opportunity.get("evidence_refs", [])}, expected_outcome="Bounded internal opportunity planning review; no external action.", recommendation_id=opportunity_id, status="queued")
    updated = transition_governed_opportunity(opportunity_id, "CONVERTED_TO_WORK_ORDER", approval_id=approval_id, work_order_id=order.get("work_order_id"))
    return {"opportunity": updated, "work_order": order, "external_action_performed": False}
