"""Pure deterministic Wick Sequence Breakout v1 rules.

Faithful, side-effect-free port of ``artifacts/trading/wick_sequence_baseline_v1_replay.py``
(Mercury case rcase_98d9635c39cf3ae5a4). ``backtest()`` must reproduce that
replay's trade list exactly (see the parity contract test); ``scan()`` exposes
the same breakout decisions to the live signal engine so the signal path and
the historical evidence share one rule implementation.

Inputs are completed candles only: ``{"o","h","l","c","v","time"}``.
"""
from __future__ import annotations

import math
from typing import Any

TRANSACTION_COST = 0.0005  # Mercury round-trip notional proxy used by the evidence replay


def sma(values: list[float], index: int, length: int) -> float | None:
    if index < length:
        return None
    return sum(values[index - length:index]) / length


def ema(values: list[float], length: int) -> list[float | None]:
    out: list[float | None] = [None] * len(values)
    if length <= 0 or len(values) < length:
        return out
    alpha = 2.0 / (length + 1.0)
    out[length - 1] = sum(values[:length]) / length
    for i in range(length, len(values)):
        out[i] = alpha * values[i] + (1.0 - alpha) * out[i - 1]  # type: ignore[operator]
    return out


def wilder_atr(rows: list[dict], period: int) -> list[float | None]:
    tr: list[float] = []
    for i, row in enumerate(rows):
        h, l = row["h"], row["l"]
        tr.append(h - l if i == 0 else max(h - l, abs(h - rows[i - 1]["c"]), abs(l - rows[i - 1]["c"])))
    values: list[float | None] = [None] * len(rows)
    if len(rows) <= period:
        return values
    values[period] = sum(tr[1:period + 1]) / period
    for i in range(period + 1, len(rows)):
        values[i] = (values[i - 1] * (period - 1) + tr[i]) / period  # type: ignore[operator]
    return values


def candles_from_oanda(raw: list[dict]) -> list[dict]:
    out = []
    for item in raw:
        if not item.get("complete"):
            continue
        mid = item["mid"]
        out.append({"o": float(mid["o"]), "h": float(mid["h"]), "l": float(mid["l"]), "c": float(mid["c"]),
                    "v": float(item["volume"]), "time": item["time"]})
    return out


