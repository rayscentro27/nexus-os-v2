from __future__ import annotations

import importlib
import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


def _release_root() -> Path:
    value = os.environ.get("R55_TEST_ROOT")
    assert value, "R55_TEST_ROOT must point at the assembled release"
    root = Path(value).resolve()
    assert root.is_dir()
    return root


def test_r55_launcher_resolves_its_own_release_root_and_pythonpath():
    root = _release_root()
    launcher = root / "scripts/ops/nexus_mcp_bridge.sh"
    text = launcher.read_text()
    assert 'ROOT="$(cd "$SCRIPT_DIR/../.." && pwd -P)"' in text
    assert 'export PYTHONPATH="$ROOT:$ROOT/scripts"' in text
    assert 'exec "$PYTHON" -m uvicorn services.nexus_mcp.http_server:app' in text
    assert "nexus-capability-actions-20261024-r53" not in text


def test_r55_has_all_direct_production_entrypoints():
    root = _release_root()
    for relative in (
        "scripts/ops/nexus_mcp_bridge.sh", "services/nexus_mcp/http_server.py",
        "services/nexus_mcp/server.py", "scripts/nexus_agent_platform/job_worker_once.py",
        "scripts/nexus_agent_platform/durable_jobs.py",
        "scripts/nexus_agent_platform/research_only_execution.py",
        "scripts/research/research_case_engine.py",
    ):
        assert (root / relative).is_file(), relative


def test_r55_runtime_imports_resolve_inside_release_not_r53():
    root = _release_root()
    code = r"""
import importlib, json, pathlib
names = ["services.nexus_mcp.http_server", "services.nexus_mcp.server",
         "nexus_agent_platform.job_worker_once", "nexus_agent_platform.durable_jobs",
         "nexus_agent_platform.research_parent_workflow", "research.research_case_engine"]
rows = {}
for name in names:
    module = importlib.import_module(name)
    rows[name] = str(pathlib.Path(module.__file__).resolve())
print(json.dumps(rows))
"""
    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"),
           "PYTHONPATH": f"{root}:{root / 'scripts'}", "PYTHONDONTWRITEBYTECODE": "1"}
    result = subprocess.run([sys.executable, "-c", code], cwd=root, env=env,
        capture_output=True, text=True, timeout=30, check=True)
    origins = json.loads(result.stdout.strip().splitlines()[-1])
    assert len(origins) == 6
    assert all(str(root) in path for path in origins.values()), origins
    assert not any("nexus-capability-actions-20261024-r53" in path for path in origins.values())


def test_r55_http_server_starts_and_unauthenticated_probe_is_401(tmp_path):
    root = _release_root()
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "PYTHONPATH": f"{root}:{root / 'scripts'}", "PYTHONDONTWRITEBYTECODE": "1",
        "NEXUS_MCP_BRIDGE_HOST": "127.0.0.1", "NEXUS_MCP_BRIDGE_PORT": str(port),
        "NEXUS_MCP_BRIDGE_TOKEN": "synthetic-r55-test-token",
        "NEXUS_REPO_ROOT": str(root), "NEXUS_RESEARCH_STATE_ROOT": str(tmp_path / "state"),
    }
    process = subprocess.Popen([sys.executable, "-m", "services.nexus_mcp.http_server"],
        cwd=root, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    status = None
    try:
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            if process.poll() is not None:
                break
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=1)
            except urllib.error.HTTPError as exc:
                status = exc.code
                break
            except (urllib.error.URLError, TimeoutError, ConnectionError):
                time.sleep(0.2)
        assert process.poll() is None, "R55 HTTP server exited before serving"
        assert status == 401
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
        if process.returncode not in (0, -15):
            stderr = process.stderr.read() if process.stderr else ""
            assert False, f"R55 HTTP server exit={process.returncode}: {stderr[-1000:]}"


def test_r55_contains_r53_host_egress_and_supervision_runtime():
    root = _release_root()
    supervisor = (root / "scripts/nexus_agent_platform/job_worker_supervisor.py").read_text()
    host = (root / "scripts/nexus_agent_platform/stability_supervisor.py").read_text()
    state = (root / "scripts/research/research_state_v2.py").read_text()
    worker = (root / "scripts/nexus_agent_platform/job_worker_once.py").read_text()
    assert "_exact_exit_recovery" in supervisor
    assert "get_host_execution_gate" in host and "research_state_architecture" in host
    assert "list_current" in state
    assert "RESEARCH_ONLY" in worker and "RESEARCH_PARENT_CONTINUATION" in worker


def test_r55_release_manifest_has_complete_composition_and_no_runtime_data():
    root = _release_root()
    manifest = json.loads((root / "R55_RELEASE_MANIFEST.json").read_text())
    assert (root / "RELEASE_MANIFEST.sha256").is_file()
    assert (root / "reports").is_dir()
    assert manifest["release_id"] == "nexus-capability-actions-20261024-r55"
    assert manifest["base_release"]["release_id"] == "nexus-capability-actions-20261024-r53"
    assert manifest["overlay_release"]["release_id"] == "nexus-capability-actions-20261024-r54"
    assert manifest["runtime_file_count"] == len(manifest["payload_sha256"])
    for relative in manifest["payload_sha256"]:
        assert not relative.endswith((".sqlite", ".sqlite3", ".db", ".jsonl", ".log", ".env"))
