"""Focused WP9.1 regression checks for Night 1 communication repairs."""
import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import wp9_company_scheduler as scheduler


class Night1CommunicationTests(unittest.TestCase):
    def test_cycle_summary_preserves_executive_context(self):
        record = {"finance_rollup": {"cash_cost_usd": 0, "compute_consumed": 2.5,
                                     "free_credit_consumed": 1, "quota_consumed": 3,
                                     "estimated_replacement_cost_usd": "UNKNOWN"},
                  "work_orders": [
                      {"execution": {"department": "ALPHA", "status": "NO_MEANINGFUL_WORK"}},
                      {"execution": {"department": "GROWTH", "status": "FAILED",
                                      "result": {"stderr_tail": "launch environment unavailable"}}},
                      {"execution": {"department": "CREATIVE", "status": "COMPLETED",
                                      "result": "review artifact written"}}]}
        text = scheduler.cycle_summary(record)
        self.assertIn("Creative: review artifact written", text)
        self.assertIn("Alpha: no new evidence available", text)
        self.assertIn("Growth: launch environment unavailable", text)
        self.assertIn("Compute: 2.5 minutes", text)
        self.assertIn("Needs you:", text)
        self.assertLessEqual(len(text), 3800)

    def test_morning_window_is_local_six_to_local_six(self):
        at = datetime.fromisoformat("2026-09-02T06:00:01-07:00")
        start, end = scheduler.morning_window(at)
        self.assertEqual(start.isoformat(), "2026-09-01T06:00:00-07:00")
        self.assertEqual(end.isoformat(), "2026-09-02T06:00:00-07:00")

    def test_test_and_report_delivery_keys_are_separate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch.object(scheduler, "RUNTIME", root), patch.object(scheduler, "load_runtime_env", return_value={}):
                with patch.dict(scheduler.os.environ, {"RESEND_API_KEY": "key", "RESEND_FROM_EMAIL": "from", "RESEND_TO_EMAIL": "to", "SUPABASE_URL": "https://example.test", "VITE_SUPABASE_ANON_KEY": "anon", "E2E_ADMIN_EMAIL": "admin", "E2E_ADMIN_PASSWORD": "password"}, clear=False):
                    with patch("urllib.request.urlopen", side_effect=AssertionError("network not needed")):
                        result = scheduler.send_email("test", "test", cycle="transport-test-cycle", dry_run=True)
                        report = scheduler.send_email("report", "report", cycle="morning-window-20260902", dry_run=True)
            self.assertEqual(result["status"], "DRY_RUN")
            self.assertEqual(report["status"], "DRY_RUN")
            self.assertNotEqual(result["fingerprint"], report["fingerprint"])
            self.assertEqual(len(list((root / "email").glob("*.json"))), 2)

    def test_failed_email_receipt_is_persisted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch.object(scheduler, "RUNTIME", root), patch.object(scheduler, "load_runtime_env", return_value={}):
                with patch.dict(scheduler.os.environ, {"RESEND_API_KEY": "key", "RESEND_FROM_EMAIL": "from", "RESEND_TO_EMAIL": "to", "SUPABASE_URL": "https://example.test", "VITE_SUPABASE_ANON_KEY": "anon", "E2E_ADMIN_EMAIL": "admin", "E2E_ADMIN_PASSWORD": "password"}, clear=False):
                    with patch("urllib.request.urlopen", side_effect=OSError("offline")):
                        result = scheduler.send_email("report", "report", cycle="failure-window")
            self.assertEqual(result["status"], "FAILED")
            receipt = json.loads((root / "email" / "failure-window-morning.json").read_text())
            self.assertEqual(receipt["status"], "FAILED")


if __name__ == "__main__":
    unittest.main()
