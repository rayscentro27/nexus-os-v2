#!/usr/bin/env python3
"""Paper-only SMA crossover certification backtest using an explicit CSV URL.

The strategy shape follows the public ``backtesting.py`` example: 10/30 SMA
crossover. This runner uses only the supplied historical OHLC CSV, has no
broker or order path, and reports bounded risk-management variants.
"""
from __future__ import annotations

import argparse
import csv
import json
import urllib.request
from pathlib import Path


def load_rows(source: str) -> list[dict[str, float]]:
    if source.startswith("http"):
        with urllib.request.urlopen(source, timeout=20) as response:  # nosec B310 - explicit public research URL supplied by operator
            text = response.read().decode("utf-8", errors="replace")
    else:
        text = Path(source).read_text(encoding="utf-8")
    rows = []
    for row in csv.DictReader(text.splitlines()):
        try:
            rows.append({"close": float(row["Close"]), "date": row.get("Date") or row.get("") or ""})
        except (KeyError, TypeError, ValueError):
            continue
    if len(rows) < 40:
        raise ValueError("insufficient_ohlc_rows")
    return rows


def sma(values: list[float], period: int, index: int) -> float | None:
    if index + 1 < period:
        return None
    return sum(values[index + 1 - period:index + 1]) / period


def run(rows: list[dict[str, float]], variant: str) -> dict[str, float | int | str]:
    closes = [row["close"] for row in rows]
    cash = 1.0
    units = 0.0
    entry = 0.0
    trades = []
    equity = []
    for index, price in enumerate(closes):
        fast, slow = sma(closes, 10, index), sma(closes, 30, index)
        if fast is None or slow is None:
            equity.append(cash)
            continue
        if units and variant == "FIXED_STOP_5PCT" and price <= entry * 0.95:
            trades.append(units * (price - entry))
            cash = units * price
            units = 0.0
        if units and variant == "TAKE_PROFIT_10PCT" and price >= entry * 1.10:
            trades.append(units * (price - entry))
            cash = units * price
            units = 0.0
        if not units and fast > slow:
            units, cash, entry = cash / price, 0.0, price
        elif units and fast < slow:
            trades.append(units * (price - entry))
            cash, units = units * price, 0.0
        equity.append(cash + units * price)
    if units:
        trades.append(units * (closes[-1] - entry))
        cash, units = units * closes[-1], 0.0
        equity.append(cash)
    peak = 1.0
    max_dd = 0.0
    for value in equity:
        peak = max(peak, value)
        max_dd = max(max_dd, (peak - value) / peak * 100)
    wins = sum(1 for value in trades if value > 0)
    gains = sum(value for value in trades if value > 0)
    losses = abs(sum(value for value in trades if value < 0))
    return {"variant": variant, "total_return_pct": round((cash - 1.0) * 100, 4), "trade_count": len(trades), "win_rate_pct": round(wins / len(trades) * 100, 2) if trades else 0.0, "profit_factor": round(gains / losses, 4) if losses else None, "max_drawdown_pct": round(max_dd, 4), "paper_only": True, "live_trading": False}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    rows = load_rows(args.source)
    results = [run(rows, variant) for variant in ("BASELINE", "FIXED_STOP_5PCT", "TAKE_PROFIT_10PCT")]
    payload = {"schema_version": "nexus.trading-certification-backtest.v1", "source": args.source, "strategy": "SMA crossover 10/30", "rows": len(rows), "date_start": rows[0]["date"], "date_end": rows[-1]["date"], "results": results, "external_action_performed": False, "live_trading": False}
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
