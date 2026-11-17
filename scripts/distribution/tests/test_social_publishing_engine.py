"""Comprehensive Test Suite for Nexus Multi-Venture Scheduling & Publishing Engine (Section 31B.1)."""
from __future__ import annotations

import json
import pytest
from datetime import datetime, timezone
from pathlib import Path

from scripts.distribution.distribution_foundation import (
    AccountScopeType,
    AssetScopeRecord,
    AssetScopeType,
    ChannelAccount,
    ChannelAccountRegistryManager,
    DistributionGovernanceGate,
    DistributionJob,
    DistributionJobStatus,
    PublishReceipt,
    create_seed_channel_accounts,
)
from scripts.distribution.social_publishing_engine import (
    ApprovalPackageManager,
    CampaignApprovalPackage,
    ChannelAccountResolver,
    DistributionKillSwitchManager,
    PlatformAuthAuditor,
    PlatformContentTransformer,
    PLATFORM_SPECS,
    PrePublishValidationPipeline,
    PublishFailureClassifier,
    PublishFailureType,
    PublishRetryPolicy,
    MultiVentureDistributionScheduler,
    SocialPublishingMemory,
    build_holiday_campaign_distribution_package,
)


# --------------------------------------------------------------------------
# 1. Platform-Specific Rendering Tests (Part 3)
# --------------------------------------------------------------------------

def test_platform_transformations_all_channels():
    base_copy = "The 6:12 AM Quiet Ritual. Substantial ceramic morning vessel. Studio design preview."
    target_url = "https://nexus-campaigns.pages.dev/holiday-commerce-pilot/holiday-ceramic-mug/"
    media = [{"asset_id": "asset_img_01"}, {"asset_id": "asset_vid_01"}]

    platforms = ["INSTAGRAM", "FACEBOOK", "TIKTOK", "YOUTUBE_SHORTS", "YOUTUBE_LONGFORM", "LINKEDIN"]
    for p in platforms:
        var = PlatformContentTransformer.render_variant(
            platform=p,
            base_copy=base_copy,
            target_url=target_url,
            media_assets=media,
            title_suggestion="The 6:12 AM Quiet Ritual",
        )
        assert var.platform == p
        assert len(var.copy) > 0
        assert var.truth_score == 100.0
        assert len(var.truth_violations) == 0

        spec = PLATFORM_SPECS[p]
        assert len(var.copy) <= spec.max_copy_chars
        if spec.title_required:
            assert var.title is not None
            assert len(var.title) <= spec.max_title_chars

        if p == "INSTAGRAM":
            assert "bio" in var.cta.lower()
            assert "#QuietRitual" in var.copy
        elif p == "FACEBOOK":
            assert target_url in var.copy
        elif p == "TIKTOK":
            assert "bio" in var.cta.lower()
        elif p == "YOUTUBE_SHORTS":
            assert "#Shorts" in var.title
            assert target_url in var.copy
        elif p == "LINKEDIN":
            assert target_url in var.copy


def test_platform_transformations_product_truth_enforcement():
    """Unverified or invented claims must fail the product truth audit."""
    unverified_copy = "Handcrafted high-fire stoneware weighing exactly 485g with 14 oz capacity."
    target_url = "https://nexus-campaigns.pages.dev/holiday-commerce-pilot/holiday-ceramic-mug/"

    var = PlatformContentTransformer.render_variant(
        platform="INSTAGRAM",
        base_copy=unverified_copy,
        target_url=target_url,
        media_assets=[{"asset_id": "asset_01"}],
    )
    # Truth score must reflect violations
    assert var.truth_score < 100.0
    assert len(var.truth_violations) > 0


# --------------------------------------------------------------------------
# 2. Channel Account Resolution Tests (Part 4)
# --------------------------------------------------------------------------

def test_channel_account_resolution():
    accounts = create_seed_channel_accounts()
    registry = ChannelAccountRegistryManager(accounts)
    resolver = ChannelAccountResolver(registry)

    # Authorized Holiday Instagram account
    ok, acc, err = resolver.resolve_account("vnt_holiday_commerce_pilot_2026", "INSTAGRAM")
    assert ok is True
    assert acc.channel_account_id == "acc_holiday_instagram_01"
    assert err is None

    # Cross-venture account request -> BLOCK
    ok_cross, acc_cross, err_cross = resolver.resolve_account(
        "vnt_holiday_commerce_pilot_2026", "LINKEDIN", requested_account_id="acc_krd_linkedin_01"
    )
    assert ok_cross is False
    assert "VENTURE_ACCOUNT_SCOPE_MISMATCH" in err_cross

    # Shared account resolution -> ALLOW
    ok_shared, acc_shared, err_shared = resolver.resolve_account(
        "vnt_holiday_commerce_pilot_2026", "YOUTUBE", requested_account_id="acc_shared_nexus_youtube_01"
    )
    assert ok_shared is True
    assert acc_shared.channel_account_id == "acc_shared_nexus_youtube_01"


