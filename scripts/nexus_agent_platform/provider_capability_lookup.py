"""Read-only lookup against the existing Nexus capability registry."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "data/runtime/nexus_capability_registry.json"


def capability_lookup(query: str) -> dict[str, Any]:
    """Return current known providers for a capability; never reads secrets."""
    needle = str(query or "").strip().casefold()
    if not needle:
        return {"query": query, "matches": [], "status": "INVALID_QUERY"}
    try:
        payload = json.loads(REGISTRY.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"query": query, "matches": [], "status": "REGISTRY_UNAVAILABLE"}
    providers = payload.get("provider_inventory") or []
    matches = []
    for row in providers:
        capabilities = [str(x) for x in row.get("capabilities") or []]
        workflows = [str(x) for x in row.get("supported_workflows") or []]
        names = [str(row.get("provider_id") or ""), str(row.get("provider_name") or "")]
        if any(needle in value.casefold() for value in [*capabilities, *workflows, *names]):
            matches.append({"provider_id": row.get("provider_id"), "provider_name": row.get("provider_name"),
                "capabilities": capabilities, "supported_workflows": workflows,
                "current_health": row.get("current_health"), "auth_status": row.get("auth_status"),
                "environment": row.get("environment"), "entitlements": row.get("entitlements") or [],
                "alternative_providers": row.get("alternative_providers")})
    return {"query": query, "matches": matches,
            "status": "FOUND" if matches else "NOT_FOUND", "raw_secrets_included": False}
