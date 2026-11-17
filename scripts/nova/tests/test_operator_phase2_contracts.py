"""Read-only Phase 2 Operator parity, authority, and switch fixtures."""
from __future__ import annotations

import inspect
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from nova import context_authority, operator_shadow
from nova.operator_cutover_switch import read_mode, read_route_mode, write_mode, write_route_mode


class OperatorPhase2Contracts(unittest.TestCase):
    def test_wave_one_current_and_completed_snapshot_parity(self):
        completed = {"mission_id": "nova_20261019T145014_590357499", "status": "COMPLETE",
                     "success_verified": True, "final_outcome": "verified final outcome"}
        active = {"mission_id": None, "status": "NO_ACTIVE_MISSION"}
        live_current = context_authority.resolve_context(
            "What are you working on right now?", active_mission=active,
            recent_completed_mission=completed, authoritative_mission_snapshot=completed)
        shadow_current = operator_shadow.decide_shadow_request(
            "What are you working on right now?", active_mission=active, completed_mission=completed)
        self.assertEqual(live_current["resolved_referent"]["status"], "NO_ACTIVE_MISSION")
        self.assertEqual(shadow_current["ACTION_CLASS"], "READ")
        self.assertEqual(shadow_current["CURRENT_STATE"], "NO_ACTIVE_MISSION")
        self.assertIsNone(shadow_current["FINAL_STATE"])
        self.assertEqual(shadow_current["DATA_SOURCE"], "AUTHORITATIVE_OPERATOR_SNAPSHOT")
        self.assertEqual(shadow_current["RESULT_SHAPE"], "AUTHORITATIVE_MISSION_SNAPSHOT")

        live_last = context_authority.resolve_context(
            "What was the last mission?", active_mission=active,
            recent_completed_mission=completed, authoritative_mission_snapshot=completed)
        shadow_last = operator_shadow.decide_shadow_request(
            "What was the last mission?", active_mission=active, completed_mission=completed)
        self.assertEqual(live_last["resolved_entity_id"], completed["mission_id"])
        self.assertEqual(shadow_last["TARGET_ENTITY_ID"], completed["mission_id"])
        self.assertEqual(shadow_last["FINAL_STATE"], "COMPLETE")
        self.assertEqual(shadow_last["ERROR_BEHAVIOR"], "NONE")

    def test_context_and_state_composition_and_historical_precedence(self):
        prior = {"assistant_text": "I don't currently have an active mission.", "update_id": 41}
        immediate = context_authority.resolve_context(
            "Summarize that.", previous_turn=prior,
            active_mission={"status": "NO_ACTIVE_MISSION"})
        self.assertEqual(immediate["context_source"], "PREVIOUS_ASSISTANT_TURN")
        shadow_immediate = operator_shadow.decide_shadow_request(
            "Summarize that.", previous_turn=prior,
            active_mission={"status": "NO_ACTIVE_MISSION"})
        self.assertEqual(shadow_immediate["DATA_SOURCE"], "PREVIOUS_ASSISTANT_TURN")

        completed = {"mission_id": "nova_20261019T145014_590357499", "status": "COMPLETE",
                     "success_verified": True, "success_evidence": {"case_status": "RECOMMENDATION_READY"}}
        last = context_authority.resolve_context("What was the last mission?", recent_completed_mission=completed)
        why = context_authority.resolve_context(
            "Why was that complete?", previous_turn={"assistant_text": "Mission complete."},
            authoritative_mission_snapshot=completed)
        self.assertEqual(last["resolved_entity_id"], completed["mission_id"])
        self.assertEqual(why["intent"], "COMPLETION_EXPLANATION")
        shadow_why = operator_shadow.decide_shadow_request(
            "Why was that complete?", previous_turn={"assistant_text": "Mission complete."},
            completed_mission=completed)
        self.assertEqual(shadow_why["TARGET_ENTITY_ID"], completed["mission_id"])
        self.assertEqual(shadow_why["DATA_SOURCE"], "AUTHORITATIVE_OPERATOR_SNAPSHOT")

        current = context_authority.resolve_context(
            "What are you working on right now?", active_mission={"status": "NO_ACTIVE_MISSION"},
            recent_completed_mission={"status": "COMPLETE", "mission_id": "old"})
        self.assertEqual(current["resolved_referent"]["status"], "NO_ACTIVE_MISSION")

    def test_read_error_contracts_are_bounded_and_non_mutating(self):
        from nova import operator_v1
        with patch.object(operator_v1, "_read_only_connect", return_value=None):
            self.assertIsNone(operator_v1.status_read("missing-mission"))
            self.assertIsNone(operator_v1.get_authoritative_mission_snapshot("missing-mission"))
        unavailable = operator_shadow.decide_shadow_request(
            "What are you working on right now?",
            active_mission={"status": "CURRENT_STATE_UNAVAILABLE"})
        self.assertEqual(unavailable["ERROR_BEHAVIOR"], "UNAVAILABLE_SNAPSHOT_NO_FABRICATION")
        malformed = operator_shadow.decide_shadow_request(
            "Continue that case", lineage={"case_id": "bad case id"})
        self.assertEqual(malformed["ACTION_CLASS"], "UNRESOLVED")
        self.assertIsNone(malformed["SELECTED_CAPABILITY_ID"])
        self.assertEqual(malformed["ERROR_BEHAVIOR"], "MALFORMED_ENTITY_ID_NO_EXECUTION")
        read_source = inspect.getsource(operator_v1._read_only_connect)
        self.assertIn("mode=ro", read_source)
        self.assertIn("query_only=ON", read_source)
        self.assertIn("timeout=5", read_source)
        self.assertIn("_read_only_connect()", inspect.getsource(operator_v1.recent_completed_status))
        self.assertIn("_read_only_connect()", inspect.getsource(operator_v1.status_read))

    def test_switch_defaults_shadow_and_immediate_rollback_without_rebuild(self):
        from nova.operator_cutover_switch import DEFAULT_CONFIG
        self.assertEqual(read_mode(DEFAULT_CONFIG), "LEGACY_LIVE")
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "mode.json"
            self.assertEqual(read_mode(path), "LEGACY_LIVE")
            self.assertEqual(write_mode(path, "SHADOW"), "SHADOW")
            self.assertEqual(read_mode(path), "SHADOW")
            self.assertEqual(write_mode(path, "LEGACY_LIVE"), "LEGACY_LIVE")
            self.assertEqual(read_mode(path), "LEGACY_LIVE")
            self.assertEqual(write_mode(path, "CANONICAL"), "CANONICAL")
            self.assertEqual(read_mode(path), "CANONICAL")
            self.assertEqual(write_route_mode(path, "R24.current", "CANONICAL"), "CANONICAL")
            self.assertEqual(write_route_mode(path, "R24.last_completed", "LEGACY_LIVE"), "LEGACY_LIVE")
            self.assertEqual(read_route_mode("R24.current", path), "CANONICAL")
            self.assertEqual(read_route_mode("R24.last_completed", path), "LEGACY_LIVE")
            self.assertEqual(write_route_mode(path, "R15.research_continue", "LEGACY_LIVE"), "LEGACY_LIVE")
            self.assertEqual(read_route_mode("R15.research_continue", path), "LEGACY_LIVE")
            with self.assertRaises(ValueError):
                write_route_mode(path, "R15.unauthorized", "CANONICAL")

    def test_wave2_route_switch_and_read_only_decision_fixtures(self):
        from nova.operator_shadow import decide_wave2_action
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "mode.json"
            for route in ("NOTE_CREATE", "NOTE_READ", "NOTE_UPDATE", "NOTE_DELETE",
                          "FILE_CREATE", "FILE_READ", "FILE_UPDATE", "FILE_DELETE"):
                self.assertEqual(write_route_mode(path, route, "LEGACY_LIVE"), "LEGACY_LIVE")
                self.assertEqual(read_route_mode(route, path), "LEGACY_LIVE")
            self.assertEqual(write_route_mode(path, "NOTE_CREATE", "CANONICAL"), "CANONICAL")
            self.assertEqual(read_route_mode("NOTE_CREATE", path), "CANONICAL")
            self.assertEqual(write_route_mode(path, "R14.research_assignment", "LEGACY_LIVE"), "LEGACY_LIVE")
            with self.assertRaises(ValueError):
                write_route_mode(path, "R14.unauthorized", "CANONICAL")

        create = decide_wave2_action('Create a small internal note that says "Phase 4 live test," verify it exists.')
        self.assertEqual(create["ROUTE_ID"], "NOTE_CREATE")
        self.assertEqual(create["ACTION_CLASS"], "CREATE")
        self.assertEqual(create["ENTITY_TYPE"], "NOTE")
        self.assertTrue(create["CREATE_NEW_ENTITY"])
        self.assertEqual(create["CAPABILITY_ID"], "mcp:nexus_mcp_remote:nexus_write_workspace_artifact")
        self.assertEqual(create["EXECUTION_ADAPTER"], "R08.workspace_file_mcp")
        self.assertEqual(create["SIDE_EFFECTS"], 0)

        lineage = {"note_id": "reports/nova_internal/nova_note_101.md"}
        read = decide_wave2_action("Read that note", lineage=lineage)
        self.assertEqual((read["ROUTE_ID"], read["ENTITY_ID"], read["CREATE_NEW_ENTITY"]),
                         ("NOTE_READ", lineage["note_id"], False))
        self.assertEqual(read["CAPABILITY_ID"], "mcp:nexus_mcp_remote:nexus_read_workspace_file")
        update = decide_wave2_action("Update that same note", lineage=lineage)
        delete = decide_wave2_action("Delete that same note", lineage=lineage)
        self.assertEqual((update["ACTION_CLASS"], update["ENTITY_ID"], update["CREATE_NEW_ENTITY"]),
                         ("UPDATE", lineage["note_id"], False))
        self.assertEqual((delete["ACTION_CLASS"], delete["ENTITY_ID"], delete["CREATE_NEW_ENTITY"]),
                         ("DELETE", lineage["note_id"], False))
        self.assertIsNone(update["ERROR_CODE"])
        self.assertIsNone(delete["ERROR_CODE"])
        self.assertEqual(update["CAPABILITY_ID"], "mcp:nexus_mcp_remote:nexus_update_workspace_artifact")
        self.assertEqual(delete["CAPABILITY_ID"], "mcp:nexus_mcp_remote:nexus_delete_workspace_artifact")

        lifecycle = decide_wave2_action(
            'Create a small internal note that says "start", read it, update that same note to say "done", read it again, then delete it.')
        self.assertEqual(lifecycle["ACTION_CLASS"], "CREATE")
        self.assertEqual(lifecycle["ACTION_SEQUENCE"], ["CREATE", "READ", "UPDATE", "READ", "DELETE"])
        unresolved = decide_wave2_action("Read that note")
        self.assertEqual(unresolved["ERROR_CODE"], "EXACT_ENTITY_REQUIRED")
        self.assertIsNone(unresolved["ENTITY_ID"])

        external = decide_wave2_action("Create a Google Drive note for a customer")
        self.assertIsNone(external)

        from nova.operator_v1 import _extract_entities
        entities = _extract_entities({"path": "reports/nova_internal/nova_note_101.md"})
        self.assertEqual(entities["note_id"], "reports/nova_internal/nova_note_101.md")
        self.assertEqual(entities["file_id"], "reports/nova_internal/nova_note_101.md")

    def test_wave2_worker_route_decision_is_configured_and_side_effect_free(self):
        from nova import nova_telegram_worker as worker
        with patch("nova.operator_cutover_switch.read_route_mode", return_value="CANONICAL"), \
             patch.object(worker, "_log"):
            route, mode, decision, canonical = worker._wave2_action_route(
                'Create a small internal note that says "Phase 4 live test"', {})
        self.assertEqual((route, mode, canonical), ("NOTE_CREATE", "CANONICAL", True))
        self.assertEqual(decision["SIDE_EFFECTS"], 0)

        lineage = {"note_id": "reports/nova_internal/nova_note_101.md"}
        with patch("nova.operator_cutover_switch.read_route_mode", return_value="CANONICAL"), \
             patch.object(worker, "_log"):
            route, mode, decision, canonical = worker._wave2_action_route("Read that note", lineage)
        self.assertEqual((route, mode, canonical), ("NOTE_READ", "CANONICAL", True))
        self.assertEqual(decision["ENTITY_ID"], lineage["note_id"])

        with patch("nova.operator_cutover_switch.read_route_mode", return_value="CANONICAL"), \
             patch.object(worker, "_log"):
            route, mode, decision, canonical = worker._wave2_action_route("Read that note", {})
        self.assertEqual((route, mode, canonical), ("NOTE_READ", "CANONICAL", False))
        self.assertEqual(decision["ERROR_CODE"], "EXACT_ENTITY_REQUIRED")
        self.assertEqual(decision["DECISION_OWNER"], "UNRESOLVED")
        self.assertFalse(decision.get("SIDE_EFFECTS", 0))

    def test_wave2_operator_result_requires_exact_entity_and_verified_readback(self):
        from nova.nova_telegram_worker import _wave2_result_envelope
        decision = {"ROUTE_ID": "NOTE_CREATE", "ACTION_CLASS": "CREATE", "ENTITY_TYPE": "NOTE"}
        result = {"status": "COMPLETE", "mission_id": "opm-wave2-1",
            "entities": {"note_id": "reports/nova_internal/nova_note_101.md"},
            "final_result": {"mission_success_verified": True, "all_postconditions_verified": True,
                "completed_steps": [{"step_id": "opm-wave2-1:1", "capability_id":
                    "mcp:nexus_mcp_remote:nexus_write_workspace_artifact"}],
                "mission_success_evidence": {"status": "PASS", "verified_at": "2026-10-20T00:00:00Z",
                    "result": {"result_data": {"path": "reports/nova_internal/nova_note_101.md", "sha256": "abc123"}}}}}
        normalized = _wave2_result_envelope(decision, result, "receipt-1")
        self.assertTrue(normalized["ACTION_SUCCEEDED"])
        self.assertEqual(normalized["ENTITY_ID"], "reports/nova_internal/nova_note_101.md")
        self.assertEqual(normalized["CURRENT_VERSION_OR_HASH"], "abc123")
        self.assertEqual(normalized["CREATED_BY_STEP"], "opm-wave2-1:1")
        self.assertTrue(normalized["POSTCONDITION_VERIFIED"])
        self.assertEqual(normalized["SOURCE"], "NOVA_OPERATOR")

        incomplete = {**result, "final_result": {"mission_success_verified": True,
            "all_postconditions_verified": True, "mission_success_evidence": {"status": "PASS"}}}
        rejected = _wave2_result_envelope(decision, incomplete)
        self.assertFalse(rejected["ACTION_SUCCEEDED"])
        self.assertFalse(rejected["POSTCONDITION_VERIFIED"])

    def test_wave1_worker_switch_and_bounded_legacy_fallback(self):
        from nova import nova_telegram_worker as worker, operator_v1
        active = {"status": "NO_ACTIVE_MISSION", "mission_id": None}
        current = {"reference_type": "CURRENT_STATE", "active_mission": active,
                   "last_completed_mission": {"mission_id": "old", "status": "COMPLETE"}}
        with patch("nova.operator_cutover_switch.read_route_mode", return_value="CANONICAL"), \
             patch.object(worker, "_log"):
            route, mode, canonical, decision = worker._wave1_route_decision(
                "What are you working on right now?", current)
        self.assertEqual((route, mode, canonical), ("R24.current", "CANONICAL", True))
        self.assertEqual(decision["DECISION_OWNER"], "NOVA_OPERATOR")
        self.assertFalse(decision["SHADOW_ONLY"])
        self.assertEqual(decision["ERROR_BEHAVIOR"], "NONE")
        self.assertEqual(worker._operator_read_only_answer(decision, current),
                         "I don't currently have an active mission.")

        completed = {"mission_id": "nova_20261019T145014_590357499", "status": "COMPLETE",
                     "success_verified": True, "final_entity_state": {"entity_type": "RESEARCH_CASE"}}
        last = {"reference_type": "RECENT_COMPLETED_WORK", "active_mission": active,
                "last_completed_mission": completed}
        with patch("nova.operator_cutover_switch.read_route_mode", return_value="CANONICAL"), \
             patch.object(worker, "_log"):
            route, mode, canonical, decision = worker._wave1_route_decision(
                "What was the last mission you completed?", last)
        self.assertEqual((route, mode, canonical), ("R24.last_completed", "CANONICAL", True))
        self.assertEqual(decision["DECISION_OWNER"], "NOVA_OPERATOR")
        self.assertIn("nova_20261019T145014_590357499", worker._operator_read_only_answer(decision, last))

        with patch("nova.operator_cutover_switch.read_route_mode", return_value="CANONICAL"), \
             patch.object(operator_v1, "decide_read_only_route", side_effect=TimeoutError), \
             patch.object(worker, "_log"):
            route, mode, canonical, decision = worker._wave1_route_decision(
                "What are you working on right now?", current)
        self.assertEqual((route, mode, canonical), ("R24.current", "CANONICAL", False))
        self.assertIsNone(decision)


if __name__ == "__main__":
    unittest.main()
