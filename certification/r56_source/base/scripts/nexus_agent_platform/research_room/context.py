"""Compact, role-specific context for Research Room model calls."""
from __future__ import annotations

import hashlib
import json
from typing import Any

PROMPT_VERSION = "research-room-advisor-v1"
MAX_TEXT = 1800
MAX_ROWS = 8


def _text(value: Any, limit: int = MAX_TEXT) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value[:limit]
    return json.dumps(value, ensure_ascii=False, default=str)[:limit]


def compact_context(case: dict[str, Any], *, role: str = "ADVISOR") -> dict[str, Any]:
    """Build a small reusable summary. Raw transcripts and full room history stay out."""
    source = case.get("source_report") or {}
    source_summary = source.get("summary") or source.get("text") or ""
    claims = source.get("claims") or [
        row.get("claim") or row.get("detail") for row in case.get("findings", [])
        if row.get("claim") or row.get("detail")
    ]
    questions = case.get("questions", [])
    result = {
        "prompt_version": PROMPT_VERSION,
        "role": role,
        "provided_input": _text(case.get("provided_input") or case.get("original_request"), 6000),
        "original_objective": _text(case.get("original_request"), 1000),
        "source_summary": _text(source_summary, 2000),
        "source_type": case.get("source_type"),
        "source_references": (case.get("source_references") or [])[:6],
        "source_claims": [_text(x, 400) for x in claims[:MAX_ROWS]],
        "verified_findings": [_text(x, 500) for x in case.get("findings", []) if x.get("confidence") == "HIGH" or x.get("status") == "VERIFIED"][:MAX_ROWS],
        "unverified_findings": [_text(x, 500) for x in case.get("unresolved_items", [])[:MAX_ROWS]],
        "contradictions": [_text(x, 500) for x in case.get("findings", []) if x.get("kind") in {"CONTRADICTION", "CONFLICT"}][:MAX_ROWS],
        "answered_questions": [{"question": _text(q.get("question"), 300), "answer": _text(q.get("answer"), 500)}
                               for q in questions if q.get("status") in {"ANSWERED", "PARTIAL"}][:MAX_ROWS],
        "unresolved_questions": [_text(q.get("question"), 300) for q in questions
                                  if q.get("status") not in {"ANSWERED", "NOT_APPLICABLE"}][:MAX_ROWS],
        "prior_knowledge_summary": [_text(x.get("summary") or x, 600) for x in case.get("prior_nexus_knowledge", [])[:4]],
        "latest_room_deltas": [_text(m.get("content"), 500) for m in case.get("room_messages", [])[-3:]],
        "recommendation_direction": _text(case.get("metadata", {}).get("likely_destination") or "Undetermined", 200),
        "test_results": case.get("test_results", [])[:4],
    }
    if case.get("tool_results") is not None:
        result["tool_results"] = case.get("tool_results")
    business = (case.get("metadata") or {}).get("business_opportunity_report")
    if isinstance(business, dict):
        result["business_opportunity_report"] = {
            "opportunities": [{key: _text(item.get(key), 700) for key in (
                "name", "customer", "problem", "demand_evidence", "offer", "price_hypothesis",
                "acquisition", "nexus_fit", "time_to_revenue", "risks", "validation_test")}
                for item in business.get("opportunities", [])[:3]],
            "recommendation": {key: _text((business.get("recommendation") or {}).get(key), 800)
                for key in ("winner", "why_winner", "why_not_opportunity_2", "why_not_opportunity_3")},
        }
    return result


def context_hash(context: dict[str, Any]) -> str:
    encoded = json.dumps(context, sort_keys=True, ensure_ascii=False, default=str).encode()
    return hashlib.sha256(encoded).hexdigest()
