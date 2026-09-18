"""Current capability truth for the canonical Admin Hermes runtime.

Documentation, installed packages, and the separate Hermes profile are not
evidence that a capability is callable from this HTTP runtime.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any
import json


def _google_health() -> dict[str, Any]:
    """Return redacted Google health from the latest governed probe."""
    report = Path(__file__).resolve().parents[2] / "reports/certification/nexus_calendar_authorization_latest.json"
    data: dict[str, Any] = {}
    try:
        data = json.loads(report.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        pass
    status = str(data.get("status") or "NOT_PROVEN")
    active = status == "GOOGLE_WORKSPACE_READ_VERIFIED"
    reason = {
        "GOOGLE_WORKSPACE_READ_VERIFIED": "Latest bounded read-only probe verified the Google Workspace grant.",
        "GOOGLE_TOKEN_REFRESH_FAILED": "Google credentials are present but the latest refresh failed; reauthorization is required before calls are claimable.",
        "GOOGLE_SCOPE_MISMATCH": "Google credentials require scope reauthorization before the requested read is claimable.",
        "GOOGLE_REFRESH_TOKEN_NOT_CONFIGURED": "No Google refresh token is configured in the canonical credential store.",
    }.get(status, "Google MCP is configured but has not been proven active in this runtime.")
    return {
        "documented": True, "installed": True, "configured": True,
        "active_connected": active, "proven_this_runtime": active,
        "available_to_admin_nova": active,
        "health_status": status, "reason": reason,
        "read_only": True,
    }


def build_admin_runtime_capability_truth() -> dict[str, Any]:
    google = _google_health()
    google_read = {
        "active_connected": google["active_connected"],
        "proven_this_runtime": google["proven_this_runtime"],
        "available_to_admin_nova": google["available_to_admin_nova"],
        "reason": google["reason"],
    }
    return {
        "runtime": "hermes_agent_0.20.6",
        "executor": "Oracle Hermes 0.20.6 -> nova_nexus -> nexus_mcp_remote",
        "nexus_mcp": {
            "documented": True, "installed": True, "configured": True,
            "active_connected": True, "proven_this_runtime": True,
            "available_to_admin_nova": True, "reason": "Current Admin transport invokes Hermes profile nova_nexus with nexus_mcp_remote.",
        },
        "google_mcp": google,
        "gmail_read": google_read,
        "calendar_read": google_read,
        "drive_read": google_read,
        "public_research": {"active_connected": True, "proven_this_runtime": True, "available_to_admin_nova": True, "mode": "bounded_read_only"},
        "bounded_mission_creation": {"active_connected": False, "proven_this_runtime": False, "available_to_admin_nova": False, "reason": "Governed intake exists, but direct Nova cannot claim mission creation."},
    }


def capability_truth_for_prompt() -> str:
    data = build_admin_runtime_capability_truth()
    return (
        "CURRENT ADMIN NOVA RUNTIME CAPABILITY TRUTH (authoritative for this turn):\n"
        f"- Nexus MCP: active={data['nexus_mcp']['active_connected']}; available_to_admin_nova={data['nexus_mcp']['available_to_admin_nova']}. {data['nexus_mcp']['reason']}\n"
        f"- Google MCP: active={data['google_mcp']['active_connected']}; available_to_admin_nova={data['google_mcp']['available_to_admin_nova']}. {data['google_mcp']['reason']}\n"
        f"- Gmail read: available_to_admin_nova={data['gmail_read']['available_to_admin_nova']}. {data['gmail_read']['reason']}\n"
        f"- Calendar read: available_to_admin_nova={data['calendar_read']['available_to_admin_nova']}. {data['calendar_read']['reason']}\n"
        f"- Drive read: available_to_admin_nova={data['drive_read']['available_to_admin_nova']}. {data['drive_read']['reason']}\n"
        "Rule: documented, installed, or configured does not mean active or callable. Never infer a connected tool from repository text or Hermes history."
    )