# --------------------------------------------------------------------------
# 3. Pre-Publish Validation Pipeline (Part 6)
# --------------------------------------------------------------------------

def test_pre_publish_pipeline_all_gates():
    accounts = create_seed_channel_accounts()
    # Mark one account as authenticated with publish permission for testing
    acc_auth = ChannelAccount(
        channel_account_id="acc_test_auth_01",
        platform="INSTAGRAM",
        account_name="@testauth",
        account_type="CREATOR",
        account_scope=AccountScopeType.SINGLE_VENTURE,
        venture_scope=["vnt_holiday_commerce_pilot_2026"],
        auth_status="AUTHENTICATED",
        connection_status="CONNECTED",
        capabilities=["POST_IMAGE", "POST_VIDEO"],
        publish_allowed=True,
        schedule_allowed=True,
    )
    accounts.append(acc_auth)
    registry = ChannelAccountRegistryManager(accounts)
    gov_gate = DistributionGovernanceGate(registry)
    gov_gate.register_campaign_venture("camp_holiday_2026", "vnt_holiday_commerce_pilot_2026")
    gov_gate.register_asset_scope(AssetScopeRecord(
        asset_id="asset_test_01",
        venture_id="vnt_holiday_commerce_pilot_2026",
        campaign_id="camp_holiday_2026",
        scope_type=AssetScopeType.CAMPAIGN,
    ))

    pipeline = PrePublishValidationPipeline(gov_gate, registry)

    # 1. Job missing approval -> Fails APPROVAL_GATE
    job_unapproved = DistributionJob(
        distribution_job_id="job_unapp_01",
        venture_id="vnt_holiday_commerce_pilot_2026",
        campaign_id="camp_holiday_2026",
        asset_ids=["asset_test_01"],
        channel_account_id="acc_test_auth_01",
        platform="INSTAGRAM",
        content_type="FEED_IMAGE",
        copy="The 6:12 AM Quiet Ritual. Substantial ceramic morning vessel. Studio design preview.",
        media={},
        target_url="https://nexus-campaigns.pages.dev/holiday-commerce-pilot/holiday-ceramic-mug/",
        status=DistributionJobStatus.READY_FOR_APPROVAL,
        approval_status="WAITING_FOR_RAY_APPROVAL",
    )
    report1 = pipeline.validate(job_unapproved)
    assert report1.passed is False
    assert any("APPROVAL_REQUIRED" in r for r in report1.blocked_reasons)

    # 2. Approved Job with valid receipt -> PASSES ALL 11 GATES
    job_approved = DistributionJob(
        distribution_job_id="job_app_01",
        venture_id="vnt_holiday_commerce_pilot_2026",
        campaign_id="camp_holiday_2026",
        asset_ids=["asset_test_01"],
        channel_account_id="acc_test_auth_01",
        platform="INSTAGRAM",
        content_type="FEED_IMAGE",
        copy="The 6:12 AM Quiet Ritual. Substantial ceramic morning vessel. Studio design preview.",
        media={},
        target_url="https://nexus-campaigns.pages.dev/holiday-commerce-pilot/holiday-ceramic-mug/",
        status=DistributionJobStatus.APPROVED,
        approval_status="APPROVED_BY_RAY",
        approval_receipt_id="rcpt_appr_mock_12345",
    )
    report2 = pipeline.validate(job_approved)
    assert report2.passed is True
    assert len(report2.blocked_reasons) == 0

    # 3. Product truth violation -> Fails PRODUCT_TRUTH_GATE
    job_truth_fail = DistributionJob(
        distribution_job_id="job_truth_fail",
        venture_id="vnt_holiday_commerce_pilot_2026",
        campaign_id="camp_holiday_2026",
        asset_ids=["asset_test_01"],
        channel_account_id="acc_test_auth_01",
        platform="INSTAGRAM",
        content_type="FEED_IMAGE",
        copy="High-fire stoneware weighing 485g with lifetime chip replacement.",
        media={},
        target_url="https://nexus-campaigns.pages.dev/holiday-commerce-pilot/holiday-ceramic-mug/",
        status=DistributionJobStatus.APPROVED,
        approval_status="APPROVED_BY_RAY",
        approval_receipt_id="rcpt_appr_mock_12345",
    )
    report3 = pipeline.validate(job_truth_fail)
    assert report3.passed is False
    assert any("PRODUCT_TRUTH_GATE_FAILED" in r for r in report3.blocked_reasons)


# --------------------------------------------------------------------------
# 4. Approval Package & Receipt Model (Parts 7, 16)
# --------------------------------------------------------------------------

