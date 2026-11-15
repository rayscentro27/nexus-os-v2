#!/usr/bin/env python3
"""Nexus REA harness session runner (runs inside the nexus-rea container; stdlib only).

Nexus is authoritative: one Nexus durable job (job_<32 hex>) maps to exactly one REA session
(rea_<24 hex>, deterministic). This runner never creates jobs; it executes one bounded session and
writes request/status/result/tool history under /rea/jobs/<rea_session_id>/ and artifacts under
/rea/artifacts/<rea_session_id>/.

Commands:
  submit            read request JSON on stdin; idempotent per nexus_job_id; prints {rea_session_id,...}
  run <sid>         execute the session (detached by the host wrapper)
  status <sid> | result <sid> | health | cleanup
"""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

VERSION = "nexus-rea-harness-r2"
ROOT = Path(os.environ.get("REA_HARNESS_ROOT", "/rea"))
CONFIG, JOBS, ARTS, WS, TEMP, STATE, LOGS = (ROOT / p for p in ("config", "jobs", "artifacts", "workspace", "temp", "state", "logs"))
HARNESS = CONFIG / "harness"
SLOT_LOCK = STATE / "heavy.lock"
NEXUS_JOB_RE = re.compile(r"^job_[0-9a-f]{32}$")
SID_RE = re.compile(r"^rea_[0-9a-f]{24}$")
MODES = {"TOOL_CERT", "MODEL"}
OUTPUT_CONTRACT = ["OBJECTIVE", "TARGET", "OBSERVED_BEHAVIOR", "WORKFLOWS", "FEATURES", "DATA_FLOW", "INTERFACES",
                   "DEPENDENCIES", "SECURITY_CONSIDERATIONS", "LIMITATIONS", "OPPORTUNITIES", "NEXUS_SPECIFIC_IMPROVEMENTS",
                   "ORIGINAL_IMPLEMENTATION_GUIDANCE", "DEVELOPMENT_DIRECTIVE", "EVIDENCE", "CONFIDENCE"]
OPTION_KEYS = {"tool_profile", "model_mode", "model_key", "fallback_key", "model_profile", "required_context"}
MODEL_PROFILES = {"general_rea", "code_analysis", "deep_reasoning", "long_context", "fast_tool_loop", "coding", "security_analysis"}
MODEL_SWITCH_WAIT_SECONDS = 1800
# A real MODEL analysis must be grounded in evidence it actually gathered. A completion
# with fewer than this many real tool calls is a hallucinated answer (observed: a model
# emitting the full contract with placeholder evidence refs and zero tool calls), so it is
# BLOCKED, never COMPLETED. TOOL_CERT mode is gated separately by its certification checks.
MIN_MODEL_TOOL_CALLS = 2
# Some profiles answer the objective from a single high-evidence tool call: one
# capture_browser_scenario returns the URL, DOM, network events and screenshot inline, so
# requiring a second call would only push the model into wasteful extra tool use.
MIN_TOOL_CALLS_BY_PROFILE = {"rea_web": 1}


def min_tool_calls(tool_profile: str | None) -> int:
    return MIN_TOOL_CALLS_BY_PROFILE.get(tool_profile or "", MIN_MODEL_TOOL_CALLS)


def _target_cwd(target: str, fallback: Path) -> Path:
    """If the target names an existing directory under an allowed REA root, return it so
    OpenCode's cwd-rooted file tools can read it; otherwise return the session workspace.
    Only paths under /rea/repos, /rea/workspace or /rea/temp are honored (never config/secrets)."""
    m = re.match(r"\s*(/[^\s()]+)", str(target or ""))
    if not m:
        return fallback
    try:
        cand = Path(m.group(1)).resolve()
    except (OSError, ValueError):
        return fallback
    allowed = (str((ROOT / "repos").resolve()), str((ROOT / "workspace").resolve()), str((ROOT / "temp").resolve()))
    if cand.is_dir() and any(str(cand) == a or str(cand).startswith(a + os.sep) for a in allowed):
        return cand
    return fallback


def _successful_tool_calls(history: list[dict]) -> int:
    """A tool call is evidence only if it actually succeeded. A rejected or errored call
    (e.g. a disabled `bash` the model attempted) produced nothing and must not count."""
    return sum(1 for h in history if h.get("status") == "completed" and not h.get("error"))


def model_result_status(successful_tool_calls: int, contract: dict | None, missing: list | None,
                        timed_out: bool, total_tool_calls: int | None = None,
                        required: int = MIN_MODEL_TOOL_CALLS) -> tuple[str, dict]:
    """Decide the terminal status of a MODEL session. The evidence gate comes first: an
    analysis with too few *successful* tool calls is BLOCKED (not COMPLETED), so a
    hallucinated answer can never certify. Returns (final_status, evidence_gate_record)."""
    total = successful_tool_calls if total_tool_calls is None else total_tool_calls
    gate = {"successful_tool_calls": successful_tool_calls, "total_tool_calls": total,
            "required": required}
    if successful_tool_calls < required:
        return "BLOCKED", {**gate, "pass": False, "reason": "INSUFFICIENT_TOOL_EVIDENCE"}
    gate["pass"] = True
    if contract and not missing and not timed_out:
        return "COMPLETED", gate
    if contract:
        return "COMPLETED_WITH_LIMITATIONS", gate
    return "FAILED", gate
TERMINAL = {"COMPLETED", "COMPLETED_WITH_LIMITATIONS", "FAILED", "BLOCKED", "WAITING_FOR_MODEL_ENDPOINT", "CANCELLED"}

