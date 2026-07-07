#!/usr/bin/env python3
"""
Alpha Draft Engine — Internal draft generation for outside opinion/advice.

Produces structured drafts from Alpha's perspective BEFORE any web enrichment.
Core principle: Alpha is the outside opinion advisor. Not research-first, not command-first.
"""

import re
from datetime import datetime, timezone


def generate_alpha_draft(understanding, active_context=None):
    """
    Generate an Alpha internal draft for the given message understanding.
    Returns a draft dict with structured items.
    """
    intent = understanding.get("intent_family", "unknown")
    text = understanding.get("normalized_text", "")
    topic = understanding.get("raw_text", "")

    # Strip alpha prefix if present
    clean_topic = re.sub(r"^alpha\s+", "", topic).strip()
    clean_text = re.sub(r"^alpha\s+", "", text).strip()

    # --- Money opinion ---
    if intent in ("money_plan", "money_research"):
        return _draft_money_opinion(clean_text, clean_topic)

    # --- Client acquisition opinion ---
    if intent in ("client_acquisition", "client_research"):
        return _draft_client_opinion(clean_text, clean_topic)

    # --- Business strategy opinion ---
    if intent == "business_strategy":
        return _draft_strategy_opinion(clean_text, clean_topic)

    # --- Critique ---
    if intent == "critique":
        return _draft_critique(clean_text, clean_topic, active_context)

    # --- Compare ---
    if intent == "compare_options":
        return _draft_compare(clean_text, clean_topic, active_context)

    # --- Web research ---
    if intent == "web_research":
        return _draft_web_research(clean_text, clean_topic)

    # --- Opinion ---
    if intent == "opinion":
        return _draft_opinion(clean_text, clean_topic, active_context)

    # --- Default: outside perspective ---
    return _draft_outside_perspective(clean_text, clean_topic)


def _draft_money_opinion(text, topic):
    """Alpha outside opinion on money/revenue questions."""
    return {
        "role": "alpha",
        "intent_family": "money_plan",
        "topic": topic,
        "answer_mode": "outside_opinion",
        "summary": "Alpha Outside Opinion — Money Moves",
        "items": [
            {
                "index": 1,
                "title": "Fastest realistic move: close a readiness review today",
                "summary": "The fastest path to cash is not a new business idea — it is using the GoClear credit/funding readiness offer that already exists. A $97 readiness review with a warm lead is more realistic than broad 'make money online' strategies.",
                "score": 8.0,
                "why": "Direct path to cash. No new product. Already built. Warm outreach converts faster.",
                "time_to_execute": "today",
                "cost": "$0",
                "risk": ["Requires an active lead"],
                "next_action": "Identify the warmest lead and offer a readiness review today.",
            },
            {
                "index": 2,
                "title": "Use checklist + short call as the funnel",
                "summary": "A free Credit Readiness Checklist plus a 15-minute call is the fastest way to qualify leads. This is more realistic than building a course, writing an ebook, or waiting for affiliate revenue.",
                "score": 7.5,
                "why": "Low barrier. Builds trust fast. Converts to paid review.",
                "time_to_execute": "today",
                "cost": "$0",
                "risk": [],
                "next_action": "Share checklist and offer 3 free calls today.",
            },
            {
                "index": 3,
                "title": "Affiliates are backend, not first sale",
                "summary": "Credit monitoring and business banking affiliate programs are good backend monetization but should not be the primary same-day revenue strategy. Close the readiness review first, then introduce affiliates as ongoing value.",
                "score": 5.5,
                "why": "Backend monetization requires client trust. Not same-day cash without an existing relationship.",
                "time_to_execute": "this week",
                "cost": "$0",
                "risk": ["Compliance requirements for financial product referrals"],
                "next_action": "Research affiliate terms after closing first readiness review.",
            },
        ],
        "evidence_gaps": [
            "How many warm leads are in the pipeline?",
            "Is Stripe connected for payments?",
        ],
        "needs_external_evidence": False,
        "confidence": 0.85,
        "recommended_next_prompt": "turn this into a work order",
    }


def _draft_client_opinion(text, topic):
    """Alpha outside opinion on client acquisition."""
    return {
        "role": "alpha",
        "intent_family": "client_acquisition",
        "topic": topic,
        "answer_mode": "outside_opinion",
        "summary": "Alpha Outside Opinion — Client Acquisition",
        "items": [
            {
                "index": 1,
                "title": "Warm outreach beats cold outreach every time",
                "summary": "DM people you already know. Local business owners who need credit help. Skip the cold email templates.",
                "score": 7.5,
                "why": "Trust is already there. Conversion rate is 5-10x higher than cold.",
                "time_to_execute": "today",
                "cost": "$0",
                "risk": [],
                "next_action": "List 10 warm contacts and DM 3 today.",
            },
            {
                "index": 2,
                "title": "Free readiness call is the best lead qualifier",
                "summary": "15 minutes is enough to qualify. Do not over-invest time upfront.",
                "score": 7.0,
                "why": "Fast qualification. Low commitment for the prospect.",
                "time_to_execute": "today",
                "cost": "$0",
                "risk": [],
                "next_action": "Post availability for 3 free calls.",
            },
        ],
        "evidence_gaps": [],
        "needs_external_evidence": False,
        "confidence": 0.8,
        "recommended_next_prompt": "turn this into a work order",
    }


