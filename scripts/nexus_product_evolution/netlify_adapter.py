"""Fixed Netlify adapter for a future explicitly approved exact-SHA release.

The adapter is deliberately unavailable without the existing Netlify
credential. It accepts no command or path from a model or Telegram message.
"""

from __future__ import annotations

import os
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
    return {
        "provider": "Netlify",
        "site_id": SITE_ID,
        "target": TARGET,
        "method": "fixed CLI upload from detached exact-SHA worktree",
        "authenticated": bool(os.environ.get("NETLIFY_AUTH_TOKEN")),
        "available": bool(os.environ.get("NETLIFY_AUTH_TOKEN")) and shutil.which("netlify") is not None,
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
    """Placeholder for the fixed provider rollback action, never a Git reset."""
    if not deploy_id or deploy_id.upper() in {"UNKNOWN", "HEAD", "MAIN", "LATEST"} or not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._:-]{5,}", deploy_id):
        return {"status": "BLOCKED", "reason": "ROLLBACK_DEPLOY_ID_REQUIRED"}
    if not exact_sha_netlify_status()["authenticated"]:
        return {"status": "BLOCKED", "reason": "NETLIFY_AUTH_UNAVAILABLE"}
    return {"status": "BLOCKED", "reason": "PROVIDER_ROLLBACK_ENDPOINT_NOT_AUTHENTICATED_IN_THIS_RUNTIME", "deploy_id": deploy_id}
