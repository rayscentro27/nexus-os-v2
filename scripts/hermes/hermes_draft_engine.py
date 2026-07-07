#!/usr/bin/env python3
"""
Hermes Draft Engine — Internal draft generation for operational/business questions.

Produces structured drafts BEFORE any web enrichment.
Core principle: Internal plan first. Web enrichment second.
"""

import re
from datetime import datetime, timezone


def generate_hermes_draft(understanding, active_context=None):
    """
    Generate a Hermes internal draft for the given message understanding.
    Returns a draft dict with structured items.
    """
    intent = understanding.get("intent_family", "unknown")
    text = understanding.get("normalized_text", "")
    topic = understanding.get("raw_text", "")

    # --- Money plan ---
    if intent == "money_plan":
        return _draft_money_plan(text, topic)

    # --- Client acquisition ---
    if intent == "client_acquisition":
        return _draft_client_acquisition(text, topic)

    # --- Business strategy ---
    if intent == "business_strategy":
        return _draft_business_strategy(text, topic)

    # --- Implementation ---
    if intent == "implementation_plan":
        return _draft_implementation(text, topic)

    # --- Opinion ---
    if intent == "opinion":
        return _draft_opinion(text, topic, active_context)

    # --- Critique ---
    if intent == "critique":
        return _draft_critique(text, topic, active_context)

    # --- Compare ---
    if intent == "compare_options":
        return _draft_compare(text, topic, active_context)

    # --- Web research ---
    if intent == "web_research":
        return _draft_web_research(text, topic)

    # --- Money research ---
    if intent == "money_research":
        return _draft_money_research(text, topic)

    # --- Client research ---
    if intent == "client_research":
        return _draft_client_research(text, topic)

    # --- System status ---
    if intent == "system_status":
        return _draft_system_status(text, topic)

    # --- Fallback: generic operational advice ---
    return _draft_generic_operational(text, topic)


def _draft_money_plan(text, topic):
    """Draft a same-day money plan for GoClear/Nexus."""
    return {
        "role": "hermes",
        "intent_family": "money_plan",
        "topic": topic,
        "answer_mode": "operator_plan",
        "summary": "Hermes Money Plan — Today",
        "items": [
            {
                "index": 1,
                "title": "Sell the $97 GoClear Credit & Funding Readiness Review today",
                "summary": "Close one readiness review today. This is the fastest path to same-day cash. Use manual payment link or invoice if Stripe is not ready.",
                "score": 8.5,
                "why": "Direct path to cash. No new product needed. Already built.",
                "time_to_execute": "today",
                "cost": "$0 additional",
                "risk": ["Requires an existing lead or warm contact"],
                "next_action": "DM or call one warm lead with the readiness review offer.",
            },
            {
                "index": 2,
                "title": "Offer 3 free 15-minute readiness calls today",
                "summary": "Short consultation calls to qualify leads and close one into the $97 review.",
                "score": 7.5,
                "why": "Low barrier entry. Converts to paid review. Builds pipeline.",
                "time_to_execute": "today",
                "cost": "$0",
                "risk": ["Time investment of ~45 min for 3 calls"],
                "next_action": "Post availability in local business groups or DM 3 warm contacts.",
            },
            {
                "index": 3,
                "title": "Use Credit Readiness Checklist as same-day lead magnet",
                "summary": "Share the free checklist to capture leads who need credit/funding help.",
                "score": 7.0,
                "why": "Generates inbound leads. Low effort to distribute.",
                "time_to_execute": "today",
                "cost": "$0",
                "risk": ["Lead quality varies"],
                "next_action": "Post checklist in 2-3 local business Facebook groups.",
            },
            {
                "index": 4,
                "title": "DM warm/local business contacts with readiness audit offer",
                "summary": "Direct outreach to people you already know. No-guarantee free audit offer.",
                "score": 6.5,
                "why": "Warm outreach converts better than cold. Local businesses need credit help.",
                "time_to_execute": "today",
                "cost": "$0",
                "risk": ["May feel pushy if not framed as helpful"],
                "next_action": "Send 5 personalized DMs with the readiness audit offer.",
            },
            {
                "index": 5,
                "title": "Set up credit monitoring / business banking affiliates as backend",
                "summary": "Add affiliate revenue streams after the core readiness review is sold.",
                "score": 5.0,
                "why": "Backend monetization. Not same-day cash unless a client is ready to sign up today.",
                "time_to_execute": "this week",
                "cost": "$0",
                "risk": ["Requires client trust before recommending financial products"],
                "next_action": "Research top 3 affiliate programs and apply.",
            },
        ],
        "evidence_gaps": [
            "Current pipeline status — how many warm leads are active?",
            "Stripe connection status — can we process payments today?",
        ],
        "needs_external_evidence": False,
        "confidence": 0.85,
        "recommended_next_prompt": "turn this into a work order",
    }


