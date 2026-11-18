#!/usr/bin/env python3
"""Bounded preflight for the existing Nexus Research Golden Path.

This validator is read-only. It does not enqueue work, invoke providers, or
change launchd configuration. --live adds authenticated MCP, policy, and
capacity probes; static mode deliberately fails closed for those live gates.
"""
from __future__ import annotations

import argparse
import json
import os
import plistlib
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


def _plist(path: Path) -> dict[str, Any]:
    with path.open("rb") as stream:
        value = plistlib.load(stream)
    if not isinstance(value, dict):
        raise ValueError(f"INVALID_LAUNCHD_PLIST:{path}")
    return value


def _release_from_plist(value: dict[str, Any]) -> str | None:
    haystack = " ".join(str(x) for x in value.get("ProgramArguments", []))
    haystack += " " + str(value.get("Program", ""))
    match = re.search(r"nexus-capability-actions-[A-Za-z0-9._-]+", haystack)
    return match.group(0) if match else None


def _runtime_env_value(path: Path, key: str) -> str | None:
    if not path.is_file():
        return None
    pattern = re.compile(rf"^\s*{re.escape(key)}\s*=\s*(.*?)\s*$")
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = pattern.match(line)
        if match:
            raw = match.group(1)
            if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in "\"'":
                raw = raw[1:-1]
            return os.path.expanduser(raw)
    return None


def _effective_state_root(plist_value: dict[str, Any], runtime_env: Path) -> str | None:
    env = plist_value.get("EnvironmentVariables", {})
    explicit = env.get("NEXUS_RESEARCH_STATE_ROOT") or _runtime_env_value(runtime_env, "NEXUS_RESEARCH_STATE_ROOT")
    if explicit:
        return str(Path(str(explicit)).expanduser().resolve())
    repo = env.get("NEXUS_REPO_ROOT") or _runtime_env_value(runtime_env, "NEXUS_REPO_ROOT")
    if not repo:
        args = [str(value) for value in plist_value.get("ProgramArguments", [])]
        wrapper = next((Path(value) for value in args if value.endswith("nexus_mcp_bridge.sh")), None)
        if wrapper and wrapper.is_file():
            match = re.search(r'^CANONICAL="([^"]+)"', wrapper.read_text(encoding="utf-8", errors="replace"), re.M)
            repo = match.group(1) if match else None
    if repo:
        repo_path = Path(str(repo)).expanduser().resolve()
        return str((Path.home() / ".nexus/state/research").resolve()
                   if (repo_path / "RELEASE_MANIFEST.sha256").is_file()
                   else (repo_path / "data").resolve())
    return None


def _failure(failures: list[str], condition: bool, code: str) -> None:
    if not condition:
        failures.append(code)


def _host_failures() -> list[str]:
    failures: list[str] = []
    try:
        result = subprocess.run(["/bin/ps", "-axo", "state=,command="], capture_output=True,
                                text=True, timeout=3, check=True)
        for row in result.stdout.splitlines():
            if any(token in row for token in ("uvicorn services.nexus_mcp", "dispatcher_once.py", "job_worker_once.py")):
                state = row.strip().split(maxsplit=1)[0]
                if "U" in state:
                    failures.append("NEXUS_PROCESS_UNINTERRUPTIBLE_IO")
                    break
    except (OSError, subprocess.SubprocessError):
        failures.append("HOST_PROCESS_STATE_UNAVAILABLE")
    try:
        pressure = subprocess.run(["/usr/bin/memory_pressure"], capture_output=True,
                                  text=True, timeout=3, check=True).stdout
        match = re.search(r"free percentage:\s*(\d+)%", pressure)
        if match and int(match.group(1)) < 10:
            failures.append("HOST_MEMORY_PRESSURE_CRITICAL")
        elif not match:
            failures.append("HOST_MEMORY_PRESSURE_UNAVAILABLE")
    except (OSError, subprocess.SubprocessError):
        failures.append("HOST_MEMORY_PRESSURE_UNAVAILABLE")
    try:
        usage = shutil.disk_usage("/")
        if usage.free < 10 * 1024**3:
            failures.append("HOST_DISK_FREE_BELOW_10_GIB")
    except OSError:
        failures.append("HOST_DISK_STATUS_UNAVAILABLE")
    try:
        load = os.getloadavg()[0]
        cpus = os.cpu_count() or 1
        if load >= max(4.0, cpus * 1.5):
            failures.append("HOST_LOAD_ABOVE_WORKER_GUARD")
    except (OSError, AttributeError):
        failures.append("HOST_LOAD_UNAVAILABLE")
    return failures


