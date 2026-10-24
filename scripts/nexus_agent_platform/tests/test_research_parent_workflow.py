from __future__ import annotations

from copy import deepcopy

import pytest

from nexus_agent_platform import research_parent_workflow as workflow


def _completed_fixture(*, domain="BUSINESS", source_type="WEB_PAGE", result="positive", prior=None):
    state = workflow.new_parent(objective_id="root-fixture", original_objective="Fixture research objective",
        source_url="https://example.test", source_type=source_type, subject_domain=domain)
    calls = []

    def execute(action, current):
        calls.append(action)
        if action == "SOURCE_UNDERSTANDING":
            return {"status": "COMPLETED", "subject": "fixture subject", "summary": "source understood",
                    "category": domain, "evidence": [{"ref": "source-1"}],
                    "transcript_acquired": source_type.startswith("YOUTUBE"),
                    "notebooklm_useful": source_type.startswith("YOUTUBE")}
        if action == "KNOWLEDGE_RECONCILIATION":
            return {"status": "COMPLETED", "relationship": "RELATED" if prior else "NEW",
                    "prior_summary": prior, "prior_conclusion": "prior conclusion" if prior else None,
                    "prior_unresolved_questions": ["prior question"] if prior else [],
                    "material_changes": ["current evidence differs"] if prior else []}
        if action == "ADVISOR_REVIEW":
            return {"status": "COMPLETED", "subject_interpretation": "fixture subject",
                    "possible_category": domain, "questions": [{"question": "What is the material risk?"}],
                    "claims_to_verify": ["risk claim"], "suggested_tests": ["bounded test"],
                    "likely_destination": "TRADING" if domain == "TRADING" else "SYSTEMS"}
        if action == "QUESTION_GENERATION":
            return {"status": "COMPLETED", "questions": [{"question": "What is the fastest safe test?"}]}
        if action == "FOLLOWUP_RESEARCH":
            return {"status": "COMPLETED", "answers": [{"question": "What is the material risk?",
                    "status": "ANSWERED", "answer": "risk documented", "evidence_refs": ["e-2"],
                    "confidence": "MEDIUM", "needs_followup": False}],
                    "evidence": [{"ref": "e-2"}], "test_result": result if domain == "TRADING" else None}
        if action == "NEEDLE_REVIEW":
            return {"status": "READY_FOR_DEPARTMENT", "missing_questions": []}
        if action == "SYNTHESIS":
            return {"status": "COMPLETED", "recommended_actions": ["run the bounded next step"],
                    "action_owner": "NOVA", "next_department": "TRADING" if domain == "TRADING" else "SYSTEMS",
                    "unresolved_uncertainty": []}
        if action == "CATEGORY_LIBRARY_ROUTING":
            return {"status": "COMPLETED", "category": domain, "library_destination": "research-library"}
        if action == "HANDOFF":
            return {"status": "COMPLETED", "handoff_id": "handoff-fixture",
                    "next_department": "TRADING" if domain == "TRADING" else "SYSTEMS",
                    "package": {"objective": current["original_objective"], "evidence": current["evidence"]}}
        raise AssertionError(action)

    return state, calls, execute


def test_website_mission_runs_to_actionable_handoff():
    state, calls, execute = _completed_fixture()
    result = workflow.run_parent_workflow(state, execute=execute)
    expected = list(workflow.WORKFLOW)
    expected.insert(expected.index("NEEDLE_REVIEW"), "FOLLOWUP_RESEARCH")
    assert calls == expected
    assert result["status"] == "COMPLETE"
    assert result["handoff"]["handoff_id"] == "handoff-fixture"
    assert result["action_owner"] == "NOVA" or result["next_department"]


def test_youtube_transcript_and_notebooklm_are_source_capabilities_not_completion():
    state, calls, execute = _completed_fixture(source_type="YOUTUBE_VIDEO")
    result = workflow.run_parent_workflow(state, execute=execute)
    assert result["source_understanding"]["transcript_acquired"] is True
    assert result["source_understanding"]["notebooklm_useful"] is True
    assert calls.index("ADVISOR_REVIEW") < calls.index("NEEDLE_REVIEW") < calls.index("HANDOFF")
    assert result["status"] == "COMPLETE"


@pytest.mark.parametrize("test_result", ["PASS", "NEGATIVE"])
def test_trading_positive_and_negative_tests_both_handoff(test_result):
    state, _, execute = _completed_fixture(domain="TRADING", source_type="TRADING_STRATEGY", result=test_result)
    result = workflow.run_parent_workflow(state, execute=execute)
    assert result["test_results"] == [test_result]
    assert result["next_department"] == "TRADING"
    assert result["handoff"]["handoff_id"]


