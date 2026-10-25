"""Alpha agent — independent outside-thinking advisor.

Alpha has its own LangGraph graph, SOUL instructions, capability
registry, context store, and Telegram worker.  Completely separate
from Hermes — no shared conversational memory.
"""

from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from nexus_agent_platform.adapters.graph_adapter import GraphAdapter
from nexus_agent_platform.adapters.otel_adapter import OtelAdapter
from nexus_agent_platform.state import AgentState
from nexus_agent_platform.capabilities.registry import CapabilityRegistry
from nexus_agent_platform.runtime.paths import get_nexus_repo_root
from nexus_agent_platform.context.resolver import get_active_context, update_active_context

log = logging.getLogger(__name__)

AGENT_ID = "alpha"

SOUL = """You are Alpha — an independent outside-thinking advisor.
You research opportunities, evaluate markets, and give honest
outside perspective.  You are NOT the operator — you advise the
operator.  You challenge assumptions, identify risks, and
propose opportunities.  Your responses are concise, well-sourced,
and actionable.  You do not execute business operations."""


# ─── Mode Detection ─────────────────────────────────────────

_MODE_PATTERNS = {
    "TRADING_ANALYSIS": r"\b(forex|trading|stocks?|invest(?:ment|ing)|market|oanda|practice\s+trading|currency|crypto)\b",
    "LIVE_RESEARCH": r"\b(research|find\s+out|look\s+up|search|investigate|what(?:'s| is)\s+current|latest\s+news)\b",
    "BUSINESS_OPPORTUNITY": r"\b(opportunity|opportunities|business\s+ideas?|make\s+money|revenue|income|side\s+hustle|grant|grants)\b",
    "CHALLENGE_HERMES": r"\b(challenge|disagree|wrong|push\s+back|second\s+opinion|alternative\s+view|what\s+do\s+you\s+think\s+about\s+hermes)\b",
    "RESEARCH_STATUS": r"\b(what\s+are\s+you\s+researching|research\s+status|what(?:'s| is)\s+new|current\s+research)\b",
    "INDEPENDENT_OPINION": r"\b(what\s+do\s+you\s+think\s+about|opinion\s+(on|of|about)|your\s+thoughts\s+on|how\s+do\s+you\s+feel\s+about|review)\b",
    "CONVERSATION": r"\b(hello|hi|good\s+(morning|afternoon|evening)|hey|how\s+are\s+you|do\s+you\s+(drink|like|want|need|have)|what\s+do\s+you\s+think\s+about\s+(coffee|tea|food))\b",
}

# Research-triggering modes (only these call Brave)
_RESEARCH_MODES = {"LIVE_RESEARCH", "BUSINESS_OPPORTUNITY"}


def _detect_mode(text: str) -> str:
    lower = text.lower().strip()
    for mode, pattern in _MODE_PATTERNS.items():
        if re.search(pattern, lower):
            return mode
    # Default: if substantive (>15 chars), treat as research
    if len(text.strip()) > 15:
        return "BUSINESS_OPPORTUNITY"
    return "CONVERSATION"


# ─── Graph Node Functions ───────────────────────────────────

def _classify_intent(state: AgentState) -> AgentState:
    """Detect Alpha mode from user message."""
    mode = _detect_mode(state.user_message)
    state.intent = mode
    state.metadata["alpha_mode"] = mode
    state.metadata["will_research"] = mode in _RESEARCH_MODES
    return state


def _research_decision(state: AgentState) -> AgentState:
    """Decide whether to call external research providers."""
    mode = state.intent or "CONVERSATION"
    should_research = mode in _RESEARCH_MODES

    state.metadata["research_decision"] = {
        "mode": mode,
        "should_research": should_research,
        "reason": f"Mode {mode} {'triggers' if should_research else 'does not trigger'} research",
    }

    if not should_research:
        state.metadata["skip_research"] = True
        state.metadata["skip_reason"] = f"Mode={mode} is conversation/opinion — no Brave call"

    return state


