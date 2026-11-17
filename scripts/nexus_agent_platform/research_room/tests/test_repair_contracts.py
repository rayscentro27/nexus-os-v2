from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from nexus_agent_platform.research_room import production_controller as controller
from nexus_agent_platform.research_room.source_tools import SourceTools


IDS = {"case_id": "rcase_fixture12345", "objective_id": "objective-fixture",
       "project_id": "project-fixture", "job_id": "job_fixture12345"}


def _queued_fakes(monkeypatch, tmp_path, case):
    from nexus_agent_platform import durable_jobs
    from nexus_agent_platform.runtime import paths
    saved = []

    def save(case_id, *, controller=None, advisor_review=None, event=""):
        case["research_room_controller"] = controller
        if advisor_review:
            case.setdefault("research_room_advisor_reviews", []).append(advisor_review)
        saved.append(event)
        return {"saved": True}

    class Store:
        def enqueue(self, *args, **kwargs):
            attempt = case["research_room_controller"]["advisor_attempts"][-1]
            assert attempt["status"] == "QUEUED"
            assert attempt["job_id"] == kwargs["job_id"]
            return SimpleNamespace(job_id=kwargs["job_id"])

    monkeypatch.setattr(controller, "_load", lambda identity: case)
    monkeypatch.setattr(controller, "_save_controller", save)
    monkeypatch.setattr(paths, "nexus_research_state_path",
        lambda *parts: tmp_path / "data" / __import__("pathlib").Path(*parts))
    monkeypatch.setattr(durable_jobs, "default_store", Store)
    return saved


def test_governance_context_is_established_before_search():
    events = []
    def route(_query):
        import os
        events.append(os.environ.get("NEXUS_RESEARCH_ROOM_PRODUCTION_CASE"))
        return {"status": "no_results", "results": []}
    with controller._production_governance_context(IDS, call_id="fixture"):
        SourceTools(methods=[], search_routes=[("fixture", route)]).research_questions(
            "objective", [{"question_id": "q", "question": "material claim"}])
    assert events == ["true"]


def test_first_source_failure_triggers_alternate_route():
    calls = []
    tools = SourceTools(methods=[("fixture", lambda *_a, **_k: {"text": "x"})],
        search_routes=[("first", lambda _q: calls.append("first") or {"status": "error", "notes": ["down"]}),
                       ("second", lambda _q: calls.append("second") or {"status": "no_results"})])
    tools.research_questions("objective", [{"question_id": "q", "question": "claim evidence"}])
    assert calls == ["first", "second"]


def test_source_attempts_keep_same_case_and_question_ids():
    attempts = []
    SourceTools(methods=[], search_routes=[("offline", lambda _q: {"status": "error", "notes": ["offline"]})],
        attempt_recorder=attempts.append).research_questions("objective", [
            {"case_id": IDS["case_id"], "question_id": "q2", "question": "claim support"}])
    assert attempts[0]["case_id"] == IDS["case_id"]
    assert attempts[0]["question_id"] == "q2"
    assert attempts[0]["result"] == "STARTED"


def test_successful_alternate_route_returns_question_linked_evidence():
    content = ("The material claim about implementation cost is supported by a published "
        "report. " * 20)
    tools = SourceTools(methods=[("fixture_page", lambda *_a, **_k: {"text": content})],
        search_routes=[("first", lambda _q: {"status": "error", "results": []}),
            ("alternate", lambda _q: {"status": "ok", "results": [{"url": "https://example.test/report"}]})])
    result = tools.research_questions("implementation cost", [
        {"case_id": IDS["case_id"], "question_id": "q2", "question": "implementation cost evidence"}])
    assert result["status"] == "SOURCE_ACQUIRED"
    assert result["sources"][0]["question_id"] == "q2"
    assert result["sources"][0]["source_refs"][0]["question_id"] == "q2"
    assert result["sources"][0]["method"] == "alternate"


def test_advisor_acceptance_persists_before_enqueue(monkeypatch, tmp_path):
    case = {"case_id": IDS["case_id"], "research_room_controller": {}}
    saved = _queued_fakes(monkeypatch, tmp_path, case)
    result = controller.advisor_request(**IDS, question="Analyze supplied transcript first")
    assert result["status"] == "queued"
    assert result["job_id"] and result["attempt_id"]
    assert case["research_room_controller"]["advisor_attempts"][0]["status"] == "QUEUED"
    assert "RESEARCH_ROOM_ADVISOR_ATTEMPT_QUEUED" in saved
    assert controller.status(**IDS)["controller"]["latest_advisor_attempt"]["status"] == "QUEUED"
    payload = json.loads((tmp_path / "data/runtime/research_room_advisor" /
                          (result["attempt_id"] + ".json")).read_text())
    assert payload["case_context"]["provided_input"] == "Analyze supplied transcript first"


