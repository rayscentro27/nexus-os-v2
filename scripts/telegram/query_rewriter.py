#!/usr/bin/env python3
"""
Query Rewriter — Rewrites user messages into effective search queries.

Never sends raw pronouns or vague phrases to Brave.
"""

import re


def rewrite_for_retrieval(text, active_context=None, selected_item=None, draft=None):
    """
    Rewrite user text into a useful Brave search query.
    Returns a clean, specific query string.
    """
    t = text.lower().strip()

    # --- Use pending action query if it exists ---
    # (caller should pass this via draft or active_context)

    # --- Use draft topic ---
    if draft and draft.get("topic"):
        topic = draft["topic"]
        topic = re.sub(r"^(alpha|hermes|nexus)\s+", "", topic).strip()
        for prefix in ["search the web for ", "search web for ", "research ", "look up ",
                        "find current ", "find latest ", "what are the best ",
                        "alpha research ", "hermes search the web for "]:
            if topic.startswith(prefix):
                topic = topic[len(prefix):].strip()
                break
        if len(topic) > 10:
            return _enrich_query(topic, active_context)

    # --- Use active context topic ---
    if active_context and active_context.get("topic"):
        topic = active_context["topic"]
        if len(topic) > 10:
            return _enrich_query(topic, active_context)

    # --- Use selected item ---
    if selected_item and selected_item.get("title"):
        return _enrich_query(selected_item["title"], active_context)

    # --- Rewrite the raw text ---
    # Strip agent prefixes
    t = re.sub(r"^(alpha|hermes|nexus)\s+", "", t).strip()

    # Strip research/search boilerplate
    for prefix in ["search the web for ", "search web for ", "research ", "look up ",
                    "find current ", "find latest ", "what are the best ",
                    "alpha research ", "hermes search the web for "]:
        if t.startswith(prefix):
            t = t[len(prefix):].strip()
            break

    # Remove pronouns and vague references
    t = re.sub(r"\b(this|that|it|the\s+one|these|those)\b", "", t).strip()
    t = re.sub(r"\b(research\s+deeper|look\s+deeper|go\s+deeper)\b", "", t).strip()

    if not t or len(t) < 5:
        # Fallback to active context
        if active_context and active_context.get("query"):
            return _enrich_query(active_context["query"], active_context)
        return "Nexus GoClear business strategy"

    return _enrich_query(t, active_context)


def _enrich_query(query, active_context=None):
    """Add relevant context keywords to make the query more specific."""
    q = query.lower()

    # Don't double-add context
    if any(kw in q for kw in ["goclear", "nexus", "credit readiness"]):
        return query

    # Add GoClear context for business/credit queries
    if any(kw in q for kw in ["client", "money", "revenue", "business", "credit", "affiliate",
                                "monetiz", "income", "sale", "pricing", "fund"]):
        return f"{query} GoClear credit readiness"

    return query
