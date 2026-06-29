#!/usr/bin/env python3
"""Run Nexus safe internal activation repeatedly with heartbeat and cycle history."""
from __future__ import annotations

import argparse
import json
import signal
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from activation_common import MANUAL, RUNTIME, SAFETY, ensure_dirs, now, write_json  # noqa: E402

STOP_REQUESTED = False


def stop_handler(_signum: int, _frame: Any) -> None:
    global STOP_REQUESTED
    STOP_REQUESTED = True


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def write_status(payload: dict[str, Any]) -> None:
    write_json(RUNTIME / "continuous_loop_status_latest.json", payload)
    lines = [
        "# Nexus Continuous Loop Status", "",
        f"- Is Nexus running?: {str(payload['is_nexus_running']).lower()}",
        f"- Last cycle time: {payload.get('last_cycle_time')}",
        f"- Next cycle time: {payload.get('next_cycle_time')}",
        f"- Systems updated: {', '.join(payload.get('systems_updated', []))}",
        f"- New opportunities: {payload.get('new_opportunities', 0)}",
        f"- New drafts: {payload.get('new_drafts', 0)}",
        f"- New approvals: {payload.get('new_approvals', 0)}",
        f"- New blockers: {payload.get('new_blockers', 0)}",
        f"- Trading/demo status: {payload.get('trading_demo_status')}",
        f"- Subscription status: {payload.get('subscription_status')}",
        f"- Feedback processed: {payload.get('feedback_processed', [])}",
        f"- Hermes recommends now: {payload.get('hermes_recommendation')}",
        f"- Single next money action: {payload.get('single_next_money_action')}",
        "- external_action_performed: false",
        "- money_spent: false",
        "- public_content_published: false",
        "- client_contacted: false",
        "- real_money_trade_placed: false",
    ]
    MANUAL.mkdir(parents=True, exist_ok=True)
    (MANUAL / "continuous_loop_status_latest.md").write_text("\n".join(lines) + "\n")


def cycle(cycle_number: int, interval_minutes: float, is_continuous: bool) -> dict[str, Any]:
    started = now()
    cmd = [sys.executable, str(ROOT / "scripts" / "activation" / "run_nexus_full_activation.py"),
           "--run-all", "--json", "--continuous-cycle"]
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=900)
    schedule_cmd = [sys.executable, str(ROOT / "scripts" / "activation" / "run_automation_schedule_registry.py"), "--json", "--run-loop-safe"]
    schedule_proc = subprocess.run(schedule_cmd, cwd=ROOT, capture_output=True, text=True, timeout=900)
    activation = load_json(RUNTIME / "nexus_full_activation_latest.json")
    hermes = load_json(RUNTIME / "hermes_current_brief_latest.json")
    trading = load_json(RUNTIME / "trading_activation_latest.json")
    subscription = load_json(RUNTIME / "subscription_engine_activation_latest.json")
    counts = activation.get("counts", {})
    finished_dt = datetime.now(timezone.utc)
    next_dt = finished_dt + timedelta(minutes=interval_minutes) if is_continuous else None
    record = {
        "cycle": cycle_number, "cycle_started_at": started, "cycle_completed_at": finished_dt.isoformat(),
        "ok": bool(activation.get("ok", proc.returncode == 0)), "activation_exit_code": proc.returncode,
        "activation_error": proc.stderr[-1000:] if proc.returncode else "",
        "automation_schedule_exit_code": schedule_proc.returncode,
        "automation_schedule_error": schedule_proc.stderr[-1000:] if schedule_proc.returncode else "",
        "is_nexus_running": is_continuous and not STOP_REQUESTED,
        "last_cycle_time": finished_dt.isoformat(), "next_cycle_time": next_dt.isoformat() if next_dt else None,
        "systems_updated": activation.get("systems_activated", []),
        "new_opportunities": counts.get("opportunities", 0), "new_drafts": counts.get("drafts", 0),
        "new_approvals": counts.get("approval_cards", 0), "new_blockers": len(activation.get("blocked_items", [])),
        "trading_demo_status": trading.get("status", "paper_only"),
        "subscription_status": subscription.get("status", "unknown"),
        "feedback_processed": activation.get("feedback_processed", []),
        "hermes_recommendation": hermes.get("recommendation", activation.get("next_money_action", "Review the $97 offer.")),
        "single_next_money_action": activation.get("next_money_action", "Approve the $97 offer."),
        "external_action_performed": False, "money_spent": False, "public_content_published": False,
        "client_contacted": False, "real_money_trade_placed": False, "demo_trade_placed": False,
        "heartbeat": finished_dt.isoformat(), "safe_internal": True,
    }
    with (RUNTIME / "continuous_loop_history.jsonl").open("a") as handle:
        handle.write(json.dumps(record) + "\n")
    write_json(RUNTIME / "continuous_loop_heartbeat_latest.json", {"cycle": cycle_number, "heartbeat": record["heartbeat"], "ok": record["ok"], **SAFETY})
    write_status(record)
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--interval-minutes", type=float, default=30)
    parser.add_argument("--max-cycles", type=int)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--safe-internal", action="store_true", default=True)
    parser.add_argument("--local-only", action="store_true", default=True)
    parser.add_argument("--feedback-enabled", action="store_true")
    parser.add_argument("--heartbeat", action="store_true")
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    if args.interval_minutes <= 0:
        parser.error("--interval-minutes must be greater than zero")
    ensure_dirs()
    signal.signal(signal.SIGINT, stop_handler)
    signal.signal(signal.SIGTERM, stop_handler)
    max_cycles = 1 if args.once else args.max_cycles
    cycle_number = 0
    last: dict[str, Any] = {}
    try:
        while not STOP_REQUESTED and (max_cycles is None or cycle_number < max_cycles):
            cycle_number += 1
            will_continue = not args.once and (max_cycles is None or cycle_number < max_cycles)
            try:
                last = cycle(cycle_number, args.interval_minutes, will_continue)
            except Exception as exc:  # noqa: BLE001
                last = {"cycle": cycle_number, "ok": False, "is_nexus_running": will_continue,
                        "last_cycle_time": now(), "next_cycle_time": None, "error": str(exc), **SAFETY}
                with (RUNTIME / "continuous_loop_history.jsonl").open("a") as handle:
                    handle.write(json.dumps(last) + "\n")
                write_status({**last, "systems_updated": [], "trading_demo_status": "paper_only",
                              "subscription_status": "cycle_failed", "feedback_processed": [],
                              "hermes_recommendation": "Inspect the failed cycle, then rerun safe internal activation.",
                              "single_next_money_action": "Do not perform external actions until the internal cycle is healthy."})
            if will_continue and not STOP_REQUESTED:
                deadline = time.monotonic() + args.interval_minutes * 60
                while not STOP_REQUESTED and time.monotonic() < deadline:
                    time.sleep(min(1, max(0, deadline - time.monotonic())))
    finally:
        if last:
            last = {**last, "is_nexus_running": False, "next_cycle_time": None, "shutdown_at": now(), "shutdown_safe": True}
            write_status(last)
    if args.json:
        print(json.dumps(last, indent=2))
    else:
        print(f"Nexus loop completed {cycle_number} cycle(s); ok={last.get('ok', False)}")
    return 0 if last.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
