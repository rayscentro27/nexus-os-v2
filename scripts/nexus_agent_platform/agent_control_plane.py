"""Deny-by-default Nexus agent, connector, skill and environment authorization.

This control plane validates identities and authority. It never invokes tools,
providers, credentials, agents, or workflows. Existing governed executors remain
responsible for those actions.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
AGENTS_PATH = ROOT / "configs/nexus_agent_control_plane.json"
SKILLS_PATH = ROOT / "configs/nexus_skill_registry.json"
CONNECTORS_PATH = ROOT / "configs/connector_registry.json"
ENVIRONMENTS_PATH = ROOT / "configs/nexus_execution_environment_registry.json"
MODELS_PATH = ROOT / "configs/nexus_model_profile_registry.json"


class AuthorizationDenied(PermissionError):
    """A requested identity or capability is not explicitly authorized."""


def _load(path: Path, key: str) -> dict[str, dict[str, Any]]:
    try:
        rows = json.loads(path.read_text(encoding="utf-8"))[key]
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise AuthorizationDenied(f"CONTROL_PLANE_REGISTRY_UNAVAILABLE:{path.name}") from exc
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        identity = row.get("agent_id") or row.get("bot_id") or row.get("skill_id") or row.get("connector_id") or row.get("environment_id") or row.get("profile_id")
        if not identity or identity in result:
            raise AuthorizationDenied(f"CONTROL_PLANE_REGISTRY_INVALID:{path.name}")
        result[identity] = row
    return result


def _identities() -> dict[str, dict[str, dict[str, Any]]]:
    agent_doc = json.loads(AGENTS_PATH.read_text(encoding="utf-8"))
    agents = _load(AGENTS_PATH, "domain_agents")
    agents.update(_load(AGENTS_PATH, "microbots"))
    return {
        "agents": agents,
        "skills": _load(SKILLS_PATH, "skills"),
        "connectors": _load(CONNECTORS_PATH, "connectors"),
        "environments": _load(ENVIRONMENTS_PATH, "environments"),
        "models": _load(MODELS_PATH, "profiles"),
        "default_deny": {"value": bool(agent_doc.get("default_deny", True))},
    }


def public_registry_snapshot() -> dict[str, Any]:
    """Return identity metadata only; never resolve or serialize credentials."""
    data = _identities()
    safe = {}
    for group in ("agents", "skills", "connectors", "environments", "models"):
        safe[group] = []
        for row in data[group].values():
            safe[group].append({k: v for k, v in row.items() if k not in {"credential_value", "secret", "token", "api_key", "access_key", "secret_access_key"}})
    return safe


def authorize(*, agent_id: str, bot_id: str | None = None, skill_id: str | None = None,
              connector_id: str | None = None, environment_id: str | None = None,
              model_profile: str | None = None, runtime_health: dict[str, str] | None = None) -> dict[str, Any]:
    data = _identities()
    agent = data["agents"].get(agent_id)
    if not agent or agent.get("status") == "DEFINED_NOT_ACTIVE":
        raise AuthorizationDenied("AGENT_UNAVAILABLE")
    bot = data["agents"].get(bot_id) if bot_id else None
    if bot_id and (not bot or bot.get("domain") != agent_id and bot.get("domain") != agent.get("agent_id")):
        # Domain lead callers may authorize their own registered bot explicitly.
        if not bot or bot.get("domain") != agent_id:
            raise AuthorizationDenied("BOT_NOT_REGISTERED_FOR_AGENT")
    if skill_id:
        skill = data["skills"].get(skill_id)
        allowed = (bot or agent).get("allowed_skills", [])
        if skill is None or skill_id not in allowed:
            raise AuthorizationDenied("SKILL_NOT_ALLOWED")
        if skill.get("status") not in {"REGISTERED", "ACTIVE"}:
            raise AuthorizationDenied("SKILL_UNAVAILABLE")
    if connector_id:
        connector = data["connectors"].get(connector_id)
        allowed = (bot or agent).get("allowed_connectors", [])
        if connector is None or connector_id not in allowed:
            raise AuthorizationDenied("CONNECTOR_NOT_ALLOWED")
        if connector.get("status") not in {"ACTIVE", "AVAILABLE", "LIVE_CERTIFIED", "AVAILABLE_LIMITED", "PRACTICE_ONLY", "REGISTERED"}:
            raise AuthorizationDenied("CONNECTOR_UNAVAILABLE")
        if connector_id in (bot or agent).get("forbidden_connectors", []):
            raise AuthorizationDenied("CONNECTOR_FORBIDDEN")
    if environment_id:
        env = data["environments"].get(environment_id)
        allowed = (bot or agent).get("allowed_execution_environments", [])
        if env is None or environment_id not in allowed:
            raise AuthorizationDenied("ENVIRONMENT_NOT_ALLOWED")
        if environment_id in (bot or agent).get("forbidden_environments", []):
            raise AuthorizationDenied("ENVIRONMENT_FORBIDDEN")
        if env.get("status") not in {"ACTIVE", "LIVE_CERTIFIED", "AVAILABLE_NOW"}:
            raise AuthorizationDenied("ENVIRONMENT_UNAVAILABLE")
        if (runtime_health or {}).get(environment_id) not in {"HEALTHY", "LIVE_CERTIFIED", "AVAILABLE", "PASS"}:
            raise AuthorizationDenied("ENVIRONMENT_HEALTH_UNVERIFIED")
    if model_profile:
        profile = data["models"].get(model_profile)
        allowed = (bot or agent).get("allowed_model_profiles", [])
        if bot and bot.get("model_required") is False and model_profile != "NO_MODEL":
            raise AuthorizationDenied("NO_MODEL_BOT_CANNOT_CALL_MODEL")
        if profile is None or model_profile not in allowed:
            raise AuthorizationDenied("MODEL_PROFILE_NOT_ALLOWED")
        if profile.get("status") not in {"ACTIVE_NO_MODEL", "ACTIVE"} and model_profile == "NO_MODEL":
            raise AuthorizationDenied("MODEL_PROFILE_UNAVAILABLE")
        if bot and bot.get("model_required") is True and model_profile == "NO_MODEL":
            raise AuthorizationDenied("MODEL_PROFILE_REQUIRED")
    return {"status": "AUTHORIZED", "agent_id": agent_id, "bot_id": bot_id,
            "skill_id": skill_id, "connector_id": connector_id,
            "environment_id": environment_id, "model_profile": model_profile}


def select_environment(*, allowed: list[str], preferred: list[str], fallbacks: list[str],
                       registry: list[dict[str, Any]] | None = None,
                       runtime_health: dict[str, str] | None = None) -> dict[str, Any]:
    """Select only a healthy explicitly allowed environment; fallback is opt-in."""
    if registry is None:
        registry = list(_identities()["environments"].values())
    by_id = {row.get("environment_id"): row for row in registry}
    for candidate in [*preferred, *fallbacks]:
        if candidate not in allowed:
            continue
        row = by_id.get(candidate)
        if not row or row.get("status") not in {"ACTIVE", "LIVE_CERTIFIED", "AVAILABLE_NOW"}:
            continue
        observed_health = (runtime_health or {}).get(candidate)
        if observed_health not in {"HEALTHY", "LIVE_CERTIFIED", "AVAILABLE", "PASS"}:
            continue
        return {"status": "SELECTED", "environment_id": candidate,
                "selection_class": "PREFERRED" if candidate in preferred else "ALLOWED_FALLBACK"}
    return {"status": "UNAVAILABLE", "error_code": "NO_HEALTHY_ALLOWED_ENVIRONMENT"}


def validate_bot_contract(bot: dict[str, Any]) -> None:
    """Reject provider pinning in bot contracts; model resolution is delegated."""
    forbidden = {"provider", "model", "model_id", "api_key", "credential_value"}
    if forbidden.intersection(bot):
        raise AuthorizationDenied("BOT_MUST_REQUEST_MODEL_PROFILE_ONLY")
    if bot.get("model_required") and not bot.get("model_profile"):
        raise AuthorizationDenied("MODEL_PROFILE_REQUIRED")
    if not bot.get("model_required") and bot.get("model_profile") != "NO_MODEL":
        raise AuthorizationDenied("NO_MODEL_BOT_PROFILE_INVALID")
    for key in ("max_model_calls", "max_input_tokens", "max_output_tokens", "max_cost_usd", "max_runtime_seconds", "max_retries"):
        if not isinstance(bot.get(key), (int, float)) or bot[key] < 0:
            raise AuthorizationDenied(f"BOT_RESOURCE_BOUND_INVALID:{key}")


def enforce_resource_budget(*, actual_cost_usd: float, max_cost_usd: float,
                            elapsed_seconds: float, max_runtime_seconds: float) -> None:
    if actual_cost_usd > max_cost_usd or elapsed_seconds > max_runtime_seconds:
        raise AuthorizationDenied("RESOURCE_BUDGET_EXCEEDED")


def resolve_model_profile(*, profile_id: str, agent_id: str, bot_id: str | None = None) -> dict[str, Any]:
    """Ask the existing central Model Manager to resolve a profile; keep route details private."""
    authorize(agent_id=agent_id, bot_id=bot_id, model_profile=profile_id)
    profile = _identities()["models"][profile_id]
    if profile_id == "NO_MODEL":
        return {"status": "NO_MODEL", "profile_id": profile_id}
    try:
        from scripts.model_router import select_reasoning_model
        result = select_reasoning_model(
            agent_key=f"nexus_{agent_id.lower()}",
            task_type=profile["task_type"],
            sensitivity=profile["sensitivity"],
            reasoning_class=profile["reasoning_class"],
            allow_free_tier=bool(profile["allow_free_tier"]),
        )
    except Exception:
        return {"status": "MODEL_MANAGER_UNAVAILABLE", "profile_id": profile_id}
    if result.get("decision") != "selected":
        return {"status": "MODEL_PROFILE_UNAVAILABLE", "profile_id": profile_id}
    # No provider/model values escape this boundary. Execution stays in the
    # existing central router/provider adapter, which owns credential access.
    return {"status": "AVAILABLE", "profile_id": profile_id, "resolved_by": "NEXUS_MODEL_MANAGER"}


def route_bot_environment(*, agent_id: str, bot_id: str, runtime_health: dict[str, str]) -> dict[str, Any]:
    """Select a bot's preferred/declared fallback only with fresh caller health evidence."""
    bot = _identities()["agents"].get(bot_id)
    if not bot:
        raise AuthorizationDenied("BOT_NOT_REGISTERED")
    candidates = list(_identities()["environments"].values())
    healthy = {key for key, value in runtime_health.items() if value in {"HEALTHY", "PASS", "AVAILABLE", "LIVE_CERTIFIED"}}
    for row in candidates:
        if row["environment_id"] not in healthy:
            row["health"] = "RUNTIME_UNHEALTHY_OR_UNOBSERVED"
        else:
            row["health"] = runtime_health[row["environment_id"]]
    choice = select_environment(allowed=bot.get("allowed_execution_environments", []),
        preferred=bot.get("preferred_execution_environments", []),
        fallbacks=bot.get("fallback_execution_environments", []), registry=candidates,
        runtime_health=runtime_health)
    if choice.get("status") == "SELECTED":
        authorize(agent_id=agent_id, bot_id=bot_id, environment_id=choice["environment_id"], runtime_health=runtime_health)
    return choice


def enforce_bot_budget(*, bot: dict[str, Any], model_calls: int, input_tokens: int,
                       output_tokens: int, cost_usd: float, elapsed_seconds: float) -> None:
    """Enforce declared per-bot resource ceilings before accepting a result."""
    if bot.get("model_required") is False and model_calls:
        raise AuthorizationDenied("NO_MODEL_BOT_CANNOT_CALL_MODEL")
    limits = (("max_model_calls", model_calls), ("max_input_tokens", input_tokens),
              ("max_output_tokens", output_tokens), ("max_cost_usd", cost_usd),
              ("max_runtime_seconds", elapsed_seconds))
    for field, actual in limits:
        if actual > float(bot.get(field, -1)):
            raise AuthorizationDenied("RESOURCE_BUDGET_EXCEEDED")
