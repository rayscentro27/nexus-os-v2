from nexus_foundation.multi_asset_engine import (
    Instrument, PaperPortfolio, backtest_sma_cross, data_quality, evaluate_promotion,
    instruments, normalize_bars, split_oos, live_order_attempt,
)


def bars(n=140):
    return [{"timestamp": f"2026-01-01T{i:03d}:00:00Z", "open": 100 + i * .1, "high": 100.2 + i * .1, "low": 99.8 + i * .1, "close": 100 + i * .1, "volume": i + 1} for i in range(n)]


def test_common_instrument_model_covers_four_assets_and_option_metadata():
    current = instruments()
    assert {item.asset_class for item in current.values()} == {"FOREX", "STOCK", "OPTION", "CRYPTO"}
    assert current["SPY_2027_CALL_500"].multiplier == 100


def test_normalization_quality_deduplicates_and_validates():
    normalized = normalize_bars(bars(3) + [bars(3)[1]], instrument=instruments()["SPY"], timeframe="1D", source="TEST")
    assert len(normalized) == 3
    assert data_quality(normalized)["status"] == "VALID"


def test_backtest_is_deterministic_and_oos_is_temporal():
    normalized = normalize_bars(bars(), instrument=instruments()["EUR_USD"], timeframe="H1", source="OANDA_PRACTICE")
    split = split_oos(normalized)
    result = backtest_sma_cross(split["train"])
    assert result == backtest_sma_cross(split["train"])
    assert split["train"][-1].timestamp < split["oos"][0].timestamp
    assert result["lookahead_protected"] is True


def test_promotion_separates_performance_from_evidence():
    decision = evaluate_promotion({"net_return_pct": 20}, {"status": "COMPLETE", "trade_count": 2, "net_return_pct": 3, "max_drawdown_pct": 1}, [])
    assert decision["decision"] == "REVISION_REQUIRED"
    assert decision["performance_score"] is not None
    assert decision["evidence_completeness"] < 100


def test_paper_portfolio_handles_option_multiplier_and_is_not_live():
    portfolio = PaperPortfolio("paper-1", cash=10000)
    option = instruments()["SPY_2027_CALL_500"]
    receipt = portfolio.fill(option, quantity=1, price=4.0, side="BUY")
    snapshot = portfolio.snapshot({option.symbol: 4.5})
    assert receipt["live_execution"] is False
    assert snapshot["unrealized_pnl"] == 50.0
    assert live_order_attempt()["status"] == "BLOCKED_BY_TRADING_GOVERNANCE"
