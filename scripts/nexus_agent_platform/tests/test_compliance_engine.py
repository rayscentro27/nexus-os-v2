import unittest

from scripts.nexus_agent_platform.compliance_engine import (
    ProductCompliancePack,
    automation_value,
    claim_intensity,
    classify_claim,
    compliance_receipt,
    evaluate_domain_claim,
    evaluate_headline,
    secondary_value_review,
    strongest_truthful_rewrite,
)


class ComplianceEngineTest(unittest.TestCase):
    def test_claim_classification_and_intensity_preserve_strong_marketing(self):
        claim = classify_claim("Turn funding uncertainty into a clearer readiness path.", ["research:1"])
        self.assertEqual(claim["claim_class"], "SUPPORTED_MARKETING_CLAIM")
        self.assertEqual(claim_intensity(claim)["level"], 3)
        self.assertTrue(claim_intensity(claim)["allowed"])

    def test_guarantee_is_rejected_with_strong_rewrite(self):
        result = evaluate_headline("Guaranteed funding approval", "Review your readiness first", [])
        self.assertEqual(result["decision"], "REVISE")
        self.assertNotIn("guaranteed", result["strongest_supported_alternative"].lower())
        self.assertIn("readiness", strongest_truthful_rewrite("Guaranteed funding approval").lower())

    def test_domain_rules_and_person_attack_boundary(self):
        trading = evaluate_domain_claim("This creator is a scammer with a 95% win rate", "trading", ["test:results"])
        self.assertEqual(trading["decision"], "BLOCK")
        funding = evaluate_domain_claim("Every new LLC will get approval", "funding", [])
        self.assertIn(funding["decision"], {"BLOCK", "RESEARCH_MORE"})

    def test_rejected_thesis_routes_to_secondary_value(self):
        routed = secondary_value_review(alpha_decision_id="alpha-1", original_use="trading strategy", rejection_reason="FAILED_TEST", evidence_refs=["test:1"])
        self.assertEqual(routed["secondary_value"], "COMPARISON")
        self.assertTrue(routed["content_value"])
        receipt = compliance_receipt("trading_finding", "finding-1", [classify_claim("The advertised result was not reproduced", ["test:1"], claim_class="TEST_RESULT")], "APPROVED_WITH_QUALIFIERS", evidence_refs=["test:1"])
        self.assertTrue(receipt["compliance_receipt_id"])

    def test_pack_and_automation_value_are_separate(self):
        pack = ProductCompliancePack("pack-1", "goclear", "readiness", "1")
        self.assertEqual(pack.status, "DRAFT")
        value = automation_value(api=True, cli=True, mcp=True, headless=True, output_retrieval=True)
        self.assertEqual(value["operational_value"], "HIGH")
        self.assertTrue(value["product_quality_separate"])


if __name__ == "__main__":
    unittest.main()
