"""Trading Core R1 offline contracts + failure gates (no network, no broker)."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from trading.core import contracts, journal, lifecycle, nova_summary, reconciliation, risk_engine, signal_engine, strategy_registry, wick_rules
from trading.core.oanda_practice_adapter import ORDER_TAG, AdapterRefused, LiveEndpointBlocked, OandaPracticeAdapter
from trading.core.store import StoreError, TradingStore

ROOT = Path(__file__).resolve().parents[4]
H1_DATA = ROOT / "data/runtime/wick_sequence_oanda_eurusd_h1_2026-10-06.json"
EVIDENCE = ROOT / "data/governed/wick_sequence_baseline_v1_backtest.json"
NOW = datetime(2026, 11, 16, 12, 0, 5, tzinfo=timezone.utc)


def _candles(n: int = 60) -> list[dict]:
    out, price = [], 1.1
    for i in range(n):
        o = price; c = price + (0.0004 if i % 2 else -0.0003)
        out.append({"o": o, "h": max(o, c) + 0.0005, "l": min(o, c) - 0.0005, "c": c, "v": 100 + i,
                    "time": (NOW - timedelta(hours=n - i)).isoformat()})
        price = c
    return out


class FakeBroker:
    """Deterministic in-memory OANDA Practice stand-in implementing the adapter contract."""

    def __init__(self, healthy: bool = True) -> None:
        self.trades: dict[str, dict] = {}; self.orders: dict[str, dict] = {}; self.closed: dict[str, dict] = {}
        self.healthy = healthy; self.submits = 0; self.next = 100

    def health_check(self, instrument="EUR_USD"):
        return {"healthy": self.healthy, "broker": "OANDA_PRACTICE", "host": "https://api-fxpractice.oanda.com", "health_reason": "ok" if self.healthy else "pricing_unavailable"}

    def get_open_trades(self):
        return {"ok": True, "error": None, "trades": list(self.trades.values())}

    def get_order(self, spec):
        o = self.orders.get(spec.lstrip("@"))
        return {"ok": bool(o), "exists": bool(o), "http_status": 200 if o else 404, "state": o and "FILLED", "trade_opened_id": o and o["trade_id"], "order_id": o and o["id"], "filling_transaction_id": None, "error": None}

    def get_trade(self, tid):
        if tid in self.trades:
            return {"ok": True, "trade_id": tid, "state": "OPEN", "current_units": self.trades[tid]["units"]}
        if tid in self.closed:
            return {"ok": True, **self.closed[tid]}
        return {"ok": False, "state": None, "error": "HTTP_404"}

    def submit_paper_order(self, req):
        if req["environment"] != "PRACTICE":
            raise LiveEndpointBlocked("x")
        if abs(req["units"]) > 1:
            raise AdapterRefused("units")
        if req["client_id"] in self.orders:
            o = self.orders[req["client_id"]]
            return {"ok": True, "idempotent_replay": True, "trade_id": o["trade_id"], "order_id": o["id"], "http_status": 200}
        self.submits += 1; self.next += 2; tid = str(self.next)
        self.orders[req["client_id"]] = {"id": str(self.next - 1), "trade_id": tid}
        self.trades[tid] = {"trade_id": tid, "instrument": req["instrument"], "units": req["units"], "tag": ORDER_TAG, "client_id": req["client_id"]}
        return {"ok": True, "idempotent_replay": False, "http_status": 201, "order_id": str(self.next - 1), "trade_id": tid, "fill_price": 1.10010,
                "fill_time": NOW.isoformat(), "half_spread_cost": "0.0001", "fill_transaction_id": tid}

    def close_paper_position(self, tid, environment="PRACTICE"):
        t = self.trades.pop(tid)
        self.closed[tid] = {"trade_id": tid, "state": "CLOSED", "average_close_price": "1.10030", "close_time": (NOW + timedelta(minutes=1)).isoformat(), "realized_pl": "0.0002", "financing": "0"}
        return {"ok": True, "http_status": 200, "exit_price": 1.10030, "exit_time": (NOW + timedelta(minutes=1)).isoformat(), "realized_pl": "0.0002", "financing": "0", "half_spread_cost": "0.0001", "close_transaction_id": "x"}


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setattr(risk_engine, "ROOT", tmp_path)  # isolate kill switch
    store = TradingStore(tmp_path / "tc")
    version = strategy_registry.freeze(store, strategy_registry.build_wick_version())
    policy = risk_engine.load_policy(overlay={"overlay_name": "test", "authorized_strategy_versions": [version["strategy_version_id"]], "certification_fixture_allowed": True})
    return store, version, policy, FakeBroker()


def _market(price=1.1001, at=NOW):
    return {"instrument": "EUR_USD", "bid": price - 0.00005, "ask": price + 0.00005, "time": at.isoformat()}


def _signal(store, version, nonce="a", direction=1, now=NOW, units=1):
    s = signal_engine.certification_fixture(version, _candles(), reference_price=1.1001, units=units, direction=direction, now=now, nonce=nonce)
    return signal_engine.record(store, s)[0]


def _gate(store, sig, policy, broker, market=None, now=NOW):
    return risk_engine.gate(store, sig, policy=policy, market=market or _market(), broker={**broker.health_check(), "open_trades": broker.get_open_trades()["trades"]}, now=now)


# ---------------- A. offline contracts ----------------

@pytest.mark.skipif(not (H1_DATA.exists() and EVIDENCE.exists()), reason="cached evidence data not present")
def test_rules_port_reproduces_evidence_replay_exactly():
    spec = json.loads(strategy_registry.WICK_SPEC_PATH.read_text())
    result = wick_rules.backtest(wick_rules.candles_from_oanda(json.loads(H1_DATA.read_text())["candles"]), spec["strategy_logic"])
    evidence = json.loads(EVIDENCE.read_text())
    assert result["trade_count"] == evidence["trade_count"] == 16
    for mine, theirs in zip(result["trades"], evidence["trades"]):
        assert mine["entry_time"] == theirs["entry_time"] and mine["exit_reason"] == theirs["exit_reason"]
        assert mine["net_pnl"] == pytest.approx(theirs["net_pnl"], abs=1e-15)


def test_strategy_freeze_is_idempotent_and_immutable(env):
    store, version, _p, _b = env
    assert strategy_registry.freeze(store, strategy_registry.build_wick_version())["strategy_version_id"] == version["strategy_version_id"]
    tampered = {**strategy_registry.build_wick_version(), "rules_hash": "0" * 64}
    with pytest.raises(StoreError):
        strategy_registry.freeze(store, tampered)
    assert version["status"] == "CERTIFICATION" and version["live_trading"] is False
    for field in ("strategy_id", "strategy_version_id", "name", "asset_class", "instrument", "timeframe", "entry_rules", "exit_rules", "stop_rule",
                  "target_rule", "position_sizing_rule", "allowed_session", "parameters", "source", "created_at", "status"):
        assert version.get(field) not in (None, ""), field


def test_signal_is_deterministic_and_contract_valid(env):
    store, version, _p, _b = env
    a = signal_engine.certification_fixture(version, _candles(), reference_price=1.1001, units=1, now=NOW, nonce="z")
    b = signal_engine.certification_fixture(version, _candles(), reference_price=1.1001, units=1, now=NOW, nonce="z")
    assert a == b and contracts.validate_signal(a) == []
    assert a["stop_price"] < a["reference_price"] < a["target_price"]
    assert a["strategy_version_id"] == version["strategy_version_id"] and a["ai_submitted"] is False


def test_real_rule_signal_only_on_latest_breakout_bar():
    spec = json.loads(strategy_registry.WICK_SPEC_PATH.read_text())
    version = {**strategy_registry.build_wick_version(), "parameters": spec["strategy_logic"]}
    if not H1_DATA.exists():
        pytest.skip("cached data not present")
    candles = wick_rules.candles_from_oanda(json.loads(H1_DATA.read_text())["candles"])
    ev = wick_rules.scan(candles, version["parameters"])[-1]
    cut = candles[: ev["signal_index"] + 1]
    sig = signal_engine.generate(version, cut, reference_price=cut[-1]["c"], units=1, now=NOW)
    assert sig and sig["origin"] == "DETERMINISTIC_STRATEGY" and sig["signal_bar_time"] == ev["signal_time"]
    assert signal_engine.generate(version, candles[: ev["signal_index"] + 2], reference_price=1.1, units=1, now=NOW) is None


def test_risk_approve_execute_reconcile_close_journal_performance(env):
    store, version, policy, broker = env
    sig = _signal(store, version)
    ev = _gate(store, sig, policy, broker)
    assert ev["decision"] == "APPROVE", ev["failed_rules"]
    assert len(ev["rule_results"]) >= 20 and ev["policy_version"].startswith("trading-risk-policy-r1.0")
    assert lifecycle.dry_run(store, sig["signal_id"], now=NOW)["submitted"] is False and broker.submits == 0
    out = lifecycle.execute(store, broker, sig["signal_id"], now=NOW)
    assert out["ok"] and [h["state"] for h in out["order"]["state_history"]] == ["ORDER_PENDING_SUBMIT", "ORDER_SUBMITTED", "ORDER_ACKNOWLEDGED", "ORDER_FILLED"]
    assert store.get("signals", sig["signal_id"])["status"] == "EXECUTED"
    assert reconciliation.reconcile(store, broker)["status"] == "MATCHED"
    pid = out["position"]["position_id"]
    closed = lifecycle.close_position(store, broker, pid, "CERTIFICATION_CLOSE")
    trade = closed["trade"]
    assert closed["position"]["state"] == "TRADE_FINALIZED"
    for k in ("strategy_version_id", "signal_id", "order_id", "position_id", "risk_event_id"):
        assert trade[k]
    assert trade["realized_pnl"] == pytest.approx(0.0002) and trade["r_multiple"] is not None
    assert len(trade["broker_receipts"]) == len(set(trade["broker_receipts"])) == 2
    with pytest.raises(StoreError):
        store.append("trades", trade)  # journal is immutable
    perf = journal.performance(store, version["strategy_version_id"])
    assert perf["total_trades"] == 1 and perf["wins"] == 1 and perf["statistical_edge_claim"] == "NONE"
    assert reconciliation.reconcile(store, broker)["status"] == "MATCHED"
    summary = nova_summary.build(store, policy=policy, engine_health="OK", broker_health=broker.health_check())
    assert summary["TRADING_MODE"] == "PAPER" and summary["LIVE_TRADING_ENABLED"] is False and summary["ACTIVE_STRATEGY"]
    assert summary["STRATEGY_PERFORMANCE"]["total_trades"] == 1


def test_broker_closed_position_is_recorded_not_retraded(env):
    store, version, policy, broker = env
    sig = _signal(store, version, nonce="bc")
    _gate(store, sig, policy, broker)
    out = lifecycle.execute(store, broker, sig["signal_id"], now=NOW)
    tid = out["position"]["broker_trade_id"]
    broker.close_paper_position(tid)  # simulate SL/TP at broker
    rec = reconciliation.reconcile(store, broker)
    assert any(f["kind"] == "BROKER_CLOSED_POSITION" for f in rec["findings"]) and rec["status"] == "MATCHED"
    res = lifecycle.refresh_position(store, broker, out["position"]["position_id"])
    assert res["position"]["state"] == "TRADE_FINALIZED" and broker.submits == 1


def test_state_machine_rejects_illegal_transitions():
    with pytest.raises(contracts.TransitionError):
        contracts.check_transition(contracts.ORDER_TRANSITIONS, "ORDER_FILLED", "ORDER_SUBMITTED")
    with pytest.raises(contracts.TransitionError):
        contracts.check_transition(contracts.POSITION_TRANSITIONS, "TRADE_FINALIZED", "POSITION_OPEN")
    with pytest.raises(contracts.TransitionError):
        contracts.check_transition(contracts.SIGNAL_TRANSITIONS, "RISK_REJECTED", "RISK_APPROVED")


# ---------------- failure gates ----------------

def test_gate_unauthorized_strategy(env):
    store, version, policy, broker = env
    sig = _signal(store, version, nonce="u")
    ev = _gate(store, sig, {**policy, "authorized_strategy_versions": []}, broker)
    assert ev["decision"] == "REJECT" and "strategy_version_authorized" in ev["failed_rules"]
    with pytest.raises(lifecycle.LifecycleError):
        lifecycle.execute(store, broker, sig["signal_id"], now=NOW)
    assert broker.submits == 0


def test_gate_fixture_blocked_without_certification_overlay(env):
    store, version, policy, broker = env
    sig = _signal(store, version, nonce="f")
    ev = _gate(store, sig, risk_engine.load_policy(overlay={"overlay_name": "t", "authorized_strategy_versions": [version["strategy_version_id"]]}), broker)
    assert "signal_origin_deterministic" in ev["failed_rules"]


def test_gate_expired_signal(env):
    store, version, policy, broker = env
    sig = _signal(store, version, nonce="e", now=NOW - timedelta(minutes=10))
    ev = _gate(store, sig, policy, broker)
    assert ev["failed_rules"] == ["signal_not_expired"] and store.get("signals", sig["signal_id"])["status"] == "EXPIRED"


def test_gate_duplicate_signal_and_duplicate_order(env):
    store, version, policy, broker = env
    sig = _signal(store, version, nonce="d")
    assert _gate(store, sig, policy, broker)["decision"] == "APPROVE"
    again, created = signal_engine.record(store, signal_engine.certification_fixture(version, _candles(), reference_price=1.1001, units=1, now=NOW, nonce="d"))
    assert created is False
    assert "no_duplicate_signal" in _gate(store, again, policy, broker)["failed_rules"]
    lifecycle.execute(store, broker, sig["signal_id"], now=NOW)
    with pytest.raises(lifecycle.LifecycleError):
        lifecycle.execute(store, broker, sig["signal_id"], now=NOW)
    # broker-level idempotency: same client id returns the original order, no second fill
    replay = broker.submit_paper_order(lifecycle.build_order_request(sig))
    assert replay["idempotent_replay"] and broker.submits == 1


def test_gate_risk_limit_breaches(env):
    store, version, policy, broker = env
    big = _signal(store, version, nonce="big", units=5)
    assert "position_size_within_limit" in _gate(store, big, policy, broker)["failed_rules"]
    tight = _signal(store, version, nonce="tight")
    assert "per_trade_risk_within_limit" in _gate(store, tight, {**policy, "max_risk_per_trade_quote_ccy": 1e-9}, broker)["failed_rules"]
    first = _signal(store, version, nonce="p1")
    _gate(store, first, policy, broker); lifecycle.execute(store, broker, first["signal_id"], now=NOW)
    second = _signal(store, version, nonce="p2")
    failed = _gate(store, second, policy, broker)["failed_rules"]
    assert "max_open_positions" in failed and "max_positions_same_instrument" in failed


def test_gate_daily_loss_and_drawdown(env):
    store, version, policy, broker = env
    store.append("trades", {"trade_id": "trd_loss", "strategy_version_id": version["strategy_version_id"], "exit_time": NOW.isoformat(), "realized_pnl": -6.0})
    failed = _gate(store, _signal(store, version, nonce="dl"), policy, broker)["failed_rules"]
    assert "daily_paper_loss_limit" in failed
    store.append("trades", {"trade_id": "trd_loss2", "strategy_version_id": version["strategy_version_id"], "exit_time": (NOW - timedelta(days=2)).isoformat(), "realized_pnl": 2.0})
    store.append("trades", {"trade_id": "trd_loss3", "strategy_version_id": version["strategy_version_id"], "exit_time": (NOW - timedelta(days=1)).isoformat(), "realized_pnl": -7.0})
    assert "strategy_drawdown_limit" in _gate(store, _signal(store, version, nonce="dd"), policy, broker)["failed_rules"]


def test_gate_stale_market_and_unhealthy_broker(env):
    store, version, policy, _broker = env
    stale = _gate(store, _signal(store, version, nonce="s"), policy, FakeBroker(), market=_market(at=NOW - timedelta(minutes=10)))
    assert "market_data_fresh" in stale["failed_rules"]
    sick = _gate(store, _signal(store, version, nonce="h"), policy, FakeBroker(healthy=False))
    assert "broker_health" in sick["failed_rules"]


def test_gate_kill_switch(env, tmp_path):
    store, version, policy, broker = env
    (tmp_path / "data/runtime").mkdir(parents=True)
    (tmp_path / "data/runtime/oanda_practice_kill_switch.json").write_text('{"active": true, "reason": "test"}')
    assert "kill_switch_inactive" in _gate(store, _signal(store, version, nonce="k"), policy, broker)["failed_rules"]


def test_live_endpoint_requested_is_blocked():
    env_ok = lambda: {"live_endpoint_configured": False, "account_id": "101-TEST", "token_present": True, "account_id_present": True}  # noqa: E731
    calls = []
    adapter = OandaPracticeAdapter(request_fn=lambda *a, **k: calls.append(a) or (False, 404, {}, None), environment_fn=env_ok)
    with pytest.raises(LiveEndpointBlocked):
        adapter.submit_paper_order({"environment": "LIVE", "instrument": "EUR_USD", "units": 1, "client_id": "c"})
    with pytest.raises(LiveEndpointBlocked):
        adapter.close_paper_position("1", environment="LIVE")
    with pytest.raises(AdapterRefused):
        adapter.submit_paper_order({"environment": "PRACTICE", "instrument": "EUR_USD", "units": 2, "client_id": "c"})
    assert calls == []  # nothing reached the transport
    with pytest.raises(LiveEndpointBlocked):
        OandaPracticeAdapter(request_fn=lambda *a: (False, None, {}, None), environment_fn=lambda: {"live_endpoint_configured": True})
    policy = risk_engine.load_policy(overlay={"overlay_name": "t", "live_trading_enabled": True})
    assert policy["live_trading_enabled"] is False


def test_adapter_unverified_idempotency_precheck_refuses_submit():
    env_ok = lambda: {"live_endpoint_configured": False, "account_id": "101-TEST", "token_present": True, "account_id_present": True}  # noqa: E731
    posts = []
    def req(method, path, payload=None, query=None):
        if method == "POST":
            posts.append(path)
        return False, None, {}, "URLError"
    out = OandaPracticeAdapter(request_fn=req, environment_fn=env_ok).submit_paper_order({"environment": "PRACTICE", "instrument": "EUR_USD", "units": 1, "client_id": "c"})
    assert out["ok"] is False and out["error"].startswith("idempotency_precheck_unverified") and posts == []


def test_position_mismatch_detected_and_blocks_new_approvals(env):
    store, version, policy, broker = env
    sig = _signal(store, version, nonce="m")
    _gate(store, sig, policy, broker)
    out = lifecycle.execute(store, broker, sig["signal_id"], now=NOW)
    broker.trades[out["position"]["broker_trade_id"]]["units"] = 3  # quantity mismatch
    broker.trades["999"] = {"trade_id": "999", "instrument": "EUR_USD", "units": 1, "tag": ORDER_TAG, "client_id": "ntc-unknown"}
    rec = reconciliation.reconcile(store, broker)
    kinds = {f["kind"] for f in rec["findings"]}
    assert rec["status"] == "MISMATCH" and {"QUANTITY_MISMATCH", "UNEXPECTED_POSITION"} <= kinds
    assert rec["auto_fix_orders_submitted"] == 0 and broker.submits == 1
    assert store.get("positions", out["position"]["position_id"])["state"] == "RECONCILIATION_REQUIRED"
    assert "reconciliation_clean" in _gate(store, _signal(store, version, nonce="m2"), policy, broker)["failed_rules"]


def test_rules_change_after_freeze_revokes_authorization(env, monkeypatch):
    store, version, policy, broker = env
    monkeypatch.setattr(strategy_registry, "file_sha256", lambda p: "changed")
    ok, why = strategy_registry.authorization(store, version["strategy_version_id"], policy)
    assert not ok and why == "strategy_rules_implementation_changed_since_freeze"


# ---------------- governor seam contract ----------------

def test_governor_estimate_practice_host_zero_cost_live_host_default_deny(monkeypatch):
    import alpha.alpha_live_research as http
    import nexus_agent_platform.provider_enforcement as enforcement
    seen = []
    monkeypatch.setattr(enforcement, "execute", lambda provider, service, action, estimate, op, **k: seen.append((provider, estimate)) or (True, 200, {}, None, 0))
    http.http_json("POST", "https://api-fxpractice.oanda.com/v3/accounts/x/orders", {}, {"order": {}})
    http.http_json("GET", "https://api-fxpractice.oanda.com/v3/accounts/x/summary", {})
    http.http_json("POST", "https://api-fxtrade.oanda.com/v3/accounts/x/orders", {}, {"order": {}})
    assert seen[0] == ("OANDA", {"requests": 1, "api_calls": 1, "tokens": 0, "billable": False, "cost": 0.0})
    assert seen[1][1]["billable"] is False and seen[1][1]["cost"] == 0.0
    assert seen[2][0] == "OANDA" and seen[2][1]["billable"] is True and seen[2][1]["cost"] is None  # live stays default-deny