def test_same_case_advisor_review_projects_substantive_generic_answer(monkeypatch):
    from research import research_case_engine
    question = ("Use only this fixture. Which option is cheaper and by how much? "
        "Which option is faster and by how many minutes? Cedar costs $12 and takes 30 minutes; "
        "Maple costs $9 and takes 45 minutes.")
    review = {"case_id": IDS["case_id"], "objective_id": IDS["objective_id"],
        "project_id": IDS["project_id"], "job_id": IDS["job_id"], "role": "PRIMARY_ADVISOR",
        "question": "Use only supplied fixture. Cedar costs $12 and takes 30 minutes; Maple costs $9 "
            "and takes 45 minutes. Answer which is cheaper, which is faster, and the tradeoff.",
        "analysis": "Maple is $3 cheaper; Cedar is 15 minutes faster.",
        "evidence_notes": ["Fixture: Cedar $12/30 minutes; Maple $9/45 minutes."], "risks": []}
    case = {"case_id": IDS["case_id"], "open_questions": [
        {"question_id": "q_fixture", "question": question, "answer_status": "OPEN"},
        {"question_id": "q_unrelated", "question": "What is the best long-term provider policy?", "answer_status": "OPEN"}],
        "answered_questions": [], "research_room_advisor_reviews": [review]}
    calls = []
    monkeypatch.setattr(research_case_engine, "answer_question", lambda *args, **kwargs:
        calls.append((args, kwargs)) or {"ok": True, "case": case})
    projected = controller._project_primary_review_answers(IDS, case)
    assert projected == {"q_fixture"}
    assert calls[0][0][1] == "q_fixture"
    assert "VERIFICATION BOUNDARY" in calls[0][1]["answer"]


def test_same_case_advisor_review_does_not_project_unrelated_question(monkeypatch):
    case = {"case_id": IDS["case_id"], "open_questions": [
        {"question_id": "q_unrelated", "question": "What is the best long-term provider policy?"}],
        "answered_questions": [], "research_room_advisor_reviews": [{
            "case_id": IDS["case_id"], "objective_id": IDS["objective_id"],
            "project_id": IDS["project_id"], "job_id": IDS["job_id"],
            "role": "PRIMARY_ADVISOR", "question": "Compare Cedar and Maple prices and times.",
            "analysis": "Maple is cheaper; Cedar is faster."}]}
    assert controller._project_primary_review_answers(IDS, case) == set()


def test_generic_answers_match_each_question_to_its_relevant_same_case_review(monkeypatch):
    from research import research_case_engine

    long_initial_review = {"case_id": IDS["case_id"], "objective_id": IDS["objective_id"],
        "project_id": IDS["project_id"], "job_id": IDS["job_id"], "role": "PRIMARY_ADVISOR",
        "question": "Compare the one-week checklist completion rates and stated usage cost in the supplied fixture.",
        "analysis": "Initial detailed review. " * 50, "evidence_notes": ["Initial fixture note."], "risks": []}
    followup_review = {"case_id": IDS["case_id"], "objective_id": IDS["objective_id"],
        "project_id": IDS["project_id"], "job_id": IDS["job_id"], "role": "PRIMARY_RESEARCH_ADVISOR",
        "question": "Which claims materially affect the requested decision, and what evidence supports them? "
            "What important costs, risks, constraints, and alternatives remain uncertain?",
        "analysis": "The counts support only a descriptive comparison. Usage cost is stated as zero; "
            "setup and support costs are not reported. The sample is small and no causal conclusion is supported.",
        "evidence_notes": ["Supplied fixture only."], "risks": ["Small sample."]}
    case = {"case_id": IDS["case_id"], "open_questions": [
        {"question_id": "q_claims", "question": "Which claims materially affect the requested decision, and what evidence supports them?"},
        {"question_id": "q_costs", "question": "What important costs, risks, constraints, and alternatives remain uncertain?"},
        {"question_id": "q_unrelated", "question": "What is the best long-term provider policy?"}],
        "answered_questions": [], "research_room_advisor_reviews": [long_initial_review, followup_review]}
    calls = []
    monkeypatch.setattr(research_case_engine, "answer_question", lambda *args, **kwargs:
        calls.append((args, kwargs)) or {"ok": True, "case": case})

    projected = controller._project_primary_review_answers(IDS, case)

    assert projected == {"q_claims", "q_costs"}
    assert [call[0][1] for call in calls] == ["q_claims", "q_costs"]
    assert all("The counts support only a descriptive comparison" in call[1]["answer"] for call in calls)


def test_advisor_request_returns_without_invoking_provider(monkeypatch, tmp_path):
    case = {"case_id": IDS["case_id"], "research_room_controller": {}}
    _queued_fakes(monkeypatch, tmp_path, case)
    result = controller.advisor_request(**IDS, question="provided source text")
    assert result["status"] == "queued"
    assert not case.get("research_room_advisor_reviews")


def test_loaded_source_input_reaches_advisor_before_search(monkeypatch, tmp_path):
    case = {"case_id": IDS["case_id"], "primary_question": IDS["project_id"],
        "original_request": "Review the supplied transcript", "sources": [
            {"extracted_evidence": "transcript words provided by user"}],
        "open_questions": [], "research_room_controller": {}}
    _queued_fakes(monkeypatch, tmp_path, case)
    response = controller.continue_case(**IDS, instruction="Continue this case")
    assert response["status"] == "queued"
    assert response["source_discovery_optional"] is True
    assert "transcript words provided by user" in json.loads(
        (tmp_path / "data/runtime/research_room_advisor" /
         (response["attempt_id"] + ".json")).read_text())["question"]


def test_zero_cost_router_excludes_metered_providers(monkeypatch):
    from nexus_agent_platform.research_room.advisor_router import AdvisorRouter
    monkeypatch.delenv("NEXUS_RESEARCH_ROOM_PRODUCTION_CASE", raising=False)
    router = AdvisorRouter(free_only=True)
    assert router.providers
    assert all(getattr(p, "free_or_metered", "") in
        {"FREE_ZERO_PRICED", "CHATGPT_PLAN_INCLUDED", "SUBSCRIPTION_INCLUDED"}
        for p in router.providers)


