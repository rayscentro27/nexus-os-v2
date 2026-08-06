"""Telegram-to-Platform integration bridge.

Connects the existing Telegram workers to the Agent Platform.
When feature flags are OFF, returns None so callers fall through
to the legacy router unchanged.
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

log = logging.getLogger("nexus_agent_platform.integration")

# Add parent scripts dir to path for platform imports
_SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "..")
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)


def _flags() -> Dict[str, bool]:
    from nexus_agent_platform.flags import status
    return status()


def _platform_enabled() -> bool:
    return _flags().get("NEXUS_AGENT_PLATFORM_ENABLED", False)


def _hermes_graph_enabled() -> bool:
    return _platform_enabled() and _flags().get("NEXUS_HERMES_LANGGRAPH_ENABLED", False)


def _alpha_graph_enabled() -> bool:
    return _platform_enabled() and _flags().get("ALPHA_LANGGRAPH_ENABLED", False)


def _legacy_fallback_enabled() -> bool:
    return _flags().get("LEGACY_HERMES_ROUTER_FALLBACK_ENABLED", True)


def _otel_enabled() -> bool:
    return _flags().get("LANGFUSE_TRACING_ENABLED", False)


# ─── Hermes Platform Path ────────────────────────────────────

def try_hermes_platform(
    text: str,
    mission: Optional[Dict] = None,
    chat_id: Optional[int] = None,
    update_id: Optional[int] = None,
) -> Optional[str]:
    """Attempt to process through the Hermes Platform graph.

    Returns the response string if the platform handled it,
    or None if the caller should fall through to legacy routing.
    """
    if not _hermes_graph_enabled():
        return None

    try:
        from nexus_agent_platform.platform import Platform
        from nexus_agent_platform.state import AgentState
        from nexus_agent_platform.agents import (
            get_hermes_graph, get_hermes_capabilities, get_hermes_otel, HERMES_SOUL,
        )
        from nexus_agent_platform.context.resolver import get_active_context, load_context
        from nexus_agent_platform.missions.mission import Mission as PlatformMission

        # Build request context
        mission_id = mission.get("mission_id", "") if mission else ""
        ray_chat_masked = _mask_chat(chat_id)

        # Load agent context
        ctx = load_context("hermes")
        active = get_active_context("hermes")

        # Build state
        state = AgentState(
            agent_id="hermes",
            mission_id=mission_id,
            user_message=text,
            context=ctx,
            active_context=active,
            metadata={
                "source": "telegram",
                "chat_id_masked": ray_chat_masked,
                "update_id": update_id,
                "soul": HERMES_SOUL,
                "ray_authorized": True,
            },
        )

        # Run through graph
        graph = get_hermes_graph()
        result = graph.invoke(state)

        # Record trace if otel enabled
        if _otel_enabled():
            otel = get_hermes_otel()
            trace_metadata = {
                "mission_id": mission_id,
                "intent": result.intent,
                "agent": "nexus_hermes",
                "update_id": update_id,
                "conversation_epoch": result.metadata.get("conversation_epoch", 0),
            }
            # Add front-brain metadata when available
            if result.metadata.get("front_brain_mode"):
                trace_metadata["selected_mode"] = result.metadata["front_brain_mode"]
                trace_metadata["selected_capability"] = result.metadata.get("front_brain_capability")
                trace_metadata["front_brain_confidence"] = result.metadata.get("front_brain_confidence", 0)
                trace_metadata["front_brain_reason"] = result.metadata.get("front_brain_reason", "")
            trace_metadata["capability_used"] = result.metadata.get("capability_used")
            trace_metadata["model_used"] = result.metadata.get("model_used")
            trace_metadata["model_provider"] = result.metadata.get("model_provider")

            otel.record_generation(
                name=f"hermes_mission_{mission_id}",
                model=result.metadata.get("model_used", "langgraph"),
                input_text=text[:200],
                output_text=(result.assistant_response or "")[:200],
                metadata=trace_metadata,
            )
            otel.flush()

        response = result.assistant_response or ""
        if response:
            log.info("Hermes platform handled mission %s (intent=%s)", mission_id, result.intent)
            return response

        # Graph returned empty — fall through
        log.warning("Hermes platform returned empty for mission %s — falling through", mission_id)
        _record_fallback(mission, "empty_graph_response")
        return None

    except Exception as exc:
        log.error("Hermes platform error for mission %s: %s", mission.get("mission_id", "?") if mission else "?", exc)
        _record_fallback(mission, f"platform_error: {exc}")
        if not _legacy_fallback_enabled():
            return "I encountered a system error. The legacy fallback is disabled. Please try again."
        return None


# ─── Alpha Platform Path ─────────────────────────────────────

def try_alpha_platform(
    text: str,
    mission: Optional[Dict] = None,
    chat_id: Optional[int] = None,
    update_id: Optional[int] = None,
) -> Optional[str]:
    """Attempt to process through the Alpha Platform graph.

    Returns the response string if the platform handled it,
    or None if the caller should fall through to legacy routing.
    """
    if not _alpha_graph_enabled():
        return None

    try:
        from nexus_agent_platform.platform import Platform
        from nexus_agent_platform.state import AgentState
        from nexus_agent_platform.agents.alpha import (
            get_alpha_graph, get_alpha_capabilities, get_alpha_otel, AGENT_ID,
        )
        from nexus_agent_platform.context.resolver import get_active_context, load_context

        mission_id = mission.get("mission_id", "") if mission else ""

        # Load Alpha context (separate from Hermes)
        ctx = load_context("alpha")
        active = get_active_context("alpha")

        state = AgentState(
            agent_id="alpha",
            mission_id=mission_id,
            user_message=text,
            context=ctx,
            active_context=active,
            metadata={
                "source": "telegram",
                "chat_id_masked": _mask_chat(chat_id),
                "update_id": update_id,
                "separate_from_hermes": True,
                "no_client_pii": True,
            },
        )

        graph = get_alpha_graph()
        result = asyncio.run(graph.ainvoke(state))

        if _otel_enabled():
            otel = get_alpha_otel()
            otel.record_generation(
                name=f"alpha_mission_{mission_id}",
                model="langgraph",
                input_text=text[:200],
                output_text=(result.assistant_response or "")[:200],
                metadata={"mission_id": mission_id, "intent": result.intent},
            )
            otel.flush()

        response = result.assistant_response or ""
        if response:
            log.info("Alpha platform handled mission %s (intent=%s)", mission_id, result.intent)
            return response

        log.warning("Alpha platform returned empty for mission %s — falling through", mission_id)
        return None

    except Exception as exc:
        log.error("Alpha platform error for mission %s: %s", mission.get("mission_id", "?") if mission else "?", exc)
        return None


# ─── Helpers ─────────────────────────────────────────────────

def _mask_chat(chat_id: Optional[int]) -> str:
    text = str(chat_id or "")
    if len(text) <= 4:
        return "***"
    return f"{text[:2]}***{text[-2:]}"


def _record_fallback(mission: Optional[Dict], reason: str) -> None:
    if not mission:
        return
    mission["fallback_used"] = True
    mission["fallback_reason"] = reason
    mission.setdefault("metadata", {})["platform_fallback"] = {
        "reason": reason,
        "at": datetime.now(timezone.utc).isoformat(),
    }
