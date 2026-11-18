from __future__ import annotations

from pathlib import Path

import pytest

from nexus_agent_platform.research_room.advisor_router import (
    AdvisorRouter, ChatGPTAdvisor, HermesAdvisor, OpenRouterAdvisor,
)
from nexus_agent_platform.research_room.context import compact_context
from nexus_agent_platform.research_room.room_graph import RoomGraph, langgraph_version
from nexus_agent_platform.research_room.source_tools import SourceTools
from nexus_agent_platform.research_room.state import JsonCaseStore, SupabaseCaseStore
from nexus_agent_platform.research_room.worker import ResearchRoomWorker, ShadowRoomRunner
from nexus_agent_platform.research_room.usage import record_call
from nexus_agent_platform.research_room.local_ollama_advisor import OracleLocalOllamaAdvisor
from nexus_agent_platform.research_room.participants import FinalSynthesizer, SourceAnalyst


class FixedAdvisor:
    provider = "FIXTURE"
    available = True
    def ask(self, *, role, case_context, objective):
        return {"status": "COMPLETED", "provider": self.provider,
            "analysis": "Fixture advisor view; material claims should be independently checked.",
            "new_questions": ["What evidence supports the main claim?", "What risks or costs remain uncertain?"]}


def _worker(tmp_path: Path, *, methods=None, advisor=None, knowledge=None, verifier=None):
    tools = SourceTools(methods=methods or [("FIXTURE", lambda url, objective="": {
        "url": url, "title": "Fixture subject", "text": "Main claim price risk seasonal strategy evidence.",
        "source_type": "FIXTURE"})])
    providers = [FixedAdvisor()] if advisor is None else ([advisor] if advisor else [])
    graph = RoomGraph(source_tools=tools, advisor_router=AdvisorRouter(providers),
        knowledge_adapter=knowledge, verifier=verifier)
    return ResearchRoomWorker(JsonCaseStore(tmp_path), graph)


def _run(tmp_path, *, metadata=None, before=None, **kwargs):
    worker = _worker(tmp_path, **kwargs)
    worker.open_case(case_id="case-test", objective="Assess this subject for Nexus.",
        source_url="https://example.test", source_type="WEB", metadata={"likely_destination": "TRADING", **(metadata or {})})
    if before:
        state = worker.store.load("case-test")
        before(state)
        worker.store.save(state)
    return ShadowRoomRunner(worker).run_to_completion("case-test")


def test_langgraph_is_reused_and_room_executes_one_participant_per_turn(tmp_path):
    assert langgraph_version()
    worker = _worker(tmp_path)
    worker.open_case(case_id="bounded", objective="Understand a source", source_url="https://example.test")
    first = worker.run_one_turn("bounded")
    assert first["executed_participant"] == "RESEARCH_LEAD"
    assert first["case"]["turn_count"] == 1
    assert first["next_job"]["shadow_mode"] is True
    assert worker.store.load("bounded")["turn_count"] == 1


def test_production_turn_requires_exact_case_binding_and_creates_no_room_store(tmp_path):
    from nexus_agent_platform.research_room.models import new_case
    graph = _worker(tmp_path).graph
    room = new_case("rcase_exact12345", "Continue the exact production case",
        metadata={"shadow_mode": False})
    state = room.to_dict()
    with pytest.raises(ValueError, match="EXACT_PRODUCTION_CASE_BINDING_REQUIRED"):
        graph.turn(state)
    binding = {"objective_id": "objective-exact", "project_id": "project-exact",
               "case_id": "rcase_exact12345", "job_id": "job_exact12345"}
    first = graph.turn(state, production_case_binding=binding)
    assert first["turn_count"] == 1
    assert first["case_id"] == binding["case_id"]
    assert JsonCaseStore(tmp_path).load(binding["case_id"]) is None


def test_shadow_case_finishes_with_proposed_handoff_and_shared_conversation(tmp_path):
    result = _run(tmp_path)
    case = result["case"]
    assert result["status"] == "COMPLETE"
    assert case["status"] == "COMPLETE"
    assert case["status_history"] == ["OPEN", "WORKING", "SYNTHESIZING", "HANDED_OFF", "COMPLETE"]
    assert case["handoff"]["kind"] == "PROPOSED_HANDOFF"
    assert case["handoff"]["target_department"] == "TRADING"
    assert len(case["room_messages"]) >= 8


