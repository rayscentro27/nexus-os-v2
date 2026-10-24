from __future__ import annotations

import sys
from pathlib import Path
import pytest
import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT))

from nexus_agent_platform import research_assignment_executor as executor
from nexus_agent_platform.research_assignment_intent import (
    assignment_job_type,
    classify_research_assignment,
    governor_policy_job_type,
    research_objective_type,
    result_contract,
)
from nexus_agent_platform.research_work_queue import ResearchWorkQueue


def test_runtime_inspection_is_not_public_search(monkeypatch):
    intent = classify_research_assignment(
        "Nova, perform a real Nexus runtime readiness inspection for Research"
    )
    assert intent == "RESEARCH_RUNTIME_INSPECTION"
    assert assignment_job_type(intent) == "RESEARCH_RUNTIME_INSPECT"
    monkeypatch.setattr(executor, "inspect_research_runtime", lambda: {
        "status": "PASS", "requested_intent": intent, "routed_intent": intent,
        "execution_path": "READ_ONLY_RESEARCH_RUNTIME_INSPECTOR",
        "task_fulfillment": result_contract(requested_intent=intent, routed_intent=intent,
            execution_path="READ_ONLY_RESEARCH_RUNTIME_INSPECTOR", status="COMPLETED", result={"checks": True}),
        "public_search_performed": False,
    })
    result = executor.execute_assignment({"requested_intent": intent, "objective": "inspect runtime"},
                                         public_search=lambda _: (_ for _ in ()).throw(AssertionError("search invoked")))
    assert result["execution_path"] == "READ_ONLY_RESEARCH_RUNTIME_INSPECTOR"
    assert result["public_search_performed"] is False


def test_notebooklm_auth_and_needle_availability_are_runtime_inspection(monkeypatch):
    intent = classify_research_assignment("Check NotebookLM authentication and Needle availability")
    assert intent == "RESEARCH_RUNTIME_INSPECTION"
    called = []
    monkeypatch.setattr(executor, "inspect_research_runtime", lambda: called.append(True) or {
        "execution_path": "READ_ONLY_RESEARCH_RUNTIME_INSPECTOR", "public_search_performed": False,
        "task_fulfillment": {"task_fulfilled": False, "execution_path": "READ_ONLY_RESEARCH_RUNTIME_INSPECTOR"},
    })
    executor.execute_assignment({"requested_intent": intent, "objective": "check runtime"},
                                public_search=lambda _: (_ for _ in ()).throw(AssertionError("search invoked")))
    assert called == [True]


def test_research_mission_enters_intake_and_selects_source_capability(monkeypatch):
    intent = classify_research_assignment("Research TikTok Shop profitability")
    assert intent == "RESEARCH_MISSION"
    assert assignment_job_type(intent) == "RESEARCH_INTAKE"
    from research import research_case_engine
    import research.notebook_playbook_runner as playbook
    monkeypatch.setattr(research_case_engine, "open_or_join_case", lambda **kwargs: {
        "case": {"case_id": "case-test", "objective": kwargs["objective"],
                 "objective_family": kwargs["objective_family"]}})
    monkeypatch.setattr(research_case_engine, "get_case", lambda case_id: {
        "case_id": case_id, "objective": "Research TikTok Shop profitability",
        "objective_family": "BUSINESS_OPPORTUNITIES"})
    calls = []
    monkeypatch.setattr(playbook, "run_case_playbook", lambda case_id, **kwargs:
        calls.append((case_id, kwargs)) or {"ok": True, "notebook_id": "dedicated-test"})
    result = executor.execute_assignment({"requested_intent": intent,
        "objective": "Research TikTok Shop profitability", "original_source_type": "YOUTUBE"},
        public_search=lambda _: (_ for _ in ()).throw(AssertionError("mission became search")))
    assert result["execution_path"] == "RESEARCH_INTAKE"
    assert result["task_fulfillment"]["task_fulfilled"] is False
    assert result["task_fulfillment"]["routing_blocker"] == "RESEARCH_CONTINUATION_REQUIRED"
    assert result["case_id"] == "case-test"
    assert result["notebook_id"] == "dedicated-test"
    assert calls[0][0] == "case-test"
    assert result["research_intake"]["notebooklm_selected"] is True


