"""Unified multi-asset Trading research and paper simulation contracts.

This module is intentionally provider-neutral. It normalizes read-only market
data, runs deterministic research calculations, and simulates paper fills. No
function can submit a broker order or enable live execution.
"""
from __future__ import annotations

import hashlib
import math
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Iterable


ASSET_CLASSES = ("FOREX", "STOCK", "OPTION", "CRYPTO")
LIVE_FLAGS = {"TRADING_LIVE_EXECUTION_ENABLED": False, "AUTO_TRADING": False, "TRADING_PAPER_ONLY": True}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _id(value: Any) -> str:
    return "tr_" + hashlib.sha256(repr(value).encode()).hexdigest()[:20]


@dataclass(frozen=True)
class Instrument:
    symbol: str
    asset_class: str
    venue: str
    currency: str
    session: str
    multiplier: int = 1
    expiration: str | None = None
    strike: float | None = None
    call_put: str | None = None

    def __post_init__(self) -> None:
        if self.asset_class not in ASSET_CLASSES:
            raise ValueError("unsupported_asset_class")
        if self.asset_class == "OPTION" and (not self.expiration or self.strike is None or self.call_put not in {"CALL", "PUT"}):
            raise ValueError("option_metadata_required")
        if self.multiplier <= 0:
            raise ValueError("invalid_multiplier")


@dataclass(frozen=True)
class MarketBar:
    timestamp: str
    instrument: str
    asset_class: str
    timeframe: str
    open: float
    high: float
    low: float
    close: float
    volume: float | None
    source: str


@dataclass(frozen=True)
class StrategyVersion:
    strategy_id: str
    version: str
    hypothesis: str
    asset_class: str
    instrument: str
    timeframe: str
    rules: dict[str, Any]
    research_refs: tuple[str, ...] = ()
    status: str = "IDEA"


def instruments() -> dict[str, Instrument]:
    return {
        "EUR_USD": Instrument("EUR_USD", "FOREX", "OANDA_PRACTICE", "USD", "SESSION_BASED"),
        "SPY": Instrument("SPY", "STOCK", "PUBLIC_READ", "USD", "US_EQUITY"),
        "SPY_2027_CALL_500": Instrument("SPY_2027_CALL_500", "OPTION", "PUBLIC_READ", "USD", "US_EQUITY", 100, "2027-01-15", 500.0, "CALL"),
        "BTC_USD": Instrument("BTC_USD", "CRYPTO", "PUBLIC_READ", "USD", "24_7"),
    }


def normalize_bars(rows: Iterable[dict[str, Any]], *, instrument: Instrument, timeframe: str, source: str) -> list[MarketBar]:
    normalized: list[MarketBar] = []
    for row in rows:
        try:
            bar = MarketBar(str(row["timestamp"]), instrument.symbol, instrument.asset_class, timeframe,
                            float(row["open"]), float(row["high"]), float(row["low"]), float(row["close"]),
                            float(row["volume"]) if row.get("volume") is not None else None, source)
        except (KeyError, TypeError, ValueError):
            continue
        normalized.append(bar)
    return sorted({bar.timestamp: bar for bar in normalized}.values(), key=lambda bar: bar.timestamp)


def data_quality(bars: list[MarketBar]) -> dict[str, Any]:
    errors: list[str] = []
    for previous, current in zip(bars, bars[1:]):
        if current.timestamp <= previous.timestamp:
            errors.append("NON_MONOTONIC_TIMESTAMP")
    for bar in bars:
        if bar.low > min(bar.open, bar.close) or bar.high < max(bar.open, bar.close) or bar.low > bar.high:
            errors.append("OHLC_INCONSISTENCY")
        if bar.close <= 0 or bar.open <= 0:
            errors.append("INVALID_NON_POSITIVE_PRICE")
    return {"status": "VALID" if not errors else "INVALID", "bar_count": len(bars), "errors": sorted(set(errors)), "source_error": False, "stale": False}


def sma(values: list[float], period: int) -> list[float | None]:
    if period <= 0:
        raise ValueError("invalid_period")
    return [None if index + 1 < period else sum(values[index + 1 - period:index + 1]) / period for index in range(len(values))]


def atr(bars: list[MarketBar], period: int = 14) -> list[float | None]:
    true_ranges = []
    for index, bar in enumerate(bars):
        previous_close = bars[index - 1].close if index else bar.close
        true_ranges.append(max(bar.high - bar.low, abs(bar.high - previous_close), abs(bar.low - previous_close)))
    return sma(true_ranges, period)


def backtest_sma_cross(bars: list[MarketBar], *, fast: int = 10, slow: int = 30, cost_rate: float = 0.0005) -> dict[str, Any]:
    """Completed-bar crossover: signal at t fills at t+1, never future data."""
    if fast >= slow or len(bars) < slow + 2:
        return {"status": "INSUFFICIENT_SAMPLE", "trade_count": 0, "lookahead_protected": True}
    closes = [bar.close for bar in bars]
    fast_values, slow_values = sma(closes, fast), sma(closes, slow)
    returns: list[float] = []
    trades: list[dict[str, Any]] = []
    for index in range(slow, len(bars) - 1):
        if fast_values[index - 1] is None or slow_values[index - 1] is None:
            continue
        if fast_values[index - 1] <= slow_values[index - 1] and fast_values[index] > slow_values[index]:
            entry, exit_ = closes[index + 1] * (1 + cost_rate), closes[min(index + 2, len(bars) - 1)] * (1 - cost_rate)
            change = exit_ / entry - 1
            returns.append(change)
            trades.append({"signal_index": index, "entry_index": index + 1, "exit_index": min(index + 2, len(bars) - 1), "return": change})
    equity = 1.0
    peak = 1.0
    max_drawdown = 0.0
    for value in returns:
        equity *= 1 + value
        peak = max(peak, equity)
        max_drawdown = max(max_drawdown, (peak - equity) / peak)
    wins = [value for value in returns if value > 0]
    losses = [value for value in returns if value < 0]
    return {"status": "COMPLETE", "trade_count": len(returns), "net_return_pct": round((equity - 1) * 100, 6), "win_rate_pct": round(len(wins) / len(returns) * 100, 4) if returns else 0, "profit_factor": round(sum(wins) / abs(sum(losses)), 5) if losses else ("INF" if wins else 0), "max_drawdown_pct": round(max_drawdown * 100, 6), "trades": trades, "lookahead_protected": True, "cost_rate": cost_rate}