@pytest.mark.parametrize("condition", [
    "low_confidence", "source_unavailable", "advisor_unavailable", "advisor_disagreement",
    "needle_missing", "negative_result", "unknown_category", "unanswered_question",
])
def test_information_quality_never_stops_a_case(tmp_path, condition):
    advisor = False if condition == "advisor_unavailable" else None
    if condition == "advisor_disagreement":
        class DisagreeingAdvisor(FixedAdvisor):
            def ask(self, **kwargs):
                result = super().ask(**kwargs)
                result["analysis"] = {"advisors": ["VIEW_A", "VIEW_B"], "disagreement": "Different interpretations"}
                return result
        advisor = DisagreeingAdvisor()
    methods = [("UNAVAILABLE", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("offline")))] \
        if condition == "source_unavailable" else [("FIXTURE", lambda url, objective="": {
            "url": url, "title": "Fixture", "text": "short source", "source_type": "FIXTURE"})]
    def seed(state):
        if condition == "negative_result":
            state["test_results"].append({"result": "NEGATIVE", "detail": "Fixture underperformed."})
        if condition == "low_confidence":
            state["findings"].append({"claim": "fixture", "confidence": "LOW"})
        if condition == "advisor_disagreement":
            state["advisor_comments"].append({"provider": "SECOND_FIXTURE", "analysis": "Alternative interpretation."})
    result = _run(tmp_path, methods=methods, advisor=advisor, before=seed)
    assert result["status"] == "COMPLETE"
    assert result["case"]["handoff"]["kind"] == "PROPOSED_HANDOFF"
    if condition in {"source_unavailable", "unanswered_question"}:
        assert result["case"]["unresolved_items"]
    if condition == "negative_result":
        assert result["case"]["final_synthesis"]["test_results"][0]["result"] == "NEGATIVE"
        assert result["case"]["status"] == "COMPLETE"


def test_source_fallback_records_failed_method_then_uses_second(tmp_path):
    tools = SourceTools(methods=[
        ("BROKEN", lambda *_a, **_k: (_ for _ in ()).throw(PermissionError("denied"))),
        ("FALLBACK", lambda url, objective="": {"url": url, "text": "secondary content", "title": "fallback"}),
    ])
    result = tools.acquire("https://example.test")
    assert result["status"] == "SOURCE_ACQUIRED"
    assert result["method"] == "FALLBACK"
    assert result["method_failures"][0]["status"] == "UNAVAILABLE"


def test_production_http_source_fetch_uses_durable_governance(monkeypatch):
    from nexus_agent_platform import provider_enforcement
    monkeypatch.setenv("NEXUS_DURABLE_JOB_ID", "job-case-fixture")
    monkeypatch.setenv("NEXUS_CORRELATION_ID", "objective-fixture")
    monkeypatch.setenv("NEXUS_PROJECT_ID", "project-fixture")
    monkeypatch.setenv("NEXUS_DEPARTMENT", "RESEARCH")
    monkeypatch.setenv("NEXUS_JOB_TYPE", "RESEARCH_CASE_CONTINUATION")
    monkeypatch.setenv("NEXUS_RESEARCH_ROOM_CALL_ID", "case-fixture:controller-turn:1")
    captured = {}
    def governed(provider, service, action_type, estimate, operation, **kwargs):
        captured.update(provider=provider, service=service, action_type=action_type,
                        estimate=estimate, **kwargs)
        return {"url": "https://example.test/source", "title": "Source", "text": "bounded evidence",
                "source_type": "WEB", "http_status": 200}
    monkeypatch.setattr(provider_enforcement, "execute", governed)
    source = SourceTools()._http("https://example.test/source", objective="case evidence")
    assert source["text"] == "bounded evidence"
    assert captured["provider"] == "PUBLIC_WEB"
    assert captured["action_type"] == "RESEARCH_READ"
    assert captured["job_id"] == "job-case-fixture"
    assert captured["correlation_id"] == "objective-fixture"
    assert captured["estimate"]["bytes"] <= 500_000
    assert captured["purpose"].startswith("research-room-source:case-fixture:controller-turn:1:")