def test_explicit_web_search_is_the_only_public_search_route():
    intent = classify_research_assignment("Search the web for Shopify affiliate programs")
    assert intent == "PUBLIC_RESEARCH_SEARCH"
    called = []
    result = executor.execute_assignment({"requested_intent": intent,
        "question": "Search the web for Shopify affiliate programs"},
        public_search=lambda question: called.append(question) or {"sources": ["https://shopify.com"]})
    assert called == ["Search the web for Shopify affiliate programs"]
    assert result["public_search_performed"] is True
    assert result["task_fulfillment"]["task_fulfilled"] is True


def test_notebooklm_operation_does_not_fall_through_to_search():
    intent = classify_research_assignment(
        "Add https://example.com/source to the existing NotebookLM notebook abc"
    )
    assert intent == "NOTEBOOKLM_OPERATION"
    result = executor.execute_assignment({"requested_intent": intent,
        "question": "Add https://example.com/source", "source_url": "https://example.com/source"},
        public_search=lambda _: (_ for _ in ()).throw(AssertionError("search invoked")))
    assert result["execution_path"] == "NOTEBOOKLM_GOVERNED_ADAPTER"
    assert result["task_fulfillment"]["task_fulfilled"] is False
    assert "NOTEBOOK_ID_REQUIRED" in result["reason"]


def test_semantic_job_types_reuse_existing_scoped_governor_policy():
    assert governor_policy_job_type("RESEARCH_RUNTIME_INSPECT", nova_research_assignment=True) == "RESEARCH_GAP_VERIFY"
    assert governor_policy_job_type("NOTEBOOKLM_RESEARCH", nova_research_assignment=True) == "RESEARCH_GAP_VERIFY"
    assert governor_policy_job_type("NOTEBOOKLM_RESEARCH", nova_research_assignment=False) == "NOTEBOOKLM_RESEARCH"


def test_status_query_reads_existing_job_without_creating_mission(monkeypatch):
    from services.nexus_mcp import server
    class Existing:
        job_id = "abc"
        job_type = "NOTEBOOKLM_RESEARCH"
        state = "COMPLETED"
        created_at = claimed_at = completed_at = claimed_by = receipt_ref = None
        attempt_count = 1

    class Store:
        def get(self, job_id):
            assert job_id == "abc"
            return Existing()

        def enqueue(self, *args, **kwargs):
            raise AssertionError("status query enqueued a job")

    monkeypatch.setattr("nexus_agent_platform.durable_jobs.default_store", lambda: Store())
    result = server._assign_research("Check status of research job abc", "Check status of research job abc")
    assert result["status"] == "read_only_result"
    assert result["job_created"] is False
    assert result["job_id"] == "abc"


def test_runtime_inspection_assignment_gets_semantic_job_type(monkeypatch, tmp_path):
    from services.nexus_mcp import server
    from types import SimpleNamespace
    from nexus_agent_platform import research_work_queue
    monkeypatch.setattr(research_work_queue, "ResearchWorkQueue",
                        lambda: ResearchWorkQueue(tmp_path / "queue.json"))
    class Store:
        def enqueue(self, department, job_type, **kwargs):
            assert department == "RESEARCH"
            assert job_type == "RESEARCH_RUNTIME_INSPECT"
            assert kwargs["governance_context"]["requested_intent"] == "RESEARCH_RUNTIME_INSPECTION"
            return SimpleNamespace(job_id="job-runtime-test", state="READY")
    monkeypatch.setattr("nexus_agent_platform.durable_jobs.default_store", lambda: Store())
    result = server._assign_research(
        "Nova, perform a real Nexus runtime readiness inspection for Research",
        "Inspect Research runtime, governor, NotebookLM integration, and Needle availability.")
    queued = ResearchWorkQueue(tmp_path / "queue.json").load()["items"][0]
    assert result["job_type"] == "RESEARCH_RUNTIME_INSPECT"
    assert queued["requested_intent"] == "RESEARCH_RUNTIME_INSPECTION"


def test_operational_instruction_with_research_word_is_not_search():
    for text in (
        "Inspect Research runtime and governor",
        "Check NotebookLM authentication and Needle availability",
        "Nova, perform a real Nexus runtime readiness inspection for Research",
    ):
        assert classify_research_assignment(text) == "RESEARCH_RUNTIME_INSPECTION"


def test_wrong_path_cannot_be_marked_fulfilled():
    result = result_contract(requested_intent="RESEARCH_RUNTIME_INSPECTION",
        routed_intent="PUBLIC_RESEARCH_SEARCH", execution_path="SEARXNG",
        status="COMPLETED", result={"results": ["unrelated"]})
    assert result["task_fulfilled"] is False
    assert result["routing_blocker"] == "INTENT_ROUTE_MISMATCH"
    same_intent_wrong_path = result_contract(requested_intent="RESEARCH_RUNTIME_INSPECTION",
        routed_intent="RESEARCH_RUNTIME_INSPECTION", execution_path="SEARXNG",
        status="COMPLETED", result={"results": ["unrelated"]})
    assert same_intent_wrong_path["task_fulfilled"] is False
    assert same_intent_wrong_path["routing_blocker"] == "EXECUTION_PATH_MISMATCH"


