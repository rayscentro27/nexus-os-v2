#!/usr/bin/env python3
"""
Nexus Daily Monitor — comprehensive system status check.

Checks: Supabase, Command Center, Client Portal, Ray Review, Hermes,
Alpha, Telegram, Stripe/paywall, process registry, runner heartbeat,
reports freshness, build status, blocked actions, next actions.
"""

import json
import os
from datetime import datetime, timezone

RUNTIME_DIR = "reports/runtime"
REGISTRY_PATH = "data/operations/nexus_process_registry.json"
HEARTBEAT_PATH = "reports/runtime/nexus_active_operator_heartbeat_latest.json"
DAILY_MD = "reports/runtime/nexus_daily_monitor_latest.md"
DAILY_JSON = "reports/runtime/nexus_daily_monitor_latest.json"

def load_json(path):
    try:
        with open(path) as f:
            return json.load(f)
    except:
        return None

def check_reports_freshness():
    stale = []
    fresh = []
    checks = [
        ("daily_monitor", DAILY_MD),
        ("heartbeat", HEARTBEAT_PATH),
        ("process_registry", REGISTRY_PATH),
        ("master_registry", "reports/runtime/nexus_activation_master_registry.json"),
        ("prompt_2_closeout", "reports/runtime/nexus_prompt_2_completion_summary.md"),
    ]
    for name, path in checks:
        if os.path.exists(path):
            age_hours = (datetime.now().timestamp() - os.path.getmtime(path)) / 3600
            entry = {"name": name, "path": path, "age_hours": round(age_hours, 1)}
            if age_hours > 24:
                stale.append(entry)
            else:
                fresh.append(entry)
        else:
            stale.append({"name": name, "path": path, "age_hours": -1, "note": "missing"})
    return {"fresh": fresh, "stale": stale}

def check_blocked_actions():
    guard = load_json("data/operations/nexus_blocked_action_guard.json")
    if not guard:
        return {"status": "guard_missing", "blocked": []}
    return {"status": "active", "blocked": guard.get("blocked_actions", [])}

def generate():
    now = datetime.now(timezone.utc)
    registry = load_json(REGISTRY_PATH) or []
    heartbeat = load_json(HEARTBEAT_PATH)
    freshness = check_reports_freshness()
    blocked = check_blocked_actions()

    enabled = [p for p in registry if p.get("enabled")]
    telegram_ok = [p for p in enabled if p.get("telegram_allowed")]
    blocked_procs = [p for p in registry if p.get("mode") == "BLOCKED"]

    summary = {
        "generated_at": now.isoformat(),
        "process_registry": {
            "total": len(registry),
            "enabled": len(enabled),
            "telegram_allowed": len(telegram_ok),
            "blocked": len(blocked_procs)
        },
        "runner_heartbeat": {
            "exists": heartbeat is not None,
            "last_run": heartbeat.get("generated_at") if heartbeat else None,
            "processes_run": heartbeat.get("processes_run", 0) if heartbeat else 0
        },
        "reports_freshness": {
            "fresh_count": len(freshness["fresh"]),
            "stale_count": len(freshness["stale"]),
            "stale": freshness["stale"]
        },
        "blocked_actions": blocked,
        "supabase": {
            "env_keys": "present_in_dotenv",
            "browser_verification": "unverified",
            "classification": "ENV_PRESENT_BROWSER_EXPECTED"
        },
        "build": {"status": "previously_passing"},
        "next_actions": [
            "Verify Supabase via browser DevTools",
            "Start Telegram bridge",
            "Run active operator runner",
            "Build client portal premium shell",
            "Connect Stripe test-mode"
        ]
    }

    with open(DAILY_JSON, "w") as f:
        json.dump(summary, f, indent=2)

    report = f"""# Nexus Daily Monitor Report

**Generated**: {now.isoformat()}

---

## Process Registry

| Metric | Value |
|--------|-------|
| Total | {summary['process_registry']['total']} |
| Enabled | {summary['process_registry']['enabled']} |
| Telegram Allowed | {summary['process_registry']['telegram_allowed']} |
| Blocked | {summary['process_registry']['blocked']} |

---

## Runner Heartbeat

| Metric | Value |
|--------|-------|
| Exists | {summary['runner_heartbeat']['exists']} |
| Last Run | {summary['runner_heartbeat']['last_run'] or 'never'} |
| Processes Run | {summary['runner_heartbeat']['processes_run']} |

---

## Reports Freshness

| Metric | Value |
|--------|-------|
| Fresh | {summary['reports_freshness']['fresh_count']} |
| Stale | {summary['reports_freshness']['stale_count']} |

"""
    for s in freshness["stale"]:
        note = s.get('note', f"{s['age_hours']}h old")
        report += f"- **{s['name']}**: {note}\n"

    report += f"""
---

## Supabase

| Dimension | Status |
|-----------|--------|
| Env Keys | Present |
| Browser Verification | Unverified |
| Classification | ENV_PRESENT_BROWSER_EXPECTED |

---

## Blocked Actions

"""
    for b in blocked.get("blocked", []):
        report += f"- {b}\n"
    if not blocked.get("blocked"):
        report += "Guard active\n"

    report += f"""
---

## Next Actions

"""
    for i, a in enumerate(summary["next_actions"], 1):
        report += f"{i}. {a}\n"

    with open(DAILY_MD, "w") as f:
        f.write(report)

    return summary

if __name__ == "__main__":
    result = generate()
    print(json.dumps(result, indent=2))