def test_workflow_linked_research_room_is_reused_for_changed_followup_objective(monkeypatch):
    from research import research_case_engine as engine
    from nexus_agent_platform import workflow_fabric
    from nexus_agent_platform.research_room import workflow_backend
    workflow_id = "wf_existing-room"
    room_id = "rcase_existing-room"
    source_id = "manual-objective-" + __import__("hashlib").sha256(workflow_id.encode()).hexdigest()[:18]
    case = {"case_id": room_id, "primary_question": "Original funding research objective",
        "project_id": workflow_id, "objective_id": workflow_id,
        "sources": [{"source_id": source_id}],
        "research_room_state": {"room_id": room_id, "objective": "Original funding research objective",
            "participants": {}, "status": "OPEN"}}
    class Store:
        def list(self, limit=100):
            return [{"workflow_id": workflow_id, "research_room_id": room_id}]
    saved = {}
    monkeypatch.setattr(workflow_fabric, "default_state_store", lambda: Store())
    monkeypatch.setattr(engine, "get_case", lambda _case_id: case)
    monkeypatch.setattr(engine, "open_or_join_case", lambda **_kw: pytest.fail("duplicate room creation attempted"))
    def save(_room_id, state, event):
        saved.update(room_id=_room_id, state=state, event=event)
        return {"case": {**case, "research_room_state": state}, "persisted": True,
            "persistence_receipt": {"verified": True}}
    monkeypatch.setattr(workflow_backend, "_save_room", save)
    result_id, result_case = workflow_backend.ensure_room(workflow_id, "Verify a new SBA claim")
    assert result_id == room_id
    assert result_case["case_id"] == room_id
    assert saved["state"]["objective"] == "Original funding research objective"
    assert saved["event"] == "RESEARCH_ROOM_REUSED_FROM_WORKFLOW_LINK"


def test_nexus_source_registry_selects_transcript_and_optional_long_form_digest():
    calls = []
    tools = SourceTools.from_nexus(
        web_search=lambda **kw: calls.append(("search", kw["url"])) or {"text": "search", "title": "search"},
        youtube_transcript=lambda **kw: calls.append(("transcript", kw["url"])) or {"text": "captions", "title": "video"},
        notebooklm=lambda **kw: calls.append(("notebooklm", kw["url"])) or {"text": "digested captions", "title": "notebook"},
    )
    result = tools.acquire("https://youtube.com/watch?v=test")
    assert result["method"] == "YOUTUBE_TRANSCRIPT"
    assert calls[0][0] == "transcript"
    assert all(name != "notebooklm" for name, _ in calls)


def test_existing_knowledge_is_loaded_and_never_stops(tmp_path):
    class Existing:
        def reconcile(self, subject, evidence):
            return {"relationship": "RELATED", "prior_knowledge": [{"summary": "old result"}],
                    "material_changes": ["Current source differs"]}
    result = _run(tmp_path, knowledge=Existing())
    assert result["status"] == "COMPLETE"
    assert result["case"]["prior_nexus_knowledge"][0]["summary"] == "old result"
    assert result["case"]["final_synthesis"]["material_changes"] == ["Current source differs"]


def test_advisor_router_exposes_hermes_openrouter_and_chatgpt_boundaries():
    assert not HermesAdvisor().available
    assert not OpenRouterAdvisor().available
    chatgpt = ChatGPTAdvisor()
    assert chatgpt.available is False
    result = chatgpt.ask(role="advisor", case_context={}, objective="test")
    assert result["status"] == "ADVISOR_UNAVAILABLE"
    with pytest.raises(RuntimeError, match="SHADOW_SUPABASE_SCHEMA_NOT_CONFIGURED"):
        SupabaseCaseStore()


def test_chatgpt_plan_is_primary_and_openrouter_free_is_fallback():
    from nexus_agent_platform.research_room.advisor_router import (
        AdvisorRouter, ChatGPTAdvisor, OpenRouterFreeAdvisor)
    router = AdvisorRouter()
    assert isinstance(router.providers[0], ChatGPTAdvisor)
    assert isinstance(router.providers[1], OpenRouterFreeAdvisor)
    assert router.providers[1].model.endswith(":free")
    assert router.providers[1].input_price_per_token == router.providers[1].output_price_per_token == 0


def test_authenticated_plan_backed_chatgpt_route_is_tier_two_and_accounted():
    class PlanConnector:
        def ask(self, **_kwargs):
            return {"status": "COMPLETED", "provider": "CHATGPT_PLAN", "model": "gpt-6-luna",
                "usage": {"total_tokens": 42}, "estimated_cost_usd": None,
                "duration_ms": 123, "analysis": "Challenge view with an actionable validation test.",
                "prompt_sent": "compact prompt", "full_response": "full ChatGPT response"}
    from nexus_agent_platform.research_room.advisor_router import OpenRouterFreeAdvisor
    free = OpenRouterFreeAdvisor()
    free.available = False
    case = {"case_id": "plan-route", "metadata": {"per_call_soft_target_usd": 0.01,
        "per_case_soft_target_usd": 0.01, "daily_research_soft_target_usd": 0.03,
        "daily_research_spend_usd": 0}}
    result = AdvisorRouter([free, ChatGPTAdvisor(PlanConnector())]).ask(
        role="ADVISOR", case_context=case, objective="Challenge the ranking")
    assert result["status"] == "COMPLETED"
    assert result["provider"] == "CHATGPT_PLAN"
    call = case["model_usage"]["calls"][-1]
    assert call["tier"] == 2
    assert call["total_tokens"] == 42
    assert call["estimated_cost_usd"] == "UNKNOWN"