def test_assignment_metadata_survives_research_queue_normalization():
    item = ResearchWorkQueue.normalize({"work_id": "intent-1", "work_class": "ASSIGNED",
        "requested_intent": "RESEARCH_RUNTIME_INSPECTION", "notebook_operation": "ASK",
        "notebook_prompt": "Check the existing notebook.",
        "routed_intent": "RESEARCH_RUNTIME_INSPECTION",
        "execution_path": "READ_ONLY_RESEARCH_RUNTIME_INSPECTOR",
        "objective_type": "RUNTIME_INSPECTION", "research_scope": "Inspect Research runtime.",
        "original_objective": "Preserve my full mission", "original_source_url": "https://example.com",
        "original_source_type": "WEB_PAGE", "current_research_context": {"stage": "RESEARCH_INTAKE"}})
    assert item["requested_intent"] == "RESEARCH_RUNTIME_INSPECTION"
    assert item["routed_intent"] == "RESEARCH_RUNTIME_INSPECTION"
    assert item["execution_path"] == "READ_ONLY_RESEARCH_RUNTIME_INSPECTOR"
    assert item["objective_type"] == "RUNTIME_INSPECTION"
    assert item["research_scope"] == "Inspect Research runtime."
    assert item["original_objective"] == "Preserve my full mission"
    assert item["original_source_url"] == "https://example.com"
    assert item["original_source_type"] == "WEB_PAGE"
    assert item["current_research_context"]["stage"] == "RESEARCH_INTAKE"
    assert item["notebook_operation"] == "ASK"
    assert item["notebook_prompt"] == "Check the existing notebook."


@pytest.mark.parametrize("prompt,objective_type", [
    ("Research livestorebuild.com and tell me whether Nexus should use it, partner with it, copy the model, or avoid it.",
     "BUSINESS_OPPORTUNITY"),
    ("Research the latest five videos from this forex YouTube channel and tell me whether anything can improve Nexus Trading.",
     "TRADING_INTELLIGENCE"),
])
def test_natural_missions_keep_intent_and_grouped_execution(prompt, objective_type, monkeypatch):
    intent = classify_research_assignment(prompt)
    assert intent == "RESEARCH_MISSION"
    assert research_objective_type(prompt) == objective_type
    assert assignment_job_type(intent) == "RESEARCH_INTAKE"

    from research import research_case_engine
    import research.notebook_playbook_runner as playbook
    monkeypatch.setattr(research_case_engine, "open_or_join_case", lambda **kwargs: {
        "case": {"case_id": "case-natural", "objective_family": kwargs["objective_family"]}})
    monkeypatch.setattr(research_case_engine, "get_case", lambda case_id: {
        "case_id": case_id, "objective_family": "TRADING_INTELLIGENCE" if objective_type == "TRADING_INTELLIGENCE"
        else "BUSINESS_OPPORTUNITIES"})
    monkeypatch.setattr(playbook, "run_case_playbook", lambda case_id, **kwargs:
        {"ok": True, "notebook_id": "notebook-fixture"})
    work = ResearchWorkQueue.normalize({"work_id": "natural-mission", "work_class": "ASSIGNED",
        "objective": prompt, "question": prompt, "requested_intent": intent,
        "routed_intent": intent, "execution_path": "RESEARCH_INTAKE",
        "objective_type": objective_type, "research_scope": prompt})
    result = executor.execute_assignment(work,
        public_search=lambda _: (_ for _ in ()).throw(AssertionError("mission became a public search")))
    assert result["requested_intent"] == "RESEARCH_MISSION"
    assert result["routed_intent"] == "RESEARCH_MISSION"
    assert result["execution_path"] == "RESEARCH_INTAKE"
    assert result["task_fulfillment"]["task_fulfilled"] is False
    assert result["task_fulfillment"]["routing_blocker"] == "RESEARCH_CONTINUATION_REQUIRED"


def test_generic_research_execution_is_not_encoded_as_gap_verification():
    assert assignment_job_type("RESEARCH_EXECUTION") == ""
    assert assignment_job_type("RESEARCH_GAP_VERIFY") == "RESEARCH_GAP_VERIFY"


