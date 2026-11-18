"""Read-only contract checks for the protected Nova r25 implementation."""
from __future__ import annotations

import importlib
import hashlib
import inspect
import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


class R25BaselineContracts(unittest.TestCase):
    def test_primary_modules_import(self):
        for module in (
            "nova.nova_telegram_worker",
            "nova.context_authority",
            "nova.operator_v1",
            "nova.approved_mcp_registry",
            "nova.nexus_mcp_status",
            "research.research_case_engine",
            "nexus_agent_platform.dispatcher_once",
        ):
            with self.subTest(module=module):
                self.assertIsNotNone(importlib.import_module(module))

    def test_critical_symbols_and_read_only_snapshot_contract(self):
        from nova import context_authority, operator_v1

        self.assertTrue(callable(context_authority.resolve_context))
        self.assertTrue(callable(operator_v1.status_read))
        self.assertTrue(callable(operator_v1.get_authoritative_mission_snapshot))
        self.assertIn("NO_ACTIVE_MISSION", inspect.getsource(operator_v1.status_read))
        self.assertIn("mode=ro", inspect.getsource(operator_v1._read_only_connect))
        self.assertTrue(callable(operator_v1._snapshot_from_mission_row))

    def test_delivery_guard_covers_all_reply_paths(self):
        worker = importlib.import_module("nova.nova_telegram_worker")
        status_fast_path = inspect.getsource(worker._deliver_authoritative_mission_answer)
        update_router = inspect.getsource(worker._process_message_inner)
        sender = inspect.getsource(worker._deliver_response)
        self.assertIn("_set_owner_turn_governance_context", status_fast_path)
        self.assertIn("_deliver_response", status_fast_path)
        self.assertIn("_set_owner_turn_governance_context", update_router)
        self.assertIn("_deliver_response", update_router)
        self.assertIn("_tg_send_attempt", sender)
        self.assertIn("_save_delivery", sender)
        self.assertTrue(callable(worker.delivery_completeness_check))

    def test_poller_offset_and_duplicate_update_delivery_guards(self):
        worker = importlib.import_module("nova.nova_telegram_worker")
        with tempfile.TemporaryDirectory() as temporary:
            offset_file = Path(temporary) / "offset.json"
            with patch.object(worker, "NOVA_OFFSET_PATH", str(offset_file)):
                self.assertEqual(worker.load_offset(), 0)
                worker.save_offset(501)
                self.assertEqual(worker.load_offset(), 501)
                worker.save_offset(502)
                self.assertEqual(worker.load_offset(), 502)

            with patch.object(worker, "_update_already_delivered", return_value=True), \
                 patch.object(worker, "_log") as log:
                duplicate = {"update_id": 502, "message": {
                    "text": "status?", "chat": {"id": 1}, "from": {"id": 1}}}
                self.assertTrue(worker.process_message(duplicate))
                log.assert_called_once()

    def test_state_precedence_contract_is_explicit(self):
        from nova.context_authority import resolve_context

        source = (ROOT / "scripts/nova/context_authority.py").read_text()
        for token in ("NO_ACTIVE_MISSION", "_IMMEDIATE", "DURABLE_ENTITY_LINEAGE", "PREVIOUS_ASSISTANT_TURN"):
            with self.subTest(token=token):
                self.assertIn(token, source)
        self.assertLess(source.index("if _CURRENT.search(message)"), source.index("if _IMMEDIATE.search(message)"))
        self.assertLess(source.index("if _CONTINUATION.search(message)"), source.index("if _IMMEDIATE.search(message)"))

        current = resolve_context(
            "What are you working on right now?",
            active_mission={"status": "NO_ACTIVE_MISSION"},
            recent_completed_mission={"mission_id": "old", "status": "COMPLETE"},
            long_term_memory={"status": "BLOCKED"},
        )
        self.assertEqual(current["resolved_referent"], {"status": "NO_ACTIVE_MISSION"})
        immediate = resolve_context(
            "Summarize that",
            previous_turn={"assistant_text": "The prior answer"},
            long_term_memory={"text": "stale memory"},
        )
        self.assertEqual(immediate["context_source"], "PREVIOUS_ASSISTANT_TURN")
        exact = resolve_context(
            "Continue that case",
            entity_lineage={"case_id": "case_exact"},
            long_term_memory={"case_id": "similar_case"},
        )
        self.assertEqual(exact["resolved_entity_id"], "case_exact")

    def test_verified_terminal_state_outranks_prior_failure_events(self):
        from nova.operator_v1 import _snapshot_from_mission_row

        db = sqlite3.connect(":memory:")
        db.row_factory = sqlite3.Row
        db.executescript("""
          CREATE TABLE operator_events(mission_id TEXT, event_type TEXT, created_at TEXT, payload_json TEXT);
          CREATE TABLE operator_steps(mission_id TEXT, step_id TEXT, sequence INTEGER, goal TEXT, status TEXT);
          CREATE TABLE operator_lineage(mission_id TEXT, entity_type TEXT, entity_id TEXT, entity_role TEXT, last_verified_at TEXT);
          INSERT INTO operator_events VALUES ('m1','BLOCKED','2026-10-19T00:00:00Z','{}');
          INSERT INTO operator_events VALUES ('m1','RECOVERY','2026-10-19T00:10:00Z','{}');
          INSERT INTO operator_events VALUES ('m1','CAPABILITY_GAP','2026-10-19T00:20:00Z','{}');
          INSERT INTO operator_events VALUES ('m1','TECHNICAL_BOUNDARY','2026-10-19T00:30:00Z','{}');
          INSERT INTO operator_events VALUES ('m1','MISSION_COMPLETE','2026-10-19T01:00:00Z','{}');
        """)
        row = {
            "mission_id": "m1", "objective_text": "existing work", "mission_success_condition_json": "{}",
            "mission_success_evidence_json": json.dumps({"recommendation": "PARK"}),
            "final_result_json": json.dumps({"response": "verified final"}), "status": "COMPLETE",
            "mission_success_verified": 1, "current_step_id": None, "mission_completion_reason": "verified",
            "completed_at": "2026-10-19T01:00:00Z", "updated_at": "2026-10-19T01:00:00Z",
        }
        snapshot = _snapshot_from_mission_row(db, row)
        self.assertEqual(snapshot["status"], "COMPLETE")
        self.assertTrue(snapshot["success_verified"])
        self.assertEqual(snapshot["final_outcome"], "verified final")
        self.assertEqual(
            {event["event_type"] for event in snapshot["historical_problem_events"]},
            {"BLOCKED", "RECOVERY", "CAPABILITY_GAP"},
        )
        db.close()

    def test_all_critical_seam_symbols_exist(self):
        required = {
            "scripts/nova/nova_telegram_worker.py": ("process_message", "_deliver_response", "_set_owner_turn_governance_context"),
            "scripts/nova/context_authority.py": ("resolve_context", "render_context_block"),
            "scripts/nova/operator_v1.py": ("status_read", "get_authoritative_mission_snapshot", "_execute_one", "completion_guard", "_snapshot_from_mission_row", "_verify_mission_success"),
            "scripts/nova/approved_mcp_registry.py": ("discover_approved_mcp", "evaluate_mcp_tool_policy"),
            "scripts/nova/nexus_mcp_status.py": ("list_mcp_tools", "call_mcp_tool"),
            "scripts/nexus_agent_platform/bridge/oracle_hermes_cli.py": ("run_oracle_hermes",),
            "services/nexus_mcp/server.py": ("_assign_research", "_exact_research_case"),
            "scripts/research/research_case_engine.py": ("continue_case_once", "record_synthesis", "evaluate_case_readiness"),
            "scripts/nexus_agent_platform/durable_jobs.py": ("dispatch_once", "claim"),
            "scripts/nexus_agent_platform/job_worker_once.py": ("main",),
        }
        for relative, symbols in required.items():
            source = (ROOT / relative).read_text()
            for symbol in symbols:
                with self.subTest(file=relative, symbol=symbol):
                    self.assertIn(symbol, source)

    def test_release_validator_checks_missing_local_dependencies(self):
        path = ROOT / "scripts/ops/validate_nova_release.py"
        self.assertTrue(path.is_file())
        source = path.read_text()
        self.assertIn("INCOMPLETE_LOCAL_DEPENDENCY_RELEASE_CAN_PROMOTE=NO", source)
        self.assertIn("ast.ImportFrom", source)
        self.assertIn("ast.Import", source)

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            entry = root / "scripts/nova/entry.py"
            entry.parent.mkdir(parents=True)
            entry.write_text("from nova.required_research import contract\n")
            cmd = [sys.executable, str(path), str(root), "--entrypoint", "scripts/nova/entry.py"]
            missing = subprocess.run(cmd, capture_output=True, text=True, check=False)
            self.assertNotEqual(missing.returncode, 0)
            self.assertIn("INCOMPLETE_LOCAL_DEPENDENCY_RELEASE_CAN_PROMOTE=NO", missing.stdout)

            package = root / "scripts/nova"
            (package / "__init__.py").write_text("")
            (package / "required_research.py").write_text("contract = True\n")
            manifest_paths = [package / "__init__.py", package / "entry.py", package / "required_research.py"]
            manifest = []
            for file_path in manifest_paths:
                digest = hashlib.sha256(file_path.read_bytes()).hexdigest()
                manifest.append(f"{digest}  ./{file_path.relative_to(root)}")
            (root / "RELEASE_MANIFEST.sha256").write_text("\n".join(manifest) + "\n")
            complete = subprocess.run(cmd, capture_output=True, text=True, check=False)
            self.assertEqual(complete.returncode, 0, complete.stdout + complete.stderr)
            self.assertIn("LOCAL_IMPORT_CLOSURE=PASS", complete.stdout)
            self.assertIn("RELEASE_IMPORT=PASS", complete.stdout)

    def test_release_validator_bounds_each_isolated_module_import(self):
        validator = ROOT / "scripts/ops/validate_nova_release.py"
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            entry = root / "scripts/nova/sleepy.py"
            entry.parent.mkdir(parents=True)
            entry.write_text("import time\ntime.sleep(30)\n")
            cmd = [sys.executable, str(validator), str(root), "--import-only",
                   "--no-entrypoint-import", "--entrypoint", "scripts/nova/sleepy.py",
                   "--module", "nova.sleepy", "--module-timeout", "2"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15, check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("RESULT=TIMEOUT MODULE=nova.sleepy PROCESS_TERMINATED=YES", result.stdout)

    def test_release_validator_blocks_import_time_network_and_reports_escape(self):
        validator = ROOT / "scripts/ops/validate_nova_release.py"
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            entry = root / "scripts/nova/probe.py"
            entry.parent.mkdir(parents=True)
            entry.write_text("import socket\nsocket.socket().connect(('127.0.0.1', 9))\n")
            cmd = [sys.executable, str(validator), str(root), "--import-only",
                   "--no-entrypoint-import", "--entrypoint", "scripts/nova/probe.py",
                   "--module", "nova.probe"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15, check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("SIDE_EFFECTS_OBSERVED=['socket.connect']", result.stdout)

    def test_required_schema_error_timeout_and_idempotency_contracts_are_recorded(self):
        doc = (ROOT / "docs/architecture/NEXUS_RUNTIME_CONTRACTS.md").read_text()
        for seam in "ABCDEFGHIJKL":
            with self.subTest(seam=seam):
                row = next((line for line in doc.splitlines() if line.startswith(f"| ({seam})")), "")
                self.assertTrue(row, f"missing contract row {seam}")
                self.assertEqual(row.count("|"), 8, f"contract row {seam} must have all seven columns")
                cells = [cell.strip() for cell in row.strip("|").split("|")]
                self.assertEqual(len(cells), 7)
                self.assertTrue(all(cells[1:]), f"contract row {seam} has an empty interface field")
        for requirement in ("schema", "required field", "structured error", "timeout", "idempotency", "read/write"):
            with self.subTest(requirement=requirement):
                self.assertIn(requirement, doc)

    def test_delivery_contract_covers_all_supported_path_classes(self):
        doc = (ROOT / "docs/architecture/NEXUS_RUNTIME_CONTRACTS.md").read_text()
        section = doc.split("## Delivery and fast paths", 1)[1].split("## Release certification gate", 1)[0]
        for route in ("greeting", "conversational reply", "current state", "last mission",
                      "Operator result", "boundary", "error"):
            with self.subTest(route=route):
                self.assertIn(route, section)
        self.assertIn("RENDERED_REPLY_WITHOUT_VALID_DELIVERY_CONTEXT_CANNOT_REACH_PRODUCTION=YES", section)


if __name__ == "__main__":
    unittest.main()
