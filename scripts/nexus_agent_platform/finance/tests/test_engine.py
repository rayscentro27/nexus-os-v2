from nexus_agent_platform.finance.engine import budget_check, break_even, campaign_preflight, finance_postrun, finance_preflight, record_cost, run_bounded_dry_run


def test_break_even_is_explicit_when_inputs_are_unknown():
    assert break_even(100.0, None)["break_even_quantity"] == "UNKNOWN"
    assert break_even(100.0, 25.0)["break_even_quantity"] == 4


def test_budget_breaker_pauses_optional_consumption():
    result = budget_check({"cash_cost_usd": 11}, {"MAX_CASH_COST_USD": 10})
    assert result["state"] == "PAUSE_OPTIONAL_CONSUMPTION"
    assert result["overages"] == ["MAX_CASH_COST_USD"]


def test_campaign_preflight_preserves_unknown_revenue():
    result = campaign_preflight(campaign_id="campaign-test", upfront_cost=12, continuous_cost=0, max_validation_cost_usd=12, price="UNKNOWN", variable_cost="UNKNOWN")
    assert result["provenance"].startswith("ESTIMATED")
    assert result["scenarios"]["BASE"]["revenue"] == "UNKNOWN"


def test_cost_receipt_is_idempotent(tmp_path, monkeypatch):
    monkeypatch.setenv("NEXUS_GOVERNED_DATA_DIR", str(tmp_path))
    first = record_cost("receipt-test", department="FINANCE", cash_cost_usd=0)
    second = record_cost("receipt-test", department="FINANCE", cash_cost_usd=0)
    assert first["receipt_id"] == second["receipt_id"]
    assert second["idempotent"] is True


def test_preflight_postrun_and_variance(tmp_path, monkeypatch):
    monkeypatch.setenv("NEXUS_GOVERNED_DATA_DIR", str(tmp_path))
    pre = finance_preflight("wo-1", department="ALPHA", envelope={"MAX_CASH_COST_USD": 0}, estimated={"cash_cost_usd": 0})
    post = finance_postrun("wo-1", department="ALPHA", estimated={"cash_cost_usd": 0}, actual={"cash_cost_usd": 0}, status="FAILED")
    assert pre["decision"] == "ALLOW"
    assert post["failed_work_still_accounted"] is True
    assert post["receipt"]["work_order_id"] == "wo-1"


def test_bounded_dry_run_has_pre_and_post_receipts(tmp_path, monkeypatch):
    monkeypatch.setenv("NEXUS_GOVERNED_DATA_DIR", str(tmp_path))
    result = run_bounded_dry_run()
    assert len(result["jobs"]) == 5
    assert all(job["preflight"]["decision"] == "ALLOW" for job in result["jobs"])
    assert all(job["postrun"]["receipt"]["money_spent_usd"] == 0 for job in result["jobs"])


def test_real_governed_executor_writes_finance_hooks(tmp_path, monkeypatch):
    monkeypatch.setenv("NEXUS_GOVERNED_DATA_DIR", str(tmp_path / "governed"))
    monkeypatch.setenv("NEXUS_EXECUTION_TELEMETRY_PATH", str(tmp_path / "telemetry.jsonl"))
    from nexus_agent_platform.capabilities.nexus_query_planner import register_executor
    from nexus_agent_platform.capabilities.shared import execute_shared_capability
    from nexus_agent_platform.governed import actions_api, engine, resolution, persistence
    register_executor(lambda capability, args=None: execute_shared_capability("hermes_nova", capability, args or {}, trace_id="finance-test"))
    rec = actions_api.prepare_action_recommendation(title="Finance hook test", problem="prove hook", recommended_action_id="system_health.run", reason="bounded", evidence=[], expected_outcome="healthy", risk_level="low")
    approval = actions_api.create_approval_request(action_id="system_health.run", action_summary="finance hook test", recommendation_id=rec["recommendation_id"])
    resolution.resolve_approval_intent("approve", chat_id=991, decision="approve")
    order = actions_api.create_work_order_from_approval(approval["approval_id"])
    result = engine.execute_approved_work_order(order["work_order_id"])
    assert result["status"] == "completed"
    assert any(r.get("work_order_id") == order["work_order_id"] for r in persistence.read_records("finance_cost_receipts"))
    assert any(r.get("work_order_id") == order["work_order_id"] and r.get("type") == "FINANCE_PREFLIGHT" for r in persistence.read_records("finance_learning"))
    register_executor(None)
