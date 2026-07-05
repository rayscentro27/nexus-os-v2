#!/usr/bin/env python3
"""
Nexus OS v2 — Daily Monitor Script
Prompt 2: Phase S

Reads process registry, receipts, reports, and system state to produce
a daily markdown report and JSON summary for the dashboard.
"""

import os
import json
from datetime import datetime, timezone

RUNTIME_DIR = "reports/runtime"
DAILY_MD = os.path.join(RUNTIME_DIR, "nexus_daily_monitor_latest.md")
DAILY_JSON = os.path.join(RUNTIME_DIR, "nexus_daily_monitor_latest.json")
REGISTRY_JSON = os.path.join(RUNTIME_DIR, "nexus_activation_master_registry.json")
HEALTH_JSON = os.path.join(RUNTIME_DIR, "nexus_system_health_latest.json")
RECEIPT_DIR = RUNTIME_DIR

def load_json(path):
    try:
        with open(path) as f:
            return json.load(f)
    except:
        return None

def get_report_stats():
    stats = {"total": 0, "categories": {}}
    for root, dirs, files in os.walk("reports"):
        for f in files:
            if f.endswith(('.md', '.json')):
                stats["total"] += 1
                cat = os.path.relpath(root, "reports").split(os.sep)[0]
                stats["categories"][cat] = stats["categories"].get(cat, 0) + 1
    return stats

def get_process_summary():
    registry = load_json(os.path.join(RECEIPT_DIR, "nexus_active_process_registry.json"))
    if not registry:
        return {"total": 0, "by_mode": {}, "by_status": {}}
    processes = registry if isinstance(registry, list) else registry.get("processes", [])
    by_mode = {}
    by_status = {}
    for p in processes:
        mode = p.get("activation_mode", "unknown")
        by_mode[mode] = by_mode.get(mode, 0) + 1
    return {"total": len(processes), "by_mode": by_mode, "by_status": by_status}

def get_health_summary():
    health = load_json(HEALTH_JSON)
    if not health:
        return {"overall": "unknown", "checks": 0}
    checks = health.get("checks", []) if isinstance(health, dict) else []
    return {
        "overall": health.get("overall_status", "unknown"),
        "checks": len(checks),
        "healthy": sum(1 for c in checks if c.get("status") == "healthy"),
        "degraded": sum(1 for c in checks if c.get("status") == "degraded"),
    }

def get_recovery_items():
    recovery_file = os.path.join(RECEIPT_DIR, "nexus_interrupted_work_latest.json")
    data = load_json(recovery_file)
    if not data:
        return {"count": 0, "items": []}
    items = data if isinstance(data, list) else data.get("items", [])
    return {"count": len(items), "items": items[:5]}

def get_supabase_status():
    status = load_json(os.path.join(RECEIPT_DIR, "nexus_live_source_status.json"))
    if not status:
        return {"status": "unknown"}
    return {
        "status": status.get("overall_status", "unknown"),
        "tables_found": status.get("tables_found", 0),
        "tables_checked": status.get("tables_checked", 0),
    }

def get_alpha_status():
    registry = load_json(REGISTRY_JSON)
    if not registry:
        return {"score": 0}
    alpha = registry.get("brain_readiness", {}).get("alpha", {})
    return {"score": alpha.get("overall", 0)}

def get_hermes_status():
    registry = load_json(REGISTRY_JSON)
    if not registry:
        return {"score": 0}
    hermes = registry.get("brain_readiness", {}).get("nexus_hermes", {})
    return {"score": hermes.get("overall", 0)}

def generate_daily_report():
    now = datetime.now(timezone.utc).isoformat()
    report_stats = get_report_stats()
    process_summary = get_process_summary()
    health_summary = get_health_summary()
    recovery = get_recovery_items()
    supabase = get_supabase_status()
    alpha = get_alpha_status()
    hermes = get_hermes_status()

    summary = {
        "generated_at": now,
        "report_stats": report_stats,
        "process_summary": process_summary,
        "health_summary": health_summary,
        "recovery_summary": recovery,
        "supabase_status": supabase,
        "alpha_status": alpha,
        "hermes_status": hermes,
    }

    # Write JSON
    os.makedirs(RECEIPT_DIR, exist_ok=True)
    with open(DAILY_JSON, "w") as f:
        json.dump(summary, f, indent=2)

    # Write Markdown
    with open(DAILY_MD, "w") as f:
        f.write("# Nexus Daily Monitor Report\n\n")
        f.write(f"**Generated**: {now}\n\n")
        f.write("---\n\n")
        f.write("## Report Summary\n\n")
        f.write(f"- **Total reports**: {report_stats['total']}\n")
        f.write(f"- **Categories**: {len(report_stats['categories'])}\n\n")
        f.write("## Process Summary\n\n")
        f.write(f"- **Total processes**: {process_summary['total']}\n")
        for mode, count in process_summary.get("by_mode", {}).items():
            f.write(f"- **{mode}**: {count}\n")
        f.write("\n## System Health\n\n")
        f.write(f"- **Overall**: {health_summary['overall']}\n")
        f.write(f"- **Checks**: {health_summary['checks']}\n")
        f.write(f"- **Healthy**: {health_summary.get('healthy', 0)}\n")
        f.write(f"- **Degraded**: {health_summary.get('degraded', 0)}\n\n")
        f.write("## Supabase Status\n\n")
        f.write(f"- **Status**: {supabase['status']}\n")
        f.write(f"- **Tables**: {supabase.get('tables_found', 0)}/{supabase.get('tables_checked', 0)}\n\n")
        f.write("## Alpha Brain\n\n")
        f.write(f"- **Score**: {alpha['score']}/100\n\n")
        f.write("## Hermes Brain\n\n")
        f.write(f"- **Score**: {hermes['score']}/100\n\n")
        f.write("## Recovery\n\n")
        f.write(f"- **Interrupted items**: {recovery['count']}\n\n")
        f.write("---\n\n")
        f.write("## Next Actions\n\n")
        f.write("1. Verify Supabase live connectivity (run verification script)\n")
        f.write("2. Replace Command Center mock data with live sources\n")
        f.write("3. Connect System Health to live checks\n")
        f.write("4. Build client portal premium shell\n")
        f.write("5. Wire Hermes work router to real processes\n")

    return summary

if __name__ == "__main__":
    result = generate_daily_report()
    print(json.dumps(result, indent=2))