def test_router_records_free_route_used_before_chatgpt_second_perspective():
    class PlanConnector:
        def ask(self, **_kwargs):
            return {"status": "COMPLETED", "provider": "CHATGPT_PLAN", "model": "gpt-6-luna",
                "usage": {"total_tokens": 8}, "estimated_cost_usd": None, "duration_ms": 10,
                "analysis": "Challenge: price and lead-data risk."}
    case = {"case_id": "two-provider", "advisor_comments": [{"status": "COMPLETED",
        "provider": "OPENROUTER", "model": "liquid/lfm-2.5-2.6b:free"}],
        "metadata": {"per_call_soft_target_usd": .01, "per_case_soft_target_usd": .01,
            "daily_research_soft_target_usd": .03, "daily_research_spend_usd": 0}}
    result = AdvisorRouter([ChatGPTAdvisor(PlanConnector())]).ask(role="CHALLENGER",
        case_context=case, objective="Challenge the ranking")
    assert result["routing_decision"]["tier"] == 2
    assert "already supplied a distinct Advisor 1" in result["routing_decision"]["why_free_route_not_used"]


def test_chatgpt_adapter_preserves_already_compacted_business_packet():
    class PacketConnector:
        def ask(self, *, role, case_context, objective):
            self.packet = case_context
            return {"status": "COMPLETED", "analysis": "Reviewed supplied source evidence."}
    from nexus_agent_platform.research_room.context import PROMPT_VERSION
    connector = PacketConnector()
    packet = {"prompt_version": PROMPT_VERSION, "source_summary": "Fed survey shows sales growth pain.",
        "business_opportunity_report": {"opportunities": [{"name": "Lead-response service"}]}}
    ChatGPTAdvisor(connector).ask(role="advisor", case_context=packet, objective="Compare three options")
    assert connector.packet["source_summary"] == packet["source_summary"]
    assert connector.packet["business_opportunity_report"] == packet["business_opportunity_report"]


def test_business_opportunity_report_scores_three_options_and_validation_plans():
    from nexus_agent_platform.research_room.business_opportunity_proof import _business_report, WEIGHTS
    report = _business_report()
    assert len(report["opportunities"]) == 3
    assert all(set(option["scores"]) == set(WEIGHTS) for option in report["opportunities"])
    assert all(0 < option["weighted_score"] <= 10 and option["total_score"] > 0 for option in report["opportunities"])
    assert len(report["recommendation"]["seven_day_validation_plan"]) == 6
    assert len(report["recommendation"]["thirty_day_launch_plan"]) == 4


def test_business_advisor_rank_extraction_handles_challenged_conditional_ranking():
    from nexus_agent_platform.research_room.business_opportunity_proof import _named_recommendation, _advisor_comparison
    first = "Provisional ranking: 1. AI-enabled lead-response and workflow automation; 2. funding readiness."
    second = "Recommended priority: Keep the lead-response offer first only if interviews confirm recurring costly failures and a buyer commits. Otherwise pivot."
    assert _named_recommendation(first) == "AI_LEAD_RESPONSE_AUTOMATION"
    assert _named_recommendation(second) == "CONDITIONAL_LEAD_RESPONSE_VALIDATION"
    comparison = _advisor_comparison({"status": "COMPLETED", "full_response": first},
        {"status": "COMPLETED", "full_response": second, "new_questions": ["Who will pay?"],
            "risks": ["Broad evidence is not offer demand."], "recommended_actions": ["Interview buyers."]})
    assert comparison["agreements"] and comparison["disagreements"]
    assert comparison["second_advisor_material_value"] == "YES"
    assert comparison["advisor_2_changed_ranking"] == "NO"


def test_needle_adds_required_business_choice_question_then_researches(tmp_path):
    result = _run(tmp_path, metadata={"needle_review_question":
        "What material unanswered questions could change which of these three opportunities Nexus should choose?",
        "needle_followup_evidence": [{"question": "What material unanswered questions could change which of these three opportunities Nexus should choose?",
            "answer": "Current evidence points to buyer acquisition, willingness to pay, delivery scope, and repeat demand as the tests most likely to change the ranking.",
            "confidence": "MEDIUM", "evidence_refs": ["https://www.fedsmallbusiness.org/report"]}]})
    case = result["case"]
    needle_q = next(q for q in case["questions"] if q.get("origin") == "NEEDLE")
    assert needle_q["status"] == "ANSWERED"
    assert case["needle_result"]["coverage_status"] == "MORE_INFORMATION_USEFUL"
    assert case["status"] == "COMPLETE"


