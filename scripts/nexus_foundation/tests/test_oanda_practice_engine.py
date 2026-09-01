from datetime import datetime, timezone

import json

import scripts.trading.nexus_oanda_practice_engine as engine
from scripts.trading.nexus_oanda_practice_engine import OrderExecutor, RiskEngine, Signal, TradingKillSwitch, classify_broker_reconciliation, market_is_fresh


def _market():
    return {"ok": True, "prices": [{"instrument": "EUR_USD", "bid": 1.1, "ask": 1.1001, "spread": 0.0001, "time": datetime.now(timezone.utc).isoformat()}]}


def _signal(**changes):
    values = {"signal_id": "test-signal", "instrument": "EUR_USD", "side": "BUY", "units": 1, "confidence": .9, "created_at": datetime.now(timezone.utc).isoformat(), "strategy_id": "nexus_practice_monitor_v1"}
    values.update(changes)
    return Signal(**values)


def test_practice_authority_gate_and_freshness():
    market = _market()
    limits = {"approved_instruments": ["EUR_USD"], "approved_strategy": "nexus_practice_monitor_v1", "max_order_units": 1, "signal_confidence_threshold": .75, "stale_signal_seconds": 120, "max_open_positions": 1, "max_pending_orders": 1, "max_spread_units": .0015, "stale_market_seconds": 120}
    risk = RiskEngine(limits, TradingKillSwitch())
    assert market_is_fresh(market, 120)
    assert risk.validate(_signal(), market, {"open_position_count": 0, "pending_order_count": 0})["approved"]
    assert risk.validate(_signal(evidence_tier="CANDIDATE"), market, {"open_position_count": 0, "pending_order_count": 0})["reason"] == "paper_evidence_tier_not_allowed"
    assert risk.validate(_signal(), market, {"open_position_count": 1, "pending_order_count": 0})["reason"] == "max_open_positions_reached"


def test_risk_fails_closed_for_stale_market_and_spread():
    limits = {"approved_instruments": ["EUR_USD"], "approved_strategy": "nexus_practice_monitor_v1", "max_order_units": 1, "signal_confidence_threshold": .75, "stale_signal_seconds": 120, "max_open_positions": 1, "max_pending_orders": 1, "max_spread_units": .0001, "stale_market_seconds": 120}
    risk = RiskEngine(limits, TradingKillSwitch())
    market = _market(); market["prices"][0]["spread"] = .001
    assert risk.validate(_signal(), market, {"open_position_count": 0, "pending_order_count": 0})["reason"] == "spread_guard_rejected"


def test_ambiguous_submission_is_journaled_without_retry(tmp_path, monkeypatch):
    class TimeoutClient:
        calls = 0
        def submit_market_order(self, _signal):
            self.calls += 1
            return {"ok": False, "status_code": None, "data": {}, "error": "TimeoutError", "filled": False}

    journal = tmp_path / "journal.jsonl"
    state = tmp_path / "state.json"
    monkeypatch.setattr(engine, "FORWARD_JOURNAL_PATH", journal)
    monkeypatch.setattr(engine, "STATE_PATH", state)
    monkeypatch.setattr(engine.persistence, "append_record", lambda *_args, **_kwargs: None)
    client = TimeoutClient()
    result = OrderExecutor(client, RiskEngine({"max_order_units": 1}, TradingKillSwitch())).execute(_signal(signal_id="ambiguous"))
    assert client.calls == 1
    assert result["ambiguous_response"] is True
    row = json.loads(journal.read_text())
    assert row["broker_status"] == "REJECTED" and row["execution_identity"] == "ambiguous"


def test_broker_truth_classifies_orphan_and_missing_state():
    broker = {"open_positions": [{"instrument": "EUR_USD", "long": {"tradeIDs": ["broker-1"]}, "short": {"tradeIDs": []}}]}
    orphan = classify_broker_reconciliation({"trade_ids": []}, broker)
    missing = classify_broker_reconciliation({"trade_ids": ["local-1"]}, {"open_positions": []})
    assert orphan["action"] == "REVIEW_AND_PAUSE" and orphan["orphan_trade_ids"] == ["broker-1"]
    assert missing["action"] == "REVIEW_AND_PAUSE" and missing["missing_trade_ids"] == ["local-1"]
