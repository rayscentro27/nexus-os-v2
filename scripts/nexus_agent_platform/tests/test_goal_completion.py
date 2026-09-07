from nexus_agent_platform.goal_completion import (
    active_objective_portfolio, build_goal, classify_path_failure,
    evaluate_parent_goal, evaluate_terminal_closure, repetition_guard, should_continue,
    next_work_for_active_goal,
    select_portfolio_goal,
)
import json


def test_report_or_child_completion_does_not_complete_parent_goal():
    goal = build_goal("stock-data", "Establish real stock data", ["real_source", "normalized_read"])
    result = evaluate_parent_goal(goal, {"satisfied_criteria": ["real_source"]})
    assert result["status"] == "ACTIVE"
    assert result["missing_criteria"] == ["normalized_read"]


def test_failure_classification_and_alternative_path_continue_parent():
    goal = build_goal("market", "Complete market data", ["source"], candidate_next_paths=("API", "ORACLE_BROWSER"))
    failure = classify_path_failure({"path": "YAHOO_API", "error": "endpoint unavailable", "known_alternatives": ["ORACLE_BROWSER"]})
    assert failure["failure_class"] == "DATA_NOT_AVAILABLE"
    decision = should_continue(goal, failure=failure, attempted_paths=["YAHOO_API"])
    assert decision["parent_goal_complete"] is False
    assert decision["next_action"]["action"] == "API"


def test_repetition_guard_switches_strategy_after_identical_failure():
    decision = repetition_guard([{"path": "dead_api", "arguments": {"symbol": "SPY"}, "result": "blocked"}] * 3)
    assert decision["repeated"] is True
    assert decision["action"] == "CHANGE_STRATEGY"


def test_portfolio_keeps_multiple_parent_goals_active():
    portfolio = active_objective_portfolio()
    assert len(portfolio) >= 7
    assert {"trading.real_data", "research.company_intelligence", "portal.client_beta"}.issubset({row["goal_id"] for row in portfolio})
    assert {row["status"] for row in portfolio}.issubset({"ACTIVE", "READY", "QUEUED"})


def test_open_parent_goal_materializes_general_internal_work():
    goal = active_objective_portfolio()[0]
    work = next_work_for_active_goal(goal, work_item_id="cycle-1", question="Find the next evidence gap")
    assert work["dispatch"] == "CREATE_OR_REUSE_WORK_ORDER"
    assert work["continue_parent"] is True
    assert work["authority"] == "INTERNAL_SAFE"


def test_selection_does_not_starve_older_lower_priority_goal():
    rows = [
        {"goal_id": "p1-open", "status": "ACTIVE", "priority": "P1", "selection_count": 8, "consecutive_selections": 1, "last_selected_at": "2026-09-05T00:00:00+00:00"},
        {"goal_id": "p2-open", "status": "ACTIVE", "priority": "P2", "selection_count": 0, "consecutive_selections": 0, "last_selected_at": None},
    ]
    selected = select_portfolio_goal(rows)
    assert selected["goal_id"] == "p2-open"


def test_selection_promotes_never_run_eligible_cohort_over_repeated_p2_work():
    rows = [
        {"goal_id": "p2-open", "status": "ACTIVE", "priority": "P2", "selection_count": 5, "consecutive_selections": 0, "last_selected_at": "2026-09-06T00:00:00+00:00"},
        {"goal_id": "p3-new", "status": "READY", "priority": "P3", "selection_count": 0, "consecutive_selections": 0, "last_selected_at": None},
    ]
    assert select_portfolio_goal(rows)["goal_id"] == "p3-new"


def test_goal_action_uses_existing_non_research_executors():
    trading = {"goal_id": "t", "status": "ACTIVE", "department": "Trading", "statement": "trade research", "priority": "P1"}
    portal = {"goal_id": "p", "status": "ACTIVE", "department": "Portal/Product", "statement": "portal", "priority": "P2"}
    assert next_work_for_active_goal(trading, work_item_id="t1", question="q")["action"] == "trading.research_cycle"
    assert next_work_for_active_goal(portal, work_item_id="p1", question="q")["action"] == "ai.plan_and_verify"


