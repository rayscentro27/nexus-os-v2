"""Tests for Nexus Campaign Test Deployment Router & Free Hosting Layer (Section 31B.0)."""

import json
import tempfile
from pathlib import Path

import pytest

from scripts.distribution.campaign_deploy_router import (
    CampaignDeployRouter,
    CampaignHostGenerator,
    DeploymentIdentity,
    DeploymentReceipt,
    HostingMode,
    HostProvider,
    PublicAssetSafetyGate,
    update_campaign_manifest_with_deployment,
)


def test_provider_audit_and_netlify_failure_detection():
    router = CampaignDeployRouter()
    audit = router.audit_providers()

    assert audit["primary_test_host"] == "CLOUDFLARE_PAGES"
    assert audit["secondary_test_host"] == "NETLIFY_GIT_DEPLOY"
    assert audit["manual_emergency_host"] == "NETLIFY_DROP"
    assert audit["existing_netlify_cli"] != "NONE"
    assert "NETLIFY_STATUS_TIMEOUT" in audit["known_netlify_cli_failure"]
    assert audit["cloudflare_pages_readiness"]["free_pages_available"] is True
    # Live host is now authenticated via Wrangler OAuth
    assert audit["cloudflare_pages_readiness"]["authenticated"] is True
    assert audit["cloudflare_pages_readiness"]["auth_method"] == "WRANGLER_OAUTH"



def test_public_asset_safety_gate_clean_pass():
    with tempfile.TemporaryDirectory() as tmp_dir:
        dir_path = Path(tmp_dir)
        html_file = dir_path / "index.html"
        html_file.write_text("<!DOCTYPE html><html><body><h1>Safe Landing Page</h1></body></html>")
        img_file = dir_path / "hero.webp"
        img_file.write_bytes(b"\x52\x49\x46\x46\x00\x00\x00\x00\x57\x45\x42\x50")

        passes, violations = PublicAssetSafetyGate.scan_directory(dir_path)
        assert passes is True
        assert len(violations) == 0


def test_public_asset_safety_gate_catches_forbidden_files():
    with tempfile.TemporaryDirectory() as tmp_dir:
        dir_path = Path(tmp_dir)
        (dir_path / "index.html").write_text("<html></html>")
        # Add forbidden .env file
        (dir_path / ".env").write_text("SECRET=123")
        # Add forbidden sqlite file
        (dir_path / "test.sqlite3").write_bytes(b"SQLite format 3\x00\x10\x00")

        passes, violations = PublicAssetSafetyGate.scan_directory(dir_path)
        assert passes is False
        assert len(violations) >= 2
        assert any(".env" in v for v in violations)
        assert any("sqlite" in v.lower() for v in violations)


def test_public_asset_safety_gate_catches_sensitive_content():
    with tempfile.TemporaryDirectory() as tmp_dir:
        dir_path = Path(tmp_dir)
        (dir_path / "index.html").write_text("<html><body>NETLIFY_AUTH_TOKEN = abc123def456</body></html>")

        passes, violations = PublicAssetSafetyGate.scan_directory(dir_path)
        assert passes is False
        assert any("NETLIFY_TOKEN" in v for v in violations)


def test_multi_venture_isolation_and_path_collision():
    router = CampaignDeployRouter()

    existing_deployments = [
        {
            "venture_id": "vnt_krd_ability_2026",
            "campaign_id": "camp_krd_finops_2026",
            "host_path": "/krd-ability/krd-finops/",
        },
        {
            "venture_id": "vnt_goclear_credit_2026",
            "campaign_id": "camp_goclear_readiness_2026",
            "host_path": "/goclear-credit/goclear-readiness/",
        },
    ]

    # Holiday Commerce deploying to own path -> ALLOWED
    iso_ok = router.evaluate_isolation(
        venture_id="vnt_holiday_commerce_pilot_2026",
        campaign_id="camp_holiday_ceramic_mug_2026",
        existing_deployments=existing_deployments,
    )
    assert iso_ok["allowed"] is True
    assert iso_ok["target_path"] == "/holiday-commerce-pilot/holiday-ceramic-mug/"

    # Holiday Commerce trying to deploy into KRD Ability path -> BLOCKED with PATH COLLISION
    existing_with_holiday_collision = existing_deployments + [
        {
            "venture_id": "vnt_krd_ability_2026",
            "campaign_id": "camp_krd_finops_2026",
            "host_path": "/holiday-commerce-pilot/holiday-ceramic-mug/",
        }
    ]
    iso_blocked = router.evaluate_isolation(
        venture_id="vnt_holiday_commerce_pilot_2026",
        campaign_id="camp_holiday_ceramic_mug_2026",
        existing_deployments=existing_with_holiday_collision,
    )
    assert iso_blocked["allowed"] is False
    assert iso_blocked["blocker"] == "DEPLOYMENT_PATH_COLLISION"


