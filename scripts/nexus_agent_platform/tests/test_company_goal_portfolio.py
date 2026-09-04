import json
from datetime import datetime, timezone


def test_company_portfolio_persists_full_roadmap(tmp_path, monkeypatch):
    from nexus_agent_platform import goal_completion as goals

    monkeypatch.setattr(goals, "PORTFOLIO_PATH", tmp_path / "company_goal_portfolio.json")
    rows = goals.ensure_company_goal_portfolio()
    assert len(rows) == 23
    assert {row["goal_id"] for row in rows}.issuperset({
        "trading.real_data", "research.company_intelligence", "portal.client_beta",
        "portal.admin_control_center", "goclear.example_campaign",
        "systems.modal_verification", "systems.oracle_browser",
        "clyde.entity_readiness", "commerce.billing_accounting",
        "nexus.productization",
    })
    assert all(row["success_criteria"] and row["missing_criteria"] for row in rows)
    assert json.loads((tmp_path / "company_goal_portfolio.json").read_text()) == rows


def test_dependency_gated_productization_is_not_presented_as_ready(tmp_path, monkeypatch):
    from nexus_agent_platform import goal_completion as goals

    monkeypatch.setattr(goals, "PORTFOLIO_PATH", tmp_path / "company_goal_portfolio.json")
    rows = goals.ensure_company_goal_portfolio()
    product = next(row for row in rows if row["goal_id"] == "nexus.productization")
    assert product["status"] == "PLANNED_DEPENDENCY"
    assert product not in goals.active_objective_portfolio()


def test_portfolio_governor_rotates_after_consecutive_selection(tmp_path, monkeypatch):
    from nexus_agent_platform import goal_completion as goals

    monkeypatch.setattr(goals, "PORTFOLIO_PATH", tmp_path / "company_goal_portfolio.json")
    rows = goals.ensure_company_goal_portfolio()
    current = [row for row in rows if row["goal_id"] in {"trading.real_data", "research.company_intelligence"}]
    first = goals.select_portfolio_goal(current, now=datetime(2026, 9, 4, tzinfo=timezone.utc))
    second = goals.select_portfolio_goal(current, now=datetime(2026, 9, 4, 0, 1, tzinfo=timezone.utc))
    assert first and second
    assert first["goal_id"] != second["goal_id"]


def test_company_goal_capability_is_read_only_and_summarized(tmp_path, monkeypatch):
    from nexus_agent_platform import goal_completion as goals
    from nexus_agent_platform.capabilities import shared

    monkeypatch.setattr(goals, "PORTFOLIO_PATH", tmp_path / "company_goal_portfolio.json")
    result = shared.execute_shared_capability("hermes_nova", "get_company_goal_portfolio", {}, trace_id="test")
    assert result["status"] == "success"
    assert result["data"]["total_goals"] == 23
    assert result["access_boundary"] == "approved read capability only"
    assert "get_company_goal_portfolio" in shared.NOVA_ALLOWED_READS
