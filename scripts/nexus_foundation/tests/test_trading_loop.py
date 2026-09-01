from nexus_foundation.trading_loop import _run
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
