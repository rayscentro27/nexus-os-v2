"""Canonical precedence and referent resolution for Nova's short context."""
from __future__ import annotations

import re
from typing import Any


_IMMEDIATE = re.compile(
    r"\b(?:that|it|this|what you just said|what you meant|summari[sz]e that|"
    r"explain that|make that shorter|shorten that|why was that)\b", re.I)
_CURRENT = re.compile(r"\b(?:what are you working on|what are you doing|what is happening|what's happening)(?:\s+right now|\s+now|\s+currently)?\b", re.I)
_RECENT_DONE = re.compile(r"\b(?:what did you just finish|what was the last mission|what did you complete|last completed mission)\b", re.I)
_WHY_COMPLETE = re.compile(r"\bwhy\b.*\b(?:complete|completed|considered complete|finished)\b", re.I)
_HISTORICAL_PROBLEMS = re.compile(r"\b(?:did|was|were|has|have)\b.*\b(?:mission|objective|it|that)\b.*\b(?:technical problems?|failures?|issues?|blocked|boundary)\b.*\b(?:before|prior to|eventually|ultimately|complete|completed)\b", re.I)
_CONTINUATION = re.compile(r"\b(?:continue|retry|update|delete|show me|keep working|keep going|resume|advance|what happened with)\b.*\b(?:that|it|case|job|project|file|note|result)\b", re.I)
_NEXT = re.compile(r"\b(?:what (?:would be )?a useful next step|what should we do next|what happens next|next step)\b", re.I)


def resolve_context(current_message: str, *, previous_turn: dict[str, Any] | None = None,
                    active_mission: dict[str, Any] | None = None,
                    recent_completed_mission: dict[str, Any] | None = None,
                    authoritative_mission_snapshot: dict[str, Any] | None = None,
                    thread_context: dict[str, Any] | None = None,
                    entity_lineage: dict[str, Any] | None = None,
                    long_term_memory: Any = None) -> dict[str, Any]:
    """Resolve references by explicit precedence; memory is last-resort only."""
    message = str(current_message or "").strip()
    previous_turn = previous_turn or {}
    active_mission = active_mission or {}
    recent_completed_mission = recent_completed_mission or {}
    authoritative_mission_snapshot = authoritative_mission_snapshot or recent_completed_mission
    thread_context = thread_context or {}
    entity_lineage = entity_lineage or {}

    if _CURRENT.search(message):
        if active_mission.get("mission_id"):
            resolved = active_mission
        elif str(active_mission.get("status") or "").upper() == "NO_ACTIVE_MISSION":
            resolved = {"status": "NO_ACTIVE_MISSION"}
        else:
            resolved = {"status": "CURRENT_STATE_UNKNOWN"}
        return _result("CURRENT_STATE", "ACTIVE_OPERATOR_MISSION", 3, resolved,
                       "Live Operator state answers right-now questions; completed history is separate.")
    if _RECENT_DONE.search(message):
        return _result("RECENT_COMPLETED_WORK", "MOST_RECENT_VERIFIED_COMPLETED_MISSION", 4,
                       recent_completed_mission or None, "Only a verified completed mission qualifies.")
    if (_WHY_COMPLETE.search(message) and previous_turn.get("assistant_text")
            and authoritative_mission_snapshot.get("success_verified")):
        return _result("COMPLETION_EXPLANATION", "PREVIOUS_ASSISTANT_TURN+AUTHORITATIVE_MISSION_SNAPSHOT", 2,
                       {"previous_turn": {"user_text": previous_turn.get("user_text"),
                                          "assistant_text": previous_turn.get("assistant_text"),
                                          "update_id": previous_turn.get("update_id")},
                        "mission_snapshot": authoritative_mission_snapshot},
                       "The immediate answer identifies the referent; verified mission evidence is authoritative for why it completed.")
    if _HISTORICAL_PROBLEMS.search(message) and authoritative_mission_snapshot.get("mission_id"):
        return _result("HISTORICAL_MISSION_EVENTS", "AUTHORITATIVE_MISSION_EVENT_HISTORY", 2,
                       {"previous_turn": {"user_text": previous_turn.get("user_text"),
                                          "assistant_text": previous_turn.get("assistant_text"),
                                          "update_id": previous_turn.get("update_id")},
                        "mission_snapshot": authoritative_mission_snapshot},
                       "Use event history only for the historical-problem question; terminal mission state remains authoritative for whether it completed.")
    if _CONTINUATION.search(message) and entity_lineage:
        return _result("ENTITY_CONTINUATION", "DURABLE_ENTITY_LINEAGE", 6,
                       entity_lineage, "Resolve the exact referenced entity from current conversation lineage.")
    if _IMMEDIATE.search(message) and previous_turn.get("assistant_text"):
        return _result("IMMEDIATE_REFERENT", "PREVIOUS_ASSISTANT_TURN", 2,
                       {"user_text": previous_turn.get("user_text"),
                        "assistant_text": previous_turn.get("assistant_text"),
                        "update_id": previous_turn.get("update_id")},
                       "Immediate dialog outranks Operator history and long-term memory.")
    if _NEXT.search(message):
        if active_mission.get("mission_id"):
            return _result("THREAD_REFERENT", "ACTIVE_OPERATOR_MISSION", 3, active_mission,
                           "Next step is grounded in live active work.")
        if thread_context:
            return _result("THREAD_REFERENT", "CURRENT_THREAD_CONTEXT", 5, thread_context,
                           "Use the current thread objective before historical memory.")
        return _result("THREAD_REFERENT", "OPTIONAL_SUGGESTION", 8, None,
                       "No active objective resolved; any next step must be clearly framed as a suggestion.")
    if thread_context:
        return _result("THREAD_CONTEXT", "CURRENT_THREAD_CONTEXT", 5, thread_context,
                       "Current thread context is available.")
    if entity_lineage:
        return _result("ENTITY_CONTEXT", "DURABLE_ENTITY_LINEAGE", 6, entity_lineage,
                       "Exact durable entity lineage is available.")
    if long_term_memory:
        return _result("MEMORY_REFERENT", "LONG_TERM_MEMORY", 7, long_term_memory,
                       "Memory is used only after immediate, live, thread, and lineage context fail.")
    return _result("GENERAL", "GENERAL_KNOWLEDGE", 8, None, "No higher-priority referent resolved.")