def test_authenticated_chatgpt_plan_requires_durable_zero_spend_policy(monkeypatch, tmp_path):
    from nexus_agent_platform.resource_spend_governor import LocalGovernorStore
    from nexus_agent_platform.research_room.advisor_router import AdvisorRouter

    db_path = tmp_path / "provider-policy.sqlite3"
    monkeypatch.setenv("NEXUS_GOVERNOR_DB", str(db_path))
    governor = LocalGovernorStore(db_path)
    governor.set_policy("CHATGPT_PLAN", "RESEARCH_ADVISOR", "RESEARCH_ROOM_ADVISOR", "DAILY",
        autonomous_usage_allowed=True, autonomous_spend_allowed=False,
        approval_required=False, state="NORMAL")
    monkeypatch.setenv("NEXUS_RESEARCH_ROOM_PRODUCTION_CASE", "true")
    monkeypatch.setenv("NEXUS_DURABLE_JOB_ID", "job-plan-policy-test")

    class PlanRoute:
        provider = "CHATGPT_PLAN"
        model = "gpt-6-luna"
        available = True
        free_or_metered = "CHATGPT_PLAN_INCLUDED"
        def ask(self, **_kwargs):
            return {"status": "COMPLETED", "analysis": "Reasoning from supplied text.",
                "estimated_cost_usd": 0.0}

    result = AdvisorRouter(providers=[PlanRoute()], free_only=True,
        attempt_recorder=lambda row: row["attempt_id"]).ask(
        role="PRIMARY_RESEARCH_ADVISOR", case_context={"metadata": {
            "per_call_soft_target_usd": 0.0, "per_case_soft_target_usd": 0.0,
            "daily_research_soft_target_usd": 0.0, "daily_research_spend_usd": 0.0}},
        objective="Analyze supplied text")
    assert result["provider"] == "CHATGPT_PLAN"
    assert result["analysis"] == "Reasoning from supplied text."
    policy = governor.resolve_policy("CHATGPT_PLAN", "RESEARCH_ADVISOR",
        "RESEARCH_ROOM_ADVISOR", "DAILY")
    assert policy["autonomous_usage_allowed"] is True
    assert policy["autonomous_spend_allowed"] is False
    assert not policy["approval_required"]
    with governor.connect() as db:
        row = db.execute("SELECT provider,status,estimate,actual FROM reservations WHERE provider='CHATGPT_PLAN'").fetchone()
    assert row["status"] == "RECONCILED"
    assert json.loads(row["estimate"])["cost"] == 0
    assert json.loads(row["actual"])["cost"] == 0


def test_paid_provider_governance_stays_default_deny(monkeypatch, tmp_path):
    from nexus_agent_platform.resource_spend_governor import GovernanceDenied, LocalGovernorStore
    governor = LocalGovernorStore(tmp_path / "provider-policy.sqlite3")
    with pytest.raises(GovernanceDenied):
        governor.reserve("OPENAI_API", "RESEARCH_ADVISOR", "RESEARCH_ROOM_ADVISOR",
            "job-metered-openai-test", {"requests": 1, "cost": 0.01}, purpose="test")
    with pytest.raises(GovernanceDenied):
        governor.reserve("OPENROUTER", "RESEARCH_ADVISOR", "RESEARCH_ROOM_ADVISOR",
            "job-paid-openrouter-test", {"requests": 1, "cost": 0.01}, purpose="test")


def test_chatgpt_plan_policy_denial_fails_closed_without_openrouter_fallback(monkeypatch, tmp_path):
    from nexus_agent_platform.research_room.advisor_router import AdvisorRouter
    monkeypatch.setenv("NEXUS_GOVERNOR_DB", str(tmp_path / "default-deny.sqlite3"))
    monkeypatch.setenv("NEXUS_RESEARCH_ROOM_PRODUCTION_CASE", "true")
    monkeypatch.setenv("NEXUS_DURABLE_JOB_ID", "job-plan-denied-test")
    calls = []
    class Route:
        available = True
        model = "fixture:free"
        def __init__(self, provider, route_class):
            self.provider, self.free_or_metered = provider, route_class
        def ask(self, **_kwargs):
            calls.append(self.provider)
            return {"status": "COMPLETED", "analysis": "must not execute"}
    result = AdvisorRouter(providers=[Route("CHATGPT_PLAN", "CHATGPT_PLAN_INCLUDED"),
        Route("OPENROUTER", "FREE_ZERO_PRICED")], free_only=True,
        attempt_recorder=lambda row: row["attempt_id"]).ask(
            role="PRIMARY_RESEARCH_ADVISOR", case_context={"metadata": {
                "per_call_soft_target_usd": 0, "per_case_soft_target_usd": 0,
                "daily_research_soft_target_usd": 0, "daily_research_spend_usd": 0}},
            objective="Analyze supplied text")
    assert result["status"] == "AUTHORIZATION_REQUIRED"
    assert calls == []


def test_certification_research_state_does_not_isolate_provider_policy(monkeypatch, tmp_path):
    from nexus_agent_platform.resource_spend_governor import LocalGovernorStore, default_store
    policy_db = tmp_path / "governance" / "provider-policy.sqlite3"
    research_state = tmp_path / "certification-state"
    policy_db.parent.mkdir()
    store = LocalGovernorStore(policy_db)
    store.set_policy("CHATGPT_PLAN", "RESEARCH_ADVISOR", "RESEARCH_ROOM_ADVISOR", "DAILY",
        autonomous_usage_allowed=True, autonomous_spend_allowed=False,
        approval_required=False, state="NORMAL")
    monkeypatch.setenv("NEXUS_GOVERNOR_DB", str(policy_db))
    monkeypatch.setenv("NEXUS_RESEARCH_STATE_ROOT", str(research_state))
    resolved = default_store().resolve_policy("CHATGPT_PLAN", "RESEARCH_ADVISOR",
        "RESEARCH_ROOM_ADVISOR", "DAILY")
    assert resolved["autonomous_usage_allowed"] is True
    assert resolved["autonomous_spend_allowed"] is False
    assert not policy_db.is_relative_to(research_state)


