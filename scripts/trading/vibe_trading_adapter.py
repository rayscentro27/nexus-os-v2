#!/usr/bin/env python3
"""Safe Vibe Trading / Trading Lab adapter.

Paper/demo/backtest status only. This script never places orders, connects live broker
execution, runs auto_executor, starts schedulers, or launches persistent trading loops.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent.parent
HOME = Path.home()
RUNTIME_REPORT = ROOT / "reports" / "runtime" / "nexus_trading_lab_vibe_integration_latest.md"
MANUAL_REPORT = ROOT / "reports" / "manual_publish" / "nexus_trading_lab_vibe_integration_latest.md"

KNOWN_PATHS = [
    HOME / "vibe-trading-ai",
    HOME / "vibe-trading",
    HOME / "nexus-ai" / "trading-engine",
    HOME / "nexuslive" / "trading-engine",
    HOME / ".vibe-trading",
]

BLOCKED_COMMANDS = [
    "python3 auto_executor.py",
    "python3 nexus_trading_engine.py",
    "python3 tournament_service.py",
    "openclaw gateway",
    "curl /signal/manual",
    "curl /webhook/tradingview",
]


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(HOME))
    except ValueError:
        return str(path)


def find_vibe_status() -> dict[str, Any]:
    found = []
    safe_commands = []
    warnings = []
    for path in KNOWN_PATHS:
        if not path.exists():
            continue
        entry: dict[str, Any] = {"path": str(path), "label": rel(path), "kind": "directory" if path.is_dir() else "file"}
        if (path / "backtest" / "backtester.py").exists():
            cmd = f"python3 {path / 'backtest' / 'backtester.py'} --signals {path / 'backtest' / 'sample_signals.json'} --balance 10000 --report"
            safe_commands.append({
                "mode": "backtest",
                "command_template": cmd,
                "paper_only": True,
                "auto_run_by_adapter": False,
                "notes": "Safe only as bounded backtest simulation; adapter reports it but does not run it automatically.",
            })
            entry["has_backtester"] = True
        if (path / "auto_executor.py").exists():
            warnings.append(f"{rel(path / 'auto_executor.py')} exists and is blocked from Nexus v2 UI/adapter.")
            entry["has_auto_executor"] = True
        if (path / "nexus_trading_engine.py").exists():
            warnings.append(f"{rel(path / 'nexus_trading_engine.py')} is a persistent/engine path and is blocked here.")
            entry["has_engine"] = True
        if (path / "tournament_service.py").exists():
            warnings.append(f"{rel(path / 'tournament_service.py')} has loop/execution paths and is blocked here.")
            entry["has_tournament_service"] = True
        if path.name == ".vibe-trading":
            entry["notes"] = "Local Vibe Trading memory directory found; no executable package metadata found."
        found.append(entry)
    return {
        "connected": bool(found),
        "status": "vibe_trading_found_paper_only" if found else "vibe_trading_not_connected",
        "found_paths": found,
        "safe_commands": safe_commands,
        "blocked_commands": BLOCKED_COMMANDS,
        "warnings": warnings,
        "paper_only": True,
        "live_trading_blocked": True,
        "scheduler_started": False,
        "trade_placed": False,
    }


def write_report(report: dict[str, Any], explicit_path: str = "") -> None:
    lines = [
        "# Nexus Trading Lab / Vibe Trading Integration",
        "",
        f"- generated_at: {report['generated_at']}",
        f"- mode: {report['mode']}",
        f"- dry_run: {report['dry_run']}",
        "- paper_only: true",
        "- live_trading_blocked: true",
        "- scheduler_started: false",
        "- trade_placed: false",
        "",
        "## Status",
        "",
        f"- {report['status']['status']}",
        "",
        "## Found Paths",
    ]
    for item in report["status"]["found_paths"]:
        lines.append(f"- {item['label']}")
    if not report["status"]["found_paths"]:
        lines.append("- none")
    lines.extend(["", "## Safe Command Templates"])
    for cmd in report["status"]["safe_commands"]:
        lines.append(f"- `{cmd['command_template']}`")
    if not report["status"]["safe_commands"]:
        lines.append("- none")
    lines.extend(["", "## Blocked Commands"])
    for cmd in report["status"]["blocked_commands"]:
        lines.append(f"- `{cmd}`")
    lines.extend(["", "## Warnings"])
    for warning in report["status"]["warnings"]:
        lines.append(f"- {warning}")
    if not report["status"]["warnings"]:
        lines.append("- none")

    text = "\n".join(lines) + "\n"
    for path in (RUNTIME_REPORT, MANUAL_REPORT):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    if explicit_path:
        Path(explicit_path).parent.mkdir(parents=True, exist_ok=True)
        Path(explicit_path).write_text(json.dumps(report, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", dest="dry_run", action="store_true")
    parser.add_argument("--no-dry-run", dest="dry_run", action="store_false")
    parser.set_defaults(dry_run=True)
    parser.add_argument("--mode", choices=["backtest", "paper-report", "status", "import-report"], default="status")
    parser.add_argument("--strategy-id", default="")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--no-live-trading", action="store_true", default=True)
    parser.add_argument("--report-path", default="")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if not args.no_live_trading:
        print(json.dumps({"ok": False, "error": "no_live_trading_required"}, indent=2))
        return 2

    status = find_vibe_status()
    report = {
        "ok": True,
        "generated_at": now(),
        "mode": args.mode,
        "dry_run": args.dry_run,
        "limit": max(1, min(args.limit, 10)),
        "strategy_id": args.strategy_id or None,
        "status": status,
        "writes": ["local_report"],
        "external_actions": {
            "trade_placed": False,
            "broker_modified": False,
            "scheduler_started": False,
            "auto_executor_called": False,
            "persistent_loop_started": False,
        },
    }
    write_report(report, args.report_path)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
