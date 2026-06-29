#!/usr/bin/env python3
"""Safe yt-dlp capability detection. Never probes targets or downloads media."""
from __future__ import annotations

import importlib.metadata
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "ops"))
from same_day_common import now, read_json, write_report  # noqa:E402


def _version(command: list[str]) -> str | None:
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=10, check=False)
        return result.stdout.strip().splitlines()[0] if result.returncode == 0 and result.stdout.strip() else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def audit() -> dict:
    path = shutil.which("yt-dlp")
    cli_version = _version([path, "--version"]) if path else None
    module_version = _version([sys.executable, "-m", "yt_dlp", "--version"])
    try:
        package_version = importlib.metadata.version("yt-dlp")
    except importlib.metadata.PackageNotFoundError:
        package_version = None
    config = read_json(ROOT / "configs" / "youtube_research_channels.json", {})
    targets = [item for item in config.get("channels", []) if item.get("enabled") and item.get("approved_by_ray")]
    available = bool(path or module_version)
    status = ("targets_configured_ytdlp_available_needs_approved_probe" if available and targets else
              "local_ytdlp_available_no_approved_targets" if available else
              "targets_configured_connector_missing" if targets else "not_configured")
    report = {
        "ok": True, "generated_at": now(), "status": status,
        "local_ytdlp_available": available, "ytdlp_path": path,
        "ytdlp_version": cli_version or module_version or package_version,
        "python_module_available": bool(module_version), "python_module_version": module_version,
        "pip_package_version": package_version, "approved_targets_count": len(targets),
        "approved_target_ids": [item.get("id") for item in targets],
        "metadata_probe_available": available, "subtitle_availability_probe_available": available,
        "approved_probe_performed": False, "video_download_performed": False,
        "restriction_bypass_performed": False, "copyrighted_content_reused": False,
        "public_content_published": False, "external_action_performed": False,
        "allowed_future_probe": "Approved targets only; metadata and subtitle availability checks with skip-download/no media output.",
        "approval_required": bool(available and targets),
        "next_required_action": "Approve local yt-dlp metadata/subtitle probe for queued YouTube targets." if available and targets else "Configure approved targets or a bounded metadata source.",
        "summary": "yt-dlp is a locally available probe capability, not a fully configured YouTube review connector." if available else "yt-dlp was not detected locally.",
    }
    write_report("youtube_local_tool_audit", "YouTube Local Tool Audit", report,
                 {"Safety rules": ["Approved configured targets only", "No video/audio downloads", "No restriction bypass", "No copyrighted reuse", "No automatic publishing"]})
    return report