def test_full_transcript_exports_prompt_response_and_redacts_secrets(tmp_path):
    from nexus_agent_platform.research_room.transcripts import write_case_artifacts
    case = {"case_id": "transcript-test", "original_request": "Review", "status": "COMPLETE",
        "advisor_sessions": [{"role": "Advisor", "provider": "TEST", "model": "model",
            "input_prompt": "api_key=supersecret analyze this", "full_response": "Bearer abcdef123 response",
            "usage": {"input_tokens": 2, "output_tokens": 3}, "estimated_cost_usd": 0, "duration_ms": 1}],
        "model_usage": {"calls": []}, "source_references": [], "needle_result": {},
        "final_synthesis": {}, "handoff": {}}
    paths = write_case_artifacts(case, tmp_path)
    markdown = Path(paths["markdown"]).read_text()
    jsonl = Path(paths["jsonl"]).read_text()
    assert "analyze this" in markdown and "response" in markdown
    assert "supersecret" not in markdown + jsonl
    assert "abcdef123" not in markdown + jsonl
    assert "input_prompt" in jsonl and "full_response" in jsonl


def test_final_report_renders_rank_scores_plans_and_sources(tmp_path):
    from nexus_agent_platform.research_room.transcripts import write_case_artifacts
    case = {"case_id": "business-report", "status": "COMPLETE", "source_references": [
        {"title": "Federal Reserve survey", "url": "https://example.test/report"}],
        "metadata": {"business_opportunity_report": {"opportunities": [{"name": "Lead response service",
            "weighted_score": 8.1, "total_score": 96, "scores": {"CUSTOMER_PAIN": 9},
            "customer": "Owner-led service firms", "offer": "10-day sprint", "price_hypothesis": "$500",
            "validation_test": "Interview 10 owners"}], "recommendation": {"winner": "Lead response service",
            "what_to_sell": "A fixed-scope sprint", "target_customer": "Service owners", "proposed_price": "$500",
            "seven_day_validation_plan": ["Interview owners"], "thirty_day_launch_plan": ["Launch pilot"]}}},
        "final_synthesis": {}, "needle_result": {}, "multi_advisor_comparison": {}, "handoff": {}}
    paths = write_case_artifacts(case, tmp_path)
    report = Path(paths["final_report"]).read_text()
    assert "Lead response service" in report
    assert "Weighted score" in report
    assert "7-Day Validation Plan" in report
    assert "30-Day Launch Plan" in report
    assert "Federal Reserve survey" in report


def test_provider_http_error_is_not_accepted_as_advisor_analysis():
    from nexus_agent_platform.research_room.advisor_router import parse_advisor_content
    with pytest.raises(ValueError, match="ADVISOR_PROVIDER_ERROR_RESPONSE"):
        parse_advisor_content("HTTP 400: The 'gpt-5.5' model is not supported when using Codex with a ChatGPT account.")


def test_failed_provider_is_recorded_and_temporarily_cooled_down():
    class Broken:
        provider = "HERMES_TEST"
        available = True
        calls = 0
        def ask(self, **kwargs):
            self.calls += 1
            raise RuntimeError("oracle_timeout")
    broken = Broken()
    case = {"case_id": "cooldown", "source_references": [], "advisor_cache": {}, "model_usage": {}}
    router = AdvisorRouter([broken])
    first = router.ask(role="ADVISOR", case_context=case, objective="Question")
    second = router.ask(role="ADVISOR", case_context=case, objective="Question two")
    assert first["status"] == "ADVISOR_UNAVAILABLE"
    assert second["provider_failures"][0]["status"] == "ADVISOR_DEPRIORITIZED"
    assert broken.calls == 1
    assert case["model_usage"]["calls"][0]["result_state"] == "FAILED"


def test_room_job_planner_is_idempotent_by_case_turn_and_next_role(tmp_path):
    worker = _worker(tmp_path)
    worker.open_case(case_id="dedupe", objective="Assess", source_url="https://example.test")
    initial = worker.store.load("dedupe")
    first_job = initial["turn_jobs"][0]
    first = worker.run_turn_job(first_job)
    again = worker.run_turn_job(first_job)
    assert first["next_job"]["idempotency_key"] == again["next_job"]["idempotency_key"]
    assert len([j for j in again["case"]["turn_jobs"] if j["state"] == "READY"]) == 1


