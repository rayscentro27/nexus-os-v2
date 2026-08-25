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


def _safe_tail(value: str, limit: int = 1200) -> str:
    text = "\n".join(value.splitlines()[-20:])[-limit:]
    text = re.sub(r"(?i)(bearer\s+)\S+", r"\1[REDACTED]", text)
    text = re.sub(r"(?i)(bearer\s+|token[=:]\s*|authorization[=:]\s*)\S+", r"\1[REDACTED]", text)
    text = re.sub(r"(?i)(NETLIFY_AUTH_TOKEN|SUPABASE_SERVICE_ROLE_KEY|[A-Z0-9_]*(?:TOKEN|SECRET|PASSWORD|API_KEY))=[^\s]+", r"\1=[REDACTED]", text)
    return text


def _build_environment(commit: str) -> Dict[str, str]:
    """Minimal non-secret build environment; never inherit credential variables."""
    return {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": str(Path.home()),
        "CI": "1",
        "NPM_CONFIG_AUDIT": "false",
        "NPM_CONFIG_FUND": "false",
        "VITE_BUILD_COMMIT": commit,
        "VITE_BUILD_BRANCH": "main",
        "VITE_BUILD_TIMESTAMP": commit,
        "VITE_NEXUS_VOICE_ENDPOINT": "https://voice.goclearonline.cc/v1/voice/transcribe",
    }


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


def _cleanup_worktree(worktree: Path) -> None:
    subprocess.run(["git", "worktree", "unlock", str(worktree)], cwd=ROOT, capture_output=True, timeout=30, check=False)
    subprocess.run(["git", "worktree", "remove", "--force", str(worktree)], cwd=ROOT, capture_output=True, timeout=30, check=False)
    shutil.rmtree(worktree, ignore_errors=True)


def _prepare_exact_sha(commit: str) -> Dict[str, Any]:
    """Build one exact SHA in an isolated, dependency-complete worktree."""
    if not FULL_SHA.fullmatch(commit):
        return {"status": "BLOCKED", "reason": "IMMUTABLE_FULL_SHA_REQUIRED", "phase": "validation"}
    worktree = Path(tempfile.mkdtemp(prefix="nexus-release-"))
    added = False
    try:
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
    return {
        "provider": "Netlify",
        "site_id": SITE_ID,
        "target": TARGET,
        "method": "fixed CLI upload from detached exact-SHA worktree",
        "authenticated": bool(os.environ.get("NETLIFY_AUTH_TOKEN")) or cli_auth,
        "available": (bool(os.environ.get("NETLIFY_AUTH_TOKEN")) or cli_auth) and shutil.which("netlify") is not None,
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
    prepared = _prepare_exact_sha(commit)
    if prepared.get("status") != "PASS":
        return prepared
    worktree = Path(str(prepared["worktree"]))
    try:
        deploy = subprocess.run(["netlify", "deploy", "--prod", "--no-build", "--dir", str(worktree / "dist"), "--site", SITE_ID, "--json"], cwd=worktree, env={**_build_environment(commit), "NETLIFY_CLI_TELEMETRY_DISABLED": "1"}, capture_output=True, text=True, timeout=300, check=False)
        if deploy.returncode != 0:
            return {"status": "FAILED", "reason": "NETLIFY_DEPLOY_FAILED", "phase": "netlify_deploy", "return_code": deploy.returncode, "stderr_tail_redacted": _safe_tail(deploy.stderr)}
        return {"status": "PASS", "commit": commit, "target": target, "provider": "Netlify", "site_id": SITE_ID, "artifact_hash": prepared.get("artifact_hash"), "deploy_metadata": "REDACTED_SAFE_METADATA_ONLY"}
    finally:
        subprocess.run(["git", "worktree", "remove", "--force", str(worktree)], cwd=ROOT, capture_output=True, timeout=30, check=False)
        shutil.rmtree(worktree, ignore_errors=True)


def rollback_exact_deploy(deploy_id: str) -> Dict[str, Any]:
    """Restore one pre-recorded Netlify deploy through the fixed API method."""
    if not deploy_id or deploy_id.upper() in {"UNKNOWN", "HEAD", "MAIN", "LATEST"} or not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._:-]{5,}", deploy_id):
        return {"status": "BLOCKED", "reason": "ROLLBACK_DEPLOY_ID_REQUIRED"}
    if not exact_sha_netlify_status()["authenticated"]:
        return {"status": "BLOCKED", "reason": "NETLIFY_AUTH_UNAVAILABLE"}
    try:
        restore = subprocess.run(["netlify", "api", "restoreSiteDeploy", "--data", json.dumps({"site_id": SITE_ID, "deploy_id": deploy_id})], cwd=ROOT, capture_output=True, text=True, timeout=60, check=False, env={**os.environ, "NETLIFY_CLI_TELEMETRY_DISABLED": "1", "CI": "1"})
    except subprocess.TimeoutExpired:
        return {"status": "FAILED", "reason": "NETLIFY_ROLLBACK_TIMEOUT", "deploy_id": deploy_id}
    if restore.returncode != 0:
        return {"status": "FAILED", "reason": "NETLIFY_ROLLBACK_FAILED", "deploy_id": deploy_id}
    return {"status": "PASS", "deploy_id": deploy_id, "provider": "Netlify", "site_id": SITE_ID, "metadata": "SAFE_METADATA_ONLY"}
