"""Deterministic Trading Lab enrichment.

No external AI. No broker calls. No live-trading recommendation.
"""
from __future__ import annotations

from typing import Any


def num(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = value.strip().replace("%", "")
        try:
            return float(cleaned)
        except ValueError:
            return None
    return None


def text(value: Any, fallback: str = "Metric not available in imported report.") -> str:
    if value is None:
        return fallback
    if isinstance(value, str):
        return value.strip() or fallback
    return str(value)


def score_backtest(metrics: dict[str, Any]) -> int:
    score = 50
    win_rate = num(metrics.get("win_rate_pct"))
    profit_factor = num(metrics.get("profit_factor"))
    total_return = num(metrics.get("total_return_pct") or metrics.get("return_pct"))
    drawdown = num(metrics.get("max_drawdown_pct"))
    trade_count = num(metrics.get("trade_count") or metrics.get("total_trades") or metrics.get("total_signals"))

    if win_rate is not None:
        if win_rate >= 55:
            score += 10
        elif win_rate < 45:
            score -= 8
    else:
        score -= 6

    if profit_factor is not None:
        if profit_factor >= 1.5:
            score += 12
        elif profit_factor < 1:
            score -= 12
    else:
        score -= 8

    if total_return is not None:
        if total_return > 0:
            score += min(10, int(total_return / 2))
        elif total_return < 0:
            score -= 10
    else:
        score -= 5

    if drawdown is not None:
        if drawdown <= 8:
            score += 8
        elif drawdown >= 20:
            score -= 15
    else:
        score -= 8

    if trade_count is not None:
        if trade_count >= 50:
            score += 8
        elif trade_count < 20:
            score -= 12
    else:
        score -= 8

    return max(0, min(100, score))


def build_trading_enrichment(parsed: dict[str, Any], source_file: str) -> dict[str, Any]:
    metrics = parsed.get("metrics") if isinstance(parsed.get("metrics"), dict) else {}
    strategy = text(parsed.get("strategy_name"), "Unnamed paper strategy")
    instrument = text(parsed.get("instrument"))
    timeframe = text(parsed.get("timeframe"))
    score = score_backtest(metrics)

    risk_notes: list[str] = []
    drawdown = num(metrics.get("max_drawdown_pct"))
    trades = num(metrics.get("trade_count") or metrics.get("total_trades") or metrics.get("total_signals"))
    pf = num(metrics.get("profit_factor"))

    if drawdown is None:
        risk_notes.append("Max drawdown is missing.")
    elif drawdown >= 20:
        risk_notes.append("Drawdown is high for a paper strategy.")
    if trades is None:
        risk_notes.append("Trade count is missing.")
    elif trades < 20:
        risk_notes.append("Trade count is low; overfit risk is elevated.")
    if pf is None:
        risk_notes.append("Profit factor is missing.")
    elif pf < 1:
        risk_notes.append("Profit factor is below 1.0.")
    if not metrics:
        risk_notes.append("Structured metrics were not available in the imported report.")
    risk_notes.append("Paper/backtest result is not live-trading proof.")
    risk_notes.append("Live trading and broker execution remain blocked.")

    pros: list[str] = []
    cons: list[str] = []
    win_rate = num(metrics.get("win_rate_pct"))
    total_return = num(metrics.get("total_return_pct") or metrics.get("return_pct"))

    if pf is not None and pf >= 1.5:
        pros.append("Profit factor is above the initial research threshold.")
    if drawdown is not None and drawdown <= 8:
        pros.append("Drawdown is relatively contained in this report.")
    if trades is not None and trades >= 50:
        pros.append("Trade count is large enough for a first-pass review.")
    if total_return is not None and total_return > 0:
        pros.append("Backtest return is positive.")
    if not pros:
        pros.append("Report is now structured for paper-only review.")

    if drawdown is None or drawdown >= 20:
        cons.append("Drawdown risk needs more review.")
    if trades is None or trades < 20:
        cons.append("Sample size is weak or unavailable.")
    if win_rate is None:
        cons.append("Win rate is missing.")
    if pf is None:
        cons.append("Profit factor is missing.")
    if not cons:
        cons.append("Still requires out-of-sample/paper validation before any further work.")

    if score >= 70:
        recommendation = "Continue paper demo and compare against a baseline; do not live trade."
        next_action = "Create a paper-demo comparison plan and request a second backtest window."
    elif score >= 45:
        recommendation = "Run another bounded backtest and review risk assumptions before paper demo."
        next_action = "Request more research or compare against a baseline strategy."
    else:
        recommendation = "Park or revise the strategy until metrics and risk data improve."
        next_action = "Send to Ops/risk review or park the strategy."

    summary = (
        f"Imported paper backtest for {strategy}. Instrument: {instrument}. Timeframe: {timeframe}. "
        f"Score: {score}/100. Live trading is blocked."
    )

    return {
        "enrichment_status": "scored",
        "enrichment_source": "deterministic",
        "summary": summary,
        "pros": pros,
        "cons": cons,
        "recommendation": recommendation,
        "proposed_schedule": "Manual paper-research review only; no scheduler or live execution.",
        "next_action": next_action,
        "risk_notes": risk_notes,
        "risk_triggers": ["live_trading_blocked", "paper_only_required"],
        "score": score,
        "confidence": 0.72 if metrics else 0.45,
        "paper_only": True,
        "live_trading_blocked": True,
        "backtest_source": source_file,
        "hermes_memory_summary": f"{strategy}: paper-only backtest import scored {score}/100; live trading blocked.",
        "category": "paper_backtest_report",
        "destination": "Trading Lab",
        "approval_required": False,
    }