def test_approval_package_and_receipt_issuance():
    accounts = create_seed_channel_accounts()
    registry = ChannelAccountRegistryManager(accounts)

    jobs = [
        DistributionJob(
            distribution_job_id="job_pkg_01",
            venture_id="vnt_holiday_commerce_pilot_2026",
            campaign_id="camp_holiday_2026",
            asset_ids=["asset_hero_01"],
            channel_account_id="acc_holiday_instagram_01",
            platform="INSTAGRAM",
            content_type="VERTICAL_REEL",
            copy="The 6:12 AM Quiet Ritual. Studio design preview.",
            media={"title": None, "cta": "Link in bio", "summary": "1 reel"},
            target_url="https://nexus-campaigns.pages.dev/holiday-commerce-pilot/holiday-ceramic-mug/",
        ),
        DistributionJob(
            distribution_job_id="job_pkg_02",
            venture_id="vnt_holiday_commerce_pilot_2026",
            campaign_id="camp_holiday_2026",
            asset_ids=["asset_hero_01"],
            channel_account_id="acc_holiday_storefront_01",
            platform="FACEBOOK",
            content_type="FEED_POST",
            copy="The 6:12 AM Quiet Ritual. Direct preview link below.",
            media={"title": None, "cta": "Explore preview", "summary": "1 post"},
            target_url="https://nexus-campaigns.pages.dev/holiday-commerce-pilot/holiday-ceramic-mug/",
        ),
    ]

    pkg = ApprovalPackageManager.create_package(
        venture_id="vnt_holiday_commerce_pilot_2026",
        campaign_id="camp_holiday_2026",
        landing_target_url="https://nexus-campaigns.pages.dev/holiday-commerce-pilot/holiday-ceramic-mug/",
        deployment_id="dep_holiday_123",
        jobs=jobs,
        account_registry=registry,
    )

    assert pkg.total_posts == 2
    assert pkg.status == "PENDING_RAY_REVIEW"
    assert len(pkg.posts) == 2

    # Issue approval receipt for entire campaign batch
    receipt = ApprovalPackageManager.issue_approval_receipt(
        venture_id="vnt_holiday_commerce_pilot_2026",
        campaign_id="camp_holiday_2026",
        scope="ENTIRE_CAMPAIGN_BATCH",
        approved_jobs=jobs,
        approver="Ray",
    )

    assert receipt.approved_by == "Ray"
    assert receipt.scope == "ENTIRE_CAMPAIGN_BATCH"
    assert len(receipt.approved_job_ids) == 2
    assert len(receipt.payload_hash) == 64

    for j in jobs:
        assert j.approval_status == "APPROVED_BY_RAY"
        assert j.approval_receipt_id == receipt.approval_receipt_id
        assert j.status == DistributionJobStatus.APPROVED


# --------------------------------------------------------------------------
# 5. Multi-Venture Distribution Scheduler (Parts 8, 9, 20)
# --------------------------------------------------------------------------

def test_scheduler_lifecycle_and_killswitch():
    accounts = create_seed_channel_accounts()
    registry = ChannelAccountRegistryManager(accounts)
    gov_gate = DistributionGovernanceGate(registry)
    gov_gate.register_campaign_venture("camp_holiday_2026", "vnt_holiday_commerce_pilot_2026")
    kill_switch = DistributionKillSwitchManager()

    scheduler = MultiVentureDistributionScheduler(
        governance_gate=gov_gate,
        account_registry=registry,
        kill_switch=kill_switch,
        default_timezone="America/Phoenix",
    )

    job = DistributionJob(
        distribution_job_id="job_sched_01",
        venture_id="vnt_holiday_commerce_pilot_2026",
        campaign_id="camp_holiday_2026",
        asset_ids=["asset_01"],
        channel_account_id="acc_holiday_instagram_01",
        platform="INSTAGRAM",
        content_type="VERTICAL_REEL",
        copy="The 6:12 AM Quiet Ritual. Studio design preview.",
        media={},
        target_url="https://nexus-campaigns.pages.dev/holiday-commerce-pilot/holiday-ceramic-mug/",
        status=DistributionJobStatus.READY_FOR_APPROVAL,
    )
    scheduler.register_job(job)

    # 1. Schedule operation
    ok_sched, msg_sched = scheduler.schedule_at("job_sched_01", "2026-11-12T08:00:00-07:00", "America/Phoenix")
    assert ok_sched is True
    assert job.status == DistributionJobStatus.SCHEDULED
    assert job.scheduled_time == "2026-11-12T08:00:00-07:00"
    assert job.timezone == "America/Phoenix"

    # 2. Reschedule operation
    ok_resched, msg_resched = scheduler.reschedule("job_sched_01", "2026-11-12T10:00:00-07:00")
    assert ok_resched is True
    assert job.scheduled_time == "2026-11-12T10:00:00-07:00"

    # 3. Kill Switch: Pause Campaign
    kill_switch.pause_campaign("camp_holiday_2026")
    ok_blocked, msg_blocked = scheduler.schedule_at("job_sched_01", "2026-11-12T12:00:00-07:00")
    assert ok_blocked is False
    assert "CAMPAIGN_PAUSED" in msg_blocked

    # Resume Campaign
    kill_switch.resume_campaign("camp_holiday_2026")

    # 4. Cancel operation
    ok_cancel, msg_cancel = scheduler.cancel("job_sched_01", reason="Creative refresh required")
    assert ok_cancel is True
    assert job.status == DistributionJobStatus.CANCELLED
    assert "Creative refresh required" in job.error


