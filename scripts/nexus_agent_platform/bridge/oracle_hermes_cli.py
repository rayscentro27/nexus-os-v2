"""Governed Mac-to-Oracle Hermes 0.20.6 transport.

This adapter owns transport only.  The remote command is fixed, the prompt is
carried on stdin, and no user text is interpolated into a shell command.
"""
from __future__ import annotations

import os
import re
import subprocess
import time
from dataclasses import dataclass
from typing import Any


ORACLE_HOST = os.getenv("NEXUS_ORACLE_SSH_HOST", "161.153.40.41")
ORACLE_USER = os.getenv("NEXUS_ORACLE_SSH_USER", "opc")
ORACLE_KEY = os.path.expanduser(os.getenv("NEXUS_ORACLE_SSH_KEY", "~/.ssh/oracle_vm"))
ORACLE_CONTAINER = "nexus-hermes-0206"
ORACLE_HERMES = "/opt/hermes/.venv/bin/hermes"
ORACLE_HOME = "/opt/data/profiles/nova_nexus"
ORACLE_MODEL = "openai/gpt-4o-mini"
ORACLE_PROFILE = "nova_nexus"
ORACLE_TOOLSET = "nexus_mcp_remote"
SESSION_RE = re.compile(r"^[A-Za-z0-9_.:-]{1,160}$")


class OracleHermesUnavailable(RuntimeError):
    """Raised when the bounded Oracle transport cannot return a response."""


@dataclass(frozen=True)
class OracleHermesResult:
    response: str | None
    status: str
    error: str | None
    latency_ms: float
    runtime_host: str = "ORACLE"
    hermes_version: str = "0.20.6"
    profile: str = ORACLE_PROFILE
    provider: str = "openrouter"
    model: str = ORACLE_MODEL
    toolset: str = ORACLE_TOOLSET


def _remote_command() -> str:
    # This is intentionally constant: only the prompt travels over stdin.
    return (
        "podman exec -i nexus-hermes-0206 sh -lc "
        "'IFS= read -r session; prompt=$(cat); exec env HERMES_HOME=/opt/data/profiles/nova_nexus "
        "HERMES_PROFILE=nova_nexus /opt/hermes/.venv/bin/hermes "
        "-z \"$prompt\" -m openai/gpt-4o-mini -t nexus_mcp_remote "
        "--resume \"$session\" --pass-session-id --no-restore-cwd'"
    )


def run_oracle_hermes(message: str, session_id: str, *, timeout_seconds: float = 180.0,
                      request_id: str | None = None) -> OracleHermesResult:
    if not isinstance(message, str) or not message.strip():
        raise OracleHermesUnavailable("empty_message")
    if not SESSION_RE.fullmatch(session_id or ""):
        raise OracleHermesUnavailable("invalid_session_id")
    if timeout_seconds <= 0 or timeout_seconds > 300:
        raise OracleHermesUnavailable("invalid_timeout")
    if not os.path.isfile(ORACLE_KEY) or not os.access(ORACLE_KEY, os.R_OK):
        return OracleHermesResult(None, "UNAVAILABLE", "ssh_key_missing", 0.0)
    started = time.monotonic()
    command = [
        "/usr/bin/ssh", "-i", ORACLE_KEY, "-o", "BatchMode=yes",
        "-o", "ConnectTimeout=8", "-o", "ServerAliveInterval=15",
        "-o", "ServerAliveCountMax=2", "-o", "StrictHostKeyChecking=accept-new",
        f"{ORACLE_USER}@{ORACLE_HOST}", _remote_command(),
    ]
    try:
        completed = subprocess.run(
            command, input=f"{session_id}\n{message}", text=True, capture_output=True,
            timeout=timeout_seconds, check=False,
        )
    except subprocess.TimeoutExpired:
        return OracleHermesResult(None, "UNAVAILABLE", "oracle_timeout", round((time.monotonic() - started) * 1000, 1))
    except OSError as exc:
        return OracleHermesResult(None, "UNAVAILABLE", type(exc).__name__, round((time.monotonic() - started) * 1000, 1))
    elapsed = round((time.monotonic() - started) * 1000, 1)
    if completed.returncode != 0:
        return OracleHermesResult(None, "UNAVAILABLE", f"ssh_exit_{completed.returncode}", elapsed)
    response = completed.stdout.strip()
    if not response:
        return OracleHermesResult(None, "UNAVAILABLE", "empty_oracle_response", elapsed)
    return OracleHermesResult(response, "SUCCEEDED", None, elapsed)
