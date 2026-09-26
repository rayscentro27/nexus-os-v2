"""Provider-agnostic social operations contracts.

This module contains deterministic routing and normalization only. It does not
publish, connect accounts, enable failover, or call a provider.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

PROVIDERS = ("METRICOOL", "POSTIZ", "TRYPOST", "NATIVE")
CHANNEL_ENVIRONMENTS = ("LAB", "STAGING", "PRODUCTION")
SOCIAL_LAB_BUSINESS_ID = "nexus_social_lab"
JOB_STATES = ("DRAFT", "SCHEDULED", "PUBLISHING", "PUBLISHED", "FAILED", "CANCELLED", "UNKNOWN")
CHANNEL_STATES = ("NOT_REQUESTED", "REQUESTED", "DISCOVERY", "EXISTING_ACCOUNT_FOUND", "PROVISIONING", "HUMAN_VERIFICATION_REQUIRED", "VERIFIED", "PRIMARY_HUB_CONNECTED", "SECONDARY_HUB_CONNECTED", "PUBLISH_READY", "ANALYTICS_READY", "ENGAGEMENT_READY", "DEGRADED", "BLOCKED_EXTERNAL")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def idempotency_key(business_id: str, campaign_id: str, asset_id: str, platform: str, account_id: str, desired_time: str | None) -> str:
    raw = "|".join((business_id, campaign_id, asset_id, platform, account_id, desired_time or ""))
    return "social_" + hashlib.sha256(raw.encode()).hexdigest()[:24]


def provider_route(*, business_id: str, platform: str, account_id: str, primary: str = "METRICOOL", secondary: str = "POSTIZ", native: str = "NATIVE", auto_failover: bool = False, channel_environment: str = "PRODUCTION") -> dict[str, Any]:
    if primary not in PROVIDERS or secondary not in PROVIDERS or native not in PROVIDERS:
        raise ValueError("unknown social provider")
    if channel_environment not in CHANNEL_ENVIRONMENTS:
        raise ValueError("unknown channel environment")
    if channel_environment == "LAB" and primary == "METRICOOL":
        raise ValueError("LAB routes must not use Metricool")
    if primary == "TRYPOST" and channel_environment != "LAB":
        raise ValueError("TryPost is LAB-only until Upgrade Control promotion")
    return {
        "business_id": business_id,
        "platform": platform,
        "account_id": account_id,
        "primary_provider": primary,
        "secondary_provider": secondary,
        "native_fallback": native,
        "current_provider": primary,
        "publish_capable": False,
        "analytics_capable": False,
        "engagement_capable": False,
        "health_status": "UNKNOWN",
        "last_health_check": None,
        "auto_failover": auto_failover,
        "provider_ownership_required": True,
        "channel_environment": channel_environment,
        "metricool_quota_reserved_for_production": channel_environment != "LAB",
    }


def publication_job(*, business_id: str, campaign_id: str, asset_id: str, platform: str, account_id: str, desired_time: str | None, approval_id: str | None, provider: str = "METRICOOL", channel_environment: str = "PRODUCTION") -> dict[str, Any]:
    if provider not in PROVIDERS:
        raise ValueError("unknown social provider")
    if channel_environment not in CHANNEL_ENVIRONMENTS:
        raise ValueError("unknown channel environment")
    if channel_environment == "LAB" and provider == "METRICOOL":
        raise ValueError("LAB jobs must not route to Metricool")
    if provider == "TRYPOST" and channel_environment != "LAB":
        raise ValueError("TryPost jobs are LAB-only until Upgrade Control promotion")
    key = idempotency_key(business_id, campaign_id, asset_id, platform, account_id, desired_time)
    return {
        "publication_job_id": "job_" + key.removeprefix("social_"),
        "business_id": business_id,
        "campaign_id": campaign_id,
        "asset_id": asset_id,
        "platform": platform,
        "account_id": account_id,
        "idempotency_key": key,
        "provider_owner": provider,
        "channel_environment": channel_environment,
        "metricool_quota_reserved_for_production": channel_environment != "LAB",
        "approval_id": approval_id,
        "status": "DRAFT",
        "receipt": None,
        "created_at": _now(),
        "updated_at": _now(),
    }


def can_transfer_ownership(job: dict[str, Any], *, remote_post_exists: bool, receipt_status: str | None) -> tuple[bool, str]:
    if job.get("status") in {"PUBLISHED", "PUBLISHING"}:
        return False, "publication_already_in_progress_or_complete"
    if remote_post_exists or receipt_status in {"PUBLISHED_REAL", "PUBLISHED", "SCHEDULED_REAL"}:
        return False, "remote_or_receipt_evidence_exists"
    if not job.get("provider_owner"):
        return False, "provider_owner_missing"
    return True, "no_successful_publication_evidence"


def normalize_post(provider: str, payload: dict[str, Any]) -> dict[str, Any]:
    return {"provider": provider, "business_id": payload.get("business_id"), "campaign_id": payload.get("campaign_id"), "asset_id": payload.get("asset_id"), "platform": payload.get("platform"), "post_id": payload.get("post_id") or payload.get("external_id"), "public_url": payload.get("public_url") or payload.get("permalink"), "published_at": payload.get("published_at"), "caption": payload.get("caption") or payload.get("text"), "cta": payload.get("cta"), "destination": payload.get("destination"), "status": payload.get("status"), "raw_reference": payload.get("raw_reference")}


def normalize_analytics(provider: str, payload: dict[str, Any]) -> dict[str, Any]:
    names = ("views", "reach", "watch_time", "completion", "likes", "comments", "shares", "saves", "profile_visits", "follows", "clicks")
    return {"provider": provider, "business_id": payload.get("business_id"), "platform": payload.get("platform"), "post_id": payload.get("post_id"), **{name: payload.get(name) for name in names}, "collected_at": payload.get("collected_at") or _now()}


def normalize_engagement(provider: str, payload: dict[str, Any]) -> dict[str, Any]:
    return {"provider": provider, "engagement_id": payload.get("engagement_id") or payload.get("id"), "platform": payload.get("platform"), "post_id": payload.get("post_id"), "type": payload.get("type") or payload.get("engagement_type"), "author_reference": payload.get("author_reference"), "text": payload.get("text"), "timestamp": payload.get("timestamp"), "parent_id": payload.get("parent_id"), "read_status": payload.get("read_status"), "handled_status": payload.get("handled_status"), "classification": None, "raw_reference": payload.get("raw_reference")}


def prepare_marketing_channels(business_id: str, channels: list[dict[str, Any]], *, channel_environment: str = "PRODUCTION", allow_account_creation: bool = False) -> dict[str, Any]:
    """Prepare discovery/provisioning work without bypassing human verification.

    This remains a plan-only boundary: account creation is never performed by
    this function. When enabled, it emits a human-assisted plan for a later
    operator step and preserves CAPTCHA, SMS, email, MFA, identity, ownership,
    and terms gates.
    """
    if channel_environment not in CHANNEL_ENVIRONMENTS:
        raise ValueError("unknown channel environment")
    return {
        "business_id": business_id,
        "channel_environment": channel_environment,
        "mode": "HUMAN_ASSISTED_PLAN" if allow_account_creation else "DRY_RUN",
        "account_creation": "PLAN_ONLY" if allow_account_creation else "DISABLED",
        "channels": channels,
        "next_state": "EXISTING_ACCOUNT_FOUND" if channels else "DISCOVERY",
        "human_verification": any(c.get("human_verification_state") == "REQUIRED" for c in channels),
        "verification_policy": "NO_CAPTCHA_OR_SMS_EMAIL_MFA_IDENTITY_OWNERSHIP_TERMS_BYPASS",
    }


def channel_operations_contract() -> dict[str, Any]:
    return {
        "capability": "NEXUS_CHANNEL_OPERATIONS",
        "owner": "MARKETING_OPERATIONS",
        "mechanical_operator": "HERMES_OPERATOR",
        "systems_owner": ["health", "credentials", "retries", "receipts", "failover"],
        "ray_gate": ["human_verification", "terms_acceptance", "material_approval"],
        "states": list(CHANNEL_STATES),
        "channel_environments": list(CHANNEL_ENVIRONMENTS),
        "account_creation_policy": "NO_CAPTCHA_OR_VERIFICATION_BYPASS",
        "account_creation_mode": "HUMAN_ASSISTED_PLAN_ONLY",
        "routine_model": "DETERMINISTIC_OR_LOW_COST",
        "auto_provider_failover": False,
        "lab_policy": {"business_id": SOCIAL_LAB_BUSINESS_ID, "primary_provider": "POSTIZ", "metricool_connected": False, "metricool_quota_usage": 0},
    }
