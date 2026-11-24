"""Restart-safe, metadata-only YouTube channel backfill state."""
from __future__ import annotations

import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
STATE_PATH = ROOT / "data/runtime/youtube_backfill_state.json"


def _runtime_binary(name: str) -> str:
    configured = None
    candidates = [configured, shutil.which(name), f"/usr/local/bin/{name}", f"/opt/homebrew/bin/{name}"]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return candidate
    return name


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_state() -> dict[str, Any]:
    if not STATE_PATH.exists():
        return {"schema_version": "nexus.youtube-backfill-state.v1", "channels": {}}
    try:
        return json.loads(STATE_PATH.read_text())
    except (OSError, ValueError):
        return {"schema_version": "nexus.youtube-backfill-state.v1", "channels": {}}


def discover_page(channel_url: str, *, page: int, page_size: int = 10, timeout: int = 30) -> dict[str, Any]:
    start = (page - 1) * page_size + 1
    end = page * page_size
    command = [_runtime_binary("yt-dlp"), "--no-update", "--flat-playlist", "--no-warnings",
               "--socket-timeout", "10", "--extractor-args", "youtube:player_client=android",
               "--playlist-start", str(start), "--playlist-end", str(end), "--dump-single-json",
               f"{channel_url.rstrip('/')}/videos"]
    try:
        completed = subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)
        if completed.returncode != 0 or not completed.stdout.strip():
            return {"status": "SOURCE_ACCESS_FAILED", "page": page, "video_ids": [],
                    "error": (completed.stderr or completed.stdout)[-600:],
                    "failure_type": "YT_DLP_CHANNEL_EXTRACTION_FAILED",
                    "command": command, "exit_code": completed.returncode,
                    "stdout": completed.stdout[-1200:], "stderr": completed.stderr[-1200:]}
        payload = json.loads(completed.stdout)
        entries = [row for row in payload.get("entries", []) if row.get("id")]
        return {"status": "PASS", "page": page, "page_size": page_size,
                "video_ids": [row["id"] for row in entries],
                "videos": [{"video_id": row["id"], "title": row.get("title"), "url": row.get("url") or f"https://www.youtube.com/watch?v={row['id']}"} for row in entries],
                "backfill_complete": len(entries) < page_size, "discovery_mode": "YTDLP_FLAT_PLAYLIST_ANDROID",
                "command": command, "exit_code": completed.returncode}
    except (OSError, subprocess.TimeoutExpired, ValueError) as exc:
        return {"status": "SOURCE_ACCESS_FAILED", "page": page, "video_ids": [],
                "error": str(exc)[:600], "failure_type": "CHANNEL_INVENTORY_EXCEPTION",
                "command": command, "exit_code": 124 if isinstance(exc, subprocess.TimeoutExpired) else None,
                "stdout": "", "stderr": str(exc)[:1200]}


def persist_page(*, channel_id: str, channel_name: str, channel_url: str, page: int, result: dict[str, Any]) -> dict[str, Any]:
    state = load_state()
    channels = state.setdefault("channels", {})
    prior = channels.get(channel_id, {})
    discovered = list(dict.fromkeys(list(prior.get("discovered_video_ids", [])) + list(result.get("video_ids", []))))
    success = result.get("status") == "PASS"
    updated = {**prior, "channel_id": channel_id, "channel_name": channel_name, "channel_url": channel_url,
               "discovered_video_ids": discovered, "discovered_video_count": len(discovered),
               "backfill_cursor": {"next_page": page + 1 if success else page, "last_page": page if success else prior.get("backfill_cursor", {}).get("last_page")},
               "backfill_complete": bool(result.get("backfill_complete", False)),
               "last_run_at": now(), "last_status": result.get("status"),
               "last_error": result.get("error"), "last_failure_type": result.get("failure_type"),
               "last_command": result.get("command"), "last_exit_code": result.get("exit_code"),
               "discovery_mode": result.get("discovery_mode", "YTDLP_FLAT_PLAYLIST_ANDROID")}
    channels[channel_id] = updated
    state["updated_at"] = now()
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")
    return updated
