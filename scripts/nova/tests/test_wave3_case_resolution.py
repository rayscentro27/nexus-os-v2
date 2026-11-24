"""Phase 5 Wave 3 decision-only Research case resolution contracts."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from nova.operator_shadow import decide_research_case_resolution, plan_research_continuation
from nova.operator_cutover_switch import read_route_mode, write_route_mode
from nova.nova_telegram_worker import (_legacy_research_assignment_owns_intake,
                                       _wave3_case_resolution_answer,
                                       _wave3_case_resolution_route,
                                       _wave3_operator_mission_for_case,
                                       _wave3_research_continuation_decision,
                                       _wave3_explicit_research_lineage,
                                       _wave3_research_controller_catalog)


CASE_A = "rcase_80fb1ea338bfaa1b41"
CASE_B = "rcase_010203040506070809"
CASE_LINEAGE = {"case_id": CASE_A, "objective_id": "obj-1", "project_id": "project-1",
                "durable_job_id": "job-1", "read_only": True, "no_mutation": True}
CASE_SNAPSHOT = {"status": "ok", "case_id": CASE_A, "read_only": True, "no_mutation": True,
                 "case_state": {"status": "RECOMMENDATION_READY", "open_questions": [],
                                "sources": [{}, {}, {}, {}], "syntheses": [{}, {}]}}


class ResearchCaseResolutionContracts(unittest.TestCase):
    def test_research_mission_resume_uses_exact_case_not_stale_chat_entities(self):
        class OperatorStub:
            def __init__(self):
                self.lookups = []

            def mission_for_entity(self, owner_id, entity_ids):
                self.lookups.append((owner_id, entity_ids))
                return None

        operator = OperatorStub()
        lineage = {**CASE_LINEAGE, "note_id": "reports/nova_internal/old_note.md",
                   "file_id": "reports/nova_internal/old_note.md"}
        result = _wave3_operator_mission_for_case(operator, "ray", lineage)
        self.assertIsNone(result)
        self.assertEqual(operator.lookups, [("ray", [CASE_A])])

    def test_canonical_operator_catalog_excludes_legacy_research_writers(self):
        contracts = {
            "nexus_get_research_controller_status": ("READ", ["case_id", "objective_id", "project_id", "durable_job_id"]),
            "nexus_get_research_controller_open_questions": ("READ", ["case_id", "objective_id", "project_id", "durable_job_id"]),
            "nexus_get_research_controller_results": ("READ", ["case_id", "objective_id", "project_id", "durable_job_id"]),
            "nexus_research_controller_continue": ("WRITE", ["case_id", "objective_id", "project_id", "durable_job_id", "instruction"]),
            "nexus_research_controller_advisor_request": ("WRITE", ["case_id", "objective_id", "project_id", "durable_job_id", "question"]),
        }
        catalog = [{"capability_id": "mcp:nexus_mcp_remote:nexus_continue_research_case",
                    "tool_name": "nexus_continue_research_case", "source_id": "nexus_mcp_remote",
                    "authorized": True, "read_write_class": "WRITE", "input_schema": {"properties": {}}}]
        for name, (action_class, required) in contracts.items():
            catalog.append({"capability_id": "mcp:nexus_mcp_remote:" + name, "tool_name": name,
                "source_id": "nexus_mcp_remote", "authorized": True,
                "read_write_class": action_class, "input_schema": {"properties": {key: {} for key in required}}})
        selected = _wave3_research_controller_catalog(catalog)
        self.assertEqual({row["tool_name"] for row in selected}, set(contracts))
        self.assertNotIn("nexus_continue_research_case", {row["tool_name"] for row in selected})
        catalog[-1]["input_schema"]["properties"].pop("question")
        with self.assertRaisesRegex(RuntimeError, "WAVE3_RESEARCH_ROOM_CONTROLLER_CONTRACT_MISSING"):
            _wave3_research_controller_catalog(catalog)

    def test_r14_legacy_intake_switch_bypasses_generic_operator_gate(self):
        research = {"department": "RESEARCH", "intent": "RESEARCH_MISSION"}
        with patch("nova.operator_cutover_switch.read_route_mode", return_value="LEGACY_LIVE"):
            self.assertTrue(_legacy_research_assignment_owns_intake(research))
            self.assertFalse(_legacy_research_assignment_owns_intake(
                research, continuation_canonical=True))
            self.assertFalse(_legacy_research_assignment_owns_intake(
                {"department": "SYSTEMS", "intent": "DEPARTMENT_ASSIGNMENT"}))
        with patch("nova.operator_cutover_switch.read_route_mode", return_value="CANONICAL"):
            self.assertFalse(_legacy_research_assignment_owns_intake(research))

    def test_resolution_precedence_and_same_case_continuation(self):
        explicit = decide_research_case_resolution(
            f"Which existing Research case is this? {CASE_A}",
            lineage={"case_id": CASE_B})
        self.assertEqual(explicit["TARGET_ENTITY_ID"], CASE_A)
        self.assertEqual(explicit["RESOLUTION_SOURCE"], "EXPLICIT_CASE_ID")

        immediate = decide_research_case_resolution(
            "Which Research case are we continuing?",
            previous_turn={"assistant_text": f"The existing case is {CASE_A}."},
            active_mission={"case_id": CASE_B}, lineage={"case_id": CASE_B})
        self.assertEqual(immediate["TARGET_ENTITY_ID"], CASE_A)
        self.assertEqual(immediate["RESOLUTION_SOURCE"], "IMMEDIATE_PREVIOUS_TURN")
        self.assertEqual(immediate["DECISION"], "READ_CASE")
        self.assertFalse(immediate["CREATE_NEW_ENTITY"])
        self.assertEqual(immediate["SIDE_EFFECTS"], 0)

    def test_active_conversation_and_durable_precedence(self):
        active = decide_research_case_resolution(
            "Which Research case is active?",
            active_mission={"entity_lineage": [{"entity_type": "RESEARCH_CASE", "entity_id": CASE_A}]},
            lineage={"case_id": CASE_B})
        self.assertEqual((active["TARGET_ENTITY_ID"], active["RESOLUTION_SOURCE"]),
                         (CASE_A, "ACTIVE_MISSION"))

        current_conversation = decide_research_case_resolution(
            "Which Research case is this?", conversation_cases=[CASE_A], lineage={"case_id": CASE_B})
        self.assertEqual((current_conversation["TARGET_ENTITY_ID"], current_conversation["RESOLUTION_SOURCE"]),
                         (CASE_A, "CURRENT_CONVERSATION"))

        durable = decide_research_case_resolution("Continue that Research case", lineage={"case_id": CASE_B})
        self.assertEqual((durable["TARGET_ENTITY_ID"], durable["RESOLUTION_SOURCE"]),
                         (CASE_B, "DURABLE_LINEAGE"))
        self.assertEqual(durable["DECISION"], "CONTINUE_EXISTING_CASE")

    def test_explicit_new_case_is_not_confused_with_continuation(self):
        result = decide_research_case_resolution("Start new research about battery recycling")
        self.assertEqual(result["DECISION"], "CREATE_NEW_CASE")
        self.assertTrue(result["CREATE_NEW_ENTITY"])
        self.assertIsNone(result["TARGET_ENTITY_ID"])
        self.assertFalse(result["EXECUTION_PERFORMED"])

    def test_missing_exact_case_is_unresolved_not_a_new_case(self):
        result = decide_research_case_resolution("Continue that Research case")
        self.assertEqual(result["DECISION"], "UNRESOLVED")
        self.assertFalse(result["CREATE_NEW_ENTITY"])
        self.assertEqual(result["SIDE_EFFECTS"], 0)

    def test_wave3_switch_defaults_legacy_and_rollback_is_config_only(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "mode.json"
            for route in ("R12.research_assignment", "R13.research_intent",
                          "R13.case_resolution", "R13.continue_vs_new",
                          "R14.research_assignment", "R15.research_continue"):
                self.assertEqual(read_route_mode(route, path), "LEGACY_LIVE")
            write_route_mode(path, "R13.case_resolution", "CANONICAL")
            write_route_mode(path, "R13.continue_vs_new", "CANONICAL")
            write_route_mode(path, "R15.research_continue", "CANONICAL")
            self.assertEqual(read_route_mode("R13.case_resolution", path), "CANONICAL")
            self.assertEqual(read_route_mode("R13.continue_vs_new", path), "CANONICAL")
            self.assertEqual(read_route_mode("R15.research_continue", path), "CANONICAL")
            write_route_mode(path, "R13.case_resolution", "LEGACY_LIVE")
            self.assertEqual(read_route_mode("R13.case_resolution", path), "LEGACY_LIVE")

    def test_canonical_read_resolution_is_side_effect_free_and_rejects_mutation(self):
        context = {"previous_user_text": "", "previous_assistant_text": f"Case {CASE_A} is active."}
        with patch("nova.operator_cutover_switch.read_route_mode", return_value="CANONICAL"), \
             patch("nova.operator_v1.recent_research_case_lineage", return_value=CASE_LINEAGE), \
             patch("nova.nova_telegram_worker._log"):
            mode, decision, _, canonical = _wave3_case_resolution_route(
                "Which Research case are we continuing?", {}, context, owner_id="ray")
        self.assertEqual(mode, "CANONICAL")
        self.assertTrue(canonical)
        self.assertEqual(decision["TARGET_ENTITY_ID"], CASE_A)
        self.assertEqual(decision["SIDE_EFFECTS"], 0)
        response = _wave3_case_resolution_answer(decision, CASE_SNAPSHOT)
        self.assertIn(CASE_A, response)
        self.assertIn("RECOMMENDATION_READY", response)
        self.assertIn("no objective, project, job, or case was created", response)

        with patch("nova.operator_cutover_switch.read_route_mode", return_value="CANONICAL"), \
             patch("nova.nova_telegram_worker._log"):
            mode, decision, _, canonical = _wave3_case_resolution_route(
                "Continue that Research case", {"case_id": CASE_A}, {})
        self.assertEqual(decision["DECISION"], "CONTINUE_EXISTING_CASE")
        self.assertFalse(canonical)
        self.assertIsNone(_wave3_case_resolution_answer(decision, CASE_SNAPSHOT))

    def test_durable_lineage_is_final_fallback_and_ambiguity_fails_closed(self):
        with patch("nova.operator_cutover_switch.read_route_mode", return_value="CANONICAL"), \
             patch("nova.operator_v1.recent_research_case_lineage", return_value=CASE_LINEAGE), \
             patch("nova.nova_telegram_worker._log"):
            mode, decision, _, canonical = _wave3_case_resolution_route(
                "Which existing Research case are we continuing?", {}, {}, owner_id="ray")
        self.assertEqual((mode, decision["TARGET_ENTITY_ID"], decision["RESOLUTION_SOURCE"]),
                         ("CANONICAL", CASE_A, "DURABLE_LINEAGE"))
        self.assertTrue(canonical)

        with patch("nova.operator_cutover_switch.read_route_mode", return_value="CANONICAL"), \
             patch("nova.operator_v1.recent_research_case_lineage", return_value={
                 "case_id": None, "ambiguous_case_ids": [CASE_A, CASE_B],
                 "resolution_status": "AMBIGUOUS"}), \
             patch("nova.nova_telegram_worker._log"):
            mode, decision, _, canonical = _wave3_case_resolution_route(
                "Which existing Research case are we continuing?", {}, {}, owner_id="ray")
        self.assertEqual(decision["RESOLUTION_SOURCE"], "AMBIGUOUS_DURABLE_RESEARCH_LINEAGE")
        self.assertFalse(canonical)

    def test_research_continuation_shadow_matrix_and_final_state_precedence(self):
        base = {"case_id": CASE_A, "objective_id": "obj-1", "project_id": "project-1",
                "durable_job_id": "job-1"}
        read = "mcp:nexus_mcp_remote:nexus_get_research_case"
        continue_case = "mcp:nexus_mcp_remote:nexus_research_controller_continue"
        advisor = "mcp:nexus_mcp_remote:nexus_research_controller_advisor_request"
        continue_research = "mcp:nexus_mcp_remote:nexus_continue_research"
        synthesis = "mcp:nexus_mcp_remote:nexus_record_research_synthesis"
        recommendation = "mcp:nexus_mcp_remote:nexus_record_research_recommendation"
        inventory = {read, continue_case, advisor, continue_research, synthesis, recommendation}

        # A open question, B worker failure, C missing receipt/source present,
        # D alternate source, E outside review, F incomplete synthesis,
        # G recommendation ready, H already complete.
        fixtures = [
            ({"open_questions": [{"question_id": "q1"}]}, {}, "CONTINUE_SAME_CASE_THROUGH_RESEARCH_ROOM", continue_case),
            ({"open_questions": []}, {"worker_failure": True}, "RECOVER_SAME_CASE_THROUGH_RESEARCH_ROOM", continue_case),
            ({"open_questions": []}, {"receipt_missing_source_exists": True}, "VERIFY_SOURCE_POSTCONDITION", read),
            ({"open_questions": [{"question_id": "q2"}]}, {}, "CONTINUE_SAME_CASE_THROUGH_RESEARCH_ROOM", continue_case),
            ({"open_questions": [{"question_id": "q3"}]}, {"outside_review_requested": True}, "REQUEST_SAME_CASE_CHALLENGER_REVIEW", advisor),
            ({"open_questions": [], "synthesis_complete": False}, {}, "COMPLETE_SAME_CASE_SYNTHESIS", synthesis),
            ({"status": "RECOMMENDATION_READY", "open_questions": [], "recommendation": "PARK"}, {}, "VERIFY_FINAL_STATE", read),
            ({"status": "COMPLETE", "open_questions": [], "recommendation": "PARK"}, {}, "VERIFY_FINAL_STATE", read),
        ]
        for state, kwargs, expected_action, expected_capability in fixtures:
            decision = plan_research_continuation(**base, case_state=state,
                approved_capability_ids=inventory, **kwargs)
            with self.subTest(action=expected_action):
                self.assertEqual(decision["TARGET_ENTITY_ID"], CASE_A)
                self.assertEqual(decision["ACTION_CLASS"], expected_action)
                self.assertEqual(decision["SELECTED_CAPABILITY_IDS"], [expected_capability])
                self.assertFalse(decision["CREATE_NEW_ENTITY"])
                self.assertFalse(decision["BLOCKER"])
                self.assertEqual(decision["SIDE_EFFECTS"], 0)
                self.assertFalse(decision["UNKNOWN_CAPABILITY_IDS"])
                self.assertTrue(decision["SUCCESS_CONDITION"])

        # I ambiguous language must keep the exact lineage; J explicit ID wins.
        ambiguous = decide_research_case_resolution("Continue that research", lineage={"case_id": CASE_A})
        explicit = decide_research_case_resolution(f"Check this Research case {CASE_A}", lineage={"case_id": CASE_B})
        self.assertEqual(ambiguous["TARGET_ENTITY_ID"], CASE_A)
        self.assertEqual(explicit["TARGET_ENTITY_ID"], CASE_A)

    def test_final_case_overrides_historical_worker_failure(self):
        decision = plan_research_continuation(
            case_id=CASE_A, objective_id="obj-1", project_id="project-1", durable_job_id="job-1",
            case_state={"status": "RECOMMENDATION_READY", "open_questions": [],
                        "recommendation": "PARK", "historical_worker_failure": True},
            approved_capability_ids={"mcp:nexus_mcp_remote:nexus_get_research_case"},
            worker_failure=True,
        )
        self.assertEqual(decision["ACTION_CLASS"], "VERIFY_FINAL_STATE")
        self.assertTrue(decision["MISSION_COMPLETE"])
        self.assertFalse(decision["BLOCKER"])

    def test_premature_blocker_requires_all_recovery_paths_exhausted(self):
        base = {"case_id": CASE_A, "objective_id": "obj-1", "project_id": "project-1",
                "durable_job_id": "job-1", "case_state":{"open_questions":[{"question_id":"q1"}]},
                "approved_capability_ids":set()}
        premature = plan_research_continuation(**base)
        self.assertFalse(premature["BLOCKER"])
        evidence = {key: True for key in (
            "direct_capability_checked", "alternate_capability_checked", "adapter_reroute_checked",
            "schema_lineage_repair_checked", "capability_acquisition_checked",
            "postcondition_recovery_checked", "same_case_resume_checked", "alternatives_exhausted")}
        final = plan_research_continuation(**base, boundary_evidence=evidence)
        self.assertTrue(final["BLOCKER"])
        self.assertEqual(final["ACTION_CLASS"], "TRUE_BOUNDARY_CANDIDATE")

    def test_canonical_continuation_route_is_read_only_and_operator_owned(self):
        modes = {"R13.continue_vs_new": "CANONICAL", "R15.research_continue": "CANONICAL"}
        catalog = [{"capability_id": cap, "source_id": "nexus_mcp_remote", "authorized": True}
                   for cap in (
                       "mcp:nexus_mcp_remote:nexus_get_research_case",
                       "mcp:nexus_mcp_remote:nexus_research_controller_continue",
                       "mcp:nexus_mcp_remote:nexus_get_research_controller_status",
                       "mcp:nexus_mcp_remote:nexus_get_research_controller_open_questions",
                       "mcp:nexus_mcp_remote:nexus_get_research_controller_results",
                       "mcp:nexus_mcp_remote:nexus_research_controller_advisor_request",
                       "mcp:nexus_mcp_remote:nexus_continue_research",
                       "mcp:nexus_mcp_remote:nexus_get_research_execution_trace",
                       "mcp:nexus_mcp_remote:nexus_record_research_synthesis",
                       "mcp:nexus_mcp_remote:nexus_record_research_recommendation")]
        snapshot = {"status": "ok", **CASE_LINEAGE, "read_only": True, "no_mutation": True,
                    "case_state": {"status": "MORE_RESEARCH_REQUIRED",
                                   "open_questions": [{"question_id": "q1"}]}}
        resolution = {"DECISION": "CONTINUE_EXISTING_CASE", "TARGET_ENTITY_ID": CASE_A,
                      "CREATE_NEW_ENTITY": False, "RESEARCH_LINEAGE": CASE_LINEAGE}
        with patch("nova.operator_cutover_switch.read_route_mode", side_effect=lambda route: modes[route]), \
             patch("nova.operator_v1.discover_catalog", return_value=catalog), \
             patch("nova.nexus_mcp_status.call_mcp_tool", return_value=(snapshot, 44)) as call, \
             patch("nova.nova_telegram_worker._log"):
            mode, decision, route_modes, canonical = _wave3_research_continuation_decision(
                "Continue that Research case", resolution, owner_id="ray")
        self.assertEqual(mode, "CANONICAL")
        self.assertTrue(canonical)
        self.assertEqual(route_modes["R15.research_continue"], "CANONICAL")
        self.assertEqual(decision["DECISION_OWNER"], "NOVA_OPERATOR")
        self.assertEqual(decision["ACTION_CLASS"], "CONTINUE_SAME_CASE_THROUGH_RESEARCH_ROOM")
        self.assertEqual(decision["TARGET_ENTITY_ID"], CASE_A)
        self.assertEqual(decision["SELECTED_CAPABILITY_IDS"],
                         ["mcp:nexus_mcp_remote:nexus_research_controller_continue"])
        self.assertFalse(decision["CREATE_NEW_ENTITY"])
        self.assertEqual(decision["SIDE_EFFECTS"], 0)
        self.assertFalse(decision["EXECUTION_PERFORMED"])
        call.assert_called_once_with("nexus_get_research_case", {
            "case_id": CASE_A, "objective_id": "obj-1", "project_id": "project-1", "durable_job_id": "job-1"})

    def test_explicit_full_lineage_is_accepted_only_after_exact_mcp_readback(self):
        objective = "nova_research_16a764a4c75b65d81e46"
        project = "nova_research_work_16a764a4c75b65d81e46"
        job = "job_d27d3093c0e248a3a1481a5a45730475"
        text = f"Continue case CASE_ID={CASE_A} OBJECTIVE_ID={objective} PROJECT_ID={project} JOB_ID={job}"
        self.assertEqual(_wave3_explicit_research_lineage(text), {
            "case_id": CASE_A, "objective_id": objective, "project_id": project,
            "durable_job_id": job})
        self.assertIsNone(_wave3_explicit_research_lineage(f"CASE_ID={CASE_A} OBJECTIVE_ID={objective}"))
        catalog = []
        contracts = {
            "nexus_get_research_controller_status": ("READ", ["case_id", "objective_id", "project_id", "durable_job_id"]),
            "nexus_get_research_controller_open_questions": ("READ", ["case_id", "objective_id", "project_id", "durable_job_id"]),
            "nexus_get_research_controller_results": ("READ", ["case_id", "objective_id", "project_id", "durable_job_id"]),
            "nexus_research_controller_continue": ("WRITE", ["case_id", "objective_id", "project_id", "durable_job_id", "instruction"]),
            "nexus_research_controller_advisor_request": ("WRITE", ["case_id", "objective_id", "project_id", "durable_job_id", "question"]),
        }
        for name, (action_class, required) in contracts.items():
            catalog.append({"capability_id": "mcp:nexus_mcp_remote:" + name, "tool_name": name,
                "source_id": "nexus_mcp_remote", "authorized": True,
                "read_write_class": action_class, "input_schema": {"properties": {key: {} for key in required}}})
        snapshot = {"status": "ok", "read_only": True, "no_mutation": True,
            "case_id": CASE_A, "objective_id": objective, "project_id": project, "durable_job_id": job,
            "case_state": {"status": "PROMISING", "open_questions": [{"question_id": "q1"}]}}
        resolution = {"DECISION": "CONTINUE_EXISTING_CASE", "TARGET_ENTITY_ID": CASE_A}
        with patch("nova.operator_cutover_switch.read_route_mode", return_value="CANONICAL"), \
             patch("nova.operator_v1.recent_research_case_lineage", return_value=None), \
             patch("nova.operator_v1.discover_catalog", return_value=catalog), \
             patch("nova.nexus_mcp_status.call_mcp_tool", return_value=(snapshot, 49)) as call, \
             patch("nova.nova_telegram_worker._log"):
            mode, decision, _, canonical = _wave3_research_continuation_decision(text, resolution, owner_id="ray")
        self.assertEqual(mode, "CANONICAL")
        self.assertTrue(canonical)
        self.assertEqual(decision["RESEARCH_LINEAGE"], {
            "case_id": CASE_A, "objective_id": objective, "project_id": project, "durable_job_id": job})
        self.assertEqual(decision["SELECTED_CAPABILITY_IDS"],
            ["mcp:nexus_mcp_remote:nexus_research_controller_continue"])
        call.assert_called_once_with("nexus_get_research_case", {
            "case_id": CASE_A, "objective_id": objective, "project_id": project, "durable_job_id": job})

    def test_outside_review_routing_stays_on_same_case_workflow(self):
        base = {"case_id": CASE_A, "objective_id": "obj-1", "project_id": "project-1",
                "durable_job_id": "job-1", "case_state":{"open_questions":[{"question_id":"q1"}]},
                "approved_capability_ids":{
                    "mcp:nexus_mcp_remote:nexus_get_research_case",
                    "mcp:nexus_mcp_remote:nexus_research_controller_continue",
                    "mcp:nexus_mcp_remote:nexus_research_controller_advisor_request"}}
        result = plan_research_continuation(**base, outside_review_requested=True)
        self.assertEqual(result["ACTION_CLASS"], "REQUEST_SAME_CASE_CHALLENGER_REVIEW")
        self.assertEqual(result["TARGET_ENTITY_ID"], CASE_A)
        self.assertEqual(result["SELECTED_CAPABILITY_IDS"],
                         ["mcp:nexus_mcp_remote:nexus_research_controller_advisor_request"])
        self.assertFalse(result["CREATE_NEW_ENTITY"])
        self.assertFalse(result["BLOCKER"])
        self.assertFalse(result["MISSION_COMPLETE"])

    def test_canonical_continuation_fails_closed_without_exact_lineage(self):
        with patch("nova.operator_cutover_switch.read_route_mode", return_value="CANONICAL"), \
             patch("nova.operator_v1.recent_research_case_lineage", return_value=None), \
             patch("nova.nova_telegram_worker._log"):
            mode, decision, _, canonical = _wave3_research_continuation_decision(
                "Continue that Research case",
                {"DECISION": "CONTINUE_EXISTING_CASE", "TARGET_ENTITY_ID": CASE_A}, owner_id="ray")
        self.assertEqual(mode, "CANONICAL")
        self.assertFalse(canonical)
        self.assertEqual(decision["ERROR_CODE"], "EXACT_RESEARCH_LINEAGE_INCOMPLETE")
        self.assertEqual(decision["SIDE_EFFECTS"], 0)

    def test_shadow_continuation_does_not_read_or_execute_research(self):
        modes = {"R13.continue_vs_new": "CANONICAL", "R15.research_continue": "SHADOW"}
        resolution = {"DECISION": "CONTINUE_EXISTING_CASE", "TARGET_ENTITY_ID": CASE_A}
        with patch("nova.operator_cutover_switch.read_route_mode", side_effect=lambda route: modes[route]), \
             patch("nova.nexus_mcp_status.call_mcp_tool") as call, \
             patch("nova.operator_v1.discover_catalog") as discover, \
             patch("nova.nova_telegram_worker._log"):
            mode, decision, _, canonical = _wave3_research_continuation_decision(
                "Continue that Research case", resolution, owner_id="ray")
        self.assertEqual(mode, "SHADOW")
        self.assertFalse(canonical)
        self.assertEqual(decision["DECISION_OWNER"], "SHADOW")
        self.assertEqual(decision["SIDE_EFFECTS"], 0)
        self.assertFalse(decision["EXECUTION_PERFORMED"])
        call.assert_not_called()
        discover.assert_not_called()


if __name__ == "__main__":
    unittest.main()