# --------------------------------------------------------------------------
# 6. Retry Policy & Failure Classifier (Part 19)
# --------------------------------------------------------------------------

def test_retry_policy():
    # Terminal failures must NOT be retried
    assert PublishRetryPolicy.is_retryable(PublishFailureType.AUTH_EXPIRED, attempt_count=0) is False
    assert PublishRetryPolicy.is_retryable(PublishFailureType.MEDIA_REJECTED, attempt_count=0) is False
    assert PublishRetryPolicy.is_retryable(PublishFailureType.COPY_REJECTED, attempt_count=0) is False
    assert PublishRetryPolicy.is_retryable(PublishFailureType.PERMISSION_DENIED, attempt_count=0) is False

    # Transient failures may be retried up to 3 attempts
    assert PublishRetryPolicy.is_retryable(PublishFailureType.RATE_LIMIT, attempt_count=0) is True
    assert PublishRetryPolicy.is_retryable(PublishFailureType.RATE_LIMIT, attempt_count=2) is True
    assert PublishRetryPolicy.is_retryable(PublishFailureType.RATE_LIMIT, attempt_count=3) is False
    assert PublishRetryPolicy.is_retryable(PublishFailureType.PLATFORM_OUTAGE, attempt_count=1) is True


# --------------------------------------------------------------------------
# 7. Multi-Venture Queue Isolation Test (Part 20)
# --------------------------------------------------------------------------

def test_multi_venture_queue_isolation_three_businesses():
    """Simulates internal scheduling for Holiday Commerce, KRD Ability, and GoClear with zero leakage."""
    accounts = create_seed_channel_accounts()
    registry = ChannelAccountRegistryManager(accounts)
    gov_gate = DistributionGovernanceGate(registry)

    # Register 3 distinct venture-campaign mappings
    gov_gate.register_campaign_venture("camp_holiday_01", "vnt_holiday_commerce_pilot_2026")
    gov_gate.register_campaign_venture("camp_krd_01", "vnt_krd_ability_2026")
    gov_gate.register_campaign_venture("camp_goclear_01", "vnt_goclear_credit_2026")

    # Register assets
    gov_gate.register_asset_scope(AssetScopeRecord("asset_holiday", "vnt_holiday_commerce_pilot_2026", "camp_holiday_01"))
    gov_gate.register_asset_scope(AssetScopeRecord("asset_krd", "vnt_krd_ability_2026", "camp_krd_01"))
    gov_gate.register_asset_scope(AssetScopeRecord("asset_goclear", "vnt_goclear_credit_2026", "camp_goclear_01"))

    scheduler = MultiVentureDistributionScheduler(gov_gate, registry)

    # Build 3 valid jobs, one per venture
    job_h = DistributionJob(
        distribution_job_id="job_h_01",
        venture_id="vnt_holiday_commerce_pilot_2026",
        campaign_id="camp_holiday_01",
        asset_ids=["asset_holiday"],
        channel_account_id="acc_holiday_instagram_01",
        platform="INSTAGRAM",
        content_type="FEED_IMAGE",
        copy="The 6:12 AM Quiet Ritual. Studio preview.",
        media={},
        target_url="https://nexus-campaigns.pages.dev/holiday-commerce-pilot/holiday-ceramic-mug/",
    )
    job_k = DistributionJob(
        distribution_job_id="job_k_01",
        venture_id="vnt_krd_ability_2026",
        campaign_id="camp_krd_01",
        asset_ids=["asset_krd"],
        channel_account_id="acc_krd_linkedin_01",
        platform="LINKEDIN",
        content_type="FEED_POST",
        copy="Enterprise Systems Architecture Overview.",
        media={},
        target_url="https://nexus-campaigns.pages.dev/krd-ability/enterprise-systems/",
    )
    job_g = DistributionJob(
        distribution_job_id="job_g_01",
        venture_id="vnt_goclear_credit_2026",
        campaign_id="camp_goclear_01",
        asset_ids=["asset_goclear"],
        channel_account_id="acc_goclear_facebook_01",
        platform="FACEBOOK",
        content_type="FEED_POST",
        copy="Educational Readiness Assessment Framework.",
        media={},
        target_url="https://nexus-campaigns.pages.dev/goclear-credit/readiness-framework/",
    )

    for j in (job_h, job_k, job_g):
        scheduler.register_job(j)

    # Verify query isolation
    h_jobs = scheduler.list_jobs(venture_id="vnt_holiday_commerce_pilot_2026")
    assert len(h_jobs) == 1
    assert h_jobs[0].distribution_job_id == "job_h_01"

    k_jobs = scheduler.list_jobs(venture_id="vnt_krd_ability_2026")
    assert len(k_jobs) == 1
    assert k_jobs[0].distribution_job_id == "job_k_01"

    g_jobs = scheduler.list_jobs(venture_id="vnt_goclear_credit_2026")
    assert len(g_jobs) == 1
    assert g_jobs[0].distribution_job_id == "job_g_01"

    # Cross-venture collision test: attempt to schedule KRD asset with Holiday account
    leak_job = DistributionJob(
        distribution_job_id="job_leak_test",
        venture_id="vnt_holiday_commerce_pilot_2026",
        campaign_id="camp_holiday_01",
        asset_ids=["asset_krd"],  # Belongs to KRD
        channel_account_id="acc_holiday_instagram_01",
        platform="INSTAGRAM",
        content_type="FEED_IMAGE",
        copy="Quiet morning ritual preview.",
        media={},
        target_url="https://nexus-campaigns.pages.dev/holiday-commerce-pilot/holiday-ceramic-mug/",
        status=DistributionJobStatus.APPROVED,
        approval_status="APPROVED_BY_RAY",
        approval_receipt_id="rcpt_leak_mock",
    )
    val_leak = scheduler.validation_pipeline.validate(leak_job)
    assert val_leak.passed is False
    assert any("ASSET_SCOPE_VIOLATIONS" in r for r in val_leak.blocked_reasons)


