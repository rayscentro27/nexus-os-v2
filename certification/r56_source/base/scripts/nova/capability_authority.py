"""Canonical capability authority vocabulary for Nova's runtime view.

Availability, authorization, runtime health, and action authority are separate
facts. Missing quota/limit rows never determine whether a capability exists.
"""
from __future__ import annotations

from typing import Any

CAPABILITY_STATES = {
    "AVAILABLE", "AVAILABLE_WITH_CONTROLS", "DEGRADED", "UNAVAILABLE",
    "NOT_INSTALLED", "NOT_AUTHORIZED",
}


def capability_record(*, name: str, installed: bool, configured: bool,
                      authorized: bool | None, runtime_health: str,
                      read_authority: str, write_authority: str,
                      cost_class: str, consequence_class: str, boundary: str,
                      available: bool | None = None,
                      last_known_good: bool | None = None,
                      last_verified_at: str | None = None,
                      last_error: str | None = None) -> dict[str, Any]:
    """Normalize capability facts without conflating availability and health."""
    health = str(runtime_health or "UNKNOWN").upper()
    if not installed:
        state = "NOT_INSTALLED"
    elif authorized is False:
        state = "NOT_AUTHORIZED"
    elif available is False or not configured:
        state = "UNAVAILABLE"
    elif health in {"DEGRADED", "FAIL", "ERROR", "UNAVAILABLE"}:
        state = "DEGRADED"
    elif read_authority != "NONE" or write_authority != "NONE":
        state = "AVAILABLE_WITH_CONTROLS"
    else:
        state = "AVAILABLE"
    record = {
        "name": name, "installed": bool(installed), "available": state in {"AVAILABLE", "AVAILABLE_WITH_CONTROLS"},
        "authorized": authorized, "runtime_health": health,
        "read_authority": read_authority, "write_authority": write_authority,
        "cost_class": cost_class, "consequence_class": consequence_class,
        "boundary": boundary, "last_known_good": last_known_good,
        "last_verified_at": last_verified_at or "UNKNOWN", "last_error": last_error,
        "status": state,
    }
    if state not in CAPABILITY_STATES:
        raise ValueError(f"INVALID_CAPABILITY_STATE:{state}")
    return record

