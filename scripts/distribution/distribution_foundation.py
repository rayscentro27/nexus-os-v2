"""Nexus Multi-Venture Social & Distribution Connector Foundation (Section 31A).

Enforces strict lineage, multi-venture isolation, and governance across:
NEXUS -> VENTURE -> CAMPAIGN -> PRODUCT/OFFER -> CREATIVE ASSETS -> CHANNEL ACCOUNT -> POST -> ENGAGEMENT -> PERFORMANCE.

Key Invariants:
1. VENTURE_ACCOUNT_SCOPE_MISMATCH = BLOCK
2. ASSET_CAMPAIGN_SCOPE_MISMATCH = BLOCK
3. CAMPAIGN_VENTURE_SCOPE_MISMATCH = BLOCK
4. PRODUCT_TRUTH_GATE = ENFORCED (via scripts.creative.product_truth_validator)
5. Zero external publishing or scheduling in Section 31A ($0 spend, published=NO).
6. Zero duplicate infrastructure (extends existing SQLite/governed patterns).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

APPROVAL_POLICY_VERSION = "nexus.distribution-approval.v1"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------
# Enums
# --------------------------------------------------------------------------

class AccountScopeType(str, Enum):
    SINGLE_VENTURE = "single_venture"
    SHARED = "shared"


class AssetScopeType(str, Enum):
    CAMPAIGN = "campaign"
    VENTURE = "venture"
    GLOBAL_BRAND = "global_brand"


class DistributionJobStatus(str, Enum):
    DRAFT = "DRAFT"
    READY_FOR_APPROVAL = "READY_FOR_APPROVAL"
    APPROVED = "APPROVED"
    SCHEDULED = "SCHEDULED"
    PUBLISHING = "PUBLISHING"
    PUBLISHED = "PUBLISHED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class ChannelPlatform(str, Enum):
    INSTAGRAM = "INSTAGRAM"
    TIKTOK = "TIKTOK"
    YOUTUBE = "YOUTUBE"
    YOUTUBE_SHORTS = "YOUTUBE_SHORTS"
    FACEBOOK = "FACEBOOK"
    LINKEDIN = "LINKEDIN"
    PINTEREST = "PINTEREST"
    X = "X"
    THREADS = "THREADS"
    STOREFRONT = "STOREFRONT"
    AMAZON = "AMAZON"
    WALMART = "WALMART"
    PRINTIFY = "PRINTIFY"


# --------------------------------------------------------------------------
# Data Models
# --------------------------------------------------------------------------

@dataclass
class DistributionLineage:
    """Carries complete traceable lineage from Venture to Post."""
    venture_id: str
    campaign_id: str
    asset_id: str
    channel_account_id: str
    channel: str
    distribution_job_id: str
    product_id: Optional[str] = None
    offer_id: Optional[str] = None
    creative_request_id: Optional[str] = None
    post_id: Optional[str] = None
    experiment_id: Optional[str] = None

    def validate_complete(self) -> Tuple[bool, List[str]]:
        missing = []
        if not self.venture_id: missing.append("venture_id")
        if not self.campaign_id: missing.append("campaign_id")
        if not self.asset_id: missing.append("asset_id")
        if not self.channel_account_id: missing.append("channel_account_id")
        if not self.channel: missing.append("channel")
        if not self.distribution_job_id: missing.append("distribution_job_id")
        return len(missing) == 0, missing

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ChannelAccount:
    """Authoritative representation of an external distribution account."""
    channel_account_id: str
    platform: str
    account_name: str
    account_type: str  # PAGE, BUSINESS, CREATOR, PERSONAL, STOREFRONT, SELLER
    account_scope: AccountScopeType
    venture_scope: List[str]  # Authorized venture IDs
    auth_status: str  # AUTHENTICATED, AUTH_REQUIRED, REQUIRES_RAY_LOGIN, EXPIRED
    connection_status: str  # CONNECTED, PARTIAL, INACTIVE, BLOCKED
    capabilities: List[str]
    publish_allowed: bool = False
    schedule_allowed: bool = False
    read_engagement_allowed: bool = False
    respond_allowed: bool = False  # Strictly False by default
    analytics_allowed: bool = False
    commerce_allowed: bool = False
    approval_policy: str = "APPROVAL_REQUIRED"
    credential_reference: str = ""  # e.g. "env:META_PAGE_ACCESS_TOKEN", NEVER raw secret
    last_health_check: Optional[str] = None
    external_account_id: str = ""  # authoritative provider ID (Page ID / IG user ID)

    def is_authorized_for_venture(self, venture_id: str) -> bool:
        if self.account_scope == AccountScopeType.SHARED:
            return venture_id in self.venture_scope
        return len(self.venture_scope) == 1 and self.venture_scope[0] == venture_id

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["account_scope"] = self.account_scope.value
        return d


@dataclass
class AssetScopeRecord:
    """Enforces asset ownership and reuse rules across campaigns and ventures."""
    asset_id: str
    venture_id: str
    campaign_id: Optional[str]
    scope_type: AssetScopeType = AssetScopeType.CAMPAIGN

    def is_usable_by(self, target_venture_id: str, target_campaign_id: str) -> Tuple[bool, str]:
        if self.scope_type == AssetScopeType.GLOBAL_BRAND:
            return True, "GLOBAL_BRAND_PERMITTED"
        if self.venture_id != target_venture_id:
            return False, f"ASSET_VENTURE_MISMATCH: asset belongs to {self.venture_id}, requested by {target_venture_id}"
        if self.scope_type == AssetScopeType.VENTURE:
            return True, "VENTURE_SCOPED_PERMITTED"
        # Otherwise strictly campaign-scoped
        if self.campaign_id != target_campaign_id:
            return False, f"ASSET_CAMPAIGN_SCOPE_MISMATCH: asset belongs to {self.campaign_id}, requested by {target_campaign_id}"
        return True, "CAMPAIGN_SCOPED_MATCH"

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["scope_type"] = self.scope_type.value
        return d


@dataclass
class DistributionJob:
    """Canonical representation of an internal distribution work order."""
    distribution_job_id: str
    venture_id: str
    campaign_id: str
    asset_ids: List[str]
    channel_account_id: str
    platform: str
    content_type: str
    copy: str
    media: Dict[str, Any]
    target_url: Optional[str] = None
    scheduled_time: Optional[str] = None
    timezone: str = "UTC"
    status: DistributionJobStatus = DistributionJobStatus.DRAFT
    approval_status: str = "WAITING_APPROVAL"
    publish_status: str = "UNPUBLISHED"
    external_post_id: Optional[str] = None
    created_at: str = field(default_factory=utc_now)
    published_at: Optional[str] = None
    error: Optional[str] = None
    receipt: Optional[Dict[str, Any]] = None
    # Prioritization & Scaling hooks (Part 15)
    priority: int = 5  # 1 (low) to 10 (urgent)
    deadline: Optional[str] = None
    campaign_priority: int = 5
    venture_priority: int = 5
    seasonality: str = "STANDARD"
    expected_value: Optional[float] = None
    resource_requirements: Dict[str, Any] = field(default_factory=dict)
    product_id: Optional[str] = None
    offer_id: Optional[str] = None
    # Section 31B.1 Canonical Fields
    landing_page_id: Optional[str] = None
    deployment_id: Optional[str] = None
    environment: str = "test"
    approval_receipt_id: Optional[str] = None
    publish_receipt_id: Optional[str] = None
    attempt_count: int = 0

    @property
    def product_id_or_offer_id(self) -> Optional[str]:
        return self.product_id or self.offer_id

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value
        d["product_id_or_offer_id"] = self.product_id_or_offer_id
        return d


@dataclass
class PublishReceipt:
    """Canonical publishing receipt generated upon successful execution."""
    publish_receipt_id: str
    distribution_job_id: str
    venture_id: str
    campaign_id: str
    channel_account_id: str
    platform: str
    external_post_id: str
    published_at: str
    media_asset_ids: List[str]
    copy_hash: str
    target_url: Optional[str] = None
    status: str = "PUBLISHED_CONFIRMED"
    error: Optional[str] = None
    provider_response_reference: str = ""
    # Canonical 31B.1 fields
    product_id_or_offer_id: Optional[str] = None
    external_url: Optional[str] = None
    cost: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# --------------------------------------------------------------------------
# Future 31C Engagement & 31D Performance Hooks
# --------------------------------------------------------------------------

@dataclass
class EngagementEventHook:
    """Prepares data schema for future Section 31C engagement ingestion."""
    engagement_event_id: str
    venture_id: str
    campaign_id: str
    post_id: str
    channel_account_id: str
    external_event_id: str
    engagement_type: str  # COMMENT, MENTION, MESSAGE, REPLY, REACTION
    author_id: str
    content: str
    sentiment: str = "NEUTRAL"
    action_required: bool = False
    timestamp: str = field(default_factory=utc_now)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PerformanceMetricHook:
    """Prepares data schema for future Section 31D performance tracking."""
    metric_id: str
    venture_id: str
    campaign_id: str
    post_id: str
    platform: str
    metric_name: str  # VIEWS, IMPRESSIONS, REACH, WATCH_TIME, LIKES, CONVERSIONS, etc.
    metric_value: float
    observed_at: str = field(default_factory=utc_now)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# --------------------------------------------------------------------------
# Platform Capability Matrix
# --------------------------------------------------------------------------

@dataclass
class PlatformCapabilityDetail:
    platform: str
    platform_capabilities: List[str]
    current_connector_capabilities: List[str]
    current_account_permissions: List[str]
    max_video_seconds: Optional[int] = None
    aspect_ratios: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def get_authoritative_capability_matrix() -> Dict[str, PlatformCapabilityDetail]:
    """Distinguishes Platform Capability vs. Connector Capability vs. Account Permission."""
    return {
        "INSTAGRAM": PlatformCapabilityDetail(
            platform="INSTAGRAM",
            platform_capabilities=[
                "POST_TEXT", "POST_IMAGE", "POST_VIDEO", "POST_CAROUSEL",
                "SHORT_FORM_VIDEO", "STORY", "REEL", "SCHEDULE", "ANALYTICS",
                "READ_COMMENTS", "READ_MESSAGES", "PRODUCT_TAGGING"
            ],
            current_connector_capabilities=[
                "POST_TEXT", "POST_IMAGE", "POST_VIDEO", "REEL",
                "DRAFT_PACKAGE_BUILD", "ASSET_FORMAT_VALIDATE"
            ],
            current_account_permissions=[
                "READ_INSIGHTS", "PAGES_MANAGE_POSTS", "INSTAGRAM_BASIC"
            ],
            max_video_seconds=900,
            aspect_ratios=["1:1", "4:5", "9:16"],
        ),
        "FACEBOOK": PlatformCapabilityDetail(
            platform="FACEBOOK",
            platform_capabilities=[
                "POST_TEXT", "POST_IMAGE", "POST_VIDEO", "POST_CAROUSEL",
                "REEL", "STORY", "SCHEDULE", "DELETE", "READ_COMMENTS",
                "RESPOND_COMMENT", "ANALYTICS"
            ],
            current_connector_capabilities=[
                "POST_TEXT", "POST_IMAGE", "POST_VIDEO", "READ_POST_STATUS",
                "DRY_RUN_PUBLISH"
            ],
            current_account_permissions=[
                "PAGES_SHOW_LIST", "PAGES_READ_ENGAGEMENT", "PAGES_MANAGE_POSTS"
            ],
            max_video_seconds=7200,
            aspect_ratios=["16:9", "1:1", "9:16"],
        ),
        "TIKTOK": PlatformCapabilityDetail(
            platform="TIKTOK",
            platform_capabilities=[
                "SHORT_FORM_VIDEO", "POST_IMAGE_CAROUSEL", "COMMERCE_LISTING",
                "PRODUCT_TAGGING", "READ_COMMENTS", "ANALYTICS"
            ],
            current_connector_capabilities=[
                "SHORT_FORM_VIDEO", "VERTICAL_FORMAT_VALIDATE"
            ],
            current_account_permissions=[],  # Account not connected yet
            max_video_seconds=600,
            aspect_ratios=["9:16"],
        ),
        "YOUTUBE": PlatformCapabilityDetail(
            platform="YOUTUBE",
            platform_capabilities=[
                "LONG_FORM_VIDEO", "SHORT_FORM_VIDEO", "POST_COMMUNITY_TEXT",
                "POST_COMMUNITY_IMAGE", "SCHEDULE", "READ_COMMENTS", "ANALYTICS"
            ],
            current_connector_capabilities=[
                "METADATA_SEARCH", "TRANSCRIPT_INTAKE", "VIDEO_FORMAT_VALIDATE"
            ],
            current_account_permissions=[
                "YOUTUBE_READONLY"
            ],
            max_video_seconds=43200,
            aspect_ratios=["16:9", "9:16"],
        ),
        "LINKEDIN": PlatformCapabilityDetail(
            platform="LINKEDIN",
            platform_capabilities=[
                "POST_TEXT", "POST_IMAGE", "POST_VIDEO", "POST_CAROUSEL",
                "POLL", "ARTICLE", "SCHEDULE", "ANALYTICS", "READ_COMMENTS"
            ],
            current_connector_capabilities=[
                "POST_TEXT", "BUSINESS_COPY_PACKAGE"
            ],
            current_account_permissions=[],  # Requires Ray OAuth
            max_video_seconds=600,
            aspect_ratios=["1:1", "16:9", "4:5"],
        ),
        "STOREFRONT": PlatformCapabilityDetail(
            platform="STOREFRONT",
            platform_capabilities=[
                "HOST_LANDING_PAGE", "COLLECT_LEADS", "COMMERCE_CHECKOUT"
            ],
            current_connector_capabilities=[
                "HOST_LANDING_PAGE", "BUILD_EDITORIAL_HTML"
            ],
            current_account_permissions=[
                "LOCAL_FILE_SERVE"
            ],
            max_video_seconds=None,
            aspect_ratios=["ALL"],
        ),
    }


# --------------------------------------------------------------------------
# Channel Account Registry Manager
# --------------------------------------------------------------------------

class ChannelAccountRegistryManager:
    """Manages external distribution account records with venture scoping."""

    def __init__(self, accounts: Optional[Sequence[ChannelAccount]] = None) -> None:
        self._accounts: Dict[str, ChannelAccount] = {}
        if accounts:
            for acc in accounts:
                self.register_account(acc)

    def register_account(self, account: ChannelAccount) -> ChannelAccount:
        self._accounts[account.channel_account_id] = account
        return account

    def get_account(self, account_id: str) -> Optional[ChannelAccount]:
        return self._accounts.get(account_id)

    def list_accounts_for_venture(self, venture_id: str) -> List[ChannelAccount]:
        return [acc for acc in self._accounts.values() if acc.is_authorized_for_venture(venture_id)]

    def list_all_accounts(self) -> List[ChannelAccount]:
        return list(self._accounts.values())


# --------------------------------------------------------------------------
# Multi-Venture Distribution Governance Gate
# --------------------------------------------------------------------------

class DistributionGovernanceGate:
    """Enforces lineage, venture scope, asset scope, and product truth before post approval."""

    def __init__(
        self,
        account_registry: ChannelAccountRegistryManager,
        capability_matrix: Optional[Dict[str, PlatformCapabilityDetail]] = None,
    ) -> None:
        self.registry = account_registry
        self.capability_matrix = capability_matrix or get_authoritative_capability_matrix()
        self._asset_scopes: Dict[str, AssetScopeRecord] = {}
        self._campaign_venture_map: Dict[str, str] = {}

    def register_asset_scope(self, asset_scope: AssetScopeRecord) -> None:
        self._asset_scopes[asset_scope.asset_id] = asset_scope

    def register_campaign_venture(self, campaign_id: str, venture_id: str) -> None:
        self._campaign_venture_map[campaign_id] = venture_id

    def validate_distribution_job(
        self,
        job: DistributionJob,
        skip_truth_check: bool = False,
    ) -> Tuple[bool, List[str]]:
        """Evaluates all isolation and truth rules for a proposed distribution job."""
        rejection_reasons = []

        # 1. Campaign -> Venture Scope Integrity
        expected_venture = self._campaign_venture_map.get(job.campaign_id)
        if expected_venture and expected_venture != job.venture_id:
            rejection_reasons.append(
                f"CAMPAIGN_VENTURE_SCOPE_MISMATCH: campaign '{job.campaign_id}' is bound to venture '{expected_venture}', not '{job.venture_id}'"
            )

        # 2. Venture -> Account Scope Integrity
        account = self.registry.get_account(job.channel_account_id)
        if not account:
            rejection_reasons.append(f"UNKNOWN_CHANNEL_ACCOUNT: '{job.channel_account_id}' is not registered")
        else:
            if not account.is_authorized_for_venture(job.venture_id):
                rejection_reasons.append(
                    f"VENTURE_ACCOUNT_SCOPE_MISMATCH: account '{job.channel_account_id}' (scope={account.venture_scope}) is not authorized for venture '{job.venture_id}'"
                )
            if account.platform != job.platform:
                rejection_reasons.append(
                    f"PLATFORM_MISMATCH: job platform '{job.platform}' does not match account platform '{account.platform}'"
                )

        # 3. Asset Scope Integrity (Cross-Venture & Cross-Campaign)
        for asset_id in job.asset_ids:
            scope_rec = self._asset_scopes.get(asset_id)
            if scope_rec:
                allowed, reason = scope_rec.is_usable_by(job.venture_id, job.campaign_id)
                if not allowed:
                    rejection_reasons.append(reason)

        # 4. Product Truth & Anti-Slop Audit (Part 14)
        if not skip_truth_check:
            from scripts.creative.product_truth_validator import ProductTruthValidator
            truth_res = ProductTruthValidator.audit_copy(job.copy)
            if truth_res["status"] != "PASS":
                for v in truth_res["violations"]:
                    rejection_reasons.append(f"PRODUCT_TRUTH_VIOLATION: {v['violation']} (matched '{v['matched_text']}')")

        # 5. Media Format & Platform Limit Validation
        cap = self.capability_matrix.get(job.platform)
        if cap and cap.max_video_seconds and job.content_type in ("FEED_VIDEO", "VERTICAL_REEL", "SHORT_FORM_VIDEO"):
            duration = job.media.get("duration_seconds", 0)
            if duration > cap.max_video_seconds:
                rejection_reasons.append(
                    f"PLATFORM_MEDIA_LIMIT_EXCEEDED: video duration {duration}s exceeds {job.platform} limit of {cap.max_video_seconds}s"
                )

        passed = len(rejection_reasons) == 0
        return passed, rejection_reasons

    def approve_job(self, job: DistributionJob, ray_approval_receipt: str) -> Tuple[bool, str]:
        """Strictly requires explicit Ray approval receipt before changing job status to APPROVED."""
        if not ray_approval_receipt or not ray_approval_receipt.strip():
            return False, "APPROVAL_REQUIRED: A valid Ray approval receipt is required to transition to APPROVED"
        valid, reasons = self.validate_distribution_job(job)
        if not valid:
            return False, f"JOB_VALIDATION_FAILED: {'; '.join(reasons)}"
        job.status = DistributionJobStatus.APPROVED
        job.approval_status = "APPROVED_BY_RAY"
        return True, "JOB_APPROVED"


# --------------------------------------------------------------------------
# Multi-Venture Seed Factory
# --------------------------------------------------------------------------

CREDENTIAL_REGISTRY_PATH = Path(__file__).resolve().parents[2] / "configs" / "nexus_credential_registry.json"
HOLIDAY_META_CREDENTIAL_ID = "credential.meta.social.holiday.prod.v1"
HOLIDAY_FACEBOOK_PAGE_ID = "1722332634511930"
HOLIDAY_INSTAGRAM_ACCOUNT_ID = "17841480885973564"  # live-verified via Raytestpage 2026-11-12


def _credential_live_state(credential_id: str) -> Tuple[str, bool, Optional[str]]:
    """Derive channel auth state from the canonical credential registry (no secrets).

    Only an AVAILABLE credential whose last live health check PASSED yields
    AUTHENTICATED + publish_allowed; anything else fails closed.
    """
    try:
        data = json.loads(CREDENTIAL_REGISTRY_PATH.read_text())
        entries = data["credentials"] if isinstance(data, dict) else data
        entry = next(e for e in entries if e.get("credential_id") == credential_id)
    except Exception:
        return "AUTH_REQUIRED", False, None
    check = entry.get("last_health_check") or {}
    if entry.get("status") == "AVAILABLE" and check.get("status") == "PASS":
        return "AUTHENTICATED", True, check.get("checked_at")
    return "AUTH_REQUIRED", False, check.get("checked_at")


def create_seed_channel_accounts() -> List[ChannelAccount]:
    """Establishes baseline registered distribution accounts across test ventures."""
    holiday_meta_auth, holiday_meta_publish, holiday_meta_checked = _credential_live_state(HOLIDAY_META_CREDENTIAL_ID)
    return [
        # Venture 1: Holiday Commerce Pilot
        ChannelAccount(
            channel_account_id="acc_holiday_tiktok_01",
            platform="TIKTOK",
            account_name="@holidayritualmugs",
            account_type="BUSINESS",
            account_scope=AccountScopeType.SINGLE_VENTURE,
            venture_scope=["vnt_holiday_commerce_pilot_2026"],
            auth_status="AUTH_REQUIRED",
            connection_status="INACTIVE",
            capabilities=["SHORT_FORM_VIDEO", "COMMERCE_LISTING"],
            publish_allowed=False,
            schedule_allowed=False,
            credential_reference="env:TIKTOK_SHOP_HOLIDAY_TOKEN",
            last_health_check=utc_now(),
        ),
        ChannelAccount(
            channel_account_id="acc_holiday_instagram_01",
            platform="INSTAGRAM",
            account_name="@the612amritual",
            account_type="PROFESSIONAL",
            account_scope=AccountScopeType.SINGLE_VENTURE,
            venture_scope=["vnt_holiday_commerce_pilot_2026"],
            auth_status=holiday_meta_auth,
            connection_status="CONNECTED",
            capabilities=["POST_IMAGE", "POST_VIDEO", "REEL", "STORY"],
            publish_allowed=holiday_meta_publish,
            schedule_allowed=False,
            credential_reference=HOLIDAY_META_CREDENTIAL_ID,
            last_health_check=holiday_meta_checked or utc_now(),
            external_account_id=HOLIDAY_INSTAGRAM_ACCOUNT_ID,
        ),
        ChannelAccount(
            channel_account_id="acc_holiday_facebook_01",
            platform="FACEBOOK",
            account_name="Raytestpage",
            account_type="PAGE",
            account_scope=AccountScopeType.SINGLE_VENTURE,
            venture_scope=["vnt_holiday_commerce_pilot_2026"],
            auth_status=holiday_meta_auth,
            connection_status="CONNECTED",
            capabilities=["POST_TEXT", "POST_IMAGE", "POST_VIDEO"],
            publish_allowed=holiday_meta_publish,
            schedule_allowed=False,
            credential_reference=HOLIDAY_META_CREDENTIAL_ID,
            last_health_check=holiday_meta_checked or utc_now(),
            external_account_id=HOLIDAY_FACEBOOK_PAGE_ID,
        ),
        ChannelAccount(
            channel_account_id="acc_holiday_storefront_01",
            platform="STOREFRONT",
            account_name="the612amritual.cc",
            account_type="STOREFRONT",
            account_scope=AccountScopeType.SINGLE_VENTURE,
            venture_scope=["vnt_holiday_commerce_pilot_2026"],
            auth_status="AUTHENTICATED",
            connection_status="CONNECTED",
            capabilities=["HOST_LANDING_PAGE", "COLLECT_LEADS"],
            publish_allowed=False,  # Held until Ray approval
            schedule_allowed=False,
            credential_reference="env:STOREFRONT_API_KEY",
            last_health_check=utc_now(),
        ),

        # Venture 2: KRD Ability
        ChannelAccount(
            channel_account_id="acc_krd_linkedin_01",
            platform="LINKEDIN",
            account_name="KRD Ability Corporation",
            account_type="PAGE",
            account_scope=AccountScopeType.SINGLE_VENTURE,
            venture_scope=["vnt_krd_ability_2026"],
            auth_status="REQUIRES_RAY_LOGIN",
            connection_status="INACTIVE",
            capabilities=["POST_TEXT", "POST_IMAGE", "POST_VIDEO"],
            publish_allowed=False,
            schedule_allowed=False,
            credential_reference="env:LINKEDIN_KRD_TOKEN",
            last_health_check=utc_now(),
        ),

        # Venture 3: GoClear Funding Readiness
        ChannelAccount(
            channel_account_id="acc_goclear_facebook_01",
            platform="FACEBOOK",
            account_name="GoClear Online",
            account_type="PAGE",
            account_scope=AccountScopeType.SINGLE_VENTURE,
            venture_scope=["vnt_goclear_credit_2026"],
            auth_status="AUTHENTICATED",
            connection_status="PARTIAL",
            capabilities=["POST_TEXT", "POST_IMAGE", "POST_VIDEO"],
            publish_allowed=False,  # Dry run only
            schedule_allowed=False,
            credential_reference="env:META_PAGE_ACCESS_TOKEN",
            last_health_check=utc_now(),
        ),

        # Shared Channel: Master Nexus YouTube Channel
        ChannelAccount(
            channel_account_id="acc_shared_nexus_youtube_01",
            platform="YOUTUBE",
            account_name="Nexus Operations Hub",
            account_type="CREATOR",
            account_scope=AccountScopeType.SHARED,
            venture_scope=["vnt_holiday_commerce_pilot_2026", "vnt_krd_ability_2026", "vnt_goclear_credit_2026"],
            auth_status="AUTHENTICATED",
            connection_status="CONNECTED",
            capabilities=["LONG_FORM_VIDEO", "SHORT_FORM_VIDEO"],
            publish_allowed=False,
            schedule_allowed=False,
            credential_reference="env:YOUTUBE_API_REFRESH_TOKEN",
            last_health_check=utc_now(),
        ),
    ]
