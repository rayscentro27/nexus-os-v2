#!/usr/bin/env python3
"""
Retrieval Gate — Decides whether to use web search.

Core principle: Internal plan first. Web enrichment second. Merge only on evidence gaps.
"""

import re
from provider_status import get_web_provider_status


def should_retrieve(understanding, draft, active_context=None, provider_status=None):
    """
    Decide whether to retrieve external evidence.
    Returns a dict with retrieve, reason, query, provider, merge_mode.
    """
    if provider_status is None:
        provider_status = get_web_provider_status()

    intent = understanding.get("intent_family", "unknown")
    needs_web = understanding.get("needs_external_evidence", False)
    text = understanding.get("normalized_text", "")
    provider = provider_status.get("provider")
    available = provider_status.get("available", False)

    # --- Rule 1: Explicit web search requests always retrieve ---
    if needs_web:
        if available:
            return {
                "retrieve": True,
                "reason": "User explicitly requested web research",
                "query": _rewrite_query(text, active_context, draft),
                "provider": provider,
                "merge_mode": "enrich",
            }
        else:
            return {
                "retrieve": False,
                "reason": "User requested web but no provider active",
                "query": None,
                "provider": None,
                "merge_mode": "none",
            }

    # --- Rule 2: Draft has evidence gaps that web can fill ---
    evidence_gaps = draft.get("evidence_gaps", [])
    if evidence_gaps and available and _gaps_need_web(evidence_gaps):
        return {
            "retrieve": True,
            "reason": f"Draft has evidence gaps: {', '.join(evidence_gaps[:2])}",
            "query": _rewrite_query(text, active_context, draft),
            "provider": provider,
            "merge_mode": "enrich",
        }

    # --- Rule 3: Broad business questions with strong internal answer — no web ---
    if intent in ("money_plan", "client_acquisition", "business_strategy"):
        if draft.get("confidence", 0) >= 0.7:
            return {
                "retrieve": False,
                "reason": f"Strong internal draft (confidence={draft.get('confidence', 0)}). No web needed.",
                "query": None,
                "provider": None,
                "merge_mode": "none",
            }

    # --- Rule 4: Research deeper on active topic ---
    followup = understanding.get("followup_type", "")
    if followup == "research_deeper" and active_context:
        if available:
            return {
                "retrieve": True,
                "reason": "User requested deeper research on active topic",
                "query": _rewrite_query(text, active_context, draft),
                "provider": provider,
                "merge_mode": "enrich",
            }
        else:
            return {
                "retrieve": False,
                "reason": "Deeper research requested but no provider active",
                "query": None,
                "provider": None,
                "merge_mode": "none",
            }

    # --- Default: no web ---
    return {
        "retrieve": False,
        "reason": "Internal draft sufficient. No web needed.",
        "query": None,
        "provider": None,
        "merge_mode": "none",
    }


def _rewrite_query(text, active_context, draft):
    """Rewrite the user's text into a useful search query."""
    t = text.lower().strip()

    # Use pending action query if available
    # Use draft topic if available
    topic = draft.get("topic", t) if draft else t

    # Strip agent prefixes
    topic = re.sub(r"^(alpha|hermes|nexus)\s+", "", topic).strip()

    # Strip research/search boilerplate
    for prefix in ["search the web for ", "search web for ", "research ", "look up ",
                    "find current ", "find latest ", "what are the best ", "alpha research ",
                    "hermes search the web for ", "hermes research "]:
        if topic.startswith(prefix):
            topic = topic[len(prefix):].strip()
            break

    # Add GoClear context if relevant
    if any(kw in topic for kw in ["client", "money", "revenue", "business", "credit"]):
        if "goclear" not in topic.lower() and "nexus" not in topic.lower():
            topic += " GoClear credit readiness"

    return topic


def _gaps_need_web(gaps):
    """Check if evidence gaps require web search."""
    web_keywords = ["fresh", "current", "latest", "web", "real-time", "external", "market", "competitor", "pricing", "affiliate"]
    for gap in gaps:
        if any(kw in gap.lower() for kw in web_keywords):
            return True
    return False
