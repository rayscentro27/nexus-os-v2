import unittest
from unittest.mock import patch

from nexus_agent_platform import ui_skills_adapter as adapter


class UISkillsAdapterTests(unittest.TestCase):
    def test_route_is_bounded_and_governed(self):
        skills = [
            {"slug": "baseline-ui", "description": "spacing accessibility QA"},
            {"slug": "branding-redesign", "description": "branding redesign"},
            {"slug": "better-accessibility", "description": "accessibility responsive"},
            {"slug": "frontend-ui-engineering", "description": "frontend implementation"},
        ]
        with patch.object(adapter, "list_skills", return_value=skills):
            routed = adapter.route_task("Improve accessibility and responsive implementation")
        self.assertLessEqual(len(routed["selected_skills"]), 3)
        self.assertNotIn("branding-redesign", routed["selected_skills"])
        self.assertTrue(adapter.governance_check(routed)["approved_design_source_of_truth"])

    def test_remote_source_is_official(self):
        self.assertEqual(adapter.REMOTE, "https://www.ui-skills.com/mcp")


if __name__ == "__main__":
    unittest.main()
