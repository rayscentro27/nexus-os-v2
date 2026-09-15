import json
import os
import tempfile
import unittest
from unittest.mock import patch


class YouTubeFollowupWorkerTests(unittest.TestCase):
    def _load(self, root):
        os.environ["NEXUS_GOVERNED_DATA_DIR"] = root
        from scripts.alpha import run_youtube_followup_worker as worker
        return worker

    def _seed(self, worker, claim_id="claim_test"):
        worker.append_record("alpha_claims", {"claim_id": claim_id, "video_id": "A5vj0ZJiVl0", "claim_text": "test claim", "revision": 1})
        worker.append_record("youtube_follow_ups", {"follow_up_id": "followup_test", "claim_id": claim_id, "video_id": "A5vj0ZJiVl0", "status": None})

    def test_followup_persists_evidence_and_revalidation(self):
        with tempfile.TemporaryDirectory() as root:
            worker = self._load(root)
            self._seed(worker)
            with patch.object(worker, "retrieve_page", return_value={"ok": True, "title": "Primary", "content_length": 10, "text_hash": "abc"}):
                result = worker.execute(limit=1)
            self.assertEqual(result["executed"], 1)
            execution = worker.read_records("youtube_follow_up_executions")[0]
            self.assertTrue(execution["evidence_created"])
            self.assertEqual(worker.read_records("youtube_claim_validations")[0]["validation_result"], "PARTIALLY_SUPPORTED")

    def test_completed_followup_is_not_redispatched(self):
        with tempfile.TemporaryDirectory() as root:
            worker = self._load(root)
            self._seed(worker)
            with patch.object(worker, "retrieve_page", return_value={"ok": True, "content_length": 10}):
                worker.execute(limit=1)
                second = worker.execute(limit=1)
            self.assertEqual(second["executed"], 0)

    def test_newest_retry_row_wins_over_legacy_row(self):
        with tempfile.TemporaryDirectory() as root:
            worker = self._load(root)
            self._seed(worker)
            worker.append_record("youtube_follow_ups", {"follow_up_id": "followup_test", "claim_id": "claim_test", "video_id": "A5vj0ZJiVl0", "status": "PARTIALLY_SUPPORTED", "retry_after": "2999-01-01T00:00:00+00:00"})
            with patch.object(worker, "retrieve_page", return_value={"ok": True, "content_length": 10}):
                result = worker.execute(limit=1)
            self.assertEqual(result["executed"], 0)

    def test_source_failure_is_retryable_and_does_not_raise(self):
        with tempfile.TemporaryDirectory() as root:
            worker = self._load(root,)
            self._seed(worker)
            with patch.object(worker, "retrieve_page", side_effect=TimeoutError("bounded canary")):
                result = worker.execute(limit=1)
            self.assertEqual(result["executed"], 1)
            execution = worker.read_records("youtube_follow_up_executions")[0]
            self.assertEqual(execution["revalidation_result"], "FAILED_RETRYABLE")
            self.assertEqual(len(execution["source_failures"]), 1)


if __name__ == "__main__":
    unittest.main()
