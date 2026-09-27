import tempfile
import unittest
from unittest.mock import patch

from scripts.nexus_agent_platform.input_feed import input_metrics, record_input


class InputFeedTest(unittest.TestCase):
    def test_real_input_contract_is_deduplicated_and_measured(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict("os.environ", {"NEXUS_GOVERNED_DATA_DIR": temp}):
            first = record_input(
                input_id="input-1", business_or_nexus="NEXUS", department="TRADING",
                source="https://example.test/strategy", source_class="PUBLIC_REPOSITORY",
                why_this_matters="A concrete ruleset can be tested.", customer_or_system_problem="Need a testable hypothesis.",
                hypothesis="SMA rules can be backtested.", expected_value="Learning", testability="SAFE CHEAP REVERSIBLE",
                evidence_strength="MEDIUM", novelty="NEW", parent_goal="goal", next_owner="TRADING",
            )
            duplicate = record_input(
                input_id="input-1", business_or_nexus="NEXUS", department="TRADING",
                source="https://example.test/strategy", source_class="PUBLIC_REPOSITORY",
                why_this_matters="duplicate", customer_or_system_problem="duplicate", hypothesis="duplicate",
                expected_value="duplicate", testability="SAFE", evidence_strength="LOW", novelty="DUPLICATE",
                parent_goal="goal", next_owner="TRADING",
            )
            self.assertFalse(first.get("deduplicated"))
            self.assertTrue(duplicate.get("deduplicated"))
            metrics = input_metrics()
            self.assertEqual(metrics["real_inputs_acquired"], 1)
            self.assertEqual(metrics["unique_sources"], 1)
            self.assertEqual(metrics["testable_inputs"], 1)


if __name__ == "__main__":
    unittest.main()
