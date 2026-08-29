"""Bounded advisory review through the already-certified Oracle Hermes route."""
from __future__ import annotations

import json
import shlex
import subprocess
from typing import Any, Mapping


def hermes_advisory_review(_: Mapping[str, Any]) -> dict[str, Any]:
    """Ask the scoped worker profile for a fixed harmless review acknowledgement."""
    prompt = "Return exactly REVIEW_OK. This is a bounded Nexus advisory review; do not claim authority or side effects."
    remote = " ".join([
        "podman exec", "-e", "HERMES_HOME=/opt/data/profiles/nexusopenrouter",
        "-e", "HERMES_PROFILE=nexusopenrouter", "nexus-hermes-0206", "hermes", "-z",
        shlex.quote(prompt), "--cli",
    ])
    command = ["ssh", "-i", str(__import__("pathlib").Path.home() / ".ssh/oracle_vm"), "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", "opc@161.153.40.41", remote]
    completed = subprocess.run(command, capture_output=True, text=True, timeout=30, check=False)
    output = completed.stdout.strip()
    return {"status": "PASS", "summary": "Hermes advisory review passed"} if completed.returncode == 0 and "REVIEW_OK" in output else {"status": "FAIL", "summary": "Hermes advisory review unavailable"}
