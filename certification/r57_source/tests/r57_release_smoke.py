#!/usr/bin/env python3
"""Offline smoke check for the built, self-contained R57 package."""
from __future__ import annotations
import importlib, json, os, shutil, socket, subprocess, sys, tempfile, time, urllib.error, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RELEASE = ROOT / "dist/nexus-capability-actions-20261025-r57"

def main() -> None:
    launcher = RELEASE / "scripts/ops/nexus_mcp_bridge.sh"
    if not launcher.is_file() or not os.access(launcher, os.X_OK):
        raise SystemExit("R57_LAUNCHER_MISSING_OR_NOT_EXECUTABLE")
    zsh = shutil.which("zsh")
    if not zsh:
        raise SystemExit("ZSH_REQUIRED_FOR_LAUNCHER_ROOT_CHECK")
    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"),
           "NEXUS_MCP_LAUNCHER_ROOT_ONLY": "1"}
    launcher_root = subprocess.run([zsh, str(launcher)], cwd=RELEASE, env=env,
        capture_output=True, text=True, timeout=10, check=True).stdout.strip()
    if Path(launcher_root).resolve() != RELEASE.resolve():
        raise SystemExit("R57_LAUNCHER_ROOT_MISMATCH:" + launcher_root)

    import_env = {"PATH": env["PATH"], "PYTHONPATH": f"{RELEASE}:{RELEASE / 'scripts'}",
                  "PYTHONDONTWRITEBYTECODE": "1"}
    names = ["services.nexus_mcp.http_server", "services.nexus_mcp.server",
             "nexus_agent_platform.job_worker_once", "nexus_agent_platform.durable_jobs",
             "nexus_agent_platform.research_parent_workflow", "research.research_case_engine"]
    code = "import importlib,json,pathlib; names=" + repr(names) + "; print(json.dumps({n:str(pathlib.Path(importlib.import_module(n).__file__).resolve()) for n in names}))"
    result = subprocess.run([sys.executable, "-c", code], cwd=RELEASE, env=import_env,
        capture_output=True, text=True, timeout=30, check=True)
    imports = json.loads(result.stdout.strip().splitlines()[-1])
    if len(imports) != len(names) or any(not Path(path).is_relative_to(RELEASE.resolve()) for path in imports.values()):
        raise SystemExit("R57_IMPORT_OUTSIDE_RELEASE:" + json.dumps(imports, sort_keys=True))
    older = [path for path in imports.values() if any(f"nexus-capability-actions-202610{day}-r{release}" in path
              for day, release in (("24", 53), ("24", 55), ("25", 56)))]
    if older:
        raise SystemExit("R57_IMPORT_FROM_OLDER_RELEASE:" + repr(older))

    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    with tempfile.TemporaryDirectory(prefix="r57-smoke-") as temp:
        runtime_env = {**import_env, "NEXUS_MCP_BRIDGE_HOST": "127.0.0.1",
            "NEXUS_MCP_BRIDGE_PORT": str(port), "NEXUS_MCP_BRIDGE_TOKEN": "synthetic-r57-smoke-token",
            "NEXUS_REPO_ROOT": str(RELEASE), "NEXUS_RESEARCH_STATE_ROOT": str(Path(temp) / "state")}
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
                stderr = process.stderr.read()[-2000:] if process.stderr else ""
                raise SystemExit(f"R57_HTTP_SMOKE_FAILED:status={status};exit={process.poll()};stderr={stderr}")
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
    if _active_state_v2_release() != ("nexus-capability-actions-20261025-r57", True):
        raise SystemExit("R57_READINESS_RESOLVER_SMOKE_FAILED")
    print(json.dumps({"result":"PASS", "http_status":401, "runtime_root":str(RELEASE),
                      "imports":imports, "imports_from_older_releases":0}, sort_keys=True))

if __name__ == "__main__":
    main()
