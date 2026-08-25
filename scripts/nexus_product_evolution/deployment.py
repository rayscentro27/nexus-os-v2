"""Read-only production deployment truth for Product Evolution operations."""

from __future__ import annotations

import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Optional

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TARGET = "https://goclearonline.cc"
VOICE_NOTICE = "Private local VAD active. One utterance at a time; persistent listening sends one final local STT request after silence."


def _git(*args: str) -> str:
    completed = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, timeout=15, check=False)
    return completed.stdout.strip() if completed.returncode == 0 else "UNKNOWN"


def _fetch(url: str) -> tuple[int, Mapping[str, str], bytes]:
    try:
        completed = subprocess.run(["/usr/bin/curl", "-sS", "-L", "--max-time", "20", "-D", "-", url], capture_output=True, timeout=25, check=False)
        raw = completed.stdout
        separator = raw.find(b"\r\n\r\n")
        if separator < 0:
            separator = raw.find(b"\n\n")
            width = 2
        else:
            width = 4
        header_bytes, body = (raw[:separator], raw[separator + width:]) if separator >= 0 else (b"", raw)
        lines = header_bytes.decode("iso-8859-1", "replace").splitlines()
        status_line = next((line for line in lines if line.startswith("HTTP/")), "")
        status = int(re.search(r"\s(\d{3})(?:\s|$)", status_line).group(1)) if re.search(r"\s(\d{3})(?:\s|$)", status_line) else 0
        headers = {}
        for line in lines[1:]:
            if ":" in line:
                key, value = line.split(":", 1)
                headers[key.strip().lower()] = value.strip()
        return status, headers, body[:8 * 1024 * 1024]
    except Exception as exc:
        return 0, {"error": type(exc).__name__}, b""


def _receipt_event(record: Mapping[str, Any], event: str, **fields: Any) -> Dict[str, Any]:
    result = dict(record.get("result") or {})
    now = datetime.now(timezone.utc).isoformat()
    history = list(result.get("execution_history") or [])
    history.append({"at": now, "event": event, **fields})
    result["execution_history"] = history
    result["updated_at"] = now
    return result


def inspect_deployment(record: Mapping[str, Any], *, target: str = DEFAULT_TARGET, requested_commit: Optional[str] = None) -> Dict[str, Any]:
    """Inspect public deployment evidence without deploying or reading secrets."""
    result = dict(record.get("result") or {})
    mission_id = str(result.get("mission_id") or record.get("mission_id") or "UNKNOWN")
    expected = requested_commit or _git("rev-parse", "HEAD")
    origin = _git("rev-parse", "origin/main")
    started = _receipt_event(record, "DEPLOYMENT_INSPECTION_STARTED", target=target, requested_commit=expected)
    status, headers, html_bytes = _fetch(target + "/admin")
    html = html_bytes.decode("utf-8", "replace")
    asset_match = re.search(r'<script[^>]+src="([^"]+\.js)"', html)
    asset_url = target.rstrip("/") + asset_match.group(1) if asset_match else ""
    js_status, js_headers, js_bytes = _fetch(asset_url) if asset_url else (0, {}, b"")
    bundle = js_bytes.decode("utf-8", "replace")
    markers = {
        "admin_http_status": status,
        "asset_http_status": js_status,
        "asset_url": asset_url or "UNKNOWN",
        "netlify_request_id": headers.get("x-nf-request-id") or headers.get("X-Nf-Request-Id") or "UNKNOWN",
        "cache_status": headers.get("age") or headers.get("x-nf-cache-status") or "UNKNOWN",
        "build_metadata_present": "__NEXUS_BUILD_METADATA__" in bundle,
        "build_commit_literal": expected if expected != "UNKNOWN" and expected in bundle else "UNKNOWN",
        "voice_notice_present": VOICE_NOTICE in bundle,
        "persistent_preview_guard_present": "persistentRef.current" in bundle and "preview" in bundle,
        "wake_state_present": "WAKE_IDLE" in bundle,
        "generic_unversioned_metadata": "unversioned" in bundle and "unknown" in bundle,
    }
    source_current = (ROOT / "src/admin/NexusWakeVoice.jsx").read_text(encoding="utf-8")
    latest_source = VOICE_NOTICE in source_current and "persistentRef.current" in source_current
    bundle_matches_expected = markers["build_commit_literal"] == expected and expected != "UNKNOWN"
    stale = latest_source and not (markers["voice_notice_present"] and markers["wake_state_present"])
    if stale:
        deployment_status = "DEPLOYMENT_STALE"
        event = "DEPLOYMENT_STALE"
    elif bundle_matches_expected:
        deployment_status = "DEPLOYED"
        event = "DEPLOYMENT_COMPLETE"
    else:
        deployment_status = "UNKNOWN"
        event = "DEPLOYMENT_COMMIT_IDENTIFIED"
    verification = "PASS" if markers["voice_notice_present"] and markers["wake_state_present"] else "FAIL"
    deployment = {
        "target": target,
        "provider": "Netlify via Git-connected deployment",
        "requested_commit": expected,
        "origin_main_commit": origin,
        "deployed_commit": expected if bundle_matches_expected else "UNKNOWN",
        "deployed_build_id": "UNKNOWN",
        "deployed_at": "UNKNOWN",
        "deployment_status": deployment_status,
        "source_of_truth": "netlify.toml + production HTML asset + production JavaScript bundle + Vite build metadata",
        "verification": verification,
        "production_markers": markers,
        "latest_source_markers": {"voice_notice": VOICE_NOTICE in source_current, "persistent_preview_guard": "persistentRef.current" in source_current},
        "stale_production": "YES" if stale else ("NO" if deployment_status == "DEPLOYED" else "UNKNOWN"),
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "mission_id": mission_id,
    }
    history = list(started.get("execution_history") or [])
    history.append({"at": datetime.now(timezone.utc).isoformat(), "event": event, "deployment_status": deployment_status, "evidence": {"target": target, "asset_url": asset_url, "verification": verification}})
    started["execution_history"] = history
    started["updated_at"] = datetime.now(timezone.utc).isoformat()
    started["deployment"] = deployment
    started["deployment_operation"] = "DEPLOYMENT_INSPECTION"
    started["deployment_events"] = list(started.get("deployment_events") or []) + [{"at": deployment["checked_at"], "event": event, "status": deployment_status}]
    return started


def deployment_response(record: Mapping[str, Any], deployment: Mapping[str, Any], *, action: str = "none") -> str:
    return ("Deployment inspection complete.\n\n"
            f"Mission: {deployment.get('mission_id', 'UNKNOWN')}\n"
            f"Origin/main: {deployment.get('origin_main_commit', 'UNKNOWN')}\n"
            f"Production commit: {deployment.get('deployed_commit', 'UNKNOWN')}\n"
            f"Production build/deploy ID: {deployment.get('deployed_build_id', 'UNKNOWN')}\n"
            f"Match: {'YES' if deployment.get('deployed_commit') == deployment.get('origin_main_commit') else 'NO/UNKNOWN'}\n"
            f"Stale production: {deployment.get('stale_production', 'UNKNOWN')}\n"
            f"Deployment action: {action}\n"
            f"Production verification: {deployment.get('verification', 'UNKNOWN')}\n"
            "No new mission was created.")
