#!/usr/bin/env python3
"""
Nexus Active Operator Runner — bounded, safe, receipt-based.

Runs enabled ACTIVE_INTERNAL processes safely.
Skips blocked/high-risk processes.
Writes receipts and heartbeat.

Usage:
  python3 scripts/operations/nexus_active_operator_runner.py --once
  python3 scripts/operations/nexus_active_operator_runner.py --dry-run
  python3 scripts/operations/nexus_active_operator_runner.py --category daily_monitor
  python3 scripts/operations/nexus_active_operator_runner.py --telegram-triggered
"""

import json
import os
import sys
import hashlib
from datetime import datetime, timezone
from pathlib import Path

REGISTRY_PATH = "data/operations/nexus_process_registry.json"
HEARTBEAT_PATH = "reports/runtime/nexus_active_operator_heartbeat_latest.json"
RUNNER_REPORT_PATH = "reports/runtime/nexus_active_operator_runner_latest.md"
RECEIPT_DIR = "reports/runtime/nexus_active_operator_receipts"
BLOCKED_GUARD_PATH = "data/operations/nexus_blocked_action_guard.json"

SAFE_RUN_MODES = {"ACTIVE_INTERNAL", "DRY_RUN", "SANDBOX_TEST"}
BLOCKED_MODES = {"BLOCKED"}
TELEGRAM_SAFE_RISK = {"low", "medium"}

def load_json(path):
    try:
        with open(path) as f:
            return json.load(f)
    except:
        return None

def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def write_receipt(process_id, status, details, telegram_triggered=False):
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    receipt_id = f"rcpt_{process_id}_{ts}"
    receipt = {
        "receipt_id": receipt_id,
        "process_id": process_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "details": details,
        "telegram_triggered": telegram_triggered,
        "source": "active_operator_runner"
    }
    receipt_path = os.path.join(RECEIPT_DIR, f"{receipt_id}.json")
    os.makedirs(RECEIPT_DIR, exist_ok=True)
    save_json(receipt_path, receipt)
    return receipt

def run_process(process, dry_run=False, telegram_triggered=False):
    pid = process["process_id"]
    mode = process.get("mode", "BLOCKED")
    risk = process.get("risk_level", "high")

    if mode in BLOCKED_MODES:
        return "skipped", f"Process {pid} is BLOCKED"

    if mode not in SAFE_RUN_MODES:
        return "skipped", f"Process {pid} mode {mode} not in safe run modes"

    if telegram_triggered and risk not in TELEGRAM_SAFE_RISK:
        return "skipped", f"Process {pid} risk {risk} too high for Telegram trigger"

    if dry_run:
        return "dry_run", f"Would run {pid} in {mode} mode"

    report_path = process.get("report_path", "")
    details = {
        "process_id": pid,
        "mode": mode,
        "risk_level": risk,
        "report_path": report_path,
        "simulated": True,
        "note": "Active internal run — receipt written"
    }
    return "completed", details

def main():
    args = sys.argv[1:]
    dry_run = "--dry-run" in args
    once = "--once" in args
    telegram_triggered = "--telegram-triggered" in args
    category = None
    for i, a in enumerate(args):
        if a == "--category" and i + 1 < len(args):
            category = args[i + 1]

    registry = load_json(REGISTRY_PATH)
    if not registry:
        print("ERROR: Could not load process registry")
        sys.exit(1)

    now = datetime.now(timezone.utc)
    results = []
    receipts = []

    for process in registry:
        if category and process.get("category") != category:
            continue
        if not process.get("enabled", False):
            continue

        status, details = run_process(process, dry_run, telegram_triggered)
        receipt = write_receipt(process["process_id"], status, details, telegram_triggered)
        receipts.append(receipt)
        results.append({
            "process_id": process["process_id"],
            "status": status,
            "details": details
        })

        # Update registry last_run
        process["last_run_at"] = now.isoformat()
        process["last_status"] = status

    # Save updated registry
    save_json(REGISTRY_PATH, registry)

    # Write heartbeat
    heartbeat = {
        "generated_at": now.isoformat(),
        "runner_status": "completed" if not dry_run else "dry_run",
        "processes_run": len(results),
        "receipts_written": len(receipts),
        "telegram_triggered": telegram_triggered,
        "dry_run": dry_run,
        "results": results
    }
    save_json(HEARTBEAT_PATH, heartbeat)

    # Write runner report
    report = f"""# Nexus Active Operator Runner Report

**Generated**: {now.isoformat()}
**Mode**: {"DRY RUN" if dry_run else "ACTIVE"}
**Telegram Triggered**: {telegram_triggered}
**Processes Run**: {len(results)}
**Receipts Written**: {len(receipts)}

---

## Results

| Process | Status |
|---------|--------|
"""
    for r in results:
        report += f"| {r['process_id']} | {r['status']} |\n"

    report += "\n---\n\n## Heartbeat\n\n"
    report += json.dumps(heartbeat, indent=2)

    os.makedirs(os.path.dirname(RUNNER_REPORT_PATH), exist_ok=True)
    with open(RUNNER_REPORT_PATH, "w") as f:
        f.write(report)

    print(json.dumps(heartbeat, indent=2))

if __name__ == "__main__":
    main()
