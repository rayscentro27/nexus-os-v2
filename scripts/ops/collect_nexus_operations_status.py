#!/usr/bin/env python3
"""Read-only Mac Mini/Nexus operations inventory. Never prints secret values."""
from __future__ import annotations

import json
import os
import plistlib
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPORTS = ROOT / "reports"
NOW = datetime.now(timezone.utc)
CHECKED = NOW.isoformat()
STATUSES = {"live_running", "installed_not_running", "configured_not_verified", "report_only", "static_only", "missing", "broken", "unknown", "not_proven_live"}
ENV_NAMES = [
    "SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY", "VITE_SUPABASE_URL", "VITE_SUPABASE_ANON_KEY",
    "VITE_HERMES_SEARCH_ENABLED", "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "OPENROUTER_API_KEY",
    "HERMES_MODEL_PROVIDER", "HERMES_LLM_PROVIDER", "OLLAMA_HOST",
]
CLI_NAMES = ["git", "node", "npm", "python3", "supabase", "netlify", "gh", "ollama", "opencode", "codex"]

def run(args: list[str], timeout: int = 8) -> tuple[int, str]:
    try:
        p = subprocess.run(args, cwd=ROOT, text=True, capture_output=True, timeout=timeout, env={**os.environ, "LC_ALL": "C"})
        return p.returncode, (p.stdout or p.stderr).strip()
    except Exception as exc:
        return 1, f"unavailable: {type(exc).__name__}"

def clean(text: str, limit: int = 240) -> str:
    text = re.sub(r"(?i)(key|token|secret|password|authorization)=?\s*[^\s]+", r"\1=[REDACTED]", text)
    text = re.sub(r"(?i)bearer\s+[^\s]+", "Bearer [REDACTED]", text)
    text = re.sub(r"eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}", "[REDACTED_JWT]", text)
    text = re.sub(r"(?i)(sk|pk|sb)_(live|test|secret)_[A-Za-z0-9_-]{12,}", "[REDACTED_KEY]", text)
    return " ".join(text.split())[:limit]

def item(name: str, category: str, status: str, source: str, proof: str, summary: str, next_action: str, limitations=None, gated=None, **extra):
    assert status in STATUSES
    return {"name": name, "category": category, "status": status, "source": source, "checked_at": CHECKED,
            "proof": clean(proof), "limitations": limitations or [], "hermes_readable_summary": summary,
            "safe_next_action": next_action, "gated_actions": gated or [], **extra}

def file_stamp(path: Path):
    if not path.exists(): return None
    return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()

def env_presence():
    file_keys = set()
    for env_file in [ROOT / ".env", ROOT / ".env.local"]:
        if env_file.exists():
            for line in env_file.read_text(errors="ignore").splitlines():
                match = re.match(r"^([A-Z][A-Z0-9_]*)\s*=", line)
                if match: file_keys.add(match.group(1))
    return {name: {"present": bool(os.environ.get(name)) or name in file_keys, "source": "process_env_or_local_env_file", "value_redacted": True} for name in ENV_NAMES}

def git_inventory():
    _, branch = run(["git", "branch", "--show-current"])
    _, head = run(["git", "rev-parse", "HEAD"])
    _, status = run(["git", "status", "--short"])
    _, ahead = run(["git", "rev-list", "--left-right", "--count", "HEAD...@{upstream}"])
    _, log = run(["git", "log", "--oneline", "-5"])
    return {"repo_path": str(ROOT), "branch": branch, "latest_commit": head, "dirty": bool(status),
            "uncommitted_files": [line[3:] for line in status.splitlines() if len(line) > 3], "ahead_behind": clean(ahead),
            "latest_commits": [clean(line) for line in log.splitlines()]}

def process_inventory():
    _, output = run(["ps", "-axo", "pid=,etime=,command="], 10)
    rows = []
    for line in output.splitlines():
        if not re.search(r"(?i)nexus|hermes|youtube|research|vite|supabase", line): continue
        if "collect_nexus_operations_status" in line or " rg " in line: continue
        match = re.match(r"\s*(\d+)\s+(\S+)\s+(.+)", line)
        if not match: continue
        command = clean(match.group(3))
        category = "youtube_research" if re.search(r"(?i)youtube", command) else "nexus_process"
        rows.append(item(f"pid-{match.group(1)}", category, "live_running", "ps -axo", f"PID {match.group(1)} uptime {match.group(2)}", command, "Inspect its latest safe log/report; do not stop it from Hermes.", gated=["stop", "restart"], pid=int(match.group(1)), uptime=match.group(2), command=command))
    return rows

