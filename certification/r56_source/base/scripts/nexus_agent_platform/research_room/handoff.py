"""Shadow-only proposed handoff; never calls production department assignment."""
from __future__ import annotations

from typing import Any

from .participants import append_message


def proposed_handoff(case: dict[str, Any]) -> dict[str, Any]:
    synthesis = case.get("final_synthesis") or {}
    handoff = {"kind": "PROPOSED_HANDOFF", "status": "PROPOSED",
        "target_department": synthesis.get("next_department"),
        "action_owner": synthesis.get("action_owner"),
        "package": synthesis, "shadow_mode": True}
    case["handoff"] = handoff
    history = case.setdefault("status_history", ["OPEN"])
    if "HANDED_OFF" not in history:
        history.append("HANDED_OFF")
    case["status"] = "COMPLETE"
    if "COMPLETE" not in history:
        history.append("COMPLETE")
    case["next_participant"] = "DONE"
    append_message(case, "RESEARCH_LEAD", "Shadow proposed handoff prepared; no production assignment was sent.", "PROPOSED_HANDOFF",
                   target=handoff["target_department"] or handoff["action_owner"])
    return handoff
