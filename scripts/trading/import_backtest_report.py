#!/usr/bin/env python3
"""Import a selected Trading Lab backtest report into paper-only project metadata.

Reads one explicit safe file. Never calls broker APIs, runs trading services, starts schedulers,
places trades, imports auto_executor, or modifies credentials.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "social"))
sys.path.insert(0, str(ROOT / "scripts" / "trading"))
import _supabase as sb  # noqa: E402
from trading_enrichment import build_trading_enrichment  # noqa: E402

RUNTIME_JSON = ROOT / "reports" / "runtime" / "trading_backtest_import_latest.json"
RUNTIME_MD = ROOT / "reports" / "runtime" / "nexus_trading_backtest_importer_latest.md"
MANUAL_MD = ROOT / "reports" / "manual_publish" / "trading_backtest_import_latest.md"
MANUAL_LATEST = ROOT / "reports" / "manual_publish" / "nexus_trading_backtest_importer_latest.md"
SAMPLE = ROOT / "tests" / "fixtures" / "trading" / "sample_backtest_report.json"
SAFE_ROOTS = [
    ROOT / "tests" / "fixtures" / "trading",
    ROOT / "reports",
    ROOT / "samples",
]
TASK_TYPE = "trading_lab_backtest_import"
FEEDER_ID = "import_backtest_report"
PROOF_EVENT = "trading_backtest_report_imported"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def text(value: Any, fallback: str = "Metric not available in imported report.") -> str:
    if value is None:
        return fallback
    if isinstance(value, str):
        return value.strip() or fallback
    return str(value)


def safe_ref(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return path.name


def resolve_input(args) -> tuple[Path | None, str | None]:
    if args.sample:
        return SAMPLE, None
    if not args.input_file:
        return None, "input_file_required_or_use_sample"
    path = Path(args.input_file).expanduser()
    if not path.is_absolute():
        path = (ROOT / path).resolve()
    else:
        path = path.resolve()
    return path, None


def is_safe_path(path: Path) -> bool:
    resolved = path.resolve()
    for root in SAFE_ROOTS:
        try:
            resolved.relative_to(root.resolve())
            return True
        except ValueError:
            continue
    return False


def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def flatten_metrics(data: dict[str, Any]) -> dict[str, Any]:
    metrics = data.get("metrics") if isinstance(data.get("metrics"), dict) else {}
    summary = data.get("summary") if isinstance(data.get("summary"), dict) else {}
    merged = {**summary, **metrics}
    aliases = {
        "win_rate": "win_rate_pct",
        "win_rate_percent": "win_rate_pct",
        "return_pct": "total_return_pct",
        "total_pnl_pct": "total_return_pct",
        "max_dd_pct": "max_drawdown_pct",
        "max_drawdown": "max_drawdown_pct",
        "trades": "trade_count",
        "total_trades": "trade_count",
        "total_signals": "trade_count",
    }
    for old, new in aliases.items():
        if old in merged and new not in merged:
            merged[new] = merged[old]
    return merged


def parse_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(errors="ignore"))
    if isinstance(data, list):
        return {
            "strategy_name": path.stem,
            "instrument": "Metric not available in imported report.",
            "timeframe": "Metric not available in imported report.",
            "metrics": {"trade_count": len(data)},
            "summary": f"Imported JSON list with {len(data)} rows.",
            "raw_shape": "list",
        }
    if not isinstance(data, dict):
        return {"strategy_name": path.stem, "metrics": {}, "summary": "Imported JSON report without object fields."}
    return {
        "strategy_name": text(data.get("strategy_name") or data.get("strategy") or data.get("name"), path.stem),
        "instrument": text(data.get("instrument") or data.get("symbol") or data.get("market")),
        "market": text(data.get("market")),
        "timeframe": text(data.get("timeframe")),
        "date_range": data.get("date_range") or {"start": data.get("start_date"), "end": data.get("end_date")},
        "metrics": flatten_metrics(data),
        "summary": text(data.get("summary") or data.get("notes")),
        "risk_notes": data.get("risk_notes") if isinstance(data.get("risk_notes"), list) else [],
        "raw_shape": "object",
    }


def parse_csv(path: Path) -> dict[str, Any]:
    with path.open(newline="", errors="ignore") as fh:
        rows = list(csv.DictReader(fh))
    metrics: dict[str, Any] = {"trade_count": len(rows)}
    if rows and len(rows) == 1:
        row = rows[0]
        for key, value in row.items():
            normalized = key.strip().lower().replace(" ", "_")
            metrics[normalized] = value
    return {
        "strategy_name": path.stem,
        "instrument": "Metric not available in imported report.",
        "timeframe": "Metric not available in imported report.",
        "metrics": flatten_metrics({"metrics": metrics}),
        "summary": f"Imported CSV report with {len(rows)} rows.",
        "risk_notes": ["CSV importer uses available header metrics only."],
        "raw_shape": "csv",
    }


def parse_text(path: Path) -> dict[str, Any]:
    content = path.read_text(errors="ignore")[:4000]
    return {
        "strategy_name": path.stem,
        "instrument": "Metric not available in imported report.",
        "timeframe": "Metric not available in imported report.",
        "metrics": {},
        "summary": content[:700] or "Imported text/Markdown report.",
        "risk_notes": ["Structured metrics were not available in text import."],
        "raw_shape": "text",
    }


def parse_report(path: Path) -> dict[str, Any]:
    suffix = path.suffix.lower()
    if suffix == ".json":
        return parse_json(path)
    if suffix == ".csv":
        return parse_csv(path)
    if suffix in {".md", ".txt"}:
        return parse_text(path)
    raise ValueError(f"unsupported_format:{suffix}")


def duplicate_task(strategy_name: str, source_ref: str, report_hash: str) -> dict[str, Any] | None:
    query = (
        f"select=id,status,payload&task_type=eq.{sb.q(TASK_TYPE)}"
        f"&payload->>report_hash=eq.{sb.q(report_hash)}"
        "&limit=1"
    )
    _status, rows = sb.get("task_requests", query)
    if isinstance(rows, list) and rows:
        return rows[0]
    query = (
        f"select=id,status,payload&task_type=eq.{sb.q(TASK_TYPE)}"
        f"&payload->>strategy_name=eq.{sb.q(strategy_name)}"
        f"&payload->>source_file_reference=eq.{sb.q(source_ref)}"
        "&limit=1"
    )
    _status, rows = sb.get("task_requests", query)
    return rows[0] if isinstance(rows, list) and rows else None


def create_task(parsed: dict[str, Any], enrichment: dict[str, Any], source_ref: str, report_hash: str) -> str | None:
    payload = {
        "source": FEEDER_ID,
        "feeder_id": FEEDER_ID,
        "department": "trading_lab",
        "owner_tab": "trading",
        "project_type": "paper_backtest_report",
        "title": parsed["strategy_name"],
        "paper_only": True,
        "live_trading_blocked": True,
        "strategy_name": parsed["strategy_name"],
        "instrument": parsed.get("instrument"),
        "market": parsed.get("market"),
        "timeframe": parsed.get("timeframe"),
        "metrics": parsed.get("metrics", {}),
        "risk_notes": enrichment.get("risk_notes", []),
        "project_enrichment": enrichment,
        "source_file_reference": source_ref,
        "report_hash": report_hash,
        "unique_key": f"backtest_import:{report_hash}",
        "summary": enrichment.get("summary"),
        "recommendation": enrichment.get("recommendation"),
        "proposed_schedule": enrichment.get("proposed_schedule"),
        "next_action": enrichment.get("next_action"),
        "score": enrichment.get("score"),
    }
    row = {
        "task_type": TASK_TYPE,
        "requested_by": FEEDER_ID,
        "sensitivity": "internal_summary",
        "allowed_data_scope": ["public", "internal_summary", "paper_trading_research"],
        "forbidden_data": ["customer_private", "credit_sensitive", "funding_sensitive", "auth_sensitive", "secrets", "broker_credentials"],
        "assigned_worker_type": "trading_research_worker",
        "hermes_visibility": "summary",
        "status": "backtested",
        "payload": payload,
        "result_summary": enrichment.get("recommendation", "Paper backtest imported.")[:500],
    }
    _status, rows = sb.insert("task_requests", row)
    return rows[0]["id"] if isinstance(rows, list) and rows else None


def create_event(task_id: str | None, parsed: dict[str, Any], source_ref: str, enrichment: dict[str, Any]) -> str | None:
    _status, rows = sb.insert("nexus_events", {
        "lane": "trading",
        "source": FEEDER_ID,
        "action": PROOF_EVENT,
        "status": "success",
        "title": f"Backtest import: {parsed['strategy_name']}"[:80],
        "summary": f"score {enrichment.get('score')} · paper-only import from {source_ref}",
        "payload": {
            "event_type": PROOF_EVENT,
            "task_request_id": task_id,
            "strategy_name": parsed["strategy_name"],
            "source_file_reference": source_ref,
            "metrics_summary": parsed.get("metrics", {}),
            "paper_only": True,
            "live_trading_blocked": True,
        },
    })
    return rows[0]["id"] if isinstance(rows, list) and rows else None


def attach_event(task_id: str, event_id: str | None, parsed: dict[str, Any], enrichment: dict[str, Any], source_ref: str, report_hash: str) -> None:
    if not event_id:
        return
    enrichment = {**enrichment, "proof_event_id": event_id}
    payload = {
        "source": FEEDER_ID,
        "feeder_id": FEEDER_ID,
        "department": "trading_lab",
        "owner_tab": "trading",
        "project_type": "paper_backtest_report",
        "title": parsed["strategy_name"],
        "paper_only": True,
        "live_trading_blocked": True,
        "strategy_name": parsed["strategy_name"],
        "instrument": parsed.get("instrument"),
        "market": parsed.get("market"),
        "timeframe": parsed.get("timeframe"),
        "metrics": parsed.get("metrics", {}),
        "risk_notes": enrichment.get("risk_notes", []),
        "project_enrichment": enrichment,
        "source_file_reference": source_ref,
        "report_hash": report_hash,
        "unique_key": f"backtest_import:{report_hash}",
        "summary": enrichment.get("summary"),
        "recommendation": enrichment.get("recommendation"),
        "proposed_schedule": enrichment.get("proposed_schedule"),
        "next_action": enrichment.get("next_action"),
        "score": enrichment.get("score"),
        "proof_event_id": event_id,
    }
    sb.update("task_requests", f"id=eq.{sb.q(task_id)}", {"payload": payload})


def write_reports(report: dict[str, Any], explicit_path: str = "") -> None:
    RUNTIME_JSON.parent.mkdir(parents=True, exist_ok=True)
    RUNTIME_JSON.write_text(json.dumps(report, indent=2))
    lines = [
        "# Nexus Trading Backtest Importer",
        "",
        f"- generated_at: {report['generated_at']}",
        f"- dry_run: {report['dry_run']}",
        "- paper_only: true",
        "- live_trading_blocked: true",
        "- trade_placed: false",
        "- broker_api_called: false",
        "- scheduler_started: false",
        "",
        "## Source",
        f"- {report['source_file_reference']}",
        "",
        "## Parsed Metrics",
    ]
    for key, value in sorted(report["parsed"].get("metrics", {}).items()):
        lines.append(f"- {key}: {value}")
    lines.extend([
        "",
        "## Enrichment",
        f"- score: {report['enrichment'].get('score')}",
        f"- recommendation: {report['enrichment'].get('recommendation')}",
        f"- next_action: {report['enrichment'].get('next_action')}",
        "",
        "## Write Result",
        f"- supabase_write: {report['supabase_write']}",
        f"- duplicate: {report.get('duplicate', False)}",
        f"- task_request_id: {report.get('task_request_id') or 'none'}",
        f"- nexus_event_id: {report.get('nexus_event_id') or 'none'}",
    ])
    md = "\n".join(lines) + "\n"
    for path in (RUNTIME_MD, MANUAL_MD, MANUAL_LATEST):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(md)
    if explicit_path:
        p = Path(explicit_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(report, indent=2) if p.suffix.lower() == ".json" else md)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-file", default="")
    parser.add_argument("--sample", action="store_true")
    parser.add_argument("--strategy-id", default="")
    parser.add_argument("--dry-run", dest="dry_run", action="store_true")
    parser.add_argument("--no-dry-run", dest="dry_run", action="store_false")
    parser.set_defaults(dry_run=True)
    parser.add_argument("--report-path", default="")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--no-live-trading", action="store_true", default=True)
    args = parser.parse_args()

    if not args.no_live_trading:
        print(json.dumps({"ok": False, "error": "no_live_trading_required"}, indent=2))
        return 2

    path, error = resolve_input(args)
    if error or path is None:
        print(json.dumps({"ok": False, "error": error}, indent=2))
        return 2
    if not path.exists() or not path.is_file():
        print(json.dumps({"ok": False, "error": "input_file_missing", "input_file": str(path)}, indent=2))
        return 2
    if not is_safe_path(path):
        print(json.dumps({"ok": False, "error": "input_file_outside_allowed_paths", "input_file": str(path)}, indent=2))
        return 2

    try:
        parsed = parse_report(path)
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"ok": False, "error": str(exc), "input_file": str(path)}, indent=2))
        return 2

    if args.strategy_id:
        parsed["strategy_id"] = args.strategy_id
    source_ref = safe_ref(path)
    h = file_hash(path)
    enrichment = build_trading_enrichment(parsed, source_ref)

    duplicate = None
    task_id = None
    event_id = None
    supabase_write = False
    if not args.dry_run:
        if not sb.configured():
            print(json.dumps({"ok": False, "error": "supabase_not_configured"}, indent=2))
            return 2
        duplicate = duplicate_task(parsed["strategy_name"], source_ref, h)
        if duplicate:
            task_id = duplicate.get("id")
        else:
            task_id = create_task(parsed, enrichment, source_ref, h)
            event_id = create_event(task_id, parsed, source_ref, enrichment)
            if task_id:
                attach_event(task_id, event_id, parsed, enrichment, source_ref, h)
            supabase_write = bool(task_id and not duplicate)

    report = {
        "ok": True,
        "generated_at": now(),
        "dry_run": args.dry_run,
        "source_file_reference": source_ref,
        "report_hash": h,
        "parsed": parsed,
        "enrichment": enrichment,
        "safety": {
            "paper_only": True,
            "live_trading_blocked": True,
            "trade_placed": False,
            "broker_api_called": False,
            "auto_executor_called": False,
            "scheduler_started": False,
            "persistent_loop_started": False,
        },
        "supabase_write": supabase_write,
        "duplicate": bool(duplicate),
        "task_request_id": task_id,
        "nexus_event_id": event_id,
        "writes": ["local_json_report", "local_markdown_report"] + ([] if args.dry_run or duplicate else ["task_requests", "nexus_events"]),
    }
    write_reports(report, args.report_path)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
