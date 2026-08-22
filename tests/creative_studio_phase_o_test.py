import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from nexus_agent_platform.creative.studio import (
    COMFYUI_STATUS, REMOTION_LICENSE_STATUS, REMOTION_TEMPLATE,
    answer_creative_question, assert_public_action_blocked,
    build_copy_asset, build_creative_brief_from_growth, build_image_specs,
    build_storyboard_asset, creative_portfolio, persist_creative_asset,
    persist_creative_brief, persist_creative_receipt, validate_creative_brief,
)


class CreativeStudioPhaseOTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {"NEXUS_GOVERNED_DATA_DIR": self.tmp.name})
        self.env.start()
        self.growth = {"id": "growth-test", "title": "Business funding readiness", "objective": "Prepare an internal brief", "status": "NEEDS_RAY_REVIEW", "target_offer": "goclear_readiness_review_97", "primary_metric": "readiness_review_leads", "evidence_refs": ["ev-public"]}
        self.brief = build_creative_brief_from_growth(self.growth, {"id": "opp-test"})

    def tearDown(self):
        self.env.stop(); self.tmp.cleanup()

    def test_contract_and_provenance(self):
        self.assertEqual(validate_creative_brief(self.brief), [])
        saved = persist_creative_brief(self.brief)
        self.assertEqual(saved["persistence"], "CREATED")
        self.assertEqual(persist_creative_brief(self.brief)["persistence"], "DUPLICATE_SUPPRESSED")
        self.assertEqual(saved["source_growth_id"], "growth-test")
        self.assertEqual(saved["source_opportunity_id"], "opp-test")
        self.assertEqual(saved["evidence_refs"], ["ev-public"])

    def test_copy_storyboard_specs_and_safety(self):
        self.assertEqual(persist_creative_asset(build_copy_asset(self.brief))["quality_score"], 92)
        self.assertEqual(build_storyboard_asset(self.brief)["content"]["template_id"], REMOTION_TEMPLATE)
        self.assertEqual(len(build_image_specs(self.brief)), 2)
        with self.assertRaises(PermissionError): assert_public_action_blocked("publish")
        with self.assertRaises(PermissionError): assert_public_action_blocked("send_email")

    def test_render_receipt_and_duplicate(self):
        asset = build_storyboard_asset(self.brief)
        asset["asset_type"] = "REMOTION_VIDEO"
        first = persist_creative_asset(asset)
        duplicate = persist_creative_asset(asset)
        self.assertEqual(first["persistence"], "CREATED")
        self.assertEqual(duplicate["persistence"], "DUPLICATE_SUPPRESSED")
        receipt = persist_creative_receipt({"asset_id": first["asset_id"], "status": "SUCCESS", "artifact_ref": "runtime-only.mp4"})
        self.assertFalse(receipt["external_action_performed"])

    def test_optional_capability_truth(self):
        self.assertEqual(REMOTION_LICENSE_STATUS, "EVALUATION_ONLY")
        self.assertEqual(COMFYUI_STATUS, "DEFERRED_TO_GPU_PHASE")
        answer = answer_creative_question("Has anything been published?")
        self.assertFalse(answer["published"])
        self.assertEqual(creative_portfolio()["public_actions"], "BLOCKED")


if __name__ == "__main__":
    unittest.main()