def validate_static(contract: dict[str, Any], *, repo_root: Path, release_root: Path,
                    dispatcher_plist: Path, mcp_plist: Path, runtime_env: Path,
                    codex_override: str | None = None) -> list[str]:
    failures: list[str] = []
    _failure(failures, release_root.is_dir(), "RELEASE_ROOT_MISSING")
    _failure(failures, (release_root / "RELEASE_MANIFEST.sha256").is_file(), "RELEASE_MANIFEST_MISSING")
    expected_release = str(contract.get("release_id") or "")
    _failure(failures, release_root.name == expected_release, "RELEASE_ID_MISMATCH")
    for name, relative in contract.get("release_components", {}).items():
        _failure(failures, (release_root / relative).is_file(), f"RELEASE_COMPONENT_MISSING:{name}")
    try:
        dispatcher = _plist(dispatcher_plist)
        mcp = _plist(mcp_plist)
    except (OSError, ValueError, plistlib.InvalidFileException):
        return failures + ["LAUNCHD_CONFIGURATION_UNREADABLE"]
    _failure(failures, dispatcher.get("Label") == contract["services"]["DURABLE_DISPATCHER"]["label"],
             "DISPATCHER_LABEL_MISMATCH")
    _failure(failures, mcp.get("Label") == contract["services"]["MCP"]["label"], "MCP_LABEL_MISMATCH")
    dispatcher_release = _release_from_plist(dispatcher)
    mcp_release = _release_from_plist(mcp)
    _failure(failures, dispatcher_release == expected_release, "DISPATCHER_RELEASE_MISMATCH")
    _failure(failures, mcp_release == expected_release, "MCP_RELEASE_MISMATCH")
    _failure(failures, dispatcher_release == mcp_release, "MCP_DISPATCHER_RELEASES_DIFFER")

    dispatcher_root = _effective_state_root(dispatcher, runtime_env)
    mcp_root = _effective_state_root(mcp, runtime_env)
    expected_root = dispatcher_root
    state_roots = [item for item in (dispatcher_root, mcp_root) if item]
    _failure(failures, bool(expected_root), "RESEARCH_STATE_ROOT_UNCONFIGURED")
    _failure(failures, len(state_roots) == 2 and all(item == expected_root for item in state_roots),
             "RESEARCH_STATE_ROOTS_DIFFER")
    if expected_root:
        _failure(failures, not Path(expected_root).is_relative_to(release_root.resolve()),
                 "MUTABLE_STATE_INSIDE_IMMUTABLE_RELEASE")

    dispatcher_env = dispatcher.get("EnvironmentVariables", {})
    effective_path = str(dispatcher_env.get("PATH") or "/usr/bin:/bin:/usr/sbin:/sbin")
    codex = codex_override or contract["executables"]["CHATGPT_PLAN_EXECUTABLE"]
    _failure(failures, "/usr/local/bin" in effective_path.split(":"),
             "CHATGPT_EXECUTABLE_NOT_VISIBLE_TO_DISPATCHER")
    _failure(failures, Path(codex).is_file() and os.access(codex, os.X_OK), "CHATGPT_PLAN_EXECUTABLE_MISSING")
    resolved = shutil.which(Path(codex).name, path=effective_path)
    _failure(failures, resolved == str(Path(codex)), "CHATGPT_EXECUTABLE_NOT_VISIBLE_TO_DISPATCHER")
    python_path = repo_root / contract["executables"]["PYTHON_EXECUTABLE"]
    _failure(failures, python_path.is_file() and os.access(python_path, os.X_OK), "RESEARCH_PYTHON_MISSING")
    for executable in contract["executables"]["REQUIRED_SUBPROCESS_EXECUTABLES"]:
        _failure(failures, Path(executable).is_file() and os.access(executable, os.X_OK),
                 f"RESEARCH_SUBPROCESS_EXECUTABLE_MISSING:{Path(executable).name}")
    failures.extend(_host_failures())
    return list(dict.fromkeys(failures))


def _mcp_rpc(url: str, token: str, method: str, params: dict[str, Any], request_id: int,
             session_id: str | None = None) -> tuple[dict[str, Any], str | None]:
    import urllib.request
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json",
               "Accept": "application/json, text/event-stream"}
    if session_id:
        headers["Mcp-Session-Id"] = session_id
    payload = json.dumps({"jsonrpc": "2.0", "id": request_id, "method": method,
                          "params": params}).encode()
    request = urllib.request.Request(url, payload, headers, method="POST")
    with urllib.request.urlopen(request, timeout=5) as response:
        raw = response.read().decode()
        session_id = response.headers.get("Mcp-Session-Id") or session_id
    if not raw and method.startswith("notifications/"):
        return {}, session_id
    line = next((line[6:] for line in raw.splitlines() if line.startswith("data: ")), raw)
    return json.loads(line), session_id


def _find_key(value: Any, key: str) -> Any:
    if isinstance(value, dict):
        if key in value:
            return value[key]
        for child in value.values():
            found = _find_key(child, key)
            if found is not None:
                return found
    elif isinstance(value, list):
        for child in value:
            found = _find_key(child, key)
            if found is not None:
                return found
    return None


