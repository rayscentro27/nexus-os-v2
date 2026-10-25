#!/usr/bin/env python3
"""Offline R60 launcher, HTTP, import-root, readiness, and selector smoke."""
from __future__ import annotations

import hashlib
import importlib
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RELEASE = ROOT / "dist/nexus-capability-actions-20261025-r60"


def main() -> None:
    launcher = RELEASE / "scripts/ops/nexus_mcp_bridge.sh"
    if not launcher.is_file() or not os.access(launcher, os.X_OK):
        raise SystemExit("R60_LAUNCHER_MISSING_OR_NOT_EXECUTABLE")
    zsh = shutil.which("zsh")
    if not zsh:
        raise SystemExit("ZSH_REQUIRED_FOR_LAUNCHER_ROOT_CHECK")
    launcher_env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"),
                    "NEXUS_MCP_LAUNCHER_ROOT_ONLY": "1"}
    resolved = subprocess.run([zsh, str(launcher)], cwd=RELEASE, env=launcher_env,
        capture_output=True, text=True, timeout=10, check=True).stdout.strip()
    if Path(resolved).resolve() != RELEASE.resolve():
        raise SystemExit("R60_LAUNCHER_ROOT_MISMATCH")

    names = ["services.nexus_mcp.http_server", "nexus_agent_platform.job_worker_once",
             "nexus_agent_platform.durable_jobs", "nexus_agent_platform.job_worker_supervisor",
             "nexus_agent_platform.supabase_egress_guard", "research.research_state_v2",
             "nexus_agent_platform.research_parent_adapters",
             "nexus_agent_platform.research_only_execution",
             "nexus_agent_platform.research_parent_workflow", "research.research_case_engine"]
    import_env = {"PATH": launcher_env["PATH"], "PYTHONPATH": f"{RELEASE}:{RELEASE / 'scripts'}",
                  "PYTHONDONTWRITEBYTECODE": "1"}
    code = ("import importlib,json,pathlib; names=" + repr(names) +
        "; print(json.dumps({n:str(pathlib.Path(importlib.import_module(n).__file__).resolve()) for n in names}))")
    imported = subprocess.run([sys.executable, "-c", code], cwd=RELEASE, env=import_env,
        capture_output=True, text=True, timeout=30, check=True)
    imports = json.loads(imported.stdout.strip().splitlines()[-1])
    if any(not Path(path).is_relative_to(RELEASE.resolve()) for path in imports.values()):
        raise SystemExit("R60_IMPORT_OUTSIDE_RELEASE")
    older = [path for path in imports.values() if any(
        f"nexus-capability-actions-202610{day}-r{release}" in path
        for day, release in (("23", 52), ("24", 53), ("24", 54), ("24", 55),
                             ("25", 56), ("25", 57), ("25", 58), ("25", 59)))]
    if older:
        raise SystemExit("R60_IMPORT_FROM_OLDER_RELEASE")

    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    with tempfile.TemporaryDirectory(prefix="r60-smoke-") as temporary:
        runtime_env = {**import_env, "NEXUS_MCP_BRIDGE_HOST": "127.0.0.1",
            "NEXUS_MCP_BRIDGE_PORT": str(port), "NEXUS_MCP_BRIDGE_TOKEN": "synthetic-r60-smoke-token",
            "NEXUS_REPO_ROOT": str(RELEASE),
            "NEXUS_RESEARCH_STATE_ROOT": str(Path(temporary) / "state")}
        process = subprocess.Popen([sys.executable, "-m", "services.nexus_mcp.http_server"],
            cwd=RELEASE, env=runtime_env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        status = None
        try:
            deadline = time.monotonic() + 20
            while time.monotonic() < deadline and process.poll() is None:
                try:
                    urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=1)
                except urllib.error.HTTPError as error:
                    status = error.code
                    break
                except (urllib.error.URLError, TimeoutError, ConnectionError):
                    time.sleep(0.2)
            if process.poll() is not None or status != 401:
                raise SystemExit(f"R60_HTTP_SMOKE_FAILED:status={status};exit={process.poll()}")
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)

    os.environ["NEXUS_ACTIVE_RESEARCH_RELEASE"] = str(RELEASE)
    sys.path.insert(0, str(RELEASE / "scripts"))
    from nexus_agent_platform.stability_supervisor import _active_state_v2_release
    if _active_state_v2_release() != ("nexus-capability-actions-20261025-r60", True):
        raise SystemExit("R60_READINESS_RESOLVER_SMOKE_FAILED")
    from nexus_agent_platform.research_only_execution import _answer_excerpt
    question = ("According to the official Python documentation, what does "
        "pathlib.Path.is_file() return when the path does not exist? Allowed source URL: "
        "https://docs.python.org/3/library/pathlib.html")
    fixture = [{"tag": "dt", "id": "pathlib.Path.is_file", "section_id": "",
                "heading": "", "text": "Path.is_file()"},
               {"tag": "dd", "id": "", "section_id": "", "heading": "",
                "text": "Return True for regular files and False if the path does not exist."}]
    answer = _answer_excerpt(question, "", fixture)
    if not answer or "False" not in answer or "does not exist" not in answer:
        raise SystemExit("R60_ANNOTATED_GOLDEN_SELECTOR_SMOKE_FAILED")
    manifest_path = RELEASE / "R60_RELEASE_MANIFEST.json"
    print(json.dumps({"result": "PASS", "http_status": status,
        "runtime_root": str(RELEASE), "imports": imports,
        "imports_from_older_releases": 0, "golden_summary": answer,
        "manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest()}, sort_keys=True))


if __name__ == "__main__":
    main()
