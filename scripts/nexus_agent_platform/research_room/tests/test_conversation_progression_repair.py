from __future__ import annotations

from nexus_agent_platform.research_room import production_controller as controller
from nexus_agent_platform.research_room.participants import Needle, ResearchLead


IDS = {"case_id": "rcase_fixture_progression", "objective_id": "objective-fixture",
       "project_id": "project-fixture", "job_id": "job_fixture_progression"}


def _primary_review():
    return {
        "review_id": "review-primary", "role": "PRIMARY_RESEARCH_ADVISOR",
        "case_id": IDS["case_id"], "objective_id": IDS["objective_id"],
        "project_id": IDS["project_id"], "job_id": IDS["job_id"],
        "analysis": ("For q_b04da13aa3b1464f, the material claim is that this case defines "
            "migration certification scope; this is established by the supplied objective. "
            "No test results or migration-specific evidence are supplied. The historical "
            "provider failures are reported context, not independent proof."),
        "risks": ["Receipts may show steps ran without proving final state.",
                  "Rollback and partial failure may be untested.",
                  "The migration type and risk tier are unspecified."],
        "evidence_notes": ["No external source was requested; treat supplied case context as context only."],
        "estimated_cost_usd": 0.0,
    }


def _case_with_review():
    return {
        "case_id": IDS["case_id"], "primary_question": IDS["project_id"],
        "status": "PROMISING", "open_questions": [
            {"question_id": "q_b04da13aa3b1464f", "question": "Which claims materially affect the requested decision, and what evidence supports them?"},
            {"question_id": "q_b42074818a3af0a5", "question": "What important costs, risks, constraints, and alternatives remain uncertain?"},
        ], "answered_questions": [], "sources": [], "findings": [], "syntheses": [],
        "research_room_advisor_reviews": [_primary_review()],
        "research_room_controller": {"lineage": IDS, "turn_count": 7,
            "state": "RUNNING", "last_event": "FACT_CHECKER",
            "advisor_attempts": [{"attempt_id": "attempt-primary", "job_id": "advisor-job-primary",
                "status": "COMPLETED", "role": "PRIMARY_ADVISOR",
                "response_reference": "review-primary"}],
            "room_state": {"case_id": IDS["case_id"], "original_request": "Certify operator migrations.",
                "metadata": {"shadow_mode": False, "production_lineage": IDS,
                             "execution_mode": "DEEP_RESEARCH_MODE"},
                "questions": [
                    {"production_question_id": "q_b04da13aa3b1464f", "question": "Which claims materially affect the requested decision, and what evidence supports them?", "status": "OPEN"},
                    {"production_question_id": "q_b42074818a3af0a5", "question": "What important costs, risks, constraints, and alternatives remain uncertain?", "status": "OPEN"},
                ], "findings": [], "advisor_comments": [], "source_report": {"status": "SOURCE_NOT_REQUESTED", "text": ""},
                "next_participant": "NEEDLE", "turn_count": 7}},
    }


def test_existing_advisor_review_projects_question_two_and_three(monkeypatch):
    from research import research_case_engine as engine
    case = _case_with_review()
    calls = []
    monkeypatch.setattr(engine, "get_case", lambda _cid: case)

    def answer_question(case_id, question_id, **kwargs):
        assert case_id == IDS["case_id"]
        calls.append((question_id, kwargs))
        q = next(row for row in case["open_questions"] if row["question_id"] == question_id)
        case["open_questions"].remove(q)
        case["answered_questions"].append({**q, "answer_status": "ANSWERED", **kwargs})
        return {"ok": True, "case": case}

    monkeypatch.setattr(engine, "answer_question", answer_question)
    result = controller._project_primary_review_answers(IDS, case)
    assert result == {"q_b04da13aa3b1464f", "q_b42074818a3af0a5"}
    assert {qid for qid, _ in calls} == result
    by_id = {qid: args for qid, args in calls}
    assert "material claims" in by_id["q_b04da13aa3b1464f"]["answer"].casefold()
    assert "costs:" in by_id["q_b42074818a3af0a5"]["answer"].casefold()
    assert by_id["q_b04da13aa3b1464f"]["evidence_ids"] == []
    assert by_id["q_b42074818a3af0a5"]["evidence_ids"] == []
    assert all(args["limitations"] for args in by_id.values())


def test_completed_review_prevents_blind_primary_requeue_and_preserves_stage(monkeypatch):
    case = _case_with_review()
    monkeypatch.setattr(controller, "_load", lambda _identity: case)
    monkeypatch.setattr(controller, "_project_primary_review_answers", lambda _identity, _case: set())
    observed = {}
    class Router:
        def __init__(self, **_kwargs): pass
    class Graph:
        def __init__(self, **_kwargs): pass
        def turn(self, state, *, production_case_binding):
            observed["state"] = state
            observed["binding"] = production_case_binding
            updated = dict(state)
            updated["turn_count"] = 8
            updated["next_participant"] = "FINAL_STRATEGIST"
            updated["updated_at"] = "fixture"
            updated["final_synthesis"] = {"research_conclusion": "Use evidence gates and preserve uncertainty.",
                "unresolved_uncertainty": [], "recommended_actions": ["define scope"]}
            return updated
    from nexus_agent_platform.research_room import advisor_router, room_graph
    monkeypatch.setattr(advisor_router, "AdvisorRouter", Router)
    monkeypatch.setattr(room_graph, "RoomGraph", Graph)
    persisted = []
    monkeypatch.setattr(controller, "_persist_room_projection", lambda identity, state:
        persisted.append(state) or {"saved": True})
    monkeypatch.setattr(controller, "_save_controller", lambda *a, **kw: {"saved": True})
    result = controller.continue_case(**IDS, instruction="Continue this same case")
    assert result["status"] == "advanced"
    assert observed["state"]["next_participant"] == "NEEDLE"
    assert observed["binding"] == IDS
    assert result["new_case_created"] is False
    assert len(case["research_room_controller"]["advisor_attempts"]) == 1
    assert persisted[-1]["handoff"] is None
    assert persisted[-1]["next_participant"] == "DONE"