def test_existing_knowledge_is_loaded_compared_and_does_not_stop():
    state, _, execute = _completed_fixture(prior={"summary": "old summary", "conclusion": "old conclusion"})
    result = workflow.run_parent_workflow(state, execute=execute)
    reconciliation = result["knowledge_reconciliation"]
    assert reconciliation["relationship"] == "RELATED"
    assert reconciliation["prior_summary"] == {"summary": "old summary", "conclusion": "old conclusion"}
    assert reconciliation["material_changes"]
    assert result["handoff"]["handoff_id"]


@pytest.mark.parametrize("child_status", ["NO_EXECUTION", "SCOPE_UNRESOLVED", "RESEARCH_MORE",
                                           "SOURCE_INSUFFICIENT", "ADVISOR_UNAVAILABLE"])
def test_child_quality_or_execution_issue_advances_to_next_parent_action(child_status):
    state = workflow.new_parent(objective_id="root-active", original_objective="Continue objective")
    state["source_understanding"] = {"summary": "partial"}
    state["knowledge_reconciliation"] = {"relationship": "NEW"}
    result = workflow.run_parent_workflow(state,
        execute=lambda action, _: {"status": child_status, "reason": "fixture blocker"})
    assert result["status"] == "IN_PROGRESS"
    assert result["next_action"] in {"NEEDLE_REVIEW", "SYNTHESIS"}
    assert result["continuation_required"] is True
    assert result["terminal_condition"] is None


def test_needle_exhaustion_synthesizes_with_uncertainty_instead_of_orphaning():
    state = workflow.new_parent(objective_id="root-needle", original_objective="Needle fixture")
    state.update({"source_understanding": {"summary": "understood"}, "knowledge_reconciliation": {"relationship": "NEW"},
        "advisor_findings": {"reviewed": True}, "questions": [{"question": "gap", "status": "UNVERIFIED", "needs_followup": True}],
        "stage_status": {"QUESTION_GENERATION": "COMPLETED"},
        "followup_attempts": 2, "needle": {"status": "RESEARCH_MORE", "missing_questions": ["gap"]},
        "needle_repair_attempts": 1})
    assert workflow.select_next_action(state) == "SYNTHESIS"


def test_synthesis_after_needle_research_more_advances_to_routing_then_handoff():
    state = workflow.new_parent(objective_id="root-needle-synthesis", original_objective="Complete fixture")
    state.update({"source_understanding": {"summary": "understood"},
        "knowledge_reconciliation": {"relationship": "NEW"},
        "advisor_findings": {"reviewed": True},
        "stage_status": {"QUESTION_GENERATION": "COMPLETED"},
        "needle": {"status": "RESEARCH_MORE", "missing_questions": []},
        "followup_attempts": 2, "needle_repair_attempts": 1,
        "synthesis": {"recommended_actions": ["review evidence"], "action_owner": "NOVA"}})
    assert workflow.select_next_action(state) == "CATEGORY_LIBRARY_ROUTING"
    state["category_library_routing"] = {"status": "COMPLETED", "category": "UNKNOWN"}
    assert workflow.select_next_action(state) == "HANDOFF"


def test_synthesis_and_handoff_require_actionable_owner_or_department():
    state = workflow.new_parent(objective_id="root-contract", original_objective="Contract fixture")
    with pytest.raises(ValueError, match="RESEARCH_SYNTHESIS_ACTION_AND_OWNER_REQUIRED"):
        workflow.apply_action_result(state, "SYNTHESIS", {"status": "COMPLETED"})


class _MemoryStore:
    def __init__(self):
        self.jobs = {}

    def enqueue(self, department, job_type, **kwargs):
        key = kwargs["idempotency_key"]
        return self.jobs.setdefault(key, {"department": department, "job_type": job_type, **kwargs})


def test_orphan_recovery_is_idempotent_and_preserves_root_active():
    state = workflow.new_parent(objective_id="root-orphan", original_objective="Orphan fixture")
    state["source_understanding"] = {"summary": "understood"}
    state["knowledge_reconciliation"] = {"relationship": "NEW"}
    store = _MemoryStore()
    first = workflow.recover_orphaned_objective(store, state=state, parent_job_id="parent-job",
        payload_ref="work-1", child_states=[])
    second = workflow.recover_orphaned_objective(store, state=state, parent_job_id="parent-job",
        payload_ref="work-1", child_states=[])
    assert first == second
    assert len(store.jobs) == 1
    assert first["governance_context"]["root_objective_status"] == "IN_PROGRESS"
    assert workflow.recover_orphaned_objective(store, state=state, parent_job_id="parent-job",
        payload_ref="work-1", child_states=["RUNNING"]) is None


def test_legitimate_terminal_conditions_are_the_only_non_handoff_stop_states():
    state = workflow.new_parent(objective_id="root-terminal", original_objective="Terminal fixture")
    state["terminal_condition"] = "RAY_ACTION_REQUIRED"
    assert workflow.select_next_action(state) is None
    invalid = deepcopy(state)
    invalid["terminal_condition"] = "NEGATIVE_FINDING"
    assert workflow.select_next_action(invalid) == "SOURCE_UNDERSTANDING"


