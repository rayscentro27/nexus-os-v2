from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from nexus_agent_platform.executive_portfolio import (
    PortfolioObjective,
    build_trust_metrics,
    classify_blocker,
    plan_portfolio,
    portfolio_score,
    run_executive_portfolio_cycle,
)


def objective(objective_id, lane, status="READY", **kwargs):
    return PortfolioObjective(
        objective_id=objective_id, title=objective_id, lane=lane, business="GoClear",
        surface=objective_id, goal="advance", expected_outcome="bounded artifact",
        business_value=kwargs.pop("business_value", 5), revenue_impact=kwargs.pop("revenue_impact", 0),
        product_impact=kwargs.pop("product_impact", 0), urgency=kwargs.pop("urgency", 5),
        status=status, current_stage=status, **kwargs,
    )


def test_contract_lanes_and_blocker_routing():
    assert classify_blocker("CANDIDATE_DEPLOY_URL_MISSING") == "INTERNAL_REPAIRABLE"
    assert classify_blocker("APPROVAL_REQUIRED") == "HUMAN_APPROVAL"
    assert classify_blocker("NETLIFY_AUTH_UNAVAILABLE") == "CREDENTIAL_REQUIRED"


def test_voice_blocker_does_not_monopolize_portfolio():
    objectives = [
        objective("voice", "RELIABILITY", "BLOCKED_INTERNAL", blocked_by=["parser"], repair_cycles_used=1),
        objective("experience", "PRODUCT", business_value=8, product_impact=9),
        objective("revenue", "BUSINESS", business_value=10, revenue_impact=10),
        objective("forex", "INTELLIGENCE"),
        objective("creative", "INTELLIGENCE", business_value=6),
    ]
    plan = plan_portfolio(objectives, cycle_id="simulation")
    selected = {row["objective_id"] for row in plan["selected"]}
    assert "voice" not in selected
    assert "experience" in selected or "revenue" in selected
    assert len(selected) >= 2


def test_human_gate_is_parked_while_other_lanes_continue():
    objectives = [
        objective("voice", "RELIABILITY", "WAITING_HUMAN", human_gate=True, human_gate_reason="Ray microphone test"),
        objective("revenue", "BUSINESS", business_value=10, revenue_impact=10),
        objective("research", "INTELLIGENCE"),
    ]
    plan = plan_portfolio(objectives)
    assert any(row["objective_id"] == "voice" for row in plan["waiting_human"])
    assert any(row["objective_id"] == "revenue" for row in plan["selected"])
    assert any(row["objective_id"] == "research" for row in plan["selected"])


def test_repair_budget_diminishes_noncritical_priority():
    fresh = objective("fresh", "PRODUCT", business_value=7, product_impact=7)
    spent = objective("spent", "RELIABILITY", business_value=7, product_impact=7, repair_cycles_used=2, actual_effort=10, estimated_effort=1)
    assert portfolio_score(fresh)[0] > portfolio_score(spent)[0]


def test_trust_metrics_and_no_change_cost_are_deterministic():
    objectives = [objective("revenue", "BUSINESS", status="ACTIVE", business_value=10, revenue_impact=10)]
    plan = plan_portfolio(objectives)
    metrics = build_trust_metrics(plan, objectives)
    assert metrics["TRUST_LINE"] == "bounded_deterministic_portfolio_read_model"
    assert metrics["PORTFOLIO_STALL_RATE"] == 0.0
    assert plan["cost_projection"]["estimated_cost_usd"] == 0.0


def test_cycle_writes_only_explicit_portfolio_outputs(tmp_path, monkeypatch):
    import nexus_agent_platform.executive_portfolio as portfolio
    monkeypatch.setattr(portfolio, "ROOT", tmp_path)
    monkeypatch.setattr(portfolio, "PORTFOLIO_DIR", tmp_path / "phase16a")
    monkeypatch.setattr(portfolio, "PORTFOLIO_JSON", tmp_path / "phase16a" / "executive_portfolio_latest.json")
    monkeypatch.setattr(portfolio, "PORTFOLIO_BRIEF", tmp_path / "phase16a" / "executive_daily_brief.md")
    receipt = run_executive_portfolio_cycle(cycle_id="simulation")
    assert receipt["cycle_id"] == "simulation"
    assert (tmp_path / "phase16a" / "executive_portfolio_latest.json").exists()
    assert receipt["authority"]["production_approval"] == "RAY_ONLY"