def validate_live(contract: dict[str, Any], repo_root: Path, release_root: Path,
                  mcp_url: str) -> list[str]:
    failures: list[str] = []
    try:
        token_result = subprocess.run(["/usr/bin/security", "find-generic-password", "-s",
            "nexus/credential.nexus.mcp.bridge.v1", "-a", "bridge_token", "-w"],
            capture_output=True, text=True, timeout=3, check=True)
        token = token_result.stdout.strip()
        if not token:
            raise ValueError("empty credential")
    except (OSError, ValueError, subprocess.SubprocessError):
        return ["MCP_AUTHENTICATION_CONTEXT_UNAVAILABLE"]
    try:
        initialized, session = _mcp_rpc(mcp_url, token, "initialize", {
            "protocolVersion": "2025-03-26", "capabilities": {},
            "clientInfo": {"name": "research-runtime-contract-validator", "version": "1"}}, 1)
        if "error" in initialized or not session:
            return ["MCP_INITIALIZE_FAILED"]
        _mcp_rpc(mcp_url, token, "notifications/initialized", {}, 0, session)
        listed, _ = _mcp_rpc(mcp_url, token, "tools/list", {}, 2, session)
        tools = _find_key(listed, "tools")
        if not isinstance(tools, list):
            failures.append("MCP_TOOL_DISCOVERY_FAILED")
        elif "nexus_assign_research" not in {row.get("name") for row in tools if isinstance(row, dict)}:
            failures.append("LIVE_RESEARCH_INTAKE_TOOL_MISSING")
        jobs, _ = _mcp_rpc(mcp_url, token, "tools/call", {"name": "nexus_get_research_queue",
            "arguments": {}}, 3, session)
        queue = _find_key(jobs, "active_case_count")
        if not isinstance(queue, int):
            failures.append("ACTIVE_RESEARCH_CAPACITY_UNVERIFIED")
        elif queue >= int(contract["runtime_gates"]["active_deep_research_case_limit"]):
            failures.append("ACTIVE_RESEARCH_CAPACITY_UNAVAILABLE")
    except Exception:
        failures.append("MCP_LIVE_PREFLIGHT_FAILED")

    wrapper = release_root / "scripts/ops/run_with_canonical_runtime_env.sh"
    python = repo_root / contract["executables"]["PYTHON_EXECUTABLE"]
    probe = """import json\nfrom nexus_agent_platform.resource_spend_governor import default_store\np=default_store().resolve_policy('CHATGPT_PLAN','RESEARCH_ADVISOR','RESEARCH_ROOM_ADVISOR')\nprint(json.dumps({'visible':bool(p),'state':(p or {}).get('state'),'usage':(p or {}).get('autonomous_usage_allowed'),'approval':(p or {}).get('approval_required'),'spend':(p or {}).get('autonomous_spend_allowed')}))\n"""
    try:
        checked = subprocess.run([str(wrapper), str(python), "-c", probe], cwd=release_root,
            capture_output=True, text=True, timeout=8, check=True)
        policy = json.loads(checked.stdout.strip().splitlines()[-1])
        expected = (policy.get("visible") and policy.get("state") == "NORMAL"
                    and policy.get("usage") is True and policy.get("approval") is False
                    and policy.get("spend") is False)
        if not expected:
            failures.append("CHATGPT_PLAN_GOVERNOR_POLICY_UNAVAILABLE_OR_UNAUTHORIZED")
    except (OSError, subprocess.SubprocessError, ValueError, json.JSONDecodeError):
        failures.append("CHATGPT_PLAN_GOVERNOR_POLICY_PROBE_FAILED")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, default=Path("config/research_runtime_contract.v1.json"))
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--release-root", type=Path,
        default=Path.home() / ".nexus/releases/nexus-capability-actions-20261022-r50")
    parser.add_argument("--dispatcher-plist", type=Path,
        default=Path.home() / "Library/LaunchAgents/com.nexus.durable-dispatcher.plist")
    parser.add_argument("--mcp-plist", type=Path,
        default=Path.home() / "Library/LaunchAgents/com.nexus.nexus-mcp-bridge.plist")
    parser.add_argument("--runtime-env", type=Path,
        default=Path.home() / ".config/nexus/runtime.env")
    parser.add_argument("--mcp-url", default="http://127.0.0.1:18765/mcp")
    parser.add_argument("--static-only", action="store_true")
    args = parser.parse_args()
    contract = json.loads(args.contract.read_text(encoding="utf-8"))
    failures = validate_static(contract, repo_root=args.repo_root.resolve(),
        release_root=args.release_root.resolve(), dispatcher_plist=args.dispatcher_plist,
        mcp_plist=args.mcp_plist, runtime_env=args.runtime_env)
    if args.static_only:
        failures.extend(["MCP_LIVE_PROTOCOL_PROBE_REQUIRED", "CHATGPT_PLAN_GOVERNOR_POLICY_PROBE_REQUIRED",
                         "ACTIVE_RESEARCH_CAPACITY_PROBE_REQUIRED"])
    else:
        failures.extend(validate_live(contract, args.repo_root.resolve(), args.release_root.resolve(), args.mcp_url))
    failures = list(dict.fromkeys(failures))
    print("RUNTIME_CONTRACT_VALIDATION=" + ("PASS" if not failures else "FAIL"))
    print("FAILED_CONTRACTS=" + (json.dumps(failures) if failures else "[]"))
    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
