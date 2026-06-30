#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "ops"))
from same_day_common import now, parse_env, read_json  # noqa: E402,F401

LEGACY_ROOT = Path.home() / "nexuslive"
LEGACY_ADAPTER = LEGACY_ROOT / "lib/notebooklm_ingest_adapter.py"
LEGACY_BIN = LEGACY_ROOT / ".venv-notebooklm/bin/nlm"
CANDIDATE_NAMES = ("notebooklm", "notebook-lm", "nblm", "nlm")


def env_presence() -> dict:
    values = dict(os.environ)
    for path in (ROOT / ".env", ROOT / ".env.local", ROOT / ".env.nexus.recovered.local", LEGACY_ROOT / ".env"):
        values.update(parse_env(path))
    names = ("NOTEBOOKLM_API_KEY", "NOTEBOOKLM_PROJECT_ID", "GOOGLE_APPLICATION_CREDENTIALS", "GOOGLE_CLOUD_PROJECT")
    return {name: bool(values.get(name)) for name in names}


def find_cli() -> dict:
    candidates = []
    for name in CANDIDATE_NAMES:
        path = shutil.which(name)
        if path:
            candidates.append({"name": name, "path": path, "source": "PATH"})
    if LEGACY_BIN.exists() and os.access(LEGACY_BIN, os.X_OK):
        candidates.append({"name": "nlm", "path": str(LEGACY_BIN), "source": "legacy_isolated_venv"})
    selected = candidates[0] if candidates else None
    version = None
    if selected:
        try:
            proc = subprocess.run([selected["path"], "--version"], capture_output=True, text=True, timeout=10)
            version = ((proc.stdout or proc.stderr).splitlines() or ["version_unreported"])[0][:160]
        except (OSError, subprocess.TimeoutExpired):
            version = "version_check_failed"
    return {"found": bool(selected), "selected": selected, "version": version, "candidates": candidates}


def classify() -> dict:
    cli = find_cli(); env = env_presence(); legacy = LEGACY_ADAPTER.exists()
    official = bool(env.get("NOTEBOOKLM_API_KEY") and env.get("NOTEBOOKLM_PROJECT_ID"))
    mode = "official_api" if official else "local_cli" if cli["found"] else "legacy_adapter" if legacy else "watched_folder"
    watched = [ROOT / "data/sources/notebooklm_exports/approved", ROOT / "data/sources/notebooklm_notes/approved"]
    for path in watched: path.mkdir(parents=True, exist_ok=True)
    return {"access_mode": mode, "official_api_configured": official, "cli": cli, "legacy_adapter_found": legacy, "legacy_adapter_path": str(LEGACY_ADAPTER) if legacy else None, "watched_folders": [str(x.relative_to(ROOT)) for x in watched], "manual_export_required": mode in {"legacy_adapter", "watched_folder"}, "consumer_browser_automation": False, "cookies_used": False}


def list_via_cli() -> tuple[bool, list[dict], str | None]:
    access = classify(); selected = access["cli"].get("selected")
    if not selected:
        return False, [], "local_cli_missing"
    command = [selected["path"], "notebook", "list", "--json"]
    try:
        proc = subprocess.run(command, capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, [], exc.__class__.__name__
    if proc.returncode != 0:
        text = (proc.stdout + proc.stderr).lower()
        return False, [], "not_authenticated" if "auth" in text or "login" in text else "notebook_list_failed"
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return False, [], "invalid_json_response"
    rows = payload if isinstance(payload, list) else payload.get("notebooks", []) if isinstance(payload, dict) else []
    safe = [{"notebook_name": str(row.get("title") or row.get("name") or "Untitled")[:200], "notebook_id": str(row.get("id") or "")[:160]} for row in rows if isinstance(row, dict)]
    return True, safe, None


def route(name: str) -> str:
    routes = read_json(ROOT / "configs/notebooklm_source_routes.json", {}).get("routes", [])
    lowered = name.lower()
    for item in routes:
        if item.get("name_pattern") != "*" and item.get("name_pattern", "") in lowered:
            return item["research_lane"]
    return "general_research"