def _run(candles: list[dict], logic: dict[str, Any], *, simulate: bool) -> tuple[list[dict], list[dict], dict]:
    formation = logic["formation"]; breakout = logic["breakout"]; size_filter = logic["breakout_size_filter"]
    volume_rule = logic["volume_proxy"]; exits = logic["atr"]
    trend_filter = logic.get("trend_filter") or {"enabled": False}
    ranges = [r["h"] - r["l"] for r in candles]
    atr = wilder_atr(candles, int(exits["period"]))
    trend = ema([r["c"] for r in candles], int(trend_filter.get("period") or 200)) if trend_filter.get("enabled") else [None] * len(candles)
    n = len(candles)
    bullish = [False] * n; bearish = [False] * n
    for i, row in enumerate(candles):
        a = atr[i]; span = row["h"] - row["l"]
        if a is None or span <= 0 or span < a * float(breakout["min_range_atr"]):
            continue
        upper = (row["h"] - max(row["o"], row["c"])) / span
        lower = (min(row["o"], row["c"]) - row["l"]) / span
        bullish[i] = lower >= float(formation["bull_lower_wick_min"]) and upper <= float(formation["bull_upper_wick_max"])
        bearish[i] = upper >= float(formation["bear_upper_wick_min"]) and lower <= float(formation["bear_lower_wick_max"])

    buy_expr = lambda r: r["v"] * (r["c"] - r["l"]) / max(r["h"] - r["l"], 1e-12)  # noqa: E731
    sell_expr = lambda r: r["v"] * (r["h"] - r["c"]) / max(r["h"] - r["l"], 1e-12)  # noqa: E731
    lookback = int(formation["lookback_bars"]); min_seq = int(formation["min_sequence_bars"])
    wait_limit = int(logic.get("invalidation_timeout_bars", 100))
    stop_mult = float(exits["stop_multiple"]); target_r = float(exits["target_multiple_r"])
    risk_fraction = float(logic["risk_fraction_per_trade"])

    events: list[dict] = []; trades: list[dict] = []
    active_box = None; open_trade = None
    equity = 1.0; peak = 1.0; max_dd = 0.0

    for i in range(1, n):
        row = candles[i]
        if simulate and open_trade:
            t = open_trade; d = t["direction"]; o, h, l = row["o"], row["h"], row["l"]
            stop_hit = l <= t["stop"] if d > 0 else h >= t["stop"]
            target_hit = h >= t["target"] if d > 0 else l <= t["target"]
            exit_price = exit_reason = None
            if stop_hit:
                exit_price = o if (o <= t["stop"] if d > 0 else o >= t["stop"]) else t["stop"]; exit_reason = "STOP_FIRST"
            elif target_hit:
                exit_price = t["target"]; exit_reason = "TARGET"
            if exit_price is not None:
                gross = d * (exit_price - t["entry"]) * t["units"]; cost = t["notional"] * TRANSACTION_COST; net = gross - cost
                equity += net; peak = max(peak, equity); max_dd = max(max_dd, (peak - equity) / peak if peak else 0.0)
                trades.append({**t, "exit_time": row["time"], "exit_price": exit_price, "exit_reason": exit_reason,
                               "gross_pnl": gross, "cost": cost, "net_pnl": net,
                               "net_r": net / t["risk_cash"] if t["risk_cash"] else None, "equity_after": equity})
                open_trade = None

        # In scan mode positions are owned by the execution layer, so the
        # formation search is not suppressed by a simulated open trade.
        flat = open_trade is None
        if active_box is None and flat and i >= lookback:
            start = i - lookback + 1
            bull_count = sum(bullish[start:i + 1]); bear_count = sum(bearish[start:i + 1])
            bull_pattern = bull_count >= min_seq and not bear_count >= min_seq
            bear_pattern = bear_count >= min_seq and not bull_count >= min_seq
            window = candles[start:i + 1]
            top = max(x["h"] for x in window); bottom = min(x["l"] for x in window)
            if bull_pattern and not (sum(bullish[start - 1:i]) >= min_seq and not sum(bearish[start - 1:i]) >= min_seq):
                active_box = {"top": top, "bottom": bottom, "form_i": i, "waited": 0,
                              "buy": sum(buy_expr(x) for x in window if x["h"] > bottom and x["l"] < top),
                              "sell": sum(sell_expr(x) for x in window if x["h"] > bottom and x["l"] < top)}
            elif bear_pattern and not (sum(bearish[start - 1:i]) >= min_seq and not sum(bullish[start - 1:i]) >= min_seq):
                active_box = {"top": top, "bottom": bottom, "form_i": i, "waited": 0,
                              "buy": sum(buy_expr(x) for x in window if x["h"] > bottom and x["l"] < top),
                              "sell": sum(sell_expr(x) for x in window if x["h"] > bottom and x["l"] < top)}

        if active_box:
            box = active_box
            up = row["c"] > box["top"] if breakout["price_basis"] == "CLOSE" else row["h"] > box["top"]
            down = row["c"] < box["bottom"] if breakout["price_basis"] == "CLOSE" else row["l"] < box["bottom"]
            if i > box["form_i"] and not (up or down):
                if row["h"] > box["bottom"] and row["l"] < box["top"]:
                    box["buy"] += buy_expr(row); box["sell"] += sell_expr(row)
                box["waited"] += 1
                if wait_limit and box["waited"] > wait_limit:
                    active_box = None
            elif i > box["form_i"] and (up or down):
                buy_share = box["buy"] / max(box["buy"] + box["sell"], 1e-12); sell_share = 1 - buy_share
                thr = float(volume_rule["dominance_threshold"])
                direction = 1 if up and buy_share >= thr else -1 if down and sell_share > thr else 0
                if direction and trend_filter.get("enabled"):
                    tv = trend[i]
                    if tv is None or (direction > 0 and row["c"] <= tv) or (direction < 0 and row["c"] >= tv):
                        direction = 0
                prior_avg = sma(ranges, i, int(size_filter.get("period", 20)))
                size_ok = prior_avg is not None and row["h"] - row["l"] >= prior_avg * float(size_filter.get("multiplier", 1.5))
                size_pass = not size_filter.get("enabled") or size_ok
                if direction and size_pass and atr[i] is not None:
                    risk_dist = atr[i] * stop_mult  # type: ignore[operator]
                    events.append({"signal_index": i, "signal_time": row["time"], "direction": direction,
                                   "signal_close": row["c"], "atr": atr[i], "risk_dist": risk_dist,
                                   "target_multiple_r": target_r, "buy_share": buy_share,
                                   "box_top": box["top"], "box_bottom": box["bottom"]})
                    if simulate and i + 1 < n:
                        eb = candles[i + 1]; entry = eb["o"]
                        stop = entry - direction * risk_dist; target = entry + direction * risk_dist * target_r
                        risk_cash = equity * risk_fraction; units = risk_cash / risk_dist
                        open_trade = {"direction": direction, "signal_time": row["time"], "entry_time": eb["time"],
                                      "signal_close": row["c"], "entry": entry, "stop": stop, "target": target,
                                      "risk_dist": risk_dist, "risk_cash": risk_cash, "units": units,
                                      "notional": units * entry, "buy_share": buy_share, "equity_before": equity}
                active_box = None

    if simulate and open_trade:
        t = open_trade; final = candles[-1]; exit_price = final["c"]
        gross = t["direction"] * (exit_price - t["entry"]) * t["units"]; cost = t["notional"] * TRANSACTION_COST; net = gross - cost
        equity += net; peak = max(peak, equity); max_dd = max(max_dd, (peak - equity) / peak if peak else 0.0)
        trades.append({**t, "exit_time": final["time"], "exit_price": exit_price, "exit_reason": "DATA_END_MARK_TO_CLOSE",
                       "gross_pnl": gross, "cost": cost, "net_pnl": net, "net_r": net / t["risk_cash"], "equity_after": equity})
    stats = {"ending_equity_from_1": equity, "max_drawdown_fraction": max_dd}
    return events, trades, stats


def backtest(candles: list[dict], logic: dict[str, Any]) -> dict[str, Any]:
    _events, trades, stats = _run(candles, logic, simulate=True)
    pnls = [t["net_pnl"] for t in trades]; wins = [x for x in pnls if x > 0]; losses = [x for x in pnls if x < 0]
    return {"trade_count": len(trades), "trades": trades,
            "win_rate": len(wins) / len(trades) if trades else None,
            "expectancy": sum(pnls) / len(pnls) if trades else None,
            "profit_factor": sum(wins) / abs(sum(losses)) if losses else (math.inf if wins else None),
            "net_result_equity_fraction": stats["ending_equity_from_1"] - 1, **stats}


def scan(candles: list[dict], logic: dict[str, Any]) -> list[dict]:
    """All breakout decisions over completed candles (no position simulation)."""
    events, _trades, _stats = _run(candles, logic, simulate=False)
    return events
