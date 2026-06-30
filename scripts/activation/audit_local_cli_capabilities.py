#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "ops"))
from same_day_common import SUPABASE_READY, now, write_json, write_report  # noqa: E402

TOOLS = {
    "git": ["git", "--version"], "gh": ["gh", "--version"], "node": ["node", "--version"],
    "npm": ["npm", "--version"], "npx": ["npx", "--version"], "python3": ["python3", "--version"],
    "pip3": ["pip3", "--version"], "pnpm": ["pnpm", "--version"], "yarn": ["yarn", "--version"],
    "jq": ["jq", "--version"], "curl": ["curl", "--version"], "wget": ["wget", "--version"],
    "openssl": ["openssl", "version"], "sqlite3": ["sqlite3", "--version"],
    "supabase": ["supabase", "--version"], "netlify": ["netlify", "--version"], "vercel": ["vercel", "--version"],
    "docker": ["docker", "--version"], "colima": ["colima", "version"], "orb": ["orb", "--version"],
    "psql": ["psql", "--version"], "stripe": ["stripe", "--version"], "yt-dlp": ["yt-dlp", "--version"],
    "ffmpeg": ["ffmpeg", "-version"], "imagemagick": ["convert", "--version"], "magick": ["magick", "-version"],
    "tesseract": ["tesseract", "--version"], "playwright": ["playwright", "--version"],
    "chromium": ["chromium", "--version"], "chrome": ["google-chrome", "--version"],
    "codex": ["codex", "--version"], "claude": ["claude", "--version"], "opencode": ["opencode", "--version"],
    "gemini": ["gemini", "--version"], "ollama": ["ollama", "--version"], "notebooklm": ["notebooklm", "--version"],
    "vibe-trading": ["vibe-trading", "--version"], "resend": ["resend", "--version"],
    "facebook": ["facebook", "--version"], "instagram": ["instagram", "--version"], "oanda": ["oanda", "--version"],
}


def detect(name: str, command: list[str]) -> dict:
    path = shutil.which(command[0])
    version = None
    if path:
        try:
            proc = subprocess.run(command, capture_output=True, text=True, timeout=8)
            line = (proc.stdout or proc.stderr).splitlines()
            version = line[0][:180] if line else "installed_version_unreported"
        except (OSError, subprocess.TimeoutExpired):
            version = "installed_version_check_failed"
    return {"tool_name": name, "installed": bool(path), "path": path, "version": version, "detection_command": " ".join(command)}


def build() -> dict:
    records = [detect(name, command) for name, command in TOOLS.items()]
    module = importlib.util.find_spec("vibe_trading")
    records.append({"tool_name": "vibe_trading_python", "installed": module is not None, "path": module.origin if module else None, "version": None, "detection_command": "python3 -m vibe_trading --version"})
    legacy_adapter = Path.home() / "nexuslive/lib/notebooklm_ingest_adapter.py"
    records.append({"tool_name": "notebooklm_legacy_adapter", "installed": legacy_adapter.exists(), "path": str(legacy_adapter) if legacy_adapter.exists() else None, "version": "local_python_adapter" if legacy_adapter.exists() else None, "detection_command": "test -f ~/nexuslive/lib/notebooklm_ingest_adapter.py"})
    vibe_adapter = ROOT / "scripts/trading/vibe_trading_adapter.py"
    records.append({"tool_name": "vibe_recovered_adapter", "installed": vibe_adapter.exists(), "path": str(vibe_adapter) if vibe_adapter.exists() else None, "version": "local_paper_adapter" if vibe_adapter.exists() else None, "detection_command": "test -f scripts/trading/vibe_trading_adapter.py"})
    oanda_connector = ROOT / "scripts/trading/oanda_demo_common.py"
    records.append({"tool_name": "oanda_demo_api_connector", "installed": oanda_connector.exists(), "path": str(oanda_connector) if oanda_connector.exists() else None, "version": "v20_practice_only" if oanda_connector.exists() else None, "detection_command": "test -f scripts/trading/oanda_demo_common.py"})
    legacy = []
    for base in (Path.home() / "nexuslive", Path.home() / "nexus-ai-council-sandbox"):
        if not base.exists():
            continue
        for pattern in ("*notebooklm*", "*oanda*", "*backtest*", "*stripe*", "*research*"):
            legacy.extend(str(path) for path in base.rglob(pattern) if path.is_file())
    legacy = sorted(set(legacy))[:250]
    report = {"ok": True, "generated_at": now(), "status": "cli_audit_complete", "tools_audited": len(records), "installed_count": sum(item["installed"] for item in records), "missing_count": sum(not item["installed"] for item in records), "legacy_capability_files_found": len(legacy), "raw_secrets_reported": False, "external_action_performed": False, "tools": records, "legacy_files": legacy}
    write_json(SUPABASE_READY / "cli_capability_registry_latest.json", records)
    write_report("cli_capability_audit", "CLI Capability Audit", report, {"Installed": [x["tool_name"] for x in records if x["installed"]], "Missing": [x["tool_name"] for x in records if not x["installed"]], "Legacy capabilities": legacy[:40]})
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--json", action="store_true"); args = parser.parse_args()
    result = build(); print(json.dumps(result, indent=2) if args.json else result)