def _draft_strategy_opinion(text, topic):
    """Alpha outside opinion on business strategy."""
    return {
        "role": "alpha",
        "intent_family": "business_strategy",
        "topic": topic,
        "answer_mode": "outside_opinion",
        "summary": f"Alpha Outside Opinion — Strategy: {topic[:50]}",
        "items": [
            {
                "index": 1,
                "title": "Focus beats diversification at this stage",
                "summary": "Do not spread into 5 revenue streams. Master the readiness review first. Then expand.",
                "score": 7.5,
                "why": "Focus creates momentum. Diversification creates noise.",
                "time_to_execute": "N/A",
                "cost": "$0",
                "risk": [],
                "next_action": "Define the single most important revenue metric and track it daily.",
            },
        ],
        "evidence_gaps": [],
        "needs_external_evidence": False,
        "confidence": 0.75,
        "recommended_next_prompt": "turn this into a work order",
    }


def _draft_critique(text, topic, active_context=None):
    """Alpha critique — outside perspective on what could go wrong."""
    return {
        "role": "alpha",
        "intent_family": "critique",
        "topic": topic,
        "answer_mode": "critique",
        "summary": f"Alpha Critique: {topic[:60]}",
        "items": [
            {
                "index": 1,
                "title": "Key risk identification",
                "summary": f"Evaluating what could go wrong with: {topic[:100]}",
                "score": 6.0,
                "why": "Identifying risks before they materialize saves time and money.",
                "time_to_execute": "N/A",
                "cost": "$0",
                "risk": [],
                "next_action": "Address the highest-priority risk first.",
            },
        ],
        "evidence_gaps": [],
        "needs_external_evidence": False,
        "confidence": 0.7,
        "recommended_next_prompt": "turn this into a work order",
    }


def _draft_compare(text, topic, active_context=None):
    """Alpha comparison — outside perspective on options."""
    items = []
    if active_context and active_context.get("items"):
        for item in active_context["items"][:4]:
            items.append({
                "index": item["index"],
                "title": item.get("title", f"Option {item['index']}"),
                "summary": item.get("summary", ""),
                "score": item.get("score", 5),
                "why": f"Scored {item.get('score', 5)}/10. Alpha's outside view on fit and risk.",
                "time_to_execute": "N/A",
                "cost": "$0",
                "risk": item.get("risk", []),
                "next_action": item.get("next_action", ""),
            })
    if not items:
        items = [{"index": 1, "title": "No items to compare", "summary": "Run a search first.", "score": 0, "why": "", "time_to_execute": "", "cost": "", "risk": [], "next_action": ""}]

    return {
        "role": "alpha",
        "intent_family": "compare_options",
        "topic": topic,
        "answer_mode": "comparison",
        "summary": f"Alpha Comparison: {topic[:60]}",
        "items": items,
        "evidence_gaps": [],
        "needs_external_evidence": False,
        "confidence": 0.8,
        "recommended_next_prompt": "turn this into a work order",
    }


def _draft_web_research(text, topic):
    """Alpha draft that needs web research."""
    return {
        "role": "alpha",
        "intent_family": "web_research",
        "topic": topic,
        "answer_mode": "research_brief",
        "summary": f"Alpha research: {topic[:60]}",
        "items": [],
        "evidence_gaps": ["Fresh web data needed"],
        "needs_external_evidence": True,
        "confidence": 0.6,
        "recommended_next_prompt": "turn this into a work order",
    }


def _draft_opinion(text, topic, active_context=None):
    """Alpha general opinion."""
    return {
        "role": "alpha",
        "intent_family": "opinion",
        "topic": topic,
        "answer_mode": "outside_opinion",
        "summary": f"Alpha Opinion: {topic[:60]}",
        "items": [
            {
                "index": 1,
                "title": "Outside perspective",
                "summary": f"Alpha's take on: {topic[:100]}",
                "score": 6.5,
                "why": "Outside perspective adds dimension that internal thinking misses.",
                "time_to_execute": "N/A",
                "cost": "$0",
                "risk": [],
                "next_action": "Consider this perspective alongside operational reality.",
            },
        ],
        "evidence_gaps": [],
        "needs_external_evidence": False,
        "confidence": 0.7,
        "recommended_next_prompt": "turn this into a work order",
    }


def _draft_outside_perspective(text, topic):
    """Alpha default: outside perspective on whatever was asked."""
    return {
        "role": "alpha",
        "intent_family": "unknown",
        "topic": topic,
        "answer_mode": "outside_opinion",
        "summary": f"Alpha Perspective: {topic[:60]}",
        "items": [
            {
                "index": 1,
                "title": "Outside perspective on this topic",
                "summary": f"Alpha evaluates: {topic[:100]}",
                "score": 6.0,
                "why": "Fresh eyes catch what insiders miss.",
                "time_to_execute": "N/A",
                "cost": "$0",
                "risk": [],
                "next_action": "Consider this alongside your operational context.",
            },
        ],
        "evidence_gaps": [],
        "needs_external_evidence": False,
        "confidence": 0.65,
        "recommended_next_prompt": "turn this into a work order",
    }
