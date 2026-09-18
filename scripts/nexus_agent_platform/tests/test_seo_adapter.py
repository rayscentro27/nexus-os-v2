import json
import os
import tempfile
import unittest
from unittest.mock import patch

from nexus_agent_platform.research import seo_adapter


class SeoAdapterTests(unittest.TestCase):
    def test_allowlist_is_typed_and_blocks_mutations(self):
        self.assertTrue(seo_adapter._allowlist_check(["crawl", "--url", "https://example.com", "--json"]))
        self.assertFalse(seo_adapter._allowlist_check(["auth", "login"]))
        self.assertFalse(seo_adapter._allowlist_check(["crawl", "--url", "https://example.com", "--publish"]))

    def test_parser_requires_complete_json(self):
        self.assertEqual(seo_adapter._parse_json_output('{"pages": []}'), {"pages": []})
        self.assertIsNone(seo_adapter._parse_json_output('log line\n{"pages": []}'))

    def test_normalization_is_stable_and_preserves_coverage(self):
        page = {"url": "https://example.com/"}
        finding = {"ruleId": "canonical_missing", "severity": "medium", "category": "canonical", "coverage": "PARTIAL"}
        one = seo_adapter._normalize_finding(page, finding, "SITE_TECHNICAL", "https://example.com")
        two = seo_adapter._normalize_finding(page, finding, "SITE_TECHNICAL", "https://example.com")
        self.assertEqual(one["seo_evidence_id"], two["seo_evidence_id"])
        self.assertEqual(one["content_hash"], two["content_hash"])
        self.assertEqual(one["coverage_state"], "PARTIAL")

    def test_adapter_persists_and_dedupes_governed_findings(self):
        result = {"definition": {"config": {"url": "https://example.com"}}, "summary": {"crawledUrls": 1},
                  "pages": [{"url": "https://example.com"}], "issues": [{"ruleId": "x", "severity": "low", "category": "content"}]}
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(os.environ, {"NEXUS_GOVERNED_DATA_DIR": directory}):
                with patch.object(seo_adapter, "_run_cmd", return_value=(json.dumps(result), "", 0, 0.2)):
                    first = seo_adapter.adapter(request_id="r1", work_id="w1", url="https://example.com")
                    second = seo_adapter.adapter(request_id="r2", work_id="w2", url="https://example.com")
        self.assertEqual(first["persisted_findings"], 1)
        self.assertEqual(second["linked_existing"], 1)

    def test_invalid_request_does_not_invoke_runtime(self):
        with patch.object(seo_adapter, "_run_cmd") as run:
            result = seo_adapter.adapter(request_id="r", work_id="w", url="file:///tmp/x")
        self.assertEqual(result["status"], "REJECTED")
        run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
