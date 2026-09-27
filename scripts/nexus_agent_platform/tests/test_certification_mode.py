import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.nexus_agent_platform.alpha_decision_policy import apply_policy
from scripts.nexus_agent_platform.certification_mode import (
    CERTIFICATION_DISPOSITION,
    certification_metrics,
    create_experiment,
    current_mode,
    update_experiment,
)


class CertificationModeTest(unittest.TestCase):
    def profile(self):
        return {
            "can_this_be_tested_safely": True,
            "can_this_be_tested_cheaply": True,
            "can_this_be_tested_reversibly": True,
            "can_this_teach_nexus_something": True,
            "hard_blocker_present": False,
        }

    def test_build_mode_converts_safe_research_more_to_certification_test(self):
        with patch.dict("os.environ", {"NEXUS_OPERATING_MODE": "BUILD_CERTIFICATION"}):
            result = apply_policy(
                {"query": "Benchmark a candidate in an isolated internal sandbox", "test_profile": self.profile()},
                {"decision": "RESEARCH_MORE", "reasoning_summary": "Compatibility remains uncertain", "deficiencies": ["benchmark"]},
            )
        self.assertEqual(current_mode(), "BUILD_CERTIFICATION")
        self.assertEqual(result["decision"], CERTIFICATION_DISPOSITION)
        self.assertFalse(result["hard_blocker_present"])
        self.assertEqual(result["why_certification_test_not_used"], "")

    def test_normal_mode_preserves_gating(self):
        with patch.dict("os.environ", {"NEXUS_OPERATING_MODE": "NORMAL_PRODUCTION"}):
            result = apply_policy(
                {"query": "Benchmark a candidate", "test_profile": self.profile()},
                {"decision": "RESEARCH_MORE", "reasoning_summary": "Evidence is incomplete"},
            )
        self.assertEqual(result["decision"], "RESEARCH_MORE")

    def test_hard_blocker_wins_over_certification_mode(self):
        with patch.dict("os.environ", {"NEXUS_OPERATING_MODE": "BUILD_CERTIFICATION"}):
            result = apply_policy(
                {"query": "Run live trading", "test_profile": self.profile()},
                {"decision": "RESEARCH_MORE", "reasoning_summary": "live trading would be required"},
            )
        self.assertEqual(result["decision"], "REJECT")
        self.assertTrue(result["hard_blocker_present"])

    def test_unknown_testability_does_not_get_fabricated(self):
        with patch.dict("os.environ", {"NEXUS_OPERATING_MODE": "BUILD_CERTIFICATION"}):
            result = apply_policy({"query": "Ambiguous candidate"}, {"decision": "RESEARCH_MORE", "reasoning_summary": "identity unknown"})
        self.assertEqual(result["decision"], "RESEARCH_MORE")
        self.assertIn("Explicit testability evidence missing", result["why_certification_test_not_used"])

    def test_learning_artifact_is_append_only_and_complete(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch.dict("os.environ", {"NEXUS_GOVERNED_DATA_DIR": temp}):
                row = create_experiment(
                    department="SYSTEMS", source_finding="finding-1", alpha_decision="RESEARCH_MORE",
                    hypothesis="A bounded benchmark can resolve compatibility", why_test_anyway="safe internal learning",
                    expected_result="benchmark receipt", test_method="ISOLATED_ORACLE", next_test="review benchmark", next_owner="SYSTEMS",
                )
                updated = update_experiment(row["experiment_id"], actual_result="blocked", lesson="Identity still ambiguous", completion_state="BLOCKED_EXTERNAL")
                self.assertEqual(updated["lesson"], "Identity still ambiguous")
                metrics = certification_metrics()
                self.assertEqual(metrics["certification_tests_created"], 1)
                self.assertEqual(metrics["experiment_lessons_created"], 1)
                path = Path(temp) / "certification_experiments.jsonl"
                records = [json.loads(line) for line in path.read_text().splitlines()]
                self.assertTrue({"experiment_id", "hypothesis", "expected_result", "actual_result", "lesson", "next_test", "next_owner"}.issubset(records[-1]))


if __name__ == "__main__":
    unittest.main()