def test_campaign_host_generator_stages_files_and_rewrites_paths():
    with tempfile.TemporaryDirectory() as tmp_base:
        generator = CampaignHostGenerator(base_dir=Path(tmp_base))

        # Create dummy source html and media
        with tempfile.TemporaryDirectory() as src_dir:
            src_path = Path(src_dir)
            html_src = src_path / "source.html"
            html_src.write_text("""
            <html>
                <img src="../meta_holiday_ceramic_mug_1794355016.webp">
                <video src="../modal_holiday_ceramic_mug_video_1794413265.mp4"></video>
            </html>
            """)

            media_img = src_path / "meta_holiday_ceramic_mug_1794355016.webp"
            media_img.write_bytes(b"WEBP_DATA")
            media_vid = src_path / "modal_holiday_ceramic_mug_video_1794413265.mp4"
            media_vid.write_bytes(b"MP4_DATA")

            result = generator.stage_landing_page(
                venture_id="vnt_holiday_commerce_pilot_2026",
                campaign_id="camp_holiday_ceramic_mug_2026",
                source_html=html_src,
                referenced_assets=[media_img, media_vid],
            )

            assert result["safety_pass"] is True
            assert len(result["violations"]) == 0
            assert len(result["build_hash"]) == 64

            staged_html = Path(result["staged_html"]).read_text()
            assert "./meta_holiday_ceramic_mug_1794355016.webp" in staged_html
            assert "./modal_holiday_ceramic_mug_video_1794413265.mp4" in staged_html
            assert "../" not in staged_html


def test_deployment_identity_and_receipt_contracts():
    with tempfile.TemporaryDirectory() as tmp_base:
        generator = CampaignHostGenerator(base_dir=Path(tmp_base))
        router = CampaignDeployRouter(host_generator=generator)

        with tempfile.TemporaryDirectory() as src_dir:
            html_file = Path(src_dir) / "index.html"
            html_file.write_text("<!DOCTYPE html><html><body>Test</body></html>")

            identity, receipt = router.deploy_test_landing_page(
                venture_id="vnt_holiday_commerce_pilot_2026",
                campaign_id="camp_holiday_ceramic_mug_2026",
                product_id="prod_stoneware_mug_14oz",
                source_html=html_file,
                mode=HostingMode.SHARED_CAMPAIGN_HOST,
                simulate_remote_auth=True,
            )

            # Contract checks
            assert identity.environment == "test"
            assert identity.custom_domain == "NO"
            assert identity.production == "NO"
            assert identity.venture_id == "vnt_holiday_commerce_pilot_2026"
            assert identity.campaign_id == "camp_holiday_ceramic_mug_2026"

            assert receipt.custom_domain is False
            assert receipt.production is False
            assert receipt.cost == 0.0
            assert receipt.safety_gate_status == "PASS"
            assert len(receipt.build_hash) == 64
            assert receipt.status == "SUCCESS"
            assert receipt.error is None



