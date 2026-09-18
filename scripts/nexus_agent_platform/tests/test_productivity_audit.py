import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import scripts.nexus_agent_platform.productivity_audit as audit


class ProductivityAuditTest(unittest.TestCase):
    def test_audit_compares_previous_state_and_persists(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state = root / "state.json"
            runtime = root / "data/runtime"
            runtime.mkdir(parents=True)
            queue = runtime / "research_work_queue.json"
            heartbeat = runtime / "research_heartbeat.json"
            programs = runtime / "research_program_registry.json"
            sources = runtime / "alpha_source_registry.json"
            jobs = runtime / "research_execution_jobs.jsonl"
            reports = root / "audits"
            session = root / "session.md"
            queue.write_text(json.dumps({"items": [{"status": "QUEUED"}]}))
            heartbeat.write_text(json.dumps({"heartbeat": "ACTIVE", "next_action": "continue"}))
            programs.write_text("[]")
            sources.write_text(json.dumps([{"source_type": "YOUTUBE_CHANNEL", "last_checked": "now"}] * 4))
            jobs.write_text(json.dumps({"status": "EVIDENCE_READY", "at": "2026-09-18T23:00:00+00:00"}) + "\n")
            with patch.object(audit, "STATE_PATH", state), patch.object(audit, "AUDIT_DIR", reports), patch.object(audit, "SESSION_REPORT", session), patch.object(audit, "ROOT", root), patch.object(audit, "_telegram", lambda text: {"status": "TESTED"}):
                result = audit.run_productivity_audit(force=True)
            self.assertEqual(result["research_summary"]["queue_depth"], 1)
            self.assertEqual(result["productive_actions"], 1)
            self.assertEqual(result["youtube_summary"]["channels_checked"], 4)
            self.assertTrue(list(reports.glob("*.json")))

    def test_status_message_is_bounded(self):
        message = audit._summary_message({"runtime_status": "HEALTHY", "research_summary": {"productive_actions": 1, "active_workers": 0}, "alpha_summary": {"reviews_completed": 0, "followups_executed": 0}, "department_summary": {"handoffs_created": 0, "completed": 0}, "youtube_summary": {"channels_checked": 4, "new_videos": 0}, "next_work": {"highest_priority": "Research", "next_action": "continue"}, "blockers": [] , "audit_id": "audit_test"})
        self.assertLess(len(message), 1200)
        self.assertIn("NEXUS OPERATIONS AUDIT", message)


if __name__ == "__main__":
    unittest.main()