def test_research_case_persistence_does_not_write_provider_policy(monkeypatch, tmp_path):
    from nexus_agent_platform.resource_spend_governor import LocalGovernorStore
    from research import research_case_engine
    policy_db = tmp_path / "governance.sqlite3"
    state_root = tmp_path / "research-state"
    governor = LocalGovernorStore(policy_db)
    governor.set_policy("CHATGPT_PLAN", "RESEARCH_ADVISOR", "RESEARCH_ROOM_ADVISOR", "DAILY",
        autonomous_usage_allowed=True, autonomous_spend_allowed=False,
        approval_required=False, state="NORMAL")
    before = governor.resolve_policy("CHATGPT_PLAN", "RESEARCH_ADVISOR", "RESEARCH_ROOM_ADVISOR")
    monkeypatch.setenv("NEXUS_RESEARCH_STATE_ROOT", str(state_root))
    monkeypatch.setenv("NEXUS_RESEARCH_CASE_LOCAL_ONLY", "1")
    research_case_engine.open_or_join_case(objective="Disposable policy-separation fixture",
        objective_family="GENERAL", business_or_nexus_goal="Verify state separation",
        owner_department="RESEARCH", primary_question="Question about fixture",
        case_id="rcase_policy_separation_fixture_01", force_existing=True)
    after = governor.resolve_policy("CHATGPT_PLAN", "RESEARCH_ADVISOR", "RESEARCH_ROOM_ADVISOR")
    assert before == after


def test_research_zero_new_spend_router_always_excludes_local_ollama(monkeypatch):
    from nexus_agent_platform.research_room.advisor_router import AdvisorRouter
    monkeypatch.setenv("NEXUS_RESEARCH_ROOM_PRODUCTION_CASE", "true")
    monkeypatch.delenv("NEXUS_RESEARCH_ROOM_DISABLE_LOCAL_OLLAMA", raising=False)
    router = AdvisorRouter(free_only=True)
    assert router.providers
    assert all(getattr(p, "provider", "") != "OLLAMA_LOCAL" for p in router.providers)
    assert all(getattr(p, "free_or_metered", "") in
        {"FREE_ZERO_PRICED", "CHATGPT_PLAN_INCLUDED"}
        for p in router.providers)


def test_chatgpt_plan_failure_falls_back_to_openrouter_free(monkeypatch):
    from nexus_agent_platform.research_room.advisor_router import AdvisorRouter
    calls, receipts = [], []

    class Route:
        available = True
        def __init__(self, provider, route_class, error=None, result=None):
            self.provider, self.free_or_metered = provider, route_class
            self.model = "fixture:free" if provider == "OPENROUTER" else provider.lower() + "-model"
            self.error, self.result = error, result
            self.input_price_per_token = self.output_price_per_token = 0
            self.max_output_tokens = 50
        def ask(self, **_kwargs):
            calls.append(self.provider)
            if self.error:
                raise RuntimeError(self.error)
            return self.result

    router = AdvisorRouter(providers=[
        Route("CHATGPT_PLAN", "CHATGPT_PLAN_INCLUDED", error="GovernanceDenied: CONCURRENCY_LIMIT"),
        Route("OPENROUTER", "FREE_ZERO_PRICED", result={"status": "COMPLETED",
            "analysis": "Useful reasoning from the supplied input.", "estimated_cost_usd": 0.0,
            "model": "fixture:free"}),
        Route("OLLAMA_LOCAL", "FREE_ZERO_PRICED", result={"analysis": "must never run"}),
    ], free_only=True, attempt_recorder=receipts.append)
    result = router.ask(role="PRIMARY_RESEARCH_ADVISOR", case_context={"metadata": {
        "per_call_soft_target_usd": 0.0, "per_case_soft_target_usd": 0.0,
        "daily_research_soft_target_usd": 0.0, "daily_research_spend_usd": 0.0}},
        objective="Analyze the supplied business idea")

    assert calls == ["CHATGPT_PLAN", "OPENROUTER"]
    assert result["analysis"] == "Useful reasoning from the supplied input."
    assert [row["status"] for row in receipts] == ["STARTED", "FAILED", "STARTED", "COMPLETED"]
    assert receipts[0]["provider_attempt_id"] == receipts[1]["provider_attempt_id"]
    assert receipts[0]["error_code"] is None
    assert receipts[1]["error_code"] == "GOVERNANCE_DENIED"
    assert receipts[1]["result"] == "FAILED"
    assert receipts[1]["started_at"] and receipts[1]["completed_at"]
    assert receipts[3]["incremental_cost"] == 0.0


def test_free_openrouter_model_fanout_is_capped(monkeypatch):
    from nexus_agent_platform.research_room.advisor_router import AdvisorRouter
    monkeypatch.setenv("NEXUS_RESEARCH_OPENROUTER_FREE_FALLBACK_MODELS",
        "alternate-a:free,alternate-b:free,alternate-c:free")
    router = AdvisorRouter(free_only=True)
    openrouter = [p for p in router.providers if p.provider == "OPENROUTER"]
    assert [p.model for p in openrouter] == [
        "liquid/lfm-2.5-2.6b:free", "alternate-a:free"]


