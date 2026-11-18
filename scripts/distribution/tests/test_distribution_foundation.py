"""Test Suite for Nexus Multi-Venture Distribution Foundation (Section 31A)."""
from __future__ import annotations

import pytest
from scripts.distribution.distribution_foundation import (
    AccountScopeType,
    AssetScopeRecord,
    AssetScopeType,
    ChannelAccount,
    ChannelAccountRegistryManager,
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
)


def test_lineage_validation():
    valid_lineage = DistributionLineage(
        venture_id="vnt_holiday_commerce_pilot_2026",
        campaign_id="camp_holiday_ceramic_mug_2026",
        asset_id="asset_metaai_1794355016",
        channel_account_id="acc_holiday_instagram_01",
        channel="INSTAGRAM",
        distribution_job_id="job_holiday_001",
        product_id="prod_stoneware_mug_14oz",
    )
    ok, missing = valid_lineage.validate_complete()
    assert ok is True
    assert len(missing) == 0

    invalid_lineage = DistributionLineage(
        venture_id="",
        campaign_id="camp_holiday_ceramic_mug_2026",
        asset_id="",
        channel_account_id="acc_holiday_instagram_01",
        channel="INSTAGRAM",
        distribution_job_id="job_holiday_001",
    )
    ok_inv, missing_inv = invalid_lineage.validate_complete()
    assert ok_inv is False
    assert "venture_id" in missing_inv
    assert "asset_id" in missing_inv


def test_multi_venture_isolation_three_namespaces():
    """Validates strict isolation across HOLIDAY_COMMERCE, KRD_ABILITY, and GOCLEAR."""
    accounts = create_seed_channel_accounts()
    registry = ChannelAccountRegistryManager(accounts)
    gate = DistributionGovernanceGate(registry)

    # Register Campaigns to Ventures
    gate.register_campaign_venture("camp_holiday_ceramic_mug_2026", "vnt_holiday_commerce_pilot_2026")
    gate.register_campaign_venture("camp_krd_leadership_2026", "vnt_krd_ability_2026")
    gate.register_campaign_venture("camp_goclear_readiness_2026", "vnt_goclear_credit_2026")

    # Register Asset Scopes
    gate.register_asset_scope(AssetScopeRecord(
        asset_id="asset_holiday_mug_img",
        venture_id="vnt_holiday_commerce_pilot_2026",
        campaign_id="camp_holiday_ceramic_mug_2026",
        scope_type=AssetScopeType.CAMPAIGN,
    ))
    gate.register_asset_scope(AssetScopeRecord(
        asset_id="asset_krd_logo",
        venture_id="vnt_krd_ability_2026",
        campaign_id=None,
        scope_type=AssetScopeType.VENTURE,
    ))

    # TEST A: Holiday campaign attempting to route to KRD LinkedIn account -> BLOCK
    bad_job_a = DistributionJob(
        distribution_job_id="job_leak_01",
        venture_id="vnt_holiday_commerce_pilot_2026",
        campaign_id="camp_holiday_ceramic_mug_2026",
        asset_ids=["asset_holiday_mug_img"],
        channel_account_id="acc_krd_linkedin_01",  # Belongs to KRD
        platform="LINKEDIN",
        content_type="IMAGE_POST",
        copy="A substantial ceramic vessel for quiet mornings.",
        media={},
    )
    passed_a, reasons_a = gate.validate_distribution_job(bad_job_a, skip_truth_check=True)
    assert passed_a is False
    assert any("VENTURE_ACCOUNT_SCOPE_MISMATCH" in r for r in reasons_a)

    # TEST B: KRD campaign attempting to route to GoClear Facebook account -> BLOCK
    bad_job_b = DistributionJob(
        distribution_job_id="job_leak_02",
        venture_id="vnt_krd_ability_2026",
        campaign_id="camp_krd_leadership_2026",
        asset_ids=["asset_krd_logo"],
        channel_account_id="acc_goclear_facebook_01",  # Belongs to GoClear
        platform="FACEBOOK",
        content_type="IMAGE_POST",
        copy="Leadership insights for the modern enterprise.",
        media={},
    )
    passed_b, reasons_b = gate.validate_distribution_job(bad_job_b, skip_truth_check=True)
    assert passed_b is False
    assert any("VENTURE_ACCOUNT_SCOPE_MISMATCH" in r for r in reasons_b)

    # TEST C: GoClear campaign attempting to use Holiday ceramic mug asset -> BLOCK
    bad_job_c = DistributionJob(
        distribution_job_id="job_leak_03",
        venture_id="vnt_goclear_credit_2026",
        campaign_id="camp_goclear_readiness_2026",
        asset_ids=["asset_holiday_mug_img"],  # Belongs to Holiday Commerce!
        channel_account_id="acc_goclear_facebook_01",
        platform="FACEBOOK",
        content_type="IMAGE_POST",
        copy="Prepare your business credit before applying.",
        media={},
    )
    passed_c, reasons_c = gate.validate_distribution_job(bad_job_c, skip_truth_check=True)
    assert passed_c is False
    assert any("ASSET_VENTURE_MISMATCH" in r for r in reasons_c)

    # TEST D: Shared Master YouTube account allows authorized ventures -> PASS
    shared_job = DistributionJob(
        distribution_job_id="job_shared_01",
        venture_id="vnt_holiday_commerce_pilot_2026",
        campaign_id="camp_holiday_ceramic_mug_2026",
        asset_ids=["asset_holiday_mug_img"],
        channel_account_id="acc_shared_nexus_youtube_01",  # Shared account
        platform="YOUTUBE",
        content_type="SHORT_FORM_VIDEO",
        copy="The 6:12 AM Quiet Ritual morning overview.",
        media={"duration_seconds": 15},
    )
    passed_d, reasons_d = gate.validate_distribution_job(shared_job, skip_truth_check=True)
    assert passed_d is True
    assert len(reasons_d) == 0