def test_simulated_remote_cloudflare_deployment():
    with tempfile.TemporaryDirectory() as tmp_base:
        generator = CampaignHostGenerator(base_dir=Path(tmp_base))
        router = CampaignDeployRouter(host_generator=generator)

        with tempfile.TemporaryDirectory() as src_dir:
            html_file = Path(src_dir) / "index.html"
            html_file.write_text("<!DOCTYPE html><html><body>Simulated Remote</body></html>")

            identity, receipt = router.deploy_test_landing_page(
                venture_id="vnt_holiday_commerce_pilot_2026",
                campaign_id="camp_holiday_ceramic_mug_2026",
                product_id="prod_stoneware_mug_14oz",
                source_html=html_file,
                mode=HostingMode.SHARED_CAMPAIGN_HOST,
                simulate_remote_auth=True,
            )

            assert identity.host_provider == "CLOUDFLARE_PAGES"
            assert identity.status == "DEPLOYED_TEST"
            assert "https://nexus-campaigns.pages.dev/holiday-commerce-pilot/holiday-ceramic-mug/" in identity.public_url
            assert receipt.status == "SUCCESS"
            assert receipt.http_verified is True
            assert receipt.cost == 0.0


def test_dedicated_project_mode():
    with tempfile.TemporaryDirectory() as tmp_base:
        generator = CampaignHostGenerator(base_dir=Path(tmp_base))
        router = CampaignDeployRouter(host_generator=generator)

        with tempfile.TemporaryDirectory() as src_dir:
            html_file = Path(src_dir) / "index.html"
            html_file.write_text("<!DOCTYPE html><html><body>Dedicated Project</body></html>")

            identity, receipt = router.deploy_test_landing_page(
                venture_id="vnt_holiday_commerce_pilot_2026",
                campaign_id="camp_holiday_ceramic_mug_2026",
                product_id="prod_stoneware_mug_14oz",
                source_html=html_file,
                mode=HostingMode.DEDICATED_PROJECT,
                simulate_remote_auth=True,
            )

            assert identity.host_project == "holiday-ceramic-mug"
            assert identity.public_url == "https://holiday-ceramic-mug.pages.dev/"
            assert receipt.status == "SUCCESS"


def test_manifest_update_integration():
    with tempfile.TemporaryDirectory() as tmp_dir:
        manifest_file = Path(tmp_dir) / "manifest.json"
        manifest_file.write_text(json.dumps({
            "venture_id": "vnt_holiday_commerce_pilot_2026",
            "campaign_id": "camp_holiday_ceramic_mug_2026",
            "status": "WAITING_FOR_RAY_APPROVAL",
        }))

        identity = DeploymentIdentity(
            deployment_id="dep_test_123",
            venture_id="vnt_holiday_commerce_pilot_2026",
            campaign_id="camp_holiday_ceramic_mug_2026",
            product_id_or_offer_id="prod_test",
            build_id="bld_test",
            host_provider="CLOUDFLARE_PAGES",
            host_project="nexus-campaigns",
            host_path="/holiday/quiet-ritual/",
            public_url="https://nexus-campaigns.pages.dev/holiday/quiet-ritual/",
            environment="test",
        )
        receipt = DeploymentReceipt(
            deployment_receipt_id="rcpt_123",
            deployment_id="dep_test_123",
            venture_id="vnt_holiday_commerce_pilot_2026",
            campaign_id="camp_holiday_ceramic_mug_2026",
            host_provider="CLOUDFLARE_PAGES",
            host_project="nexus-campaigns",
            host_path="/holiday/quiet-ritual/",
            public_url="https://nexus-campaigns.pages.dev/holiday/quiet-ritual/",
            build_hash="abc123456",
            deployed_at="2026-11-11T12:00:00Z",
            http_verified=True,
            safety_gate_status="PASS",
            status="SUCCESS",
        )

        updated = update_campaign_manifest_with_deployment(manifest_file, identity, receipt)
        assert updated["deployment_id"] == "dep_test_123"
        assert updated["host_provider"] == "CLOUDFLARE_PAGES"
        assert updated["environment"] == "test"
        assert updated["custom_domain"] is False
        assert updated["production"] is False
        assert updated["deployment_receipt"]["status"] == "SUCCESS"