def _draft_client_acquisition(text, topic):
    """Draft client acquisition plan."""
    return {
        "role": "hermes",
        "intent_family": "client_acquisition",
        "topic": topic,
        "answer_mode": "operator_plan",
        "summary": "Hermes Client Acquisition Plan",
        "items": [
            {
                "index": 1,
                "title": "Offer free 15-minute readiness calls",
                "summary": "Short consultations to qualify and convert leads.",
                "score": 8.0,
                "why": "Low barrier, high conversion potential.",
                "time_to_execute": "today",
                "cost": "$0",
                "risk": [],
                "next_action": "Post availability and DM 3 warm contacts.",
            },
            {
                "index": 2,
                "title": "Share Credit Readiness Checklist in local groups",
                "summary": "Lead magnet for inbound interest.",
                "score": 7.0,
                "why": "Generates warm leads organically.",
                "time_to_execute": "today",
                "cost": "$0",
                "risk": [],
                "next_action": "Post in 2-3 business groups.",
            },
            {
                "index": 3,
                "title": "Close one $97 readiness review",
                "summary": "Convert a qualified lead into a paid review.",
                "score": 7.5,
                "why": "Direct revenue from existing pipeline.",
                "time_to_execute": "today",
                "cost": "$0",
                "risk": [],
                "next_action": "Follow up with most engaged lead.",
            },
        ],
        "evidence_gaps": ["Pipeline count", "Lead temperature"],
        "needs_external_evidence": False,
        "confidence": 0.8,
        "recommended_next_prompt": "turn this into a work order",
    }


def _draft_business_strategy(text, topic):
    """Draft business strategy advice."""
    return {
        "role": "hermes",
        "intent_family": "business_strategy",
        "topic": topic,
        "answer_mode": "operator_plan",
        "summary": f"Hermes Strategy: {topic[:60]}",
        "items": [
            {
                "index": 1,
                "title": "Focus on readiness review pipeline",
                "summary": "Core revenue driver. Build pipeline before expanding.",
                "score": 7.5,
                "why": "Proven offer, direct path to revenue.",
                "time_to_execute": "this week",
                "cost": "$0",
                "risk": [],
                "next_action": "Review current pipeline and identify top 3 prospects.",
            },
            {
                "index": 2,
                "title": "Connect Stripe for automated payments",
                "summary": "Remove manual payment friction.",
                "score": 7.0,
                "why": "Enables self-serve checkout and scales.",
                "time_to_execute": "today",
                "cost": "$0",
                "risk": [],
                "next_action": "Complete Stripe test mode setup.",
            },
            {
                "index": 3,
                "title": "Build content funnel for inbound leads",
                "summary": "Checklist + social posts + readiness calls.",
                "score": 6.5,
                "why": "Compounds over time. Low cost.",
                "time_to_execute": "this week",
                "cost": "$0",
                "risk": [],
                "next_action": "Draft 3 social posts about credit readiness.",
            },
        ],
        "evidence_gaps": [],
        "needs_external_evidence": False,
        "confidence": 0.75,
        "recommended_next_prompt": "turn this into a work order",
    }


def _draft_implementation(text, topic):
    """Draft implementation plan."""
    return {
        "role": "hermes",
        "intent_family": "implementation_plan",
        "topic": topic,
        "answer_mode": "operator_plan",
        "summary": f"Hermes Implementation: {topic[:60]}",
        "items": [
            {
                "index": 1,
                "title": "Break into concrete steps",
                "summary": "Define the smallest next action that moves this forward.",
                "score": 7.0,
                "why": "Actionable steps beat vague plans.",
                "time_to_execute": "today",
                "cost": "$0",
                "risk": [],
                "next_action": "List the 3 smallest next steps.",
            },
        ],
        "evidence_gaps": [],
        "needs_external_evidence": False,
        "confidence": 0.7,
        "recommended_next_prompt": "turn this into a work order",
    }


def _draft_opinion(text, topic, active_context=None):
    """Draft Hermes operational opinion."""
    summary_parts = []
    if active_context and active_context.get("topic"):
        summary_parts.append(f"Context: {active_context['topic'][:40]}")
    summary_parts.append(f"Hermes opinion on: {topic[:60]}")

    return {
        "role": "hermes",
        "intent_family": "opinion",
        "topic": topic,
        "answer_mode": "operator_plan",
        "summary": " | ".join(summary_parts),
        "items": [
            {
                "index": 1,
                "title": "Operational assessment",
                "summary": f"Hermes evaluates: {topic[:100]}",
                "score": 6.5,
                "why": "Based on operational context and GoClear priorities.",
                "time_to_execute": "N/A",
                "cost": "$0",
                "risk": [],
                "next_action": "Review and decide on next step.",
            },
        ],
        "evidence_gaps": [],
        "needs_external_evidence": False,
        "confidence": 0.7,
        "recommended_next_prompt": "turn this into a work order",
    }


