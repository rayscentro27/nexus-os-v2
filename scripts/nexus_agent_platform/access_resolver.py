"""Remote-aware capability access resolution.

This is metadata-only.  It never fetches or returns Netlify environment
values; it tells callers where a capability can execute and which governed
relay/provider should be used.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping

from nexus_agent_platform.credential_control_plane import _netlify_env_names, resolve

REMOTE_REQUIREMENTS: dict[str, dict[str, Any]] = {
    "voice.transport": {
        "credential_id": "credential.cloudflare.voice_service.prod.v1",
        "aliases": ("CF_ACCESS_CLIENT_ID", "CF_ACCESS_CLIENT_SECRET", "VOICE_ACCESS_ORIGIN"),
        "execution_location": "NETLIFY_SERVER",
        "resolution": "USE_NETLIFY_RELAY",
    },
    "model.groq": {
        "credential_id": "credential.groq.models.prod.v1",
        "aliases": ("GROQ_API_KEY",),
        "execution_location": "NETLIFY_SERVER",
        "resolution": "USE_NETLIFY_MODEL_RELAY",
    },
    "model.openrouter": {
        "credential_id": "credential.openrouter.models.prod.v1",
        "aliases": ("OPENROUTER_API_KEY",),
        "execution_location": "NETLIFY_SERVER",
        "resolution": "USE_NETLIFY_MODEL_RELAY",
    },
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def resolve_access(capability: str, *, environ: Mapping[str, str] | None = None) -> dict[str, Any]:
    spec = REMOTE_REQUIREMENTS.get(capability)
    if spec:
        names = _netlify_env_names()
        remote_present = all(alias in names for alias in spec["aliases"])
        local = resolve(spec["credential_id"], environ=environ)
        local_selected = any(source != "NETLIFY_ENV" for source in local.get("source_found", []))
        return {
            "capability": capability,
            "credential_id": spec["credential_id"],
            "sources_checked": ["PROCESS_ENV", "CANONICAL_RUNTIME_ENV", "MACOS_KEYCHAIN", "NETLIFY_ENV"],
            "available_sources": (["LOCAL"] if local_selected else []) + (["NETLIFY_ENV"] if remote_present else []),
            "execution_location": "NETLIFY_SERVER" if remote_present else ("LOCAL" if local_selected else "UNRESOLVED"),
            "auth_state": "AVAILABLE_REMOTE_NETLIFY" if remote_present else ("AVAILABLE_LOCAL" if local_selected else "UNRESOLVED"),
            "provider_health": "CONFIGURED_UNTESTED",
            "authority_state": "ADVISORY_OR_READ_ONLY",
            "human_action_required": not remote_present and not local_selected,
            "local_secret_required": False if remote_present else True,
            "resolution": spec["resolution"] if remote_present else "NO_SAFE_EXECUTION_LOCATION",
            "checked_at": _now(),
            "values_included": False,
        }
    return {
        "capability": capability,
        "sources_checked": ["PROCESS_ENV", "CANONICAL_RUNTIME_ENV", "MACOS_KEYCHAIN"],
        "available_sources": [], "execution_location": "UNRESOLVED", "auth_state": "DISCOVERY_INCOMPLETE",
        "provider_health": "NOT_RUN", "authority_state": "UNRESOLVED", "human_action_required": False,
        "local_secret_required": False, "resolution": "CAPABILITY_NOT_REGISTERED", "checked_at": _now(),
        "values_included": False,
    }


def resolve_access_snapshot(*, environ: Mapping[str, str] | None = None) -> dict[str, Any]:
    return {"generated_at": _now(), "access": {name: resolve_access(name, environ=environ) for name in REMOTE_REQUIREMENTS}, "values_included": False}