def test_controller_projection_preserves_attempt_and_source_receipts(monkeypatch):
    from research import research_case_engine as engine
    case = {"case_id": IDS["case_id"], "open_questions": [], "sources": [],
        "answered_questions": [], "findings": [], "syntheses": [],
        "research_room_controller": {"advisor_attempts": [{"attempt_id": "a1", "status": "COMPLETED"}],
            "source_attempts": [{"attempt_id": "s1", "result": "NO_RESULT"}], "custom_receipt": "keep"}}
    monkeypatch.setattr(engine, "get_case", lambda _cid: case)
    monkeypatch.setattr(controller, "_save_controller", lambda _cid, **kw: case.update(
        research_room_controller=kw["controller"]) or {"saved": True})
    controller._persist_room_projection(IDS, {"questions": [], "findings": [],
        "source_report": {"status": "SOURCE_NOT_REQUESTED"}})
    saved = case["research_room_controller"]
    assert saved["advisor_attempts"][0]["attempt_id"] == "a1"
    assert saved["source_attempts"][0]["attempt_id"] == "s1"
    assert saved["custom_receipt"] == "keep"


def test_needle_completes_with_no_new_question_when_answers_cover_open_questions():
    state = {"questions": [{"question": "q1", "status": "ANSWERED"}],
        "metadata": {}, "unresolved_items": []}
    result = Needle().review(state)
    assert result["coverage_status"] == "NO_MATERIAL_GAPS"
    assert result["new_questions"] == []
    assert result["missing_questions"] == []
    assert state["next_participant"] == "FINAL_STRATEGIST"


def test_needle_returns_material_candidate_for_same_case_advisor_followup():
    state = {"questions": [{"question": "q1", "status": "ANSWERED"}],
        "source_report": {"status": "SOURCE_NOT_REQUESTED"}, "knowledge_reconciliation": {"relationship": "known"},
        "advisor_comments": [{}], "questions_generated": True, "fact_check_completed": True,
        "metadata": {"needle_candidate_questions": [
            "Which migration risk tier applies to the actual operator change?"]}, "unresolved_items": []}
    result = Needle().review(state)
    assert len(result["new_questions"]) == 1
    assert state["questions"][-1]["origin"] == "NEEDLE"
    assert state["questions"][-1]["status"] == "OPEN"
    assert state["next_participant"] == "ADVISOR_FOLLOWUP"
    assert ResearchLead().select_next_participant(state) == "FOLLOWUP_RESEARCH"


def test_source_free_synthesis_persists_review_provenance_without_claiming_citations(monkeypatch):
    from research import research_case_engine as engine
    case = _case_with_review()
    case["answered_questions"] = [
        {"question_id": "q_b04da13aa3b1464f", "answer": "claims classified from context"},
        {"question_id": "q_b42074818a3af0a5", "answer": "costs and risks retained"},
    ]
    saved = []
    monkeypatch.setattr(engine, "get_case", lambda _cid: case)
    def save(_case, event, **updates):
        saved.append((event, updates))
        case.update(updates)
        return case
    monkeypatch.setattr(engine, "_save", save)
    monkeypatch.setattr(controller, "_save_controller", lambda *a, **kw: {"saved": True})
    state = {"source_report": {"status": "SOURCE_NOT_REQUESTED"}, "questions": [], "findings": [],
        "final_synthesis": {"research_conclusion": "Certification needs risk-based gates.",
            "unresolved_uncertainty": [{"question": "Migration-specific scope is unknown."}],
            "recommended_actions": ["Collect migration scope"]}}
    controller._enrich_conversational_synthesis(state, case, IDS)
    controller._persist_room_projection(IDS, state)
    rows = case.get("syntheses") or []
    assert len(rows) == 1
    assert rows[0]["source_ids"] == []
    assert rows[0]["source_backed"] is False
    assert rows[0]["advisor_review_ids"] == ["review-primary"]
    assert rows[0]["next_best_action"] == "Collect migration scope"


def test_results_projection_is_bounded(monkeypatch):
    case = {"case_id": IDS["case_id"], "status": "PROMISING", "open_questions": [],
        "sources": [{"source_id": str(i), "extracted_evidence": "x" * 30000} for i in range(100)],
        "findings": [], "answered_questions": [], "syntheses": [], "research_room_controller": {}}
    monkeypatch.setattr(controller, "_load", lambda _identity: case)
    result = controller.results(**IDS)
    blob = __import__("json").dumps(result)
    assert len(blob.encode()) <= controller.RESULTS_READ_MAX_BYTES
    assert result["read_payload_truncated"] is True


def test_production_conversation_synthesis_is_not_an_execution_handoff():
    state = {"status": "SYNTHESIZING", "final_synthesis": {"research_conclusion": "Done"},
        "execution_strategy": {"execution_mode": "DEEP_RESEARCH_MODE"}, "handoff": None,
        "questions": [], "source_report": {"status": "SOURCE_NOT_REQUESTED"},
        "knowledge_reconciliation": {"relationship": "known"}, "advisor_comments": [{}], "questions_generated": True,
        "fact_check_completed": True, "needle_result": {"missing_questions": []}}
    assert ResearchLead().select_next_participant(state) == "DONE"

