"""Provider-neutral, pre-publish social distribution contracts.

This module is intentionally a draft router.  It prepares platform packages and
enforces tenant/business/brand boundaries, but it cannot schedule or publish.
Credentials are references only; raw credentials never enter these records.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
from typing import Any, Dict, Iterable, List, Optional, Protocol


PLATFORMS = {
    "FACEBOOK", "INSTAGRAM", "YOUTUBE", "YOUTUBE_SHORTS", "TIKTOK",
    "LINKEDIN", "X", "THREADS", "PINTEREST", "OTHER",
}
ACCOUNT_STATUSES = {"UNCONFIGURED", "CONFIGURED", "AUTH_REQUIRED", "READY", "DEGRADED", "DISABLED", "RETIRED"}
PUBLISH_MODES = {"DRAFT_ONLY", "SCHEDULE_AFTER_APPROVAL", "MANUAL_PUBLISH", "AUTOMATED_PUBLISH"}
QUEUE_STATUSES = {"WAITING_CREATIVE", "WAITING_COMPLIANCE", "WAITING_APPROVAL", "READY", "SCHEDULED", "PUBLISHED", "BLOCKED"}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def stable_id(prefix: str, *parts: Any) -> str:
    raw = "|".join(str(part) for part in parts)
    return f"{prefix}_{sha256(raw.encode()).hexdigest()[:16]}"


@dataclass
class SocialAccount:
    social_account_id: str
    tenant_id: str
    business_id: str
    brand_id: str
    platform: str
    account_type: str
    account_handle: str
    platform_account_id: Optional[str] = None
    credential_ref: Optional[str] = None
    status: str = "UNCONFIGURED"
    posting_allowed: bool = False
    approval_required: bool = True
    analytics_allowed: bool = False
    default_campaign_scope: Optional[str] = None
    role: str = "PRIMARY"
    created_at: str = field(default_factory=now)
    updated_at: str = field(default_factory=now)

    def __post_init__(self) -> None:
        if self.platform not in PLATFORMS:
            raise ValueError(f"unsupported platform: {self.platform}")
        if self.status not in ACCOUNT_STATUSES:
            raise ValueError(f"unsupported account status: {self.status}")


@dataclass
class SocialPlatformCapability:
    platform: str
    supports_text: bool
    supports_image: bool
    supports_video: bool
    supports_carousel: bool
    supports_short_video: bool
    supports_link: bool
    supports_hashtags: bool
    supports_scheduling: bool
    supports_analytics: bool
    supports_comment_read: bool
    supports_dm: bool
    supports_api_publish: bool
    supports_browser_fallback: bool
    max_video_duration: Optional[int] = None
    aspect_ratio_constraints: List[str] = field(default_factory=list)


def platform_capabilities() -> Dict[str, SocialPlatformCapability]:
    # Capability truth is conservative: no API publishing is certified here.
    return {
        "FACEBOOK": SocialPlatformCapability("FACEBOOK", True, True, True, True, False, True, True, False, True, False, False, False, False, None, []),
        "INSTAGRAM": SocialPlatformCapability("INSTAGRAM", True, True, True, True, True, True, True, False, True, False, False, False, False, None, ["1:1", "4:5", "9:16"]),
        "YOUTUBE": SocialPlatformCapability("YOUTUBE", True, True, True, False, False, True, False, False, True, False, False, False, False, None, []),
        "YOUTUBE_SHORTS": SocialPlatformCapability("YOUTUBE_SHORTS", True, False, True, False, True, True, False, False, True, False, False, False, False, 180, ["9:16"]),
        "TIKTOK": SocialPlatformCapability("TIKTOK", True, False, True, False, True, False, True, False, False, False, False, False, False, 600, ["9:16"]),
        "LINKEDIN": SocialPlatformCapability("LINKEDIN", True, True, True, False, False, True, True, False, True, False, False, False, False, None, []),
        "X": SocialPlatformCapability("X", True, True, True, False, False, True, True, False, True, False, False, False, False, None, []),
        "THREADS": SocialPlatformCapability("THREADS", True, True, True, False, False, True, True, False, False, False, False, False, False, None, []),
        "PINTEREST": SocialPlatformCapability("PINTEREST", True, True, True, True, False, True, True, False, True, False, False, False, False, None, []),
        "OTHER": SocialPlatformCapability("OTHER", False, False, False, False, False, False, False, False, False, False, False, False, False, None, []),
    }


class SocialAccountRegistry:
    """The single account registry used by the router; records contain refs, not secrets."""

    def __init__(self, accounts: Iterable[SocialAccount] = ()) -> None:
        self._accounts: Dict[str, SocialAccount] = {}
        for account in accounts:
            self.register(account)

    def register(self, account: SocialAccount) -> SocialAccount:
        if account.social_account_id in self._accounts:
            raise ValueError(f"duplicate social account: {account.social_account_id}")
        self._accounts[account.social_account_id] = account
        return account

    def get_account(self, account_id: str) -> Optional[SocialAccount]:
        return self._accounts.get(account_id)

    def get_accounts_for_business(self, business_id: str) -> List[SocialAccount]:
        return [a for a in self._accounts.values() if a.business_id == business_id]

    def get_accounts_for_brand(self, brand_id: str) -> List[SocialAccount]:
        return [a for a in self._accounts.values() if a.brand_id == brand_id]

    def list_ready_accounts(self) -> List[SocialAccount]:
        return [a for a in self._accounts.values() if a.status == "READY"]

    def list_blocked_accounts(self) -> List[SocialAccount]:
        return [a for a in self._accounts.values() if a.status != "READY" or not a.posting_allowed]

    def validate_account_scope(self, campaign: Dict[str, Any], account: Optional[SocialAccount]) -> str:
        if account is None:
            return "POST_BLOCKED_UNKNOWN_ACCOUNT"
        if campaign.get("tenant_id") != account.tenant_id:
            return "POST_BLOCKED_CROSS_TENANT"
        if campaign.get("business_id") != account.business_id:
            return "POST_BLOCKED_CROSS_BUSINESS"
        if campaign.get("brand_id") != account.brand_id:
            return "POST_BLOCKED_CROSS_BRAND"
        return "PASS"

    def account_health(self, account_id: str) -> Dict[str, Any]:
        account = self.get_account(account_id)
        if not account:
            return {"account_id": account_id, "status": "UNKNOWN", "found": False}
        return {"account_id": account_id, "status": account.status, "found": True,
                "posting_allowed": account.posting_allowed, "analytics_allowed": account.analytics_allowed,
                "credential_ref_present": bool(account.credential_ref), "platform": account.platform}


@dataclass
class SocialDistributionRequest:
    distribution_request_id: str
    tenant_id: str
    business_id: str
    brand_id: str
    campaign_id: str
    variant_id: str
    creative_asset_ids: List[str]
    platform_targets: List[str]
    social_account_ids: List[str]
    headline: str
    caption: str
    cta: str
    landing_url: str
    utm_config: Dict[str, str]
    hashtags: List[str]
    publish_mode: str = "DRAFT_ONLY"
    requested_schedule: Optional[str] = None
    approval_ref: Optional[str] = None
    compliance_receipt_ref: Optional[str] = None
    created_by: str = "nexus_internal"
    status: str = "WAITING_APPROVAL"

    def __post_init__(self) -> None:
        if self.publish_mode not in PUBLISH_MODES:
            raise ValueError(f"unsupported publish mode: {self.publish_mode}")
        if not self.platform_targets or not self.social_account_ids:
            raise ValueError("at least one platform and account are required")


@dataclass
class SocialPost:
    social_post_id: str
    distribution_request_id: str
    tenant_id: str
    business_id: str
    brand_id: str
    campaign_id: str
    variant_id: str
    creative_asset_ids: List[str]
    platform: str
    social_account_id: str
    status: str = "DRAFT"
    scheduled_at: Optional[str] = None
    published_at: Optional[str] = None
    platform_post_id: Optional[str] = None
    landing_url: Optional[str] = None
    attribution_ref: Optional[str] = None
    approval_ref: Optional[str] = None
    compliance_ref: Optional[str] = None
    error: Optional[str] = None
    created_at: str = field(default_factory=now)
    updated_at: str = field(default_factory=now)


class SocialPlatformAdapter(Protocol):
    def probe(self) -> Dict[str, Any]: ...
    def account_health(self, account: SocialAccount) -> Dict[str, Any]: ...
    def prepare_post(self, request: SocialDistributionRequest, account: SocialAccount) -> Dict[str, Any]: ...
    def validate_post(self, package: Dict[str, Any]) -> Dict[str, Any]: ...
    def schedule_post(self, package: Dict[str, Any]) -> Dict[str, Any]: ...
    def publish_post(self, package: Dict[str, Any]) -> Dict[str, Any]: ...
    def read_post_status(self, post_id: str) -> Dict[str, Any]: ...
    def read_post_analytics(self, post_id: str) -> Dict[str, Any]: ...


def build_attribution(request: SocialDistributionRequest, platform: str, account_id: str, creative_id: str) -> Dict[str, str]:
    base = {"business_id": request.business_id, "brand_id": request.brand_id, "campaign_id": request.campaign_id,
            "variant_id": request.variant_id, "creative_id": creative_id, "platform": platform,
            "social_account_id": account_id}
    utm = request.utm_config or {}
    base.update({key: utm[key] for key in ("utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term") if key in utm})
    return base


def build_platform_packages(request: SocialDistributionRequest, account: SocialAccount) -> Dict[str, Dict[str, Any]]:
    platform = account.platform
    caption = request.caption
    if platform == "INSTAGRAM":
        return {platform: {"format": "vertical_video_or_image", "caption": caption, "hashtags": request.hashtags,
                           "cta": request.cta, "link_strategy": "approved_profile_or_landing_link", "draft_only": True}}
    if platform == "FACEBOOK":
        return {platform: {"format": "video_or_text_link", "headline": request.headline, "caption": caption,
                           "landing_url": request.landing_url, "cta": request.cta, "draft_only": True}}
    if platform == "YOUTUBE_SHORTS":
        return {platform: {"format": "short_form_video", "title": request.headline, "description": caption,
                           "cta": request.cta, "landing_url": request.landing_url, "draft_only": True}}
    if platform == "LINKEDIN":
        return {platform: {"format": "business_copy_with_link", "copy": f"{request.headline}\n\n{caption}",
                           "landing_url": request.landing_url, "cta": request.cta, "draft_only": True}}
    return {platform: {"format": "platform_draft", "headline": request.headline, "caption": caption,
                       "cta": request.cta, "landing_url": request.landing_url, "draft_only": True}}


class SocialDistributionRouter:
    def __init__(self, registry: SocialAccountRegistry, capabilities: Optional[Dict[str, SocialPlatformCapability]] = None) -> None:
        self.registry = registry
        self.capabilities = capabilities or platform_capabilities()

    def route(self, request: SocialDistributionRequest, *, asset_context: Optional[Dict[str, Dict[str, Any]]] = None,
              compliance_approved: bool = False, approval_approved: bool = False) -> Dict[str, Any]:
        results: List[Dict[str, Any]] = []
        packages: List[Dict[str, Any]] = []
        for account_id in request.social_account_ids:
            account = self.registry.get_account(account_id)
            scope = self.registry.validate_account_scope(asdict(request), account)
            if scope != "PASS":
                results.append({"account_id": account_id, "status": "BLOCKED", "reason": scope}); continue
            assert account is not None
            if account.status != "READY" or not account.posting_allowed:
                results.append({"account_id": account_id, "status": "BLOCKED", "reason": "POST_BLOCKED_ACCOUNT_NOT_READY"}); continue
            if account.platform not in request.platform_targets:
                results.append({"account_id": account_id, "status": "BLOCKED", "reason": "POST_BLOCKED_PLATFORM_MISMATCH"}); continue
            if request.publish_mode != "DRAFT_ONLY":
                results.append({"account_id": account_id, "status": "BLOCKED", "reason": "POST_BLOCKED_PUBLISH_DISABLED"}); continue
            if not request.compliance_receipt_ref or not compliance_approved:
                results.append({"account_id": account_id, "status": "BLOCKED", "reason": "POST_BLOCKED_COMPLIANCE"}); continue
            if not request.approval_ref or not approval_approved:
                results.append({"account_id": account_id, "status": "BLOCKED", "reason": "POST_BLOCKED_APPROVAL"}); continue
            cap = self.capabilities.get(account.platform, self.capabilities["OTHER"])
            if asset_context:
                wrong = [aid for aid in request.creative_asset_ids if asset_context.get(aid, {}).get("brand_id") not in (None, request.brand_id)]
                if wrong:
                    results.append({"account_id": account_id, "status": "BLOCKED", "reason": "POST_BLOCKED_CROSS_BRAND_ASSET", "asset_ids": wrong}); continue
            package = build_platform_packages(request, account)[account.platform]
            package.update({"account_id": account.social_account_id, "platform": account.platform,
                            "capability": asdict(cap), "attribution": build_attribution(request, account.platform, account.social_account_id, request.creative_asset_ids[0] if request.creative_asset_ids else "none")})
            packages.append(package)
            results.append({"account_id": account_id, "platform": account.platform, "status": "READY_FOR_REVIEW", "reason": "DRAFT_ONLY_PREPARED"})
        overall = "READY_FOR_REVIEW" if packages and not any(r["status"] == "BLOCKED" for r in results) else ("PARTIAL" if packages else "BLOCKED")
        return {"distribution_request_id": request.distribution_request_id, "status": overall, "results": results,
                "platform_packages": packages, "publication_executed": False, "external_mutation": False}


def build_queue_record(request: SocialDistributionRequest, status: str = "WAITING_APPROVAL") -> Dict[str, Any]:
    if status not in QUEUE_STATUSES:
        raise ValueError(status)
    return {"distribution_request_id": request.distribution_request_id, "business_id": request.business_id,
            "brand_id": request.brand_id, "campaign_id": request.campaign_id, "status": status,
            "publication_enabled": False, "created_at": now()}


@dataclass
class SocialAccountProvisioningRequest:
    business_id: str
    brand_id: str
    platform: str
    desired_handle: str
    fallback_handles: List[str]
    business_name: str
    bio: str
    description: str
    website: str
    contact_info_ref: Optional[str]
    profile_asset_ref: Optional[str]
    cover_asset_ref: Optional[str]
    verification_state: str = "UNKNOWN"
    human_actions_required: List[str] = field(default_factory=list)
    credential_destination: Optional[str] = None
    status: str = "DRAFT"


@dataclass
class SocialAccountReadiness:
    business_name_ready: bool
    handle_candidates_ready: bool
    bio_ready: bool
    profile_image_ready: bool
    cover_image_ready: bool
    website_ready: bool
    cta_ready: bool
    contact_info_ready: bool
    compliance_ready: bool
    email_ready: bool
    phone_ready: bool
    verification_requirement_known: bool


def audit_connection_inventory() -> Dict[str, Any]:
    """Return safe, non-secret evidence about existing connector/config records."""
    from pathlib import Path
    import json
    root = Path(__file__).resolve().parents[2]
    connector_path = root / "configs" / "connector_registry.json"
    registry = json.loads(connector_path.read_text()) if connector_path.exists() else {"connectors": []}
    social = [c for c in registry.get("connectors", []) if "social" in c.get("category", "") or "social" in c.get("connector_id", "")]
    env_names = ["META_PAGE_ACCESS_TOKEN", "META_PAGE_ID", "META_APP_ID", "META_APP_SECRET", "META_INSTAGRAM_ACCOUNT_ID"]
    import os
    return {"connector_records": [{"connector_id": c.get("connector_id"), "status": c.get("status"), "live_enabled": c.get("live_enabled", False),
                                   "approval_required": c.get("approval_required", False)} for c in social],
            "credential_presence": {name: bool(os.environ.get(name)) for name in env_names},
            "raw_credentials_exposed": False,
            "publish_executed": False,
            "account_business_mapping": "UNKNOWN_UNPROVEN"}


def visibility(registry: SocialAccountRegistry, requests: Iterable[SocialDistributionRequest] = (), posts: Iterable[SocialPost] = ()) -> Dict[str, Any]:
    return {"accounts": [asdict(a) for a in registry._accounts.values()],
            "ready_account_count": len(registry.list_ready_accounts()),
            "blocked_account_count": len(registry.list_blocked_accounts()),
            "requests": [asdict(r) for r in requests], "posts": [asdict(p) for p in posts],
            "publication_enabled": False, "credentials_exposed": False}
