"""Nexus Research Room v1: Research Room / Research Chat engine."""
from __future__ import annotations

from .room_manager import (
    ResearchRoomManager,
    ResearchRoomStore,
    RoomSource,
    RoomMessage,
    CompactResearchBrief,
    generate_compact_brief,
    calculate_preliminary_score,
    converse_with_alpha,
    AUTONOMOUS_RESEARCH_OFF,
)

__all__ = [
    "ResearchRoomManager",
    "ResearchRoomStore",
    "RoomSource",
    "RoomMessage",
    "CompactResearchBrief",
    "generate_compact_brief",
    "calculate_preliminary_score",
    "converse_with_alpha",
    "AUTONOMOUS_RESEARCH_OFF",
]
