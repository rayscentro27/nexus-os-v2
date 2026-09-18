import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from nexus_agent_platform.research.semantic_intelligence import (
    create_accept_execute_feedback,
    expand_customer_problem_queries,
    filter_customer_signals,
    route_qualified_finding,
    source_role,
    topicless_two_stage,
)


class SemanticIntelligenceTests(unittest.TestCase):
    def test_query_expansion_is_bounded_and_reusable(self):
        values = expand_customer_problem_queries(audience="startup owners", problem="funding denial and documentation")
        self.assertLessEqual(len(values), 8)
        self.assertTrue(any("denied" in value for value in values))

    def test_source_roles_and_negative_filter(self):
        self.assertEqual(source_role("REDDIT")["role"], "PRIMARY")
        self.assertEqual(source_role("GITHUB")["role"], "LOW_WEIGHT")
        accepted, rejected = filter_customer_signals([
            {"signal_id": "a", "source_type": "REDDIT", "excerpt": "I was denied funding for my new LLC and need options."},
            {"signal_id": "b", "source_type": "GITHUB", "excerpt": "This repository contains source code for an npm package."},
        ])
        self.assertEqual([row["signal_id"] for row in accepted], ["a"])
        self.assertEqual(rejected[0]["reason"], "capability_or_software_artifact_not_customer_pain")

    def test_route_requires_explicit_finding_class(self):
        self.assertEqual(route_qualified_finding({"finding_type": "FUNDING"})["target_department"], "CLYDE_CREDIT")
        self.assertEqual(route_qualified_finding({"finding_type": "SEO"})["target_department"], "SEO")
        self.assertEqual(route_qualified_finding({"finding_type": "CAPABILITY"})["target_department"], "SYSTEMS_ENGINEERING")
        self.assertEqual(route_qualified_finding({"finding_type": "TRADING_HYPOTHESIS"})["target_department"], "TRADING_RESEARCH")

    def test_topicless_two_stage_does_not_promote(self):
        result = topicless_two_stage([{"candidate_id": "c1", "topic": "funding denials"}, {"candidate_id": "c2", "topic": "credit documentation"}])
        self.assertEqual(result["theme_count"], 2)
        self.assertTrue(all(row["promotion"] == "REQUIRES_COHERENCE_AND_ALPHA" for row in result["stage2"]))

    def test_handoff_acceptance_execution_and_feedback_share_ids(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"NEXUS_GOVERNED_DATA_DIR": directory}):
            result = create_accept_execute_feedback(finding={"finding_id": "f1", "need_id": "n1", "investigation_id": "i1"}, alpha_receipt_id="a1", department="MARKETING", task="Prepare an internal opportunity brief")
            self.assertEqual(result["status"], "COMPLETE")
            self.assertFalse(result["external_mutation"])
            path = os.path.join(directory, "research_v2_handoffs.jsonl")
            self.assertIn(result["handoff_id"], Path(path).read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
