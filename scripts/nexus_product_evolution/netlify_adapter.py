"""Fixed Netlify adapter for a future explicitly approved exact-SHA release.

The adapter is deliberately unavailable without the existing Netlify
credential. It accepts no command or path from a model or Telegram message.
"""

from __future__ import annotations

import os
import json
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
    worktree = Path(tempfile.mkdtemp(prefix="nexus-release-"))
    try:
        add = subprocess.run(["git", "worktree", "add", "--detach", str(worktree), commit], cwd=ROOT, capture_output=True, text=True, timeout=30, check=False)
        if add.returncode != 0:
            return {"status": "FAILED", "reason": "WORKTREE_CREATE_FAILED"}
        build = subprocess.run(["npm", "run", "build"], cwd=worktree, capture_output=True, text=True, timeout=300, check=False)
        if build.returncode != 0:
            return {"status": "FAILED", "reason": "BUILD_FAILED"}
        deploy = subprocess.run(["netlify", "deploy", "--prod", "--no-build", "--dir", str(worktree / "dist"), "--site", SITE_ID, "--json"], cwd=worktree, capture_output=True, text=True, timeout=300, check=False)
        if deploy.returncode != 0:
            return {"status": "FAILED", "reason": "NETLIFY_DEPLOY_FAILED"}
        return {"status": "PASS", "commit": commit, "target": target, "provider": "Netlify", "site_id": SITE_ID, "deploy_metadata": "REDACTED_SAFE_METADATA_ONLY"}
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
