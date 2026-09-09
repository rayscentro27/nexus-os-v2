from nexus_agent_platform.unified_capability_control import Candidate, failure_learning, filter_candidates, select_candidate
from nexus_agent_platform.downstream_continuation import next_action_after_result
from nexus_agent_platform.hermes_kanban_executor import execute_with_hermes_kanban
from nexus_agent_platform.unified_capability_control import execute_selected_candidate
from nexus_agent_platform.adaptive_hermes_routing import ModelRoute, score_route, validate_criterion_evidence


def test_engineering_selection_compares_internal_and_opencode(tmp_path, monkeypatch):
    result = select_candidate(task_id="r12-engineering", goal_id="g", criterion_id="c", goal="Portal engineering", criterion="implement a safe code fix", persist=False)
    assert len(result["candidates_discovered"]) >= 2
    assert result["selected_worker"] in {"nexus_ai_workforce", "opencode"}
    assert result["candidates_scored"]
    assert result["skill_selection"]["skills_selected"]


def test_requirements_and_selection_are_receipted():
    result = select_candidate(task_id="r12-research", goal_id="g", criterion_id="c", goal="Opportunity", criterion="research current pricing", persist=False)
    assert result["requirements"]["capability_classes"] == ["RESEARCH"]
    assert result["selected_tool"] in {"research.alpha", "oracle.browser.read", "hermes.kanban.executor"}


def test_failure_requires_material_delta_and_can_change_skill_tool_worker():
    old = {"failure_fingerprint": "x", "strategy": "plan", "tool": "artifact", "worker": "internal", "skills": ["repo-intelligence"]}
    result = failure_learning(old, new_strategy="execute", new_skills=["test-debugging"], new_tool="tests.run", new_worker="opencode")
    assert result["retry_allowed"] is True
    assert {"test-debugging", "tests.run", "opencode"}.issubset(set(result["material_delta"]))


def test_selector_negative_paths_reject_unready_candidates():
    bad = Candidate("bad", "unsafe", "LOCAL", (), 1, 0, 0, 0, 0, 0, 0, 1, 1, 1, 0, 1, authorized=False)
    good = Candidate("good", "safe", "LOCAL", (), 1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 1)
    qualified, rejected = filter_candidates([bad, good], {"privacy": "INTERNAL_SAFE"})
    assert [c.worker for c in qualified] == ["good"]
    assert set(rejected[0]["reasons"]) >= {"AUTHORITY", "WORKER_ACCESS", "REAL_TEST_REQUIRED", "PRIVACY"}


def test_failure_memory_changes_task_scoped_selection_score():
    clean = select_candidate(task_id="clean", goal_id="g", criterion_id="c", goal="Portal engineering", criterion="implement a safe code fix", persist=False)
    failed = select_candidate(task_id="failed", goal_id="g", criterion_id="c", goal="Portal engineering", criterion="implement a safe code fix", failure_memory=[{"worker": "nexus_ai_workforce", "tool": "engineering.portal_beta"}], persist=False)
    clean_score = next(x["score"] for x in clean["candidates_scored"] if x["worker"] == "nexus_ai_workforce")
    failed_score = next(x["score"] for x in failed["candidates_scored"] if x["worker"] == "nexus_ai_workforce")
    assert failed_score < clean_score


def test_evidence_failure_compiles_different_downstream_action():
    result = next_action_after_result(result={"status": "FAILED", "action": "research.refresh", "failure_class": "EVIDENCE_INSUFFICIENT", "result_count": 0}, previous={"tool": "research.refresh"})
    assert result["decision"] == "RESEARCH_MORE_WITH_DIFFERENT_METHOD"
    assert result["next_action"] == "research.alternate_public"
    assert set(result["material_delta"]) >= {"SOURCE_CLASS", "QUERY_STRATEGY", "TOOL"}


def test_hermes_is_a_normal_candidate_for_research():
    result = select_candidate(task_id="r15-7", goal_id="opportunity.engine", criterion_id="c", goal="Opportunity", criterion="research current public evidence", persist=False)
    assert any(row["tool"] == "hermes.kanban.executor" for row in result["candidates_discovered"])


def test_hermes_executor_uses_create_dispatch_show_and_normalizes_result():
    calls = []
    responses = [
        {"id": "hk-1", "status": "READY"},
        {"dispatched": 1},
        {"id": "hk-1", "status": "COMPLETED", "result": "evidence", "artifacts": ["a"]},
    ]
    def runner(command, timeout):
        calls.append(command)
        return responses.pop(0)
    result = execute_with_hermes_kanban({"goal_id":"g", "criterion_id":"c", "task_id":"t", "task_requirements":{"capability_classes":["RESEARCH"]}, "profile":"nexus_research_test", "skills":["research-intelligence"], "instruction":"read-only evidence"}, runner=runner)
    assert result["status"] == "COMPLETED"
    assert result["material_delta"] is True
    assert "create" in calls[0] and "dispatch" in calls[1] and "show" in calls[2]


def test_executor_maps_nexus_skill_to_installed_hermes_skill():
    calls = []
    responses = [{"id": "hk-2", "status": "READY"}, {"dispatched": 1}, {"task": {"id": "hk-2", "status": "completed", "result": "ok"}}]
    def runner(command, timeout):
        calls.append(command)
        return responses.pop(0)
    execute_with_hermes_kanban({"goal_id":"g", "criterion_id":"c", "task_id":"t", "task_requirements":{}, "profile":"nexus_research_test", "skills":["research-intelligence"]}, runner=runner)
    assert "--skill sdlc-review" in calls[0]


def test_hermes_executor_rejects_non_internal_authority():
    try:
        execute_with_hermes_kanban({"goal_id":"g", "criterion_id":"c", "task_id":"t", "task_requirements":{}, "authority_class":"EXTERNAL"}, runner=lambda *_: {})
    except Exception as exc:
        assert type(exc).__name__ == "HermesKanbanExecutionError"
    else:
        raise AssertionError("external authority was accepted")


def test_normal_executor_boundary_routes_selected_hermes_candidate(monkeypatch):
    seen = {}
    def fake(spec):
        seen.update(spec)
        return {"status": "COMPLETED", "material_delta": True}
    monkeypatch.setattr("nexus_agent_platform.hermes_kanban_executor.execute_with_hermes_kanban", fake)
    result = execute_selected_candidate({"selected_tool": "hermes.kanban.executor", "selected_skills": ["research-intelligence"]}, {"goal_id":"g", "criterion_id":"c", "task_id":"t", "task_requirements":{}})
    assert result["status"] == "COMPLETED"
    assert seen["skills"] == ["research-intelligence"]


def test_slow_model_failure_is_penalized_and_prose_is_not_evidence():
    route = ModelRoute("openrouter", "nvidia/nemotron-3.5-lightning:free", "nexus_research_test", True, True, True, "READY", 51)
    assert score_route(route, "RESEARCH", [{"fingerprint": "wrong"}]) > 0
    invalid = validate_criterion_evidence("task complete", "opportunity.engine", "opportunity-scoring", "t")
    assert invalid["valid"] is False and invalid["reason"] == "PASS_WITHOUT_MATERIAL_DELTA"
