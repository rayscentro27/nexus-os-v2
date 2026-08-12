"""Conversation-scoped governed intent resolution.

Binds Ray's explicit words to EXACTLY ONE persisted pending approval per chat.
Ambiguity (multiple matching approvals, or non-explicit phrasing) never executes.

This is the deterministic validation layer the Telegram conversation flow and
the Nova graph use. It does NOT rely on phrase regex alone: it requires persisted
approval records scoped to the requester/approver, plus explicit phrasing.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Optional

from nexus_agent_platform.governed import approvals as approval_mod
from nexus_agent_platform.governed.action_registry import action_exists
from nexus_agent_platform.governed.approvals import (
    EXPLICIT_APPROVE_PHRASES,
    EXPLICIT_REJECT_PHRASES,
)


def _normalize(text: str) -> str:
    return " ".join((text or "").strip().lower().split())


def is_explicit_approve(text: str) -> bool:
    norm = _normalize(text)
    if not norm:
        return False
    for phrase in EXPLICIT_APPROVE_PHRASES:
        if phrase in norm:
            return True
    return norm in {"yes", "ok", "okay", "yeah", "sure", "go"}


def is_explicit_reject(text: str) -> bool:
    norm = _normalize(text)
    if not norm:
        return False
    for phrase in EXPLICIT_REJECT_PHRASES:
        if phrase in norm:
            return True
    return False


def pending_for_approver(approver: str = "ray") -> List[Dict[str, Any]]:
    return approval_mod.get_pending_approvals(requested_for=approver, include_self=False)


def pending_for_chat(chat_id: int) -> List[Dict[str, Any]]:
    """Pending approvals tied to this chat's conversation context (all for ray)."""
    return approval_mod.get_pending_approvals(requested_for="ray", include_self=False)


def _scoped_pending(chat_id: int, subset: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """Pending approvals for this chat, optionally filtered to a subset of approval_ids."""
    all_pending = pending_for_chat(chat_id)
    if subset:
        allowed = set(subset or [])
        all_pending = [a for a in all_pending if a.get("approval_id") in allowed]
    return all_pending


MULTIPLE_AMBIGUOUS = "multiple"
NO_MATCH = "no_match"
NOT_EXPLICIT = "not_explicit"
NONE_PENDING = "none_pending"


class ApprovalResolution:
    def __init__(
        self,
        verdict: str,
        approval: Optional[Dict[str, Any]] = None,
        message: str = "",
        resolution: Optional[Dict[str, Any]] = None,
        candidates: Optional[List[Dict[str, Any]]] = None,
    ):
        self.verdict = verdict  # 'resolved' | 'ambiguous' | 'none' | 'invalid'
        self.approval = approval
        self.message = message
        self.resolution = resolution
        self.candidates = candidates or []


def resolve_approval_intent(
    text: str,
    *,
    chat_id: int,
    decision: str = "approve",  # 'approve' | 'reject'
    approval_ids: Optional[List[str]] = None,
) -> ApprovalResolution:
    """Resolve Ray's explicit intent against persisted pending approvals.

    Rules:
      - exactly one matching pending approval + explicit phrasing -> resolve
      - multiple matching pending approvals  -> ambiguous (ask which one)
      - explicit phrase but no matching approval -> none/invalid
      - non-explicit phrase (e.g. "looks good") -> invalid (never executes)
    """
    explicit = is_explicit_approve(text) if decision == "approve" else is_explicit_reject(text)
    if not explicit:
        return ApprovalResolution(
            "invalid",
            message=(
                "That does not look like an explicit approval. "
                "Please say \"approve it\" or confirm with the approval ID."
            ),
        )

    candidates = _scoped_pending(chat_id, approval_ids)
    if not candidates:
        return ApprovalResolution(
            "none",
            message="There is no pending approval matching that request.",
        )

    if len(candidates) > 1:
        return ApprovalResolution(
            "ambiguous",
            message="You have multiple pending approvals. Which one do you approve?",
            candidates=candidates,
        )

    approval = candidates[0]
    resolution = approval_mod.resolve_approval(
        approval["approval_id"],
        decision,
        resolved_by="ray",
    )
    if resolution.get("status") == "ok":
        return ApprovalResolution(
            "resolved",
            approval=approval,
            message="Approval resolved.",
            resolution=resolution,
        )
    return ApprovalResolution(
        "invalid",
        approval=approval,
        message=resolution.get("status", "unable to resolve"),
        resolution=resolution,
    )


def describe_pending(approval: Dict[str, Any]) -> str:
    return (
        f"{approval.get('approval_id')} — {approval.get('action_summary')} "
        f"(risk {approval.get('risk_level')})"
    )


def fmt_ambiguity(candidates: List[Dict[str, Any]]) -> str:
    lines = ["I see more than one action waiting for your approval. Please pick one:"]
    for i, a in enumerate(candidates, start=1):
        lines.append(f"{i}. {describe_pending(a)}")
    return "\n".join(lines)


def latest_action_context(chat_id: int) -> Dict[str, Any]:
    """Bounded recent governed context for a chat: last approvals + work orders."""
    approvals = pending_for_chat(chat_id)
    return {
        "pending_approvals": approvals,
        "pending_count": len(approvals),
    }