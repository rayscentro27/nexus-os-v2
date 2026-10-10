"""Bounded, case-specific offline replay for Mercury's Wick Sequence v1 spec.

This is a reproducible execution adapter for one strategy case, not a shared
backtest framework. It reads only the persisted Mercury spec and a cached,
completed OANDA Practice candle snapshot. It never connects to a broker.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = Path(os.environ.get("NEXUS_WICK_REPLAY_SPEC", ROOT / "data/governed/mercury_strategy_specs/strategy_wick_sequence_breakout_v1.json"))
DATA = Path(os.environ.get("NEXUS_WICK_REPLAY_DATA", ROOT / "data/runtime/wick_sequence_oanda_eurusd_h1_2026-10-06.json"))
OUT = Path(os.environ.get("NEXUS_WICK_REPLAY_OUT", ROOT / "data/governed/wick_sequence_baseline_v1_backtest.json"))
TEST_SELECTIONS = ROOT / "data/governed/mercury_next_test_selection_receipts.jsonl"


def sma(values: list[float], index: int, length: int) -> float | None:
    if index < length:
        return None
    return sum(values[index - length:index]) / length


def ema(values: list[float], length: int) -> list[float | None]:
    """Causal EMA: each value uses only the current and prior closes."""
    out: list[float | None] = [None] * len(values)
    if length <= 0 or len(values) < length:
        return out
    alpha = 2.0 / (length + 1.0)
    out[length - 1] = sum(values[:length]) / length
    for i in range(length, len(values)):
        prior = out[i - 1]
        assert prior is not None
        out[i] = alpha * values[i] + (1.0 - alpha) * prior
    return out


def wilder_atr(rows: list[dict], period: int) -> list[float | None]:
    tr: list[float] = []
    for i, row in enumerate(rows):
        high, low, close = row["h"], row["l"], row["c"]
        tr.append(high - low if i == 0 else max(high - low, abs(high - rows[i-1]["c"]), abs(low - rows[i-1]["c"])))
    values: list[float | None] = [None] * len(rows)
    if len(rows) <= period:
        return values
    values[period] = sum(tr[1:period+1]) / period
    for i in range(period + 1, len(rows)):
        values[i] = (values[i-1] * (period - 1) + tr[i]) / period
    return values


def main() -> None:
    spec = json.loads(SPEC.read_text())
    snapshot = json.loads(DATA.read_text())
    # Trading-owned projects are authorized by the claimed durable Company
    # Case directive, not by a second Research receipt. The parent adapter
    # sets these values only after checking project ownership, claim status,
    # spec/data paths, and live-trading-off metadata.
    practice_authorized = (os.environ.get("NEXUS_WICK_EXPERIMENT_CLASS") == "PRACTICE_EXPERIMENT"
        and os.environ.get("NEXUS_WICK_LIVE_TRADING_ENABLED") == "NO"
        and os.environ.get("NEXUS_WICK_BROKER_ACCESS") == "NO")
    trading_authorized = (practice_authorized or (os.environ.get("NEXUS_WICK_TRADING_PROJECT_AUTHORIZED") == "1"
        and bool(os.environ.get("NEXUS_WICK_DIRECTIVE_ID"))
        and bool(os.environ.get("NEXUS_WICK_STRATEGY_PROJECT_ID"))
        and os.environ.get("NEXUS_WICK_LIVE_TRADING_ENABLED") == "NO"))
    if not trading_authorized:
        raise RuntimeError("DURABLE_TRADING_DIRECTIVE_AUTHORIZATION_REQUIRED")
    project_id = os.environ.get("NEXUS_WICK_STRATEGY_PROJECT_ID") or (spec.get("strategy_id") if practice_authorized else "")
    if (str(spec.get("case_id")) != "rcase_98d9635c39cf3ae5a4" or
            str(spec.get("live_trading")).lower() != "false" or
            (not practice_authorized and not project_id.startswith("strat_"))):
        raise RuntimeError("TRADING_PROJECT_SPEC_AUTHORIZATION_MISMATCH")
    logic = spec["strategy_logic"]
    formation = logic["formation"]
    breakout = logic["breakout"]
    size_filter = logic["breakout_size_filter"]
    volume_rule = logic["volume_proxy"]
    exits = logic["atr"]
    trend_filter = logic.get("trend_filter") or {"enabled": False, "kind": "NONE"}
    assert spec["case_id"] == "rcase_98d9635c39cf3ae5a4"
    assert spec["market"] == snapshot["instrument"]
    assert spec["timeframe"] == snapshot["granularity"]
    assert spec["no_lookahead"] is True and spec["live_trading"] is False
    assert snapshot["provider"] == "OANDA_PRACTICE" and snapshot["price_component"] == "MID"
    assert snapshot.get("live_endpoint_used") is False and snapshot.get("orders_placed") is False
    assert isinstance(size_filter.get("enabled"), bool), "EXPLICIT_BREAKOUT_SIZE_FILTER_SETTING_REQUIRED"

    candles = []
    for item in snapshot["candles"]:
        if not item.get("complete"):
            continue
        mid = item["mid"]
        candles.append({"o": float(mid["o"]), "h": float(mid["h"]), "l": float(mid["l"]),
                        "c": float(mid["c"]), "v": float(item["volume"]), "time": item["time"]})
    ranges = [r["h"] - r["l"] for r in candles]
    atr = wilder_atr(candles, int(exits["period"]))
    ema_period = int(trend_filter.get("period") or 200)
    trend = ema([row["c"] for row in candles], ema_period) if trend_filter.get("enabled") else [None] * len(candles)
    n = len(candles)
    bullish = [False] * n
    bearish = [False] * n
    for i, row in enumerate(candles):
        a = atr[i]
        span = row["h"] - row["l"]
        if a is None or span <= 0 or span < a * float(breakout["min_range_atr"]):
            continue
        upper = (row["h"] - max(row["o"], row["c"])) / span
        lower = (min(row["o"], row["c"]) - row["l"]) / span
        bullish[i] = lower >= float(formation["bull_lower_wick_min"]) and upper <= float(formation["bull_upper_wick_max"])
        bearish[i] = upper >= float(formation["bear_upper_wick_min"]) and lower <= float(formation["bear_lower_wick_max"])

    trades: list[dict] = []
    active_box = None
    open_trade = None
    equity = 1.0
    peak = 1.0
    max_dd = 0.0
    buy_expr = lambda row: row["v"] * (row["c"] - row["l"]) / max(row["h"] - row["l"], 1e-12)
    sell_expr = lambda row: row["v"] * (row["h"] - row["c"]) / max(row["h"] - row["l"], 1e-12)
    wait_limit = int(logic.get("invalidation_timeout_bars", 100))
    stop_mult = float(exits["stop_multiple"])
    target_r = float(exits["target_multiple_r"])
    risk_fraction = float(logic["risk_fraction_per_trade"])
    transaction_cost = float(spec.get("assumptions", {}).get("mercury_design_choices", ["0.0005"])[0].split("0.05%")[0] or 0) if False else 0.0005

    for i in range(1, n):
        row = candles[i]
        # Existing trade management is evaluated on complete bars. If both
        # levels occur in one bar, stop is deliberately processed first.
        if open_trade:
            t = open_trade
            direction = t["direction"]
            o, h, l = row["o"], row["h"], row["l"]
            stop_hit = (l <= t["stop"] if direction > 0 else h >= t["stop"])
            target_hit = (h >= t["target"] if direction > 0 else l <= t["target"])
            exit_price = None
            exit_reason = None
            if stop_hit:
                exit_price = o if (o <= t["stop"] if direction > 0 else o >= t["stop"]) else t["stop"]
                exit_reason = "STOP_FIRST"
            elif target_hit:
                exit_price = t["target"]
                exit_reason = "TARGET"
            if exit_price is not None:
                gross = direction * (exit_price - t["entry"]) * t["units"]
                cost = t["notional"] * transaction_cost
                net = gross - cost
                equity += net
                peak = max(peak, equity)
                max_dd = max(max_dd, (peak - equity) / peak if peak else 0.0)
                trades.append({**t, "exit_time": row["time"], "exit_price": exit_price,
                               "exit_reason": exit_reason, "gross_pnl": gross, "cost": cost,
                               "net_pnl": net, "net_r": net / t["risk_cash"] if t["risk_cash"] else None,
                               "equity_after": equity})
                open_trade = None

        # Formations are identified at the close of bar i, from current and
        # prior completed bars only. New boxes cannot break on their formation bar.
        if active_box is None and open_trade is None and i >= int(formation["lookback_bars"]):
            start = i - int(formation["lookback_bars"]) + 1
            bull_count = sum(bullish[start:i+1])
            bear_count = sum(bearish[start:i+1])
            bull_pattern = bull_count >= int(formation["min_sequence_bars"]) and not (bear_count >= int(formation["min_sequence_bars"]))
            bear_pattern = bear_count >= int(formation["min_sequence_bars"]) and not (bull_count >= int(formation["min_sequence_bars"]))
            if bull_pattern and not (sum(bullish[start-1:i]) >= int(formation["min_sequence_bars"]) and not (sum(bearish[start-1:i]) >= int(formation["min_sequence_bars"]))):
                active_box = {"top": max(x["h"] for x in candles[start:i+1]), "bottom": min(x["l"] for x in candles[start:i+1]),
                              "form_i": i, "waited": 0,
                              "buy": sum(buy_expr(x) for x in candles[start:i+1] if x["h"] > min(y["l"] for y in candles[start:i+1]) and x["l"] < max(y["h"] for y in candles[start:i+1])),
                              "sell": sum(sell_expr(x) for x in candles[start:i+1] if x["h"] > min(y["l"] for y in candles[start:i+1]) and x["l"] < max(y["h"] for y in candles[start:i+1]))}
            elif bear_pattern and not (sum(bearish[start-1:i]) >= int(formation["min_sequence_bars"]) and not (sum(bullish[start-1:i]) >= int(formation["min_sequence_bars"]))):
                top = max(x["h"] for x in candles[start:i+1]); bottom = min(x["l"] for x in candles[start:i+1])
                active_box = {"top": top, "bottom": bottom, "form_i": i, "waited": 0,
                              "buy": sum(buy_expr(x) for x in candles[start:i+1] if x["h"] > bottom and x["l"] < top),
                              "sell": sum(sell_expr(x) for x in candles[start:i+1] if x["h"] > bottom and x["l"] < top)}

        if active_box:
            box = active_box
            breakout_up = row["c"] > box["top"] if breakout["price_basis"] == "CLOSE" else row["h"] > box["top"]
            breakout_down = row["c"] < box["bottom"] if breakout["price_basis"] == "CLOSE" else row["l"] < box["bottom"]
            if i > box["form_i"] and not (breakout_up or breakout_down):
                if row["h"] > box["bottom"] and row["l"] < box["top"]:
                    box["buy"] += buy_expr(row); box["sell"] += sell_expr(row)
                box["waited"] += 1
                if wait_limit and box["waited"] > wait_limit:
                    active_box = None
            elif i > box["form_i"] and (breakout_up or breakout_down):
                buy_share = box["buy"] / max(box["buy"] + box["sell"], 1e-12)
                sell_share = 1 - buy_share
                direction = 1 if breakout_up and buy_share >= float(volume_rule["dominance_threshold"]) else -1 if breakout_down and sell_share > float(volume_rule["dominance_threshold"]) else 0
                if direction and trend_filter.get("enabled"):
                    trend_value = trend[i]
                    if trend_value is None or (direction > 0 and row["c"] <= trend_value) or (direction < 0 and row["c"] >= trend_value):
                        direction = 0
                prior_avg_range = sma(ranges, i, int(size_filter.get("period", 20)))
                size_ok = prior_avg_range is not None and row["h"] - row["l"] >= prior_avg_range * float(size_filter.get("multiplier", 1.5))
                size_filter_pass = not size_filter.get("enabled") or size_ok
                if direction and size_filter_pass and atr[i] is not None and i + 1 < n:
                    entry_bar = candles[i+1]
                    entry = entry_bar["o"]
                    risk_dist = atr[i] * stop_mult
                    stop = entry - direction * risk_dist
                    target = entry + direction * risk_dist * target_r
                    risk_cash = equity * risk_fraction
                    units = risk_cash / risk_dist
                    notional = units * entry
                    open_trade = {"direction": direction, "signal_time": row["time"], "entry_time": entry_bar["time"],
                                  "signal_close": row["c"], "entry": entry, "stop": stop, "target": target,
                                  "risk_dist": risk_dist, "risk_cash": risk_cash, "units": units, "notional": notional,
                                  "buy_share": buy_share, "equity_before": equity}
                active_box = None

    if open_trade:
        t = open_trade; final = candles[-1]; exit_price = final["c"]
        gross = t["direction"] * (exit_price - t["entry"]) * t["units"]
        cost = t["notional"] * transaction_cost; net = gross - cost; equity += net
        peak = max(peak, equity); max_dd = max(max_dd, (peak-equity)/peak if peak else 0.0)
        trades.append({**t,"exit_time":final["time"],"exit_price":exit_price,"exit_reason":"DATA_END_MARK_TO_CLOSE",
                       "gross_pnl":gross,"cost":cost,"net_pnl":net,"net_r":net/t["risk_cash"],"equity_after":equity})

    pnls=[t["net_pnl"] for t in trades]; wins=[x for x in pnls if x>0]; losses=[x for x in pnls if x<0]
    result={"schema_version":"nexus.case-specific-backtest-replay.v1","strategy_id":spec["strategy_id"],"case_id":spec["case_id"],
      "created_at":datetime.now(timezone.utc).isoformat(),"engine_class":"BOUNDED_CASE_SPECIFIC_OFFLINE_REPLAY; NO_SHARED_GENERAL_ENGINE_FOUND",
      "instrument":snapshot["instrument"],"timeframe":snapshot["granularity"],"data_provider":snapshot["provider"],
      "price_component":snapshot["price_component"],"bar_count":len(candles),"date_start":candles[0]["time"],"date_end":candles[-1]["time"],
      "data_sha256":hashlib.sha256(DATA.read_bytes()).hexdigest(),"spec_sha256":hashlib.sha256(SPEC.read_bytes()).hexdigest(),
      "trade_count":len(trades),"long_trades":sum(t["direction"]>0 for t in trades),"short_trades":sum(t["direction"]<0 for t in trades),
      "win_rate":len(wins)/len(trades) if trades else None,"average_win":sum(wins)/len(wins) if wins else None,
      "average_loss":sum(losses)/len(losses) if losses else None,"expectancy":sum(pnls)/len(pnls) if trades else None,
      "profit_factor":sum(wins)/abs(sum(losses)) if losses else (math.inf if wins else None),"max_drawdown_fraction":max_dd,
      "net_result_equity_fraction":equity-1,"ending_equity_from_1":equity,"transaction_cost_round_trip_notional_fraction":transaction_cost,
      "rules":{"formation":formation,"breakout":breakout,"breakout_size_filter":size_filter,"volume_proxy":volume_rule,"atr":exits,"trend_filter":trend_filter,
               "risk_fraction":risk_fraction,"same_bar_collision":"STOP_FIRST","concurrent_positions":"ONE_AT_A_TIME_TEST_ASSUMPTION"},
      "limitations":["OANDA volume is tick volume used as a proxy, not exchange-traded buyer/seller volume.",
        "Mid prices omit bid/ask spread; Mercury's 0.05% round-trip notional cost was applied as a flat proxy.",
        "This bounded replay adapter is case-specific; no reusable general deterministic strategy backtest engine was found in the canonical checkout.",
        "Historical results are not live or paper trading results."],"live_trading_enabled":False,"broker_order_api_called":False,"trades":trades}
    OUT.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    summary={k:result[k] for k in ("trade_count","long_trades","short_trades","win_rate","average_win","average_loss","expectancy","profit_factor","max_drawdown_fraction","net_result_equity_fraction","date_start","date_end")}
    print(json.dumps(summary,indent=2,allow_nan=False))

if __name__ == "__main__":
    main()
