"""Fixed Netlify adapter for a future explicitly approved exact-SHA release.

The adapter is deliberately unavailable without the existing Netlify
credential. It accepts no command or path from a model or Telegram message.
"""

from __future__ import annotations

import os
import json
import hashlib
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[2]
SITE_ID = "e8b7a0c2-9278-4b4c-a9a0-b950bcd66583"
TARGET = "https://goclearonline.cc"
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
NODE_BIN = Path.home() / ".nvm/versions/node/v22.22.3/bin"


def _tool_path() -> str:
    """Return a bounded tool path suitable for launchd's minimal environment."""
    entries = [str(NODE_BIN), "/opt/homebrew/bin", "/usr/local/bin"]
    entries.extend(os.environ.get("PATH", "/usr/bin:/bin").split(os.pathsep))
    return os.pathsep.join(dict.fromkeys(item for item in entries if item))


def _netlify_executable() -> str | None:
    """Resolve the certified CLI even when launchd supplies a minimal PATH."""
    candidates = (
        Path.home() / ".nvm/versions/node/v22.22.3/bin/netlify",
        Path.home() / ".npm-global/bin/netlify",
        Path("/opt/homebrew/bin/netlify"),
        Path("/usr/local/bin/netlify"),
    )
    for candidate in candidates:
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return shutil.which("netlify")


def _safe_tail(value: str, limit: int = 1200) -> str:
    text = "\n".join(value.splitlines()[-20:])[-limit:]
    text = re.sub(r"(?i)(bearer\s+)\S+", r"\1[REDACTED]", text)
    text = re.sub(r"(?i)(bearer\s+|token[=:]\s*|authorization[=:]\s*)\S+", r"\1[REDACTED]", text)
    text = re.sub(r"(?i)(NETLIFY_AUTH_TOKEN|SUPABASE_SERVICE_ROLE_KEY|[A-Z0-9_]*(?:TOKEN|SECRET|PASSWORD|API_KEY))=[^\s]+", r"\1=[REDACTED]", text)
    return text


def _build_environment(commit: str) -> Dict[str, str]:
    """Minimal non-secret build environment; never inherit credential variables."""
    return {
        "PATH": _tool_path(),
        "HOME": str(Path.home()),
        "CI": "1",
        "NPM_CONFIG_AUDIT": "false",
        "NPM_CONFIG_FUND": "false",
        "VITE_BUILD_COMMIT": commit,
        "VITE_BUILD_BRANCH": "main",
        "VITE_BUILD_TIMESTAMP": commit,
        "VITE_NEXUS_VOICE_ENDPOINT": "https://voice.goclearonline.cc/v1/voice/transcribe",
    }


def _netlify_environment() -> Dict[str, str]:
    """Credential-limited environment for the fixed Netlify subprocess only."""
    env = {
        "PATH": _tool_path(),
        "HOME": str(Path.home()),
        "CI": "1",
        "NETLIFY_CLI_TELEMETRY_DISABLED": "1",
    }
    token = os.environ.get("NETLIFY_AUTH_TOKEN")
    if token:
        env["NETLIFY_AUTH_TOKEN"] = token
    return env