def test_explicit_technical_metadata_prefers_codex_without_filtering_input():
    from nexus_agent_platform.research_room.advisor_router import AdvisorRouter
    calls = []
    class Route:
        available = True
        input_price_per_token = output_price_per_token = 0
        max_output_tokens = 80
        def __init__(self, provider, route_class):
            self.provider = provider
            self.model = "fixture:free" if provider == "OPENROUTER" else provider + "-model"
            self.free_or_metered = route_class
        def ask(self, **kwargs):
            calls.append((self.provider, kwargs["case_context"].get("provided_input")))
            return {"status": "COMPLETED", "analysis": "Technical review", "estimated_cost_usd": 0.0}
    router = AdvisorRouter(providers=[Route("CHATGPT_PLAN", "CHATGPT_PLAN_INCLUDED"),
        Route("OPENROUTER", "FREE_ZERO_PRICED")], technical_provider=Route("CODEX", "CHATGPT_PLAN_INCLUDED"),
        free_only=True)
    result = router.ask(role="PRIMARY_RESEARCH_ADVISOR", case_context={"provided_input": "Review this repository patch",
        "metadata": {"research_type": "REPOSITORY", "per_call_soft_target_usd": 0,
            "per_case_soft_target_usd": 0, "daily_research_soft_target_usd": 0,
            "daily_research_spend_usd": 0}}, objective="Review this repository patch")
    assert result["analysis"] == "Technical review"
    assert calls == [("CODEX", "Review this repository patch")]


def test_zero_new_spend_policy_skips_metered_codex_technical_route():
    from nexus_agent_platform.research_room.advisor_router import AdvisorRouter
    calls = []

    class Route:
        available = True
        input_price_per_token = output_price_per_token = 0
        max_output_tokens = 80
        def __init__(self, provider, route_class, model=None):
            self.provider, self.free_or_metered = provider, route_class
            self.model = model or ("fixture:free" if provider == "OPENROUTER" else provider + "-model")
        def ask(self, **_kwargs):
            calls.append(self.provider)
            return {"status": "COMPLETED", "analysis": "Plan-backed reasoning", "estimated_cost_usd": 0.0}

    router = AdvisorRouter(providers=[Route("CHATGPT_PLAN", "CHATGPT_PLAN_INCLUDED"),
        Route("OPENROUTER", "FREE_ZERO_PRICED")],
        technical_provider=Route("CODEX", "METERED", "codex-paid-model"), free_only=True)
    result = router.ask(role="PRIMARY_RESEARCH_ADVISOR", case_context={"metadata": {
        "research_type": "REPOSITORY", "per_call_soft_target_usd": 0,
        "per_case_soft_target_usd": 0, "daily_research_soft_target_usd": 0,
        "daily_research_spend_usd": 0}}, objective="Review this repository patch")

    assert result["analysis"] == "Plan-backed reasoning"
    assert calls == ["CHATGPT_PLAN"]


def test_provider_attempt_receipts_include_lifecycle_and_cost_fields():
    from nexus_agent_platform.research_room.advisor_router import AdvisorRouter
    receipts = []

    class Route:
        provider = "OPENROUTER"
        model = "fixture:free"
        available = True
        free_or_metered = "FREE_ZERO_PRICED"
        input_price_per_token = output_price_per_token = 0
        max_output_tokens = 50
        def ask(self, **_kwargs):
            return {"status": "COMPLETED", "analysis": "Reasoning", "estimated_cost_usd": 0.0}

    AdvisorRouter([Route()], attempt_recorder=receipts.append, free_only=True).ask(
        role="PRIMARY", case_context={"metadata": {"per_call_soft_target_usd": 0,
        "per_case_soft_target_usd": 0, "daily_research_soft_target_usd": 0,
        "daily_research_spend_usd": 0}}, objective="Analyze supplied text")
    started, completed = receipts
    assert started["provider_attempt_id"] == completed["provider_attempt_id"]
    assert started["started_at"]
    assert completed["completed_at"]
    assert completed["result"] == "COMPLETED"
    assert completed["incremental_cost"] == 0.0


def test_openrouter_failure_reroutes_to_another_approved_zero_spend_provider():
    from nexus_agent_platform.research_room.advisor_router import AdvisorRouter
    events = []
    class Route:
        available = True
        def __init__(self, provider, free_class, result=None, error=None):
            self.provider, self.free_or_metered = provider, free_class
            self.model = "fixture:free" if provider == "OPENROUTER" else provider + "-model"
            self.result, self.error = result, error
        def ask(self, **_kwargs):
            events.append(self.provider)
            if self.error:
                raise TimeoutError(self.error)
            return self.result
    receipts = []
    router = AdvisorRouter(providers=[
        Route("OPENROUTER", "FREE_ZERO_PRICED", error="timeout"),
        Route("CHATGPT_PLAN", "CHATGPT_PLAN_INCLUDED", {"status": "COMPLETED", "analysis": "Useful initial analysis",
            "estimated_cost_usd": 0.0}),
        Route("OPENROUTER_METERED", "METERED", {"analysis": "must not run"})], free_only=True,
        attempt_recorder=receipts.append)
    result = router.ask(role="PRIMARY", case_context={"metadata": {
        "per_call_soft_target_usd": 0, "per_case_soft_target_usd": 0,
        "daily_research_soft_target_usd": 0}}, objective="Analyze input")
    assert events == ["OPENROUTER", "CHATGPT_PLAN"]
    assert result["analysis"] == "Useful initial analysis"
    assert [row["status"] for row in receipts] == ["STARTED", "TIMEOUT", "STARTED", "COMPLETED"]


def test_advisor_durable_job_uses_research_worker_route():
    from nexus_agent_platform.durable_jobs import handler_route
    assert handler_route("RESEARCH_ROOM_ADVISOR") == "RESEARCH_ROOM_ADVISOR"