# --------------------------------------------------------------------------
# 8. Bounded Live-Publish Certification & Lineage (Parts 17, 18, 22, 23)
# --------------------------------------------------------------------------

def test_bounded_live_publish_and_lineage_persistence(tmp_path, monkeypatch):
    test_memory_file = tmp_path / "nexus_social_memory_test.json"
    monkeypatch.setattr(SocialPublishingMemory, "MEMORY_FILE", test_memory_file)

    accounts = create_seed_channel_accounts()
    acc_pub = ChannelAccount(
        channel_account_id="acc_cert_pub_01",
        platform="FACEBOOK",
        account_name="GoClear Official",
        account_type="PAGE",
        account_scope=AccountScopeType.SINGLE_VENTURE,
        venture_scope=["vnt_goclear_credit_2026"],
        auth_status="AUTHENTICATED",
        connection_status="CONNECTED",
        capabilities=["POST_TEXT", "POST_IMAGE"],
        publish_allowed=True,
        schedule_allowed=True,
    )
    accounts.append(acc_pub)
    registry = ChannelAccountRegistryManager(accounts)
    gov_gate = DistributionGovernanceGate(registry)
    gov_gate.register_campaign_venture("camp_cert_01", "vnt_goclear_credit_2026")
    gov_gate.register_asset_scope(AssetScopeRecord("asset_cert_01", "vnt_goclear_credit_2026", "camp_cert_01"))

    scheduler = MultiVentureDistributionScheduler(gov_gate, registry)

    job = DistributionJob(
        distribution_job_id="job_cert_live_01",
        venture_id="vnt_goclear_credit_2026",
        campaign_id="camp_cert_01",
        product_id="prod_readiness_score",
        asset_ids=["asset_cert_01"],
        channel_account_id="acc_cert_pub_01",
        platform="FACEBOOK",
        content_type="FEED_POST",
        copy="A structured review of credit readiness blockers. Educational score preview.",
        media={},
        target_url="https://nexus-campaigns.pages.dev/goclear-credit/readiness-framework/",
        status=DistributionJobStatus.APPROVED,
        approval_status="APPROVED_BY_RAY",
        approval_receipt_id="rcpt_appr_cert_9999",
    )
    scheduler.register_job(job)

    # Execute bounded publication
    ok, receipt, msg = scheduler.publish_now_after_approval("job_cert_live_01", simulated_external_id="fb_post_987654321")
    assert ok is True
    assert receipt is not None
    assert receipt.external_post_id == "fb_post_987654321"
    assert receipt.status == "PUBLISHED_CONFIRMED"
    assert receipt.cost == 0.0
    assert "Bearer" not in json.dumps(receipt.to_dict())

    # Record in persistent memory
    record = SocialPublishingMemory.record_publication(receipt, job)
    assert record["external_post_id"] == "fb_post_987654321"
    assert record["lineage"]["section_31c_engagement_hook"]["post_id"] == "fb_post_987654321"
    assert record["lineage"]["section_31d_performance_hook"]["platform"] == "FACEBOOK"

    # Query back from memory
    queried = SocialPublishingMemory.get_post_lineage("fb_post_987654321")
    assert queried is not None
    assert queried["distribution_job_id"] == "job_cert_live_01"


# --------------------------------------------------------------------------
# 9. Authentication Readiness Auditor (Parts 10-14)
# --------------------------------------------------------------------------