def test_safe_ai_executor_covers_customer_service_documents_and_systems():
    for department in ("Customer Service", "Documents", "Nexus/Systems"):
        goal = {"goal_id": department, "status": "READY", "department": department, "statement": "internal work", "priority": "P3"}
        assert next_work_for_active_goal(goal, work_item_id=f"{department}-1", question="q")["action"] == "ai.plan_and_verify"


def test_goal_action_uses_existing_safe_funding_fixture_executor():
    funding = {"goal_id": "f", "status": "ACTIVE", "department": "Funding/Product", "statement": "funding readiness", "priority": "P2"}
    assert next_work_for_active_goal(funding, work_item_id="f1", question="q")["action"] == "funding.readiness_review"


def test_existing_campaign_package_reaches_human_review_closure():
    goal = {"goal_id": "goclear.example_campaign", "status": "ACTIVE",
            "success_criteria": ["Research and Marketing rationale recorded",
                                 "Creative campaign package exists",
                                 "publication remains approval-gated"]}
    closure = evaluate_terminal_closure(goal)
    assert closure["status"] == "READY_FOR_HUMAN_REVIEW"
    assert closure["artifact_id"]
    assert closure["external_action_performed"] is False


def test_unverified_goal_does_not_close_from_a_child_receipt():
    goal = {"goal_id": "media.youtube_video", "status": "ACTIVE"}
    assert evaluate_terminal_closure(goal)["status"] == "ACTIVE"


def test_generic_final_deliverable_contract_is_reusable(tmp_path, monkeypatch):
    import nexus_agent_platform.goal_completion as completion
    artifact = tmp_path / "final.json"
    artifact.write_text(json.dumps({
        "schema_version": "nexus.final-deliverable.v1",
        "artifact_id": "final-real-goal-1",
        "goal_id": "portal.admin_control_center",
        "status": "READY_FOR_HUMAN_REVIEW",
        "criteria_satisfied": ["audit", "admin state readable"],
        "final_evaluation": {"verified": True, "result": "PASS"},
        "external_action_performed": False,
        "human_action": "Review the internal control-center package.",
    }), encoding="utf-8")
    monkeypatch.setattr(completion, "ROOT", tmp_path)
    goal = {"goal_id": "portal.admin_control_center", "status": "ACTIVE",
            "success_criteria": ["audit", "admin state readable"],
            "current_evidence": ["final.json"]}
    closure = completion.evaluate_terminal_closure(goal)
    assert closure["status"] == "READY_FOR_HUMAN_REVIEW"
    assert closure["artifact_id"] == "final-real-goal-1"


def test_existing_progress_requests_finalization_after_intermediate_work():
    goal = {"goal_id": "portal.admin_control_center", "status": "ACTIVE",
            "department": "Portal/Product", "current_evidence": ["reports/runtime/x.json"],
            "last_result": {"action": "internal.create_bounded_work_artifact"},
            "missing_criteria": ["audit"]}
    work = next_work_for_active_goal(goal, work_item_id="w1", question="assemble the real final package")
    assert work["productive_action"] == "internal.assemble_final_deliverable"
    assert work["finalization_requested"] is True


def test_rework_goal_is_prioritized_over_new_exploration():
    from nexus_agent_platform.goal_completion import select_portfolio_goal
    rows = [
        {"goal_id": "new", "status": "ACTIVE", "priority": "P1", "selection_count": 0},
        {"goal_id": "rework", "status": "ACTIVE", "priority": "P2", "selection_count": 10,
         "last_result": {"rework_required": ["missing final section"]}},
    ]
    selected = select_portfolio_goal(rows)
    assert selected["goal_id"] == "rework"