def _draft_critique(text, topic, active_context=None):
    """Draft Hermes critique."""
    return {
        "role": "hermes",
        "intent_family": "critique",
        "topic": topic,
        "answer_mode": "operator_plan",
        "summary": f"Hermes critique: {topic[:60]}",
        "items": [
            {
                "index": 1,
                "title": "Risk and gap analysis",
                "summary": f"Evaluating risks and gaps in: {topic[:100]}",
                "score": 6.0,
                "why": "Identifying blind spots before they become problems.",
                "time_to_execute": "N/A",
                "cost": "$0",
                "risk": [],
                "next_action": "Address identified gaps.",
            },
        ],
        "evidence_gaps": [],
        "needs_external_evidence": False,
        "confidence": 0.7,
        "recommended_next_prompt": "turn this into a work order",
    }


def _draft_compare(text, topic, active_context=None):
    """Draft comparison from active context items."""
    items = []
    if active_context and active_context.get("items"):
        for item in active_context["items"][:4]:
            items.append({
                "index": item["index"],
                "title": item.get("title", f"Option {item['index']}"),
                "summary": item.get("summary", ""),
                "score": item.get("score", 5),
                "why": f"Scored {item.get('score', 5)}/10 based on available evidence.",
                "time_to_execute": "N/A",
                "cost": "$0",
                "risk": item.get("risk", []),
                "next_action": item.get("next_action", ""),
            })
    if not items:
        items = [{"index": 1, "title": "No items to compare", "summary": "Run a search first.", "score": 0, "why": "", "time_to_execute": "", "cost": "", "risk": [], "next_action": ""}]

    return {
        "role": "hermes",
        "intent_family": "compare_options",
        "topic": topic,
        "answer_mode": "operator_plan",
        "summary": f"Comparison: {topic[:60]}",
        "items": items,
        "evidence_gaps": [],
        "needs_external_evidence": False,
        "confidence": 0.8,
        "recommended_next_prompt": "turn this into a work order",
    }


def _draft_web_research(text, topic):
    """Draft that explicitly needs web research."""
    return {
        "role": "hermes",
        "intent_family": "web_research",
        "topic": topic,
        "answer_mode": "research_brief",
        "summary": f"Research requested: {topic[:60]}",
        "items": [],
        "evidence_gaps": ["Fresh web data needed for this query"],
        "needs_external_evidence": True,
        "confidence": 0.6,
        "recommended_next_prompt": "turn this into a work order",
    }


def _draft_money_research(text, topic):
    """Draft money research that needs web enrichment."""
    return {
        "role": "hermes",
        "intent_family": "money_research",
        "topic": topic,
        "answer_mode": "research_brief",
        "summary": f"Money research: {topic[:60]}",
        "items": [
            {
                "index": 1,
                "title": "Start with GoClear readiness review as base",
                "summary": "Use existing offer as foundation. Web research for additional channels.",
                "score": 7.0,
                "why": "Already built. Direct path to cash.",
                "time_to_execute": "today",
                "cost": "$0",
                "risk": [],
                "next_action": "Enrich with web research on additional revenue channels.",
            },
        ],
        "evidence_gaps": ["Current affiliate programs", "Local market rates", "Competitor pricing"],
        "needs_external_evidence": True,
        "confidence": 0.6,
        "recommended_next_prompt": "turn this into a work order",
    }


def _draft_client_research(text, topic):
    """Draft client research that needs web enrichment."""
    return {
        "role": "hermes",
        "intent_family": "client_research",
        "topic": topic,
        "answer_mode": "research_brief",
        "summary": f"Client research: {topic[:60]}",
        "items": [],
        "evidence_gaps": ["Current client acquisition channels", "Local market data"],
        "needs_external_evidence": True,
        "confidence": 0.6,
        "recommended_next_prompt": "turn this into a work order",
    }


def _draft_system_status(text, topic):
    """Draft system status."""
    return {
        "role": "hermes",
        "intent_family": "system_status",
        "topic": topic,
        "answer_mode": "operator_plan",
        "summary": "System status requested",
        "items": [],
        "evidence_gaps": [],
        "needs_external_evidence": False,
        "confidence": 0.9,
        "recommended_next_prompt": None,
    }


def _draft_generic_operational(text, topic):
    """Draft generic operational advice as last resort before fallback."""
    return {
        "role": "hermes",
        "intent_family": "unknown",
        "topic": topic,
        "answer_mode": "operator_plan",
        "summary": f"Hermes guidance: {topic[:60]}",
        "items": [
            {
                "index": 1,
                "title": "Clarify the question",
                "summary": "I want to make sure I give you the most useful answer.",
                "score": 5.0,
                "why": "Ambiguous queries need clarification.",
                "time_to_execute": "N/A",
                "cost": "$0",
                "risk": [],
                "next_action": "Try: 'hermes what should we do next' or 'alpha what do you think about...' or 'search the web for...'",
            },
        ],
        "evidence_gaps": [],
        "needs_external_evidence": False,
        "confidence": 0.4,
        "recommended_next_prompt": None,
    }