def _execute_research(state: AgentState) -> AgentState:
    """Execute research via Brave if decision says to."""
    if state.metadata.get("skip_research"):
        return state

    mode = state.intent or "BUSINESS_OPPORTUNITY"
    query = state.user_message

    try:
        sys_path_backup = list(__import__("sys").path)
        repo_root = os.path.join(os.path.dirname(__file__), "..", "..")
        __import__("sys").path.insert(0, os.path.join(repo_root, "scripts", "hermes"))
        from hermes_web_search import web_search
        results = web_search(query, max_results=6)
        __import__("sys").path = sys_path_backup

        state.search_results = results if isinstance(results, list) else []
        state.metadata["research_completed"] = True
        state.metadata["result_count"] = len(state.search_results)
    except Exception as exc:
        log.warning("Alpha research failed: %s", exc)
        state.metadata["research_completed"] = False
        state.metadata["research_error"] = str(exc)

    return state


def _synthesize_findings(state: AgentState) -> AgentState:
    """Synthesize research results or compose opinion."""
    mode = state.intent or "CONVERSATION"

    if mode == "CONVERSATION":
        state.assistant_response = _compose_conversation(state.user_message)
    elif mode == "INDEPENDENT_OPINION":
        state.assistant_response = _compose_opinion(state.user_message, state.search_results)
    elif mode == "TRADING_ANALYSIS":
        state.assistant_response = _compose_trading_analysis(state.user_message, state.search_results)
    elif mode == "LIVE_RESEARCH":
        state.assistant_response = _compose_research(state.user_message, state.search_results)
    elif mode == "BUSINESS_OPPORTUNITY":
        state.assistant_response = _compose_opportunities(state.user_message, state.search_results)
    elif mode == "CHALLENGE_HERMES":
        state.assistant_response = _compose_challenge(state.user_message, state.active_context)
    elif mode == "RESEARCH_STATUS":
        state.assistant_response = _compose_research_status()
    else:
        state.assistant_response = _compose_conversation(state.user_message)

    return state


def _compose_advisory(state: AgentState) -> AgentState:
    """Final composition — update context."""
    if state.intent:
        update_active_context(AGENT_ID, "last_mode", state.intent, ttl=600)
    if state.search_results:
        update_active_context(AGENT_ID, "last_research_results", state.search_results[:3], ttl=1800)
    return state


# ─── Response Composers ─────────────────────────────────────

def _compose_conversation(text: str) -> str:
    lower = text.lower()
    if any(w in lower for w in ["hello", "hi", "good morning", "good afternoon", "good evening", "hey"]):
        from zoneinfo import ZoneInfo
        now = datetime.now(ZoneInfo("America/Phoenix"))
        greeting = "Good afternoon" if 12 <= now.hour < 17 else ("Good morning" if now.hour < 12 else "Good evening")
        return f"{greeting}! I'm Alpha — your outside-thinking advisor. What's on your mind?"
    if "coffee" in lower:
        return "I don't drink coffee — I'm an AI advisor. But I can research the best coffee shops if you want! What can I help with?"
    return "I'm Alpha. I research opportunities, evaluate markets, and give honest outside perspective. What would you like to explore?"


def _compose_opinion(text: str, results: list) -> str:
    topic = re.sub(r"(what do you think about|opinion on|your thoughts on|how do you feel about|review)", "", text, flags=re.IGNORECASE).strip()
    if not topic:
        return "What topic would you like my opinion on?"
    if results:
        sources = "\n".join(f"- {r.get('title', r.get('url', 'source'))}" for r in results[:3])
        return (
            f"Here's my take on {topic}:\n\n"
            f"Based on current sources:\n{sources}\n\n"
            "I see both opportunities and risks here. Want me to dig deeper?"
        )
    return f"My opinion on {topic}: It's worth watching, but I'd want more data before making a call. Want me to research it?"


def _compose_trading_analysis(text: str, results: list) -> str:
    topic = re.sub(r"(what do you think about|opinion on|your thoughts on|forex|trading|stocks?|invest(?:ment|ing)|market|oanda|practice\s+trading|currency|crypto)", "", text, flags=re.IGNORECASE).strip()
    if "oanda" in text.lower() or "practice" in text.lower():
        return (
            "For practice trading, Oanda is our current platform. "
            "I can research current forex conditions or specific pairs if you'd like.\n\n"
            "What's your risk appetite and timeline?"
        )
    if results:
        return f"Here's my analysis on {topic or 'the market'}:\n\nCurrent conditions suggest careful positioning. Want me to run a deeper research pass?"
    return f"I can research {topic or 'current market conditions'} for you. Want me to look into specific pairs or instruments?"


