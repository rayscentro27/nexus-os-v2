import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.nexus_agent_platform.research_missions import build_proactive_question, charters, persist_question


class ResearchMissionsTest(unittest.TestCase):
    def test_all_required_charters_and_fields_exist(self):
        departments = {row["department"] for row in charters()}
        self.assertTrue({"TRADING", "SYSTEMS", "MARKETING", "CREATIVE", "OPERATIONS", "FINANCE", "CLYDE_FUNDING", "REVENUE_OPPORTUNITY_DISCOVERY"} <= departments)
        item = build_proactive_question(department="SYSTEMS", question="Should Nexus benchmark Needle?", why_this_research="Named technology request is otherwise unowned.", trigger="DEPARTMENT_MISSION", business_or_nexus="NEXUS")
        for key in ("WHY_THIS_RESEARCH", "TRIGGER", "DEPARTMENT", "BUSINESS_OR_NEXUS", "PARENT_GOAL", "PROJECT", "QUESTION", "EXPECTED_VALUE", "SOURCE_PLAN"):
            self.assertIn(key, item)
        self.assertEqual(item["research_mode"], "NEXUS_DEPARTMENTAL_PROACTIVE")
        self.assertTrue(item["alpha_eligible"])

    def test_persist_question_uses_existing_queue_and_is_idempotent(self):
        item = build_proactive_question(department="TRADING", question="What should be paper-tested?", why_this_research="Standing mission.", trigger="DEPARTMENT_MISSION", business_or_nexus="NEXUS")
        with tempfile.TemporaryDirectory() as temp:
            queue_path = Path(temp) / "queue.json"
            governed = Path(temp) / "governed"
            with patch("scripts.nexus_agent_platform.research_missions.default_queue") as queue, patch("scripts.nexus_agent_platform.research_missions.persistence") as persistence:
                persist_question(item)
                persistence.append_record.assert_called_once_with("research_questions", item)
                queued = queue.return_value.upsert.call_args.args[0]
                self.assertEqual(queued["work_id"], item["work_id"])
                self.assertEqual(queued["status"], "QUEUED")
                self.assertEqual(queued["source_type"], "RESEARCH_OBJECTIVE")


if __name__ == "__main__":
    unittest.main()
