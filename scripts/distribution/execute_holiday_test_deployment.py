"""Execute Holiday Campaign Test Deployment (Section 31B.0 Part 12-15).

Takes:
- VENTURE_ID: vnt_holiday_commerce_pilot_2026
- CAMPAIGN_ID: camp_holiday_ceramic_mug_2026
- PRODUCT_ID: prod_stoneware_mug_14oz
- Source landing page: dist/creative/landing/index.html
- Media dependencies: meta_holiday_ceramic_mug_1794355016.webp,
                     meta_holiday_ceramic_mug_video_1794355722.mp4,
                     modal_holiday_ceramic_mug_video_1794413265.mp4

Outputs:
- Staged static test package in dist/campaign-host/holiday-commerce-pilot/holiday-ceramic-mug/
- Canonical deployment receipt in dist/creative/holiday_campaign_deployment_receipt.json
- Updated campaign manifest in dist/creative/campaign_holiday_ceramic_mug_manifest.json
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.distribution.campaign_deploy_router import (
    CampaignDeployRouter,
    CampaignHostGenerator,
    HostingMode,
    update_campaign_manifest_with_deployment,
)

ROOT = Path(__file__).resolve().parents[2]


def main():
    landing_html = ROOT / "dist" / "creative" / "landing" / "index.html"
    media_assets = [
        ROOT / "dist" / "creative" / "meta_holiday_ceramic_mug_1794355016.webp",
        ROOT / "dist" / "creative" / "meta_holiday_ceramic_mug_video_1794355722.mp4",
        ROOT / "dist" / "creative" / "modal_holiday_ceramic_mug_video_1794413265.mp4",
    ]
    manifest_path = ROOT / "dist" / "creative" / "campaign_holiday_ceramic_mug_manifest.json"
    receipt_out_path = ROOT / "dist" / "creative" / "holiday_campaign_deployment_receipt.json"

    router = CampaignDeployRouter()
    identity, receipt = router.deploy_test_landing_page(
        venture_id="vnt_holiday_commerce_pilot_2026",
        campaign_id="camp_holiday_ceramic_mug_2026",
        product_id="prod_stoneware_mug_14oz",
        source_html=landing_html,
        referenced_assets=media_assets,
        preferred_provider="auto",
        mode=HostingMode.SHARED_CAMPAIGN_HOST,
    )

    # Save canonical deployment receipt
    receipt_dict = receipt.to_dict()
    receipt_out_path.write_text(json.dumps(receipt_dict, indent=2), encoding="utf-8")
    print(f"Deployment receipt written to {receipt_out_path}")

    # Update canonical campaign manifest
    updated_manifest = update_campaign_manifest_with_deployment(
        manifest_path=manifest_path,
        identity=identity,
        receipt=receipt,
    )
    print(f"Campaign manifest updated at {manifest_path}")

    print("\nDEPLOYMENT EXECUTION SUMMARY:")
    print(f"DEPLOYMENT_ID={identity.deployment_id}")
    print(f"VENTURE_ID={identity.venture_id}")
    print(f"CAMPAIGN_ID={identity.campaign_id}")
    print(f"STATUS={identity.status}")
    print(f"HOST_PROVIDER={identity.host_provider}")
    print(f"HOST_PROJECT={identity.host_project}")
    print(f"HOST_PATH={identity.host_path}")
    print(f"PUBLIC_URL={identity.public_url}")
    print(f"ENVIRONMENT={identity.environment}")
    print(f"CUSTOM_DOMAIN={identity.custom_domain}")
    print(f"PRODUCTION={identity.production}")
    print(f"BUILD_HASH={receipt.build_hash}")
    print(f"SAFETY_GATE_STATUS={receipt.safety_gate_status}")
    print(f"COST=${receipt.cost:.2f}")
    print(f"ERROR={receipt.error}")


if __name__ == "__main__":
    main()
