"""Nexus OS v2 — centralized AI agent permission checks (server-side enforcement).

Loads an agent's row from agent_registry and answers permission questions. Scripts MUST use
this before creating jobs/approvals or taking actions. The frontend uses summaries only.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "social"))
from _supabase import get, q  # noqa: E402

_CACHE: dict[str, dict] = {}


def load_agent(agent_key: str) -> dict | None:
    if agent_key in _CACHE:
        return _CACHE[agent_key]
    st, rows = get("agent_registry", f"agent_key=eq.{q(agent_key)}&limit=1")
    agent = rows[0] if isinstance(rows, list) and rows else None
    if agent:
        _CACHE[agent_key] = agent
    return agent


def is_client_agent(agent: dict) -> bool:
    return agent.get("agent_class") == "client_agent"


def is_hermes_advisor(agent: dict) -> bool:
    return agent.get("agent_class") == "hermes_advisor"


def can_use_web(agent: dict) -> bool:
    return bool(agent.get("web_access_allowed"))


def can_use_external_api(agent: dict) -> bool:
    return bool(agent.get("external_api_allowed"))


def can_create_job(agent: dict, job_type: str = "") -> bool:
    return bool(agent.get("can_create_jobs"))


def can_create_approval(agent: dict, approval_type: str = "") -> bool:
    return bool(agent.get("can_create_approvals"))


def can_execute_action(agent: dict, action_type: str = "") -> bool:
    return bool(agent.get("can_execute_actions"))


def requires_approval(agent: dict, action_type: str) -> bool:
    needs = agent.get("requires_approval_for") or []
    return action_type in needs or "any_external_action" in needs or "any_public_claim" in needs


def explain_boundary(agent_key: str) -> dict:
    a = load_agent(agent_key)
    if not a:
        return {"agent_key": agent_key, "found": False}
    return {
        "agent_key": agent_key, "found": True, "name": a.get("name"),
        "agent_class": a.get("agent_class"), "audience_type": a.get("audience_type"),
        "web_access_allowed": a.get("web_access_allowed"),
        "external_api_allowed": a.get("external_api_allowed"),
        "can_create_jobs": a.get("can_create_jobs"),
        "can_create_approvals": a.get("can_create_approvals"),
        "can_execute_actions": a.get("can_execute_actions"),
        "requires_approval_for": a.get("requires_approval_for"),
        "cost_policy": a.get("cost_policy"), "compliance_policy": a.get("compliance_policy"),
        "allowed_data_sources": a.get("allowed_data_sources"),
    }


if __name__ == "__main__":
    import json
    key = sys.argv[1] if len(sys.argv) > 1 else "hermes_advisor"
    print(json.dumps(explain_boundary(key), indent=2))
