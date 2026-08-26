from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from nexus_agent_platform.executive_portfolio import (
    PortfolioObjective,
    build_trust_metrics,
    classify_blocker,
    plan_portfolio,
    portfolio_score,
    run_executive_portfolio_cycle,
    dispatch_selected_objectives,
    portfolio_status_response,
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


def test_real_dispatch_calls_existing_capability_adapters_and_records_progress(tmp_path):
    objectives = [
        objective("voice", "RELIABILITY", "BLOCKED_INTERNAL", blocked_by=["parser"]),
        objective("experience", "PRODUCT"),
        objective("revenue", "BUSINESS", revenue_impact=10),
        objective("research", "INTELLIGENCE"),
    ]
    plan = plan_portfolio(objectives, cycle_id="dispatch-sim")
    calls = []
    def adapter(name):
        def run(item, row):
            calls.append((name, item.objective_id))
            return {"status": "MATERIAL_PROGRESS", "material_change": True, "result": "HANDOFF", "receipt_refs": [f"receipt:{item.objective_id}"]}
        return run
    dispatchers = {
        "PRODUCT_EVOLUTION_OR_BUILDER": adapter("product"),
        "REVENUE_OPPORTUNITY_LOOP": adapter("business"),
        "ALPHA_RESEARCH": adapter("research"),
    }
    execution = dispatch_selected_objectives(plan, objectives, dispatchers=dispatchers, receipt_dir=tmp_path)
    assert {name for name, _ in calls} == {"product", "business", "research"}
    assert set(execution["materially_advanced"]) == {"experience", "revenue", "research"}
    assert len(list(tmp_path.glob("*.json"))) == 3
    assert all("objective_id" in json.loads(path.read_text()) for path in tmp_path.glob("*.json"))


def test_voice_blocked_does_not_prevent_non_voice_dispatch_and_engineering_is_bounded(tmp_path):
    objectives = [
        objective("voice", "RELIABILITY", "BLOCKED_INTERNAL", blocked_by=["internal"]),
        objective("experience", "PRODUCT"),
        objective("admin", "PRODUCT", business_value=4),
        objective("revenue", "BUSINESS", revenue_impact=10),
    ]
    plan = plan_portfolio(objectives, cycle_id="isolation")
    calls = []
    def product(item, row):
        calls.append(item.objective_id)
        return {"status": "DISPATCHED", "result": "QUEUED"}
    execution = dispatch_selected_objectives(plan, objectives, dispatchers={"PRODUCT_EVOLUTION_OR_BUILDER": product, "REVENUE_OPPORTUNITY_LOOP": product}, receipt_dir=tmp_path)
    assert "revenue" in calls
    assert execution["dispatched"]
    assert sum(1 for receipt in execution["receipts"] if receipt["blocker"] == "ENGINEERING_CONCURRENCY_LIMIT") <= 1


def test_portfolio_status_is_read_only_and_distinguishes_plan_from_progress(tmp_path):
    report = tmp_path / "portfolio.json"
    report.write_text(json.dumps({"cycle_id": "c1", "objectives": [{"objective_id": "p", "title": "Product", "lane": "PRODUCT", "status": "READY"}], "plan": {"selected": [{"objective_id": "p"}], "execution": {"dispatched": [], "materially_advanced": [], "blocked": ["p"], "waiting_human": []}}}))
    before = report.read_text()
    response = portfolio_status_response(report_path=report)
    assert "Selected: Product" in response
    assert "Dispatched: None" in response
    assert "Material progress: None" in response
    assert report.read_text() == before