def test_combined_imperfect_information_still_synthesizes_and_proposes_handoff(tmp_path):
    unavailable = [("METHOD_A", lambda *_a, **_k: (_ for _ in ()).throw(PermissionError("denied"))),
                   ("METHOD_B", lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("offline")))]
    def seed(state):
        state["questions"].append({"question": "Unanswered fixture question?", "status": "OPEN", "needs_followup": True})
        state["findings"].append({"kind": "CONTRADICTION", "claim_a": "A", "claim_b": "B"})
    result = _run(tmp_path, methods=unavailable, advisor=False, before=seed,
                  metadata={"category": "UNKNOWN"})
    case = result["case"]
    assert result["status"] == "COMPLETE"
    assert case["source_report"]["status"] == "SOURCE_INCOMPLETE"
    assert case["advisor_comments"][0]["status"] == "ADVISOR_UNAVAILABLE"
    assert case["final_synthesis"]["category"] == "UNKNOWN"
    assert case["final_synthesis"]["unresolved_uncertainty"]
    assert case["handoff"]["kind"] == "PROPOSED_HANDOFF"


def test_advisor_receives_compact_context_not_full_transcript_or_room_history():
    state = {"original_request": "Assess this", "source_report": {"text": "x" * 30000,
        "summary": "A concise source summary", "claims": ["claim"]},
        "room_messages": [{"content": "old"} for _ in range(100)],
        "questions": [{"question": "Q?", "status": "OPEN"}]}
    compact = compact_context(state, role="TRADING_ADVISOR")
    encoded = str(compact)
    assert "x" * 500 not in encoded
    assert len(compact["latest_room_deltas"]) <= 3
    assert compact["source_summary"] == "A concise source summary"


def test_duplicate_advisor_question_uses_persisted_cache(tmp_path):
    class Counting(FixedAdvisor):
        calls = 0
        def ask(self, **kwargs):
            self.calls += 1
            return super().ask(**kwargs)
    advisor = Counting()
    router = AdvisorRouter([advisor])
    case = {"case_id": "cache", "original_request": "Assess", "source_references": [{"url": "https://example.test"}],
            "source_report": {"source_content_hash": "same"}, "advisor_cache": {}, "model_usage": {}}
    one = router.ask(role="BUSINESS_ADVISOR", case_context=case, objective="Assess customer economics")
    two = router.ask(role="BUSINESS_ADVISOR", case_context=case, objective="Assess customer economics")
    assert advisor.calls == 1
    assert one["cache_hit"] is False and two["cache_hit"] is True
    assert case["model_usage"]["total_model_calls"] == 1
    assert case["model_usage"]["cache_hits"] == 1


def test_usage_ledger_marks_missing_tokens_and_cost_unknown():
    case = {}
    item = record_call(case, provider="HERMES", model="local", role="ADVISOR",
        usage={}, cost_usd=None, duration_ms=12, purpose="question review")
    assert item["input_tokens"] == item["output_tokens"] == item["total_tokens"] == "UNKNOWN"
    assert item["estimated_cost_usd"] == "UNKNOWN"
    assert case["model_usage"]["token_counts_complete"] is False
    assert case["model_usage"]["cost_complete"] is False


def test_usage_ledger_keeps_known_total_when_input_output_split_is_unknown():
    case = {}
    record_call(case, provider="CHATGPT_PLAN", model="gpt-6-luna", role="ADVISOR",
        usage={"total_tokens": 5021}, cost_usd=None, duration_ms=1200, purpose="challenger")
    ledger = case["model_usage"]
    assert ledger["total_input_tokens"] == ledger["total_output_tokens"] == "UNKNOWN"
    assert ledger["total_tokens"] == 5021
    assert ledger["estimated_total_cost_usd"] == "UNKNOWN"


def test_supabase_shadow_store_round_trip_and_large_source_compaction():
    class Response:
        def __init__(self, body): self.body = body
        def raise_for_status(self): pass
        def json(self): return self.body
    class Session:
        headers = {}
        def __init__(self): self.row = None
        def post(self, url, json, timeout):
            self.row = json
            return Response([json])
        def get(self, url, params, timeout):
            return Response([{"state": self.row["state"]}] if self.row else [])
    session = Session()
    store = SupabaseCaseStore(enabled=True, session=session, url="https://db.test", key="secret-test")
    state = {"case_id": "shadow", "root_objective": "Objective", "status": "WORKING",
        "metadata": {"shadow_mode": True}, "source_report": {"text": "z" * 5000},
        "room_messages": [{"kind": "SOURCE_REPORT", "content": "z" * 5000}],
        "model_usage": {"total_model_calls": 1, "total_tokens": 10}}
    store.save(state)
    restored = store.load("shadow")
    assert session.row["case_id"] == "shadow"
    assert session.row["shadow_mode"] is True
    assert len(restored["source_report"]["text"]) == 2400
    assert restored["model_usage"]["total_tokens"] == 10
    assert len(restored["room_messages"][0]["content"]) == 1800


