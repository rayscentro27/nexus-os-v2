import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.nexus_agent_platform.alpha_decision_policy import apply_policy, record_ray_override


class AlphaDecisionPolicyTest(unittest.TestCase):
    def test_reversible_low_cost_uncertainty_becomes_test(self):
        result = apply_policy({"query": "Test a small internal offer", "test_profile": {"plausible_upside": "YES", "reversibility": "REVERSIBLE", "no_external_action": True, "expected_cost_to_test": "LOW", "customer_demand_signal": "YES"}, "handoff_target": "MARKETING"}, {"decision": "RESEARCH_MORE", "reasoning_summary": "Demand needs validation", "deficiencies": ["conversion unknown"]})
        self.assertEqual(result["decision"], "TEST")
        self.assertEqual(result["next_owner"], "MARKETING")

    def test_hard_safety_boundary_stays_reject(self):
        result = apply_policy({"query": "unsafe paid action", "test_profile": {"plausible_upside": "YES", "reversibility": "REVERSIBLE", "no_external_action": True}}, {"decision": "TEST", "reasoning_summary": "unsafe security exposure"})
        self.assertEqual(result["decision"], "REJECT")
        self.assertTrue(result["hard_blockers"])

    def test_missing_evidence_without_test_profile_does_not_get_fabricated_test(self):
        result = apply_policy({"query": "unresolved source"}, {"decision": "RESEARCH_MORE", "reasoning_summary": "source unavailable"})
        self.assertEqual(result["decision"], "RESEARCH_MORE")

    def test_department_candidate_profiles_preserve_safe_next_step(self):
        cases = {
            "SYSTEMS": "isolated compatibility benchmark",
            "TRADING": "bounded backtest",
            "GOCLEAR": "internal concept test",
            "REVENUE": "zero-cost demand test",
        }
        for department, expected in cases.items():
            result = apply_policy({"query": f"{department} candidate", "handoff_target": department, "test_profile": {"plausible_upside": "YES", "reversibility": "REVERSIBLE", "no_external_action": True, "expected_cost_to_test": "LOW", "reuse_of_existing_nexus_capability": "YES"}}, {"decision": "RESEARCH_MORE", "reasoning_summary": expected, "deficiencies": ["result unknown"]})
            self.assertEqual(result["decision"], "TEST")
            self.assertEqual(result["next_owner"], department)

    def test_ray_override_is_append_only_and_authorized(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch.dict("os.environ", {"NEXUS_GOVERNED_DATA_DIR": temp}):
                row = record_ray_override(evaluation_id="eval-1", decision="TEST", reason="cheap reversible benchmark")
                self.assertEqual(row["authorized_by"], "RAY")
                self.assertEqual(row["decision"], "TEST")
                self.assertTrue((Path(temp) / "alpha_decision_overrides.jsonl").exists())


if __name__ == "__main__":
    unittest.main()