def test_advisor_worker_uses_dedicated_handler_and_never_generic_runner(monkeypatch):
    from nexus_agent_platform import job_worker_once
    from nexus_agent_platform.durable_jobs import handler_route
    calls = []
    job = SimpleNamespace(job_id="advisor-job", job_type="RESEARCH_ROOM_ADVISOR",
        department="RESEARCH", governance_context={"source": "RESEARCH_ROOM_ADVISOR"})
    monkeypatch.setattr(job_worker_once, "execute_research_room_advisor",
        lambda _job, payload: calls.append(("advisor", payload)) or {"status": "COMPLETED"})
    monkeypatch.setattr(job_worker_once.subprocess, "run",
        lambda *args, **kwargs: calls.append(("generic", args)) or (_ for _ in ()).throw(AssertionError("generic Research runner called")))
    route = handler_route("RESEARCH_ROOM_ADVISOR")
    outcome = job_worker_once.execute_routed_job(job, route, {"input": "provided text"})
    assert outcome["status"] == "COMPLETED"
    assert calls == [("advisor", {"input": "provided text"})]


def test_advisor_worker_failure_persists_nonqueued_attempt(monkeypatch):
    from nexus_agent_platform import job_worker_once
    calls = []
    job = SimpleNamespace(job_id="advisor-job", job_type="RESEARCH_ROOM_ADVISOR",
        department="RESEARCH", governance_context={"source": "RESEARCH_ROOM_ADVISOR"})
    monkeypatch.setattr(job_worker_once, "_execute_queued_advisor", lambda *_args: (_ for _ in ()).throw(RuntimeError("provider path failed")))
    monkeypatch.setattr(job_worker_once, "_persist_advisor_worker_failure",
        lambda _payload, _job, exc: calls.append(str(exc)))
    try:
        job_worker_once.execute_research_room_advisor(job,
            {"attempt_id": "attempt", "identity": {"case_id": "case"}})
    except RuntimeError:
        pass
    assert calls == ["provider path failed"]


@pytest.mark.parametrize("advisor_status", ["COMPLETED", "UNAVAILABLE"])
def test_advisor_worker_completes_job_and_attempt_after_provider_outcome(monkeypatch, tmp_path, advisor_status):
    from nexus_agent_platform import durable_jobs, job_worker_once, resource_spend_governor, supabase_egress_guard
    db = tmp_path / "jobs.sqlite"
    store = durable_jobs.DurableJobStore(db)
    payload = {"identity": {"case_id": "case", "objective_id": "objective",
        "project_id": "project", "job_id": "parent"}, "attempt_id": "attempt"}
    (tmp_path / "advisor.json").write_text(json.dumps(payload))
    job = store.enqueue("RESEARCH", "RESEARCH_ROOM_ADVISOR", job_id="advisor-job",
        payload_ref="advisor.json", correlation_id="objective", max_attempts=1,
        idempotency_key="advisor-success", governance_context={"source": "RESEARCH_ROOM_ADVISOR"})
    claimed = store.claim_by_id(job.job_id, "worker")
    assert claimed and claimed.state == "CLAIMED"
    transitions = []
    original_transition = store.transition
    def transition(job_id, state, **kwargs):
        transitions.append(state)
        return original_transition(job_id, state, **kwargs)
    monkeypatch.setattr(store, "transition", transition)
    monkeypatch.setattr(job_worker_once, "ROOT", tmp_path)
    monkeypatch.setattr(job_worker_once, "_is_under_nexus_runtime_root", lambda _path: True)
    monkeypatch.setattr(job_worker_once, "_footprint", lambda *args, **kwargs: "footprint")
    monkeypatch.setattr(supabase_egress_guard, "job_egress_snapshot",
        lambda _job: {"request_count": 0, "response_bytes": 0})
    class Governor:
        def reserve(self, *args, **kwargs): return {"reservation_id": "reservation"}
        def reconcile(self, *_args, **_kwargs): pass
        def release(self, *_args, **_kwargs): pass
    monkeypatch.setattr(resource_spend_governor, "default_store", lambda: Governor())
    attempt_states = ["QUEUED"]
    def execute(_payload, _worker_job):
        attempt_states.append("RUNNING")
        attempt_states.append(advisor_status)
        return {"status": "COMPLETED", "advisor_status": advisor_status, "cost": 0.0}
    monkeypatch.setattr(job_worker_once, "_execute_queued_advisor", execute)
    result = job_worker_once.run(job.job_id, "worker", store)
    assert result["status"] == "COMPLETED"
    assert transitions[0] == "RUNNING"
    assert store.get(job.job_id).state == "COMPLETED"
    assert attempt_states == ["QUEUED", "RUNNING", advisor_status]


def test_advisor_provider_receives_primary_input_and_zero_dollar_context(monkeypatch):
    case = {"case_id": IDS["case_id"], "primary_question": IDS["project_id"],
        "sources": [], "findings": [], "open_questions": [], "status": "PROMISING",
        "research_room_controller": {"advisor_attempts": [{"attempt_id": "attempt",
            "job_id": "worker-job", "status": "QUEUED"}]}}
    monkeypatch.setattr(controller, "_load", lambda _identity: case)
    monkeypatch.setattr(controller, "_save_controller", lambda _case, **kwargs:
        case.update(research_room_controller=kwargs["controller"]) or {"saved": True})
    seen = {}
    from nexus_agent_platform.research_room import advisor_router
    class Router:
        def __init__(self, *, free_only, **_kwargs):
            seen["free_only"] = free_only
        def ask(self, *, case_context, **_kwargs):
            seen["provided_input"] = case_context["provided_input"]
            seen["budget"] = case_context["metadata"]["per_call_soft_target_usd"]
            return {"analysis": "Initial analysis", "estimated_cost_usd": 0.0}
    monkeypatch.setattr(advisor_router, "AdvisorRouter", Router)
    result = controller.execute_queued_advisor({"identity": IDS, "attempt_id": "attempt",
        "review_role": "PRIMARY_ADVISOR", "question": "Read this supplied transcript first.",
        "case_context": {"provided_input": "provided transcript", "metadata": {}}},
        worker_job_id="worker-job")
    assert result["advisor_status"] == "COMPLETED"
    assert seen == {"free_only": True, "provided_input": "provided transcript", "budget": 0.0}