def test_research_intake_selects_notebooklm_only_for_source_digestion():
    from nexus_agent_platform.research_assignment_executor import select_intake_capabilities
    website = select_intake_capabilities({"original_objective": "Assess vendor", "source_type": "WEB_PAGE",
        "source_url": "https://example.com", "current_research_context": {"stage": "RESEARCH_INTAKE"}})
    video = select_intake_capabilities({"original_objective": "Research latest five videos", "source_type": "YOUTUBE"})
    assert website["entry_path"] == video["entry_path"] == "RESEARCH_INTAKE"
    assert website["notebooklm_selected"] is False
    assert video["notebooklm_selected"] is True
    assert website["classification_required_before_start"] is False


def test_source_metadata_preserves_bare_website_and_youtube_channel_url():
    from services.nexus_mcp import server
    assert server._research_source_metadata("Research livestorebuild.com for Nexus") == {
        "source_url": "https://livestorebuild.com", "source_type": "WEB_PAGE"}
    assert server._research_source_metadata("Research https://youtube.com/@sample/videos") == {
        "source_url": "https://youtube.com/@sample/videos", "source_type": "YOUTUBE_CHANNEL"}


def test_mcp_assignment_persists_semantic_intent_through_durable_and_queue(monkeypatch, tmp_path):
    from services.nexus_mcp import server
    from types import SimpleNamespace
    from nexus_agent_platform import research_work_queue

    queue_path = tmp_path / "queue.json"
    monkeypatch.setattr(research_work_queue, "ResearchWorkQueue",
                        lambda: ResearchWorkQueue(queue_path))
    captured = {}

    class Store:
        def enqueue(self, department, job_type, **kwargs):
            captured.update(department=department, job_type=job_type, **kwargs)
            return SimpleNamespace(job_id="job-fixture", state="READY")

    monkeypatch.setattr("nexus_agent_platform.durable_jobs.default_store", lambda: Store())
    prompt = "Research livestorebuild.com and tell me whether Nexus should use it, partner with it, copy the model, or avoid it."
    result = server._assign_research(prompt, prompt, parent_request_id="root-fixture",
                                     requested_intent="RESEARCH_MISSION")
    queued = ResearchWorkQueue(queue_path).load()["items"][0]
    context = captured["governance_context"]
    assert result["job_type"] == "RESEARCH_INTAKE"
    assert result["durable_job_id"] == "job-fixture"
    for record in (queued, context):
        assert record["requested_intent"] == "RESEARCH_MISSION"
        assert record["routed_intent"] == "RESEARCH_MISSION"
        assert record["execution_path"] == "RESEARCH_INTAKE"
        assert record["objective_type"] == "BUSINESS_OPPORTUNITY"
        assert record["research_scope"] == prompt
        assert record["original_objective"] == prompt
        assert record["original_source_url"] == "https://livestorebuild.com"
        assert record["original_source_type"] == "WEB_PAGE"
        assert record["current_research_context"]["stage"] == "RESEARCH_INTAKE"
    assert captured["job_type"] == "RESEARCH_INTAKE"


def test_mcp_honors_nova_classification_instead_of_reclassifying_free_text(monkeypatch, tmp_path):
    from services.nexus_mcp import server
    from types import SimpleNamespace
    from nexus_agent_platform import research_work_queue
    monkeypatch.setattr(research_work_queue, "ResearchWorkQueue",
                        lambda: ResearchWorkQueue(tmp_path / "queue.json"))

    class Store:
        def enqueue(self, department, job_type, **kwargs):
            assert job_type == "RESEARCH_INTAKE"
            assert kwargs["governance_context"]["requested_intent"] == "RESEARCH_MISSION"
            return SimpleNamespace(job_id="job-authoritative", state="READY")

    monkeypatch.setattr("nexus_agent_platform.durable_jobs.default_store", lambda: Store())
    prompt = "Research livestorebuild.com and assess whether Nexus should back it."
    # This wording is ambiguous to the legacy text classifier, but Nova's
    # already-resolved intent is authoritative across the MCP boundary.
    result = server._assign_research(prompt, prompt, requested_intent="RESEARCH_MISSION")
    assert result["requested_intent"] == "RESEARCH_MISSION"
    assert result["job_type"] == "RESEARCH_INTAKE"