def _compose_research(text: str, results: list) -> str:
    if not results:
        return f"I attempted research on: {text[:80]}\n\nNo strong results found. Try a more specific query."
    sources = "\n".join(f"- {r.get('title', 'source')}: {r.get('url', '')}" for r in results[:5])
    return f"Here's what I found:\n\n{sources}\n\nWant me to synthesize these into actionable insights?"


def _compose_opportunities(text: str, results: list) -> str:
    if not results:
        return f"I looked into: {text[:80]}\n\nI did not find strong results. Try a more specific query."
    items = []
    for r in results[:3]:
        title = r.get("title", "Opportunity")
        url = r.get("url", "")
        snippet = r.get("snippet", r.get("description", ""))
        items.append(f"**{title}**\n{snippet}\n{url}")
    return (
        "Here are the current opportunities I found:\n\n"
        + "\n\n".join(items)
        + "\n\nWant me to score these or dig deeper into any?"
    )


def _compose_challenge(text: str, context: dict) -> str:
    return (
        "I'm challenging Hermes' recommendation from an outside perspective.\n\n"
        "Without seeing the specific recommendation, my general approach is:\n"
        "1. What assumptions is Hermes making?\n"
        "2. What data is the recommendation based on?\n"
        "3. What are the risks if the assumptions are wrong?\n"
        "4. Is there a contrarian view worth considering?\n\n"
        "Share the recommendation and I'll give you a structured challenge."
    )


def _compose_research_status() -> str:
    try:
        status_path = get_nexus_repo_root() / "data" / "runtime" / "alpha_telegram_status.json"
        with open(status_path) as f:
            data = json.load(f)
        mission = data.get("current_mission", "none")
        stage = data.get("mission_stage", "unknown")
        return f"Current research mission: {mission}\nStage: {stage}\nNo active research in progress." if stage == "COMPLETED" else f"Mission {mission} is at stage: {stage}"
    except Exception:
        return "Research status unavailable. No active research."


# ─── Graph Builder ──────────────────────────────────────────

def build_alpha_graph() -> GraphAdapter:
    """Build and compile the Alpha LangGraph."""
    graph = GraphAdapter(agent_id=AGENT_ID)
    graph.add_node("classify_intent", _classify_intent)
    graph.add_node("research_decision", _research_decision)
    graph.add_node("execute_research", _execute_research)
    graph.add_node("synthesize_findings", _synthesize_findings)
    graph.add_node("compose_advisory", _compose_advisory)

    graph.add_edge("classify_intent", "research_decision")
    graph.add_edge("research_decision", "execute_research")
    graph.add_edge("execute_research", "synthesize_findings")
    graph.add_edge("synthesize_findings", "compose_advisory")

    graph.set_entry_point("classify_intent")
    graph.set_finish_point("compose_advisory")
    return graph.compile()


# ─── Singleton Instances ────────────────────────────────────

_graph: GraphAdapter | None = None
_capabilities: CapabilityRegistry | None = None
_otel: OtelAdapter | None = None


def get_alpha_graph() -> GraphAdapter:
    global _graph
    if _graph is None:
        _graph = build_alpha_graph()
    return _graph


def get_alpha_capabilities() -> CapabilityRegistry:
    global _capabilities
    if _capabilities is None:
        _capabilities = CapabilityRegistry(AGENT_ID)
        _capabilities.register("research", "Brave web search", lambda: None)
        _capabilities.register("opinion", "Independent opinion", lambda: None)
        _capabilities.register("challenge", "Challenge Hermes recommendation", lambda: None)
    return _capabilities


def get_alpha_otel() -> OtelAdapter:
    global _otel
    if _otel is None:
        _otel = OtelAdapter(AGENT_ID)
    return _otel