def test_platform_auth_auditor():
    audits = PlatformAuthAuditor.audit_all()
    # 6 accounts across 5 platforms (including both holiday and goclear Facebook venture accounts)
    assert len(audits) == 6

    account_map = {a.account_id: a for a in audits}
    assert "acc_holiday_instagram_01" in account_map
    assert "acc_holiday_facebook_01" in account_map
    assert "acc_goclear_facebook_01" in account_map
    assert "acc_holiday_tiktok_01" in account_map
    assert "acc_shared_nexus_youtube_01" in account_map
    assert "acc_krd_linkedin_01" in account_map

    platforms = {a.platform: a for a in audits}
    assert "INSTAGRAM" in platforms
    assert "FACEBOOK" in platforms
    assert "TIKTOK" in platforms
    assert "YOUTUBE" in platforms
    assert "LINKEDIN" in platforms

    # Verify key platform states
    assert platforms["INSTAGRAM"].auth_status == "REQUIRES_RAY_LOGIN"
    assert platforms["INSTAGRAM"].blocker == "META_SOCIAL_APP_CREDENTIALS_MISSING"

    assert platforms["FACEBOOK"].auth_status == "UNCONFIGURED"
    assert platforms["FACEBOOK"].blocker == "META_PAGE_ACCESS_TOKEN_MISSING"

    assert platforms["TIKTOK"].auth_status == "UNCONFIGURED"
    assert "BLOCKED_OFFICIAL_INTEGRATION_REQUIRED" in platforms["TIKTOK"].blocker

    assert platforms["YOUTUBE"].auth_status == "AUTHENTICATED_READONLY"
    assert "READONLY" in platforms["YOUTUBE"].blocker

    assert platforms["LINKEDIN"].auth_status == "UNCONFIGURED"


# --------------------------------------------------------------------------
# 10. Holiday Campaign Distribution Package Integration Test (Part 15)
# --------------------------------------------------------------------------

def test_holiday_campaign_distribution_package_build():
    jobs, pkg, sched = build_holiday_campaign_distribution_package()
    assert len(jobs) == 4
    assert pkg.total_posts == 4
    assert pkg.landing_target_url == "https://nexus-campaigns.pages.dev/holiday-commerce-pilot/holiday-ceramic-mug/"

    platforms = [j.platform for j in jobs]
    assert "INSTAGRAM" in platforms
    assert "FACEBOOK" in platforms
    assert "TIKTOK" in platforms
    assert "YOUTUBE" in platforms

    for j in jobs:
        assert j.venture_id == "vnt_holiday_commerce_pilot_2026"
        assert j.campaign_id == "camp_holiday_ceramic_mug_2026"
        assert j.target_url == "https://nexus-campaigns.pages.dev/holiday-commerce-pilot/holiday-ceramic-mug/"
        assert j.scheduled_time is not None
        assert j.timezone == "America/Phoenix"
        assert j.status == DistributionJobStatus.READY_FOR_APPROVAL
        assert j.approval_status == "WAITING_FOR_RAY_APPROVAL"


# --------------------------------------------------------------------------
# 11. Truth Remediation Regression Tests (Defects 1 & 2)
# --------------------------------------------------------------------------

def test_facebook_cannot_display_authenticated_when_auditor_reports_unconfigured():
    """Defect 1 Regression: Authority Rule enforces LIVE_AUTH_STATE_WINS."""
    accounts = create_seed_channel_accounts()
    # Artificially set an account's static auth_status to AUTHENTICATED
    acc_fb = ChannelAccount(
        channel_account_id="acc_holiday_facebook_01",
        platform="FACEBOOK",
        account_name="@the612amritual",
        account_type="PAGE",
        account_scope=AccountScopeType.SINGLE_VENTURE,
        venture_scope=["vnt_holiday_commerce_pilot_2026"],
        auth_status="AUTHENTICATED",  # Stale / incorrect static flag
        connection_status="CONNECTED",
        capabilities=["POST_TEXT", "POST_IMAGE"],
        publish_allowed=True,
    )
    registry = ChannelAccountRegistryManager([acc_fb])

    job_fb = DistributionJob(
        distribution_job_id="job_fb_test_auth",
        venture_id="vnt_holiday_commerce_pilot_2026",
        campaign_id="camp_holiday_ceramic_mug_2026",
        product_id="prod_stoneware_mug_14oz",
        asset_ids=["asset_metaai_image_1794355016"],
        channel_account_id="acc_holiday_facebook_01",
        platform="FACEBOOK",
        content_type="FEED_POST",
        copy="Quiet ritual studio preview.",
        media={},
        target_url="https://nexus-campaigns.pages.dev/holiday-commerce-pilot/holiday-ceramic-mug/",
    )

    pkg = ApprovalPackageManager.create_package(
        venture_id="vnt_holiday_commerce_pilot_2026",
        campaign_id="camp_holiday_ceramic_mug_2026",
        landing_target_url="https://nexus-campaigns.pages.dev/holiday-commerce-pilot/holiday-ceramic-mug/",
        deployment_id="dep_test_123",
        jobs=[job_fb],
        account_registry=registry,
    )

    card = pkg.posts[0]
    # LIVE_AUTH_STATE_WINS must override the stale static account status
    assert card.auth_status == "UNCONFIGURED"
    assert card.auth_status != "AUTHENTICATED"


