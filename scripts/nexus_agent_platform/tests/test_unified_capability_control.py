from nexus_agent_platform.unified_capability_control import failure_learning, select_candidate


def test_engineering_selection_compares_internal_and_opencode(tmp_path, monkeypatch):
    result = select_candidate(task_id="r12-engineering", goal_id="g", criterion_id="c", goal="Portal engineering", criterion="implement a safe code fix", persist=False)
    assert len(result["candidates_discovered"]) >= 2
    assert result["selected_worker"] in {"nexus_ai_workforce", "opencode"}
    assert result["candidates_scored"]
    assert result["skill_selection"]["skills_selected"]


def test_requirements_and_selection_are_receipted():
    result = select_candidate(task_id="r12-research", goal_id="g", criterion_id="c", goal="Opportunity", criterion="research current pricing", persist=False)
    assert result["requirements"]["capability_classes"] == ["RESEARCH"]
    assert result["selected_tool"] in {"research.alpha", "oracle.browser.read"}


def test_failure_requires_material_delta_and_can_change_skill_tool_worker():
    old = {"failure_fingerprint": "x", "strategy": "plan", "tool": "artifact", "worker": "internal", "skills": ["repo-intelligence"]}
    result = failure_learning(old, new_strategy="execute", new_skills=["test-debugging"], new_tool="tests.run", new_worker="opencode")
    assert result["retry_allowed"] is True
    assert {"test-debugging", "tests.run", "opencode"}.issubset(set(result["material_delta"]))
