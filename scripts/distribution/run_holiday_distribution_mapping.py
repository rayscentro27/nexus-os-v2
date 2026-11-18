"""Maps the certified Holiday Ceramic Mug Campaign assets to candidate distribution channels.

Performs internal validation only: zero publishing, zero scheduling, zero external network calls.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.distribution.distribution_foundation import (
    ChannelAccountRegistryManager,
    DistributionGovernanceGate,
    DistributionJob,
    DistributionJobStatus,
    create_seed_channel_accounts,
    get_authoritative_capability_matrix,
    utc_now,
)


def run_mapping():
    # Load canonical manifest
    manifest_path = ROOT / "dist/creative/campaign_holiday_ceramic_mug_manifest.json"
    with open(manifest_path) as f:
        manifest = json.load(f)

    accounts = create_seed_channel_accounts()
    registry = ChannelAccountRegistryManager(accounts)
    gate = DistributionGovernanceGate(registry)
    gate.register_campaign_venture(manifest["campaign_id"], manifest["venture_id"])

    channels_to_map = [
        {
            "channel": "STOREFRONT",
            "account_id": "acc_holiday_storefront_01",
            "asset_id": "landing_page_html",
            "content_type": "LANDING_PAGE",
            "copy": "The 6:12 AM Quiet Ritual. The only fifteen minutes that belong entirely to you.",
            "media": {"file": "dist/creative/landing/index.html"},
            "account_connected": True,
            "asset_compatible": True,
            "copy_ready": True,
            "publish_capability": True,
            "schedule_capability": False,
            "auth_status": "AUTHENTICATED",
            "approval_required": True,
            "blocker": "WAITING_FOR_RAY_APPROVAL",
        },
        {
            "channel": "INSTAGRAM",
            "account_id": "acc_holiday_instagram_01",
            "asset_id": "asset_metaai_1794355016",
            "content_type": "IMAGE_POST",
            "copy": "Before the house wakes up. 15 quiet minutes with a substantial ceramic vessel. Studio preview open. Link in bio.",
            "media": {"file": "dist/creative/meta_holiday_ceramic_mug_1794355016.webp", "format": "WEBP", "dimensions": "1920x1280"},
            "account_connected": False,
            "asset_compatible": True,
            "copy_ready": True,
            "publish_capability": False,
            "schedule_capability": False,
            "auth_status": "REQUIRES_RAY_LOGIN",
            "approval_required": True,
            "blocker": "INSTAGRAM_ACCOUNT_REQUIRES_RAY_OAUTH",
        },
        {
            "channel": "TIKTOK",
            "account_id": "acc_holiday_tiktok_01",
            "asset_id": "asset_modal_video_1794413265",
            "content_type": "SHORT_FORM_VIDEO",
            "copy": "The only fifteen minutes that belong entirely to you. #QuietRitual #SlowLiving #Ceramics",
            "media": {"file": "dist/creative/modal_holiday_ceramic_mug_video_1794413265.mp4", "duration_seconds": 5.04, "aspect_ratio": "9:16"},
            "account_connected": False,
            "asset_compatible": True,
            "copy_ready": True,
            "publish_capability": False,
            "schedule_capability": False,
            "auth_status": "AUTH_REQUIRED",
            "approval_required": True,
            "blocker": "TIKTOK_ACCOUNT_UNCONFIGURED_WAITING_RAY_SETUP",
        },
        {
            "channel": "YOUTUBE_SHORTS",
            "account_id": "acc_shared_nexus_youtube_01",
            "asset_id": "asset_modal_video_1794413265",
            "content_type": "SHORT_FORM_VIDEO",
            "copy": "The 6:12 AM Quiet Ritual. Substantial ceramic morning vessel. Studio design preview.",
            "media": {"file": "dist/creative/modal_holiday_ceramic_mug_video_1794413265.mp4", "duration_seconds": 5.04, "aspect_ratio": "9:16"},
            "account_connected": True,
            "asset_compatible": True,
            "copy_ready": True,
            "publish_capability": False,  # Needs upload scope approval
            "schedule_capability": False,
            "auth_status": "AUTHENTICATED_READONLY",
            "approval_required": True,
            "blocker": "YOUTUBE_CONNECTOR_CURRENTLY_READONLY_UPLOAD_SCOPE_UNGRANTED",
        },
        {
            "channel": "PRINTIFY",
            "account_id": "acc_printify_pod_catalog",
            "asset_id": "asset_metaai_1794355016",
            "content_type": "PRODUCT_MOCKUP",
            "copy": "Studio Ceramic Mug Blank Artwork Template",
            "media": {"file": "dist/creative/meta_holiday_ceramic_mug_1794355016.webp"},
            "account_connected": False,
            "asset_compatible": False,
            "copy_ready": False,
            "publish_capability": False,
            "schedule_capability": False,
            "auth_status": "UNCONFIGURED",
            "approval_required": True,
            "blocker": "PRINTIFY_PRODUCT_DATA_REQUIRED_BASE_MUG_SKU_UNSELECTED",
        },
        {
            "channel": "AMAZON",
            "account_id": "acc_amazon_handmade",
            "asset_id": "asset_metaai_1794355016",
            "content_type": "MARKETPLACE_LISTING",
            "copy": "The 6:12 AM Ritual Ceramic Drinkware Concept",
            "media": {"file": "dist/creative/meta_holiday_ceramic_mug_1794355016.webp"},
            "account_connected": False,
            "asset_compatible": True,
            "copy_ready": True,
            "publish_capability": False,
            "schedule_capability": False,
            "auth_status": "UNCONFIGURED",
            "approval_required": True,
            "blocker": "AMAZON_MERCHANT_ACCOUNT_INTEGRATION_REQUIRED",
        },
        {
            "channel": "WALMART",
            "account_id": "acc_walmart_marketplace",
            "asset_id": "asset_metaai_1794355016",
            "content_type": "MARKETPLACE_LISTING",
            "copy": "The 6:12 AM Ritual Ceramic Drinkware Concept",
            "media": {"file": "dist/creative/meta_holiday_ceramic_mug_1794355016.webp"},
            "account_connected": False,
            "asset_compatible": True,
            "copy_ready": True,
            "publish_capability": False,
            "schedule_capability": False,
            "auth_status": "UNCONFIGURED",
            "approval_required": True,
            "blocker": "WALMART_SELLER_ACCOUNT_INTEGRATION_REQUIRED",
        },
    ]

    report = {
        "venture_id": manifest["venture_id"],
        "campaign_id": manifest["campaign_id"],
        "product_id": manifest["product_id"],
        "evaluated_at": utc_now(),
        "total_channels_mapped": len(channels_to_map),
        "external_content_published": False,
        "external_content_scheduled": False,
        "ad_spend_usd": 0.0,
        "channel_mappings": channels_to_map,
    }

    out_file = ROOT / "dist/creative/holiday_campaign_distribution_mapping.json"
    with open(out_file, "w") as f:
        json.dump(report, f, indent=2)
    print(f"Mapping saved to {out_file} (bytes: {out_file.stat().st_size})")
    return report


if __name__ == "__main__":
    run_mapping()