def test_research_lead_advises_reuse_and_avoids_automatic_extra_models():
    from nexus_agent_platform.research_room.advisor_router import lead_advisor_plan
    plan = lead_advisor_plan({"advisor_comments": [], "prior_nexus_knowledge": [{"summary": "Prior"}],
                              "model_usage": {"total_model_calls": 0}})
    assert plan["reuse_existing_context"] is True
    assert plan["need_new_model_call"] is True  # one useful first advisor; no extra advisor loop
    assert plan["estimated_cost_class"] == "LOW"


def test_existing_local_ollama_advisor_is_governed_zero_spend_and_reports_usage(tmp_path, monkeypatch):
    monkeypatch.setenv("NEXUS_GOVERNOR_DB", str(tmp_path / "governor.sqlite3"))
    monkeypatch.setenv("NEXUS_DURABLE_JOB_ID", "rr-ollama-test-job")
    monkeypatch.setenv("NEXUS_CORRELATION_ID", "rr-ollama-test-correlation")
    monkeypatch.setenv("NEXUS_DEPARTMENT", "RESEARCH")
    envelope = {"message": {"content": '{"analysis":"The source needs independent price checks.","new_questions":["What is the verified cost?"]}'},
        "prompt_eval_count": 90, "eval_count": 35, "total_duration": 1000000000}
    advisor = OracleLocalOllamaAdvisor(transport=lambda payload: envelope)
    result = advisor.ask(role="BUSINESS_ADVISOR", case_context={"case_id": "local-advisor",
        "source_summary": "A compact source", "original_objective": "Assess"}, objective="Question")
    assert result["provider"] == "OLLAMA_LOCAL"
    assert result["model"] == "gemma3:4b"
    assert result["usage"]["total_tokens"] == 125
    assert result["estimated_cost_usd"] == 0
    assert result["analysis"] == "The source needs independent price checks."


def test_local_ollama_advisor_rejects_empty_analysis_result(tmp_path, monkeypatch):
    monkeypatch.setenv("NEXUS_GOVERNOR_DB", str(tmp_path / "governor.sqlite3"))
    monkeypatch.setenv("NEXUS_DURABLE_JOB_ID", "rr-ollama-empty-test-job")
    monkeypatch.setenv("NEXUS_CORRELATION_ID", "rr-ollama-empty-test-correlation")
    monkeypatch.setenv("NEXUS_DEPARTMENT", "RESEARCH")
    envelope = {"message": {"content": "{}"}, "prompt_eval_count": 10,
                "eval_count": 2, "total_duration": 100000000}
    advisor = OracleLocalOllamaAdvisor(transport=lambda payload: envelope)
    import pytest
    with pytest.raises(ValueError, match="ANALYSIS_MISSING"):
        advisor.ask(role="DOMAIN_ADVISOR", case_context={"case_id": "empty-result"}, objective="Review")


def test_source_body_is_not_duplicated_into_findings_or_final_synthesis():
    raw = "A source claim about the strategy. " * 500
    class Source:
        def acquire(self, url, *, objective=""):
            return {"url": url, "title": "Source title", "text": raw,
                    "summary": "Bounded source summary.", "status": "SOURCE_ACQUIRED",
                    "source_type": "WEB", "source_content_hash": "hash", "source_character_count": len(raw)}
    case = {"original_request": "Review this source", "source_references": [{"url": "https://example.test"}],
            "findings": [], "unresolved_items": [], "questions": [], "answers": [],
            "advisor_comments": [], "test_results": [], "metadata": {"shadow_mode": True}}
    SourceAnalyst(Source()).contribute(case)
    assert case["source_report"]["text"] == raw
    assert raw not in str(case["findings"])
    case["questions_generated"] = True
    synthesis = FinalSynthesizer().synthesize(case)
    assert raw not in str(synthesis)
    assert synthesis["what_it_is"] == "Bounded source summary."


def test_gateway_advisor_keeps_plain_text_as_usable_analysis():
    from nexus_agent_platform.research_room.advisor_router import parse_advisor_content
    plain = parse_advisor_content("Demand, fulfillment cost, and repeat purchase are the key unknowns.")
    structured = parse_advisor_content('{"analysis":"Main risk is route density.","new_questions":["How many buyers?"]}')
    assert plain["response_format"] == "PLAIN_TEXT"
    assert "repeat purchase" in plain["analysis"]
    assert structured["analysis"] == "Main risk is route density."
    assert structured["new_questions"] == ["How many buyers?"]


