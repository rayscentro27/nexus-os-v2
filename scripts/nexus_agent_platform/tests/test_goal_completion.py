from nexus_agent_platform.goal_completion import (
    active_objective_portfolio, build_goal, classify_path_failure,
    evaluate_parent_goal, repetition_guard, should_continue,
    next_work_for_active_goal,
    select_portfolio_goal,
)


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


def test_goal_action_uses_existing_non_research_executors():
    trading = {"goal_id": "t", "status": "ACTIVE", "department": "Trading", "statement": "trade research", "priority": "P1"}
    portal = {"goal_id": "p", "status": "ACTIVE", "department": "Portal/Product", "statement": "portal", "priority": "P2"}
    assert next_work_for_active_goal(trading, work_item_id="t1", question="q")["action"] == "trading.research_cycle"
    assert next_work_for_active_goal(portal, work_item_id="p1", question="q")["action"] == "internal.capability_verify"
