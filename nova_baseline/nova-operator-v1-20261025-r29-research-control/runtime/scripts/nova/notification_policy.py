"""Canonical policy for Nova's proactive, Ray-facing notifications.

This module contains no transport and no scheduler.  It makes routine
operational state internal-only, fingerprints material state semantically, and
renders concise executive messages.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any

IGNORED_FIELDS = {
    "audit_id", "receipt_id", "timestamp", "cycle_id", "window_id",
    "heartbeat_id", "run_id", "delivery_id", "created_at", "updated_at",
}

ROUTINE_KINDS = {
    "CYCLE", "HEARTBEAT", "REFRESH", "UNCHANGED", "ROUTINE", "NO_ACTION",
    "PRODUCTIVITY_AUDIT", "HEALTHY_AUDIT", "SCHEDULER_WAKE",
}

def event_type(event: dict[str, Any]) -> str:
    return str(event.get("event_type") or event.get("kind") or "UNKNOWN").upper()

def material_state(event: dict[str, Any]) -> dict[str, Any]:
    """Return only stable fields that can represent a meaningful state."""
    preferred = (
        "event_type", "kind", "severity", "affected_system", "material_status",
        "status", "state", "blocker", "required_action", "project_id",
        "client_id", "goal", "department", "source", "failure_class",
    )
    state = {key: event.get(key) for key in preferred if event.get(key) not in (None, "", [])}
    state["event_type"] = event_type(event)
    # Explicitly exclude volatile identifiers even when callers pass a broad
    # event object through this helper.
    return {key: value for key, value in state.items() if key not in IGNORED_FIELDS}

def event_fingerprint(event: dict[str, Any]) -> str:
    payload = json.dumps(material_state(event), sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]

def classify_event(event: dict[str, Any]) -> str:
    if event.get("test") is True:
        return "MATERIAL"
    kind = event_type(event)
    if kind in {"SUPERVISOR_UNHEALTHY", "RESEARCH_NOT_REAL", "REQUIRED_PATH_FAILED",
                "RAY_REQUIRED", "APPROVAL_REQUIRED", "SAFETY_EVENT", "RECOVERY",
                "PRODUCTIVITY_STALL", "CRITICAL_FAILURE"}:
        return "CRITICAL"
    if kind in {"TERMINAL_CERTIFICATION", "GOAL_ADVANCED", "GOAL_COMPLETED",
                "BLOCKER_REPAIRED", "CAPABILITY_PROVEN", "DEPARTMENT_MILESTONE",
                "SIGNIFICANT_RESEARCH", "BUSINESS_EVENT", "MATERIAL_COMPLETION"}:
        return "MATERIAL"
    if kind in ROUTINE_KINDS:
        return "ROUTINE"
    return "SUPPRESSED"

def _clean(value: Any) -> str:
    text = str(value or "").strip()
    text = re.sub(r"(?:audit_id|receipt_id|run_id|cycle_id|timestamp)\s*[=:]\s*[^\s,;]+", "", text, flags=re.I)
    text = re.sub(r"(?:/Users/|/var/|data/|reports/)[^\s]+", "the persisted internal record", text)
    return re.sub(r"\s+", " ", text).strip()

def executive_message(event: dict[str, Any], severity: str) -> str:
    title = _clean(event.get("title")) or ("Nexus needs your attention" if severity == "CRITICAL" else "Nexus update")
    happened = _clean(event.get("summary")) or _clean(event.get("what_happened")) or "A material company event was verified."
    why = _clean(event.get("why_it_matters"))
    needs = _clean(event.get("required_action"))
    next_step = _clean(event.get("next")) or ("Nexus is continuing safe bounded work." if severity != "CRITICAL" else "Nexus is preserving the state and continuing safe recovery where possible.")
    lines = [title, "", "What happened:", f"• {happened}"]
    if why:
        lines += ["", "Why it matters:", f"• {why}"]
    if needs:
        lines += ["", "Needs you:", f"• {needs}"]
    lines += ["", "Next:", f"• {next_step}"]
    return "\n".join(lines)[:3800]
