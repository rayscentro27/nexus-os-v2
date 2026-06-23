"""Shared helpers for nexus_runner handlers. Server-side only; no secrets printed."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent          # ~/nexus-os-v2/scripts
ROOT = SCRIPTS.parent                                       # repo root
sys.path.insert(0, str(SCRIPTS / "social"))
import _supabase as sb  # noqa: E402,F401  (re-exported for handlers)


def run_script(rel_path: str, args: list[str] | None = None, timeout: int = 120) -> dict:
    """Run a repo script as a subprocess (inherits env incl. SSL_CERT_FILE). Returns a
    safe summary. The called scripts never print secrets."""
    cmd = [sys.executable, str(ROOT / rel_path), *(args or [])]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=str(ROOT))
        tail = "\n".join((p.stdout or "").strip().splitlines()[-12:])
        return {"returncode": p.returncode, "stdout_tail": tail,
                "stderr_tail": "\n".join((p.stderr or "").strip().splitlines()[-4:])}
    except subprocess.TimeoutExpired:
        return {"returncode": 124, "stdout_tail": "", "stderr_tail": "timeout"}


def ok(output: dict) -> dict:
    return {"status": "done", "output": output, "error": None}


def fail(error: str, output: dict | None = None) -> dict:
    return {"status": "failed", "output": output or {}, "error": error[:300]}


def blocked(reason: str) -> dict:
    return {"status": "blocked", "output": {"reason": reason}, "error": reason[:300]}