def test_local_storefront_connector_cannot_satisfy_facebook_authentication():
    """Defect 1 Regression: Storefront account cannot be bound to Facebook social jobs."""
    accounts = create_seed_channel_accounts()
    registry = ChannelAccountRegistryManager(accounts)
    gov_gate = DistributionGovernanceGate(registry)
    gov_gate.register_campaign_venture("camp_holiday_ceramic_mug_2026", "vnt_holiday_commerce_pilot_2026")
    pipeline = PrePublishValidationPipeline(gov_gate, registry)

    # Job erroneously targets acc_holiday_storefront_01 (STOREFRONT) with platform FACEBOOK
    bad_fb_job = DistributionJob(
        distribution_job_id="job_bad_fb_storefront",
        venture_id="vnt_holiday_commerce_pilot_2026",
        campaign_id="camp_holiday_ceramic_mug_2026",
        product_id="prod_stoneware_mug_14oz",
        asset_ids=["asset_metaai_image_1794355016"],
        channel_account_id="acc_holiday_storefront_01",
        platform="FACEBOOK",
        content_type="FEED_POST",
        copy="The 6:12 AM Quiet Ritual. Studio design preview.",
        media={},
        target_url="https://nexus-campaigns.pages.dev/holiday-commerce-pilot/holiday-ceramic-mug/",
        status=DistributionJobStatus.APPROVED,
        approval_status="APPROVED_BY_RAY",
        approval_receipt_id="rcpt_appr_mock",
    )

    val = pipeline.validate(bad_fb_job)
    assert val.passed is False
    assert any("PLATFORM_MISMATCH" in r and "storefront" in r.lower() for r in val.blocked_reasons)

    # In approval card creation, storefront mismatch must be explicitly blocked
    pkg = ApprovalPackageManager.create_package(
        venture_id="vnt_holiday_commerce_pilot_2026",
        campaign_id="camp_holiday_ceramic_mug_2026",
        landing_target_url="https://nexus-campaigns.pages.dev/holiday-commerce-pilot/holiday-ceramic-mug/",
        deployment_id="dep_test_123",
        jobs=[bad_fb_job],
        account_registry=registry,
    )
    assert "MISMATCH_BLOCKED" in pkg.posts[0].auth_status


def test_meta_horizontal_video_cannot_be_labeled_916():
    """Defect 2 Regression: Meta video is 1152x768 horizontal (3:2) and cannot be labeled 9:16 or used vertically."""
    from scripts.distribution.social_publishing_engine import CERTIFIED_ASSET_REGISTRY

    meta_vid = CERTIFIED_ASSET_REGISTRY["asset_metaai_video_1794355722"]
    assert meta_vid.width == 1152
    assert meta_vid.height == 768
    assert meta_vid.aspect_ratio == "3:2"
    assert meta_vid.orientation == "HORIZONTAL_LANDSCAPE"
    assert meta_vid.duration_seconds == 10.0

    # Pipeline validation: attempting to attach horizontal Meta video to an Instagram Reel must fail
    accounts = create_seed_channel_accounts()
    registry = ChannelAccountRegistryManager(accounts)
    gov_gate = DistributionGovernanceGate(registry)
    gov_gate.register_campaign_venture("camp_holiday_2026", "vnt_holiday_commerce_pilot_2026")
    gov_gate.register_asset_scope(AssetScopeRecord("asset_metaai_video_1794355722", "vnt_holiday_commerce_pilot_2026", "camp_holiday_2026"))

    pipeline = PrePublishValidationPipeline(gov_gate, registry)

    bad_reel_job = DistributionJob(
        distribution_job_id="job_bad_reel_horiz",
        venture_id="vnt_holiday_commerce_pilot_2026",
        campaign_id="camp_holiday_2026",
        asset_ids=["asset_metaai_video_1794355722"],  # Horizontal video attached to vertical reel
        channel_account_id="acc_holiday_instagram_01",
        platform="INSTAGRAM",
        content_type="VERTICAL_REEL",
        copy="The 6:12 AM Quiet Ritual. Studio design preview.",
        media={"video_asset": "asset_metaai_video_1794355722"},
        target_url="https://nexus-campaigns.pages.dev/holiday-commerce-pilot/holiday-ceramic-mug/",
        status=DistributionJobStatus.APPROVED,
        approval_status="APPROVED_BY_RAY",
        approval_receipt_id="rcpt_appr_mock",
    )

    val = pipeline.validate(bad_reel_job)
    assert val.passed is False
    assert any("ORIENTATION_MISMATCH" in r and "HORIZONTAL_LANDSCAPE" in r for r in val.blocked_reasons)


