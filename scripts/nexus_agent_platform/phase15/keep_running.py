"""Phase 15 runtime continuation policy.

Normal empty, duplicate, or no-change cycles are not runtime failures. Only
explicit integrity, authorization, or repeated execution failures escalate.
This policy is descriptive and never changes launchd state by itself.
"""
from __future__ import annotations

KEEP_RUNNING_STATES = frozenset({
    "NO_CHANGE", "ZERO_OPPORTUNITIES", "DUPLICATE_ONLY", "NO_WORK",
    "SUCCESS", "PARTIAL", "BOUNDED_DEGRADED", "WAITING", "DEFERRED",
})
STOP_OR_ESCALATE_STATES = frozenset({
    "AUTHORITY_VIOLATION", "INTEGRITY_FAILURE", "SECURITY_FAILURE",
    "RLS_VIOLATION", "REPEATED_CRITICAL_FAILURE",
})
POLICY = {
    "version": "phase15-keep-running-v1",
    "rationale": (
        "Normal operating outcomes preserve state and await the next bounded "
        "schedule. Stop or escalate only for explicit safety, integrity, or "
        "repeated critical failure conditions."
    ),
}


def disposition(state: str) -> str:
    normalized = str(state).strip().upper()
    if normalized in STOP_OR_ESCALATE_STATES:
        return "STOP_OR_ESCALATE"
    if normalized in KEEP_RUNNING_STATES:
        return "KEEP_RUNNING"
    return "REVIEW_REQUIRED"
