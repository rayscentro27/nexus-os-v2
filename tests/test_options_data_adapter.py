import pytest

from scripts.trading.options_data_adapter import AlpacaOptionsData, material_test_gate, normalize_snapshot


def test_alpaca_chain_read_is_read_only_and_normalizes_supported_fields():
    calls = []
    def transport(url, headers):
        calls.append((url, headers))
        return {"snapshots": {"CRDO261120P00100000": {
            "latestQuote": {"bp": 1.1, "ap": 1.3, "t": "2026-10-07T19:00:00Z"},
            "latestTrade": {"p": 1.2, "s": 12}, "greeks": {"delta": -0.25, "gamma": 0.02, "theta": -0.03, "vega": 0.1}}}}
    client = AlpacaOptionsData("id", "secret", transport)
    assert client.chain("CRDO")['snapshots']
    assert "snapshots/CRDO" in calls[0][0]
    assert not any("order" in call[0].lower() for call in calls)
    result = normalize_snapshot("CRDO", "CRDO261120P00100000", client.chain("CRDO")['snapshots']['CRDO261120P00100000'])
    assert result["mid"] == pytest.approx(1.2)
    assert result["delta"] == -0.25
    assert "MISSING_OPEN_INTEREST" in result["quality_flags"]


def test_missing_credentials_and_material_gates_fail_closed():
    assert AlpacaOptionsData(None, None).configured is False
    gate = material_test_gate(adapter=True, chain=True, bid_ask=True, iv=False, greeks=True,
                              liquidity=False, execution_feasibility=False)
    assert gate["options_material_test_ready"] is False
    assert "HISTORICAL_DATA_SUFFICIENT" in gate["missing_capabilities"]
    assert gate["live_trading_enabled"] is False


def test_alpaca_paper_read_methods_never_call_order_paths():
    calls = []

    def transport(url, headers):
        calls.append(url)
        return {"option_contracts": []}

    client = AlpacaOptionsData("id", "secret", transport, paper_endpoint="https://paper-api.alpaca.markets")
    client.contracts("SPY", params={"limit": "10"})
    client.contract("SPY261120C00100000")
    client.underlying_quote("SPY")
    client.snapshots(["SPY261120C00100000"])
    assert any("paper-api.alpaca.markets/v2/options/contracts" in url for url in calls)
    assert any("data.alpaca.markets/v2/stocks/SPY/quotes/latest" in url for url in calls)
    assert not any("/orders" in url for url in calls)


def test_normalizer_uses_contract_daily_volume_and_preserves_missing_fields():
    result = normalize_snapshot("SPY", "SPY261120C00100000", {
        "latestQuote": {"bp": 1.0, "ap": 1.2, "t": "2026-10-07T19:00:00Z"},
        "latestTrade": {"p": 1.1}, "dailyBar": {"v": 321},
        "impliedVolatility": 0.2,
        "greeks": {"delta": 0.3, "gamma": 0.1, "theta": -0.02, "vega": 0.04},
    })
    assert result["mid"] == pytest.approx(1.1)
    assert result["volume"] == 321
    assert result["open_interest"] is None
    assert "MISSING_OPEN_INTEREST" in result["quality_flags"]
