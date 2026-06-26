"""Trading Lab paper/demo research feeder.

Creates research-only Trading Lab project cards. Never places trades, calls broker execution,
starts schedulers, runs auto_executor, or launches persistent loops.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from feeders.common import ROOT, make_candidate, run_candidates, score_value, table_rows, text

FEEDER_ID = "trading_lab_demo_research_feeder"
TASK_TYPE = "trading_lab_research_project"
PROOF_EVENT = "trading_lab_research_project_created"


def _paper_payload(candidate: dict[str, Any], *, status: str, risk_notes: list[str]) -> dict[str, Any]:
    payload = candidate["payload"]
    payload["paper_only"] = True
    payload["live_trading_blocked"] = True
    payload["vibe_trading_status"] = status
    payload["risk_notes"] = risk_notes
    enrichment = dict(payload.get("project_enrichment") or {})
    enrichment.update({
        "risk_notes": risk_notes,
        "paper_only": True,
        "live_trading_blocked": True,
        "vibe_trading_status": status,
    })
    payload["project_enrichment"] = enrichment
    return candidate


def _paper_status_candidate(path: Path) -> dict[str, Any]:
    rel = str(path.relative_to(ROOT))
    return _paper_payload(make_candidate(
        feeder_id=FEEDER_ID, task_type=TASK_TYPE, proof_event_type=PROOF_EVENT,
        department="trading_lab", owner_tab="trading", project_type="paper_strategy_research",
        unique_key=f"local_report:{rel}", source_kind="local_report", source_id=rel,
        title="Trading Lab paper-only integration status",
        summary=f"Safe local Trading Lab/Vibe Trading status report is available at {rel}. Live execution is blocked.",
        pros=["Documents Vibe Trading status without running it.", "Paper/demo/backtest research only."],
        cons=["Does not validate strategy profitability.", "Broker/live execution remains blocked."],
        recommendation="Review status and only run bounded backtests through explicit paper-only commands.",
        proposed_schedule="Manual research review only; no trading scheduler.",
        next_action="Open Trading Lab and inspect the paper-only status card.",
        score=55,
        status="paper_demo",
        risk_triggers=["live_trading_blocked"],
        data_sources=["local_report", "vibe_trading_adapter"],
        metadata_extra={"paper_only": True, "live_trading_blocked": True, "vibe_trading_status": "status_report_available"},
    ), status="status_report_available", risk_notes=["live trading blocked", "broker execution blocked", "auto_executor blocked"])


def _strategy_candidate(row: dict[str, Any]) -> dict[str, Any]:
    title = text(row.get("title") or row.get("strategy_name") or row.get("name"), "Trading strategy candidate")
    return _paper_payload(make_candidate(
        feeder_id=FEEDER_ID, task_type=TASK_TYPE, proof_event_type=PROOF_EVENT,
        department="trading_lab", owner_tab="trading", project_type="paper_strategy_research",
        unique_key=f"trading_strategy_candidates:{row.get('id')}", source_kind="trading_strategy_candidates", source_id=text(row.get("id")),
        title=f"Paper strategy research: {title}",
        summary=text(row.get("summary") or row.get("thesis") or row.get("description"), "Existing strategy candidate requires paper-only research review."),
        pros=["Existing strategy research row.", "Can be reviewed without execution."],
        cons=["Needs backtest and risk review before any demo loop; live trading remains blocked."],
        recommendation="Run bounded backtest/report only; do not connect live execution.",
        proposed_schedule="Manual backtest review only.",
        next_action="Create a backtest/report task or park the strategy.",
        score=score_value(row.get("score"), row.get("total_score"), fallback=45),
        status=text(row.get("status"), "proposed"),
        risk_triggers=["live_trading_blocked"],
        data_sources=["trading_strategy_candidates"],
        metadata_extra={"paper_only": True, "live_trading_blocked": True},
    ), status="strategy_research_only", risk_notes=["requires backtest", "live trading blocked"])


def _backtest_candidate(row: dict[str, Any]) -> dict[str, Any]:
    title = text(row.get("title") or row.get("strategy_id") or row.get("symbol"), "Backtest result")
    return _paper_payload(make_candidate(
        feeder_id=FEEDER_ID, task_type=TASK_TYPE, proof_event_type=PROOF_EVENT,
        department="trading_lab", owner_tab="trading", project_type="paper_strategy_research",
        unique_key=f"trading_backtests:{row.get('id')}", source_kind="trading_backtests", source_id=text(row.get("id")),
        title=f"Backtest review: {title}",
        summary=text(row.get("summary") or row.get("notes"), "Existing backtest result needs score/risk review."),
        pros=["Backtest data is research-only.", "Can inform strategy scorecards."],
        cons=["Backtest is not proof of live profitability.", "Live/funded execution is blocked."],
        recommendation="Review drawdown, win rate, assumptions, and sample size before any paper demo.",
        proposed_schedule="Manual risk review this week.",
        next_action="Create a strategy scorecard or request more historical testing.",
        score=score_value(row.get("score"), row.get("return_pct"), row.get("win_rate_pct"), fallback=50),
        status="backtested",
        risk_triggers=["live_trading_blocked"],
        data_sources=["trading_backtests"],
        metadata_extra={"paper_only": True, "live_trading_blocked": True},
    ), status="backtest_review_only", risk_notes=["backtest is not live proof", "funded execution blocked"])


def _paper_trade_candidate(row: dict[str, Any]) -> dict[str, Any]:
    title = text(row.get("strategy_name") or row.get("symbol") or row.get("title"), "Paper/demo signal")
    return _paper_payload(make_candidate(
        feeder_id=FEEDER_ID, task_type=TASK_TYPE, proof_event_type=PROOF_EVENT,
        department="trading_lab", owner_tab="trading", project_type="paper_strategy_research",
        unique_key=f"paper_trading_journal_entries:{row.get('id')}", source_kind="paper_trading_journal_entries", source_id=text(row.get("id")),
        title=f"Paper demo signal review: {title}",
        summary=text(row.get("summary") or row.get("notes"), "Paper/demo signal journal entry needs research review."),
        pros=["Paper/demo only.", "No live order is placed by this feeder."],
        cons=["Paper fills can diverge from live execution.", "No funded account path is exposed."],
        recommendation="Review signal quality and risk notes; keep as research unless Ray separately approves a paper-only test plan.",
        proposed_schedule="Manual review only.",
        next_action="Review the paper signal and update strategy notes.",
        score=score_value(row.get("score"), row.get("risk_score"), fallback=45),
        status="paper_demo",
        risk_triggers=["live_trading_blocked"],
        data_sources=["paper_trading_journal_entries"],
        metadata_extra={"paper_only": True, "live_trading_blocked": True},
    ), status="paper_demo_only", risk_notes=["paper fill only", "no broker order placed by Nexus v2"])


def build_candidates(sb, limit: int) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    report = ROOT / "reports" / "manual_publish" / "nexus_trading_lab_vibe_integration_latest.md"
    if report.exists():
        candidates.append(_paper_status_candidate(report))
    for row in table_rows(sb, "trading_strategy_candidates", f"select=*&order=created_at.desc&limit={limit * 2}"):
        candidates.append(_strategy_candidate(row))
    for row in table_rows(sb, "trading_backtests", f"select=*&order=created_at.desc&limit={limit * 2}"):
        candidates.append(_backtest_candidate(row))
    for row in table_rows(sb, "paper_trading_journal_entries", f"select=*&order=created_at.desc&limit={limit * 2}"):
        candidates.append(_paper_trade_candidate(row))
    return candidates


def run(sb, *, dry_run: bool, limit: int) -> dict[str, Any]:
    result = run_candidates(sb, feeder_id=FEEDER_ID, task_type=TASK_TYPE, proof_event_type=PROOF_EVENT,
                            dry_run=dry_run, limit=limit, candidates=build_candidates(sb, limit))
    result["paper_only"] = True
    result["live_trading_blocked"] = True
    return result