def test_source_understanding_uses_governed_http_fallback_when_crawl4ai_missing(monkeypatch):
    from nexus_agent_platform import evidence_ingestion, research_parent_adapters

    monkeypatch.setattr(evidence_ingestion, "ingest_url", lambda *a, **k: {
        "status": "DEPENDENCY_UNAVAILABLE", "error": "crawl4ai unavailable: No module named crawl4ai"})
    monkeypatch.setattr(research_parent_adapters, "_fallback_public_page", lambda url, item: {
        "status_code": 200, "url": url, "title": "Test subject", "text": "A public website fixture."})
    result = research_parent_adapters.execute_action("SOURCE_UNDERSTANDING",
        {"original_objective": "Research test subject", "source_url": "https://example.test",
         "source_type": "WEB_PAGE", "subject_domain": "UNKNOWN"},
        {"work_id": "isolated-work"})
    assert result["status"] == "COMPLETED"
    assert result["source_adapter"] == "BOUNDED_PUBLIC_HTTP_FALLBACK"
    assert result["summary"] == "A public website fixture."


def test_exhausted_source_methods_become_findings_and_parent_advances():
    state = workflow.new_parent(objective_id="root-source-failure", original_objective="Inspect public source",
        source_url="https://example.test")
    failure = {"status": "CONTINUATION_REQUIRED", "reason": "SOURCE_ACQUIRE_FAILED",
        "error": "governed public fetch unavailable", "source_url": state["source_url"]}
    workflow.apply_action_result(state, "SOURCE_UNDERSTANDING", failure)
    assert state["continuation_required"] is False
    assert state["terminal_condition"] is None
    assert state["source_understanding"]["status"] == "SOURCE_INCOMPLETE"
    assert state["method_failures"][0]["reason"] == failure["reason"]
    assert workflow.select_next_action(state) == "KNOWLEDGE_RECONCILIATION"


def test_advisor_unavailable_is_data_and_question_generation_continues():
    state = workflow.new_parent(objective_id="root-advisor-unavailable",
        original_objective="Research the supplied company", source_url="https://example.test")
    state["source_understanding"] = {"status": "COMPLETED", "subject": "Example company",
        "summary": "Evidence summary."}
    state["knowledge_reconciliation"] = {"relationship": "NEW", "lookup": "PASS"}
    workflow.apply_action_result(state, "ADVISOR_REVIEW", {
        "status": "ADVISOR_UNAVAILABLE", "reason": "No web search provider configured."})
    assert state["advisor_findings"]["status"] == "ADVISOR_UNAVAILABLE"
    assert state["continuation_required"] is False
    assert state["terminal_condition"] is None
    assert workflow.select_next_action(state) == "QUESTION_GENERATION"


def test_followup_provider_unavailable_marks_questions_unverified_and_continues():
    state = workflow.new_parent(objective_id="root-followup-unavailable",
        original_objective="Research the supplied company")
    state["source_understanding"] = {"summary": "Initial evidence."}
    state["knowledge_reconciliation"] = {"relationship": "NEW"}
    state["advisor_findings"] = {"status": "ADVISOR_UNAVAILABLE"}
    state["stage_status"]["QUESTION_GENERATION"] = "COMPLETED"
    state["questions"] = [{"question": "Are costs verified?", "status": "OPEN", "needs_followup": True}]
    workflow.apply_action_result(state, "FOLLOWUP_RESEARCH", {
        "status": "CONTINUATION_REQUIRED", "error": "No public search provider configured."})
    assert state["questions"][0]["status"] == "UNVERIFIED"
    assert state["questions"][0]["needs_followup"] is False
    assert state["followup_attempts"] == 1
    assert state["terminal_condition"] is None
    assert workflow.select_next_action(state) == "NEEDLE_REVIEW"


def test_source_acquisition_policy_denial_uses_bounded_alternative(monkeypatch):
    from nexus_agent_platform import evidence_ingestion, research_parent_adapters

    monkeypatch.setattr(evidence_ingestion, "ingest_url", lambda *a, **k: {
        "status": "POLICY_DENIED", "error": "GovernanceDenied: POLICY_DENIED"})
    monkeypatch.setattr(research_parent_adapters, "_fallback_public_page", lambda url, item: {
        "status_code": 200, "url": url, "title": "Public source", "text": "Independent page evidence."})
    result = research_parent_adapters.execute_action("SOURCE_UNDERSTANDING",
        {"original_objective": "Understand this subject", "source_url": "https://example.test"},
        {"work_id": "isolated-policy-denial"})
    assert result["status"] == "COMPLETED"
    assert result["source_adapter"] == "BOUNDED_PUBLIC_HTTP_FALLBACK"
    assert result["source_method_failure"]["status"] == "POLICY_DENIED"