def test_scale_model_10_ventures_100_campaigns():
    router = CampaignDeployRouter()
    seen_paths = set()

    for v_idx in range(1, 11):
        v_id = f"vnt_scale_venture_{v_idx:02d}_2026"
        for c_idx in range(1, 11):
            c_id = f"camp_scale_offer_{v_idx:02d}_{c_idx:02d}_2026"
            v_slug = CampaignHostGenerator.get_slug(v_id)
            c_slug = CampaignHostGenerator.get_slug(c_id)
            path = f"/{v_slug}/{c_slug}/"

            assert path not in seen_paths, f"Path collision at {path}"
            seen_paths.add(path)

    assert len(seen_paths) == 100


def test_resolve_campaign_distribution_landing_target_for_31b1():
    manifest = {
        "deployment_id": "dep_holiday_123",
        "public_test_url": "https://nexus-campaigns.pages.dev/holiday/quiet-ritual/",
        "environment": "test",
        "host_provider": "CLOUDFLARE_PAGES",
        "deployment_status": "DEPLOYED_TEST",
    }
    from scripts.distribution.campaign_deploy_router import resolve_campaign_distribution_landing_target
    target = resolve_campaign_distribution_landing_target(manifest)

    assert target["landing_page_id"] == "landing_page_html"
    assert target["deployment_id"] == "dep_holiday_123"
    assert target["target_url"] == "https://nexus-campaigns.pages.dev/holiday/quiet-ritual/"
    assert target["environment"] == "test"


def test_auth_detection_state1_api_token(monkeypatch):
    """State 1: API token available -> authenticated via API_TOKEN."""
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "mock_dummy_token_for_test")
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "mock_dummy_account_id")

    probe = CampaignDeployRouter.probe_cloudflare_auth()
    assert probe["authenticated"] is True
    assert probe["auth_method"] == "API_TOKEN"
    assert probe["error"] is None


def test_auth_detection_state2_wrangler_oauth(monkeypatch):
    """State 2: No API token, but Wrangler OAuth available -> authenticated via WRANGLER_OAUTH."""
    monkeypatch.delenv("CLOUDFLARE_API_TOKEN", raising=False)
    monkeypatch.delenv("CF_API_TOKEN", raising=False)
    # Ensure cached account info is available so unit test doesn't stall on external network
    CampaignDeployRouter._cached_account_info = ("Goclearonline@gmail.com's Account", "76779da36e77e8d51b036949b16816c5")

    probe = CampaignDeployRouter.probe_cloudflare_auth()
    assert probe["authenticated"] is True
    assert probe["auth_method"] == "WRANGLER_OAUTH"
    assert probe["error"] is None
    assert probe["account_id"] == "76779da36e77e8d51b036949b16816c5"


def test_auth_detection_state3_neither_available(monkeypatch):
    """State 3: Neither API token nor Wrangler OAuth session available -> CLOUDFLARE_AUTH_REQUIRED."""
    monkeypatch.delenv("CLOUDFLARE_API_TOKEN", raising=False)
    monkeypatch.delenv("CF_API_TOKEN", raising=False)
    monkeypatch.setattr(CampaignDeployRouter, "find_wrangler_binary", lambda: None)
    monkeypatch.setattr(CampaignDeployRouter, "is_wrangler_authenticated", lambda: False)

    probe = CampaignDeployRouter.probe_cloudflare_auth()
    assert probe["authenticated"] is False
    assert probe["auth_method"] == "NONE"
    assert probe["error"] == "CLOUDFLARE_AUTH_REQUIRED"


def test_no_raw_tokens_in_receipt_or_manifest():
    """Verify that neither receipt nor manifest contains raw tokens or secrets."""
    receipt_path = Path("dist/creative/holiday_campaign_deployment_receipt.json")
    manifest_path = Path("dist/creative/campaign_holiday_ceramic_mug_manifest.json")

    for p in (receipt_path, manifest_path):
        if p.exists():
            text = p.read_text(encoding="utf-8")
            # Must not contain bearer tokens or sensitive prefixes
            assert "Bearer " not in text
            assert "CLOUDFLARE_API_TOKEN=" not in text
            assert "CF_API_TOKEN=" not in text
            assert "oauth_token" not in text.lower()


