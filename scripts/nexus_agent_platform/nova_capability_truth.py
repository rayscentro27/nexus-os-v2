"""Current capability truth for the canonical Admin Hermes runtime.

Documentation, installed packages, and the separate Hermes profile are not
evidence that a capability is callable from this HTTP runtime.
"""
from __future__ import annotations

from typing import Any


def build_admin_runtime_capability_truth() -> dict[str, Any]:
    return {
        "runtime": "hermes_agent_0.20.6",
        "executor": "Oracle Hermes 0.20.6 -> nova_nexus -> nexus_mcp_remote",
        "nexus_mcp": {
            "documented": True, "installed": True, "configured": True,
            "active_connected": True, "proven_this_runtime": True,
            "available_to_admin_nova": True, "reason": "Current Admin transport invokes Hermes profile nova_nexus with nexus_mcp_remote.",
        },
        "google_mcp": {
            "documented": True, "installed": True, "configured": True,
            "active_connected": False, "proven_this_runtime": False,
            "available_to_admin_nova": False, "reason": "Google MCP is not exposed by the direct Admin Nova request path.",
        },
        "gmail_read": {"active_connected": False, "proven_this_runtime": False, "available_to_admin_nova": False, "reason": "No authorized Gmail reader is exposed in this runtime."},
        "calendar_read": {"active_connected": False, "proven_this_runtime": False, "available_to_admin_nova": False, "reason": "No authorized Calendar reader is exposed in this runtime."},
        "drive_read": {"active_connected": False, "proven_this_runtime": False, "available_to_admin_nova": False, "reason": "No authorized Drive reader is exposed in this runtime."},
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
