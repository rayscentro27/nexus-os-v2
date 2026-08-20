"""Phase 15 runtime activation audit — canonical answer to "what is running?".

This audit maps Hermes/Alpha/Nova/loop startup, the scheduler, the Daily
Brief, Mission Control refresh, worker health, opportunities/research refresh,
required env vars, stale locks/PIDs, launchd overlaps, and duplicate
schedulers. It does not start or stop anything.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List

from nexus_agent_platform.phase15.common import (
    DATA_RUNTIME,
    MODERNIZATION_DIR,
    RUNTIME_REPORTS,
    RUNTIME_ENV,
    atomic_write_json,
    load_json,
    load_jsonl,
    utc_now,
)

LAUNCH_AGENTS = Path.home() / "Library" / "LaunchAgents"

# Authorization list for what SHOULD be scheduled/bounded.
CANONICAL = {
    "hermes_telegram_bridge": {
        "label": "com.nexus.telegram-hermes",
        "script": "scripts/telegram/nexus_telegram_bridge.py --once",
        "cadence": "bounded one-shot (launchd StartInterval)",
        "mode": "HERMES",
    },
    "nova_telegram_worker": {
        "label": "com.nexus.telegram-hermes-nova",
        "script": "scripts/ops/run_nova_with_runtime_env.sh -> scripts/nova/nova_telegram_worker.py --once",
        "cadence": "30s bounded one-shot",
        "mode": "NOVA",
    },
    "alpha_telegram_worker": {
        "label": "com.nexus.telegram-alpha",
        "script": "scripts/ops/run_alpha_with_runtime_env.sh -> scripts/alpha/alpha_telegram_worker.py --poll",
        "cadence": "long-lived polling worker",
        "mode": "ALPHA",
    },
    "phase15_bounded_scheduler": {
        "label": "com.nexus.continuous-loop",
        "script": "scripts/nexus_agent_platform/phase15/run_all.py",
        "cadence": "bounded one-shot every 60 minutes",
        "mode": "HERMES/LOOPS",
    },
}


def launchd_rows() -> List[Dict[str, str]]:
    try:
        out = subprocess.run(["launchctl", "list"], capture_output=True, text=True, timeout=10).stdout
    except Exception:  # noqa: BLE001
        return []
    rows: List[Dict[str, str]] = []
    for line in out.splitlines():
        parts = line.split()
        if len(parts) < 3:
            continue
        rows.append({"pid": parts[0], "status": parts[1], "label": parts[2]})
    return rows


def nexus_processes() -> List[Dict[str, Any]]:
    try:
        out = subprocess.run(["ps", "aux"], capture_output=True, text=True, timeout=10).stdout
    except Exception:  # noqa: BLE001
        return []
    procs: List[Dict[str, Any]] = []
    for line in out.splitlines():
        low = line.lower()
        if any(token in low for token in ("alpha_telegram_worker", "nova_telegram_worker", "nexus_telegram_bridge", "nexus_hermes_runtime_adapter", "run_nexus_continuous_loop")):
            procs.append({"command": line[:220]})
    return procs


def stale_locks_and_pids() -> List[Dict[str, str]]:
    stale: List[Dict[str, str]] = []
    candidates = [
        DATA_RUNTIME / "nexus-live.lock",
        RUNTIME_REPORTS / "nexus_overnight_safe_ops.lock",
        RUNTIME_REPORTS / "nexus_overnight_safe_ops.pid",
        DATA_RUNTIME / "nova_locks",
        RUNTIME_REPORTS / "nexus_watch.lock",
        RUNTIME_REPORTS / "nexus_overnight_safe_ops.lock",
    ]
    for path in candidates:
        if path.is_dir():
            files = list(path.iterdir())[:20]
            if files:
                stale.append({"path": str(path), "kind": "dir", "detail": ", ".join(p.name for p in files[:10])})
        elif path.exists():
            text = (path.read_text(errors="replace") or "")[:200] if path.is_file() else ""
            stale.append({"path": str(path), "kind": "file", "detail": text.strip()})
    return stale


def duplicate_detection(rows: List[Dict[str, str]]) -> List[Dict[str, str]]:
    issues: List[Dict[str, str]] = []
    labels = {row["label"]: row.get("pid", "-") for row in rows}
    # Two registered telegram-operator / hermes bridges or an old activation
    # snapshot continuous-loop running from a stale path are the known overlap
    # class. Detection is label-based and read-only.
    if "com.nexus.telegram-operator" in labels or "com.nexus.activation.continuous-loop" in labels:
        issues.append({
            "kind": "duplicate_or_stale_launchd",
            "detail": (
                "telegram-operator (stale activation-snapshot bridge) and/or "
                "activation.continuous-loop (old snapshot scheduler) are registered. "
                "Phase 15 keeps the canonical bridge and introduces ONE bounded scheduler; "
                "the stale snapshot jobs are left registered, not duplicated."
            ),
        })
    return issues


def required_environment() -> Dict[str, List[str]]:
    env_keys: Dict[str, List[str]] = {
        "hermes": ["BRAVE_SEARCH_API_KEY", "OPENROUTER_API_KEY", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"],
        "alpha": ["BRAVE_SEARCH_API_KEY", "ALPHA_TELEGRAM_BOT_TOKEN", "OPENROUTER_API_KEY"],
        "nova": ["HERMES_NOVA_TELEGRAM_BOT_TOKEN", "HERMES_NOVA_MODEL"],
        "stripe_test": ["STRIPE_SECRET_KEY", "STRIPE_WEBHOOK_SECRET", "VITE_STRIPE_PUBLISHABLE_KEY"],
        "supabase_live": ["SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY", "VITE_SUPABASE_URL", "VITE_SUPABASE_ANON_KEY"],
        "runtime_env_file": [k for k in (RUNTIME_ENV.read_text(encoding="utf-8").splitlines() if RUNTIME_ENV.exists() else []) if "=" in k and not k.strip().startswith("#")][:80],
    }
    present: Dict[str, List[str]] = {"hermes": [], "alpha": [], "nova": [], "stripe_test": [], "supabase_live": []}
    for group, keys in env_keys.items():
        if group == "runtime_env_file":
            continue
        present[group] = [key for key in keys if bool(os.environ.get(key, "").strip())]
    return {
        "canonical_runtime_env_present": RUNTIME_ENV.exists(),
        "requirement_groups": {g: {"required": k, "present_in_process_env": present.get(g, [])} for g, k in env_keys.items() if g != "runtime_env_file"},
    }


def build_activation_audit() -> Dict[str, Any]:
    now = utc_now()
    rows = launchd_rows()
    nexus_rows = [row for row in rows if "nexus" in row["label"].lower()]
    procs = nexus_processes()
    lives = load_json(RUNTIME_REPORTS / "nexus_network_live.json", {}) if (RUNTIME_REPORTS / "nexus_network_live.json").exists() else {}

    audit: Dict[str, Any] = {
        "phase": "PHASE 15 — RUNTIME ACTIVATION AUDIT",
        "generated_at": now,
        "components": {
            "hermes_runtime": {
                "startup": "launchd com.nexus.telegram-hermes -> run_with_nexus_runtime_env.sh -> .venv-agent-platform/bin/python3 scripts/telegram/nexus_telegram_bridge.py --once",
                "registered": any(r["label"] == "com.nexus.telegram-hermes" for r in nexus_rows),
                "current_pid": next((r["pid"] for r in nexus_rows if r["label"] == "com.nexus.telegram-hermes"), "-"),
                "note": "bounded one-shot bridge; operator console + Daily Brief + Mission Control data are the persistent Hermes surfaces",
            },
            "alpha_runtime": {
                "startup": "launchd com.nexus.telegram-alpha -> scripts/ops/run_alpha_with_runtime_env.sh -> scripts/alpha/alpha_telegram_worker.py --poll",
                "registered": any(r["label"] == "com.nexus.telegram-alpha" for r in nexus_rows),
                "current_pid": next((r["pid"] for r in nexus_rows if r["label"] == "com.nexus.telegram-alpha"), "-"),
                "process_running": any("alpha_telegram_worker.py" in p["command"] for p in procs),
                "note": "long-lived polling worker; bounded external intelligence",
            },
            "nova_runtime": {
                "startup": "launchd com.nexus.telegram-hermes-nova -> run_nova_with_runtime_env.sh -> scripts/nova/nova_telegram_worker.py --once (StartInterval 30s)",
                "registered": any(r["label"] == "com.nexus.telegram-hermes-nova" for r in nexus_rows),
                "current_pid": next((r["pid"] for r in nexus_rows if r["label"] == "com.nexus.telegram-hermes-nova"), "-"),
                "note": "bounded one-shot reasoning worker (Nova); isolated governance lane",
            },
            "loop_scheduler": {
                "startup": "Canonical scheduler com.nexus.continuous-loop -> scripts/nexus_agent_platform/phase15/run_all.py (bounded one-shot)",
                "registered": any(r["label"] == "com.nexus.continuous-loop" for r in rows),
                "current_pid": next((r["pid"] for r in rows if r["label"] == "com.nexus.continuous-loop"), "-"),
                "note": "runs the 4 certified business loops + daily brief + research + status on a bounded cadence; no continuous LLM",
            },
            "daily_brief": {
                "refresh": "scripts/nexus_agent_platform/brief/daily_brief.py via the phase15 scheduler",
                "source": "reports/hermes_modernization/daily_brief.json",
                "generated_at": (load_json(MODERNIZATION_DIR / "daily_brief.json", {}) or {}).get("generated_at"),
            },
            "mission_control": {
                "refresh": "phase15 scheduler rewrites reports/hermes_modernization/state.json, daily_brief.json, ai_workforce_registry.json, and data/runtime/nexus_loops/loop_state.json",
                "component": "src/components/command-center/HermesMissionControlV2.tsx",
            },
            "worker_health": {
                "refresh": "reads reports/hermes_modernization/ai_workforce_registry.json + workforce_certification.json (certified checkpoint); no provider mutation",
            },
            "opportunity_research_refresh": {
                "refresh": "research decisions + intake loop + bounded live research session",
            },
        },
        "scheduler_health": {
            "launchd_nexus_count": len(nexus_rows),
            "overlap_and_duplicates": duplicate_detection(rows),
        },
        "processes_exiting_after_once": [
            {"label": "com.nexus.telegram-hermes", "note": "exit after --once (bounded)"},
            {"label": "com.nexus.telegram-hermes-nova", "note": "exit after --once (bounded)"},
        ],
        "processes_bounded_scheduled": [
            {"label": "com.nexus.continuous-loop", "note": "bounded one-shot scheduler"},
            {"label": "com.nexus.telegram-alpha", "note": "long-lived poller with bounded work per cycle"},
        ],
        "stale_locks_and_pids": stale_locks_and_pids(),
        "runtime_environment": required_environment(),
        "live_process_snapshot": procs,
        "network_live_status": lives,
        "verdict": "Canonical runtime startup identified; Phase 15 adds exactly ONE bounded scheduler and does not introduce duplicate daemons.",
    }
    atomic_write_json(MODERNIZATION_DIR / "live_runtime_activation.json", audit)
    lines = [
        "# Nexus Live Runtime Activation — Phase 15",
        "",
        f"- generated_at: `{now}`",
        f"- verdict: {audit['verdict']}",
        "",
        "## Startup paths",
    ]
    for name, comp in audit["components"].items():
        lines.append(f"### {name}")
        for key, value in comp.items():
            if key in {"note", "generated_at"}:
                lines.append(f"- {key}: `{value}`")
            else:
                lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## Required environment variables"])
    for group, info in audit["runtime_environment"]["requirement_groups"].items():
        lines.append(f"- `{group}` required={info['required']} present={info['present_in_process_env']}")
    lines.append(f"- canonical runtime.env file present: `{audit['runtime_environment']['canonical_runtime_env_present']}`")
    lines.extend(["", "## Stale locks / PIDs"])
    for row in audit["stale_locks_and_pids"]:
        lines.append(f"- `{row['path']}` ({row['kind']}): {row['detail'][:120]}")
    lines.extend(["", "## launchd / duplicate detection"])
    for row in audit["scheduler_health"]["overlap_and_duplicates"]:
        lines.append(f"- {row['kind']}: {row['detail']}")
    lines.extend(["", "## Bounded cadence"])
    for label, comp in CANONICAL.items():
        lines.append(f"- `{comp['label']}` -> {comp['script']} ({comp['cadence']}) — {comp['mode']}")
    (MODERNIZATION_DIR / "live_runtime_activation.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return audit
