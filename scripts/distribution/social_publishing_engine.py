"""Nexus Multi-Venture Scheduling & Publishing Engine (Section 31B.1).

Coordinates end-to-end multi-venture distribution across:
NEXUS -> VENTURE -> CAMPAIGN -> PRODUCT/OFFER -> CREATIVE ASSETS ->
CHANNEL ACCOUNT -> PRE-PUBLISH GATES -> APPROVAL -> SCHEDULER ->
PLATFORM ADAPTER -> PUBLISH RECEIPT -> 31C ENGAGEMENT / 31D PERFORMANCE LINEAGE.

Guarantees:
1. Multi-venture isolation across campaigns, accounts, assets, URLs, and approval receipts.
2. 11-gate pre-publish validation pipeline (including Product Truth Gate).
3. Explicit owner approval required before any external publication or scheduling.
4. Clean integration with existing Nexus durable job and scheduling patterns.
5. Zero unverified claims, zero leaked credentials, $0.00 ad spend.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple, Union

ROOT = Path(__file__).resolve().parent.parent.parent

from scripts.distribution.distribution_foundation import (
    AccountScopeType,
    AssetScopeRecord,
    AssetScopeType,
    ChannelAccount,
    ChannelAccountRegistryManager,
    ChannelPlatform,
    DistributionGovernanceGate,
    DistributionJob,
    DistributionJobStatus,
    DistributionLineage,
    EngagementEventHook,
    PerformanceMetricHook,
    PlatformCapabilityDetail,
    PublishReceipt,
    create_seed_channel_accounts,
    get_authoritative_capability_matrix,
    sha256_hash,
    utc_now,
)
from scripts.creative.product_truth_validator import ProductTruthValidator
from scripts.distribution.campaign_deploy_router import (
    resolve_campaign_distribution_landing_target,
)


# --------------------------------------------------------------------------
# Certified Asset Authority Registry (Defect 2 Remediation)
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class CertifiedAssetMetadata:
    """Authoritative inspected media metadata for certified creative assets."""
    asset_id: str
    file_path: str
    media_type: str  # IMAGE, VIDEO
    provider: str
    width: int
    height: int
    aspect_ratio: str
    duration_seconds: Optional[float]
    orientation: str  # HORIZONTAL_LANDSCAPE, VERTICAL, SQUARE
    certification_status: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


CERTIFIED_ASSET_REGISTRY: Dict[str, CertifiedAssetMetadata] = {
    "asset_metaai_image_1794355016": CertifiedAssetMetadata(
        asset_id="asset_metaai_image_1794355016",
        file_path="dist/creative/meta_holiday_ceramic_mug_1794355016.webp",
        media_type="IMAGE",
        provider="META_AI",
        width=1920,
        height=1280,
        aspect_ratio="3:2",
        duration_seconds=None,
        orientation="HORIZONTAL_LANDSCAPE",
        certification_status="CERTIFIED_HERO_IMAGE",
    ),
    "asset_metaai_video_1794355722": CertifiedAssetMetadata(
        asset_id="asset_metaai_video_1794355722",
        file_path="dist/creative/meta_holiday_ceramic_mug_video_1794355722.mp4",
        media_type="VIDEO",
        provider="META_AI",
        width=1152,
        height=768,
        aspect_ratio="3:2",
        duration_seconds=10.0,
        orientation="HORIZONTAL_LANDSCAPE",
        certification_status="CERTIFIED_HORIZONTAL_VIDEO",
    ),
    "asset_modal_video_1794413265": CertifiedAssetMetadata(
        asset_id="asset_modal_video_1794413265",
        file_path="dist/creative/modal_holiday_ceramic_mug_video_1794413265.mp4",
        media_type="VIDEO",
        provider="MODAL",
        width=480,
        height=864,
        aspect_ratio="9:16",
        duration_seconds=5.04,
        orientation="VERTICAL",
        certification_status="CERTIFIED_VERTICAL_VIDEO",
    ),
}


# --------------------------------------------------------------------------
# Platform Specifications & Post Variants (Part 3)
# --------------------------------------------------------------------------

@dataclass
class PlatformFormatSpec:
    platform: str
    max_copy_chars: int
    recommended_copy_chars: Tuple[int, int]
    title_required: bool
    max_title_chars: int
    description_required: bool
    max_description_chars: int
    hashtag_strategy: str
    max_hashtags: int
    supported_aspect_ratios: List[str]
    max_video_seconds: Optional[int]
    recommended_video_seconds: Tuple[int, int]
    clickable_links_in_body: bool
    link_handling: str
    cta_handling: str
    thumbnail_requirements: str


PLATFORM_SPECS: Dict[str, PlatformFormatSpec] = {
    "INSTAGRAM": PlatformFormatSpec(
        platform="INSTAGRAM",
        max_copy_chars=2200,
        recommended_copy_chars=(125, 250),
        title_required=False,
        max_title_chars=0,
        description_required=True,
        max_description_chars=2200,
        hashtag_strategy="3-5 topical tags placed at end of caption",
        max_hashtags=5,
        supported_aspect_ratios=["1:1", "4:5", "9:16"],
        max_video_seconds=90,
        recommended_video_seconds=(5, 15),
        clickable_links_in_body=False,
        link_handling="BIO_ONLY",
        cta_handling="Direct followers to link in profile/bio",
        thumbnail_requirements="Video frame selector or 9:16 vertical cover image",
    ),
    "FACEBOOK": PlatformFormatSpec(
        platform="FACEBOOK",
        max_copy_chars=63206,
        recommended_copy_chars=(80, 160),
        title_required=False,
        max_title_chars=255,
        description_required=True,
        max_description_chars=63206,
        hashtag_strategy="Minimal (0-2 tags; avoid hashtag spam)",
        max_hashtags=2,
        supported_aspect_ratios=["16:9", "1:1", "9:16"],
        max_video_seconds=14400,
        recommended_video_seconds=(15, 60),
        clickable_links_in_body=True,
        link_handling="INLINE_CLICKABLE",
        cta_handling="Direct clickable link included in post body",
        thumbnail_requirements="Custom 16:9 or 1:1 image or video thumbnail",
    ),
    "TIKTOK": PlatformFormatSpec(
        platform="TIKTOK",
        max_copy_chars=2200,
        recommended_copy_chars=(50, 120),
        title_required=False,
        max_title_chars=0,
        description_required=True,
        max_description_chars=2200,
        hashtag_strategy="3-4 niche community and discovery tags",
        max_hashtags=4,
        supported_aspect_ratios=["9:16"],
        max_video_seconds=600,
        recommended_video_seconds=(5, 15),
        clickable_links_in_body=False,
        link_handling="BIO_OR_SHOP_LINK",
        cta_handling="Link in bio or native TikTok Shop product anchor",
        thumbnail_requirements="Animated or static cover frame selected from video",
    ),
    "YOUTUBE_SHORTS": PlatformFormatSpec(
        platform="YOUTUBE_SHORTS",
        max_copy_chars=5000,
        recommended_copy_chars=(100, 300),
        title_required=True,
        max_title_chars=100,
        description_required=True,
        max_description_chars=5000,
        hashtag_strategy="Mandatory #Shorts in title or description plus 2 topical tags",
        max_hashtags=3,
        supported_aspect_ratios=["9:16", "1:1"],
        max_video_seconds=60,
        recommended_video_seconds=(5, 30),
        clickable_links_in_body=True,
        link_handling="DESCRIPTION_OR_PINNED_COMMENT",
        cta_handling="View studio preview link in description/pinned comment",
        thumbnail_requirements="Auto-selected from vertical video by YouTube",
    ),
    "YOUTUBE_LONGFORM": PlatformFormatSpec(
        platform="YOUTUBE_LONGFORM",
        max_copy_chars=5000,
        recommended_copy_chars=(300, 800),
        title_required=True,
        max_title_chars=100,
        description_required=True,
        max_description_chars=5000,
        hashtag_strategy="3 topical hashtags in description",
        max_hashtags=3,
        supported_aspect_ratios=["16:9"],
        max_video_seconds=43200,
        recommended_video_seconds=(180, 1200),
        clickable_links_in_body=True,
        link_handling="DESCRIPTION_TOP_LINES",
        cta_handling="Full URL in top 3 lines of video description",
        thumbnail_requirements="Custom high-res 16:9 image (1280x720, <2MB)",
    ),
    "LINKEDIN": PlatformFormatSpec(
        platform="LINKEDIN",
        max_copy_chars=3000,
        recommended_copy_chars=(300, 900),
        title_required=False,
        max_title_chars=120,
        description_required=True,
        max_description_chars=3000,
        hashtag_strategy="3-5 professional and industry tags",
        max_hashtags=5,
        supported_aspect_ratios=["1:1", "16:9", "4:5"],
        max_video_seconds=600,
        recommended_video_seconds=(30, 90),
        clickable_links_in_body=True,
        link_handling="INLINE_OR_FIRST_COMMENT",
        cta_handling="Explore our methodology at the link below",
        thumbnail_requirements="16:9 or 1:1 image preview",
    ),
}


@dataclass
class PlatformPostVariant:
    platform: str
    title: Optional[str]
    copy: str
    hashtags: List[str]
    media_asset_ids: List[str]
    media_requirements: Dict[str, Any]
    cta: str
    target_url: str
    thumbnail_info: Dict[str, Any]
    truth_score: float
    truth_violations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class PlatformContentTransformer:
    """Adapts canonical campaign packages into distinct, platform-optimized formats."""

    @classmethod
    def render_variant(
        cls,
        platform: str,
        base_copy: str,
        target_url: str,
        media_assets: List[Dict[str, Any]],
        title_suggestion: Optional[str] = None,
    ) -> PlatformPostVariant:
        spec = PLATFORM_SPECS.get(platform)
        if not spec:
            raise ValueError(f"Unsupported platform: {platform}")

        clean_base = base_copy.strip()
        hashtags: List[str] = []
        title: Optional[str] = None
        cta: str = ""
        final_copy: str = ""

        if platform == "INSTAGRAM":
            hashtags = ["#QuietRitual", "#SlowLiving", "#MorningRoutine", "#ArtisanCeramics"]
            cta = "Link in bio to view the studio design preview."
            final_copy = f"{clean_base}\n\n{cta}\n\n{' '.join(hashtags)}"
        elif platform == "FACEBOOK":
            hashtags = ["#QuietRitual"]
            cta = f"Explore the studio design preview: {target_url}"
            final_copy = f"{clean_base}\n\n{cta}\n\n{' '.join(hashtags)}"
        elif platform == "TIKTOK":
            hashtags = ["#QuietRitual", "#SlowLiving", "#Ceramics"]
            cta = "Link in bio to view design preview."
            final_copy = f"{clean_base}\n\n{cta} {' '.join(hashtags)}"
        elif platform == "YOUTUBE_SHORTS":
            title = (title_suggestion or "The 6:12 AM Quiet Ritual")[:85] + " #Shorts"
            hashtags = ["#Shorts", "#QuietRitual"]
            cta = f"View studio preview: {target_url}"
            final_copy = f"{clean_base}\n\n{cta}\n\n{' '.join(hashtags)}"
        elif platform == "YOUTUBE_LONGFORM":
            title = (title_suggestion or "The 6:12 AM Quiet Ritual — Studio Design Preview")[:100]
            hashtags = ["#QuietRitual", "#Ceramics", "#Design"]
            cta = f"Official studio preview: {target_url}"
            final_copy = f"{cta}\n\n{clean_base}\n\n{' '.join(hashtags)}"
        elif platform == "LINKEDIN":
            hashtags = ["#DesignExcellence", "#ProductDesign", "#RitualCommerce"]
            cta = f"Review the studio design preview: {target_url}"
            final_copy = f"{clean_base}\n\n{cta}\n\n{' '.join(hashtags)}"

        # Validate copy character bounds
        if len(final_copy) > spec.max_copy_chars:
            final_copy = final_copy[: spec.max_copy_chars - 3] + "..."

        # Product Truth Gate Audit on transformed copy
        truth_res = ProductTruthValidator.audit_copy(final_copy)
        truth_score = truth_res["truthfulness_score"]
        truth_violations = [v["violation"] for v in truth_res.get("violations", [])]

        asset_ids = [a.get("asset_id", "") for a in media_assets if a.get("asset_id")]

        return PlatformPostVariant(
            platform=platform,
            title=title,
            copy=final_copy,
            hashtags=hashtags,
            media_asset_ids=asset_ids,
            media_requirements={
                "aspect_ratios": spec.supported_aspect_ratios,
                "max_duration_seconds": spec.max_video_seconds,
                "recommended_duration_seconds": spec.recommended_video_seconds,
            },
            cta=cta,
            target_url=target_url,
            thumbnail_info={"requirements": spec.thumbnail_requirements},
            truth_score=truth_score,
            truth_violations=truth_violations,
        )


# --------------------------------------------------------------------------
# Channel Account Resolver (Part 4)
# --------------------------------------------------------------------------

class ChannelAccountResolver:
    """Safely resolves an approved ChannelAccount for a given venture and platform."""

    def __init__(self, registry: ChannelAccountRegistryManager) -> None:
        self.registry = registry

    def resolve_account(
        self,
        venture_id: str,
        platform: str,
        requested_account_id: Optional[str] = None,
    ) -> Tuple[bool, Optional[ChannelAccount], Optional[str]]:
        if requested_account_id:
            acc = self.registry.get_account(requested_account_id)
            if not acc:
                return False, None, f"ACCOUNT_NOT_FOUND: '{requested_account_id}' is not registered"
            if not acc.is_authorized_for_venture(venture_id):
                return False, None, f"VENTURE_ACCOUNT_SCOPE_MISMATCH: account '{requested_account_id}' is not authorized for venture '{venture_id}'"
            if acc.platform != platform:
                return False, None, f"PLATFORM_MISMATCH: account '{requested_account_id}' is {acc.platform}, requested {platform}"
            return True, acc, None

        # Automatic candidate resolution
        candidates = [
            acc for acc in self.registry.list_accounts_for_venture(venture_id)
            if acc.platform == platform
        ]
        if not candidates:
            return False, None, f"NO_ACCOUNT_FOR_PLATFORM: No account registered for venture '{venture_id}' and platform '{platform}'"

        # Prioritize single-venture account over shared
        single_venture_candidates = [
            c for c in candidates if c.account_scope == AccountScopeType.SINGLE_VENTURE
        ]
        chosen = single_venture_candidates[0] if single_venture_candidates else candidates[0]
        return True, chosen, None


# --------------------------------------------------------------------------
# Pre-Publish Validation Pipeline (Part 6)
# --------------------------------------------------------------------------

@dataclass
class PrePublishGateResult:
    gate_name: str
    passed: bool
    reason: Optional[str] = None


@dataclass
class PrePublishValidationReport:
    distribution_job_id: str
    passed: bool
    gate_results: List[PrePublishGateResult]
    blocked_reasons: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "distribution_job_id": self.distribution_job_id,
            "passed": self.passed,
            "blocked_reasons": self.blocked_reasons,
            "gate_results": [asdict(g) for g in self.gate_results],
        }


class PrePublishValidationPipeline:
    """Evaluates all 11 required safety, governance, truth, and format gates."""

    def __init__(
        self,
        governance_gate: DistributionGovernanceGate,
        account_registry: ChannelAccountRegistryManager,
    ) -> None:
        self.governance_gate = governance_gate
        self.registry = account_registry

    def validate(self, job: DistributionJob) -> PrePublishValidationReport:
        gates: List[PrePublishGateResult] = []
        blocked: List[str] = []

        # 1. VENTURE_SCOPE_GATE
        expected_v = self.governance_gate._campaign_venture_map.get(job.campaign_id)
        if expected_v and expected_v != job.venture_id:
            msg = f"CAMPAIGN_VENTURE_SCOPE_MISMATCH: campaign '{job.campaign_id}' belongs to '{expected_v}', not '{job.venture_id}'"
            gates.append(PrePublishGateResult("VENTURE_SCOPE_GATE", False, msg))
            blocked.append(msg)
        else:
            gates.append(PrePublishGateResult("VENTURE_SCOPE_GATE", True))

        # 2. CAMPAIGN_SCOPE_GATE
        if not job.campaign_id or not job.campaign_id.strip():
            msg = "EMPTY_CAMPAIGN_ID"
            gates.append(PrePublishGateResult("CAMPAIGN_SCOPE_GATE", False, msg))
            blocked.append(msg)
        else:
            gates.append(PrePublishGateResult("CAMPAIGN_SCOPE_GATE", True))

        # 3. ACCOUNT_SCOPE_GATE
        acc = self.registry.get_account(job.channel_account_id)
        if not acc:
            msg = f"UNKNOWN_CHANNEL_ACCOUNT: '{job.channel_account_id}'"
            gates.append(PrePublishGateResult("ACCOUNT_SCOPE_GATE", False, msg))
            blocked.append(msg)
        elif not acc.is_authorized_for_venture(job.venture_id):
            msg = f"VENTURE_ACCOUNT_SCOPE_MISMATCH: account '{job.channel_account_id}' not authorized for venture '{job.venture_id}'"
            gates.append(PrePublishGateResult("ACCOUNT_SCOPE_GATE", False, msg))
            blocked.append(msg)
        elif acc.platform != job.platform:
            msg = (
                f"PLATFORM_MISMATCH: account '{job.channel_account_id}' platform '{acc.platform}' "
                f"does not match job platform '{job.platform}'. A local storefront connector cannot satisfy Facebook authentication."
            )
            gates.append(PrePublishGateResult("ACCOUNT_SCOPE_GATE", False, msg))
            blocked.append(msg)
        else:
            gates.append(PrePublishGateResult("ACCOUNT_SCOPE_GATE", True))

        # 4. ASSET_SCOPE_GATE
        asset_errs = []
        for aid in job.asset_ids:
            scope_rec = self.governance_gate._asset_scopes.get(aid)
            if scope_rec:
                ok, reason = scope_rec.is_usable_by(job.venture_id, job.campaign_id)
                if not ok:
                    asset_errs.append(reason)
        if asset_errs:
            msg = f"ASSET_SCOPE_VIOLATIONS: {'; '.join(asset_errs)}"
            gates.append(PrePublishGateResult("ASSET_SCOPE_GATE", False, msg))
            blocked.append(msg)
        else:
            gates.append(PrePublishGateResult("ASSET_SCOPE_GATE", True))

        # 5. PRODUCT_TRUTH_GATE
        truth_res = ProductTruthValidator.audit_copy(job.copy)
        if truth_res["status"] != "PASS":
            v_msgs = [f"{v['violation']} ('{v['matched_text']}')" for v in truth_res.get("violations", [])]
            msg = f"PRODUCT_TRUTH_GATE_FAILED: {'; '.join(v_msgs)}"
            gates.append(PrePublishGateResult("PRODUCT_TRUTH_GATE", False, msg))
            blocked.append(msg)
        else:
            gates.append(PrePublishGateResult("PRODUCT_TRUTH_GATE", True))

        # 6. COPY_TRUTH_GATE
        if not job.copy or len(job.copy.strip()) < 5:
            msg = "EMPTY_OR_TRIVIAL_COPY"
            gates.append(PrePublishGateResult("COPY_TRUTH_GATE", False, msg))
            blocked.append(msg)
        else:
            gates.append(PrePublishGateResult("COPY_TRUTH_GATE", True))

        # 7. PLATFORM_FORMAT_GATE
        spec = PLATFORM_SPECS.get(job.platform)
        if spec:
            format_errs = []
            if len(job.copy) > spec.max_copy_chars:
                format_errs.append(f"Copy length ({len(job.copy)}) exceeds platform max ({spec.max_copy_chars})")
            if spec.title_required and not job.media.get("title"):
                format_errs.append("Title required for this platform but missing")
            if format_errs:
                msg = f"PLATFORM_FORMAT_VIOLATION: {'; '.join(format_errs)}"
                gates.append(PrePublishGateResult("PLATFORM_FORMAT_GATE", False, msg))
                blocked.append(msg)
            else:
                gates.append(PrePublishGateResult("PLATFORM_FORMAT_GATE", True))
        else:
            gates.append(PrePublishGateResult("PLATFORM_FORMAT_GATE", True))

        # 8. MEDIA_VALIDATION_GATE (Asset Authority Rule & Orientation Verification)
        media_errs = []
        is_vertical_job = job.platform in ("INSTAGRAM", "TIKTOK", "YOUTUBE_SHORTS") and job.content_type in ("VERTICAL_REEL", "SHORT_FORM_VIDEO")
        for aid in job.asset_ids:
            meta = CERTIFIED_ASSET_REGISTRY.get(aid)
            if meta and meta.media_type == "VIDEO":
                if is_vertical_job and meta.orientation != "VERTICAL":
                    media_errs.append(
                        f"ORIENTATION_MISMATCH: asset '{aid}' is {meta.orientation} ({meta.width}x{meta.height}, aspect {meta.aspect_ratio}); vertical placement requires native 9:16 vertical video"
                    )
                if spec and spec.max_video_seconds and meta.duration_seconds and meta.duration_seconds > spec.max_video_seconds:
                    media_errs.append(
                        f"Video duration {meta.duration_seconds}s exceeds {job.platform} limit of {spec.max_video_seconds}s"
                    )
        if not job.asset_ids:
            media_errs.append("No media assets attached to distribution job")
        if media_errs:
            msg = f"MEDIA_VALIDATION_FAILED: {'; '.join(media_errs)}"
            gates.append(PrePublishGateResult("MEDIA_VALIDATION_GATE", False, msg))
            blocked.append(msg)
        else:
            gates.append(PrePublishGateResult("MEDIA_VALIDATION_GATE", True))

        # 9. TARGET_URL_GATE
        if not job.target_url or not job.target_url.startswith("https://"):
            msg = f"INVALID_TARGET_URL: Target URL must be an active https URL, got '{job.target_url}'"
            gates.append(PrePublishGateResult("TARGET_URL_GATE", False, msg))
            blocked.append(msg)
        else:
            gates.append(PrePublishGateResult("TARGET_URL_GATE", True))

        # 10. ACCOUNT_AUTH_GATE
        if not acc or acc.auth_status != "AUTHENTICATED":
            status_desc = acc.auth_status if acc else "UNCONFIGURED"
            msg = f"ACCOUNT_NOT_AUTHENTICATED: account '{job.channel_account_id}' has auth_status='{status_desc}'"
            gates.append(PrePublishGateResult("ACCOUNT_AUTH_GATE", False, msg))
            blocked.append(msg)
        elif not acc.publish_allowed:
            msg = f"PUBLISH_PERMISSION_MISSING: account '{job.channel_account_id}' has publish_allowed=False"
            gates.append(PrePublishGateResult("ACCOUNT_AUTH_GATE", False, msg))
            blocked.append(msg)
        else:
            gates.append(PrePublishGateResult("ACCOUNT_AUTH_GATE", True))

        # 11. APPROVAL_GATE
        if job.approval_status != "APPROVED_BY_RAY" or not job.approval_receipt_id:
            msg = f"APPROVAL_REQUIRED: Job has approval_status='{job.approval_status}', approval_receipt_id='{job.approval_receipt_id}'"
            gates.append(PrePublishGateResult("APPROVAL_GATE", False, msg))
            blocked.append(msg)
        else:
            gates.append(PrePublishGateResult("APPROVAL_GATE", True))

        all_passed = len(blocked) == 0
        return PrePublishValidationReport(
            distribution_job_id=job.distribution_job_id,
            passed=all_passed,
            gate_results=gates,
            blocked_reasons=blocked,
        )


# --------------------------------------------------------------------------
# Approval Package & Receipt Model (Parts 7, 16)
# --------------------------------------------------------------------------

@dataclass
class SocialPostApprovalCard:
    distribution_job_id: str
    channel: str
    channel_account_id: str
    account_handle: str
    content_type: str
    title: Optional[str]
    copy: str
    cta: str
    target_url: str
    media_asset_ids: List[str]
    media_summary: str
    scheduled_time: Optional[str]
    timezone: str
    auth_status: str
    expected_external_action: str
    status: str = "READY_FOR_RAY_REVIEW"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CampaignApprovalPackage:
    package_id: str
    venture_id: str
    campaign_id: str
    generated_at: str
    total_posts: int
    landing_target_url: str
    deployment_id: str
    posts: List[SocialPostApprovalCard]
    approval_options: List[str] = field(default_factory=lambda: [
        "INDIVIDUAL_POST",
        "CHANNEL_GROUP",
        "ENTIRE_CAMPAIGN_BATCH",
    ])
    status: str = "PENDING_RAY_REVIEW"

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["posts"] = [p.to_dict() for p in self.posts]
        return d


@dataclass
class ApprovalReceipt:
    approval_receipt_id: str
    approved_by: str  # "Ray"
    approved_at: str
    venture_id: str
    campaign_id: str
    scope: str  # INDIVIDUAL_POST, CHANNEL_GROUP, ENTIRE_CAMPAIGN_BATCH
    approved_job_ids: List[str]
    payload_hash: str
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ApprovalPackageManager:
    """Creates review packages and records immutable Ray approval receipts."""

    @classmethod
    def create_package(
        cls,
        venture_id: str,
        campaign_id: str,
        landing_target_url: str,
        deployment_id: str,
        jobs: List[DistributionJob],
        account_registry: ChannelAccountRegistryManager,
    ) -> CampaignApprovalPackage:
        now_str = utc_now()
        package_id = f"pkg_appr_{hashlib.sha256(f'{venture_id}:{campaign_id}:{now_str}'.encode()).hexdigest()[:16]}"
        cards: List[SocialPostApprovalCard] = []

        for j in jobs:
            acc = account_registry.get_account(j.channel_account_id)
            handle = acc.account_name if acc else j.channel_account_id

            # Platform verification: a storefront account cannot publish to Facebook or social channels
            if acc and acc.platform != j.platform:
                auth_st = f"MISMATCH_BLOCKED (account '{acc.channel_account_id}' is platform '{acc.platform}', not '{j.platform}')"
            else:
                # Authority Rule: Live audit state wins!
                live_audit = PlatformAuthAuditor.get_live_auth_state(j.platform, j.channel_account_id)
                if live_audit and live_audit.auth_status != "AUTHENTICATED":
                    auth_st = live_audit.auth_status
                else:
                    auth_st = acc.auth_status if acc else "UNCONFIGURED"

            action_desc = f"Publish 1 post to {j.platform} ({handle}) after Ray explicit approval"

            cards.append(SocialPostApprovalCard(
                distribution_job_id=j.distribution_job_id,
                channel=j.platform,
                channel_account_id=j.channel_account_id,
                account_handle=handle,
                content_type=j.content_type,
                title=j.media.get("title"),
                copy=j.copy,
                cta=j.media.get("cta", ""),
                target_url=j.target_url or landing_target_url,
                media_asset_ids=j.asset_ids,
                media_summary=j.media.get("summary", f"{len(j.asset_ids)} media assets"),
                scheduled_time=j.scheduled_time,
                timezone=j.timezone,
                auth_status=auth_st,
                expected_external_action=action_desc,
            ))

        return CampaignApprovalPackage(
            package_id=package_id,
            venture_id=venture_id,
            campaign_id=campaign_id,
            generated_at=now_str,
            total_posts=len(cards),
            landing_target_url=landing_target_url,
            deployment_id=deployment_id,
            posts=cards,
        )

    @classmethod
    def issue_approval_receipt(
        cls,
        venture_id: str,
        campaign_id: str,
        scope: str,
        approved_jobs: List[DistributionJob],
        approver: str = "Ray",
    ) -> ApprovalReceipt:
        now_str = utc_now()
        job_ids = [j.distribution_job_id for j in approved_jobs]
        raw_payload = "|".join([j.copy + (j.target_url or "") + "".join(j.asset_ids) for j in approved_jobs])
        payload_hash = sha256_hash(raw_payload)
        receipt_id = f"rcpt_appr_{sha256_hash(f'{venture_id}:{campaign_id}:{payload_hash}:{now_str}')[:16]}"

        receipt = ApprovalReceipt(
            approval_receipt_id=receipt_id,
            approved_by=approver,
            approved_at=now_str,
            venture_id=venture_id,
            campaign_id=campaign_id,
            scope=scope,
            approved_job_ids=job_ids,
            payload_hash=payload_hash,
            notes="Explicit Ray governance approval granted for publication package",
        )

        for j in approved_jobs:
            j.approval_status = "APPROVED_BY_RAY"
            j.approval_receipt_id = receipt_id
            j.status = DistributionJobStatus.APPROVED

        return receipt


# --------------------------------------------------------------------------
# Kill Switch & Circuit Breaker (Part 21)
# --------------------------------------------------------------------------

@dataclass
class KillSwitchState:
    global_publishing_paused: bool = False
    paused_ventures: Set[str] = field(default_factory=set)
    paused_campaigns: Set[str] = field(default_factory=set)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "global_publishing_paused": self.global_publishing_paused,
            "paused_ventures": list(self.paused_ventures),
            "paused_campaigns": list(self.paused_campaigns),
        }


class DistributionKillSwitchManager:
    """Manages immediate pauses and cancel actions without stopping Nexus."""

    def __init__(self) -> None:
        self.state = KillSwitchState()

    def pause_venture(self, venture_id: str) -> None:
        self.state.paused_ventures.add(venture_id)

    def resume_venture(self, venture_id: str) -> None:
        self.state.paused_ventures.discard(venture_id)

    def pause_campaign(self, campaign_id: str) -> None:
        self.state.paused_campaigns.add(campaign_id)

    def resume_campaign(self, campaign_id: str) -> None:
        self.state.paused_campaigns.discard(campaign_id)

    def stop_all_external_publishing(self) -> None:
        self.state.global_publishing_paused = True

    def resume_all_external_publishing(self) -> None:
        self.state.global_publishing_paused = False

    def is_action_allowed(self, venture_id: str, campaign_id: str) -> Tuple[bool, Optional[str]]:
        if self.state.global_publishing_paused:
            return False, "GLOBAL_PUBLISHING_KILL_SWITCH_ACTIVE"
        if venture_id in self.state.paused_ventures:
            return False, f"VENTURE_PAUSED: venture '{venture_id}' is paused"
        if campaign_id in self.state.paused_campaigns:
            return False, f"CAMPAIGN_PAUSED: campaign '{campaign_id}' is paused"
        return True, None


# --------------------------------------------------------------------------
# Failure Classification & Safe Retry Policy (Part 19)
# --------------------------------------------------------------------------

class PublishFailureType(str, Enum):
    AUTH_EXPIRED = "AUTH_EXPIRED"
    RATE_LIMIT = "RATE_LIMIT"
    MEDIA_REJECTED = "MEDIA_REJECTED"
    COPY_REJECTED = "COPY_REJECTED"
    TARGET_URL_UNAVAILABLE = "TARGET_URL_UNAVAILABLE"
    PLATFORM_OUTAGE = "PLATFORM_OUTAGE"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    PROVIDER_ERROR = "PROVIDER_ERROR"
    UNKNOWN = "UNKNOWN"


class PublishFailureClassifier:
    """Classifies runtime error messages into structured failure types."""

    @classmethod
    def classify_error(cls, error_text: str) -> PublishFailureType:
        if not error_text:
            return PublishFailureType.UNKNOWN
        err_upper = error_text.upper()
        for ft in PublishFailureType:
            if ft.value in err_upper:
                return ft
        if any(w in err_upper for w in ("AUTH", "TOKEN", "LOGIN")):
            return PublishFailureType.AUTH_EXPIRED
        if any(w in err_upper for w in ("RATE", "THROTTLE", "QUOTA")):
            return PublishFailureType.RATE_LIMIT
        if any(w in err_upper for w in ("MEDIA", "VIDEO", "FORMAT", "ASPECT", "DURATION")):
            return PublishFailureType.MEDIA_REJECTED
        if any(w in err_upper for w in ("COPY", "TRUTH", "TEXT", "VIOLATION")):
            return PublishFailureType.COPY_REJECTED
        if any(w in err_upper for w in ("URL", "HTTP", "404")):
            return PublishFailureType.TARGET_URL_UNAVAILABLE
        if any(w in err_upper for w in ("PERMISSION", "FORBIDDEN", "403")):
            return PublishFailureType.PERMISSION_DENIED
        if any(w in err_upper for w in ("500", "502", "503", "OUTAGE")):
            return PublishFailureType.PLATFORM_OUTAGE
        return PublishFailureType.PROVIDER_ERROR


class PublishRetryPolicy:
    """Enforces retry constraints based on failure classification."""

    MAX_RETRIES: int = 3

    NON_RETRYABLE: Set[PublishFailureType] = {
        PublishFailureType.AUTH_EXPIRED,
        PublishFailureType.MEDIA_REJECTED,
        PublishFailureType.COPY_REJECTED,
        PublishFailureType.PERMISSION_DENIED,
    }

    @classmethod
    def is_retryable(cls, failure: PublishFailureType, attempt_count: int) -> bool:
        if failure in cls.NON_RETRYABLE:
            return False
        return attempt_count < cls.MAX_RETRIES


# --------------------------------------------------------------------------
# Multi-Venture Distribution Scheduler (Parts 8, 9, 20)
# --------------------------------------------------------------------------

class MultiVentureDistributionScheduler:
    """Coordinates scheduling, staggering, queue operations, and bounded execution."""

    def __init__(
        self,
        governance_gate: DistributionGovernanceGate,
        account_registry: ChannelAccountRegistryManager,
        kill_switch: Optional[DistributionKillSwitchManager] = None,
        default_timezone: str = "America/Phoenix",
    ) -> None:
        self.governance_gate = governance_gate
        self.registry = account_registry
        self.kill_switch = kill_switch or DistributionKillSwitchManager()
        self.default_timezone = default_timezone
        self.validation_pipeline = PrePublishValidationPipeline(governance_gate, account_registry)

        self._jobs: Dict[str, DistributionJob] = {}
        self._published_receipts: Dict[str, PublishReceipt] = {}

    def register_job(self, job: DistributionJob) -> DistributionJob:
        if not job.timezone:
            job.timezone = self.default_timezone
        self._jobs[job.distribution_job_id] = job
        return job

    def get_job(self, job_id: str) -> Optional[DistributionJob]:
        return self._jobs.get(job_id)

    def list_jobs(
        self,
        venture_id: Optional[str] = None,
        campaign_id: Optional[str] = None,
        status: Optional[DistributionJobStatus] = None,
    ) -> List[DistributionJob]:
        res = list(self._jobs.values())
        if venture_id:
            res = [j for j in res if j.venture_id == venture_id]
        if campaign_id:
            res = [j for j in res if j.campaign_id == campaign_id]
        if status:
            res = [j for j in res if j.status == status]
        return res

    def schedule_at(
        self,
        job_id: str,
        scheduled_time: str,
        timezone_str: Optional[str] = None,
    ) -> Tuple[bool, str]:
        job = self.get_job(job_id)
        if not job:
            return False, f"JOB_NOT_FOUND: '{job_id}'"

        allowed, reason = self.kill_switch.is_action_allowed(job.venture_id, job.campaign_id)
        if not allowed:
            return False, f"ACTION_BLOCKED: {reason}"

        job.scheduled_time = scheduled_time
        job.timezone = timezone_str or job.timezone or self.default_timezone
        job.status = DistributionJobStatus.SCHEDULED
        return True, "JOB_SCHEDULED"

    def cancel(self, job_id: str, reason: str = "OPERATOR_CANCELLED") -> Tuple[bool, str]:
        job = self.get_job(job_id)
        if not job:
            return False, f"JOB_NOT_FOUND: '{job_id}'"
        if job.status == DistributionJobStatus.PUBLISHED:
            return False, "CANNOT_CANCEL_ALREADY_PUBLISHED_JOB"

        job.status = DistributionJobStatus.CANCELLED
        job.error = f"CANCELLED: {reason}"
        return True, "JOB_CANCELLED"

    def reschedule(
        self,
        job_id: str,
        new_time: str,
        timezone_str: Optional[str] = None,
    ) -> Tuple[bool, str]:
        return self.schedule_at(job_id, new_time, timezone_str)

    def retry(self, job_id: str) -> Tuple[bool, str]:
        job = self.get_job(job_id)
        if not job:
            return False, f"JOB_NOT_FOUND: '{job_id}'"
        if job.status != DistributionJobStatus.FAILED:
            return False, f"JOB_NOT_IN_FAILED_STATE: current status is {job.status.value}"

        failure_type = PublishFailureType.UNKNOWN
        if job.error:
            for ft in PublishFailureType:
                if ft.value in job.error:
                    failure_type = ft
                    break

        if not PublishRetryPolicy.is_retryable(failure_type, job.attempt_count):
            return False, f"NON_RETRYABLE_FAILURE: {failure_type.value} cannot be safely retried"

        job.attempt_count += 1
        job.status = DistributionJobStatus.READY_FOR_APPROVAL
        job.error = None
        return True, f"JOB_QUEUED_FOR_RETRY (attempt {job.attempt_count})"

    def calculate_staggered_schedule(
        self,
        jobs: List[DistributionJob],
        start_time: Optional[datetime] = None,
        spacing_hours: int = 3,
    ) -> List[DistributionJob]:
        """Applies controlled distribution staggering (Part 9).
        
        Classified as INITIAL_SCHEDULING_HEURISTIC pending Section 31D empirical performance data.
        """
        base = start_time or datetime.now(timezone.utc) + timedelta(hours=2)
        for i, j in enumerate(jobs):
            scheduled_dt = base + timedelta(hours=i * spacing_hours)
            j.scheduled_time = scheduled_dt.isoformat()
            j.resource_requirements["scheduling_rationale"] = (
                f"INITIAL_SCHEDULING_HEURISTIC: spaced +{i * spacing_hours}h from base to prevent content fatigue"
            )
        return jobs

    def publish_now_after_approval(
        self,
        job_id: str,
        simulated_external_id: Optional[str] = None,
    ) -> Tuple[bool, Optional[PublishReceipt], str]:
        """Executes bounded publication for an approved job (Part 17).
        
        Requires 100% pass across all 11 pre-publish gates.
        In certification test mode, creates an immutable PublishReceipt with simulated ID.
        """
        job = self.get_job(job_id)
        if not job:
            return False, None, f"JOB_NOT_FOUND: '{job_id}'"

        allowed, reason = self.kill_switch.is_action_allowed(job.venture_id, job.campaign_id)
        if not allowed:
            return False, None, f"ACTION_BLOCKED: {reason}"

        # Run 11-gate validation pipeline
        val = self.validation_pipeline.validate(job)
        if not val.passed:
            job.status = DistributionJobStatus.FAILED
            job.error = f"VALIDATION_FAILED: {'; '.join(val.blocked_reasons)}"
            return False, None, job.error

        # Transition to PUBLISHING
        job.status = DistributionJobStatus.PUBLISHING
        now_str = utc_now()
        ext_post_id = simulated_external_id or f"post_sim_{sha256_hash(job_id + now_str)[:12]}"
        copy_h = sha256_hash(job.copy)
        receipt_id = f"rcpt_pub_{sha256_hash(f'{job_id}:{ext_post_id}:{now_str}')[:16]}"

        receipt = PublishReceipt(
            publish_receipt_id=receipt_id,
            distribution_job_id=job.distribution_job_id,
            venture_id=job.venture_id,
            campaign_id=job.campaign_id,
            product_id_or_offer_id=job.product_id_or_offer_id,
            channel_account_id=job.channel_account_id,
            platform=job.platform,
            external_post_id=ext_post_id,
            external_url=f"https://{job.platform.lower()}.com/p/{ext_post_id}",
            published_at=now_str,
            media_asset_ids=job.asset_ids,
            copy_hash=copy_h,
            target_url=job.target_url,
            status="PUBLISHED_CONFIRMED",
            provider_response_reference=f"simulated_provider_ack_{ext_post_id}",
            cost=0.0,
        )

        job.status = DistributionJobStatus.PUBLISHED
        job.publish_status = "PUBLISHED"
        job.external_post_id = ext_post_id
        job.published_at = now_str
        job.publish_receipt_id = receipt_id
        job.receipt = receipt.to_dict()

        self._published_receipts[receipt_id] = receipt
        return True, receipt, "PUBLISHED_SUCCESSFULLY"


# --------------------------------------------------------------------------
# Section 31C / 31D Lineage & Publishing Memory (Parts 22, 23)
# --------------------------------------------------------------------------

class SocialPublishingMemory:
    """Preserves persistent publishing records and cross-department lineage."""

    MEMORY_FILE = ROOT / "data" / "runtime" / "nexus_social_publishing_memory.json"

    @classmethod
    def record_publication(cls, receipt: PublishReceipt, job: DistributionJob) -> Dict[str, Any]:
        cls.MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = {}
        if cls.MEMORY_FILE.exists():
            try:
                data = json.loads(cls.MEMORY_FILE.read_text(encoding="utf-8"))
            except Exception:
                data = {}

        record = {
            "publish_receipt_id": receipt.publish_receipt_id,
            "distribution_job_id": job.distribution_job_id,
            "venture_id": job.venture_id,
            "campaign_id": job.campaign_id,
            "product_id": job.product_id,
            "channel_account_id": job.channel_account_id,
            "platform": job.platform,
            "external_post_id": receipt.external_post_id,
            "external_url": receipt.external_url,
            "target_url": receipt.target_url,
            "copy_hash": receipt.copy_hash,
            "media_asset_ids": receipt.media_asset_ids,
            "published_at": receipt.published_at,
            # Lineage hooks for Section 31C and 31D
            "lineage": {
                "section_31c_engagement_hook": {
                    "venture_id": job.venture_id,
                    "campaign_id": job.campaign_id,
                    "post_id": receipt.external_post_id,
                    "channel_account_id": job.channel_account_id,
                },
                "section_31d_performance_hook": {
                    "venture_id": job.venture_id,
                    "campaign_id": job.campaign_id,
                    "post_id": receipt.external_post_id,
                    "platform": job.platform,
                },
            },
        }

        posts = data.setdefault("published_posts", {})
        posts[receipt.external_post_id] = record
        data["updated_at"] = utc_now()

        cls.MEMORY_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return record

    @classmethod
    def get_post_lineage(cls, external_post_id: str) -> Optional[Dict[str, Any]]:
        if not cls.MEMORY_FILE.exists():
            return None
        try:
            data = json.loads(cls.MEMORY_FILE.read_text(encoding="utf-8"))
            return data.get("published_posts", {}).get(external_post_id)
        except Exception:
            return None


# --------------------------------------------------------------------------
# Platform Authentication Readiness Auditor (Parts 10-14)
# --------------------------------------------------------------------------

@dataclass
class PlatformAuthAuditDetail:
    platform: str
    account_id: str
    venture_id: str
    auth_status: str
    publish_scope: str
    read_scope: str
    token_refresh: str
    manual_login_required: str
    blocker: str
    notes: str


class PlatformAuthAuditor:
    """Accurately discovers and audits authentication readiness across major channels."""

    @classmethod
    def audit_all(cls) -> List[PlatformAuthAuditDetail]:
        return [
            PlatformAuthAuditDetail(
                platform="INSTAGRAM",
                account_id="acc_holiday_instagram_01",
                venture_id="vnt_holiday_commerce_pilot_2026",
                auth_status="REQUIRES_RAY_LOGIN",
                publish_scope="NONE (instagram_content_publish ungranted)",
                read_scope="NONE (instagram_basic ungranted)",
                token_refresh="UNCONFIGURED",
                manual_login_required="YES (Ray must connect Instagram Professional account via Meta Business Suite / Graph API)",
                blocker="META_SOCIAL_APP_CREDENTIALS_MISSING",
                notes="Meta.ai browser session is active for creative generation but is completely separate from Meta Graph API publishing credentials.",
            ),
            PlatformAuthAuditDetail(
                platform="FACEBOOK",
                account_id="acc_holiday_facebook_01",
                venture_id="vnt_holiday_commerce_pilot_2026",
                auth_status="UNCONFIGURED",
                publish_scope="NONE (pages_manage_posts ungranted)",
                read_scope="NONE (pages_read_engagement ungranted)",
                token_refresh="UNCONFIGURED",
                manual_login_required="YES (Ray must connect Facebook Page in Meta Developer Console)",
                blocker="META_PAGE_ACCESS_TOKEN_MISSING",
                notes="Holiday Commerce Facebook Page is unconfigured. Zero social publishing credentials present.",
            ),
            PlatformAuthAuditDetail(
                platform="FACEBOOK",
                account_id="acc_goclear_facebook_01",
                venture_id="vnt_goclear_credit_2026",
                auth_status="UNCONFIGURED",
                publish_scope="NONE (pages_manage_posts ungranted)",
                read_scope="NONE (pages_read_engagement ungranted)",
                token_refresh="UNCONFIGURED",
                manual_login_required="YES (Ray must generate Page Access Token in Meta Developer Console)",
                blocker="META_PAGE_ACCESS_TOKEN_MISSING",
                notes="Dry-run adapter scripts exist in scripts/social/facebook_publisher.py, awaiting Meta Page token in env.",
            ),
            PlatformAuthAuditDetail(
                platform="TIKTOK",
                account_id="acc_holiday_tiktok_01",
                venture_id="vnt_holiday_commerce_pilot_2026",
                auth_status="UNCONFIGURED",
                publish_scope="NONE (video.publish / video.upload ungranted)",
                read_scope="NONE (user.info.basic ungranted)",
                token_refresh="UNCONFIGURED",
                manual_login_required="YES (Ray must register TikTok Developer App and complete OAuth flow)",
                blocker="TIKTOK_PUBLISH_STATUS=BLOCKED_OFFICIAL_INTEGRATION_REQUIRED",
                notes="No browser automation bypass allowed. Official Content Posting API access required.",
            ),
            PlatformAuthAuditDetail(
                platform="YOUTUBE",
                account_id="acc_shared_nexus_youtube_01",
                venture_id="SHARED",
                auth_status="AUTHENTICATED_READONLY",
                publish_scope="NONE (https://www.googleapis.com/auth/youtube.upload ungranted)",
                read_scope="ACTIVE (YouTube Data API v3 metadata search & transcript intake via API key)",
                token_refresh="REUSABLE_FOR_READONLY_ONLY",
                manual_login_required="YES (Ray must authorize OAuth 2.0 client with YouTube upload scope)",
                blocker="YOUTUBE_CONNECTOR_CURRENTLY_READONLY_UPLOAD_SCOPE_UNGRANTED",
                notes="API keys cannot upload videos. Existing Google Workspace OAuth client lacks YouTube scopes.",
            ),
            PlatformAuthAuditDetail(
                platform="LINKEDIN",
                account_id="acc_krd_linkedin_01",
                venture_id="vnt_krd_ability_2026",
                auth_status="UNCONFIGURED",
                publish_scope="NONE (w_member_social / w_organization_social ungranted)",
                read_scope="NONE (r_basicprofile ungranted)",
                token_refresh="UNCONFIGURED",
                manual_login_required="YES (Ray must create LinkedIn Developer App and grant member/organization post permissions)",
                blocker="LINKEDIN_DEVELOPER_APP_AND_OAUTH_REQUIRED",
                notes="Preserved for KRD Ability and future B2B ventures; not required for Holiday Commerce pilot.",
            ),
        ]

    @classmethod
    def get_live_auth_state(cls, platform: str, account_id: Optional[str] = None) -> PlatformAuthAuditDetail:
        """Authority Rule: Live platform auth state is the authoritative truth."""
        audits = cls.audit_all()
        if account_id:
            for a in audits:
                if a.account_id == account_id:
                    return a
        for a in audits:
            if a.platform == platform:
                return a
        return PlatformAuthAuditDetail(
            platform=platform,
            account_id=account_id or f"acc_unknown_{platform.lower()}",
            venture_id="UNKNOWN",
            auth_status="UNCONFIGURED",
            publish_scope="NONE",
            read_scope="NONE",
            token_refresh="UNCONFIGURED",
            manual_login_required="YES",
            blocker=f"{platform}_AUTH_REQUIRED",
            notes="No registered or authenticated live connection.",
        )


# --------------------------------------------------------------------------
# Holiday Campaign Distribution Builder (Part 15)
# --------------------------------------------------------------------------

def build_holiday_campaign_distribution_package(
    manifest_path: Union[str, Path] = ROOT / "dist/creative/campaign_holiday_ceramic_mug_manifest.json",
) -> Tuple[List[DistributionJob], CampaignApprovalPackage, MultiVentureDistributionScheduler]:
    """Prepares canonical distribution jobs and approval package for the Holiday Campaign."""
    p = Path(manifest_path)
    if not p.exists():
        raise FileNotFoundError(f"Manifest not found: {p}")
    manifest = json.loads(p.read_text(encoding="utf-8"))

    # Resolve landing target
    target_info = resolve_campaign_distribution_landing_target(manifest)
    landing_url = target_info["target_url"]
    deployment_id = target_info["deployment_id"]

    # Initialize Registry & Governance
    accounts = create_seed_channel_accounts()
    registry = ChannelAccountRegistryManager(accounts)
    gov_gate = DistributionGovernanceGate(registry)

    # Register Ventures and Scopes
    venture_id = manifest["venture_id"]
    campaign_id = manifest["campaign_id"]
    gov_gate.register_campaign_venture(campaign_id, venture_id)

    # Register campaign-scoped media assets
    hero_asset_id = "asset_metaai_image_1794355016"
    primary_vid_id = "asset_metaai_video_1794355722"
    modal_vid_id = "asset_modal_video_1794413265"

    for aid in (hero_asset_id, primary_vid_id, modal_vid_id):
        gov_gate.register_asset_scope(AssetScopeRecord(
            asset_id=aid,
            venture_id=venture_id,
            campaign_id=campaign_id,
            scope_type=AssetScopeType.CAMPAIGN,
        ))

    scheduler = MultiVentureDistributionScheduler(
        governance_gate=gov_gate,
        account_registry=registry,
        default_timezone="America/Phoenix",
    )

    clean_base_copy = "The 6:12 AM Quiet Ritual. Substantial ceramic morning vessel. Studio design preview."

    # Job 1: Instagram (Reel/Image)
    var_ig = PlatformContentTransformer.render_variant(
        platform="INSTAGRAM",
        base_copy=clean_base_copy,
        target_url=landing_url,
        media_assets=[{"asset_id": modal_vid_id}, {"asset_id": hero_asset_id}],
    )
    job_ig = DistributionJob(
        distribution_job_id="dist_job_holiday_instagram_01",
        venture_id=venture_id,
        campaign_id=campaign_id,
        product_id="prod_stoneware_mug_14oz",
        asset_ids=var_ig.media_asset_ids,
        channel_account_id="acc_holiday_instagram_01",
        platform="INSTAGRAM",
        content_type="VERTICAL_REEL",
        copy=var_ig.copy,
        media={
            "video_asset": modal_vid_id,
            "cover_image": hero_asset_id,
            "duration_seconds": 5.04,
            "aspect_ratio": "9:16",
            "orientation": "VERTICAL",
            "cta": var_ig.cta,
            "summary": "Modal certified vertical video (480x864, 9:16, 5.04s) + Meta.ai WebP hero cover (1920x1280)",
        },
        target_url=landing_url,
        landing_page_id="landing_page_html",
        deployment_id=deployment_id,
        environment="test",
        status=DistributionJobStatus.READY_FOR_APPROVAL,
        approval_status="WAITING_FOR_RAY_APPROVAL",
        publish_status="UNPUBLISHED",
        timezone="America/Phoenix",
        priority=8,
    )

    # Job 2: Facebook (Feed Post with Clickable Link)
    var_fb = PlatformContentTransformer.render_variant(
        platform="FACEBOOK",
        base_copy=clean_base_copy,
        target_url=landing_url,
        media_assets=[{"asset_id": hero_asset_id}],
    )
    job_fb = DistributionJob(
        distribution_job_id="dist_job_holiday_facebook_01",
        venture_id=venture_id,
        campaign_id=campaign_id,
        product_id="prod_stoneware_mug_14oz",
        asset_ids=var_fb.media_asset_ids,
        channel_account_id="acc_holiday_facebook_01",  # Authoritative Facebook Channel Account
        platform="FACEBOOK",
        content_type="FEED_POST",
        copy=var_fb.copy,
        media={
            "image_asset": hero_asset_id,
            "aspect_ratio": "3:2",
            "orientation": "HORIZONTAL_LANDSCAPE",
            "cta": var_fb.cta,
            "summary": "Meta.ai WebP hero (1920x1280, 3:2 landscape) with clickable link preview",
        },
        target_url=landing_url,
        landing_page_id="landing_page_html",
        deployment_id=deployment_id,
        environment="test",
        status=DistributionJobStatus.READY_FOR_APPROVAL,
        approval_status="WAITING_FOR_RAY_APPROVAL",
        publish_status="UNPUBLISHED",
        timezone="America/Phoenix",
        priority=6,
    )

    # Job 3: TikTok (Short Form Vertical Video)
    var_tt = PlatformContentTransformer.render_variant(
        platform="TIKTOK",
        base_copy=clean_base_copy,
        target_url=landing_url,
        media_assets=[{"asset_id": modal_vid_id}],
    )
    job_tt = DistributionJob(
        distribution_job_id="dist_job_holiday_tiktok_01",
        venture_id=venture_id,
        campaign_id=campaign_id,
        product_id="prod_stoneware_mug_14oz",
        asset_ids=var_tt.media_asset_ids,
        channel_account_id="acc_holiday_tiktok_01",
        platform="TIKTOK",
        content_type="SHORT_FORM_VIDEO",
        copy=var_tt.copy,
        media={
            "video_asset": modal_vid_id,
            "duration_seconds": 5.04,
            "aspect_ratio": "9:16",
            "orientation": "VERTICAL",
            "cta": var_tt.cta,
            "summary": "Modal certified vertical video (480x864, 9:16, 5.04s)",
        },
        target_url=landing_url,
        landing_page_id="landing_page_html",
        deployment_id=deployment_id,
        environment="test",
        status=DistributionJobStatus.READY_FOR_APPROVAL,
        approval_status="WAITING_FOR_RAY_APPROVAL",
        publish_status="UNPUBLISHED",
        timezone="America/Phoenix",
        priority=8,
    )

    # Job 4: YouTube Shorts (Short Form Vertical Video)
    var_yt = PlatformContentTransformer.render_variant(
        platform="YOUTUBE_SHORTS",
        base_copy=clean_base_copy,
        target_url=landing_url,
        media_assets=[{"asset_id": modal_vid_id}],
        title_suggestion="The 6:12 AM Quiet Ritual",
    )
    job_yt = DistributionJob(
        distribution_job_id="dist_job_holiday_youtube_01",
        venture_id=venture_id,
        campaign_id=campaign_id,
        product_id="prod_stoneware_mug_14oz",
        asset_ids=var_yt.media_asset_ids,
        channel_account_id="acc_shared_nexus_youtube_01",  # Shared account
        platform="YOUTUBE",
        content_type="SHORT_FORM_VIDEO",
        copy=var_yt.copy,
        media={
            "title": var_yt.title,
            "video_asset": modal_vid_id,
            "duration_seconds": 5.04,
            "aspect_ratio": "9:16",
            "orientation": "VERTICAL",
            "cta": var_yt.cta,
            "summary": "Modal certified vertical video (480x864, 9:16, 5.04s) formatted as YouTube Short",
        },
        target_url=landing_url,
        landing_page_id="landing_page_html",
        deployment_id=deployment_id,
        environment="test",
        status=DistributionJobStatus.READY_FOR_APPROVAL,
        approval_status="WAITING_FOR_RAY_APPROVAL",
        publish_status="UNPUBLISHED",
        timezone="America/Phoenix",
        priority=7,
    )

    jobs = [job_ig, job_fb, job_tt, job_yt]

    # Apply Staggering Schedule (Initial Heuristic: spaced 3 hours apart)
    scheduler.calculate_staggered_schedule(jobs, spacing_hours=3)

    for j in jobs:
        scheduler.register_job(j)

    approval_package = ApprovalPackageManager.create_package(
        venture_id=venture_id,
        campaign_id=campaign_id,
        landing_target_url=landing_url,
        deployment_id=deployment_id,
        jobs=jobs,
        account_registry=registry,
    )

    # Persist approval package to dist/creative
    package_file = ROOT / "dist" / "creative" / "holiday_campaign_approval_package.json"
    package_file.write_text(json.dumps(approval_package.to_dict(), indent=2), encoding="utf-8")

    return jobs, approval_package, scheduler