def scheduler_inventory():
    agents = Path.home() / "Library" / "LaunchAgents"
    _, loaded_text = run(["launchctl", "list"], 12)
    rows = []
    for path in sorted(agents.glob("*nexus*.plist")):
        try:
            with path.open("rb") as fh: data = plistlib.load(fh)
        except Exception: data = {}
        label = str(data.get("Label") or path.stem)
        loaded = label in loaded_text
        cadence = data.get("StartCalendarInterval") or data.get("StartInterval") or "unknown"
        stdout = str(data.get("StandardOutPath") or "")
        stderr = str(data.get("StandardErrorPath") or "")
        log_stamps = {p: file_stamp(Path(p)) for p in [stdout, stderr] if p}
        rows.append(item(label, "launchd", "installed_not_running", str(path), f"plist exists; loaded={loaded}",
                         f"{label} is installed{' and loaded' if loaded else ' but not loaded'}; no active PID is inferred from load state.",
                         "Check the configured log and process inventory before claiming it is running.",
                         limitations=["launchd loaded state is not proof of active execution"], gated=["load", "unload", "restart"],
                         loaded=loaded, cadence=cadence, stdout_log=stdout or None, stderr_log=stderr or None, log_timestamps=log_stamps))
    return rows

def session_inventory():
    rows = []
    for name, args in [("cron", ["crontab", "-l"]), ("tmux", ["tmux", "list-sessions"]), ("screen", ["screen", "-ls"])]:
        code, output = run(args)
        matches = [clean(line) for line in output.splitlines() if re.search(r"(?i)nexus|hermes|youtube|research", line)]
        rows.append({"type": name, "accessible": code == 0, "nexus_entries": matches})
    return rows

def cli_inventory():
    rows = []
    for name in CLI_NAMES:
        path = shutil.which(name)
        version = "unknown"
        if path:
            _, version_out = run([name, "--version"], 5)
            version = clean(version_out.splitlines()[0] if version_out else "available")
        rows.append(item(name, "cli", "installed_not_running" if path else "missing", path or "PATH", f"available={bool(path)} version={version}",
                         f"{name} is {'available' if path else 'not available'}; availability does not imply connection or authorization.",
                         "Use only allow-listed read-only commands.", gated=["commands that deploy, write, send, or execute"], available=bool(path), path=path, version=version))
    playwright = ROOT / "node_modules" / "playwright"
    rows.append(item("playwright", "cli", "installed_not_running" if playwright.exists() else "missing", str(playwright), f"package_present={playwright.exists()}",
                     f"Playwright package is {'present' if playwright.exists() else 'missing'}.", "Run existing UI tests only.", available=playwright.exists()))
    return rows

def youtube_status(processes, schedulers):
    scripts = list((ROOT / "scripts").rglob("*youtube*.py"))
    youtube_process = any(x["category"] == "youtube_research" for x in processes)
    yt_schedulers = [x for x in schedulers if "youtube" in x["name"].lower()]
    loaded = any(x.get("loaded") for x in yt_schedulers)
    metadata_files = list((ROOT / "data/cache/youtube/api_metadata").glob("*.json"))
    transcript_files = list((ROOT / "data/sources/youtube_transcripts/approved").glob("*.txt")) if (ROOT / "data/sources/youtube_transcripts/approved").exists() else []
    supabase_ready = list((ROOT / "reports/runtime/supabase_ready").glob("youtube*.json"))
    write_proof = ROOT / "reports/live_seed_execution_latest.json"
    watched = ROOT / "configs/youtube_research_channels.json"
    channels = []
    if watched.exists():
        try:
            raw = json.loads(watched.read_text()); channels = raw if isinstance(raw, list) else raw.get("channels", [])
        except Exception: pass
    proven = youtube_process and bool(metadata_files) and write_proof.exists()
    status = "live_running" if proven else "not_proven_live"
    return item("youtube_research", "research_job", status, "scripts/config/cache/launchd inventory",
                f"scripts={len(scripts)} scheduler_exists={bool(yt_schedulers)} loaded={loaded} process={youtube_process} metadata_files={len(metadata_files)} write_proof={write_proof.exists()}",
                "YouTube tooling and cached metadata exist, but live operation requires concurrent process/log/write proof." if not proven else "YouTube research has process, metadata, and write proof.",
                "Inspect the scheduler log and a recent safe Supabase write receipt; rerun this collector.",
                limitations=["Cached files do not prove a currently running scheduler", "Supabase row counts were not queried by this local collector"],
                gated=["start scheduler", "run paid API", "write to Supabase"], installed=bool(scripts), scheduler_exists=bool(yt_schedulers), loaded=loaded,
                running_now=youtube_process, watched_channels_count=len(channels), last_metadata_fetch=max((file_stamp(p) for p in metadata_files), default=None),
                last_transcript_fetch=max((file_stamp(p) for p in transcript_files), default=None), notebooklm_export_status="report_only" if (ROOT / "data/exports/notebooklm/youtube/youtube_research_bundle_latest.json").exists() else "missing",
                supabase_write_proof=write_proof.exists(), supabase_ready_files=len(supabase_ready), rows_written_last_24h="unknown", rows_written_last_7d="unknown")

