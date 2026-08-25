"""Read-only production deployment truth for Product Evolution operations."""

from __future__ import annotations

import re
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Optional

from .netlify_adapter import _netlify_environment, _netlify_executable, exact_sha_netlify_status

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TARGET = "https://goclearonline.cc"
NETLIFY_SITE_ID = "e8b7a0c2-9278-4b4c-a9a0-b950bcd66583"
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


def _cors_options(path: str) -> tuple[int, Mapping[str, str]]:
    try:
        completed = subprocess.run(["/usr/bin/curl", "-sS", "-L", "--max-time", "15", "-X", "OPTIONS", "-D", "-", "-o", "/dev/null", "-H", "Origin: https://goclearonline.cc", "-H", "Access-Control-Request-Method: POST", "-H", "Access-Control-Request-Headers: content-type,x-nexus-voice-session,x-nexus-voice-preview-sequence", path], capture_output=True, timeout=20, check=False)
        lines = completed.stdout.decode("iso-8859-1", "replace").splitlines()
        status_line = next((line for line in lines if line.startswith("HTTP/")), "")
        match = re.search(r"\s(\d{3})(?:\s|$)", status_line)
        headers = {}
        for line in lines[1:]:
            if ":" in line:
                key, value = line.split(":", 1)
                headers[key.strip().lower()] = value.strip()
        return (int(match.group(1)) if match else 0), headers
    except Exception:
        return 0, {}


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
    preview_cors_status, preview_cors_headers = _cors_options("https://voice.goclearonline.cc/v1/voice/preview")
    transcribe_cors_status, transcribe_cors_headers = _cors_options("https://voice.goclearonline.cc/v1/voice/transcribe")
    cors_ok = all(status == 204 for status in (preview_cors_status, transcribe_cors_status)) and all(headers.get("access-control-allow-origin") == "https://goclearonline.cc" for headers in (preview_cors_headers, transcribe_cors_headers))
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
        "cors_verification": "PASS" if cors_ok else ("FAIL" if preview_cors_status or transcribe_cors_status else "UNKNOWN"),
        "cors_evidence": {"preview_status": preview_cors_status, "transcribe_status": transcribe_cors_status, "preview_allow_origin": preview_cors_headers.get("access-control-allow-origin", "UNKNOWN"), "transcribe_allow_origin": transcribe_cors_headers.get("access-control-allow-origin", "UNKNOWN")},
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


def verify_release_markers(record: Mapping[str, Any], expected_commit: str, *, target: str = DEFAULT_TARGET) -> Dict[str, Any]:
    """Produce the bounded verification shape consumed by the release contract."""
    inspected = inspect_deployment(record, target=target, requested_commit=expected_commit)
    deployment = inspected.get("deployment") or {}
    markers = deployment.get("production_markers") or {}
    return {
        "https": "PASS" if markers.get("admin_http_status") == 200 else "FAIL",
        "admin": "PASS" if markers.get("asset_http_status") == 200 else "FAIL",
        "production_commit": deployment.get("deployed_commit", "UNKNOWN"),
        "voice_marker": "PASS" if markers.get("voice_notice_present") else "FAIL",
        "persistent_preview_guard": "PASS" if markers.get("persistent_preview_guard_present") and markers.get("wake_state_present") else "FAIL",
        "old_marker_absent": "PASS" if not markers.get("old_voice_notice_present", False) else "FAIL",
        "cors": deployment.get("cors_verification", "UNKNOWN"),
        "evidence": deployment,
    }


def inspect_netlify_control_plane() -> Dict[str, Any]:
    """Read the public Netlify site/deploy metadata without credentials or mutation."""
    site_status, _, site_bytes = _fetch(f"https://api.netlify.com/api/v1/sites/{NETLIFY_SITE_ID}")
    deploy_status, _, deploy_bytes = _fetch(f"https://api.netlify.com/api/v1/sites/{NETLIFY_SITE_ID}/deploys?per_page=20")
    try:
        site = json.loads(site_bytes.decode("utf-8")) if site_bytes else {}
    except (ValueError, TypeError):
        site = {}
    cli_site = {}
    try:
        cli_path = _netlify_executable()
        cli = subprocess.run([cli_path, "api", "getSite", "--data", json.dumps({"site_id": NETLIFY_SITE_ID})], cwd=ROOT, capture_output=True, text=True, timeout=20, check=False, env=_netlify_environment()) if cli_path else None
        if cli is not None and cli.returncode == 0:
            cli_site = json.loads(cli.stdout)
    except (OSError, ValueError, TypeError, subprocess.TimeoutExpired):
        cli_site = {}
    if cli_site:
        site = {**site, **cli_site}
    try:
        deploys = json.loads(deploy_bytes.decode("utf-8")) if deploy_bytes else []
    except (ValueError, TypeError):
        deploys = []
    published = site.get("published_deploy") or {}
    safe_deploys = [{key: item.get(key) for key in ("id", "state", "branch", "commit_ref", "created_at", "published_at", "context", "title", "build_id", "deploy_ssl_url")} for item in deploys[:20] if isinstance(item, dict)]
    main_deploys = [item for item in safe_deploys if item.get("branch") == "main" and item.get("context") == "production"]
    auto_deploy = bool(site.get("repo_url") and any(item.get("commit_ref") for item in main_deploys))
    latest = main_deploys[0] if main_deploys else {}
    return {
        "provider": "Netlify",
        "site_id": site.get("id") or NETLIFY_SITE_ID,
        "site_name": site.get("name", "UNKNOWN"),
        "custom_domain": site.get("custom_domain", DEFAULT_TARGET),
        "repo_url": site.get("repo_url", "UNKNOWN"),
        "production_branch": published.get("branch") or "UNKNOWN",
        "published_deploy_id": published.get("id", "UNKNOWN"),
        "published_deploy_state": published.get("state", "UNKNOWN"),
        "published_commit": published.get("commit_ref") or "UNKNOWN",
        "published_created_at": published.get("created_at", "UNKNOWN"),
        "published_url": published.get("deploy_ssl_url") or DEFAULT_TARGET,
        "previous_known_good_deploy_id": published.get("id", "UNKNOWN"),
        "previous_known_good_commit": published.get("commit_ref") or "UNKNOWN",
        "previous_known_good_created_at": published.get("created_at", "UNKNOWN"),
        "previous_known_good_url": published.get("deploy_ssl_url") or DEFAULT_TARGET,
        "recent_deploys": safe_deploys,
        "auto_deploy_enabled": "NO" if (site.get("build_settings") or {}).get("stop_builds") is True else ("YES" if auto_deploy else "UNKNOWN"),
        "builds_stopped": "YES" if (site.get("build_settings") or {}).get("stop_builds") is True else ("NO" if site.get("build_settings") else "UNKNOWN"),
        "main_push_mutates_production": "NO" if (site.get("build_settings") or {}).get("stop_builds") is True else ("YES" if auto_deploy else "UNKNOWN"),
        "git_pipeline_health": "FAIL" if latest.get("state") == "error" else ("PASS" if latest.get("state") == "ready" else "UNKNOWN"),
        "normal_git_pipeline": "FAILED" if latest.get("state") == "error" else "UNKNOWN",
        "api_read_status": site_status if site_status else deploy_status,
        "auth_available": bool(exact_sha_netlify_status().get("authenticated")),
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }
