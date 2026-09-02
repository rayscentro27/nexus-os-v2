"""WP9E resource-aware browser placement and talent evidence contracts.

This module is deliberately control-plane-only.  It never starts a scheduler,
creates an account, installs a provider, or grants authority.
"""
from __future__ import annotations

import hashlib
import json
import platform
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def stable_id(prefix: str, value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, default=str, separators=(",", ":"))
    return f"{prefix}_{hashlib.sha256(raw.encode()).hexdigest()[:16]}"


@dataclass(frozen=True)
class BrowserLimits:
    max_browser_sessions: int
    max_tabs_per_session: int
    max_job_duration_seconds: int
    idle_timeout_seconds: int
    memory_guard_percent: int
    cleanup_on_exit: bool = True


def browser_limits(*, available_ram_gib: float, cpu_count: int) -> BrowserLimits:
    """Choose conservative limits from measured worker capacity."""
    sessions = 1 if available_ram_gib < 8 else 2
    tabs = 3 if available_ram_gib < 16 else 5
    duration = 300 if cpu_count <= 4 else 600
    return BrowserLimits(sessions, tabs, duration, 45, 80)


def browser_placement(*, estimated_ram_mb: int, duration_seconds: int,
                      tabs: int, auth_required: bool, privacy: str,
                      oracle_health: str) -> dict[str, Any]:
    """Place browser work without silently falling back to a constrained Mac."""
    heavy = estimated_ram_mb > 1200 or duration_seconds > 180 or tabs > 2
    private = privacy.upper() in {"SENSITIVE", "CONFIDENTIAL"}
    if oracle_health != "HEALTHY":
        location = "LOCAL_REQUIRED" if not heavy and not private else "DEFER"
    elif auth_required:
        location = "AUTHENTICATED_ORACLE"
    elif heavy:
        location = "ORACLE_REMOTE"
    else:
        location = "LOCAL_LIGHT"
    return {
        "decision_id": stable_id("placement", [estimated_ram_mb, duration_seconds, tabs, auth_required, privacy, oracle_health]),
        "capability": "browser",
        "run_location": location,
        "heavy": heavy,
        "oracle_health": oracle_health,
        "created_at": now(),
        "reason": "bounded workload and measured worker capacity" if location in {"ORACLE_REMOTE", "AUTHENTICATED_ORACLE"} else "local-only or safe deferral policy",
    }


def resource_baseline() -> dict[str, Any]:
    return {
        "execution_class": "MAC_CONTROL_PLANE",
        "architecture": platform.machine(),
        "os": platform.platform(),
        "python": platform.python_version(),
        "cpu_count": __import__("os").cpu_count(),
        "authority": "control/state/Finance/secrets remain local",
    }


def talent_cost_card(name: str, *, license_cost: str, model_cost: str,
                     compute_cost: str, free_tier: str, unknown_costs: list[str],
                     recommendation: str) -> dict[str, Any]:
    return {
        "candidate": name,
        "software_license_cost": license_cost,
        "account_cost": "$0 account not required by software",
        "subscription_cost": "UNKNOWN; provider/model dependent",
        "api_cost": "UNKNOWN; no provider bundled",
        "model_cost": model_cost,
        "free_tier": free_tier,
        "compute_cost": compute_cost,
        "storage_cost": "existing local/Oracle storage; incremental cash UNKNOWN",
        "estimated_cost_per_task": "UNKNOWN until model route and task are measured",
        "estimated_monthly_cost": "UNKNOWN; usage dependent",
        "replacement_cost": "manual/Jax comparison not measured",
        "unknown_costs": unknown_costs,
        "cost_class": "USAGE_DEPENDENT",
        "finance_recommendation": recommendation,
        "created_at": now(),
    }


def browser_receipt(*, host: str, container: str, url: str, screenshot_sha256: str,
                    duration_ms: int, cleanup: str) -> dict[str, Any]:
    return {
        "receipt_id": stable_id("browser", [host, container, url, screenshot_sha256]),
        "status": "PASS",
        "execution_location": "ORACLE_HERMES_CONTAINER",
        "host": host,
        "container": container,
        "url": url,
        "pages": 1,
        "dom_extraction": "PASS",
        "screenshot": "PASS",
        "screenshot_sha256": screenshot_sha256,
        "duration_ms": duration_ms,
        "cleanup": cleanup,
        "cash_cost_usd": 0,
        "created_at": now(),
    }