def _netlify_status_probe() -> Dict[str, Any]:
    """Run the fixed, read-only CLI status probe in the scheduler environment."""
    cli = _netlify_executable()
    if not cli:
        return {"status": "BLOCKED", "reason": "NETLIFY_CLI_UNAVAILABLE"}
    try:
        probe = subprocess.run(
            [cli, "status", "--json"],
            cwd=ROOT,
            env=_netlify_environment(),
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {"status": "BLOCKED", "reason": "NETLIFY_STATUS_TIMEOUT"}
    if probe.returncode != 0:
        return {"status": "BLOCKED", "reason": "NETLIFY_STATUS_FAILED", "return_code": probe.returncode, "stderr_tail_redacted": _safe_tail(probe.stderr)}
    try:
        payload = json.loads(probe.stdout)
    except (TypeError, ValueError):
        return {"status": "BLOCKED", "reason": "NETLIFY_STATUS_INVALID_JSON"}
    site = payload.get("siteData") if isinstance(payload, dict) else {}
    if not isinstance(site, dict):
        return {"status": "BLOCKED", "reason": "NETLIFY_SITE_UNRESOLVED"}
    site_id = site.get("site-id")
    site_url = site.get("site-url")
    if site_id != SITE_ID or site_url != TARGET:
        return {"status": "BLOCKED", "reason": "NETLIFY_SITE_BINDING_MISMATCH", "site_id": site_id or "UNKNOWN", "target": site_url or "UNKNOWN"}
    return {"status": "PASS", "site_id": site_id, "target": site_url}


def _artifact_hash(dist: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in dist.rglob("*") if item.is_file()):
        digest.update(str(path.relative_to(dist)).encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _dist_contains(dist: Path, needle: str) -> bool:
    for path in dist.rglob("*"):
        if not path.is_file():
            continue
        try:
            if needle in path.read_text(encoding="utf-8", errors="ignore"):
                return True
        except OSError:
            continue
    return False


def _safe_deploy_metadata(stdout: str, *, commit: str, artifact_hash: str) -> Dict[str, Any]:
    """Retain only non-sensitive identity fields from Netlify's JSON result."""
    try:
        payload = json.loads(stdout)
    except (TypeError, ValueError):
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    return {
        "deploy_id": payload.get("id") or payload.get("deploy_id") or "UNKNOWN",
        "deploy_url": payload.get("deploy_url") or payload.get("url") or "UNKNOWN",
        "deploy_ssl_url": payload.get("deploy_ssl_url") or payload.get("ssl_url") or "UNKNOWN",
        "state": payload.get("state") or "UNKNOWN",
        "site_id": payload.get("site_id") or SITE_ID,
        "commit": commit,
        "artifact_hash": artifact_hash,
    }


def _cleanup_worktree(worktree: Path) -> None:
    subprocess.run(["git", "worktree", "unlock", str(worktree)], cwd=ROOT, capture_output=True, timeout=30, check=False)
    # npm can leave a large node_modules tree; cleanup is bounded but must not
    # turn a successful exact-SHA preflight into an unhandled timeout.
    try:
        subprocess.run(["git", "worktree", "remove", "--force", str(worktree)], cwd=ROOT, capture_output=True, timeout=300, check=False)
    except subprocess.TimeoutExpired:
        return
    shutil.rmtree(worktree, ignore_errors=True)


def _cleanup_stale_adapter_worktrees() -> list[str]:
    """Remove only detached temporary worktrees created by this adapter."""
    try:
        listed = subprocess.run(["git", "worktree", "list", "--porcelain"], cwd=ROOT, capture_output=True, text=True, timeout=15, check=False)
    except subprocess.TimeoutExpired:
        return []
    removed: list[str] = []
    current_path = Path(tempfile.gettempdir()).resolve()
    blocks = listed.stdout.split("\n\n") if listed.returncode == 0 else []
    for block in blocks:
        lines = block.splitlines()
        path_line = next((line for line in lines if line.startswith("worktree ")), "")
        path = Path(path_line[9:]).resolve() if path_line else None
        if not path or path.parent != current_path or not path.name.startswith("nexus-release-") or "detached" not in lines:
            continue
        try:
            subprocess.run(["git", "worktree", "remove", "--force", str(path)], cwd=ROOT, capture_output=True, timeout=120, check=False)
            if not path.exists():
                removed.append(str(path))
        except subprocess.TimeoutExpired:
            continue
    return removed


def _prepare_exact_sha(commit: str) -> Dict[str, Any]:
    """Build one exact SHA in an isolated, dependency-complete worktree."""
    if not FULL_SHA.fullmatch(commit):
        return {"status": "BLOCKED", "reason": "IMMUTABLE_FULL_SHA_REQUIRED", "phase": "validation"}
    worktree = Path(tempfile.mkdtemp(prefix="nexus-release-"))
    added = False
    try:
        _cleanup_stale_adapter_worktrees()
        tracked = subprocess.run(["git", "ls-files", "--error-unmatch", "package.json", "package-lock.json"], cwd=ROOT, capture_output=True, text=True, timeout=30, check=False)
        if tracked.returncode != 0:
            shutil.rmtree(worktree, ignore_errors=True)
            return {"status": "BLOCKED", "reason": "LOCKFILE_INPUT_NOT_TRACKED", "phase": "validation", "return_code": tracked.returncode}
        try:
            add = subprocess.run(["git", "worktree", "add", "--detach", str(worktree), commit], cwd=ROOT, capture_output=True, text=True, timeout=30, check=False)
        except subprocess.TimeoutExpired:
            _cleanup_worktree(worktree)
            return {"status": "FAILED", "reason": "WORKTREE_CREATE_TIMEOUT", "phase": "worktree", "return_code": None}
        if add.returncode != 0:
            _cleanup_worktree(worktree)
            return {"status": "FAILED", "reason": "WORKTREE_CREATE_FAILED", "phase": "worktree", "return_code": add.returncode, "stderr_tail_redacted": _safe_tail(add.stderr)}
        added = True
        env = _build_environment(commit)
        npm_ci = subprocess.run(["npm", "ci"], cwd=worktree, env=env, capture_output=True, text=True, timeout=600, check=False)
        if npm_ci.returncode != 0:
            return {"status": "FAILED", "reason": "DEPENDENCY_INSTALL_FAILED", "phase": "npm_ci", "return_code": npm_ci.returncode, "stderr_tail_redacted": _safe_tail(npm_ci.stderr), "stdout_tail_redacted": _safe_tail(npm_ci.stdout), "worktree": str(worktree)}
        build = subprocess.run(["npm", "run", "build"], cwd=worktree, env=env, capture_output=True, text=True, timeout=600, check=False)
        if build.returncode != 0:
            return {"status": "FAILED", "reason": "BUILD_FAILED", "phase": "npm_build", "return_code": build.returncode, "stderr_tail_redacted": _safe_tail(build.stderr), "stdout_tail_redacted": _safe_tail(build.stdout), "worktree": str(worktree)}
        dist = worktree / "dist"
        if not dist.is_dir() or not any(dist.iterdir()):
            return {"status": "FAILED", "reason": "DIST_MISSING", "phase": "post_build", "return_code": 0, "worktree": str(worktree)}
        if not _dist_contains(dist, commit):
            return {"status": "FAILED", "reason": "BUILD_SHA_MARKER_MISMATCH", "phase": "post_build", "return_code": 0, "worktree": str(worktree)}
        return {"status": "PASS", "phase": "preflight", "commit": commit, "worktree": str(worktree), "artifact_hash": _artifact_hash(dist), "build_sha_marker": "PASS", "dist": str(dist), "npm_ci": "PASS", "build": "PASS"}
    finally:
        if added:
            # The caller uploads before cleanup; preflight cleanup is handled below.
            pass


def preflight_exact_sha(commit: str, target: str) -> Dict[str, Any]:
    """Run all production build checks without invoking Netlify deployment."""
    if target != TARGET:
        return {"status": "BLOCKED", "reason": "TARGET_NOT_ALLOWLISTED", "phase": "validation"}
    status = exact_sha_netlify_status()
    if not status["available"]:
        return {"status": "BLOCKED", "reason": "NETLIFY_AUTH_UNAVAILABLE", "phase": "auth", "netlify_available": False}
    result = _prepare_exact_sha(commit)
    worktree = result.get("worktree")
    if worktree:
        _cleanup_worktree(Path(worktree))
        result.pop("worktree", None)
        result.pop("dist", None)
    result["netlify_available"] = True
    return result


def exact_sha_netlify_status() -> Dict[str, Any]:
    config_path = Path.home() / "Library" / "Preferences" / "netlify" / "config.json"
    cli_auth = False
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
        cli_auth = any(bool((user.get("auth") or {}).get("token")) for user in (config.get("users") or {}).values() if isinstance(user, dict))
    except (OSError, ValueError, TypeError):
        cli_auth = False
    cli = _netlify_executable()
    authenticated = bool(os.environ.get("NETLIFY_AUTH_TOKEN")) or cli_auth
    probe = _netlify_status_probe() if authenticated and cli else {"status": "BLOCKED", "reason": "NETLIFY_AUTH_UNAVAILABLE"}
    return {
        "provider": "Netlify",
        "site_id": SITE_ID,
        "target": TARGET,
        "method": "fixed CLI upload from detached exact-SHA worktree",
        "authenticated": authenticated,
        "cli_available": cli is not None,
        "available": authenticated and cli is not None and probe.get("status") == "PASS",
        "auth_source": "RUNTIME_TOKEN" if os.environ.get("NETLIFY_AUTH_TOKEN") else ("CLI_CONFIG" if cli_auth else "NONE"),
        "probe": probe,
    }


def deploy_exact_sha(commit: str, target: str) -> Dict[str, Any]:
    """Deploy only the approved SHA through the fixed Netlify CLI procedure."""
    if not FULL_SHA.fullmatch(commit):
        return {"status": "BLOCKED", "reason": "IMMUTABLE_FULL_SHA_REQUIRED"}
    if target != TARGET:
        return {"status": "BLOCKED", "reason": "TARGET_NOT_ALLOWLISTED"}
    status = exact_sha_netlify_status()
    if not status["available"]:
        return {"status": "BLOCKED", "reason": "NETLIFY_AUTH_UNAVAILABLE", "provider": "Netlify", "site_id": SITE_ID}
    netlify = _netlify_executable()
    if not netlify:
        return {"status": "BLOCKED", "reason": "NETLIFY_CLI_UNAVAILABLE", "provider": "Netlify", "site_id": SITE_ID}
    prepared = _prepare_exact_sha(commit)
    if prepared.get("status") != "PASS":
        return prepared
    worktree = Path(str(prepared["worktree"]))
    try:
        deploy = subprocess.run([netlify, "deploy", "--prod", "--no-build", "--dir", str(worktree / "dist"), "--site", SITE_ID, "--json"], cwd=worktree, env=_netlify_environment(), capture_output=True, text=True, timeout=300, check=False)
        if deploy.returncode != 0:
            return {"status": "FAILED", "reason": "NETLIFY_DEPLOY_FAILED", "phase": "netlify_deploy", "return_code": deploy.returncode, "stderr_tail_redacted": _safe_tail(deploy.stderr)}
        metadata = _safe_deploy_metadata(deploy.stdout, commit=commit, artifact_hash=str(prepared.get("artifact_hash") or "UNKNOWN"))
        return {"status": "PASS", "commit": commit, "target": target, "provider": "Netlify", "site_id": SITE_ID, "artifact_hash": prepared.get("artifact_hash"), **metadata}
    finally:
        subprocess.run(["git", "worktree", "remove", "--force", str(worktree)], cwd=ROOT, capture_output=True, timeout=300, check=False)
        shutil.rmtree(worktree, ignore_errors=True)


def rollback_exact_deploy(deploy_id: str) -> Dict[str, Any]:
    """Restore one pre-recorded Netlify deploy through the fixed API method."""
    if not deploy_id or deploy_id.upper() in {"UNKNOWN", "HEAD", "MAIN", "LATEST"} or not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._:-]{5,}", deploy_id):
        return {"status": "BLOCKED", "reason": "ROLLBACK_DEPLOY_ID_REQUIRED"}
    if not exact_sha_netlify_status()["authenticated"]:
        return {"status": "BLOCKED", "reason": "NETLIFY_AUTH_UNAVAILABLE"}
    netlify = _netlify_executable()
    if not netlify:
        return {"status": "BLOCKED", "reason": "NETLIFY_CLI_UNAVAILABLE"}
    try:
        restore = subprocess.run([netlify, "api", "restoreSiteDeploy", "--data", json.dumps({"site_id": SITE_ID, "deploy_id": deploy_id})], cwd=ROOT, capture_output=True, text=True, timeout=60, check=False, env=_netlify_environment())
    except subprocess.TimeoutExpired:
        return {"status": "FAILED", "reason": "NETLIFY_ROLLBACK_TIMEOUT", "deploy_id": deploy_id}
    if restore.returncode != 0:
        return {"status": "FAILED", "reason": "NETLIFY_ROLLBACK_FAILED", "deploy_id": deploy_id}
    return {"status": "PASS", "deploy_id": deploy_id, "provider": "Netlify", "site_id": SITE_ID, "metadata": "SAFE_METADATA_ONLY"}
