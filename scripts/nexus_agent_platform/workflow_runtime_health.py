"""Bounded, timestamped health observations for Workflow Fabric dispatch.

This module reads local Research health endpoints only. Remote environments must
be supplied by their approved adapters; this module never infers their health.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any


MAC_RESEARCH_ENDPOINTS = {
    "research_api": "http://127.0.0.1:4000/health",
    "research_r10": "http://127.0.0.1:18766/health",
    "research_mcp": "http://127.0.0.1:18768/health",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def probe_http(url: str, *, timeout_seconds: float = 2.0) -> dict[str, Any]:
    """Return a redacted observation; expected auth challenges are explicit."""
    started = time.monotonic()
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            status = int(response.status)
            body = response.read(4096)
        state = "HEALTHY" if 200 <= status < 300 else "DEGRADED"
        detail = None
        if body:
            try:
                parsed = json.loads(body.decode("utf-8", "replace"))
                detail = parsed.get("status") if isinstance(parsed, dict) else None
            except (ValueError, UnicodeDecodeError):
                detail = None
    except urllib.error.HTTPError as exc:
        status = int(exc.code)
        state = "AUTH_REQUIRED" if status in {401, 403} else "DEGRADED"
        detail = None
    except (urllib.error.URLError, TimeoutError, OSError):
        status, state, detail = None, "UNAVAILABLE", None
    return {"status": state, "http_status": status, "observed_at": _utc_now(),
            "latency_ms": round((time.monotonic() - started) * 1000), "detail": detail}


def probe_mac_research(*, timeout_seconds: float = 2.0) -> dict[str, Any]:
    """Probe the three owned endpoints and derive conservative environment health."""
    checks = {name: probe_http(url, timeout_seconds=timeout_seconds)
              for name, url in MAC_RESEARCH_ENDPOINTS.items()}
    required = (checks["research_api"]["status"], checks["research_r10"]["status"])
    # Research MCP can correctly challenge an unauthenticated health request;
    # protocol access is certified separately through its authenticated route.
    if all(value == "HEALTHY" for value in required):
        status = "HEALTHY"
    elif "UNAVAILABLE" in required:
        status = "UNAVAILABLE"
    else:
        status = "DEGRADED"
    return {"environment_id": "MAC_MINI", "status": status,
            "observed_at": _utc_now(), "checks": checks}


def fresh_environment_health(observations: dict[str, dict[str, Any]], *,
                             max_age_seconds: int = 300,
                             now: datetime | None = None) -> dict[str, str]:
    """Convert timestamped adapter evidence to router health, rejecting stale data."""
    now = now or datetime.now(timezone.utc)
    result: dict[str, str] = {}
    for environment_id, observation in observations.items():
        try:
            observed = datetime.fromisoformat(str(observation["observed_at"]).replace("Z", "+00:00"))
            age = (now - observed).total_seconds()
        except (KeyError, TypeError, ValueError):
            continue
        if age < 0 or age > max_age_seconds:
            continue
        status = str(observation.get("status", "UNKNOWN"))
        if status in {"HEALTHY", "LIVE_CERTIFIED", "AVAILABLE", "PASS"}:
            result[environment_id] = status
    return result