# Resource protection (Postiz + n8n share this host). The container cgroup is the hard cap; these are admission checks.
LIMITS = {
    "max_concurrent_heavy_sessions": 1,
    "slot_wait_seconds": 900,
    "min_host_mem_available_mb": 1200,
    "min_disk_free_gb": 15,
    "max_workspace_gb": 20,
    "max_artifacts_gb": 10,
    "session_timeout_seconds": {"TOOL_CERT": 900, "MODEL": 2700},
    "temp_retention_hours": 24,
    "workspace_retention_days": 7,
    "max_result_bytes": 262144,
    "max_tool_output_bytes_in_history": 4096,
}
SECRET_PATTERNS = [re.compile(p) for p in (
    r"(?i)\b(api[_-]?key|authorization|bearer|access[_-]?token|refresh[_-]?token|secret|password|cookie)\b\s*[:=]\s*[\"']?[^\s\"',}]{6,}",
    r"\bsk-[A-Za-z0-9_-]{16,}", r"\bhf_[A-Za-z0-9]{16,}", r"\bgh[pousr]_[A-Za-z0-9]{20,}", r"\beyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}")]


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sid_for(nexus_job_id: str) -> str:
    return "rea_" + hashlib.sha256(("nexus-rea:" + nexus_job_id).encode()).hexdigest()[:24]