def test_advisor_worker_exception_is_persisted_on_same_attempt(monkeypatch):
    case = {"case_id": IDS["case_id"], "research_room_controller": {"advisor_attempts": [{
        "attempt_id": "attempt", "job_id": "worker-job", "status": "QUEUED"}]}}
    monkeypatch.setattr("research.research_case_engine.get_case", lambda _case_id: case)
    monkeypatch.setattr(controller, "_save_controller", lambda _case, **kwargs:
        case.update(research_room_controller=kwargs["controller"]) or {"saved": True})
    result = controller.record_queued_advisor_worker_failure(
        {"identity": IDS, "attempt_id": "attempt"}, worker_job_id="worker-job",
        error=RuntimeError("worker dispatch failure"))
    attempt = case["research_room_controller"]["advisor_attempts"][0]
    assert result["saved"] is True
    assert attempt["status"] == "FAILED"
    assert attempt["error_summary"] == "worker dispatch failure"


def test_worker_accepts_durable_payload_through_release_data_symlink(monkeypatch, tmp_path):
    from nexus_agent_platform import job_worker_once
    from nexus_agent_platform.runtime import paths
    release = tmp_path / "release"
    canonical_runtime = tmp_path / "canonical-runtime"
    release.mkdir()
    (release / "data/runtime").mkdir(parents=True)
    canonical_runtime.mkdir()
    (release / "data/runtime").rmdir()
    (release / "data/runtime").symlink_to(canonical_runtime, target_is_directory=True)
    payload = release / "data/runtime/research_room_advisor/job.json"
    payload.parent.mkdir(parents=True)
    payload.write_text("{}")
    monkeypatch.setattr(job_worker_once, "ROOT", release)
    monkeypatch.setattr(paths, "get_nexus_repo_root", lambda: release)
    monkeypatch.setattr(paths, "nexus_data_path", lambda *parts: release / "data" / __import__("pathlib").Path(*parts))
    assert job_worker_once._is_under_nexus_runtime_root(payload)
    assert not job_worker_once._is_under_nexus_runtime_root(tmp_path / "outside" / "payload.json")


def test_advisor_requested_search_returns_to_same_advisor_context(monkeypatch):
    case = {"case_id": IDS["case_id"], "primary_question": IDS["project_id"],
        "open_questions": [{"question_id": "q2", "question": "Which claim needs support?"}],
        "sources": [], "findings": [], "research_room_controller": {"advisor_attempts": [
            {"attempt_id": "a1", "job_id": "j1", "status": "QUEUED"}]}}
    monkeypatch.setattr(controller, "_load", lambda _identity: case)
    monkeypatch.setattr(controller, "_save_controller", lambda _case, **kwargs:
        case.update(research_room_controller=kwargs["controller"]) or {"saved": True})
    persisted_projection = []
    monkeypatch.setattr(controller, "_persist_room_projection", lambda identity, state:
        persisted_projection.append(state) or {"saved": True})
    from nexus_agent_platform.research_room import advisor_router, source_tools
    calls = []
    class Router:
        def __init__(self, **_kwargs): pass
        def ask(self, *, case_context, **_kwargs):
            calls.append(case_context)
            if len(calls) == 1:
                return {"analysis": "Need a source for q2.", "tool_requests": [
                    {"question_id": "q2", "question": "Published evidence for this claim"}]}
            return {"analysis": "The requested evidence was reviewed.", "estimated_cost_usd": 0.0}
    class Tools:
        def __init__(self, *, attempt_recorder): self.record = attempt_recorder
        def research_questions(self, _objective, questions):
            assert questions[0]["production_question_id"] == "q2"
            self.record({"attempt_id": "s1", "question_id": "q2", "result": "SOURCE_ACQUIRED"})
            return {"status": "SOURCE_ACQUIRED", "sources": [], "source_attempts": [],
                "text": "", "summary": ""}
    monkeypatch.setattr(advisor_router, "AdvisorRouter", Router)
    monkeypatch.setattr(source_tools, "SourceTools", Tools)
    result = controller.execute_queued_advisor({"identity": IDS, "attempt_id": "a1",
        "review_role": "PRIMARY_ADVISOR", "question": "provided transcript",
        "case_context": {"metadata": {}}}, worker_job_id="j1")
    assert len(calls) == 2
    assert calls[1]["tool_results"]["status"] == "SOURCE_ACQUIRED"
    assert persisted_projection
    assert result["advisor_status"] == "COMPLETED"


