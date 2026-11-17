import tempfile, unittest
from pathlib import Path
from scripts.nexus_agent_platform.project_portfolio_memory import save, search, match_research_and_reopen

class PortfolioMemoryTests(unittest.TestCase):
 def test_save_and_retrieve_by_research_trigger(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/"memory.jsonl"
   save({"project_id":"p1","version":"v1","score":4,"outputs":["workbook"],"weaknesses":["demand"],"missing_components":[],"improvement_targets":["interviews"],"research_triggers":["spreadsheet cleanup demand"],"next_stage":"RAY_REVIEW"},p)
   self.assertEqual(search("spreadsheet demand",p)[0]["project_id"],"p1")
 def test_requires_complete_portfolio_record(self):
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaises(ValueError): save({"project_id":"p"},Path(d)/"x")
 def test_new_research_finds_reopen_candidate_without_authority_change(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/"memory.jsonl"
   save({"project_id":"p1","version":"v1","score":4,"outputs":[],"weaknesses":[],"missing_components":[],"improvement_targets":[],"research_triggers":["customer demand evidence"],"next_stage":"RAY_REVIEW"},p)
   found=match_research_and_reopen("new customer demand evidence",p)
   self.assertEqual(found[0]["status"],"REOPEN_CANDIDATE")
   self.assertFalse(found[0]["authority_change"])

if __name__=="__main__": unittest.main()