def test_soft_cost_target_cannot_stop_synthesis_or_handoff(tmp_path):
    result = _run(tmp_path, metadata={"per_case_soft_target_usd": 0.0})
    case = result["case"]
    assert result["status"] == "COMPLETE"
    assert case["advisor_comments"][0]["status"] == "COST_BUDGET_PRESSURE"
    assert case["final_synthesis"]
    assert case["handoff"]["kind"] == "PROPOSED_HANDOFF"
    assert case["cost_routing"]["paid_call_skipped"] is True


def test_provider_hard_budget_pressure_routes_away_and_preserves_partial_synthesis(tmp_path):
    class BudgetDenied:
        provider, available = "OPENROUTER", True
        model = "google/gemini-2.5-flash-lite"
        def ask(self, **_kwargs):
            raise RuntimeError("RESOURCE_BUDGET_HARD_STOP")
    result = _run(tmp_path, advisor=BudgetDenied())
    case = result["case"]
    assert case["advisor_comments"][0]["status"] == "COST_BUDGET_PRESSURE"
    assert case["cost_routing"]["paid_call_skipped"] is True
    assert case["final_synthesis"]["what_it_is"]
    assert case["handoff"]["kind"] == "PROPOSED_HANDOFF"
    assert case["status"] == "COMPLETE"


def test_multi_advisor_comparison_is_included_in_final_synthesis():
    case = {"original_request": "Assess opportunity", "source_report": {"title": "Evidence"},
        "source_references": [], "metadata": {"shadow_mode": True}, "questions": [],
        "answers": [], "findings": [], "unresolved_items": [], "advisor_comments": [],
        "test_results": [], "multi_advisor_comparison": {"disagreements": ["Different risk view"]}}
    synthesis = FinalSynthesizer().synthesize(case)
    assert synthesis["multi_advisor_comparison"]["disagreements"] == ["Different risk view"]


def test_governor_daily_research_spend_is_read_from_reconciled_reservations(tmp_path, monkeypatch):
    from nexus_agent_platform.resource_spend_governor import LocalGovernorStore
    from nexus_agent_platform.research_room.advisor_router import _current_daily_research_spend
    monkeypatch.setenv("NEXUS_GOVERNOR_DB", str(tmp_path / "governor.sqlite3"))
    monkeypatch.setenv("NEXUS_JOB_BUDGET", '{"max_requests":5,"max_tokens":5000,"max_estimated_cost":0.01}')
    store = LocalGovernorStore(tmp_path / "governor.sqlite3")
    limits = {"rate": {}, "usage": {"requests": 10, "tokens": 20000},
        "money": {"per_job": 0.05, "per_day": 0.05, "per_month": 0.5}}
    store.set_policy("OPENROUTER", "research_room_advisor", "RESEARCH_ROOM_SHADOW_ADVISOR", "DAILY",
        autonomous_usage_allowed=True, autonomous_spend_allowed=True, soft_limits=limits,
        hard_limits=limits, state="NORMAL", approval_required=False)
    reservation = store.reserve("OPENROUTER", "research_room_advisor", "RESEARCH_ROOM_SHADOW_ADVISOR",
        "daily-spend-test", {"requests": 1, "cost": 0.001, "billable": True})
    store.reconcile(reservation["reservation_id"], {"requests": 1, "cost": 0.0007})
    assert _current_daily_research_spend() == pytest.approx(0.0007)


def test_high_value_case_tries_lower_cost_default_before_strong_model(monkeypatch):
    from nexus_agent_platform.research_room.advisor_router import (
        AdvisorRouter, OpenRouterHostedAdvisor, StrongOpenRouterAdvisor)
    strong, default = StrongOpenRouterAdvisor(), OpenRouterHostedAdvisor()
    calls = []
    monkeypatch.setattr(strong, "ask", lambda **_kwargs: (_ for _ in ()).throw(AssertionError("strong route called")))
    monkeypatch.setattr(default, "ask", lambda **_kwargs: calls.append("default") or {
        "status": "COMPLETED", "provider": "OPENROUTER", "model": default.model,
        "usage": {"input_tokens": 10, "output_tokens": 10, "total_tokens": 20},
        "estimated_cost_usd": 0.000005, "duration_ms": 5, "analysis": "bounded result"})
    case = {"case_id": "cost-route", "original_request": "Assess a complex opportunity",
        "source_report": {"text": "Short source."}, "metadata": {"research_complexity": "HIGH",
            "per_call_soft_target_usd": 0.001, "per_case_soft_target_usd": 0.01,
            "daily_research_soft_target_usd": 0.03, "daily_research_spend_usd": 0.0}}
    result = AdvisorRouter([strong, default]).ask(role="ADVISOR", case_context=case, objective="Assess")
    assert result["status"] == "COMPLETED"
    assert result["model"] == default.model
    assert calls == ["default"]
    assert case["model_usage"]["calls"][0]["tier"] == 4

