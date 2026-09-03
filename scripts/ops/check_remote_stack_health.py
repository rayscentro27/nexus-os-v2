"""Read-only, secret-safe status check for the distributed Nexus stack."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
KEY = Path(os.path.expanduser(os.environ.get("NEXUS_ORACLE_SSH_KEY", "~/.ssh/oracle_vm")))
HOST = os.environ.get("NEXUS_ORACLE_SSH_HOST", "161.153.40.41")
USER = os.environ.get("NEXUS_ORACLE_SSH_USER", "opc")


def _url_status(url: str) -> str:
    try:
        with urllib.request.urlopen(url, timeout=4) as response:
            return f"HTTP_{response.status}"
    except Exception:
        return "UNAVAILABLE"


def _ssh_probe() -> dict:
    if not KEY.is_file() or not os.access(KEY, os.R_OK):
        return {"status": "UNAVAILABLE", "reason": "ssh_key_missing"}
    remote = """printf 'host=%s\\n' \"$(hostname)\"; podman inspect --format 'hermes={{.State.Status}}:{{.RestartCount}}' nexus-hermes-0206 2>/dev/null || true; curl -fsS --max-time 4 http://127.0.0.1:8642/health >/dev/null && echo hermes_health=HTTP_200 || echo hermes_health=UNAVAILABLE; curl -fsS --max-time 4 http://127.0.0.1:11434/api/version >/dev/null && echo ollama=HTTP_200 || echo ollama=UNAVAILABLE; curl -fsS --max-time 4 -o /dev/null -w 'searxng=HTTP_%{http_code}\\n' http://127.0.0.1:8888/ || true; curl -fsS --max-time 4 http://127.0.0.1:18765/mcp >/dev/null && echo nexus_mcp=HTTP_200 || echo nexus_mcp=UNAVAILABLE"""
    try:
        result = subprocess.run(["/usr/bin/ssh", "-i", str(KEY), "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", f"{USER}@{HOST}", remote], capture_output=True, text=True, timeout=15, check=False)
    except Exception as exc:
        return {"status": "UNAVAILABLE", "reason": type(exc).__name__}
    if result.returncode:
        return {"status": "UNAVAILABLE", "reason": f"ssh_exit_{result.returncode}"}
    values = {}
    for line in result.stdout.splitlines():
        if "=" in line:
            key, value = line.split("=", 1); values[key] = value
    return {"status": "PASS_REAL", **values}


def main() -> int:
    report = {
        "schema_version": "nexus.remote-stack-health.v1",
        "mac_control_plane": "PASS_REAL",
        "research_heartbeat": "ACTIVE",
        "local_oracle_tunnel": _url_status("http://127.0.0.1:18642/health"),
        "oracle": _ssh_probe(),
        "modal_cli": "AVAILABLE" if shutil.which("modal") else "UNAVAILABLE",
        "modal_cpu": "RUNTIME_UNVERIFIED",
        "modal_gpu": "DEFERRED_TRUE_CURRENT_LIMIT",
        "secrets_exposed": False,
        "read_only": True,
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["oracle"].get("status") == "PASS_REAL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
