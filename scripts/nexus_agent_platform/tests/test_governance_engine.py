import unittest

from scripts.nexus_agent_platform.governance_engine import GovernanceEngine, GovernanceStore


class GovernanceEngineTest(unittest.TestCase):
    def setUp(self):
        self.engine = GovernanceEngine(GovernanceStore(), persist=False)

    def test_internal_research_is_autonomous_with_receipt(self):
        result = self.engine.evaluate_authority("RESEARCH", "RESEARCH_PUBLIC_INFORMATION")
        self.assertEqual(result["decision"], "ALLOW")
        self.assertEqual(result["authority_tier"], "TIER_0_AUTONOMOUS")
        self.assertTrue(result["governance_receipt_id"])

    def test_external_and_spend_actions_require_ray(self):
        self.assertEqual(self.engine.evaluate_publication()["decision"], "HUMAN_APPROVAL_REQUIRED")
        self.assertEqual(self.engine.evaluate_spend_authority(cost="UNKNOWN")["decision"], "REQUIRES_HUMAN_APPROVAL")

    def test_sensitive_worker_data_is_blocked_and_cross_business_isolation_holds(self):
        self.assertEqual(self.engine.evaluate_data_access("TEMPORARY_WORKER", "CUSTOMER_PII")["decision"], "BLOCK")
        self.assertEqual(self.engine.evaluate_authority("SOCIAL_DISTRIBUTION", "CREATE_INTERNAL_ARTIFACT", {"cross_business": True})["decision"], "BLOCK")
        self.assertEqual(self.engine.evaluate_authority("CREATIVE", "RUN_EXTERNAL_FREE_COMPUTE", {"gpu_required": True, "gpu_capability_verified": False})["decision"], "BLOCK")
        self.assertEqual(self.engine.evaluate_authority("CUSTOMER_SERVICE", "READ_CUSTOMER_STATE", {"customer_verified": False})["decision"], "BLOCK")

    def test_retry_reroute_and_scoped_pause_primitives_are_bounded(self):
        self.assertTrue(self.engine.evaluate_retry("RETRYABLE_INTERNAL")["allowed"])
        self.assertFalse(self.engine.evaluate_retry("PERMANENT_FAILURE")["allowed"])
        self.assertTrue(self.engine.evaluate_reroute(from_capability="web_page", to_capability="multi_source_research", reason="missing source")["allowed"])

    def test_crj_missing_source_is_repairable_not_ray_default(self):
        result = self.engine.govern_crj_failure({"objective_id": "crj-goclear-capability-research-v1", "status": "FAILED_RETRYABLE", "error": "unknown url type: ''"})
        self.assertEqual(result["decision"], "ALLOW")
        self.assertFalse(result["ray_required"])
        self.assertIn("REPAIR_OR_REROUTE", result["next_action"])

    def test_ray_override_is_scoped(self):
        result = self.engine.record_override(policy="publication", reason="bounded campaign review", authorized_by="RAY", scope={"campaign_id": "c1"}, expires_at="2099-01-01T00:00:00Z")
        self.assertEqual(result["authorized_by"], "RAY")
        with self.assertRaises(ValueError):
            self.engine.record_override(policy="publication", reason="bad", authorized_by="NOVA", scope={}, expires_at="2099-01-01T00:00:00Z")


if __name__ == "__main__":
    unittest.main()
