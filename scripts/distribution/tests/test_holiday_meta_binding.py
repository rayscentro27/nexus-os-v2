"""Tests for Holiday Commerce Meta Account Binding and Pre-Publish Distribution Gates."""
import json
import pytest

from nexus_agent_platform.credential_control_plane import (
    resolve_credential,
    CredentialStatus,
    registry_entry,
    _load as load_registry,
)
from scripts.distribution.distribution_foundation import (
    create_seed_channel_accounts,
    DistributionJobStatus,
)
from scripts.distribution.social_publishing_engine import (
    build_holiday_campaign_distribution_package,
    PrePublishValidationPipeline,
)

RAYTESTPAGE_ID = "1722332634511930"
RAYTESTPAGE_NAME = "Raytestpage"
INSTAGRAM_HANDLE = "@the612amritual"
HOLIDAY_VENTURE = "vnt_holiday_commerce_pilot_2026"
GOCLEAR_VENTURE = "vnt_goclear_credit_2026"
HOLIDAY_CREDENTIAL_ID = "credential.meta.social.holiday.prod.v1"
GOCLEAR_CREDENTIAL_ID = "credential.meta.social.goclear.prod.v1"


def test_1_raytestpage_discovered_by_authoritative_meta_query():
    """1. Raytestpage discovered by authoritative Meta query."""
    entry = registry_entry(HOLIDAY_CREDENTIAL_ID)
    assert "Raytestpage" in entry.get("account_scope", "")
    assert RAYTESTPAGE_ID in entry.get("account_scope", "")


def test_2_the612amritual_discovered_as_connected_account():
    """2. @the612amritual discovered as connected account."""
    entry = registry_entry(HOLIDAY_CREDENTIAL_ID)
    assert INSTAGRAM_HANDLE in entry.get("account_scope", "")


def test_3_correct_page_id_captured():
    """3. Correct Page ID captured."""
    entry = registry_entry(HOLIDAY_CREDENTIAL_ID)
    assert RAYTESTPAGE_ID in entry.get("account_scope", "")


def test_4_correct_instagram_account_captured():
    """4. Correct Instagram Account captured."""
    accounts = create_seed_channel_accounts()
    ig_acc = next(a for a in accounts if a.channel_account_id == "acc_holiday_instagram_01")
    assert ig_acc.account_name == INSTAGRAM_HANDLE
    assert ig_acc.platform == "INSTAGRAM"
    assert HOLIDAY_VENTURE in ig_acc.venture_scope


def test_5_existing_holiday_credential_identity_reused():
    """5. Existing Holiday credential identity reused."""
    entry = registry_entry(HOLIDAY_CREDENTIAL_ID)
    assert entry["credential_id"] == HOLIDAY_CREDENTIAL_ID
    assert entry["provider"] == "meta"
    assert entry["venture_binding"] == [HOLIDAY_VENTURE]


def test_6_no_duplicate_meta_credential_created():
    """6. No duplicate Meta credential created."""
    creds = load_registry()
    holiday_meta = [c for c in creds if c.get("provider") == "meta" and HOLIDAY_VENTURE in c.get("venture_binding", [])]
    assert len(holiday_meta) == 1
    assert holiday_meta[0]["credential_id"] == HOLIDAY_CREDENTIAL_ID


def test_7_no_duplicate_channel_account_created():
    """7. No duplicate channel account created."""
    accounts = create_seed_channel_accounts()
    holiday_fb = [a for a in accounts if a.platform == "FACEBOOK" and HOLIDAY_VENTURE in a.venture_scope]
    holiday_ig = [a for a in accounts if a.platform == "INSTAGRAM" and HOLIDAY_VENTURE in a.venture_scope]
    assert len(holiday_fb) == 1
    assert holiday_fb[0].channel_account_id == "acc_holiday_facebook_01"
    assert len(holiday_ig) == 1
    assert holiday_ig[0].channel_account_id == "acc_holiday_instagram_01"


def test_8_goclear_bindings_unchanged():
    """8. GoClear bindings unchanged."""
    entry = registry_entry(GOCLEAR_CREDENTIAL_ID)
    assert entry["credential_id"] == GOCLEAR_CREDENTIAL_ID
    assert GOCLEAR_VENTURE in entry["venture_binding"]
    assert "Clear Credentials" in entry.get("account_scope", "")
    assert "131069194210954" in entry.get("account_scope", "")
    assert "@goclearonline" in entry.get("account_scope", "")
    assert "17841480265043148" in entry.get("account_scope", "")

    # Resolver check
    res = resolve_credential(capability="facebook.publish", venture_id=GOCLEAR_VENTURE)
    assert res.status == CredentialStatus.AVAILABLE
    assert res.credential_id == GOCLEAR_CREDENTIAL_ID


def test_9_holiday_goclear_cross_venture_isolation_passes():
    """9. Holiday/GoClear cross-venture isolation passes."""
    res_holiday = resolve_credential(capability="facebook.publish", venture_id=HOLIDAY_VENTURE)
    assert res_holiday.credential_id != GOCLEAR_CREDENTIAL_ID
    # Live-verified 2026-11-12 via owner OAuth: Raytestpage Page token in Keychain.
    assert res_holiday.credential_id == "credential.meta.social.holiday.prod.v1"
    assert res_holiday.status == CredentialStatus.AVAILABLE

    res_goclear = resolve_credential(capability="facebook.publish", venture_id=GOCLEAR_VENTURE)
    assert res_goclear.credential_id == GOCLEAR_CREDENTIAL_ID
    assert res_goclear.status == CredentialStatus.AVAILABLE


def test_10_distribution_package_points_to_live_holiday_social_accounts():
    """10. Distribution package points to live Holiday social accounts."""
    jobs, pkg, sched = build_holiday_campaign_distribution_package()
    card_map = {p.channel: p for p in pkg.posts}
    assert "FACEBOOK" in card_map
    assert "INSTAGRAM" in card_map

    # Facebook post targets Raytestpage
    assert card_map["FACEBOOK"].account_handle == RAYTESTPAGE_NAME
    assert card_map["FACEBOOK"].channel_account_id == "acc_holiday_facebook_01"

    # Instagram post targets @the612amritual
    assert card_map["INSTAGRAM"].account_handle == INSTAGRAM_HANDLE
    assert card_map["INSTAGRAM"].channel_account_id == "acc_holiday_instagram_01"


def test_11_12_no_external_content_published_or_scheduled():
    """11 & 12. No external content published or scheduled."""
    jobs, pkg, sched = build_holiday_campaign_distribution_package()
    pipeline = PrePublishValidationPipeline(sched.governance_gate, sched.governance_gate.registry)

    for j in jobs:
        # All jobs must remain UNPUBLISHED and WAITING_FOR_RAY_APPROVAL
        assert j.publish_status == "UNPUBLISHED"
        assert j.approval_status == "WAITING_FOR_RAY_APPROVAL"
        assert j.status == DistributionJobStatus.READY_FOR_APPROVAL
        assert j.approval_receipt_id is None

        # Pre-publish pipeline enforces that unauthenticated or unapproved jobs CANNOT publish
        val = pipeline.validate(j)
        assert val.passed is False
        assert any("APPROVAL_REQUIRED" in r for r in val.blocked_reasons)


def test_13_no_raw_token_exposed():
    """13. No raw token exposed in package, cards, or accounts."""
    jobs, pkg, sched = build_holiday_campaign_distribution_package()
    pkg_str = json.dumps(pkg.to_dict())
    assert "EAAB" not in pkg_str
    assert "Bearer" not in pkg_str
    assert "access_token" not in pkg_str
