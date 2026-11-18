from __future__ import annotations

from nexus_agent_platform.research_room import production_controller as controller


IDS = {"case_id": "rcase_fixture12345", "objective_id": "objective-fixture",
       "project_id": "project-fixture", "job_id": "job_fixture12345"}


def test_read_operations_are_exact_lineage_bound_and_read_only(monkeypatch):
    case = {"case_id": IDS["case_id"], "status": "MORE_RESEARCH_REQUIRED",
        "open_questions": [{"question_id": "q1", "question": "citation?"}],
        "sources": [{"source_id": "s1"}], "syntheses": [], "research_room_controller": {"turn_count": 2}}
    monkeypatch.setattr(controller, "_load", lambda identity: case)
    status = controller.status(**IDS)
    questions = controller.open_questions(**IDS)
    results = controller.results(**IDS)
    assert status["read_only"] and status["no_mutation"]
    assert status["case_id"] == IDS["case_id"] and status["evidence_count"] == 1
    assert questions["open_questions"][0]["question_id"] == "q1"
    assert results["results"]["sources"] == case["sources"]


def test_continue_executes_one_room_turn_against_same_production_binding(monkeypatch):
    case = {"case_id": IDS["case_id"], "primary_question": IDS["project_id"],
            "open_questions": [{"question_id": "q1", "question": "citation?"}],
            "sources": [], "findings": [], "research_room_controller": {"lineage": IDS,
                "advisor_attempts": [{"attempt_id": "a1", "status": "COMPLETED"}],
                "room_state": {"case_id": IDS["case_id"], "original_request": "Continue this same case",
                    "metadata": {"shadow_mode": False, "production_lineage": IDS},
                    "questions": [], "findings": [], "advisor_comments": [{"analysis": "initial reasoning"}],
                    "next_participant": "KNOWLEDGE_RECONCILIATION", "turn_count": 0}}}
    monkeypatch.setattr(controller, "_load", lambda identity: case)
    persisted = []
    monkeypatch.setattr(controller, "_save_controller", lambda *args, **kwargs:
        persisted.append((args, kwargs)) or {"saved": True})
    monkeypatch.setattr(controller, "_persist_room_projection", lambda identity, state:
        persisted.append(((identity["case_id"],), {"controller": state})) or {"saved": True})
    from nexus_agent_platform.research_room import room_graph
    from nexus_agent_platform.research_room import advisor_router
    bindings = []
    router_options = []
    class Router:
        def __init__(self, **kwargs): router_options.append(kwargs)
    monkeypatch.setattr(advisor_router, "AdvisorRouter", Router)
    def turn(self, state, *, production_case_binding=None):
        bindings.append(production_case_binding)
        updated = dict(state)
        updated["turn_count"] = 1
        updated["next_participant"] = "SOURCE_ANALYST"
        updated["updated_at"] = "fixture-time"
        return updated
    monkeypatch.setattr(room_graph.RoomGraph, "turn", turn)
    result = controller.continue_case(**IDS, instruction="Continue the same case")
    assert result["status"] == "advanced"
    assert result["case_id"] == IDS["case_id"]
    assert result["new_case_created"] is False
    assert bindings == [IDS]
    assert persisted and persisted[0][0] == (IDS["case_id"],)
    assert persisted[0][1]["controller"]["metadata"]["production_lineage"] == IDS
    assert result["research_room_status_is_not_case_completion"] is True
    assert router_options == [{"free_only": True}]


def test_projection_maps_same_production_source_question_and_finding(monkeypatch):
    from research import research_case_engine as engine
    case = {"case_id": IDS["case_id"], "status": "MORE_RESEARCH_REQUIRED",
        "open_questions": [{"question_id": "q1", "question": "citation?"}],
        "answered_questions": [], "sources": [], "findings": [], "syntheses": []}
    calls = []
    monkeypatch.setattr(engine, "get_case", lambda _case_id: case)
    def add_source(case_id, source):
        assert case_id == IDS["case_id"]
        case["sources"].append(source)
        calls.append(("source", source))
        return {"ok": True}
    def record_finding(case_id, finding):
        assert case_id == IDS["case_id"]
        case["findings"].append(finding)
        calls.append(("finding", finding))
        return {"ok": True}
    def answer_question(case_id, question_id, **kwargs):
        assert (case_id, question_id) == (IDS["case_id"], "q1")
        case["open_questions"] = []
        case["answered_questions"].append({"question_id": question_id, **kwargs})
        calls.append(("answer", kwargs))
        return {"ok": True}
    monkeypatch.setattr(engine, "add_source", add_source)
    monkeypatch.setattr(engine, "record_finding", record_finding)
    monkeypatch.setattr(engine, "answer_question", answer_question)
    monkeypatch.setattr(controller, "_save_controller", lambda *args, **kwargs: {"saved": True})
    state = {"source_report": {"url": "https://example.test/evidence", "text": "Evidence text",
            "title": "Evidence", "source_type": "WEB"},
        "questions": [{"production_question_id": "q1", "question": "citation?", "status": "ANSWERED",
            "answer": "Supported answer", "confidence": 0.8,
            "evidence_refs": [{"url": "https://example.test/evidence"}]}],
        "findings": [{"summary": "Source-backed finding", "source_refs": [{"url": "https://example.test/evidence"}]}]}
    result = controller._persist_room_projection(IDS, state)
    assert result["saved"] is True
    assert [name for name, _ in calls] == ["source", "answer", "finding"]
    assert calls[1][1]["evidence_ids"] == [calls[0][1]["source_id"]]
    assert calls[2][1]["evidence_ids"] == [calls[0][1]["source_id"]]


