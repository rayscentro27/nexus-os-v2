"""Certified deployment strategy boundary for Product Evolution releases."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class DeploymentStrategy:
    strategy_id: str
    enabled: bool
    certified: bool
    supports_exact_sha: bool


NETLIFY_EXACT_SHA_CLI = DeploymentStrategy(
    strategy_id="NETLIFY_EXACT_SHA_CLI",
    enabled=True,
    certified=True,
    supports_exact_sha=True,
)

NETLIFY_GIT_RELEASE_BRANCH = DeploymentStrategy(
    strategy_id="NETLIFY_GIT_RELEASE_BRANCH",
    enabled=False,
    certified=False,
    supports_exact_sha=True,
)


def strategy_failover_recommendation(transport_failures: list[Mapping[str, Any]]) -> dict[str, Any]:
    """Recommend, but never activate, fallback after independent transport failures."""
    transport_codes = {
        "DEPLOY_AUTH", "DEPLOY_CLI", "DEPLOY_UPLOAD", "NETLIFY_STATUS_FAILED",
    }
    independent = [item for item in transport_failures if item.get("failure_class") in transport_codes]
    releases = {item.get("release_id") for item in independent}
    eligible = len(independent) >= 3 and len(releases) >= 2
    return {
        "recommendation": "NETLIFY_GIT_RELEASE_BRANCH" if eligible else "NONE",
        "eligible": eligible,
        "activation": "DISABLED",
        "reason": "three transport failures across two or more releases" if eligible else "FAILOVER_THRESHOLD_NOT_REACHED",
    }