def test_mcp_preserves_explicit_research_only_contract(monkeypatch, tmp_path):
    from services.nexus_mcp import server
    from types import SimpleNamespace
    from nexus_agent_platform import research_work_queue
    monkeypatch.setattr(research_work_queue, "ResearchWorkQueue",
                        lambda: ResearchWorkQueue(tmp_path / "queue.json"))
    captured = {}

    class Store:
        def enqueue(self, department, job_type, **kwargs):
            captured.update(department=department, job_type=job_type, **kwargs)
            return SimpleNamespace(job_id="job-research-only", state="READY")

    monkeypatch.setattr("nexus_agent_platform.durable_jobs.default_store", lambda: Store())
    prompt = "Read the official pathlib documentation and answer this bounded API question."
    result = server._assign_research(prompt, prompt, requested_intent="RESEARCH_ONLY")
    work = ResearchWorkQueue(tmp_path / "queue.json").load()["items"][0]
    assert result["requested_intent"] == "RESEARCH_ONLY"
    assert captured["job_type"] == "RESEARCH_INTAKE"
    assert captured["governance_context"]["requested_intent"] == "RESEARCH_ONLY"
    assert captured["governance_context"]["execution_path"] == "BOUNDED_RESEARCH_ONLY"
    assert work["requested_intent"] == "RESEARCH_ONLY"
    assert work["execution_path"] == "BOUNDED_RESEARCH_ONLY"


def test_worker_hydrates_scope_from_durable_envelope_without_text_reclassification():
    from nexus_agent_platform.job_worker_once import hydrate_research_assignment_scope
    work, error = hydrate_research_assignment_scope({"work_id": "w", "requested_intent": ""}, {
        "requested_intent": "RESEARCH_MISSION", "routed_intent": "RESEARCH_MISSION",
        "execution_path": "RESEARCH_INTAKE", "objective_type": "BUSINESS_OPPORTUNITY",
        "research_scope": "Evaluate this vendor."})
    assert error is None
    assert work["requested_intent"] == "RESEARCH_MISSION"
    assert work["routed_intent"] == "RESEARCH_MISSION"
    assert work["execution_path"] == "RESEARCH_INTAKE"
    assert work["objective_type"] == "BUSINESS_OPPORTUNITY"
    assert work["research_scope"] == "Evaluate this vendor."
    _, mismatch = hydrate_research_assignment_scope({"requested_intent": "RESEARCH_GAP_VERIFY"}, {
        "requested_intent": "RESEARCH_MISSION"})
    assert mismatch == "RESEARCH_INTENT_CONTRACT_MISMATCH"



@pytest.mark.parametrize("destination", ["TRADING", "MARKETING", "FUNDING", "SYSTEMS"])
def test_research_mission_destination_hint_does_not_gate_intake(monkeypatch, tmp_path, destination):
    from services.nexus_mcp import server
    from types import SimpleNamespace
    from nexus_agent_platform import research_work_queue

    queue_path = tmp_path / f"queue-{destination}.json"
    monkeypatch.setattr(research_work_queue, "ResearchWorkQueue",
                        lambda: ResearchWorkQueue(queue_path))
    jobs = []

    class Store:
        def enqueue(self, department, job_type, **kwargs):
            jobs.append((department, job_type, kwargs))
            return SimpleNamespace(job_id=f"job-{destination.lower()}", state="READY")

    monkeypatch.setattr("nexus_agent_platform.durable_jobs.default_store", lambda: Store())
    prompt = (
        "Nova, have Nexus research and review this TradingView strategy with the goal "
        "of preparing it for Nexus Trading to paper trade: "
        "https://www.tradingview.com/script/VFzCk3HX-TASC-2026-08-An-Ag-Selling-Model/ "
        "Verify the important claims and rules, identify questions Trading needs answered, "
        "and produce an actionable handoff. A poor result does not stop Research. "
        "Paper trading only; no live-money trading."
    )
    result = server._assign_research(prompt, prompt, requested_intent="RESEARCH_MISSION",
                                     followup_department=destination)

    assert result["status"] == "queued"
    assert result["requested_intent"] == "RESEARCH_MISSION"
    assert result["job_type"] == "RESEARCH_INTAKE"
    assert result["durable_job_state"] == "READY"
    assert len(jobs) == 1
    department, job_type, kwargs = jobs[0]
    assert department == "RESEARCH"
    assert job_type == "RESEARCH_INTAKE"
    assert kwargs["governance_context"]["execution_path"] == "RESEARCH_INTAKE"
    assert kwargs["governance_context"]["followup_department"] == ""
    queued = ResearchWorkQueue(queue_path).load()["items"]
    assert len(queued) == 1
    assert queued[0]["requested_intent"] == "RESEARCH_MISSION"
    assert queued[0]["followup_department"] is None