def test_asset_scope_types():
    # Campaign Scoped
    c_asset = AssetScopeRecord("a1", "v1", "c1", AssetScopeType.CAMPAIGN)
    assert c_asset.is_usable_by("v1", "c1")[0] is True
    assert c_asset.is_usable_by("v1", "c2")[0] is False  # Same venture, different campaign

    # Venture Scoped
    v_asset = AssetScopeRecord("a2", "v1", None, AssetScopeType.VENTURE)
    assert v_asset.is_usable_by("v1", "c1")[0] is True
    assert v_asset.is_usable_by("v1", "c2")[0] is True
    assert v_asset.is_usable_by("v2", "c3")[0] is False  # Cross venture blocked

    # Global Brand Scoped
    g_asset = AssetScopeRecord("a3", "nexus_corp", None, AssetScopeType.GLOBAL_BRAND)
    assert g_asset.is_usable_by("v1", "c1")[0] is True
    assert g_asset.is_usable_by("v2", "c2")[0] is True


def test_truth_gate_blocks_unverified_copy():
    accounts = create_seed_channel_accounts()
    registry = ChannelAccountRegistryManager(accounts)
    gate = DistributionGovernanceGate(registry)
    gate.register_campaign_venture("camp_holiday_ceramic_mug_2026", "vnt_holiday_commerce_pilot_2026")

    # Job containing unverified quantitative claims
    bad_truth_job = DistributionJob(
        distribution_job_id="job_bad_truth_01",
        venture_id="vnt_holiday_commerce_pilot_2026",
        campaign_id="camp_holiday_ceramic_mug_2026",
        asset_ids=[],
        channel_account_id="acc_holiday_storefront_01",
        platform="STOREFRONT",
        content_type="IMAGE_POST",
        copy="This 485 grams mug holds 14 oz and keeps coffee hot twice as long in Batch #04!",
        media={},
    )
    passed, reasons = gate.validate_distribution_job(bad_truth_job, skip_truth_check=False)
    assert passed is False
    assert any("PRODUCT_TRUTH_VIOLATION" in r for r in reasons)

    # Job with clean honest copy
    clean_job = DistributionJob(
        distribution_job_id="job_clean_01",
        venture_id="vnt_holiday_commerce_pilot_2026",
        campaign_id="camp_holiday_ceramic_mug_2026",
        asset_ids=[],
        channel_account_id="acc_holiday_storefront_01",
        platform="STOREFRONT",
        content_type="IMAGE_POST",
        copy="The 6:12 AM Quiet Ritual. The only fifteen minutes that belong entirely to you. A substantial ceramic vessel made for slow winter mornings.",
        media={},
    )
    passed_clean, reasons_clean = gate.validate_distribution_job(clean_job, skip_truth_check=False)
    assert passed_clean is True


def test_approval_governance_gate():
    accounts = create_seed_channel_accounts()
    registry = ChannelAccountRegistryManager(accounts)
    gate = DistributionGovernanceGate(registry)
    gate.register_campaign_venture("camp_holiday_ceramic_mug_2026", "vnt_holiday_commerce_pilot_2026")

    job = DistributionJob(
        distribution_job_id="job_appr_01",
        venture_id="vnt_holiday_commerce_pilot_2026",
        campaign_id="camp_holiday_ceramic_mug_2026",
        asset_ids=[],
        channel_account_id="acc_holiday_storefront_01",
        platform="STOREFRONT",
        content_type="IMAGE_POST",
        copy="The 6:12 AM Quiet Ritual. Substantial ceramic vessel for quiet mornings.",
        media={},
    )
    # Attempt approval without receipt -> FAILS
    ok, err = gate.approve_job(job, "")
    assert ok is False
    assert "APPROVAL_REQUIRED" in err
    assert job.status == DistributionJobStatus.DRAFT

    # With valid Ray receipt -> SUCCEEDS
    ok_approved, msg = gate.approve_job(job, "ray_approval_receipt_20261111_verified")
    assert ok_approved is True
    assert job.status == DistributionJobStatus.APPROVED
    assert job.approval_status == "APPROVED_BY_RAY"


