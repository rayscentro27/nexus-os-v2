from nexus_foundation.trading_loop import _run, score_trading_evidence
from nexus_foundation.contracts import authority_allows, validate_trading_safety


def _bars(values):
    return [{"time": f"2026-01-01T{i:02d}:00:00Z", "mid": {"c": str(v)}} for i, v in enumerate(values)]


def test_deterministic_completed_bar_backtest():
    values = [1 + i * 0.0005 for i in range(140)]
    spec = {"fast": 10, "slow": 30, "max_hold_bars": 24, "cost_rate": 0.00015, "risk_fraction": 0.01}
    first = _run(_bars(values), 0, 100, spec)
    assert first == _run(_bars(values), 0, 100, spec)
    assert all(t["exit_i"] >= t["entry_i"] for t in first["trades"])


def test_live_order_authority_fails_closed():
    assert validate_trading_safety()["LIVE_TRADING_AUTHORITY"] == "NONE"
    assert authority_allows("TRADING_ENGINE", "live_trading", "execute") is False

def test_unknown_metric_is_evidence_gap_not_negative_performance():
    scored = score_trading_evidence(performance={"net_return_pct": 2.0, "expectancy_pct": 0.1, "max_drawdown_pct": 1.0, "trade_count": 10, "profit_factor": None})
    assert scored["performance_score"] is not None
    assert scored["evidence_completeness"] < 100
    assert "profit_factor" in scored["unknown_metrics"]


def test_backtest_feedback_contract_is_bounded_and_open():
    from nexus_foundation import trading_loop
    import scripts.trading.forex_research_scanner as scanner
    import tempfile
    import os

    rows = _bars([1 + ((i % 16) - 8) * 0.001 + (i // 16) * 0.0002 for i in range(500)])
    def candles(*_args, **_kwargs):
        return {"ok": True, "complete": len(rows), "candles": rows, "error": None}
    with tempfile.TemporaryDirectory() as directory:
        old = os.environ.get("NEXUS_GOVERNED_DATA_DIR")
        os.environ["NEXUS_GOVERNED_DATA_DIR"] = directory
        try:
            original = scanner.fetch_candles
            scanner.fetch_candles = candles
            result = trading_loop.run_trading_loop()
        finally:
            scanner.fetch_candles = original
            if old is None: os.environ.pop("NEXUS_GOVERNED_DATA_DIR", None)
            else: os.environ["NEXUS_GOVERNED_DATA_DIR"] = old
    assert result["cost"]["backtest_executions"] == 2
    assert result["feedback"]["next_action"] == "RESEARCH_AND_RETEST"
    assert result["feedback"]["parent_objective_open"] is True