def split_oos(bars: list[MarketBar], train_ratio: float = 0.6, oos_ratio: float = 0.2) -> dict[str, list[MarketBar]]:
    train_end, oos_end = int(len(bars) * train_ratio), int(len(bars) * (train_ratio + oos_ratio))
    return {"train": bars[:train_end], "validation": bars[train_end:oos_end], "oos": bars[oos_end:]}


def evaluate_promotion(in_sample: dict[str, Any], oos: dict[str, Any], robustness: list[dict[str, Any]]) -> dict[str, Any]:
    missing = [name for name in ("trade_count", "net_return_pct", "max_drawdown_pct") if oos.get(name) is None]
    if missing or oos.get("status") != "COMPLETE":
        return {"decision": "NEEDS_MORE_DATA", "performance_score": None, "evidence_completeness": 0 if missing else 50, "reason": "missing_or_incomplete_oos_metrics"}
    collapse = float(in_sample.get("net_return_pct", 0)) - float(oos.get("net_return_pct", 0))
    evidence = 100 if oos.get("trade_count", 0) >= 20 else 60
    if not robustness or collapse > 20:
        evidence = min(evidence, 40)
    score = max(0, min(100, round(50 + float(oos["net_return_pct"]) - float(oos["max_drawdown_pct"]))))
    decision = "PAPER_CANDIDATE" if evidence >= 60 and oos.get("trade_count", 0) >= 5 else "REVISION_REQUIRED"
    return {"decision": decision, "performance_score": score, "evidence_completeness": evidence, "reason": "oos_and_robustness_review"}


class PaperPortfolio:
    def __init__(self, portfolio_id: str, cash: float = 10000.0, max_exposure: float = 0.25) -> None:
        self.portfolio_id, self.cash, self.max_exposure = portfolio_id, float(cash), float(max_exposure)
        self.positions: dict[str, dict[str, Any]] = {}
        self.receipts: list[dict[str, Any]] = []

    def fill(self, instrument: Instrument, *, quantity: int, price: float, side: str, timestamp: str | None = None, fee: float = 0.0) -> dict[str, Any]:
        if not LIVE_FLAGS["TRADING_PAPER_ONLY"] or LIVE_FLAGS["TRADING_LIVE_EXECUTION_ENABLED"] or LIVE_FLAGS["AUTO_TRADING"]:
            raise RuntimeError("TRADING_GOVERNANCE_INVALID")
        if quantity <= 0 or price <= 0 or side not in {"BUY", "SELL"}:
            raise ValueError("invalid_paper_fill")
        notional = quantity * price * instrument.multiplier
        if side == "BUY" and notional + fee > self.cash * self.max_exposure:
            raise RuntimeError("PAPER_EXPOSURE_LIMIT")
        position = self.positions.setdefault(instrument.symbol, {"instrument": asdict(instrument), "quantity": 0, "average_price": 0.0, "realized_pnl": 0.0})
        signed = quantity if side == "BUY" else -quantity
        old_quantity = position["quantity"]
        if signed > 0:
            position["average_price"] = ((old_quantity * position["average_price"]) + (quantity * price)) / (old_quantity + quantity) if old_quantity + quantity else price
        else:
            position["realized_pnl"] += (price - position["average_price"]) * min(quantity, old_quantity) * instrument.multiplier
        position["quantity"] += signed
        self.cash += -notional - fee if side == "BUY" else notional - fee
        receipt = {"receipt_id": _id((self.portfolio_id, instrument.symbol, len(self.receipts))), "type": "PAPER_FILL", "portfolio_id": self.portfolio_id, "instrument": asdict(instrument), "side": side, "quantity": quantity, "price": price, "fee": fee, "cash_after": round(self.cash, 8), "live_execution": False, "created_at": timestamp or _now()}
        self.receipts.append(receipt)
        return receipt

    def snapshot(self, marks: dict[str, float]) -> dict[str, Any]:
        unrealized = sum((marks[symbol] - position["average_price"]) * position["quantity"] * position["instrument"]["multiplier"] for symbol, position in self.positions.items() if symbol in marks)
        return {"portfolio_id": self.portfolio_id, "cash": round(self.cash, 8), "positions": self.positions, "unrealized_pnl": round(unrealized, 8), "realized_pnl": round(sum(p["realized_pnl"] for p in self.positions.values()), 8), "paper_only": True, "live_execution": False, "created_at": _now()}


def live_order_attempt(*_: Any, **__: Any) -> dict[str, Any]:
    return {"status": "BLOCKED_BY_TRADING_GOVERNANCE", "live_execution": False, "reason": "paper_only_authority"}
