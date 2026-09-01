#!/usr/bin/env python3
"""Native Nexus Oanda practice trading engine.

Practice/demo only. The daemon monitors approved instruments, evaluates the
configured strategy lane, enforces risk controls, reconciles state, and records
evidence. It never connects to the live-money Oanda host.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import signal
import sys
import time
import urllib.parse
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "trading"))
sys.path.insert(0, str(ROOT / "scripts" / "ops"))
sys.path.insert(0, str(ROOT / "scripts"))
from nexus_runtime_env import load_runtime_env  # noqa: E402
from oanda_demo_common import account_path, environment, execute_smoke, request  # noqa: E402
from nexus_agent_platform.governed import persistence  # noqa: E402

load_runtime_env()

RUNTIME = ROOT / "reports" / "runtime"
MANUAL = ROOT / "reports" / "manual_publish"
PUBLIC_STATUS = ROOT / "public" / "runtime" / "oanda-practice-status.json"
STATE_PATH = ROOT / "data" / "runtime" / "oanda_practice_engine_state.json"
KILL_SWITCH_PATH = ROOT / "data" / "runtime" / "oanda_practice_kill_switch.json"
AUDIT_PATH = RUNTIME / "oanda_practice_engine_audit.jsonl"
FORWARD_JOURNAL_PATH = RUNTIME / "oanda_practice_execution_journal.jsonl"
STATUS_PATH = RUNTIME / "oanda_practice_engine_status_latest.json"
MD_STATUS_PATH = MANUAL / "oanda_practice_engine_status_latest.md"

VALID_DB_RUN_STATES = {"QUEUED", "RUNNING", "SUCCEEDED", "PARTIAL", "FAILED", "BLOCKED", "CANCELLED", "TIMED_OUT", "SIMULATED", "UNKNOWN"}

TEMPORARY_PRACTICE_CERTIFICATION_LIMITS = {
    "label": "TEMPORARY_PRACTICE_CERTIFICATION_LIMITS",
    "approved_instruments": ["AUD_USD", "EUR_USD", "GBP_USD", "USD_CAD", "NZD_USD"],
    "approved_strategy": "nexus_practice_monitor_v1",
    "max_order_units": 1,
    "max_order_notional_usd": 10,
    "max_open_positions": 1,
    "max_trades_per_day": 3,
    "max_daily_simulated_loss_usd": 5,
    "signal_confidence_threshold": 0.75,
    "stale_signal_seconds": 120,
    "max_spread_units": 0.0015,
    "cooldown_seconds": 300,
    "allowed_order_types": ["MARKET"],
}

ENGINE_STATES = {
    "ENGINE_STARTING",
    "MONITORING",
    "WAITING_FOR_VALID_SIGNAL",
    "SIGNAL_RECEIVED",
    "SIGNAL_REJECTED",
    "SIGNAL_APPROVED",
    "ORDER_SUBMITTED",
    "ORDER_ACCEPTED",
    "ORDER_FILLED",
    "POSITION_RECONCILED",
    "RISK_STOPPED",
    "KILL_SWITCHED",
    "ERROR",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text())
    except Exception:
        return default


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n")


def append_audit(event: dict[str, Any]) -> None:
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    event = {"timestamp": utc_now(), **event}
    with AUDIT_PATH.open("a") as fh:
        fh.write(json.dumps(event, sort_keys=True) + "\n")


def mask(value: str | None) -> str | None:
    if not value:
        return None
    return f"{value[:4]}***{value[-3:]}" if len(value) > 8 else "***"


def load_limits() -> dict[str, Any]:
    config_path = ROOT / "config" / "oanda_practice_risk_limits.json"
    configured = read_json(config_path, {})
    if configured:
        merged = {**TEMPORARY_PRACTICE_CERTIFICATION_LIMITS, **configured}
        merged["source"] = str(config_path)
        return merged
    return {**TEMPORARY_PRACTICE_CERTIFICATION_LIMITS, "source": "temporary_practice_certification_defaults"}


@dataclass
class Signal:
    signal_id: str
    instrument: str
    side: str
    units: int
    confidence: float
    created_at: str
    strategy_id: str
    synthetic_test: bool = False
    price: float | None = None
    stop_price: float | None = None
    target_price: float | None = None
    experiment_id: str | None = None
    evidence_tier: str = "PAPER_RESEARCH"


class OandaPracticeClient:
    def __init__(self) -> None:
        self.env = environment()
        configured = os.environ.get("OANDA_ENVIRONMENT", "").strip().lower()
        if configured not in {"practice", "demo", "fxpractice"}:
            raise RuntimeError("oanda_environment_not_practice")
        if self.env.get("live_endpoint_configured"):
            raise RuntimeError("oanda_live_endpoint_detected_blocked")
        if not self.env.get("token_present") or not self.env.get("account_id_present"):
            raise RuntimeError("oanda_credentials_missing")

    def summary(self) -> dict[str, Any]:
        ok, status, data, error = request("GET", account_path("/summary"))
        return {"ok": ok, "status_code": status, "data": data, "error": error}

    def pricing(self, instruments: list[str]) -> dict[str, Any]:
        ok, status, data, error = request("GET", account_path("/pricing"), query={"instruments": ",".join(instruments)})
        return {"ok": ok, "status_code": status, "data": data, "error": error}

    def open_positions(self) -> dict[str, Any]:
        ok, status, data, error = request("GET", account_path("/openPositions"))
        return {"ok": ok, "status_code": status, "data": data, "error": error}

    def pending_orders(self) -> dict[str, Any]:
        ok, status, data, error = request("GET", account_path("/pendingOrders"))
        return {"ok": ok, "status_code": status, "data": data, "error": error}

    def submit_market_order(self, signal_obj: Signal) -> dict[str, Any]:
        payload = {
            "order": {
                "type": "MARKET",
                "instrument": signal_obj.instrument,
                "units": str(signal_obj.units if signal_obj.side == "BUY" else -abs(signal_obj.units)),
                "timeInForce": "FOK",
                "positionFill": "DEFAULT",
                "clientExtensions": {
                    "id": signal_obj.signal_id[:64],
                    "tag": "NEXUS_PRACTICE_ENGINE",
                    "comment": "Nexus practice-only strategy bridge",
                },
            }
        }
        if signal_obj.stop_price is not None:
            payload["order"]["stopLossOnFill"] = {"price": f"{signal_obj.stop_price:.5f}", "timeInForce": "GTC"}
        if signal_obj.target_price is not None:
            payload["order"]["takeProfitOnFill"] = {"price": f"{signal_obj.target_price:.5f}", "timeInForce": "GTC"}
        ok, status, data, error = request("POST", account_path("/orders"), payload)
        fill = data.get("orderFillTransaction") if isinstance(data, dict) else None
        return {"ok": ok, "status_code": status, "data": data, "error": error, "filled": bool(fill)}

    def close_trade(self, trade_id: str) -> dict[str, Any]:
        ok, status, data, error = request("PUT", account_path(f"/trades/{urllib.parse.quote(trade_id, safe='')}/close"), {"units": "ALL"})
        return {"ok": ok, "status_code": status, "data": data, "error": error}


class MarketDataAdapter:
    def __init__(self, client: OandaPracticeClient, limits: dict[str, Any]) -> None:
        self.client = client
        self.limits = limits

    def fetch(self) -> dict[str, Any]:
        instruments = self.limits["approved_instruments"]
        pricing = self.client.pricing(instruments)
        prices = []
        for row in pricing.get("data", {}).get("prices", []) if pricing.get("ok") else []:
            bids = row.get("bids") or []
            asks = row.get("asks") or []
            bid = float(bids[0]["price"]) if bids else None
            ask = float(asks[0]["price"]) if asks else None
            spread = round(ask - bid, 6) if bid is not None and ask is not None else None
            prices.append({"instrument": row.get("instrument"), "bid": bid, "ask": ask, "spread": spread, "time": row.get("time")})
        return {"ok": pricing.get("ok"), "prices": prices, "status_code": pricing.get("status_code"), "error": pricing.get("error")}


def market_is_fresh(market: dict[str, Any], max_age_seconds: int) -> bool:
    if not market.get("ok") or not market.get("prices"):
        return False
    now = datetime.now(timezone.utc)
    for price in market["prices"]:
        try:
            timestamp = datetime.fromisoformat(str(price.get("time", "")).replace("Z", "+00:00"))
            if (now - timestamp).total_seconds() <= max_age_seconds:
                return True
        except Exception:
            continue
    return False


def classify_broker_reconciliation(local_expected: dict[str, Any], broker: dict[str, Any]) -> dict[str, Any]:
    """Classify broker truth without claiming ownership of unknown state."""
    local_positions = set(local_expected.get("trade_ids", []))
    broker_positions = {str(trade_id) for row in broker.get("open_positions", []) for trade_id in (row.get("long", {}).get("tradeIDs", []) + row.get("short", {}).get("tradeIDs", []))}
    return {"broker_authoritative": True, "orphan_trade_ids": sorted(broker_positions - local_positions), "missing_trade_ids": sorted(local_positions - broker_positions), "safe_to_enter": not bool(broker_positions - local_positions or local_positions - broker_positions), "action": "REVIEW_AND_PAUSE" if broker_positions != local_positions else "CONTINUE"}


class StrategyAdapter:
    def __init__(self, limits: dict[str, Any]) -> None:
        self.limits = limits
        self.strategy_id = limits["approved_strategy"]

    def evaluate(self, market: dict[str, Any]) -> dict[str, Any]:
        # This bridge does not invent profitable signals. Real strategy signals
        # may be supplied through the governed local queue by a certified worker.
        queued = read_json(ROOT / "data" / "runtime" / "oanda_practice_signal_queue.json", [])
        for raw in queued if isinstance(queued, list) else []:
            if raw.get("status", "new") == "new":
                return {"state": "SIGNAL_RECEIVED", "signal": raw, "reason": "governed_signal_queue"}
        return {
            "state": "WAITING_FOR_VALID_SIGNAL",
            "signal": None,
            "reason": "no_valid_strategy_signal_available",
            "strategy_id": self.strategy_id,
            "paper_cohort": self.paper_cohort(),
            "market_ok": market.get("ok"),
        }

    @staticmethod
    def paper_cohort() -> list[dict[str, Any]]:
        """Return bounded durable paper candidates without loading full bodies."""
        rows = persistence.read_records("trading_experiments", limit=50)
        seen: set[str] = set(); cohort = []
        for row in rows:
            if row.get("decision") not in {"PAPER_RESEARCH", "PAPER_QUALIFIED"}:
                continue
            spec = row.get("spec") or {}
            strategy_id = spec.get("strategy_id") or row.get("strategy_id")
            if not strategy_id or strategy_id in seen:
                continue
            seen.add(strategy_id)
            cohort.append({"strategy_id": strategy_id, "strategy_version": spec.get("strategy_version", "1.0"), "instrument": spec.get("instrument"), "tier": row.get("decision"), "experiment_id": row.get("experiment_id")})
        return cohort

    def synthetic_signal(self, instrument: str = "AUD_USD", *, stale: bool = False, duplicate: bool = False, risk_limit: bool = False) -> Signal:
        created = datetime.now(timezone.utc) - timedelta(seconds=(300 if stale else 0))
        units = self.limits["max_order_units"] + 10 if risk_limit else 1
        seed = "duplicate" if duplicate else f"{instrument}:{created.isoformat()}:{risk_limit}:{stale}"
        return Signal(
            signal_id="synthetic_" + hashlib.sha256(seed.encode()).hexdigest()[:24],
            instrument=instrument,
            side="BUY",
            units=units,
            confidence=0.9,
            created_at=created.isoformat(),
            strategy_id=self.strategy_id,
            synthetic_test=True,
        )


class TradingKillSwitch:
    def active(self) -> tuple[bool, str | None]:
        data = read_json(KILL_SWITCH_PATH, {})
        return bool(data.get("active")), data.get("reason")


class PositionReconciler:
    def __init__(self, client: OandaPracticeClient) -> None:
        self.client = client

    def reconcile(self) -> dict[str, Any]:
        positions = self.client.open_positions()
        orders = self.client.pending_orders()
        open_positions = positions.get("data", {}).get("positions", []) if positions.get("ok") else []
        pending_orders = orders.get("data", {}).get("orders", []) if orders.get("ok") else []
        return {
            "ok": bool(positions.get("ok") and orders.get("ok")),
            "open_positions": open_positions,
            "pending_orders": pending_orders,
            "open_position_count": len(open_positions),
            "pending_order_count": len(pending_orders),
            "position_error": positions.get("error"),
            "order_error": orders.get("error"),
            "reconciled_at": utc_now(),
        }


class RiskEngine:
    def __init__(self, limits: dict[str, Any], kill_switch: TradingKillSwitch) -> None:
        self.limits = limits
        self.kill_switch = kill_switch
        self.state = read_json(STATE_PATH, {})

    def _seen_signals(self) -> set[str]:
        return set(self.state.get("seen_signal_ids", []))

    def validate(self, signal_obj: Signal, market: dict[str, Any], reconciliation: dict[str, Any]) -> dict[str, Any]:
        kill, reason = self.kill_switch.active()
        if kill:
            return {"approved": False, "state": "KILL_SWITCHED", "reason": reason or "kill_switch_active"}
        if signal_obj.instrument not in self.limits["approved_instruments"]:
            return {"approved": False, "state": "SIGNAL_REJECTED", "reason": "instrument_not_approved"}
        if signal_obj.strategy_id != self.limits["approved_strategy"]:
            return {"approved": False, "state": "SIGNAL_REJECTED", "reason": "strategy_not_approved"}
        if signal_obj.evidence_tier not in {"PAPER_RESEARCH", "PAPER_QUALIFIED"}:
            return {"approved": False, "state": "SIGNAL_REJECTED", "reason": "paper_evidence_tier_not_allowed"}
        if abs(signal_obj.units) > int(self.limits["max_order_units"]):
            return {"approved": False, "state": "SIGNAL_REJECTED", "reason": "max_order_units_exceeded"}
        if signal_obj.confidence < float(self.limits["signal_confidence_threshold"]):
            return {"approved": False, "state": "SIGNAL_REJECTED", "reason": "confidence_below_threshold"}
        try:
            created = datetime.fromisoformat(signal_obj.created_at.replace("Z", "+00:00"))
        except Exception:
            return {"approved": False, "state": "SIGNAL_REJECTED", "reason": "invalid_signal_timestamp"}
        if (datetime.now(timezone.utc) - created).total_seconds() > int(self.limits["stale_signal_seconds"]):
            return {"approved": False, "state": "SIGNAL_REJECTED", "reason": "stale_signal"}
        if signal_obj.signal_id in self._seen_signals():
            return {"approved": False, "state": "SIGNAL_REJECTED", "reason": "duplicate_signal"}
        if reconciliation.get("open_position_count", 0) >= int(self.limits["max_open_positions"]):
            return {"approved": False, "state": "RISK_STOPPED", "reason": "max_open_positions_reached"}
        if reconciliation.get("pending_order_count", 0) >= int(self.limits.get("max_pending_orders", 1)):
            return {"approved": False, "state": "RISK_STOPPED", "reason": "max_pending_orders_reached"}
        if not market_is_fresh(market, int(self.limits.get("stale_market_seconds", 120))):
            return {"approved": False, "state": "SIGNAL_REJECTED", "reason": "stale_market_data"}
        price = next((p for p in market.get("prices", []) if p.get("instrument") == signal_obj.instrument), None)
        if not price:
            return {"approved": False, "state": "SIGNAL_REJECTED", "reason": "price_unavailable"}
        if price.get("spread") is None or float(price["spread"]) > float(self.limits["max_spread_units"]):
            return {"approved": False, "state": "SIGNAL_REJECTED", "reason": "spread_guard_rejected"}
        recent_orders = []
        for value in self.state.get("order_timestamps", []):
            try:
                if (datetime.now(timezone.utc) - datetime.fromisoformat(value.replace("Z", "+00:00"))).total_seconds() < 3600:
                    recent_orders.append(value)
            except Exception:
                continue
        if len(recent_orders) >= int(self.limits.get("max_orders_per_hour", 3)):
            return {"approved": False, "state": "RISK_STOPPED", "reason": "max_orders_per_hour_reached"}
        if abs(float(price.get("ask") or price.get("bid") or 0) * signal_obj.units) > float(self.limits.get("max_order_notional_usd", 10)):
            return {"approved": False, "state": "RISK_STOPPED", "reason": "max_order_notional_exceeded"}
        return {"approved": True, "state": "SIGNAL_APPROVED", "reason": "risk_checks_passed", "price": price}

    def mark_seen(self, signal_obj: Signal) -> None:
        seen = list(self._seen_signals())
        if signal_obj.signal_id not in seen:
            seen.append(signal_obj.signal_id)
        self.state["seen_signal_ids"] = seen[-200:]
        self.state["last_signal_id"] = signal_obj.signal_id
        self.state["order_timestamps"] = [*self.state.get("order_timestamps", []), utc_now()][-50:]
        self.state["updated_at"] = utc_now()
        write_json(STATE_PATH, self.state)


class OrderExecutor:
    def __init__(self, client: OandaPracticeClient, risk: RiskEngine) -> None:
        self.client = client
        self.risk = risk

    def execute(self, signal_obj: Signal) -> dict[str, Any]:
        intent = {
            "order_intent_id": "intent_" + hashlib.sha256(signal_obj.signal_id.encode()).hexdigest()[:24],
            "execution_identity": signal_obj.signal_id,
            "strategy_id": signal_obj.strategy_id,
            "strategy_version": "1.0",
            "experiment_id": signal_obj.experiment_id,
            "instrument": signal_obj.instrument,
            "direction": signal_obj.side,
            "units": signal_obj.units,
            "order_type": "MARKET",
            "stop": signal_obj.stop_price,
            "target": signal_obj.target_price,
            "signal_timestamp": signal_obj.created_at,
            "evidence_tier": signal_obj.evidence_tier,
        }
        FORWARD_JOURNAL_PATH.parent.mkdir(parents=True, exist_ok=True)
        existing = []
        if FORWARD_JOURNAL_PATH.exists():
            for line in FORWARD_JOURNAL_PATH.read_text().splitlines():
                try:
                    existing.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
        prior = next((row for row in reversed(existing) if row.get("execution_identity") == signal_obj.signal_id and row.get("broker_order_id")), None)
        if prior:
            return {"ok": True, "reused": True, "status_code": None, "filled": bool(prior.get("fill_transaction_id")), "journal": prior}
        result = self.client.submit_market_order(signal_obj)
        result["ambiguous_response"] = (not result.get("ok") and result.get("error") in {"TimeoutError", "URLError", "socket.timeout"})
        data = result.get("data") or {}
        create = data.get("orderCreateTransaction") or {}
        fill = data.get("orderFillTransaction") or {}
        intent.update({"broker_order_id": create.get("id"), "fill_transaction_id": fill.get("id"), "trade_id": (fill.get("tradeOpened") or {}).get("tradeID"), "broker_status": "FILLED" if result.get("filled") else "ACCEPTED" if result.get("ok") else "REJECTED", "status_code": result.get("status_code"), "error_code": result.get("error")})
        with FORWARD_JOURNAL_PATH.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(intent, sort_keys=True) + "\n")
        persistence.append_record("trading_journal", {"journal_id": persistence.new_id("broker"), "type": "PRACTICE_EXECUTION", **intent, "created_at": utc_now()})
        if result.get("ok"):
            self.risk.mark_seen(signal_obj)
        result["journal"] = intent
        return result


class TradingAuditRecorder:
    def record(self, event: str, payload: dict[str, Any]) -> None:
        append_audit({"event": event, **payload})


class TradingStatusAdapter:
    @staticmethod
    def simulated_pnl(summary: dict[str, Any], reconciliation: dict[str, Any]) -> str:
        account = summary.get("data", {}).get("account", {}) if summary.get("ok") else {}
        value = account.get("pl") or account.get("unrealizedPL") or "0"
        return str(value)

    @staticmethod
    def write(status: dict[str, Any]) -> None:
        write_json(STATUS_PATH, status)
        write_json(PUBLIC_STATUS, {
            "ok": status.get("ok"),
            "environment": "OANDA_PRACTICE",
            "engine_active": status.get("engine_active"),
            "state": status.get("state"),
            "strategy": status.get("strategy"),
            "monitored_instruments": status.get("monitored_instruments"),
            "risk_limits": status.get("risk_limits"),
            "current_simulated_pnl": status.get("current_simulated_pnl"),
            "open_position_count": status.get("open_position_count"),
            "pending_order_count": status.get("pending_order_count"),
            "most_recent_signal": status.get("most_recent_signal"),
            "most_recent_decision": status.get("most_recent_decision"),
            "kill_switch_active": status.get("kill_switch_active"),
            "last_market_data_fetch": status.get("last_market_data_fetch"),
            "last_reconciliation": status.get("last_reconciliation"),
            "updated_at": status.get("heartbeat_at"),
        })
        lines = [
            "# Oanda Practice Engine Status",
            "",
            f"- generated_at: {status.get('heartbeat_at')}",
            "- environment: OANDA_PRACTICE",
            f"- engine_active: {status.get('engine_active')}",
            f"- state: {status.get('state')}",
            f"- strategy: {status.get('strategy')}",
            f"- monitored_instruments: {', '.join(status.get('monitored_instruments', []))}",
            f"- open_positions: {status.get('open_position_count')}",
            f"- pending_orders: {status.get('pending_order_count')}",
            f"- simulated_pnl: {status.get('current_simulated_pnl')}",
            f"- kill_switch_active: {status.get('kill_switch_active')}",
            f"- next_evaluation_time: {status.get('next_evaluation_time')}",
            "",
            "## Risk Limits",
            "",
        ]
        for key, value in status.get("risk_limits", {}).items():
            lines.append(f"- {key}: {value}")
        MD_STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
        MD_STATUS_PATH.write_text("\n".join(lines) + "\n")


def supabase_record_process(status: dict[str, Any]) -> dict[str, Any]:
    base = os.environ.get("SUPABASE_URL") or os.environ.get("VITE_SUPABASE_URL") or ""
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not base or not key:
        return {"remote_registry_updated": False, "error": "supabase_service_missing"}
    headers = {"apikey": key, "authorization": f"Bearer {key}", "content-type": "application/json", "prefer": "resolution=merge-duplicates,return=representation"}

    def supabase_ssl_context():
        try:
            import certifi

            return __import__("ssl").create_default_context(cafile=certifi.where())
        except Exception:
            return __import__("ssl").create_default_context()

    def call(method: str, url: str, payload: dict[str, Any] | None = None) -> tuple[bool, int | None, Any, str | None]:
        body = json.dumps(payload).encode() if payload is not None else None
        req = __import__("urllib.request").request.Request(url, data=body, headers=headers, method=method)
        try:
            with __import__("urllib.request").request.urlopen(req, timeout=20, context=supabase_ssl_context()) as resp:
                return True, resp.status, json.loads(resp.read().decode() or "{}"), None
        except urllib.error.HTTPError as exc:
            return False, exc.code, {}, f"HTTP_{exc.code}"
        except urllib.error.URLError as exc:
            reason = getattr(exc, "reason", None)
            return False, None, {}, f"URLError:{getattr(reason, '__class__', type(reason)).__name__}"
        except Exception as exc:  # noqa: BLE001
            return False, None, {}, exc.__class__.__name__

    definition = {
        "process_key": "oanda_practice_strategy_engine",
        "name": "Oanda Practice Strategy Engine",
        "description": "Native Nexus practice-only trading monitor, risk engine, and Oanda demo execution bridge.",
        "system": "trading",
        "entry_point": "scripts/trading/nexus_oanda_practice_engine.py",
        "trigger_type": "launchd_daemon",
        "enabled": True,
        "execution_mode": "practice_autonomous_monitor",
        "owner": "Nexus Operations",
        "approval_policy": "practice_only_hard_risk_controls",
        "is_mock": False,
        "metadata": {"final_state": "PRACTICE_AUTONOMOUS_TRADING_ACTIVE", "live_money_trading": False},
        "updated_at": utc_now(),
    }
    ok, _, data, err = call("POST", f"{base.rstrip()}/rest/v1/nexus_process_definitions?on_conflict=process_key", definition)
    process_id = data[0].get("id") if ok and isinstance(data, list) and data else None
    if not process_id:
        return {"remote_registry_updated": False, "error": err or "definition_not_returned"}
    db_status = "RUNNING" if status.get("engine_active") else "FAILED"
    if db_status not in VALID_DB_RUN_STATES:
        db_status = "UNKNOWN"
    run_payload = {
        "process_id": process_id,
        "idempotency_key": f"oanda_practice_strategy_engine:{status.get('run_id')}:{status.get('heartbeat_at')}",
        "status": db_status,
        "started_at": status.get("started_at"),
        "heartbeat_at": status.get("heartbeat_at"),
        "items_attempted": 1,
        "items_succeeded": 1 if status.get("ok") else 0,
        "items_failed": 0 if status.get("ok") else 1,
        "output_location": str(STATUS_PATH),
        "triggered_by": "launchd_or_manual",
        "trace_id": status.get("run_id"),
        "metadata": status,
    }
    headers["prefer"] = "return=representation"
    ok_run, _, _, err_run = call("POST", f"{base.rstrip()}/rest/v1/nexus_process_runs", run_payload)
    return {"remote_registry_updated": ok_run, "process_id_present": True, "run_error": err_run}


def build_engine_status(state: str, client: OandaPracticeClient, market: dict[str, Any], decision: dict[str, Any], reconciliation: dict[str, Any], started_at: str, interval: int) -> dict[str, Any]:
    limits = load_limits()
    summary = client.summary()
    kill, kill_reason = TradingKillSwitch().active()
    env = environment()
    status = {
        "ok": state in ENGINE_STATES and market.get("ok") and reconciliation.get("ok"),
        "run_id": hashlib.sha256(f"{started_at}:{os.getpid()}".encode()).hexdigest()[:20],
        "started_at": started_at,
        "heartbeat_at": utc_now(),
        "engine_active": state not in {"ERROR", "KILL_SWITCHED"},
        "state": state,
        "strategy_monitor": "running",
        "strategy": limits["approved_strategy"],
        "environment": "OANDA_PRACTICE",
        "real_money_trading": False,
        "practice_account_masked": mask(env.get("account_id")),
        "monitored_instruments": limits["approved_instruments"],
        "risk_limits": limits,
        "current_simulated_pnl": TradingStatusAdapter.simulated_pnl(summary, reconciliation),
        "open_position_count": reconciliation.get("open_position_count", 0),
        "pending_order_count": reconciliation.get("pending_order_count", 0),
        "open_positions": reconciliation.get("open_positions", []),
        "pending_orders": reconciliation.get("pending_orders", []),
        "most_recent_signal": decision.get("signal_id"),
        "most_recent_decision": decision,
        "last_market_data_fetch": utc_now() if market.get("ok") else None,
        "last_reconciliation": reconciliation.get("reconciled_at"),
        "next_evaluation_time": (datetime.now(timezone.utc) + timedelta(seconds=interval)).isoformat(),
        "kill_switch_active": kill,
        "kill_switch_reason": kill_reason,
        "restart_recovery": "state_file_loaded",
        "audit_log": str(AUDIT_PATH),
        "kill_command": f"printf '{{\"active\":true,\"reason\":\"manual_stop\",\"updated_at\":\"%s\"}}\\n' \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\" > {KILL_SWITCH_PATH}",
    }
    status["process_registry"] = supabase_record_process(status)
    return status


def run_cycle(*, execute_signal: Signal | None = None, started_at: str | None = None, interval: int = 60) -> dict[str, Any]:
    started_at = started_at or utc_now()
    client = OandaPracticeClient()
    limits = load_limits()
    market = MarketDataAdapter(client, limits).fetch()
    reconciliation = PositionReconciler(client).reconcile()
    kill_switch = TradingKillSwitch()
    risk = RiskEngine(limits, kill_switch)
    strategy = StrategyAdapter(limits)
    audit = TradingAuditRecorder()
    decision: dict[str, Any] = {"state": "WAITING_FOR_VALID_SIGNAL", "reason": "no_signal", "signal_id": None}
    state = "WAITING_FOR_VALID_SIGNAL"

    signal_obj = execute_signal
    if not signal_obj:
        evaluated = strategy.evaluate(market)
        raw_signal = evaluated.get("signal")
        if raw_signal:
            signal_obj = Signal(
                signal_id=raw_signal.get("signal_id") or hashlib.sha256(json.dumps(raw_signal, sort_keys=True).encode()).hexdigest()[:24],
                instrument=raw_signal.get("instrument", limits["approved_instruments"][0]),
                side=raw_signal.get("side", "BUY").upper(),
                units=int(raw_signal.get("units", 1)),
                confidence=float(raw_signal.get("confidence", 0)),
                created_at=raw_signal.get("created_at", utc_now()),
                strategy_id=raw_signal.get("strategy_id", limits["approved_strategy"]),
                synthetic_test=False,
            )
        else:
            decision = evaluated

    if signal_obj:
        validation = risk.validate(signal_obj, market, reconciliation)
        decision = {**validation, "signal_id": signal_obj.signal_id, "instrument": signal_obj.instrument, "synthetic_test": signal_obj.synthetic_test}
        state = validation["state"]
        audit.record("signal_validated", decision)
        if validation.get("approved"):
            executor = OrderExecutor(client, risk)
            execution = executor.execute(signal_obj)
            decision["execution"] = {"ok": execution.get("ok"), "status_code": execution.get("status_code"), "filled": execution.get("filled"), "error": execution.get("error")}
            state = "ORDER_FILLED" if execution.get("filled") else "ORDER_ACCEPTED" if execution.get("ok") else "ERROR"
            audit.record("practice_order_execution", decision)
    status = build_engine_status(state, client, market, decision, reconciliation, started_at, interval)
    TradingStatusAdapter.write(status)
    append_audit({"event": "engine_cycle", "state": state, "decision": decision, "market_ok": market.get("ok"), "reconciliation_ok": reconciliation.get("ok")})
    return status


def self_test(*, execute_order: bool = False) -> dict[str, Any]:
    client = OandaPracticeClient()
    limits = load_limits()
    strategy = StrategyAdapter(limits)
    market = MarketDataAdapter(client, limits).fetch()
    reconciliation = PositionReconciler(client).reconcile()
    risk = RiskEngine(limits, TradingKillSwitch())
    valid = strategy.synthetic_signal(limits["approved_instruments"][0])
    invalid = Signal(**{**valid.__dict__, "signal_id": "invalid_instrument_test", "instrument": "XAU_USD"})
    stale = strategy.synthetic_signal(limits["approved_instruments"][0], stale=True)
    duplicate = strategy.synthetic_signal(limits["approved_instruments"][0], duplicate=True)
    risk.mark_seen(duplicate)
    risk_limit = strategy.synthetic_signal(limits["approved_instruments"][0], risk_limit=True)
    checks = {
        "practice_account_connected": client.summary().get("ok"),
        "market_data_connected": market.get("ok"),
        "position_reconciliation": reconciliation.get("ok"),
        "valid_signal_approved": risk.validate(valid, market, reconciliation).get("approved"),
        "invalid_signal_rejected": not risk.validate(invalid, market, reconciliation).get("approved"),
        "stale_signal_rejected": risk.validate(stale, market, reconciliation).get("reason") == "stale_signal",
        "duplicate_signal_rejected": risk.validate(duplicate, market, reconciliation).get("reason") == "duplicate_signal",
        "risk_limit_rejected": risk.validate(risk_limit, market, reconciliation).get("reason") == "max_order_units_exceeded",
    }
    order_result = {"attempted": False}
    if execute_order:
        order_result = {"attempted": True, **run_certification_order()}
    report = {
        "ok": all(checks.values()) and (not execute_order or order_result.get("ok")),
        "generated_at": utc_now(),
        "checks": checks,
        "bounded_practice_execution_path": order_result,
        "risk_limits": limits,
        "real_money_trading": False,
        "live_endpoint_used": False,
    }
    write_json(RUNTIME / "oanda_practice_engine_self_test_latest.json", report)
    return report


def run_certification_order(*, close_after: bool = True) -> dict[str, Any]:
    """One bounded Practice-only broker proof through the full canonical path.

    This is explicitly a certification trade, not strategy-performance evidence.
    It is opened with broker-side protection, verified, closed, and reconciled.
    """
    client = OandaPracticeClient()
    limits = load_limits()
    market = MarketDataAdapter(client, limits).fetch()
    before = PositionReconciler(client).reconcile()
    if not before.get("ok") or before.get("open_position_count") or before.get("pending_order_count"):
        return {"ok": False, "status": "certification_gate_blocked_existing_broker_state", "before": before}
    price = next((row for row in market.get("prices", []) if row.get("instrument") == limits["approved_instruments"][0]), None)
    if not price or price.get("ask") is None or price.get("bid") is None:
        return {"ok": False, "status": "certification_gate_price_unavailable"}
    signal_obj = Signal(
        signal_id="certification_" + hashlib.sha256(f"{limits['approved_instruments'][0]}:{price['time']}".encode()).hexdigest()[:24],
        instrument=limits["approved_instruments"][0], side="BUY", units=1, confidence=0.99,
        created_at=utc_now(), strategy_id=limits["approved_strategy"], synthetic_test=True,
        price=price["ask"], stop_price=round(float(price["bid"]) - 0.001, 5), target_price=round(float(price["ask"]) + 0.001, 5),
        evidence_tier="PAPER_RESEARCH",
    )
    risk = RiskEngine(limits, TradingKillSwitch())
    decision = risk.validate(signal_obj, market, before)
    if not decision.get("approved"):
        return {"ok": False, "status": "certification_risk_veto", "decision": decision}
    execution = OrderExecutor(client, risk).execute(signal_obj)
    data = execution.get("data") or {}
    fill = data.get("orderFillTransaction") or {}
    trade_id = str((fill.get("tradeOpened") or {}).get("tradeID") or "")
    after_open = PositionReconciler(client).reconcile()
    close = client.close_trade(trade_id) if trade_id and close_after else {"ok": not close_after, "status": "left_open_for_restart_proof"}
    after_close = PositionReconciler(client).reconcile() if close_after else {"ok": True, "open_position_count": 1}
    close_data = close.get("data") or {}
    close_fill = close_data.get("orderFillTransaction") or close_data.get("orderFillTransaction") or {}
    close_row = {"execution_identity": signal_obj.signal_id, "event": "certification_close" if close_after else "certification_open_position_checkpoint", "trade_id": trade_id, "close_transaction_id": close_fill.get("id"), "broker_status": "CLOSED" if close_after and close.get("ok") else "OPEN_CHECKPOINT" if not close_after else "CLOSE_FAILED", "real_money_trading": False, "timestamp": utc_now()}
    FORWARD_JOURNAL_PATH.parent.mkdir(parents=True, exist_ok=True)
    with FORWARD_JOURNAL_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(close_row, sort_keys=True) + "\n")
    persistence.append_record("trading_journal", {"journal_id": persistence.new_id("broker"), **close_row, "created_at": utc_now()})
    return {"ok": bool(execution.get("filled") and trade_id and after_open.get("ok") and close.get("ok") and after_close.get("ok") and (not close_after or after_close.get("open_position_count") == 0)), "status": "certification_trade_opened_verified_closed" if close_after and close.get("ok") else "certification_trade_opened_left_open" if not close_after else "certification_close_failed", "order": execution.get("journal"), "trade_id": trade_id, "before": before, "after_open": after_open, "close": {"ok": close.get("ok"), "status_code": close.get("status_code"), "error": close.get("error")}, "after_close": after_close, "real_money_trading": False}


def reconcile_only() -> dict[str, Any]:
    client = OandaPracticeClient()
    summary = client.summary()
    reconciliation = PositionReconciler(client).reconcile()
    return {"ok": bool(summary.get("ok") and reconciliation.get("ok")), "environment": "OANDA_PRACTICE", "account_state": {"ok": summary.get("ok"), "status_code": summary.get("status_code")}, "reconciliation": reconciliation, "real_money_trading": False}


def close_practice_trade(trade_id: str) -> dict[str, Any]:
    client = OandaPracticeClient()
    result = client.close_trade(trade_id)
    after = PositionReconciler(client).reconcile()
    close_data = result.get("data") or {}
    close_fill = close_data.get("orderFillTransaction") or {}
    row = {"journal_id": persistence.new_id("broker"), "event": "practice_close", "trade_id": trade_id, "close_transaction_id": close_fill.get("id"), "broker_status": "CLOSED" if result.get("ok") else "CLOSE_FAILED", "status_code": result.get("status_code"), "error_code": result.get("error"), "created_at": utc_now(), "real_money_trading": False}
    FORWARD_JOURNAL_PATH.parent.mkdir(parents=True, exist_ok=True)
    with FORWARD_JOURNAL_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, sort_keys=True) + "\n")
    persistence.append_record("trading_journal", row)
    return {"ok": bool(result.get("ok") and after.get("ok")), "close_status_code": result.get("status_code"), "error": result.get("error"), "reconciliation": after, "journal": row, "real_money_trading": False}


def daemon(interval: int, max_cycles: int = 0) -> int:
    stop = {"requested": False}

    def handle_stop(_signum: int, _frame: Any) -> None:
        stop["requested"] = True

    signal.signal(signal.SIGTERM, handle_stop)
    signal.signal(signal.SIGINT, handle_stop)
    started_at = utc_now()
    cycles = 0
    while not stop["requested"] and (max_cycles <= 0 or cycles < max_cycles):
        try:
            run_cycle(started_at=started_at, interval=interval)
            cycles += 1
        except Exception as exc:  # noqa: BLE001
            status = {"ok": False, "engine_active": False, "state": "ERROR", "heartbeat_at": utc_now(), "error": exc.__class__.__name__, "real_money_trading": False}
            TradingStatusAdapter.write(status)
            append_audit({"event": "engine_error", "error": exc.__class__.__name__})
        time.sleep(max(15, interval))
    append_audit({"event": "engine_stopped", "reason": "signal"})
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--interval-seconds", type=int, default=60)
    parser.add_argument("--max-cycles", type=int, default=0)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--execute-test-order", action="store_true")
    parser.add_argument("--certification-order", action="store_true")
    parser.add_argument("--leave-open-certification-order", action="store_true")
    parser.add_argument("--reconcile-only", action="store_true")
    parser.add_argument("--close-trade-id")
    parser.add_argument("--test-valid-signal", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if args.close_trade_id:
        result = close_practice_trade(args.close_trade_id)
    elif args.reconcile_only:
        result = reconcile_only()
    elif args.certification_order:
        result = run_certification_order(close_after=not args.leave_open_certification_order)
    elif args.self_test:
        result = self_test(execute_order=args.execute_test_order)
    elif args.test_valid_signal:
        limits = load_limits()
        sig = StrategyAdapter(limits).synthetic_signal(limits["approved_instruments"][0])
        result = run_cycle(execute_signal=sig, interval=args.interval_seconds)
    elif args.daemon:
        return daemon(args.interval_seconds, args.max_cycles)
    else:
        result = run_cycle(interval=args.interval_seconds)

    if args.json:
        print(json.dumps({
            "ok": result.get("ok"),
            "state": result.get("state") or ("SELF_TEST" if args.self_test else None),
            "engine_active": result.get("engine_active"),
            "practice": not result.get("real_money_trading", False),
            "checks": result.get("checks"),
            "bounded_practice_execution_path": result.get("bounded_practice_execution_path"),
            "certification_result": result if args.certification_order else None,
            "process_registry": result.get("process_registry", {}).get("remote_registry_updated") if isinstance(result.get("process_registry"), dict) else None,
        }, indent=2))
    else:
        print(json.dumps(result, indent=2))
    return 0 if result.get("ok", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())
