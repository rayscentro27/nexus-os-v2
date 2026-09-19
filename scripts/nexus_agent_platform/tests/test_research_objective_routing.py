import json
import os
import unittest

from scripts.nexus_agent_platform.research_work_queue import ResearchWorkQueue


class ResearchObjectiveRoutingTest(unittest.TestCase):
    def test_queue_preserves_objective_source_candidates(self):
        item = ResearchWorkQueue.normalize({
            "work_id": "objective-1",
            "work_class": "ASSIGNED",
            "source_type": "RESEARCH_OBJECTIVE",
            "source_candidates": [{"source_type": "WEB_PAGE", "source_url": "https://example.test/a"}],
        })
        self.assertEqual(item["source_candidates"][0]["source_url"], "https://example.test/a")

    def test_existing_worker_selects_candidate_without_empty_url(self):
        import sys
        sys.path.insert(0, "scripts/research")
        from run_dispatched_research_job import select_scheduled_item

        prior = os.environ.get("NEXUS_WORK_ITEM_JSON")
        try:
            os.environ["NEXUS_WORK_ITEM_JSON"] = json.dumps({
                "work_id": "objective-1",
                "work_class": "ASSIGNED",
                "source_type": "RESEARCH_OBJECTIVE",
                "objective_id": "objective-1",
                "source_candidates": [{"source_id": "candidate-1", "source_type": "WEB_PAGE", "source_url": "https://example.test/a", "title": "Candidate"}],
            })
            selected = select_scheduled_item("CUSTOMER_DEMAND", "execution-1")
            self.assertEqual(selected["source_url"], "https://example.test/a")
            self.assertEqual(selected["selection_reason"], "governed_objective_source_candidate")
        finally:
            if prior is None:
                os.environ.pop("NEXUS_WORK_ITEM_JSON", None)
            else:
                os.environ["NEXUS_WORK_ITEM_JSON"] = prior


if __name__ == "__main__":
    unittest.main()
