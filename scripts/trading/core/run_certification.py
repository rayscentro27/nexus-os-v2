#!/usr/bin/env python3
"""TRADING_ENGINE_RECOVERY_AND_PAPER_CERTIFICATION_R1 progressive runner.

Stages (each runs only if every earlier stage passed):
  B  OANDA Practice read-only checks
  C  dry-run: deterministic signal -> risk gate -> execution request (not submitted)
  D  one bounded OANDA Practice execution (1 unit)
  E  reconciliation (Nexus vs OANDA)
  F  certification close + reconciliation
  G  journal + performance + Nova summary contract

Usage: run_certification.py --through C   (stop after dry-run)
       run_certification.py --through G   (full slice; places ONE 1-unit practice order)
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
from trading.core.store import ROOT, TradingStore, utc_now  # noqa: E402

REPORT = ROOT / "reports" / "trading" / "trading_core_r1_certification_latest.json"
NOVA = ROOT / "reports" / "trading" / "trading_core_nova_summary_latest.json"
ORDER = "BCDEFG"
CERT_OVERLAY = {"overlay_name": "certification-r1", "certification_fixture_allowed": True}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--through", default="C", choices=list(ORDER))
    args = ap.parse_args()
    # Provider governor job context. The governor's reservation / default-deny
    # policy still decides every OANDA call; this only identifies the job.
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    base_job = f"trading-core-r1-cert-{run_id}"
    os.environ["NEXUS_CORRELATION_ID"] = base_job
    os.environ["NEXUS_DEPARTMENT"] = "TRADING"
    os.environ["NEXUS_JOB_TYPE"] = "TRADING_PAPER_CERTIFICATION"

    def scope(stage: str) -> None:
        # The governor treats an identical request inside one job as a replay;
        # each stage is its own bounded sub-job under one correlation id.
        os.environ["NEXUS_DURABLE_JOB_ID"] = f"{base_job}-{stage}"

    scope("B")
    store = TradingStore()
    policy = risk_engine.load_policy(overlay=CERT_OVERLAY)
    version = strategy_registry.freeze(store, strategy_registry.build_wick_version())
    vid = version["strategy_version_id"]; inst = version["instrument"]
    report: dict = {"task": "TRADING_ENGINE_RECOVERY_AND_PAPER_CERTIFICATION_R1", "started_at": utc_now(), "through": args.through,
                    "strategy_id": version["strategy_id"], "strategy_version_id": vid, "policy_version": policy["policy_version"],
                    "live_trading_used": False, "stages": {},
                    "governor_job_context": {"correlation_id": base_job, "department": "TRADING", "job_type": "TRADING_PAPER_CERTIFICATION", "per_stage_job_ids": True}, "ids": {"STRATEGY_ID": version["strategy_id"], "STRATEGY_VERSION_ID": vid}}

    def done(stage: str, ok: bool, **detail) -> bool:
        report["stages"][stage] = {"result": "PASS" if ok else "FAIL", **detail}
        return ok

    def finish() -> int:
        report["finished_at"] = utc_now()
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_text(json.dumps(report, indent=2, default=str) + "\n")
        print(json.dumps({k: v["result"] for k, v in report["stages"].items()} | {"ids": report["ids"]}, indent=2))
        return 0 if all(v["result"] == "PASS" for v in report["stages"].values()) else 1

    adapter = OandaPracticeAdapter()
    # ---- B
    health = adapter.health_check(inst)
    instrument = adapter.get_instrument(inst)
    trades = adapter.get_open_trades(); positions = adapter.get_open_positions()
    b_ok = health["healthy"] and instrument["ok"] and trades["ok"] and positions["ok"] and adapter.host == policy["allowed_broker_host"] and not health["live_endpoint_configured"]
    if not done("B_OANDA_READONLY", b_ok, host=adapter.host, health_reason=health["health_reason"],
                account={k: health["account"].get(k) for k in ("account_id_masked", "currency", "openTradeCount", "openPositionCount", "pendingOrderCount")},
                instrument=instrument, pricing={k: health["pricing"].get(k) for k in ("instrument", "bid", "ask", "time", "tradeable")},
                broker_open_trades=len(trades["trades"]), live_endpoint_configured=health["live_endpoint_configured"]) or args.through == "B":
        return finish()

    # ---- C
    scope("C1")
    raw = adapter.get_candles(inst, version["timeframe"], 500)
    candles = wick_rules.candles_from_oanda(raw["candles"])
    price = adapter.get_pricing(inst)
    mid = (price["bid"] + price["ask"]) / 2
    rule_state = signal_engine.latest_rule_state(version, candles)
    now = datetime.now(timezone.utc)
    sig = signal_engine.generate(version, candles, reference_price=mid, units=policy["max_order_units"], now=now)
    if sig is None:
        sig = signal_engine.certification_fixture(version, candles, reference_price=mid, units=policy["max_order_units"], direction=1, now=now,
                                                  nonce=now.strftime("%Y%m%dT%H%M%S"))
    sig, _created = signal_engine.record(store, sig)
    scope("C2")
    broker_view = {**adapter.health_check(inst), "open_trades": adapter.get_open_trades()["trades"]}
    market = {"instrument": inst, "bid": price["bid"], "ask": price["ask"], "time": price["time"]}
    event = risk_engine.gate(store, sig, policy=policy, market=market, broker=broker_view)
    report["ids"].update({"SIGNAL_ID": sig["signal_id"], "RISK_EVENT_ID": event["risk_event_id"]})
    dry = lifecycle.dry_run(store, sig["signal_id"]) if event["decision"] == "APPROVE" else None
    if not done("C_DRY_RUN", bool(dry), candles=len(candles), rule_state=rule_state, signal_origin=sig["origin"],
                signal={k: sig[k] for k in ("direction", "reference_price", "stop_price", "target_price", "proposed_units", "expires_at")},
                risk_decision=event["decision"], failed_rules=event["failed_rules"], would_submit=dry and dry["would_submit"]) or args.through == "C":
        return finish()

    # ---- D
    scope("D")
    out = lifecycle.execute(store, adapter, sig["signal_id"])
    report["ids"]["ORDER_ID"] = out["order"]["order_id"]
    if out.get("position"):
        report["ids"]["POSITION_ID"] = out["position"]["position_id"]
    if not done("D_PRACTICE_EXECUTION", out["ok"], order_state=out["order"]["state"], receipt_id=out["receipt"]["receipt_id"],
                receipt={k: out["receipt"].get(k) for k in ("ok", "http_status", "error", "fill_price", "units_filled", "reject_reason", "cancel_reason", "idempotent_replay")}) or args.through == "D":
        return finish()

    # ---- E
    scope("E")
    rec = reconciliation.reconcile(store, adapter)
    if not done("E_RECONCILIATION", rec["status"] == "MATCHED", reconciliation_id=rec["reconciliation_id"],
                findings=[f["kind"] for f in rec["findings"]]) or args.through == "E":
        return finish()

    # ---- F
    scope("F")
    closed = lifecycle.close_position(store, adapter, report["ids"]["POSITION_ID"], "CERTIFICATION_CLOSE")
    if not closed["ok"] and closed.get("position", {}).get("state") == "RECONCILIATION_REQUIRED":
        refreshed = lifecycle.refresh_position(store, adapter, report["ids"]["POSITION_ID"])  # SL/TP may have closed it first
        closed = refreshed if refreshed.get("trade") else closed
    rec2 = reconciliation.reconcile(store, adapter)
    if closed.get("trade"):
        report["ids"]["TRADE_ID"] = closed["trade"]["trade_id"]
    if not done("F_CLOSE_RECONCILE", bool(closed.get("ok")) and rec2["status"] == "MATCHED", position_state=closed["position"]["state"],
                reconciliation_id=rec2["reconciliation_id"], findings=[f["kind"] for f in rec2["findings"]]) or args.through == "F":
        return finish()

    # ---- G
    scope("G")
    trade = store.get("trades", report["ids"]["TRADE_ID"])
    perf = journal.performance(store, vid)
    summary = nova_summary.build(store, policy=risk_engine.load_policy(), engine_health="OK", broker_health=adapter.health_check(inst))
    NOVA.write_text(json.dumps(summary, indent=2, default=str) + "\n")
    linkage = all(trade.get(k) for k in ("strategy_version_id", "signal_id", "order_id", "position_id", "risk_event_id")) and \
        trade["signal_id"] == report["ids"]["SIGNAL_ID"] and trade["risk_event_id"] == report["ids"]["RISK_EVENT_ID"] and \
        trade["order_id"] == report["ids"]["ORDER_ID"] and trade["position_id"] == report["ids"]["POSITION_ID"]
    done("G_JOURNAL_PERFORMANCE", linkage and trade["trade_id"] in perf["trade_ids"], linkage_complete=linkage,
         trade={k: trade.get(k) for k in ("direction", "entry_price", "exit_price", "position_size", "realized_pnl", "r_multiple", "execution_costs", "entry_slippage_price", "duration_seconds", "exit_reason", "broker_receipts")},
         performance={k: perf.get(k) for k in ("snapshot_id", "total_trades", "wins", "losses", "win_rate", "net_pnl", "profit_factor", "expectancy", "max_drawdown", "statistical_edge_claim")},
         nova_summary_path=str(NOVA.relative_to(ROOT)))
    return finish()


if __name__ == "__main__":
    raise SystemExit(main())
