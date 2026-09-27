import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from clyde.research_handoff_consumer import build_internal_result


class ClydeResearchHandoffTests(unittest.TestCase):
    def test_qualified_handoff_becomes_internal_review_without_external_action(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifact = root / "reports/runtime/research_artifacts/web/cert-sba-funding.document.json"
            artifact.parent.mkdir(parents=True)
            artifact.write_text(json.dumps({"source_id": "cert-sba-funding", "source_url": "https://www.sba.gov/funding-programs/loans", "retrieved_at": "2026-09-27T00:00:00Z"}))
            normalized = artifact.with_name("cert-sba-funding.normalized.txt")
            normalized.write_text("SBA 7(a), 504, and microloan program evidence")
            result = build_internal_result(
                {"handoff_id": "h1", "finding_id": "f1", "need_id": "n1", "alpha_receipt_id": "a1"},
                {"decision": "QUALIFY", "investigation_id": "i1"},
                {},
                root=root,
            )
            self.assertEqual(result["decision"], "RESEARCH_MORE")
            self.assertTrue(result["verified"]["official_sba_evidence"])
            self.assertFalse(result["lender_evidence_found"])
            self.assertFalse(result["consequential_action_performed"])

    def test_rejects_non_clyde_target_before_processing(self):
        from clyde import research_handoff_consumer as consumer
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"NEXUS_GOVERNED_DATA_DIR": directory}):
            from nexus_agent_platform.governed import persistence
            persistence.append_record("research_v2_handoffs", {"handoff_id": "h2", "target_department": "MARKETING"})
            with self.assertRaises(ValueError):
                consumer.process_handoff("h2", root=Path(directory))


if __name__ == "__main__":
    unittest.main()
