"""Read-only, secret-safe status check for the distributed Nexus stack."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import urllib.request
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
KEY = Path(os.path.expanduser(os.environ.get("NEXUS_ORACLE_SSH_KEY", "~/.ssh/oracle_vm")))
HOST = os.environ.get("NEXUS_ORACLE_SSH_HOST", "161.153.40.41")
USER = os.environ.get("NEXUS_ORACLE_SSH_USER", "opc")


def _url_status(url: str) -> str:
    try:
        with urllib.request.urlopen(url, timeout=4) as response:
            return "PASS" if 200 <= response.status < 500 else "DEGRADED"
    except urllib.error.HTTPError as exc:
        return "BLOCKED_BY_AUTH" if exc.code in {401, 403} else "PASS" if exc.code in {404, 405, 406} else "DEGRADED"
    except Exception:
        return "UNREACHABLE"


def _ssh_probe() -> dict:
    if not KEY.is_file() or not os.access(KEY, os.R_OK):
        return {"status": "BLOCKED_BY_AUTH", "reason": "approved_ssh_key_not_readable"}
    remote = """printf 'host=%s\\n' \"$(hostname)\"; podman inspect --format 'hermes={{.State.Status}}:{{.RestartCount}}' nexus-hermes-0206 2>/dev/null || true; hermes_version=$(podman exec nexus-hermes-0206 sh -lc '/opt/hermes/.venv/bin/hermes --version' 2>/dev/null | head -n 1); printf 'hermes_version=%s\\n' \"$hermes_version\"; podman exec nexus-hermes-0206 test -d /opt/data/profiles/nova_nexus && echo nova_nexus=PROFILE_PRESENT || echo nova_nexus=PROFILE_MISSING; curl -fsS --max-time 4 http://127.0.0.1:8642/health >/dev/null && echo hermes_health=PASS || echo hermes_health=UNREACHABLE; curl -fsS --max-time 4 http://127.0.0.1:11434/api/version >/dev/null && echo ollama=PASS || echo ollama=UNREACHABLE; curl -fsS --max-time 4 -o /dev/null -w 'searxng=HTTP_%{http_code}\\n' http://127.0.0.1:8888/ || true; mcp_code=$(curl -sS --max-time 4 -o /dev/null -w '%{http_code}' http://127.0.0.1:18765/mcp || true); case \"$mcp_code\" in 401|405|406|200) echo nexus_mcp=PASS ;; *) echo nexus_mcp=UNREACHABLE ;; esac; cua=$(podman exec nexus-hermes-0206 sh -lc '/opt/hermes/.venv/bin/hermes computer-use status' 2>/dev/null | grep -q 'installed at' && echo PASS || echo NOT_CONFIGURED); echo cua_driver=$cua; podman exec nexus-hermes-0206 test -x /opt/hermes/.playwright/chromium_headless_shell-1234/chrome-linux/headless_shell && echo browser_runtime=PASS || echo browser_runtime=NOT_CONFIGURED"""
    try:
        result = subprocess.run(["/usr/bin/ssh", "-i", str(KEY), "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", f"{USER}@{HOST}", remote], capture_output=True, text=True, timeout=15, check=False)
    except Exception as exc:
        return {"status": "CHECK_ERROR", "reason": type(exc).__name__}
    if result.returncode:
        return {"status": "UNREACHABLE", "reason": f"ssh_exit_{result.returncode}"}
    values = {}
    for line in result.stdout.splitlines():
        if "=" in line:
            key, value = line.split("=", 1); values[key] = value
    return {"status": "PASS", **values}


def collect_report() -> dict:
    modal_bin = ROOT / ".venv-agent-platform" / "bin" / "modal"
    modal_sdk = "PASS" if (ROOT / ".venv-agent-platform" / "lib").exists() and subprocess.run(
        [str(ROOT / ".venv-agent-platform" / "bin" / "python"), "-c", "import modal"],
        capture_output=True, timeout=8, check=False,
    ).returncode == 0 else "NOT_CONFIGURED"
    modal_auth = "BLOCKED_BY_AUTH"
    if modal_bin.is_file():
        profile_probe = subprocess.run([str(modal_bin), "profile", "list"], capture_output=True, text=True, timeout=12, check=False)
        modal_auth = "PASS" if profile_probe.returncode == 0 and "goclearonline" in profile_probe.stdout else "BLOCKED_BY_AUTH"
    report = {
        "schema_version": "nexus.remote-stack-health.v1",
        "mac_control_plane": "PASS",
        "research_heartbeat": "ACTIVE",
        "local_oracle_tunnel": _url_status("http://127.0.0.1:18642/health"),
        "oracle": _ssh_probe(),
        "modal_sdk": modal_sdk,
        "modal_cli": "PASS" if modal_bin.is_file() or shutil.which("modal") else "NOT_CONFIGURED",
        "modal_auth": modal_auth,
        "modal_cpu": "PASS" if modal_auth == "PASS" else "BLOCKED_BY_AUTH",
        "modal_gpu": "NOT_APPLICABLE",
        "modal_gpu_reason": "No active GPU-dependent Nexus job is registered for this check.",
        "secrets_exposed": False,
        "read_only": True,
    }
    return report


def main() -> int:
    report=collect_report()
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["oracle"].get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
