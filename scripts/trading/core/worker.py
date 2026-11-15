#!/usr/bin/env python3
"""Trading Core R1 bounded cycle worker (Contabo target; one cycle per invocation).

Cycle: refresh open positions (broker truth) -> reconcile -> on a newly
completed bar, evaluate the frozen strategy -> risk gate -> [execute only if
--execute AND policy.paper_auto_execution_enabled] -> performance -> Nova summary.

Real strategy signals only (no certification fixtures). Default is
observe-only: recurring practice orders still need owner approval
(configs/oanda_demo_trading_policy.json: recurring_demo_orders_approval_required).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path[:0] = [str(Path(__file__).resolve().parents[2]), str(Path(__file__).resolve().parents[3])]

from trading.core import journal, lifecycle, nova_summary, reconciliation, risk_engine, signal_engine, strategy_registry, wick_rules  # noqa: E402
from trading.core.oanda_practice_adapter import OandaPracticeAdapter  # noqa: E402
from trading.core.store import ROOT, TradingStore  # noqa: E402

SUMMARY = ROOT / "reports" / "trading" / "trading_core_nova_summary_latest.json"
MAX_ACTIVE_TRADING_STRATEGIES = 1


def cycle(execute: bool) -> dict:
    run = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    os.environ.update({"NEXUS_CORRELATION_ID": f"trading-core-cycle-{run}", "NEXUS_DEPARTMENT": "TRADING", "NEXUS_JOB_TYPE": "TRADING_PAPER_CERTIFICATION"})
    scope = lambda s: os.environ.__setitem__("NEXUS_DURABLE_JOB_ID", f"trading-core-cycle-{run}-{s}")  # noqa: E731
    store, policy = TradingStore(), risk_engine.load_policy()
    versions = policy["authorized_strategy_versions"][:MAX_ACTIVE_TRADING_STRATEGIES]
    adapter = OandaPracticeAdapter()
    out: dict = {"run": run, "execute_requested": execute, "actions": []}
    scope("refresh")
    for pos in store.latest("positions"):
        if pos.get("state") in {"POSITION_OPEN", "POSITION_UPDATED"}:
            out["actions"].append({"refresh": lifecycle.refresh_position(store, adapter, pos["position_id"]).get("position", {}).get("state")})
    scope("reconcile")
    out["reconciliation"] = reconciliation.reconcile(store, adapter)["status"]
    for vid in versions:
        version = store.get("strategy_versions", vid)
        scope(f"signal-{vid[-6:]}")
        raw = adapter.get_candles(version["instrument"], version["timeframe"], 500)
        candles = wick_rules.candles_from_oanda(raw["candles"])
        price = adapter.get_pricing(version["instrument"])
        if not raw["ok"] or not candles or not price["ok"]:
            # Transient broker/data failure: record and let the next cycle retry (no in-job retry: governor replay guard).
            out["actions"].append({"signal": "market_data_unavailable", "candles_error": raw["error"], "pricing_error": price["error"]}); continue
        sig = signal_engine.generate(version, candles, reference_price=(price["bid"] + price["ask"]) / 2, units=policy["max_order_units"])
        if not sig:
            out["actions"].append({"signal": None, "state": signal_engine.latest_rule_state(version, candles)["last_bar_time"]}); continue
        sig, created = signal_engine.record(store, sig)
        if not created:
            out["actions"].append({"signal": sig["signal_id"], "duplicate": True}); continue
        scope(f"risk-{vid[-6:]}")
        broker = {**adapter.health_check(version["instrument"]), "open_trades": adapter.get_open_trades()["trades"]}
        event = risk_engine.gate(store, sig, policy=policy, market={k: price[k] for k in ("instrument", "bid", "ask", "time")}, broker=broker)
        action = {"signal": sig["signal_id"], "risk": event["decision"], "failed": event["failed_rules"]}
        if event["decision"] == "APPROVE":
            if execute and policy.get("paper_auto_execution_enabled") is True:
                scope(f"exec-{vid[-6:]}")
                action["execution"] = lifecycle.execute(store, adapter, sig["signal_id"])["order"]["state"]
            else:
                action["execution"] = "OBSERVE_ONLY"; action["dry_run"] = lifecycle.dry_run(store, sig["signal_id"])["would_submit"]
        out["actions"].append(action)
        journal.performance(store, vid)
    scope("summary")
    summary = nova_summary.build(store, policy=policy, engine_health="OK", broker_health=adapter.health_check())
    SUMMARY.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY.write_text(json.dumps(summary, indent=2, default=str) + "\n")
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--execute", action="store_true")
    print(json.dumps(cycle(ap.parse_args().execute), indent=2, default=str))