def test_all_free_routes_unavailable_persists_nonterminal_case(monkeypatch):
    case = {"case_id": IDS["case_id"], "status": "PROMISING",
        "research_room_controller": {"lineage": IDS, "advisor_attempts": [{
            "attempt_id": "rradvatt_fixture", "job_id": "job-advisor", "status": "QUEUED"}]}}
    monkeypatch.setattr(controller, "_load", lambda _identity: case)
    saved = []
    monkeypatch.setattr(controller, "_save_controller", lambda _case, **kwargs:
        saved.append(kwargs) or {"saved": True})
    from nexus_agent_platform.research_room import advisor_router

    status_when_provider_called = []
    class Router:
        def __init__(self, **kwargs):
            assert kwargs["free_only"] is True
        def ask(self, **kwargs):
            status_when_provider_called.append(case["research_room_controller"]["advisor_attempts"][0]["status"])
            return {"status": "ADVISOR_UNAVAILABLE", "analysis": None, "reason": "all_free_failed"}
    monkeypatch.setattr(advisor_router, "AdvisorRouter", Router)
    result = controller.execute_queued_advisor({"identity": IDS, "attempt_id": "rradvatt_fixture",
        "review_role": "PRIMARY_ADVISOR", "question": "provided input",
        "case_context": {"metadata": {}}}, worker_job_id="job-advisor")
    assert result["advisor_status"] == "UNAVAILABLE"
    assert status_when_provider_called == ["RUNNING"]
    assert case["research_room_controller"]["advisor_attempts"][0]["status"] == "UNAVAILABLE"
    assert case["status"] == "PROMISING"
    assert any(row.get("event") == "RESEARCH_ROOM_ADVISOR_UNAVAILABLE" for row in saved)


def test_controller_continues_when_all_free_advisors_are_unavailable(monkeypatch):
    case = {"case_id": IDS["case_id"], "primary_question": IDS["project_id"],
        "open_questions": [{"question_id": "q2", "question": "material claim?"}],
        "sources": [], "findings": [], "status": "PROMISING",
        "research_room_controller": {"lineage": IDS, "advisor_attempts": [
            {"attempt_id": "a1", "status": "UNAVAILABLE"}]}}
    monkeypatch.setattr(controller, "_load", lambda _identity: case)
    monkeypatch.setattr(controller, "_persist_room_projection", lambda _identity, state: {"saved": True})
    from nexus_agent_platform.research_room import room_graph
    seen = []
    def turn(_self, state, *, production_case_binding=None):
        seen.append((state["next_participant"], state["advisor_comments"][0]["status"],
            production_case_binding))
        return {**state, "turn_count": 1, "next_participant": "QUESTION_GENERATOR"}
    monkeypatch.setattr(room_graph.RoomGraph, "turn", turn)
    result = controller.continue_case(**IDS, instruction="Continue using the supplied input")
    assert result["status"] == "advanced"
    assert seen == [("KNOWLEDGE_RECONCILIATION", "ADVISOR_UNAVAILABLE", IDS)]
    assert case["status"] == "PROMISING"


def test_failed_advisor_job_is_readable_from_controller_results(monkeypatch):
    case = {"case_id": IDS["case_id"], "research_room_controller": {
        "advisor_attempts": [{"attempt_id": "a1", "job_id": "j1", "status": "UNAVAILABLE"}]}}
    monkeypatch.setattr(controller, "_load", lambda _identity: case)
    result = controller.results(**IDS)
    assert result["results"]["research_room_controller"]["advisor_attempts"][0]["status"] == "UNAVAILABLE"


def test_control_question_is_not_sent_to_source_search(monkeypatch):
    case = {"case_id": IDS["case_id"], "primary_question": IDS["project_id"],
        "open_questions": [{"question_id": "control",
            "question": "Continue the existing Research project; preserve the same case and leave the citation question open."},
            {"question_id": "q2", "question": "Which claims affect the decision?"}],
        "sources": [], "findings": []}
    state = controller._room_state(case, IDS, "continue")
    assert [row["production_question_id"] for row in state["questions"]] == ["q2"]
    assert state["control_requirements"][0]["status"] == "CONTROL_REQUIREMENT_SATISFIED"


def test_control_requirement_persists_without_answering_substantive_questions(monkeypatch, tmp_path):
    from research import research_case_engine as engine
    case = {"case_id": IDS["case_id"], "open_questions": [
        {"question_id": "control", "question": "Continue the existing Research project; preserve the same case and leave the citation question open."},
        {"question_id": "q2", "question": "Which claims materially affect the decision?"}],
        "research_room_controller": {}}
    _queued_fakes(monkeypatch, tmp_path, case)
    def save(_case, _event, **updates):
        case.update(updates)
        return case
    monkeypatch.setattr(engine, "_save", save)
    monkeypatch.setattr(engine, "get_case", lambda _case_id: case)
    result = controller.advisor_request(**IDS, question="Analyze the supplied input")
    assert result["status"] == "queued"
    assert [row["question_id"] for row in case["open_questions"]] == ["q2"]
    assert case["research_room_control_requirements"][0]["status"] == "CONTROL_REQUIREMENT_SATISFIED"
    assert not case.get("answered_questions")


def test_source_retry_receipt_is_upserted_on_same_case(monkeypatch):
    case = {"case_id": IDS["case_id"], "research_room_controller": {"lineage": IDS}}
    monkeypatch.setattr(controller, "_load", lambda _identity: case)
    monkeypatch.setattr(controller, "_save_controller", lambda _case, **kwargs:
        case.update(research_room_controller=kwargs["controller"]) or {"saved": True})
    receipt = {"attempt_id": "a1", "question_id": "q2", "result": "SEARCH_FAILED"}
    controller._persist_source_attempt(IDS, receipt)
    controller._persist_source_attempt(IDS, {**receipt, "result": "SOURCE_ACQUIRED"})
    attempts = case["research_room_controller"]["source_attempts"]
    assert len(attempts) == 1
    assert attempts[0]["case_id"] == IDS["case_id"]
    assert attempts[0]["result"] == "SOURCE_ACQUIRED"
