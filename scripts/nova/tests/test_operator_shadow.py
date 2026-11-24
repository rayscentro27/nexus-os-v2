"""Offline, side-effect-free Phase 1 Operator shadow contract fixtures."""
from __future__ import annotations

import unittest

from nova.operator_shadow import (
    approved_shadow_capabilities, completion_authorized, decide_shadow_request, decide_wave2_action,
    recovery_class,
)


class OperatorShadowContracts(unittest.TestCase):
    def test_historic_and_entity_first_fixtures(self):
        fixtures = [
            ("continue that same Research case", {"case_id": "case-1"}, "CONTINUE", "case-1", False),
            ("keep working on that same Research case", {"case_id": "case-1"}, "CONTINUE", "case-1", False),
            ("what are you working on right now?", {}, "READ", None, False),
            ("what was the last mission you completed?", {}, "READ", "mission-1", False),
            ("can you summarize that?", {}, "READ", "file-1", False),
            ("delete that same note", {"note_id": "note-1"}, "DELETE", "note-1", False),
            ("retry that job", {"job_id": "job-1"}, "RETRY", "job-1", False),
            ("Create a new Research case about X", {}, "CREATE", None, True),
            ("Make another version", {}, "CREATE_VERSION", "file-1", True),
            ("Update the one you just made", {}, "UPDATE", "file-1", False),
        ]
        for text, ids, action, target, create in fixtures:
            previous = {"entity_ids": {"file_id": "file-1"}} if text in {
                "can you summarize that?", "Make another version", "Update the one you just made"
            } else {}
            if text == "what was the last mission you completed?":
                result = decide_shadow_request(text, completed_mission={"mission_id": "mission-1"})
            else:
                result = decide_shadow_request(text, lineage=ids, previous_turn=previous)
            with self.subTest(text=text):
                self.assertEqual(result["ACTION_CLASS"], action)
                self.assertEqual(result["TARGET_ENTITY_ID"], target)
                self.assertEqual(result["CREATE_NEW_ENTITY"], create)
                self.assertTrue(result["SHADOW_ONLY"])
                self.assertFalse(result["EXECUTION_PERFORMED"])
                self.assertEqual(result["SIDE_EFFECTS"], 0)

    def test_capability_selection_uses_only_snapshot_ids(self):
        inventory = approved_shadow_capabilities()
        inventory.update({
            "nexus_mcp_remote:nexus_research_controller_continue": {
                "server_id": "nexus_mcp_remote", "name": "nexus_research_controller_continue"},
            "nexus_mcp_remote:nexus_research_controller_advisor_request": {
                "server_id": "nexus_mcp_remote", "name": "nexus_research_controller_advisor_request"},
        })
        requests = [
            ("what are you working on right now?", {}, "nova:operator:nexus_get_operator_mission_status"),
            ("continue that Research case", {"case_id": "case-1"}, "mcp:nexus_mcp_remote:nexus_research_controller_continue"),
            ("check Systems status", {}, "mcp:nexus_mcp_remote:nexus_get_system_health"),
            ("read file document-1", {}, "mcp:nexus_mcp_remote:nexus_read_workspace_file"),
        ]
        for text, lineage, expected in requests:
            result = decide_shadow_request(text, lineage=lineage, previous_turn={"entity_ids": {"file_id": "document-1"}}, capabilities=inventory)
            with self.subTest(text=text):
                self.assertEqual(result["SELECTED_CAPABILITY_ID"], expected)
                self.assertFalse(result["UNKNOWN_CAPABILITY_IDS"])
                self.assertIn(expected.split(":")[-1], {row["name"] for row in inventory.values()})
        multi = decide_shadow_request(
            "continue that case and then have Systems verify worker health",
            lineage={"case_id": "case-1"},
            capabilities=inventory,
        )
        self.assertEqual(multi["ACTION_CLASS"], "MULTI_CAPABILITY")
        self.assertEqual(multi["SELECTED_CAPABILITY_ID"], [
            "mcp:nexus_mcp_remote:nexus_research_controller_continue",
            "mcp:nexus_mcp_remote:nexus_get_system_health",
        ])
        self.assertEqual([goal["action_class"] for goal in multi["SUBGOALS"]], ["CONTINUE", "READ_HEALTH"])
        self.assertIsNotNone(multi["SUCCESS_CONDITION"])
        self.assertFalse(multi["UNKNOWN_CAPABILITY_IDS"])

    def test_research_continue_and_review_never_select_legacy_worker(self):
        inventory = approved_shadow_capabilities()
        inventory.update({
            "nexus_mcp_remote:nexus_research_controller_continue": {
                "server_id": "nexus_mcp_remote", "name": "nexus_research_controller_continue"},
            "nexus_mcp_remote:nexus_research_controller_advisor_request": {
                "server_id": "nexus_mcp_remote", "name": "nexus_research_controller_advisor_request"},
        })
        continued = decide_shadow_request("Continue that same Research case", lineage={"case_id": "rcase_abcd1234"}, capabilities=inventory)
        reviewed = decide_shadow_request("Request an outside review for that Research case", lineage={"case_id": "rcase_abcd1234"}, capabilities=inventory)
        self.assertEqual(continued["SELECTED_CAPABILITY_ID"], "mcp:nexus_mcp_remote:nexus_research_controller_continue")
        self.assertEqual(reviewed["SELECTED_CAPABILITY_ID"], "mcp:nexus_mcp_remote:nexus_research_controller_advisor_request")
        self.assertNotIn("nexus_continue_research_case", continued["SELECTED_CAPABILITY_ID"])
        self.assertNotIn("nexus_continue_research_case", reviewed["SELECTED_CAPABILITY_ID"])

    def test_existing_note_update_selects_exact_entity_update_capability(self):
        path = "reports/nova_internal/nova_note_590357529.md"
        result = decide_wave2_action("Update that same note to say passed", lineage={"note_id": path})
        self.assertEqual(result["ROUTE_ID"], "NOTE_UPDATE")
        self.assertEqual(result["ENTITY_TYPE"], "NOTE")
        self.assertEqual(result["ENTITY_ID"], path)
        self.assertFalse(result["CREATE_NEW_ENTITY"])
        self.assertEqual(result["CAPABILITY_ID"], "mcp:nexus_mcp_remote:nexus_update_workspace_artifact")
        self.assertNotEqual(result["ACTION_CLASS"], "CREATE")
        self.assertEqual(result["SIDE_EFFECTS"], 0)

    def test_actionable_success_false_completion_and_recovery(self):
        for text, lineage in (("delete that same note", {"note_id": "n1"}),
                              ("continue that case", {"case_id": "c1"}),
                              ("retry that job", {"job_id": "j1"}),
                              ("create a new Research case", {})):
            result = decide_shadow_request(text, lineage=lineage)
            self.assertIsNotNone(result["SUCCESS_CONDITION"])
        self.assertFalse(completion_authorized(tool_succeeded=True, postcondition_verified=False, receipt_valid=True))
        self.assertFalse(completion_authorized(tool_succeeded=True, postcondition_verified=True, receipt_valid=False))
        self.assertTrue(completion_authorized(tool_succeeded=True, postcondition_verified=True, receipt_valid=True))
        self.assertEqual(recovery_class("tool_failure"), "RETRY_OR_ALTERNATE")
        self.assertEqual(recovery_class("retry_limit"), "ALTERNATE_OR_REPAIR")
        self.assertEqual(recovery_class("capability_gap"), "ACQUIRE_OR_ALTERNATE_CAPABILITY")
        self.assertEqual(recovery_class("worker_failure"), "REPAIR_OR_REROUTE")
        self.assertEqual(recovery_class("missing_receipt"), "VERIFY_POSTCONDITION")
        self.assertEqual(recovery_class("tool_failure", genuine_boundary=True), "WAIT_FOR_APPROVAL_BOUNDARY")


if __name__ == "__main__":
    unittest.main()