def _result(intent: str, source: str, priority: int, referent: Any, why: str) -> dict[str, Any]:
    entity_type = entity_id = None
    if isinstance(referent, dict):
        for key, kind in (("case_id", "RESEARCH_CASE"), ("job_id", "RESEARCH_JOB"),
                          ("project_id", "RESEARCH_PROJECT"), ("note_id", "NOTE"),
                          ("file_id", "FILE"), ("mission_id", "OPERATOR_MISSION")):
            if referent.get(key):
                entity_type, entity_id = kind, str(referent[key])
                break
    return {"intent": intent, "reference_type": intent, "resolved_referent": referent,
            "resolved_entity_type": entity_type, "resolved_entity_id": entity_id,
            "context_source": source, "context_priority": priority,
            "confidence": 1.0 if referent else 0.95, "ambiguous": False, "why": why}


def render_context_block(snapshot: dict[str, Any]) -> str:
    """Bounded, inspectable authority contract supplied before every Hermes turn."""
    import json
    payload = {key: snapshot.get(key) for key in (
        "message_id", "current_text", "previous_user_text", "previous_assistant_text",
        "active_mission_id", "active_mission", "last_completed_mission_id",
        "last_completed_mission", "thread_objective", "resolved_referent",
        "resolution_source", "resolution_priority", "reference_type", "authoritative_mission_snapshot")}
    return (
        "NOVA CONTEXT AUTHORITY SNAPSHOT (authoritative for this turn; do not let older session or personal memory override it).\n"
        "Precedence: current user message > immediately previous exchange > live active Operator mission > "
        "most recent verified completed mission > current thread > exact lineage > long-term/session memory > general knowledge.\n"
        "For 'that/it/this/what you just said', use PREVIOUS_ASSISTANT_TEXT exactly. For 'right now', use ACTIVE_MISSION; "
        "if absent, state there is no active mission and do not revive a completed/stale blocked record. For 'next step', "
        "ground it in active mission/thread; if no active mission exists, clearly label the recommendation as a suggestion, "
        "not current assigned work. Historical memory is background, never current state. The authoritative mission row and verified success evidence define current/final state; older boundary, recovery, capability-gap, and failure events are history only. Keep historical failures distinct from the final outcome.\nSNAPSHOT_JSON="
        + json.dumps(payload, ensure_ascii=False, default=str)[:10000]
    )
