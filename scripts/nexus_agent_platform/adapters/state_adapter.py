"""State adapter — manages LangGraph state serialization.

Provides ``AgentState`` which wraps LangGraph state dict management
and adds Nexus-specific fields (agent_id, mission_id, context, etc.).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class AgentState:
    """State object passed through LangGraph nodes.

    This is the Nexus-owned state schema — LangGraph nodes read and
    write to this, not directly to a raw dict.  The adapter serializes
    it to/from dicts for LangGraph's ``StateGraph``.
    """

    # --- Core fields ---
    agent_id: str = ""
    mission_id: str = ""
    thread_id: str = ""

    # --- Conversation ---
    messages: List[Dict[str, str]] = field(default_factory=list)
    user_message: str = ""
    assistant_response: str = ""

    # --- Intent / context ---
    intent: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    active_context: Dict[str, Any] = field(default_factory=dict)

    # --- Research ---
    search_results: List[Dict[str, Any]] = field(default_factory=list)
    research_synthesis: str = ""

    # --- Capability / tools ---
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    tool_results: List[Dict[str, Any]] = field(default_factory=list)

    # --- Slots ---
    slots: Dict[str, Any] = field(default_factory=dict)
    slot_fill_target: Optional[str] = None

    # --- Tracing ---
    trace_id: str = ""
    span_id: str = ""

    # --- Metadata ---
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "mission_id": self.mission_id,
            "thread_id": self.thread_id,
            "messages": list(self.messages),
            "user_message": self.user_message,
            "assistant_response": self.assistant_response,
            "intent": self.intent,
            "context": dict(self.context),
            "active_context": dict(self.active_context),
            "search_results": list(self.search_results),
            "research_synthesis": self.research_synthesis,
            "tool_calls": list(self.tool_calls),
            "tool_results": list(self.tool_results),
            "slots": dict(self.slots),
            "slot_fill_target": self.slot_fill_target,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentState":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    @staticmethod
    def state_schema() -> Dict[str, Any]:
        """Return a LangGraph-compatible TypedDict-style schema.

        Used by ``StateGraph(AgentState.state_schema())``.
        """
        from typing import TypedDict

        class _Schema(TypedDict, total=False):
            agent_id: str
            mission_id: str
            thread_id: str
            messages: List[Dict[str, str]]
            user_message: str
            assistant_response: str
            intent: Optional[str]
            context: Dict[str, Any]
            active_context: Dict[str, Any]
            search_results: List[Dict[str, Any]]
            research_synthesis: str
            tool_calls: List[Dict[str, Any]]
            tool_results: List[Dict[str, Any]]
            slots: Dict[str, Any]
            slot_fill_target: Optional[str]
            trace_id: str
            span_id: str
            created_at: str
            updated_at: str
            metadata: Dict[str, Any]

        return _Schema
