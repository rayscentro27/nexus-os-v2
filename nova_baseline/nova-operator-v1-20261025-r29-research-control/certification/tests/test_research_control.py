from __future__ import annotations

import ast
import hashlib
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


COMPONENT = Path(__file__).resolve().parents[2]
RUNTIME = COMPONENT / "runtime"
sys.path.insert(0, str(RUNTIME / "scripts"))

from nova.nova_research_control import (  # noqa: E402
    deterministic_correlation, parse_handoff, progress_for, render_handoff,
    user_facing_job_status,
)
from nova.research_intent import route_research_only_request  # noqa: E402
from nova.semantic_orchestration import resolve_owner_request  # noqa: E402
from nova.nexus_mcp_status import assign_research_only, call_exact_job_status  # noqa: E402


class NovaResearchControlTests(unittest.TestCase):
    def test_01_conversational_research_request_recognized(self):
        route = resolve_owner_request("Can you verify this claim: Path.is_file returns false when missing?")
        self.assertEqual(route["intent"], "RESEARCH_ONLY_REQUEST")
        self.assertEqual(route["research_only_request"]["research_intent"], "RESEARCH_ONLY")

    def test_02_non_research_conversation_unaffected(self):
        route = resolve_owner_request("Can you explain how rainbows form?")
        self.assertNotEqual(route["intent"], "RESEARCH_ONLY_REQUEST")

    def test_02b_expected_conversational_phrases_route_or_clarify(self):
        for phrase in ("Research this.", "Look into this.", "Check the official documentation."):
            with self.subTest(phrase=phrase):
                self.assertEqual(resolve_owner_request(phrase)["intent"], "RESEARCH_ONLY_REQUEST")
        self.assertEqual(resolve_owner_request("Find out whether this claim is true: X is true.")["intent"],
                         "RESEARCH_ONLY_REQUEST")

    def test_02c_existing_worker_diagnostic_keeps_operational_route(self):
        self.assertEqual(resolve_owner_request("Check this Research worker for status")["intent"],
                         "NEXUS_OPERATIONAL_DIAGNOSTIC_AND_REPAIR")

    def test_02d_existing_full_research_mission_semantics_remain(self):
        self.assertEqual(resolve_owner_request("Research mission: determine whether the claim is true")["intent"],
                         "RESEARCH_MISSION")

    def test_03_deictic_request_asks_clarification(self):
        request = route_research_only_request("Research this for me.")
        self.assertEqual(request["status"], "CLARIFICATION_REQUIRED")
        self.assertTrue(request["clarification"])

    def test_03b_generic_business_referent_asks_clarification(self):
        self.assertEqual(route_research_only_request("Look into this business opportunity.")["status"],
                         "CLARIFICATION_REQUIRED")

    def test_03c_reply_context_is_bounded_question_context(self):
        request = route_research_only_request("Research this.",
            quoted_context="According to the official docs, what does pathlib.Path.is_file return for a missing path?")
        self.assertEqual(request["status"], "READY")
        self.assertIn("pathlib.Path.is_file", request["question"])

    def test_04_submission_uses_existing_mcp_action_and_research_only(self):
        accepted = {"status": "queued", "durable_job_id": "job_a", "objective_id": "obj_a", "work_id": "work_a"}
        with patch("nova.nexus_mcp_status.call_mcp_tool", return_value=({"data": accepted}, 49)) as call:
            payload, count = assign_research_only(objective="Verify Path behavior", question="What does it return when absent?",
                                                  correlation_id="nova-research-only-abc")
        self.assertEqual(payload["durable_job_id"], "job_a")
        self.assertEqual(count, 49)
        args = call.call_args.args
        self.assertEqual(args[0], "nexus_assign_research")
        self.assertEqual(args[1]["requested_intent"], "RESEARCH_ONLY")
        self.assertEqual(args[1]["parent_request_id"], "nova-research-only-abc")

    def test_05_exact_identifiers_are_capturable(self):
        assignment = {"objective_id": "obj", "project_id": "proj", "work_id": "work", "durable_job_id": "job"}
        identity = {"objective_id": assignment["objective_id"], "project_id": assignment["project_id"],
                    "work_item_id": assignment["work_id"], "job_id": assignment["durable_job_id"],
                    "correlation_id": "corr"}
        self.assertEqual(set(identity), {"objective_id", "project_id", "work_item_id", "job_id", "correlation_id"})

    def test_06_same_telegram_update_has_deterministic_idempotency(self):
        a = deterministic_correlation("chat", 42, "Verify this claim")
        b = deterministic_correlation("chat", 42, "  verify THIS claim ")
        self.assertEqual(a, b)

    def test_07_new_update_has_distinct_idempotency_identity(self):
        self.assertNotEqual(deterministic_correlation("chat", 42, "Question"),
                            deterministic_correlation("chat", 43, "Question"))

    def test_08_assignment_api_replay_is_idempotent(self):
        calls = {}
        def fake_call(tool, arguments):
            key = (tool, arguments["parent_request_id"], arguments["objective"], arguments["question"])
            calls[key] = calls.get(key, 0) + 1
            return ({"data": {"status": "queued" if calls[key] == 1 else "idempotent_existing",
                               "durable_job_id": "job_once"}}, 49)
        with patch("nova.nexus_mcp_status.call_mcp_tool", side_effect=fake_call):
            first, _ = assign_research_only(objective="A sufficiently long objective", question="A sufficiently long question",
                                             correlation_id="stable-corr")
            replay, _ = assign_research_only(objective="A sufficiently long objective", question="A sufficiently long question",
                                              correlation_id="stable-corr")
        self.assertEqual(first["durable_job_id"], replay["durable_job_id"])
        self.assertEqual(sum(calls.values()), 2)  # same MCP idempotency key, one logical assignment

    def test_09_exact_job_status_uses_one_id_and_limit_one(self):
        job = {"job_id": "job_exact", "state": "RUNNING"}
        with patch("nova.nexus_mcp_status.call_mcp_tool", return_value=({"data": {"jobs": [job]}}, 49)) as call:
            result, _ = call_exact_job_status("job_exact")
        self.assertEqual(result["job"]["job_id"], "job_exact")
        self.assertEqual(call.call_args.args[0], "nexus_get_durable_jobs")
        self.assertEqual(call.call_args.args[1], {"job_id": "job_exact", "limit": 1})

    def test_10_status_poll_is_bounded_per_user_turn(self):
        from nova import nova_research_control as control
        self.assertEqual(control.MAX_POLLS_PER_INTERACTION, 1)
        self.assertEqual(control.STATUS_POLL_INTERVAL_SECONDS, 10)
        from datetime import datetime, timezone, timedelta
        now = datetime.now(timezone.utc)
        self.assertFalse(control.status_poll_allowed((now - timedelta(seconds=2)).isoformat(), now=now))
        self.assertTrue(control.status_poll_allowed((now - timedelta(seconds=11)).isoformat(), now=now))
        self.assertFalse(control.status_poll_allowed("not-a-timestamp", now=now))

    def test_11_queued_running_and_terminal_progress_mapping(self):
        self.assertEqual(progress_for("QUEUED"), "Research is queued.")
        self.assertEqual(progress_for("RUNNING"), "I’m researching that now.")
        self.assertIn("temporary", progress_for("FAILED_RETRYABLE"))

    def test_12_completed_handoff_is_parsed(self):
        handoff = {"schema": "nexus.research-only-handoff.v1", "status": "COMPLETED",
                   "summary": "Path.is_file() returns False when the path does not exist.",
                   "evidence_refs": [{"title": "Python pathlib documentation"}], "unanswered_questions": []}
        parsed = parse_handoff({"job": {}, "research_work_item": {"result": handoff}})
        self.assertEqual(parsed["schema"], "nexus.research-only-handoff.v1")
        self.assertEqual(parsed["evidence_refs"][0]["title"], "Python pathlib documentation")

    def test_13_answer_rendered_conversationally(self):
        handoff = {"schema": "nexus.research-only-handoff.v1", "status": "COMPLETED",
                   "summary": "Path.is_file() returns False when the path does not exist.",
                   "evidence_refs": [{"title": "Python pathlib documentation"}], "unanswered_questions": []}
        rendered = render_handoff(handoff)
        self.assertIn("returns False when the path does not exist", rendered)
        self.assertNotIn('"schema"', rendered)

    def test_14_evidence_and_unanswered_questions_preserved(self):
        handoff = {"schema": "nexus.research-only-handoff.v1", "summary": "A bounded answer.",
                   "evidence_refs": ["ref1", "ref2"], "unanswered_questions": ["Q1"]}
        parsed = parse_handoff({"job": {"result_summary": handoff}})
        rendered = render_handoff(parsed)
        self.assertIn("ref1", rendered)
        self.assertIn("Q1", rendered)

    def test_15_source_insufficient_is_uncertainty_not_failure(self):
        self.assertIn("didn’t provide enough evidence", progress_for("COMPLETED", "SOURCE_INSUFFICIENT"))
        self.assertIn("didn’t provide enough evidence", render_handoff({"status": "SOURCE_INSUFFICIENT"}))

    def test_16_retryable_failure_never_creates_replacement(self):
        text = progress_for("FAILED_RETRYABLE")
        self.assertIn("haven’t created a replacement", text)

    def test_17_status_response_uses_compact_handoff(self):
        handoff = {"schema": "nexus.research-only-handoff.v1", "status": "COMPLETED",
                   "summary": "The answer is supported.", "evidence_refs": [], "unanswered_questions": []}
        result = {"status": "ok", "job": {"state": "COMPLETED"},
                  "research_work_item": {"requested_intent": "RESEARCH_ONLY", "result": handoff}}
        self.assertEqual(user_facing_job_status(result), "The answer is supported.")

    def test_18_no_advisor_needle_or_parent_creation_in_control_module(self):
        source = (RUNTIME / "scripts/nova/nova_research_control.py").read_text().casefold()
        self.assertNotIn("nexus_assign_advisor", source)
        self.assertNotIn("nexus_assign_needle", source)
        self.assertNotIn("nexus_continue_research", source)

    def test_19_no_direct_supabase_write_in_control_path(self):
        for name in ("nova_research_control.py", "research_intent.py", "nexus_mcp_status.py"):
            source = (RUNTIME / "scripts/nova" / name).read_text().casefold()
            self.assertNotIn("supabase.create_client", source)
            self.assertNotIn("postgrest", source)

    def test_20_no_full_transcript_storage_in_new_control(self):
        source = (RUNTIME / "scripts/nova/nova_telegram_worker.py").read_text()
        self.assertIn('"original_message": question', source)
        self.assertIn('"transcript_persisted": False', source)

    def test_21_r60_runtime_not_copied_or_modified(self):
        self.assertFalse((RUNTIME / "scripts/nexus_agent_platform/research_only_execution.py").exists())

    def test_22_existing_non_research_router_contract_remains(self):
        self.assertEqual(resolve_owner_request("What services are available?")["intent"], "CAPABILITY_QUERY")

    def test_23_full_handoff_limit_enforced(self):
        handoff = {"schema": "nexus.research-only-handoff.v1", "summary": "x" * 9000}
        self.assertIsNone(parse_handoff({"job": {"result_summary": handoff}}))

    def test_24_handoff_summary_limit_enforced(self):
        handoff = {"schema": "nexus.research-only-handoff.v1", "summary": "x" * 1201}
        self.assertIsNone(parse_handoff({"job": {"result_summary": handoff}}))

    def test_25_source_body_and_transcript_are_not_rendered(self):
        handoff = {"schema": "nexus.research-only-handoff.v1", "summary": "Answer.",
                   "source_body": "private body", "transcript": "long conversation"}
        parsed = parse_handoff({"job": {"result_summary": handoff}})
        self.assertNotIn("source_body", parsed)
        self.assertNotIn("transcript", parsed)

    def test_26_ambiguous_simple_trigger_is_not_submitted(self):
        request = route_research_only_request("Look into this.")
        self.assertEqual(request["status"], "CLARIFICATION_REQUIRED")

    def test_27_status_maps_source_insufficient_from_job_result(self):
        result = {"status": "ok", "job": {"state": "COMPLETED", "result_status": "SOURCE_INSUFFICIENT"},
                  "research_work_item": {"requested_intent": "RESEARCH_ONLY"}}
        self.assertIn("enough evidence", user_facing_job_status(result))

    def test_28_no_automatic_poll_loop(self):
        source = (RUNTIME / "scripts/nova/nova_research_control.py").read_text()
        self.assertNotIn("while True", source)
        self.assertNotIn("sleep(", source)

    def test_29_controls_keep_exact_correlation_and_identity_bounded(self):
        corr = deterministic_correlation("chat", 8, "question")
        self.assertTrue(corr.startswith("nova-research-only-"))
        self.assertLessEqual(len(corr), 64)

    def test_30_exact_status_helper_never_uses_broad_default_query(self):
        source = (RUNTIME / "scripts/nova/nexus_mcp_status.py").read_text()
        tree = ast.parse(source)
        fn = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "call_exact_job_status")
        code = ast.get_source_segment(source, fn)
        self.assertIn('"job_id": target', code)
        self.assertIn('"limit": 1', code)

    def test_31_telegram_worker_imports_from_r29_runtime(self):
        import nova.nova_telegram_worker as worker
        self.assertTrue(Path(worker.__file__).resolve().is_relative_to(RUNTIME.resolve()))

    def test_32_exact_r60_handoff_shape_is_consumed(self):
        actual_shape = {"status": "COMPLETED", "research_result": {
            "schema_version": "nexus.research-only-handoff.v1",
            "summary": "Path.is_file() returns False when the path does not exist.",
            "key_findings": ["Path.is_file() returns False when the path does not exist."],
            "evidence_references": ["https://docs.python.org/3/library/pathlib.html"],
            "unanswered_questions": [], "result_status": "RESEARCH_COMPLETE",
            "source_body": "must be ignored", "transcript": "must be ignored"}}
        parsed = parse_handoff({"status": "ok", "job": {"result_summary": actual_shape},
                                "research_work_item": {"requested_intent": "RESEARCH_ONLY"}})
        self.assertEqual(parsed["schema"], "nexus.research-only-handoff.v1")
        self.assertIn("returns False", parsed["summary"])
        self.assertEqual(parsed["evidence_refs"][0], "https://docs.python.org/3/library/pathlib.html")
        self.assertNotIn("source_body", parsed)
        self.assertNotIn("transcript", parsed)

    def test_33_restart_recovery_replays_same_research_correlation(self):
        source = (RUNTIME / "scripts/nova/nova_telegram_worker.py").read_text()
        self.assertIn('"RESEARCH_ONLY_SUBMISSION_PENDING"', source)
        self.assertIn('"RESEARCH_ONLY_SUBMISSION_UNCONFIRMED"', source)
        self.assertIn('"RESEARCH_ONLY_QUEUED"', source)
        self.assertIn('"text": ("Research this: "', source)
        self.assertIn("deterministic_correlation(chat_id, update_id, question)", source)


if __name__ == "__main__":
    unittest.main()