def test_modal_certified_vertical_video_resolves_for_vertical_jobs():
    """Defect 2 Regression: Modal video is 480x864 vertical (9:16, 5.04s) and passes vertical placement checks."""
    from scripts.distribution.social_publishing_engine import CERTIFIED_ASSET_REGISTRY

    modal_vid = CERTIFIED_ASSET_REGISTRY["asset_modal_video_1794413265"]
    assert modal_vid.width == 480
    assert modal_vid.height == 864
    assert modal_vid.aspect_ratio == "9:16"
    assert modal_vid.orientation == "VERTICAL"
    assert modal_vid.duration_seconds == 5.04

    # Pipeline validation: attaching native vertical Modal video to Instagram Reel passes orientation check
    accounts = create_seed_channel_accounts()
    acc_auth_ig = ChannelAccount(
        channel_account_id="acc_holiday_ig_test",
        platform="INSTAGRAM",
        account_name="@the612amritual",
        account_type="CREATOR",
        account_scope=AccountScopeType.SINGLE_VENTURE,
        venture_scope=["vnt_holiday_commerce_pilot_2026"],
        auth_status="AUTHENTICATED",
        connection_status="CONNECTED",
        capabilities=["POST_VIDEO", "REEL"],
        publish_allowed=True,
    )
    registry = ChannelAccountRegistryManager([acc_auth_ig])
    gov_gate = DistributionGovernanceGate(registry)
    gov_gate.register_campaign_venture("camp_holiday_2026", "vnt_holiday_commerce_pilot_2026")
    gov_gate.register_asset_scope(AssetScopeRecord("asset_modal_video_1794413265", "vnt_holiday_commerce_pilot_2026", "camp_holiday_2026"))

    pipeline = PrePublishValidationPipeline(gov_gate, registry)

    good_reel_job = DistributionJob(
        distribution_job_id="job_good_reel_modal",
        venture_id="vnt_holiday_commerce_pilot_2026",
        campaign_id="camp_holiday_2026",
        asset_ids=["asset_modal_video_1794413265"],
        channel_account_id="acc_holiday_ig_test",
        platform="INSTAGRAM",
        content_type="VERTICAL_REEL",
        copy="The 6:12 AM Quiet Ritual. Studio design preview.",
        media={"video_asset": "asset_modal_video_1794413265"},
        target_url="https://nexus-campaigns.pages.dev/holiday-commerce-pilot/holiday-ceramic-mug/",
        status=DistributionJobStatus.APPROVED,
        approval_status="APPROVED_BY_RAY",
        approval_receipt_id="rcpt_appr_mock",
    )

    val = pipeline.validate(good_reel_job)
    assert val.passed is True


def test_campaign_package_regeneration_inherits_live_auth_state():
    """Verify regenerated Holiday campaign package reflects truthful live auth states."""
    jobs, pkg, sched = build_holiday_campaign_distribution_package()

    card_map = {p.channel: p for p in pkg.posts}

    # Instagram
    assert card_map["INSTAGRAM"].auth_status == "REQUIRES_RAY_LOGIN"
    assert card_map["INSTAGRAM"].channel_account_id == "acc_holiday_instagram_01"
    assert "Modal certified vertical video" in card_map["INSTAGRAM"].media_summary

    # Facebook
    assert card_map["FACEBOOK"].auth_status == "UNCONFIGURED"
    assert card_map["FACEBOOK"].channel_account_id == "acc_holiday_facebook_01"
    assert "the612amritual.cc" not in card_map["FACEBOOK"].account_handle
    assert "Meta.ai WebP hero" in card_map["FACEBOOK"].media_summary

    # TikTok
    assert card_map["TIKTOK"].auth_status == "UNCONFIGURED"
    assert card_map["TIKTOK"].channel_account_id == "acc_holiday_tiktok_01"

    # YouTube Shorts
    assert card_map["YOUTUBE"].auth_status == "AUTHENTICATED_READONLY"
    assert card_map["YOUTUBE"].channel_account_id == "acc_shared_nexus_youtube_01"


def test_no_external_content_published_or_scheduled():
    """Verify that zero external content has been published or scheduled."""
    jobs, pkg, sched = build_holiday_campaign_distribution_package()

    for j in jobs:
        assert j.status == DistributionJobStatus.READY_FOR_APPROVAL
        assert j.publish_status == "UNPUBLISHED"
        assert j.published_at is None
        assert j.external_post_id is None

    assert pkg.status == "PENDING_RAY_REVIEW"

    manifest_path = Path("dist/creative/campaign_holiday_ceramic_mug_manifest.json")
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        social_dist = manifest.get("social_distribution", {})
        assert social_dist.get("published_externally") is False
        assert social_dist.get("scheduled_externally") is False
        assert social_dist.get("ad_spend_usd") == 0.0
