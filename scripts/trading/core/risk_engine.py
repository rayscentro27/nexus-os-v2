"""Central deterministic Risk Engine R1.

Sits between every signal and every broker execution. Every rule is evaluated
(no short-circuit) so the risk event carries complete RULE_RESULTS. Same
inputs -> same decision. There is no override API: a REJECT is final for that
signal, and AI cannot submit or re-approve.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import LIVE_TRADING_ENABLED
from .contracts import check_transition, SIGNAL_TRANSITIONS, validate_signal
from .signal_engine import parse_time
from .store import ROOT, TradingStore, new_id, utc_now
from .strategy_registry import authorization

POLICY_PATH = ROOT / "configs" / "trading_core_risk_policy_r1.json"
OPEN_POSITION_STATES = {"POSITION_OPEN", "POSITION_UPDATED", "STALE_POSITION", "RECONCILIATION_REQUIRED"}
LIVE_ORDER_STATES = {"ORDER_PENDING_SUBMIT", "ORDER_SUBMITTED", "ORDER_ACKNOWLEDGED", "ORDER_FILLED", "EXECUTION_ERROR", "RECONCILIATION_REQUIRED"}


def load_policy(path: Path = POLICY_PATH, overlay: dict[str, Any] | None = None) -> dict[str, Any]:
    policy = json.loads(path.read_text())
    if overlay:
        policy = {**policy, **overlay, "policy_version": f"{policy['policy_version']}+{overlay.get('overlay_name', 'overlay')}"}
    # A policy can never enable live trading; that requires a different release.
    policy["live_trading_enabled"] = False
    return policy


def kill_switch_active(policy: dict[str, Any]) -> tuple[bool, str | None]:
    path = ROOT / policy.get("kill_switch_path", "data/runtime/oanda_practice_kill_switch.json")
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError):
        return False, None
    return bool(data.get("active")), data.get("reason")


def _day(ts: str) -> str:
    return parse_time(ts).astimezone(timezone.utc).date().isoformat()


def evaluate(store: TradingStore, signal: dict[str, Any], *, policy: dict[str, Any], market: dict[str, Any],
             broker: dict[str, Any], now: datetime | None = None) -> dict[str, Any]:
    """Pure decision (no writes). ``market``: {instrument,bid,ask,time}; ``broker``: health + open_trades."""
    now = now or datetime.now(timezone.utc)
    results: list[dict[str, Any]] = []

    def rule(name: str, passed: bool, detail: Any = None) -> None:
        results.append({"rule": name, "pass": bool(passed), "detail": detail})

    contract_errors = validate_signal(signal)
    rule("signal_contract_valid", not contract_errors, contract_errors or None)
    rule("live_trading_disabled", LIVE_TRADING_ENABLED is False and policy.get("live_trading_enabled") is False and not signal.get("live"))
    rule("broker_is_oanda_practice", broker.get("broker") == policy["allowed_broker"] and broker.get("host") == policy["allowed_broker_host"],
         {"broker": broker.get("broker"), "host": broker.get("host")})
    ok, why = authorization(store, signal.get("strategy_version_id", ""), policy)
    rule("strategy_version_authorized", ok, why)
    rule("instrument_authorized", signal.get("instrument") in policy["authorized_instruments"], signal.get("instrument"))
    origins = set(policy["allowed_signal_origins"]) | ({"CERTIFICATION_FIXTURE"} if policy.get("certification_fixture_allowed") else set())
    rule("signal_origin_deterministic", signal.get("origin") in origins and not signal.get("ai_submitted"), signal.get("origin"))

    try:
        expired = parse_time(signal["expires_at"]) <= now
    except (KeyError, ValueError):
        expired = True
    rule("signal_not_expired", not expired, signal.get("expires_at"))

    try:
        age = (now - parse_time(market["time"])).total_seconds()
        fresh = market.get("instrument") == signal.get("instrument") and 0 <= age <= policy["stale_market_seconds"] + 5
    except (KeyError, ValueError, TypeError):
        age, fresh = None, False
    rule("market_data_fresh", fresh, {"age_seconds": age})
    spread = (float(market["ask"]) - float(market["bid"])) if fresh else None
    rule("spread_within_limit", spread is not None and spread <= policy["max_spread_price"], spread)

    units = int(signal.get("proposed_units") or 0)
    rule("position_size_within_limit", 0 < units <= policy["max_order_units"], units)
    risk_amt = float((signal.get("proposed_risk") or {}).get("quote_ccy_amount") or 1e9)
    rule("per_trade_risk_within_limit", risk_amt <= policy["max_risk_per_trade_quote_ccy"], risk_amt)

    broker_trades = broker.get("open_trades") or []
    local_open = [p for p in store.latest("positions") if p.get("state") in OPEN_POSITION_STATES]
    open_count = max(len(broker_trades), len(local_open))
    rule("max_open_positions", open_count < policy["max_open_trading_positions"], open_count)
    same = max(sum(1 for t in broker_trades if t.get("instrument") == signal.get("instrument")),
               sum(1 for p in local_open if p.get("instrument") == signal.get("instrument")))
    rule("max_positions_same_instrument", same < policy["max_positions_per_instrument"], same)

    today = now.date().isoformat()
    trades_today = [t for t in store.latest("trades") if t.get("exit_time") and _day(t["exit_time"]) == today]
    daily_pnl = sum(float(t.get("realized_pnl") or 0) for t in trades_today)
    rule("daily_paper_loss_limit", daily_pnl > -policy["max_daily_paper_loss_usd"], round(daily_pnl, 6))
    orders_today = [o for o in store.latest("orders") if o.get("created_at") and _day(o["created_at"]) == today and o.get("state") in LIVE_ORDER_STATES]
    rule("max_trades_per_day", len(orders_today) < policy["max_trades_per_day"], len(orders_today))

    equity, peak, max_dd = 0.0, 0.0, 0.0
    for t in sorted((t for t in store.latest("trades") if t.get("strategy_version_id") == signal.get("strategy_version_id")), key=lambda t: t.get("exit_time") or ""):
        equity += float(t.get("realized_pnl") or 0); peak = max(peak, equity); max_dd = max(max_dd, peak - equity)
    rule("strategy_drawdown_limit", max_dd < policy["max_strategy_drawdown_usd"], round(max_dd, 6))

    rule("broker_health", bool(broker.get("healthy")), broker.get("health_reason"))
    active, reason = kill_switch_active(policy)
    rule("kill_switch_inactive", not active, reason)
    recon = sorted(store.latest("reconciliation_events"), key=lambda r: r.get("recorded_at") or "")
    last_recon_mismatch = bool(recon and recon[-1].get("status") == "MISMATCH")
    blocking = [p for p in store.latest("positions") if p.get("state") == "RECONCILIATION_REQUIRED"] + \
               [o for o in store.latest("orders") if o.get("state") in {"RECONCILIATION_REQUIRED", "EXECUTION_ERROR"}]
    rule("reconciliation_clean", not blocking and not last_recon_mismatch,
         {"blocking_entities": len(blocking), "last_reconciliation_mismatch": last_recon_mismatch})

    prior_signal = store.get("signals", signal.get("signal_id", ""))
    dup_signal = bool(prior_signal and prior_signal.get("status") != "GENERATED") or bool(store.find("risk_events", signal_id=signal.get("signal_id")))
    rule("no_duplicate_signal", not dup_signal, prior_signal.get("status") if prior_signal else None)
    rule("no_duplicate_order", not store.find("orders", signal_id=signal.get("signal_id")))

    failed = [r["rule"] for r in results if not r["pass"]]
    return {"decision": "REJECT" if failed else "APPROVE", "rule_results": results, "failed_rules": failed,
            "reason": "all_rules_passed" if not failed else ";".join(failed), "policy_version": policy["policy_version"],
            "evaluated_at": now.isoformat()}


def gate(store: TradingStore, signal: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
    """Evaluate, persist an immutable risk event, and advance signal state."""
    decision = evaluate(store, signal, **kwargs)
    event = {"risk_event_id": new_id("risk"), "signal_id": signal.get("signal_id"), "strategy_version_id": signal.get("strategy_version_id"),
             "decision": decision["decision"], "rule_results": decision["rule_results"], "failed_rules": decision["failed_rules"],
             "reason": decision["reason"], "policy_version": decision["policy_version"], "timestamp": utc_now()}
    store.append("risk_events", event)
    current = store.get("signals", signal.get("signal_id", ""))
    if current and current.get("status") == "GENERATED":
        target = "RISK_APPROVED" if event["decision"] == "APPROVE" else ("EXPIRED" if decision["failed_rules"] == ["signal_not_expired"] else "RISK_REJECTED")
        check_transition(SIGNAL_TRANSITIONS, current["status"], target)
        store.append("signals", {**current, "status": target, "risk_event_id": event["risk_event_id"]})
    return event