def test_advisor_request_is_accepted_as_durable_async_work(monkeypatch, tmp_path):
    from .test_repair_contracts import _queued_fakes
    case = {"case_id": IDS["case_id"], "sources": [], "findings": [], "open_questions": [],
            "missing_information": [], "research_room_controller": {}}
    _queued_fakes(monkeypatch, tmp_path, case)
    result = controller.advisor_request(**IDS, question="Review citation support")
    assert result["status"] == "queued"
    assert result["attempt_id"] and result["job_id"]
    assert result["mission_complete"] is False


def test_async_advisor_worker_persists_selected_provider(monkeypatch, tmp_path):
    from .test_repair_contracts import _queued_fakes
    case = {"case_id": IDS["case_id"], "sources": [], "findings": [], "open_questions": [],
            "missing_information": [], "research_room_controller": {}}
    _queued_fakes(monkeypatch, tmp_path, case)
    accepted = controller.advisor_request(**IDS, question="Review citation support", review_role="CHALLENGER")
    from nexus_agent_platform.research_room import advisor_router

    class Router:
        def __init__(self, **kwargs): assert kwargs["free_only"] is True
        def ask(self, *, role, case_context, objective):
            assert case_context["case_id"] == IDS["case_id"]
            assert role == "CHALLENGER_SECOND_OPINION"
            return {"status": "COMPLETED", "provider": "OPENROUTER", "model": "fixture-free",
                "analysis": "The citation question remains unsupported by attached source evidence.",
                "new_questions": [], "risks": ["Citation still requires a primary source."],
                "evidence_notes": ["No source is attached yet."], "estimated_cost_usd": 0.0,
                "cost_class": "FREE_ZERO_PRICED"}

    monkeypatch.setattr(advisor_router, "AdvisorRouter", Router)
    result = controller.execute_queued_advisor({"identity": IDS, "attempt_id": accepted["attempt_id"],
        "review_role": "CHALLENGER", "question": "Review citation support",
        "case_context": {"metadata": {}}}, worker_job_id=accepted["job_id"])
    assert result["advisor_status"] == "COMPLETED"
    assert case["research_room_advisor_reviews"][0]["provider"] == "OPENROUTER"
    assert case["research_room_controller"]["advisor_attempts"][0]["status"] == "COMPLETED"


def test_production_governance_context_uses_same_durable_research_lineage(monkeypatch):
    monkeypatch.delenv("NEXUS_RESEARCH_ROOM_PRODUCTION_CASE", raising=False)
    with controller._production_governance_context(IDS, call_id="case:turn:1"):
        assert __import__("os").environ["NEXUS_RESEARCH_ROOM_PRODUCTION_CASE"] == "true"
        assert __import__("os").environ["NEXUS_DURABLE_JOB_ID"] == IDS["job_id"]
        assert __import__("os").environ["NEXUS_CORRELATION_ID"] == IDS["objective_id"]
        assert __import__("os").environ["NEXUS_PROJECT_ID"] == IDS["project_id"]
        assert __import__("os").environ["NEXUS_JOB_TYPE"] == "RESEARCH_CASE_CONTINUATION"
        assert __import__("os").environ["NEXUS_RESEARCH_ROOM_CALL_ID"] == "case:turn:1"
    assert "NEXUS_RESEARCH_ROOM_PRODUCTION_CASE" not in __import__("os").environ


def test_research_production_router_never_selects_local_ollama(monkeypatch):
    from nexus_agent_platform.research_room.advisor_router import AdvisorRouter
    from nexus_agent_platform.research_room.local_ollama_advisor import OracleLocalOllamaAdvisor
    monkeypatch.setenv("NEXUS_RESEARCH_ROOM_PRODUCTION_CASE", "true")
    monkeypatch.delenv("NEXUS_RESEARCH_ROOM_DISABLE_LOCAL_OLLAMA", raising=False)
    router = AdvisorRouter(free_only=True)
    assert not any(isinstance(p, OracleLocalOllamaAdvisor) for p in router.providers)
    assert all(getattr(p, "provider", "") != "OLLAMA_LOCAL" for p in router.providers)
    assert not AdvisorRouter(providers=[OracleLocalOllamaAdvisor()]).providers


def test_continue_retries_prior_source_failure_on_same_case(monkeypatch, tmp_path):
    from .test_repair_contracts import _queued_fakes
    import json
    case = {"case_id": IDS["case_id"], "primary_question": IDS["project_id"], "open_questions": [],
        "sources": [], "findings": [], "research_room_controller": {"lineage": IDS,
            "turn_count": 4, "next_participant": "FACT_CHECKER", "room_state": {
                "case_id": IDS["case_id"], "original_request": "Continue this same case",
                "metadata": {"shadow_mode": False, "production_lineage": IDS},
                "next_participant": "FACT_CHECKER", "turn_count": 4,
                "source_references": [], "source_report": {"status": "SOURCE_INCOMPLETE", "text": ""},
                "questions": [], "unresolved_items": []}}}
    _queued_fakes(monkeypatch, tmp_path, case)
    discovery_calls = []
    def discover(question):
        discovery_calls.append((question, os.environ.get("NEXUS_DURABLE_JOB_ID"),
                                os.environ.get("NEXUS_PROJECT_ID"),
                                os.environ.get("NEXUS_RESEARCH_ROOM_CALL_ID")))
        return "https://example.test/evidence", []
    monkeypatch.setattr(controller, "_discover_public_source", discover)
    result = controller.continue_case(**IDS, instruction="Continue the existing case and resolve its citation question")
    assert result["status"] == "queued"
    assert result["source_discovery_optional"] is True
    assert discovery_calls == []
    payload = json.loads((tmp_path / "data/runtime/research_room_advisor" /
        (result["attempt_id"] + ".json")).read_text())
    assert payload["case_context"]["provided_input"].startswith("Continue the existing case")
