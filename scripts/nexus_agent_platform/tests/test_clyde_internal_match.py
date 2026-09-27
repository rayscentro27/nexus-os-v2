import unittest

from scripts.clyde.research_handoff_consumer import build_internal_profile_match


class ClydeInternalMatchTest(unittest.TestCase):
    def test_profile_variant_preserves_unknowns_and_surfaces_gap(self):
        requirements = {"identity_consistent": True, "cash_flow_known": True}
        baseline = build_internal_profile_match(
            {"identity_consistent": True, "cash_flow_known": None}, requirements,
            product="internal product comparison", source_refs=["official-source"],
        )
        variant = build_internal_profile_match(
            {"identity_consistent": False, "cash_flow_known": None}, requirements,
            product="internal product comparison", source_refs=["official-source"],
        )
        self.assertEqual(baseline["result"], "UNKNOWN")
        self.assertEqual(variant["result"], "GAP")
        self.assertIn("cash_flow_known", variant["unknowns"])
        self.assertFalse(variant["customer_application_submitted"])


if __name__ == "__main__":
    unittest.main()