def write_json(name, payload):
    (REPORTS / name).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")

def main():
    git = git_inventory(); processes = process_inventory(); schedulers = scheduler_inventory(); sessions = session_inventory(); clis = cli_inventory(); env = env_presence()
    youtube = youtube_status(processes, schedulers)
    package = json.loads((ROOT / "package.json").read_text())
    operations = {
        "audit_run_id": f"ops-{NOW.strftime('%Y%m%dT%H%M%SZ')}", "checked_at": CHECKED, "read_only": True,
        "repo": git, "build_test": {"package_scripts": package.get("scripts", {}), "last_known_build_report": file_stamp(ROOT / "reports/manual_publish/pre_deploy_build_result_latest.md")},
        "env_presence": env, "hermes": {"supabase": "conditional" if env["VITE_SUPABASE_URL"]["present"] and env["VITE_SUPABASE_ANON_KEY"]["present"] else "not_configured",
            "model": "conditional" if any(env[x]["present"] for x in ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "OPENROUTER_API_KEY", "HERMES_MODEL_PROVIDER"]) else "not_configured",
            "web_search": "conditional" if env["VITE_HERMES_SEARCH_ENABLED"]["present"] else "not_configured", "execution_gated": True},
        "processes": processes, "schedulers": schedulers, "sessions": sessions, "cli": clis, "youtube_research": youtube,
        "token_rate_limits": {"status": "unknown", "reason": "No verified limits were found in safe config/report metadata; values were not guessed."},
        "supabase_summary_write": {"performed": False, "reason": "No collector-authenticated, tenant-scoped server write path was used."},
    }
    write_json("nexus_operations_status_latest.json", operations)
    write_json("nexus_process_inventory_latest.json", {"checked_at": CHECKED, "items": processes})
    write_json("nexus_scheduler_inventory_latest.json", {"checked_at": CHECKED, "items": schedulers, "sessions": sessions})
    write_json("nexus_cli_inventory_latest.json", {"checked_at": CHECKED, "items": clis})
    write_json("nexus_youtube_research_status_latest.json", {"checked_at": CHECKED, "items": [youtube]})
    real = [x["name"] for x in processes]
    installed = [x["name"] for x in schedulers]
    md = f"""# Nexus Operations Status\n\nChecked: {CHECKED}\n\n## What is real\n\n- Repo `{git['branch']}` at `{git['latest_commit'][:12]}`.\n- {len(processes)} Nexus-related processes had direct `ps` proof.\n- {len(schedulers)} Nexus launchd plists were inspected.\n- CLI availability was checked without reading credentials.\n\n## What is running\n\n{chr(10).join(f'- {x}' for x in real) or '- No Nexus-related process was proven running.'}\n\n## Installed but not proven running\n\n{chr(10).join(f'- {x}' for x in installed) or '- No Nexus launchd jobs found.'}\n\n## Static or report-only\n\n- Package scripts, report timestamps, cached YouTube metadata, and Supabase-ready files are evidence snapshots, not process proof.\n\n## Broken or unproven\n\n- YouTube research: **{youtube['status']}**. {youtube['hermes_readable_summary']}\n- Token/rate limits: unknown; no values were guessed.\n\n## What Hermes can report\n\n- Git/repo state, safe process inventory, launchd inventory, CLI availability, env-name presence, report freshness, and YouTube proof status.\n\n## What needs Ray approval\n\n- Starting/stopping/restarting jobs, deployment, Supabase writes/seeds, external research, sends, publishing, charges, disputes, and trading.\n\nSafe refresh command: `python3 scripts/ops/collect_nexus_operations_status.py`\n"""
    (REPORTS / "nexus_operations_status_latest.md").write_text(md)
    print(json.dumps({"ok": True, "checked_at": CHECKED, "processes": len(processes), "schedulers": len(schedulers), "youtube_status": youtube["status"], "secrets_exposed": False}))

if __name__ == "__main__": main()