def test_platform_media_limits():
    accounts = create_seed_channel_accounts()
    registry = ChannelAccountRegistryManager(accounts)
    gate = DistributionGovernanceGate(registry)
    gate.register_campaign_venture("camp_holiday_ceramic_mug_2026", "vnt_holiday_commerce_pilot_2026")

    # TikTok limit is 600s
    over_limit_job = DistributionJob(
        distribution_job_id="job_over_limit_01",
        venture_id="vnt_holiday_commerce_pilot_2026",
        campaign_id="camp_holiday_ceramic_mug_2026",
        asset_ids=[],
        channel_account_id="acc_holiday_tiktok_01",
        platform="TIKTOK",
        content_type="SHORT_FORM_VIDEO",
        copy="Quiet morning ritual video.",
        media={"duration_seconds": 950},  # Exceeds 600s
    )
    passed, reasons = gate.validate_distribution_job(over_limit_job, skip_truth_check=True)
    assert passed is False
    assert any("PLATFORM_MEDIA_LIMIT_EXCEEDED" in r for r in reasons)


def test_publish_receipt_contract():
    receipt = PublishReceipt(
        publish_receipt_id="rec_pub_001",
        distribution_job_id="job_holiday_001",
        venture_id="vnt_holiday_commerce_pilot_2026",
        campaign_id="camp_holiday_ceramic_mug_2026",
        channel_account_id="acc_holiday_storefront_01",
        platform="STOREFRONT",
        external_post_id="post_store_12345",
        published_at="2026-11-11T17:00:00Z",
        media_asset_ids=["asset_metaai_1794355016"],
        copy_hash=sha256_hash("The 6:12 AM Quiet Ritual"),
        target_url="https://the612amritual.cc",
        status="SIMULATED_TEST_ONLY",
        provider_response_reference="local_staging_deploy_receipt",
    )
    d = receipt.to_dict()
    assert d["publish_receipt_id"] == "rec_pub_001"
    assert d["status"] == "SIMULATED_TEST_ONLY"
    assert len(d["copy_hash"]) == 64


def test_future_engagement_and_performance_hooks():
    eng = EngagementEventHook(
        engagement_event_id="eng_001",
        venture_id="vnt_holiday_commerce_pilot_2026",
        campaign_id="camp_holiday_ceramic_mug_2026",
        post_id="post_12345",
        channel_account_id="acc_holiday_instagram_01",
        external_event_id="ig_comment_9876",
        engagement_type="COMMENT",
        author_id="user_quiet_coffee",
        content="Is this dishwasher safe?",
    )
    assert eng.engagement_type == "COMMENT"
    assert eng.to_dict()["venture_id"] == "vnt_holiday_commerce_pilot_2026"

    perf = PerformanceMetricHook(
        metric_id="perf_001",
        venture_id="vnt_holiday_commerce_pilot_2026",
        campaign_id="camp_holiday_ceramic_mug_2026",
        post_id="post_12345",
        platform="INSTAGRAM",
        metric_name="REACH",
        metric_value=4250.0,
    )
    assert perf.metric_name == "REACH"
    assert perf.metric_value == 4250.0


def test_scale_target_simulation():
    """Validates architectural readiness for >= 10 ventures, 100 campaigns, 1,000 distribution jobs."""
    accounts = []
    # 10 Ventures
    for v_idx in range(1, 11):
        v_id = f"vnt_scale_test_{v_idx:02d}"
        accounts.append(ChannelAccount(
            channel_account_id=f"acc_scale_{v_idx:02d}",
            platform="INSTAGRAM",
            account_name=f"@venture_{v_idx:02d}",
            account_type="BUSINESS",
            account_scope=AccountScopeType.SINGLE_VENTURE,
            venture_scope=[v_id],
            auth_status="AUTHENTICATED",
            connection_status="CONNECTED",
            capabilities=["POST_IMAGE", "POST_VIDEO"],
        ))

    manager = ChannelAccountRegistryManager(accounts)
    gate = DistributionGovernanceGate(manager)

    # 100 Campaigns (10 per venture)
    campaign_ids = []
    for v_idx in range(1, 11):
        v_id = f"vnt_scale_test_{v_idx:02d}"
        for c_idx in range(1, 11):
            c_id = f"camp_scale_v{v_idx:02d}_c{c_idx:02d}"
            campaign_ids.append((c_id, v_id, f"acc_scale_{v_idx:02d}"))
            gate.register_campaign_venture(c_id, v_id)

    assert len(campaign_ids) == 100

    # 1,000 Distribution Jobs (10 per campaign)
    jobs = []
    for job_idx in range(1, 1001):
        c_id, v_id, acc_id = campaign_ids[(job_idx - 1) % 100]
        jobs.append(DistributionJob(
            distribution_job_id=f"job_scale_{job_idx:04d}",
            venture_id=v_id,
            campaign_id=c_id,
            asset_ids=[],
            channel_account_id=acc_id,
            platform="INSTAGRAM",
            content_type="IMAGE_POST",
            copy="Scale target simulation copy.",
            media={},
            priority=5,
        ))

    assert len(jobs) == 1000

    # Validate first and last job
    ok_first, _ = gate.validate_distribution_job(jobs[0], skip_truth_check=True)
    ok_last, _ = gate.validate_distribution_job(jobs[-1], skip_truth_check=True)
    assert ok_first is True
    assert ok_last is True
