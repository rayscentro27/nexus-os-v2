#!/usr/bin/env python3
"""
Nexus Recovery Check — identify stale reports, failed processes,
create safe local work orders, write recovery receipts.
"""

import json
import os
from datetime import datetime, timezone

RECOVERY_REPORT = "reports/runtime/nexus_recovery_check_latest.md"
RECOVERY_WO = "reports/runtime/nexus_recovery_work_orders_latest.json"
RECEIPT_DIR = "reports/runtime/nexus_active_operator_receipts"
REGISTRY_PATH = "data/operations/nexus_process_registry.json"

def load_json(path):
    try:
        with open(path) as f:
            return json.load(f)
    except:
        return None

def check_stale_reports():
    stale = []
    checks = [
        ("daily_monitor", "reports/runtime/nexus_daily_monitor_latest.md"),
        ("heartbeat", "reports/runtime/nexus_active_operator_heartbeat_latest.json"),
        ("runner_report", "reports/runtime/nexus_active_operator_runner_latest.md"),
        ("supabase_verification", "reports/supabase/nexus_supabase_browser_verification_latest.md"),
        ("command_center_ux", "reports/runtime/nexus_command_center_active_ux_report.md"),
        ("blocked_guard", "reports/runtime/nexus_blocked_action_guard_latest.md"),
    ]
    for name, path in checks:
        if not os.path.exists(path):
            stale.append({"name": name, "path": path, "reason": "missing"})
        else:
            age = (datetime.now().timestamp() - os.path.getmtime(path)) / 3600
            if age > 48:
                stale.append({"name": name, "path": path, "reason": f"stale ({age:.0f}h)"})
    return stale

def check_failed_processes():
    registry = load_json(REGISTRY_PATH) or []
    failed = []
    for p in registry:
        if p.get("last_status") in ("failed", "error"):
            failed.append(p)
    return failed

def create_recovery_work_orders(stale, failed):
    work_orders = []
    for s in stale:
        wo = {
            "work_order_id": f"recovery_report_{s['name']}",
            "type": "recovery",
            "target": s["path"],
            "reason": s["reason"],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "status": "created"
        }
        work_orders.append(wo)
    for f in failed:
        wo = {
            "work_order_id": f"recovery_process_{f['process_id']}",
            "type": "recovery",
            "target": f["process_id"],
            "reason": f"process failed: {f.get('last_status')}",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "status": "created"
        }
        work_orders.append(wo)
    return work_orders

def main():
    now = datetime.now(timezone.utc)
    stale = check_stale_reports()
    failed = check_failed_processes()
    work_orders = create_recovery_work_orders(stale, failed)

    receipt = {
        "receipt_id": f"recovery_{now.strftime('%Y%m%dT%H%M%SZ')}",
        "timestamp": now.isoformat(),
        "stale_reports": len(stale),
        "failed_processes": len(failed),
        "work_orders_created": len(work_orders)
    }
    os.makedirs(RECEIPT_DIR, exist_ok=True)
    with open(os.path.join(RECEIPT_DIR, f"{receipt['receipt_id']}.json"), "w") as f:
        json.dump(receipt, f, indent=2)

    with open(RECOVERY_WO, "w") as f:
        json.dump(work_orders, f, indent=2)

    report = f"""# Nexus Recovery Check

**Generated**: {now.isoformat()}

---

## Stale Reports

| Count | {len(stale)} |
|-------|---|
"""
    for s in stale:
        report += f"- {s['name']}: {s['reason']}\n"

    report += f"""
---

## Failed Processes

| Count | {len(failed)} |
|-------|---|
"""
    for f_proc in failed:
        report += f"- {f_proc['process_id']}: {f_proc.get('last_status')}\n"

    report += f"""
---

## Recovery Work Orders Created: {len(work_orders)}
"""
    for wo in work_orders:
        report += f"- {wo['work_order_id']}: {wo['reason']}\n"

    with open(RECOVERY_REPORT, "w") as f:
        f.write(report)

    print(json.dumps({"stale": len(stale), "failed": len(failed), "work_orders": len(work_orders)}, indent=2))

if __name__ == "__main__":
    main()