def redact(text: str) -> str:
    for pat in SECRET_PATTERNS:
        text = pat.sub("[REDACTED]", text)
    return text


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + f".tmp{os.getpid()}")
    tmp.write_text(json.dumps(obj, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def read_json(path: Path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def update_status(sid: str, **fields) -> dict:
    path = JOBS / sid / "status.json"
    cur = read_json(path, {}) or {}
    cur.update(fields)
    cur["updated_at"] = now()
    write_json(path, cur)
    return cur


def dir_gb(path: Path) -> float:
    total = 0
    for p in path.rglob("*"):
        try:
            if p.is_file() and not p.is_symlink():
                total += p.stat().st_size
        except OSError:
            pass
    return total / 1e9


def resources() -> dict:
    mem = {}
    for line in Path("/proc/meminfo").read_text().splitlines():
        k, v = line.split(":", 1)
        mem[k] = int(v.split()[0]) // 1024
    du = shutil.disk_usage(str(ROOT))
    cg = {}
    for name in ("memory.max", "memory.current", "cpu.max", "pids.max"):
        try:
            cg[name] = Path("/sys/fs/cgroup", name).read_text().strip()
        except OSError:
            pass
    try:
        load1 = os.getloadavg()[0]
    except OSError:
        load1 = None
    return {"host_mem_available_mb": mem.get("MemAvailable"), "host_mem_total_mb": mem.get("MemTotal"),
            "disk_free_gb": round(du.free / 1e9, 1), "disk_total_gb": round(du.total / 1e9, 1),
            "load1": load1, "cgroup": cg}


def admission() -> tuple[bool, str | None, dict]:
    res = resources()
    if (res["host_mem_available_mb"] or 0) < LIMITS["min_host_mem_available_mb"]:
        return False, "HOST_MEMORY_LOW", res
    if res["disk_free_gb"] < LIMITS["min_disk_free_gb"]:
        return False, "DISK_FREE_LOW", res
    ws = dir_gb(WS)
    res["workspace_gb"] = round(ws, 2)
    if ws > LIMITS["max_workspace_gb"]:
        return False, "WORKSPACE_QUOTA_EXCEEDED", res
    arts = dir_gb(ARTS)
    res["artifacts_gb"] = round(arts, 2)
    if arts > LIMITS["max_artifacts_gb"]:
        return False, "ARTIFACT_QUOTA_EXCEEDED", res
    return True, None, res


# ---------------------------------------------------------------- provider abstraction

def provider() -> dict:
    return read_json(CONFIG / "model_provider.json", {}) or {}


def provider_ready(p: dict) -> tuple[bool, str]:
    if str(p.get("status") or "") != "READY":
        return False, str(p.get("status") or "PROVIDER_NOT_CONFIGURED")
    for key in ("base_url", "model_name", "context_length", "output_limit"):
        if not p.get(key):
            return False, "PROVIDER_FIELD_MISSING:" + key
    if p.get("tool_calling") is not True:
        return False, "PROVIDER_TOOL_CALLING_UNVERIFIED"
    cost = str(p.get("cost_class") or "UNSET").upper()
    if cost not in {"FREE", "INCLUDED", "PAID"}:
        return False, "PROVIDER_COST_CLASS_UNSET"
    if cost == "PAID" and not p.get("cost_approval_ref"):
        return False, "COST_GOVERNOR_APPROVAL_REQUIRED"
    return True, "READY"


def tool_profiles() -> dict:
    return read_json(HARNESS / "tool_profiles.json", {}) or {}


def apply_tool_profile(tpl: dict, profile: str | None) -> str:
    """Deterministic tool profile: the full 213-tool catalog (~70-80K tokens) cannot fit a 32K model context."""
    prof = tool_profiles()
    name = profile or prof.get("default") or "rea_general"
    entries = (prof.get("profiles") or {}).get(name)
    if entries is None:
        raise ValueError("TOOL_PROFILE_UNKNOWN")
    if entries == "__ALL__":
        return name
    tools = tpl["agent"]["rea"].setdefault("tools", {})
    tools["rea_*"] = False
    tools.update(prof.get("always") or {})
    for tool in entries:
        tools["rea_" + tool] = True
    # Per-profile overrides of the shared `always` set (e.g. rea_web has no local files, so
    # read/glob/grep are off — a model otherwise loops on reading a returned evidence_id).
    tools.update((prof.get("profile_always") or {}).get(name) or {})
    # rea_web runs one capture against a Nexus-owned loopback fixture in the sealed container
    # (no egress but the model endpoint, read-only config/fixtures). Allow bash there so a stray
    # bash the model emits returns an error instead of a permission rejection, which otherwise
    # ends the OpenCode run before the model writes its final contract.
    if name == "rea_web":
        tpl["agent"]["rea"].setdefault("permission", {})["bash"] = "allow"
    return name


def render_config(sid: str, base_url: str, model_name: str, context: int, output: int, tool_profile: str | None = None) -> Path:
    tpl = json.loads((CONFIG / "opencode.template.json").read_text(encoding="utf-8"))
    if tool_profile is not None or (HARNESS / "tool_profiles.json").exists():
        apply_tool_profile(tpl, tool_profile)
    prov = tpl["provider"]["nexus_rea_model"]
    prov["options"]["baseURL"] = base_url
    model = prov["models"]["rea-default"]
    model["id"] = model_name
    model["limit"] = {"context": int(context), "output": int(output)}
    path = TEMP / sid / "opencode" / "opencode.json"
    write_json(path, tpl)
    return path


def _model_api(p: dict, key: str, method: str, path: str, body: dict | None = None, timeout: int = 30) -> tuple[int, dict]:
    import urllib.error
    import urllib.request
    root = str(p["base_url"]).rstrip("/").removesuffix("/v1")
    req = urllib.request.Request(root + path, method=method, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Authorization": "Bearer " + key, "Content-Type": "application/json",
                                          # Named UA required: the provider sits behind Cloudflare, whose Bot Fight Mode
                                          # rejects urllib's default "Python-urllib/*" UA with 403 error 1010. The session
                                          # chat path (OpenCode/undici) is unaffected; this covers only the model-step preflight.
                                          "User-Agent": "nexus-rea-harness/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as exc:
        try:
            return exc.code, json.loads(exc.read() or b"{}")
        except ValueError:
            return exc.code, {}


def ensure_model(sid: str, p: dict, key: str, options: dict) -> dict:
    """Pre-session model step: request the assignment's model (or default) and wait, bounded, until READY.
    Returns {ok, state, reason, retryable}. Never loads anything itself (Kaggle does) and never uses paid providers."""
    sel = p.get("default_selection") or {}
    body = {"mode": options.get("model_mode") or sel.get("mode") or "manual",
            "model_key": options.get("model_key") or sel.get("model_key"),
            "fallback_key": options.get("fallback_key") or sel.get("fallback_key"),
            "profile": options.get("model_profile") or sel.get("profile") or "general_rea"}
    if options.get("required_context"):
        body["required_context"] = int(options["required_context"])
    try:
        code, out = _model_api(p, key, "POST", "/nexus/v1/model", body)
    except OSError as exc:
        return {"ok": False, "reason": "MODEL_ENDPOINT_UNREACHABLE:" + type(exc).__name__, "retryable": True}
    if code in (401, 403):
        return {"ok": False, "reason": "MODEL_ENDPOINT_AUTH_FAILED", "retryable": False}
    if code == 400:
        return {"ok": False, "reason": "MODEL_SELECTION_INVALID:" + str((out.get("error") or {}).get("message"))[:120], "retryable": False}
    if code == 409 and not out.get("accepted", True) and (out.get("decision") or {}).get("status") == "NO_MODEL_FITS":
        return {"ok": False, "reason": "MODEL_SELECTION_REJECTED_DOES_NOT_FIT", "retryable": False, "decision": out.get("decision")}
    if code not in (200, 202, 409):
        return {"ok": False, "reason": f"MODEL_ENDPOINT_HTTP_{code}", "retryable": True}
    decision = out.get("decision") or {}
    update_status(sid, model_step={"decision": decision, "already_loaded": out.get("already_loaded")})
    deadline = time.time() + MODEL_SWITCH_WAIT_SECONDS
    while time.time() < deadline:
        try:
            code, st = _model_api(p, key, "GET", "/nexus/v1/model")
        except OSError:
            code, st = 0, {}
        state = (st or {}).get("state") or {}
        if code == 200 and state.get("status") == "READY" and (not decision.get("selected") or state.get("model_key") in
                                                               {decision.get("selected"), decision.get("fallback")}):
            return {"ok": True, "state": state, "decision": decision}
        if code == 200 and state.get("status") == "PAUSED":
            return {"ok": False, "reason": "MODEL_STEP_PAUSED:" + str(state.get("reason")), "retryable": True, "state": state}
        time.sleep(10)
    return {"ok": False, "reason": "MODEL_SWITCH_WAIT_TIMEOUT", "retryable": True}


# ---------------------------------------------------------------- helpers for the session

def _free_port(preferred: int) -> int:
    with socket.socket() as s:
        try:
            s.bind(("127.0.0.1", preferred))
            return preferred
        except OSError:
            s.bind(("127.0.0.1", 0))
            return s.getsockname()[1]


def _wait_port(port: int, timeout: float = 15) -> bool:
    end = time.time() + timeout
    while time.time() < end:
        with socket.socket() as s:
            s.settimeout(0.5)
            if s.connect_ex(("127.0.0.1", port)) == 0:
                return True
        time.sleep(0.2)
    return False


def _chromium() -> str:
    hits = sorted(Path("/opt/ms-playwright").glob("chromium-*/chrome-linux*/chrome"))
    if not hits:
        raise RuntimeError("CHROMIUM_NOT_INSTALLED")
    return str(hits[-1])


def _heartbeat(sid: str, stop: threading.Event) -> None:
    while not stop.wait(20):
        update_status(sid, heartbeat_at=now())


def _events_from_stdout(lines: list[str]) -> tuple[list[dict], str | None]:
    events, session = [], None
    for line in lines:
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        events.append(ev)
        session = session or ev.get("sessionID") or (ev.get("part") or {}).get("sessionID") or (ev.get("properties") or {}).get("sessionID")
    return events, session


def _tool_history(export: dict) -> tuple[list[dict], str]:
    """Flatten an `opencode export` document into tool history + final assistant text."""
    history, final_text = [], ""
    for msg in export.get("messages") or []:
        info = msg.get("info") or {}
        for part in msg.get("parts") or []:
            if part.get("type") == "tool":
                st = part.get("state") or {}
                out = st.get("output")
                out = out if isinstance(out, str) else json.dumps(out, default=str)
                history.append({"tool": part.get("tool"), "call_id": part.get("callID"), "status": st.get("status"),
                                "input": st.get("input"), "output_bytes": len(out or ""),
                                "output_sha256": hashlib.sha256((out or "").encode()).hexdigest()[:16],
                                "output_head": redact((out or "")[:LIMITS["max_tool_output_bytes_in_history"]]),
                                "error": st.get("error"), "time": st.get("time")})
            elif part.get("type") == "text" and info.get("role") == "assistant" and part.get("text"):
                final_text = part["text"]
    return history, final_text


def _parse_contract(text: str) -> tuple[dict | None, list[str]]:
    candidates = [text] + re.findall(r"\{.*\}", text, re.S)
    for cand in candidates:
        try:
            obj = json.loads(cand)
        except ValueError:
            continue
        if isinstance(obj, dict):
            return obj, [k for k in OUTPUT_CONTRACT if k not in obj]
    return None, list(OUTPUT_CONTRACT)


def _run_opencode(sid: str, cfg: Path, prompt: str, cwd: Path, env_extra: dict, timeout: int) -> dict:
    env = {**os.environ, "OPENCODE_CONFIG": str(cfg), "OPENCODE_DISABLE_AUTOUPDATE": "true",
           "OPENCODE_DISABLE_SHARE": "true", **env_extra}
    cmd = ["opencode", "run", "--agent", "rea", "--model", "nexus_rea_model/rea-default", "--format", "json", prompt]
    started = time.monotonic()
    proc = subprocess.Popen(cmd, cwd=str(cwd), env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                            start_new_session=True)
    try:
        out, err = proc.communicate(timeout=timeout)
        timed_out = False
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGTERM)
        try:
            out, err = proc.communicate(timeout=20)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            out, err = proc.communicate()
        timed_out = True
    lines = (out or "").splitlines()
    (JOBS / sid / "opencode_events.jsonl").write_text(redact("\n".join(lines)) + "\n", encoding="utf-8")
    (LOGS / f"{sid}.opencode.stderr.log").write_text(redact((err or "")[-200000:]), encoding="utf-8")
    events, session = _events_from_stdout(lines)
    export = {}
    if session:
        exp = subprocess.run(["opencode", "export", session], cwd=str(cwd), env=env, capture_output=True, text=True, timeout=120)
        try:
            export = json.loads(exp.stdout[exp.stdout.find("{"):]) if "{" in exp.stdout else {}
        except ValueError:
            export = {}
        if export:
            (ARTS / sid / "opencode_session_export.json").write_text(redact(json.dumps(export, indent=1, default=str)), encoding="utf-8")
    return {"returncode": proc.returncode, "timed_out": timed_out, "elapsed_seconds": round(time.monotonic() - started, 1),
            "harness_session_id": session, "event_count": len(events), "export": export, "stderr_tail": redact((err or "")[-1500:])}


def _save_inline_pngs(sid: str, history_src: dict) -> list[str]:
    """Persist base64 PNGs returned inline by REA tools (screenshots) as artifacts."""
    saved = []
    blob = json.dumps(history_src, default=str)
    for i, m in enumerate(re.finditer(r"iVBORw0KGgo[A-Za-z0-9+/=]{200,}", blob)):
        import base64
        try:
            data = base64.b64decode(m.group(0) + "=" * (-len(m.group(0)) % 4))
        except ValueError:
            continue
        path = ARTS / sid / f"screenshot_{i}.png"
        path.write_bytes(data)
        saved.append(str(path))
        if i >= 4:
            break
    return saved


def _browser_screenshot(sid: str, url: str) -> str | None:
    """Capture a PNG of the (loopback fixture) page as a saved artifact, via the proven REA
    browser tool (not raw chrome, which hangs offline), and WITHOUT routing the ~25 KB base64
    image through the model. Bounded and best-effort; failure is non-fatal."""
    import base64
    scenario = {
        "browser": {"mode": "launch", "executable_path": _chromium(), "headless": True},
        "start_url": {"url": url},
        "actions": [
            {"step_id": "open", "action": "goto", "destination": {"url": url}, "wait_until": "load", "timeout_ms": 20000},
            {"step_id": "settle", "action": "wait_for_timeout", "duration_ms": 500},
        ],
        "capture": {"at_end": ["screenshot"]},
    }
    try:
        proc = subprocess.run(["rea", "capture-browser-scenario", json.dumps(scenario), "--format", "json", "--full-output"],
                              capture_output=True, text=True, timeout=120,
                              env={**os.environ, "REA_MCP_INPUT_SCHEMA_PROFILE": "compact"})
    except (subprocess.TimeoutExpired, OSError, RuntimeError):
        return None
    m = re.search(r"iVBORw0KGgo[A-Za-z0-9+/=]{200,}", proc.stdout or "")
    if not m:
        return None
    try:
        data = base64.b64decode(m.group(0) + "=" * (-len(m.group(0)) % 4))
    except ValueError:
        return None
    out = ARTS / sid / "screenshot_0.png"
    out.write_bytes(data)
    return str(out)


# ---------------------------------------------------------------- modes

def _prepare_cert_fixtures(sid: str) -> dict:
    tmp = TEMP / sid
    repo = tmp / "repo"
    if repo.exists():
        shutil.rmtree(repo)
    shutil.copytree(ROOT / "fixtures" / "repo", repo)
    git = ["git", "-c", "user.name=nexus-rea", "-c", "user.email=rea@nexus.invalid", "-c", "init.defaultBranch=main"]
    subprocess.run(git + ["init", "-q"], cwd=repo, check=True)
    subprocess.run(git + ["add", "."], cwd=repo, check=True)
    subprocess.run(git + ["commit", "-qm", "fixture"], cwd=repo, check=True)
    web = tmp / "web"
    if web.exists():
        shutil.rmtree(web)
    shutil.copytree(ROOT / "fixtures" / "web", web)
    (tmp / "bin").mkdir(parents=True, exist_ok=True)
    shutil.copy2("/usr/bin/true", tmp / "bin" / "true")   # GNU coreutils (GPL, open source)
    return {"repo": str(repo), "web": str(web), "binary": str(tmp / "bin" / "true"),
            "binary_sha256": hashlib.sha256((tmp / "bin" / "true").read_bytes()).hexdigest()}


def _cert_checks(sid: str, history: list[dict], stub_log: list[dict], fixtures: dict, run: dict, contract: dict | None) -> dict:
    by_tool = {}
    for h in history:
        by_tool.setdefault(h["tool"], []).append(h)

    def ok(tool: str, needle: str | None = None) -> bool:
        rows = by_tool.get(tool) or []
        good = [r for r in rows if r["status"] == "completed" and not r.get("error")]
        return bool(good) and (needle is None or any(needle in (r.get("output_head") or "") for r in good))

    lists = [e["rea_tools"] for e in stub_log if isinstance(e.get("rea_tools"), list)]
    advertised = max(lists, key=len) if lists else []
    export_path = ARTS / sid / "opencode_session_export.json"
    checks = {
        "OPENCODE_DISCOVERS_REA_MCP": {"pass": len(advertised) >= 50, "advertised_rea_tools": len(advertised)},
        "REA_READS_TEST_REPO": {"pass": ok("read", "nexus-rea-cert-fixture") and ok("rea_analyze_javascript_application")},
        "REA_BROWSER_INSPECTION": {"pass": ok("rea_capture_browser_scenario")},
        "REA_GHIDRA_SMALL_BINARY": {"pass": ok("rea_open_binary") and ok("rea_binary_overview") and ok("rea_list_procedures"),
                                    "binary": "GNU coreutils true", "binary_sha256": fixtures["binary_sha256"]},
        "OUTPUTS_RETURNED_TO_OPENCODE": {"pass": bool(contract) and len(contract.get("EVIDENCE") or []) >= 6 and
                                         all(e.get("supports", {}).get("bytes", 0) > 0 for e in contract.get("EVIDENCE") or [])},
        "SESSION_ARTIFACTS_SAVED": {"pass": export_path.is_file() and (JOBS / sid / "opencode_events.jsonl").is_file(),
                                    "export": str(export_path)},
    }
    # Browser: read the complete tool output from the session export (history keeps only a head).
    full = [p["state"].get("output") for m in (run["export"].get("messages") or []) for p in (m.get("parts") or [])
            if p.get("type") == "tool" and p.get("tool") == "rea_capture_browser_scenario" and isinstance(p.get("state"), dict)]
    steps_ok = dom = net = False
    shot = False
    rea_completeness, dropped = None, None
    for out in full:
        try:
            norm = json.loads(out).get("normalized_result") or {}
        except (TypeError, ValueError):
            continue
        steps = norm.get("steps") or []
        steps_ok = bool(steps) and all(st.get("status") == "completed" for st in steps)
        rea_completeness = norm.get("completeness")
        dropped = ((norm.get("events") or {}).get("dropped"))
        net = "/api/catalog.json" in out
        dom = "REA Fixture Catalog" in out
        shot = '"screenshot"' in out and '"state":"missing"' not in out.replace(" ", "")
    screenshots = sorted(str(p) for p in (ARTS / sid).glob("screenshot_*.png"))
    checks["REA_BROWSER_INSPECTION"] = {
        "pass": ok("rea_capture_browser_scenario") and steps_ok and dom and net and bool(screenshots) and dropped == 0,
        "all_steps_completed": steps_ok, "events_dropped": dropped, "rea_completeness": rea_completeness, "dom_captured": dom,
        "network_observed": net, "screenshot_returned": shot, "screenshots_saved": screenshots}
    return checks


def run_session(sid: str) -> int:
    req = read_json(JOBS / sid / "request.json")
    if not req:
        return 2
    mode = req["mode"]
    (ARTS / sid).mkdir(parents=True, exist_ok=True)
    (TEMP / sid).mkdir(parents=True, exist_ok=True)
    update_status(sid, status="QUEUED_WAITING_FOR_SLOT", runner_pid=os.getpid())
    SLOT_LOCK.parent.mkdir(parents=True, exist_ok=True)
    lock = open(SLOT_LOCK, "a+")
    deadline = time.time() + LIMITS["slot_wait_seconds"]
    while True:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            break
        except BlockingIOError:
            if time.time() > deadline:
                update_status(sid, status="FAILED", reason="REA_SLOT_WAIT_TIMEOUT", retryable=True)
                return 3
            time.sleep(5)
    admitted, reason, res = admission()
    if not admitted:
        update_status(sid, status="FAILED", reason="RESOURCE_ADMISSION_" + reason, retryable=True, resources=res)
        return 3
    stop = threading.Event()
    threading.Thread(target=_heartbeat, args=(sid, stop), daemon=True).start()
    update_status(sid, status="RUNNING", started_at=now(), resources_at_start=res)
    helpers: list[subprocess.Popen] = []
    try:
        timeout = LIMITS["session_timeout_seconds"][mode]
        if mode == "MODEL":
            p = provider()
            ready, why = provider_ready(p)
            if not ready:
                update_status(sid, status="WAITING_FOR_MODEL_ENDPOINT", reason=why, provider=p.get("provider"))
                write_json(JOBS / sid / "result.json", {"rea_session_id": sid, "nexus_job_id": req["nexus_job_id"],
                                                         "status": "WAITING_FOR_MODEL_ENDPOINT", "reason": why})
                return 0
            key = ""
            key_ref = Path(str(p.get("api_key_ref") or "/nonexistent"))
            if key_ref.is_file():
                key = key_ref.read_text(encoding="utf-8").strip()
            options = req.get("options") or {}
            step = ensure_model(sid, p, key, options)
            if not step["ok"]:
                update_status(sid, status="FAILED", reason=step["reason"], retryable=step["retryable"], model_step=step)
                return 3
            served = step["state"]
            context = min(int(p["context_length"]), int(served.get("context") or p["context_length"]))
            cfg = render_config(sid, p["base_url"], p["model_name"], context, p["output_limit"], options.get("tool_profile"))
            work = WS / sid
            work.mkdir(parents=True, exist_ok=True)
            # OpenCode's built-in read/glob/grep tools are rooted at the run cwd. If the target
            # names an existing directory (repo mode), run there so those tools can read it;
            # the rea_* MCP tools take absolute paths and work regardless of cwd. For URL/binary
            # targets there is no such directory, so we stay in the per-session workspace.
            cwd = _target_cwd(req["target"], work)
            # Browser fixture: if the target is a loopback URL, serve the Nexus-owned web fixture
            # on that port for the session (MODEL mode has no cert helpers of its own). Only the
            # harness's own fixture content is ever served, and only on 127.0.0.1/localhost.
            murl = re.search(r"https?://(?:127\.0\.0\.1|localhost):(\d+)", req["target"] or "")
            web_fixture = ROOT / "fixtures" / "web"
            browser_link = None
            if murl and web_fixture.is_dir():
                fport = int(murl.group(1))
                helpers.append(subprocess.Popen(
                    [sys.executable, "-m", "http.server", str(fport), "--bind", "127.0.0.1",
                     "--directory", str(web_fixture)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
                if not _wait_port(fport):
                    raise RuntimeError("FIXTURE_SERVER_DID_NOT_START")
                # Stable, digit-free symlink to the browser so the model copies one short path
                # (models unreliably retype the chromium-<version> directory and the launch fails).
                browser_link = TEMP / "chrome"   # sid-free, short; heavy sessions are serialized (max 1)
                try:
                    browser_link.unlink()
                except FileNotFoundError:
                    pass
                browser_link.symlink_to(_chromium())
            # The exact, known-good capture scenario for the fixture (selectors match /rea/fixtures/web).
            # Models reliably launch and schema-match the browser tool only when handed the whole call, so
            # the harness supplies it; the model still drives the loop and writes the analysis from the result.
            browser_scenario_json = None
            if murl and browser_link:
                _url = murl.group(0) + "/"
                browser_scenario_json = json.dumps({
                    "browser": {"mode": "launch", "executable_path": str(browser_link), "headless": True},
                    "start_url": {"url": _url},
                    "actions": [
                        {"step_id": "open", "action": "goto", "destination": {"url": _url}, "wait_until": "load", "timeout_ms": 20000},
                        {"step_id": "items", "action": "wait_for", "locator": {"kind": "css", "selector": "li[data-sku=\"MUG-11OZ\"]"}, "state": "visible", "timeout_ms": 10000},
                        {"step_id": "refresh", "action": "click", "locator": {"kind": "role", "role": "button", "name": "Refresh catalog"}, "timeout_ms": 10000},
                        {"step_id": "settle", "action": "wait_for_timeout", "duration_ms": 500},
                    ],
                    # No screenshot here: a full-page PNG is ~25 KB of base64 that would swamp a
                    # 32K-context model and derail its analysis. The harness captures the screenshot
                    # separately (binary evidence is not fed to the text model).
                    "capture": {"at_end": ["url", "dom"], "events": ["network", "console"],
                                "network": {"request_body": False, "response_body": True, "header_values": False}},
                }, separators=(",", ":"))
            # Binary job: hand the model the exact stateful tool order and argument shapes. The
            # compact MCP schema hides these, and a model otherwise calls overview before open,
            # guesses open_binary args, or tries to `read` the binary bytes.
            binary_steps = None
            mbin = re.match(r"\s*(/[^\s()]+)", req["target"] or "")
            if options.get("tool_profile") == "rea_binary" and mbin and Path(mbin.group(1)).is_file():
                _bp = mbin.group(1)
                binary_steps = (
                    "1) rea_open_binary {\"path\":\"" + _bp + "\",\"provider_id\":\"ghidra\"}\n"
                    "2) rea_binary_overview {}\n"
                    "3) rea_list_procedures {\"detail\":\"summary\"}\n"
                    "4) rea_list_strings {\"detail\":\"summary\"}\n"
                    "5) rea_close_binary {}\n")
            prompt = (
                f"NEXUS_JOB_ID={req['nexus_job_id']}\nREA_SESSION_ID={sid}\nTARGET={req['target']}\n"
                f"OBJECTIVE={req['objective']}\n"
                f"Work only under {work} and {ROOT / 'repos'}. Follow the REA harness instructions.\n"
                "MANDATORY PROCEDURE — do this before writing anything else:\n"
                "1. FIRST, call a tool to inspect the target, then keep using tools. For a repository use "
                "`list`/`glob`/`read`; for a URL or a binary use the matching `rea_*` tool. The `bash` tool "
                "is disabled. Do not describe the target before a tool has shown it to you.\n"
                "2. Work the loop one tool per step until the objective is answered.\n"
                "3. You may NOT emit the final JSON contract until you have made at least two SUCCESSFUL "
                "tool calls whose results you cite. Every EVIDENCE.evidence_ref must be a real Evidence ID "
                "from a tool you called this session — never a placeholder or example id.\n"
                "4. If something is absent (e.g. no authentication code), state that explicitly from what the "
                "tools showed; do not guess with words like \"likely\" or \"typical\".\n"
                f"Your tools' working directory is {cwd}; built-in read/glob/grep resolve paths "
                f"there, and rea_* tools accept absolute paths.\n"
                + (
                    "BROWSER JOB — STRICT: Call `rea_capture_browser_scenario` EXACTLY ONCE, passing this "
                    "input object VERBATIM (it has the correct executable symlink, selectors and network "
                    "capture already):\n" + browser_scenario_json + "\n"
                    "Its single result contains the final URL, the DOM, and the network and console events — "
                    "that IS your evidence (the screenshot is captured separately by the harness, so you do not "
                    "request it). The instant that one call returns, STOP: make NO more tool calls (do not call "
                    "it again, do not `read` the returned evidence_id — it is a reference, not a file, never call "
                    "bash) and write the final JSON contract from that result, citing its evidence_id. Report the "
                    "page structure, the user flow, the catalog.json request and its response, and that no events "
                    "were dropped.\n"
                    if (options.get("tool_profile") == "rea_web" and browser_scenario_json) else ""
                )
                + (
                    "BINARY JOB — STRICT: Make these stateful tool calls in EXACTLY this order, one per "
                    "step, and never call a binary tool before rea_open_binary or `read` the binary bytes:\n"
                    + binary_steps +
                    "Open gives the format, architecture and entry point; overview and list_procedures give "
                    "the procedures; list_strings gives notable strings (look there for how the exit status / "
                    "return code is set). After rea_close_binary, STOP making tool calls and write the final "
                    "JSON contract from these results, citing each tool's evidence_id.\n"
                    if (options.get("tool_profile") == "rea_binary" and binary_steps) else ""
                )
                + "Begin now by calling the first tool.")
            run = _run_opencode(sid, cfg, prompt, cwd, {"NEXUS_REA_MODEL_API_KEY": key, "NEXUS_REA_SESSION_ID": sid}, timeout)
            provider_mode = "NEXUS_REA_MODEL"
            # Binary evidence (screenshot) is captured by the harness, not the text model: the
            # fixture server is still up here, so grab a PNG of the page as a saved artifact.
            if murl and browser_link:
                _browser_screenshot(sid, murl.group(0) + "/")
            fixtures, stub_log = {}, []
            model_info = {"served_model_key": served.get("model_key"), "served_model_id": served.get("model_id"),
                          "context": context, "selection": served.get("selection"), "fallback_used": served.get("fallback_used"),
                          "tool_profile": options.get("tool_profile") or tool_profiles().get("default")}
        else:
            fixtures = _prepare_cert_fixtures(sid)
            web_port = _free_port(18798)
            stub_port = _free_port(18799)
            helpers.append(subprocess.Popen([sys.executable, "-m", "http.server", str(web_port), "--bind", "127.0.0.1",
                                             "--directory", fixtures["web"]], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
            stub_env = {**os.environ, "REA_STUB_PORT": str(stub_port), "REA_SESSION_TEMP": str(TEMP / sid),
                        "REA_FIXTURE_PORT": str(web_port), "REA_CHROMIUM_PATH": _chromium()}
            helpers.append(subprocess.Popen([sys.executable, str(HARNESS / "scripted_cert_model.py")], env=stub_env,
                                            stdout=subprocess.DEVNULL, stderr=open(LOGS / f"{sid}.stub.log", "w")))
            if not (_wait_port(web_port) and _wait_port(stub_port)):
                raise RuntimeError("CERT_HELPERS_DID_NOT_START")
            cfg = render_config(sid, f"http://127.0.0.1:{stub_port}/v1", "scripted-certification-stub", 32768, 4096, "rea_full")
            model_info = {"served_model_key": "scripted-certification-stub", "tool_profile": "rea_full"}
            prompt = f"REA tool-layer certification for NEXUS_JOB_ID={req['nexus_job_id']} REA_SESSION_ID={sid}."
            run = _run_opencode(sid, cfg, prompt, TEMP / sid, {"NEXUS_REA_MODEL_API_KEY": "certification-stub-no-key",
                                                                "NEXUS_REA_SESSION_ID": sid}, timeout)
            provider_mode = "SCRIPTED_CERTIFICATION_STUB"
            stub_log = [json.loads(l) for l in (TEMP / sid / "stub_log.jsonl").read_text().splitlines()] \
                if (TEMP / sid / "stub_log.jsonl").is_file() else []
        history, final_text = _tool_history(run["export"])
        with (JOBS / sid / "tool_history.jsonl").open("w", encoding="utf-8") as fh:
            for row in history:
                fh.write(json.dumps(row, default=str) + "\n")
        _save_inline_pngs(sid, run["export"])
        # All PNGs for this session: inline ones the model's capture returned (if any) plus any the
        # harness captured directly. Globbing covers both sources.
        screenshots = sorted(str(p) for p in (ARTS / sid).glob("screenshot_*.png"))
        contract, missing = _parse_contract(final_text)
        result = {"schema_version": "nexus.rea-result.v1", "harness_version": VERSION, "rea_session_id": sid,
                  "nexus_job_id": req["nexus_job_id"], "harness_session_id": run["harness_session_id"],
                  "target": req["target"], "objective": req["objective"], "mode": mode, "provider_mode": provider_mode,
                  "created_at": req["created_at"], "started_at": (read_json(JOBS / sid / "status.json", {}) or {}).get("started_at"),
                  "completed_at": now(), "elapsed_seconds": run["elapsed_seconds"], "opencode_returncode": run["returncode"],
                  "timed_out": run["timed_out"], "tool_call_count": len(history),
                  "tools_used": sorted({h["tool"] for h in history}), "artifacts": {
                      "session_export": str(ARTS / sid / "opencode_session_export.json"),
                      "events": str(JOBS / sid / "opencode_events.jsonl"),
                      "tool_history": str(JOBS / sid / "tool_history.jsonl"), "screenshots": screenshots},
                  "contract": contract, "contract_missing_keys": missing, "resources_at_end": resources(), "model": model_info,
                  "cost": {"paid_cost_usd": 0, "external_paid_calls": 0, "provider_cost_class":
                           "NONE_LOCAL_STUB" if mode == "TOOL_CERT" else provider().get("cost_class")}}
        if mode == "TOOL_CERT":
            checks = _cert_checks(sid, history, stub_log, fixtures, run, contract)
            result["certification_checks"] = checks
            passed = all(c["pass"] for c in checks.values()) and not run["timed_out"]
            result["harness_tool_layer"] = "PASS" if passed else "FAIL"
            final = "COMPLETED" if passed else "FAILED"
        else:
            final, result["evidence_gate"] = model_result_status(
                _successful_tool_calls(history), contract, missing, run["timed_out"],
                total_tool_calls=len(history), required=min_tool_calls(model_info.get("tool_profile")))
        raw = json.dumps(result, default=str)
        if len(raw) > LIMITS["max_result_bytes"]:
            result["contract"] = {"TRUNCATED": True, "missing": missing}
            raw = json.dumps(result, default=str)
        write_json(JOBS / sid / "result.json", json.loads(redact(raw)))
        if final.startswith("COMPLETED"):
            final_reason = None
        elif final == "BLOCKED":
            final_reason = "INSUFFICIENT_TOOL_EVIDENCE"
        elif run["timed_out"]:
            final_reason = "OPENCODE_TIMEOUT"
        else:
            final_reason = "RESULT_INVALID"
        update_status(sid, status=final, completed_at=now(), harness_session_id=run["harness_session_id"],
                      reason=final_reason, retryable=(final == "BLOCKED"))
        return 0
    except Exception as exc:  # never leak secrets in status
        update_status(sid, status="FAILED", reason=type(exc).__name__ + ":" + redact(str(exc))[:300], retryable=True)
        return 1
    finally:
        stop.set()
        for h in helpers:
            h.terminate()
        fcntl.flock(lock, fcntl.LOCK_UN)


# ---------------------------------------------------------------- commands

def submit(raw: dict) -> dict:
    nexus_job_id = str(raw.get("nexus_job_id") or "")
    if not NEXUS_JOB_RE.fullmatch(nexus_job_id):
        raise ValueError("NEXUS_JOB_ID_INVALID")
    mode = str(raw.get("mode") or "MODEL").upper()
    if mode not in MODES:
        raise ValueError("MODE_INVALID")
    objective = " ".join(str(raw.get("objective") or "").split())[:4000]
    target = " ".join(str(raw.get("target") or "").split())[:1000]
    if not objective or not target:
        raise ValueError("OBJECTIVE_AND_TARGET_REQUIRED")
    sid = sid_for(nexus_job_id)
    req_path = JOBS / sid / "request.json"
    existing = read_json(req_path)
    if existing:
        if existing.get("nexus_job_id") != nexus_job_id:
            raise ValueError("REA_SESSION_COLLISION")
        return {"rea_session_id": sid, "idempotent": True, "status": (read_json(JOBS / sid / "status.json", {}) or {}).get("status")}
    options = {k: v for k, v in (raw.get("options") or {}).items() if k in OPTION_KEYS and v not in (None, "")}
    if "tool_profile" in options and options["tool_profile"] not in (tool_profiles().get("profiles") or {}):
        raise ValueError("TOOL_PROFILE_UNKNOWN")
    if "model_mode" in options and options["model_mode"] not in {"manual", "auto"}:
        raise ValueError("MODEL_MODE_INVALID")
    if "model_profile" in options and options["model_profile"] not in MODEL_PROFILES:
        raise ValueError("MODEL_PROFILE_INVALID")
    if "required_context" in options and not (isinstance(options["required_context"], int) and 2048 <= options["required_context"] <= 262144):
        raise ValueError("REQUIRED_CONTEXT_INVALID")
    req = {"schema_version": "nexus.rea-request.v1", "nexus_job_id": nexus_job_id, "rea_session_id": sid, "mode": mode,
           "options": options,
           "objective": redact(objective), "target": redact(target), "created_at": str(raw.get("created_at") or now()),
           "submitted_at": now(), "authorization_ref": raw.get("authorization_ref"), "spend_allowed": False}
    write_json(req_path, req)
    update_status(sid, status="SUBMITTED", nexus_job_id=nexus_job_id, mode=mode)
    return {"rea_session_id": sid, "idempotent": False, "status": "SUBMITTED"}


def status_of(sid: str) -> dict:
    st = read_json(JOBS / sid / "status.json")
    if not st:
        return {"rea_session_id": sid, "status": "NOT_FOUND"}
    if st.get("status") in {"RUNNING", "QUEUED_WAITING_FOR_SLOT"}:
        beat = st.get("heartbeat_at") or st.get("updated_at")
        try:
            age = (datetime.now(timezone.utc) - datetime.fromisoformat(beat)).total_seconds()
        except (TypeError, ValueError):
            age = 0
        pid = st.get("runner_pid")
        alive = bool(pid) and Path(f"/proc/{pid}").exists()
        if not alive or (st.get("status") == "RUNNING" and age > 120):
            st = update_status(sid, status="FAILED", reason="REA_RUNNER_LOST", retryable=True)
    return {"rea_session_id": sid, **st}


def health() -> dict:
    p = provider()
    ready, why = provider_ready(p)
    versions = {}
    for name, cmd in {"opencode": ["opencode", "--version"], "rea": ["rea", "--version"], "node": ["node", "--version"]}.items():
        try:
            versions[name] = subprocess.run(cmd, capture_output=True, text=True, timeout=30).stdout.strip().splitlines()[0]
        except Exception:
            versions[name] = None
    props = Path("/opt/ghidra/Ghidra/application.properties").read_text() if Path("/opt/ghidra/Ghidra/application.properties").exists() else ""
    versions["ghidra"] = (re.search(r"application.version=(\S+)", props) or [None, None])[1]
    java = [l for l in subprocess.run(["java", "-version"], capture_output=True, text=True).stderr.splitlines()
            if not l.startswith("Picked up")]
    versions["java"] = java[0] if java else None
    try:
        versions["chromium"] = _chromium()
    except RuntimeError:
        versions["chromium"] = None
    busy = False
    with open(SLOT_LOCK, "a+") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.flock(lock, fcntl.LOCK_UN)
        except BlockingIOError:
            busy = True
    return {"harness_version": VERSION, "versions": versions, "model_provider": {"provider": p.get("provider"), "ready": ready,
            "status": why if not ready else "READY", "model_alias": p.get("model_alias"), "cost_class": p.get("cost_class")},
            "slot_busy": busy, "limits": LIMITS, "resources": resources()}


def cleanup() -> dict:
    removed = []
    cutoff_tmp = time.time() - LIMITS["temp_retention_hours"] * 3600
    cutoff_ws = time.time() - LIMITS["workspace_retention_days"] * 86400
    for base, cutoff in ((TEMP, cutoff_tmp), (WS, cutoff_ws)):
        for child in base.iterdir() if base.exists() else []:
            try:
                if child.is_dir() and child.stat().st_mtime < cutoff:
                    st = read_json(JOBS / child.name / "status.json", {}) or {}
                    if st.get("status") in {"RUNNING", "QUEUED_WAITING_FOR_SLOT"}:
                        continue
                    shutil.rmtree(child)
                    removed.append(str(child))
            except OSError:
                pass
    return {"removed": removed, "resources": resources()}


def main(argv: list[str]) -> int:
    os.umask(0o027)
    cmd = argv[1] if len(argv) > 1 else "health"
    try:
        if cmd == "submit":
            out = submit(json.loads(sys.stdin.read() or "{}"))
        elif cmd == "run":
            if not SID_RE.fullmatch(argv[2]):
                raise ValueError("SID_INVALID")
            return run_session(argv[2])
        elif cmd in {"status", "result"}:
            if not SID_RE.fullmatch(argv[2]):
                raise ValueError("SID_INVALID")
            out = status_of(argv[2]) if cmd == "status" else (read_json(JOBS / argv[2] / "result.json") or {"status": "NOT_READY"})
        elif cmd == "health":
            out = health()
        elif cmd == "cleanup":
            out = cleanup()
        else:
            raise ValueError("UNKNOWN_COMMAND")
        print(json.dumps({"ok": True, "data": out}, default=str))
        return 0
    except ValueError as exc:
        print(json.dumps({"ok": False, "error": {"code": str(exc)[:80], "retryable": False}}))
        return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
