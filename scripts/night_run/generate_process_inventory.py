#!/usr/bin/env python3
"""Part 3 — Nexus process inventory (dry-run, internal)."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import night_run_model as nm  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(); p.add_argument("--dry-run", action="store_true", default=True); p.add_argument("--json", action="store_true"); a = p.parse_args()
    processes = [{"name": n, "category": c, "status": s, "script_or_module": x} for (n, c, s, x) in nm.PROCESS_INVENTORY]
    by_status: dict[str, int] = {}
    for pr in processes:
        by_status[pr["status"]] = by_status.get(pr["status"], 0) + 1
    r = {
        "ok": True, "title": "Nexus Process Inventory", "generated_at": nm.now(), "dry_run": True,
        "processes": processes, "by_status": by_status,
        "counts": {"total": len(processes), **by_status},
        "summary": f"Inventoried {len(processes)} Nexus processes: {by_status.get('ready_to_run', 0)} ready, "
                   f"{by_status.get('blocked_by_policy', 0)} blocked by policy, {by_status.get('approval_required', 0)} approval-required.",
        "safety": nm.SAFETY,
    }
    md = ["## By status"] + [f"- {k}: {v}" for k, v in by_status.items()] + ["", "## Processes"]
    for pr in processes:
        md.append(f"- [{pr['status']}] {pr['name']} ({pr['category']}) — {pr['script_or_module']}")
    nm.write_report("nexus_process_inventory_latest", r, md)
    print(json.dumps(r, indent=2) if a.json else r["summary"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
