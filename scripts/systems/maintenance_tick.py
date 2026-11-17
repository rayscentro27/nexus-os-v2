#!/usr/bin/env python3
"""Read-only Systems maintenance tick; persists a compact receipt in Systems SQLite."""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import sqlite3
import stat
import subprocess
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "docs/systems/NEXUS_LIVING_MANIFEST.v1.json"
SYSTEMS_DB = Path.home() / ".nexus/state/systems/systems.sqlite3"
RESEARCH_JOBS = Path.home() / ".nexus/state/research/r10/research_r10_batch_c.sqlite3"
RESEARCH_RESULTS = Path.home() / ".nexus/state/research/r10/research_r10_bridge.sqlite3"
RESEARCH_PYTHON = Path.home() / ".nexus/venvs/research-r10-20261027-batch-b/bin/python3.12"
S1_HEALTH = "http://127.0.0.1:18770/health"
RESEARCH_HEALTH = "http://127.0.0.1:18766/health"
MCP_ENDPOINT = "http://127.0.0.1:18765/mcp"
RESEARCH_MCP_ENDPOINT = "http://127.0.0.1:18768/mcp"
RESEARCH_MCP_TOKEN_FILE = Path.home() / ".nexus/state/research-mcp/transport.token"
MCP_KEYCHAIN_SERVICE = "nexus/credential.nexus.mcp.bridge.v1"
MCP_KEYCHAIN_ACCOUNT = "bridge_token"
MCP_REQUIRED_TOOLS = {"systems_status", "systems_job_create", "systems_job_status", "systems_job_result"}
ACTIVE_NEXUS_MCP_RELEASE = Path.home() / ".nexus/releases/nexus-capability-actions-20261104-systems-operator-v3/services/nexus_mcp/systems_bridge.py"
PENDING_STATES = {"READY", "READY_FOR_AGENT", "RUNNING", "EXECUTING", "VALIDATING", "PENDING", "WAITING_APPROVAL", "WAITING_EXTERNAL_BOUNDARY"}
FINAL_STATES = {"COMPLETED", "COMPLETED_WITH_LIMITATIONS", "FAILED", "FAILED_RECOVERABLE", "ROLLED_BACK", "CANCELLED"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _http_health(url: str) -> dict[str, Any]:
    try:
        with urlopen(url, timeout=3) as response:
            payload = json.loads(response.read(4096) or b"{}")
            ok = response.status == 200 and str(payload.get("status", "")).casefold() in {"ok", "healthy"}
            return {"status": "PASS" if ok else "FAIL", "http_status": response.status}
    except Exception as exc:  # Never persist response bodies or exception text.
        return {"status": "FAIL", "error_class": type(exc).__name__}


def _s1_health() -> dict[str, Any]:
    """:18770 is now served by the authenticated MCP bridge candidate; a 401 means
    the listener is alive but auth-gated. Report AUTH_REQUIRED, never PASS."""
    import urllib.error
    try:
        with urlopen(S1_HEALTH, timeout=3) as response:
            payload = json.loads(response.read(4096) or b"{}")
            ok = response.status == 200 and str(payload.get("status", "")).casefold() in {"ok", "healthy"}
            return {"status": "PASS" if ok else "FAIL", "http_status": response.status}
    except urllib.error.HTTPError as exc:
        return {"status": "AUTH_REQUIRED" if exc.code == 401 else "FAIL", "http_status": exc.code}
    except Exception as exc:
        return {"status": "CONNECTION_UNAVAILABLE", "error_class": type(exc).__name__}


def _sqlite_check(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"status": "FAIL", "reason": "DATABASE_NOT_FOUND"}
    try:
        con = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True, timeout=3)
        con.execute("PRAGMA query_only=ON")
        answer = str(con.execute("PRAGMA quick_check").fetchone()[0])
        con.close()
        return {"status": "PASS" if answer == "ok" else "FAIL", "integrity": answer}
    except (sqlite3.Error, OSError) as exc:
        return {"status": "FAIL", "error_class": type(exc).__name__}


def _launchd(label: str, expected_interval: int | None = None) -> dict[str, Any]:
    try:
        result = subprocess.run(["launchctl", "print", f"gui/{os.getuid()}/{label}"],
                                capture_output=True, text=True, timeout=4, check=False)
        loaded = result.returncode == 0
        interval = None
        last_exit = None
        for line in result.stdout.splitlines():
            line = line.strip()
            if line.startswith("run interval ="):
                try:
                    interval = int(line.split("=", 1)[1].strip().split()[0])
                except (ValueError, IndexError):
                    pass
            elif line.startswith("last exit code ="):
                last_exit = line.rsplit("=", 1)[-1].strip()
        passed = loaded and (expected_interval is None or interval == expected_interval)
        return {"status": "PASS" if passed else "FAIL", "loaded": loaded,
                "interval_seconds": interval, "last_exit": last_exit}
    except (OSError, subprocess.SubprocessError) as exc:
        return {"status": "FAIL", "error_class": type(exc).__name__}


class _McpHttpSession:
    """Minimal stdlib client for the MCP streamable-HTTP transport (same
    protocol, endpoints and tools as the SDK client). The `mcp` SDK package
    import pulls in its whole server stack and takes 70-100s on this spinning
    disk, which consumed the check budgets before any request was sent."""

    PROTOCOL_VERSION = "2025-03-26"

    def __init__(self, endpoint: str, token: str, timeout: float = 8):
        self.endpoint, self.timeout, self._id, self.session_id = endpoint, timeout, 0, None
        self._headers = {"Authorization": "Bearer " + token, "Content-Type": "application/json",
                         "Accept": "application/json, text/event-stream"}

    def _post(self, message: dict[str, Any], timeout: float | None = None) -> dict[str, Any] | None:
        from urllib.request import Request
        headers = dict(self._headers)
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id
            headers["MCP-Protocol-Version"] = self.PROTOCOL_VERSION
        req = Request(self.endpoint, data=json.dumps(message).encode(), headers=headers, method="POST")
        with urlopen(req, timeout=timeout or self.timeout) as response:
            self.session_id = response.headers.get("Mcp-Session-Id") or self.session_id
            if "id" not in message:
                return None
            body = response.read(8_000_000).decode("utf-8", "replace")
            if "text/event-stream" in (response.headers.get("Content-Type") or ""):
                for event in body.split("\n\n"):
                    data = "".join(line[5:].strip() for line in event.splitlines() if line.startswith("data:"))
                    if data:
                        parsed = json.loads(data)
                        if parsed.get("id") == message["id"]:
                            body = data
                            break
            reply = json.loads(body)
        if "error" in reply:
            raise RuntimeError("MCP_JSONRPC_ERROR")
        return reply.get("result") or {}

    def request(self, method: str, params: dict[str, Any] | None = None, timeout: float | None = None) -> dict[str, Any]:
        self._id += 1
        return self._post({"jsonrpc": "2.0", "id": self._id, "method": method, "params": params or {}}, timeout) or {}

    def __enter__(self) -> "_McpHttpSession":
        self.request("initialize", {"protocolVersion": self.PROTOCOL_VERSION, "capabilities": {},
                                    "clientInfo": {"name": "nexus-systems-maintenance", "version": "2"}})
        self._post({"jsonrpc": "2.0", "method": "notifications/initialized"})
        return self

    def __exit__(self, *exc: Any) -> None:
        if self.session_id:  # terminate_on_close equivalent
            from urllib.request import Request
            try:
                urlopen(Request(self.endpoint, headers={**self._headers, "Mcp-Session-Id": self.session_id},
                                method="DELETE"), timeout=3).close()
            except Exception:
                pass

    def tool_names(self) -> set[str]:
        return {str(t.get("name")) for t in self.request("tools/list").get("tools", []) if isinstance(t, dict)}

    def call_tool(self, name: str, arguments: dict[str, Any], timeout: float | None = None) -> dict[str, Any]:
        return self.request("tools/call", {"name": name, "arguments": arguments}, timeout)


def _tool_payload(result: dict[str, Any] | None) -> dict[str, Any]:
    if not result:
        return {}
    payload = result.get("structuredContent")
    if isinstance(payload, dict) and payload:
        return payload
    text = next((c.get("text") for c in result.get("content", []) if isinstance(c, dict) and c.get("type") == "text"), None)
    try:
        parsed = json.loads(text) if text else {}
    except ValueError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _nexus_mcp_sync(token: str) -> dict[str, Any]:
    with _McpHttpSession(MCP_ENDPOINT, token) as session:
        names = session.tool_names()
        health = session.call_tool("nexus_get_system_health", {}, timeout=15)
        # systems_status runs a full live S1 snapshot (Oracle SSH + lsof) and
        # can exceed 40s on this host; bound it and report it separately so a
        # slow snapshot does not mask a healthy MCP transport.
        try:
            systems: dict[str, Any] | None = session.call_tool("systems_status", {}, timeout=SYSTEMS_STATUS_BUDGET_SECONDS)
        except (TimeoutError, OSError):
            systems = None
    return {"names": names, "health": health, "systems": systems}


async def _mcp_snapshot() -> dict[str, Any]:
    token = ""
    try:
        auth = subprocess.run(["security", "find-generic-password", "-s", MCP_KEYCHAIN_SERVICE,
                               "-a", MCP_KEYCHAIN_ACCOUNT, "-w"], capture_output=True,
                              text=True, timeout=5, check=False)
        if auth.returncode != 0 or not auth.stdout.strip():
            return {"status": "FAIL", "reason": "AUTH_REFERENCE_UNAVAILABLE"}
        token = auth.stdout.strip()
        got = await asyncio.to_thread(_nexus_mcp_sync, token)
        names, health, systems = got["names"], got["health"], got["systems"]
        health_data = _tool_payload(health)
        health_data = health_data.get("data", {}) if isinstance(health_data, dict) else {}
        source_statuses = health_data.get("source_statuses", {}) if isinstance(health_data, dict) else {}
        env = {str(name): str(value.get("status", "UNKNOWN"))
               for name, value in source_statuses.items() if isinstance(value, dict)} if isinstance(source_statuses, dict) else {}
        base_ok = MCP_REQUIRED_TOOLS <= names and health.get("isError") is not True
        if systems is None:
            status, systems_call = ("DEGRADED" if base_ok else "FAIL"), "TIMEOUT"
        else:
            status = "PASS" if base_ok and systems.get("isError") is not True else "FAIL"
            systems_call = "PASS" if _tool_payload(systems) else "UNVERIFIED"
        return {"status": status,
                "protocol_initialized": True, "tool_count": len(names),
                "systems_read_write_surface": MCP_REQUIRED_TOOLS <= names,
                "environment_summary": {"overall": str(health_data.get("overall_status", "UNKNOWN"))[:48],
                                        "sources": env},
                "systems_status_call": systems_call}
    except Exception as exc:
        return {"status": "FAIL", "error_class": type(exc).__name__}
    finally:
        token = ""


async def _research_mcp_snapshot() -> dict[str, Any]:
    token = ""
    try:
        info = RESEARCH_MCP_TOKEN_FILE.stat()
        if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o600:
            return {"status": "FAIL", "reason": "TRANSPORT_TOKEN_FILE_OWNERSHIP_OR_MODE_INVALID"}
        token = RESEARCH_MCP_TOKEN_FILE.read_text(encoding="utf-8").strip()
        if not token:
            return {"status": "FAIL", "reason": "TRANSPORT_AUTH_REFERENCE_EMPTY"}
        def _research_sync() -> tuple[set[str], dict[str, Any]]:
            with _McpHttpSession(RESEARCH_MCP_ENDPOINT, token) as session:
                return session.tool_names(), session.call_tool("research_health", {}, timeout=15)
        names, health = await asyncio.to_thread(_research_sync)
        payload = _tool_payload(health)
        data = payload.get("data", {}) if isinstance(payload, dict) else {}
        backend_status = str(data.get("status", "UNKNOWN")) if isinstance(data, dict) else "UNKNOWN"
        required = {"research_health", "research_status", "research_result"}
        passed = required <= names and health.get("isError") is not True and backend_status.casefold() in {"ok", "healthy", "pass"}
        return {"status": "PASS" if passed else "FAIL", "protocol_initialized": True,
                "tool_count": len(names), "required_read_tools_discovered": required <= names,
                "backend_health": backend_status[:32]}
    except Exception as exc:
        return {"status": "FAIL", "error_class": type(exc).__name__}
    finally:
        token = ""


def _workflow_snapshot() -> dict[str, Any]:
    if not RESEARCH_PYTHON.is_file():
        return {"status": "FAIL", "reason": "RESEARCH_PYTHON_UNAVAILABLE"}
    script = ROOT / "scripts/systems/workflow_integrity.py"
    try:
        proc = subprocess.run([str(RESEARCH_PYTHON), str(script)], cwd=str(ROOT),
                              capture_output=True, text=True, timeout=60, check=False)
        report = json.loads(proc.stdout)
        snap = report.get("checks", {}).get("research_durable_results_and_events", {})
        ages = report.get("checks", {}).get("paused_work_age", {})
        completion = report.get("checks", {}).get("runnable_work_progress", {})
        sched = report.get("checks", {}).get("scheduler_single_owner", {})
        r10 = report.get("checks", {}).get("r10_http_health", {})
        return {"status": str(report.get("status", "FAIL")), "check_count": report.get("check_count"),
                "pass_count": report.get("pass_count"),
                "research_http": r10.get("status", "UNKNOWN"),
                "research_scheduler": sched.get("status", "UNKNOWN"),
                "paused_resumable_count": ages.get("paused_count", snap.get("paused_resumable_count")),
                "oldest_paused_age_hours": ages.get("oldest_age_hours", snap.get("oldest_paused_age_hours")),
                "active_job_count": snap.get("job_statuses", {}).get("RUNNING", 0),
                "latest_completion_status": snap.get("latest_result_status"),
                "missing_summary_or_findings": snap.get("completed_results_missing_summary_or_findings"),
                "completion_event_count": snap.get("completion_event_count"),
                "runnable_work_progress": completion.get("status", "UNKNOWN"),
                "probe_exit_code": proc.returncode}
    except Exception as exc:
        return {"status": "FAIL", "error_class": type(exc).__name__}


def _manifest_drift() -> dict[str, Any]:
    try:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        records = manifest.get("systems_current_production_hashes", {}).get("files", [])
        mismatch_count = 0
        checked = 0
        for record in records:
            path = Path(str(record.get("path", ""))).expanduser()
            expected = record.get("sha256")
            if not expected:
                continue
            if not path.is_file():
                mismatch_count += 1
                checked += 1
                continue
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            checked += 1
            mismatch_count += digest != expected
        validation = subprocess.run([sys.executable, str(ROOT / "scripts/systems/phase1_runtime.py"),
                                     "--validate-only"], cwd=str(ROOT), capture_output=True,
                                    text=True, timeout=20, check=False)
        parsed = json.loads(validation.stdout or "{}")
        manifest_ok = parsed.get("validation") == "PASS" and validation.returncode == 0
        return {"status": "PASS" if mismatch_count == 0 and manifest_ok else "ATTENTION",
                "production_hashes_checked": checked, "production_hash_mismatches": mismatch_count,
                "manifest_validation": parsed.get("validation", "FAIL")}
    except Exception as exc:
        return {"status": "ATTENTION", "error_class": type(exc).__name__}


def _pending_systems_work() -> dict[str, Any]:
    try:
        con = sqlite3.connect(SYSTEMS_DB.resolve().as_uri() + "?mode=ro", uri=True, timeout=3)
        con.execute("PRAGMA query_only=ON")
        rows = con.execute("SELECT request_id,receipt_type,payload,created_at FROM receipts "
                           "WHERE receipt_type LIKE 'SYSTEMS_MANAGED_JOB%' ORDER BY created_at,rowid").fetchall()
        con.close()
        latest: dict[str, tuple[dict[str, Any], str]] = {}
        for request_id, kind, raw, created_at in rows:
            try:
                payload = json.loads(raw)
            except (TypeError, json.JSONDecodeError):
                continue
            state = str(payload.get("status", "UNKNOWN")).upper()
            if state == "UNKNOWN" and kind == "SYSTEMS_MANAGED_JOB":
                state = "READY_FOR_AGENT"
            latest[str(request_id)] = ({"state": state}, str(created_at))
        counts: dict[str, int] = {}
        pending = 0
        for record, _ in latest.values():
            state = record["state"]
            counts[state] = counts.get(state, 0) + 1
            if state in PENDING_STATES and state not in FINAL_STATES:
                pending += 1
        return {"status": "PASS", "active_or_pending_count": pending,
                "state_counts": counts, "continuation_required": pending > 0}
    except Exception as exc:
        return {"status": "FAIL", "error_class": type(exc).__name__}


def _eligible_same_job_retry() -> dict[str, Any] | None:
    """Select at most one explicitly retryable, due transient failure from the existing job ledger."""
    try:
        with sqlite3.connect(SYSTEMS_DB.resolve().as_uri() + "?mode=ro", uri=True, timeout=3) as con:
            rows = con.execute("SELECT request_id,receipt_type,payload FROM receipts WHERE receipt_type LIKE 'SYSTEMS_MANAGED_JOB%' ORDER BY created_at,rowid").fetchall()
        grouped: dict[str, list[tuple[str, dict[str, Any]]]] = {}
        for job_id, kind, raw in rows:
            try: item = json.loads(raw)
            except (TypeError, json.JSONDecodeError): continue
            grouped.setdefault(str(job_id), []).append((str(kind), item))
        now = datetime.now(timezone.utc)
        for job_id, events in reversed(list(grouped.items())):
            if not events: continue
            order = events[0][1]
            latest = events[-1][1]
            retry = latest.get("retry") if isinstance(latest.get("retry"), dict) else {}
            if (latest.get("status") != "FAILED_RECOVERABLE" or retry.get("retryable") is not True
                    or int(retry.get("attempt", 0)) >= int(retry.get("max_attempts", 0))):
                continue
            action = str(order.get("requested_action", ""))
            if action not in {"BOUNDED_UPGRADE", "SAFE_CLEANUP", "CREDENTIAL_ROTATION", "KAGGLE_PREP", "SAFE_RESTART", "ROLLBACK"}:
                continue
            if order.get("maintenance_classification") != "AUTONOMOUS_BOUNDED":
                continue
            typed_config = order.get("typed_action_config") if isinstance(order.get("typed_action_config"), dict) else {}
            if typed_config.get("approval_reference"):
                continue
            try:
                if retry.get("not_before") and datetime.fromisoformat(str(retry["not_before"])) > now:
                    continue
            except ValueError:
                continue
            return {"systems_job_id": job_id}
    except (sqlite3.Error, OSError, ValueError):
        return None
    return None


def _eligible_ready_job() -> dict[str, Any] | None:
    """Use the existing managed-work ledger to find one supported READY read-only job."""
    try:
        sys.path.insert(0, str(ROOT / "scripts/systems"))
        from managed_work import next_ready_readonly_job
        job_id = next_ready_readonly_job(db_path=SYSTEMS_DB)
        return {"systems_job_id": job_id} if job_id else None
    except (ImportError, OSError, sqlite3.Error):
        return None


def _resume_one_same_job() -> dict[str, Any]:
    """Use the existing authenticated S1 bridge; this path never invokes an AI worker."""
    ready = _eligible_ready_job()
    if ready:
        sys.path.insert(0, str(ROOT / "scripts/systems"))
        from managed_work import resume_ready_readonly_work
        result = resume_ready_readonly_work(ready["systems_job_id"], db_path=SYSTEMS_DB)
        return {"status": str(result.get("status", "UNKNOWN")), "same_job": True,
                "attempted": bool(result.get("attempted")), "ai_usage": "NONE"}

    bridge_path = ACTIVE_NEXUS_MCP_RELEASE
    if bridge_path.is_symlink() or not bridge_path.is_file():
        return {"status": "UNAVAILABLE", "reason": "ACTIVE_TYPED_BRIDGE_UNAVAILABLE"}
    candidate = _eligible_same_job_retry()
    if not candidate:
        return {"status": "NO_ELIGIBLE_WORK"}
    auth = subprocess.run(["security", "find-generic-password", "-s", MCP_KEYCHAIN_SERVICE,
                           "-a", MCP_KEYCHAIN_ACCOUNT, "-w"], capture_output=True, text=True, timeout=5, check=False)
    if auth.returncode != 0 or not auth.stdout.strip():
        return {"status": "UNAVAILABLE", "reason": "BRIDGE_AUTH_REFERENCE_UNAVAILABLE"}
    os.environ["NEXUS_MCP_BRIDGE_TOKEN"] = auth.stdout.strip()
    import importlib.util
    spec = importlib.util.spec_from_file_location("systems_existing_mcp_bridge", bridge_path)
    if spec is None or spec.loader is None:
        return {"status": "UNAVAILABLE", "reason": "ACTIVE_TYPED_BRIDGE_IMPORT_FAILED"}
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    sys.path.insert(0, str(ROOT / "scripts/systems"))
    from managed_work import resume_recoverable_work
    result = resume_recoverable_work(candidate["systems_job_id"], typed_executor=lambda operation, **kwargs:
        module.request(operation, **kwargs), db_path=SYSTEMS_DB)
    return {"status": str(result.get("completion") or result.get("status", "UNKNOWN")),
            "same_job": True, "attempted": True}


MCP_SNAPSHOT_DEADLINE_SECONDS = 45
SYSTEMS_STATUS_BUDGET_SECONDS = 25
TICK_WATCHDOG_SECONDS = 240  # must stay below the 300s StartInterval


async def _bounded(coro: Any, seconds: int) -> dict[str, Any]:
    """Hard overall deadline: per-request MCP timeouts alone let a silent stream
    block asyncio forever (observed: one tick hung from 2026-11-06 for 6 days,
    which stopped every later launchd interval run)."""
    try:
        return await asyncio.wait_for(coro, seconds)
    except (asyncio.TimeoutError, TimeoutError):
        return {"status": "FAIL", "error_class": "TimeoutError", "bounded_seconds": seconds}


# Private-node probes over Tailscale (canonical SSH aliases). Read-only; a
# transport failure degrades CONNECTION only and never removes a capability.
# Postiz authenticated read on Contabo itself: the API key file stays on the
# host (sourced in a subshell); only HTTP status, counts and provider names
# come back. Configured providers are env-name presence only, never values.
POSTIZ_PROBE = r"""; T=$(mktemp); ( . /opt/nexus-app-services/shared/secrets/postiz_api.env 2>/dev/null; curl -s -m 8 -o "$T" -w 'POSTIZ_AUTH_API=%{http_code}\n' -H "Authorization: $POSTIZ_API_KEY" http://127.0.0.1:4007/api/public/v1/integrations ); python3 -c 'import json,sys
try: d=json.load(open(sys.argv[1]))
except Exception: d=None
if isinstance(d,list):
    print("POSTIZ_INTEGRATIONS=%d" % len(d)); print("POSTIZ_INTEGRATIONS_ACTIVE=%d" % sum(1 for i in d if not i.get("disabled"))); print("POSTIZ_INTEGRATION_PROVIDERS=" + ",".join(sorted({str(i.get("identifier")) for i in d})))' "$T"; rm -f "$T"; echo POSTIZ_PROVIDERS_CONFIGURED=$(docker exec postiz printenv 2>/dev/null | grep -oE '^(FACEBOOK_APP_ID|INSTAGRAM_APP_ID|YOUTUBE_CLIENT_ID|TIKTOK_CLIENT_ID|LINKEDIN_CLIENT_ID)=.' | cut -d= -f1 | paste -sd, -); echo POSTIZ_FRONTEND_SCHEME=$(docker exec postiz printenv FRONTEND_URL 2>/dev/null | cut -d: -f1)"""

# Meta OAuth callback-origin override (Postiz stays tailnet-only; Meta redirects
# to static bounce pages on POSTIZ_META_OAUTH_ORIGIN). Compares the running
# image and the two in-container provider files against the on-host manifest
# written when the overrides were made. No Postiz API calls (public API is
# rate-limited), no secrets: hashes, image ids and the non-secret origin only.
POSTIZ_EXPECTED_VERSION = "v2.25.3"
POSTIZ_META_OAUTH_ORIGIN_EXPECTED = "https://postiz-auth.goclearonline.cc"
POSTIZ_PRIVATE_ORIGIN = "https://nexus-app-services.tailb1e262.ts.net"
POSTIZ_META_PROVIDERS = ("facebook", "instagram")
POSTIZ_BOUNCE_PROVIDERS = ("facebook", "instagram", "tiktok")
# user.info.profile is not enabled in the TikTok Sandbox (2026-11-13): open_id is the
# primary identity, display_name secondary; username is not requested.
POSTIZ_TIKTOK_EXPECTED_SCOPES = ("user.info.basic", "video.upload")
POSTIZ_TIKTOK_FORBIDDEN_SCOPES = ("video.publish", "video.list", "user.info.stats")
POSTIZ_OAUTH_PROBE = r"""; python3 -c 'import json,subprocess as s
def r(*a):
    try: return s.run(list(a),capture_output=True,text=True,timeout=8).stdout.strip()
    except Exception: return ""
D="/app/apps/backend/dist/libraries/nestjs-libraries/src/integrations/social"
img=r("docker","inspect","-f","{{.Image}}","postiz")
try: m=json.load(open("/opt/nexus-app-services/postiz/overrides/v2.25.3/MANIFEST.json"))
except Exception: m={}
print("POSTIZ_IMAGE="+r("docker","inspect","-f","{{.Config.Image}}","postiz"))
print("POSTIZ_IMAGE_MATCHES_MANIFEST="+("YES" if m and img==m.get("image_id") else "NO"))
print("POSTIZ_META_OAUTH_ORIGIN="+r("docker","exec","postiz","printenv","POSTIZ_META_OAUTH_ORIGIN"))
print("POSTIZ_TIKTOK_OAUTH_ORIGIN="+r("docker","exec","postiz","printenv","POSTIZ_TIKTOK_OAUTH_ORIGIN"))
src=r("docker","exec","postiz","cat",D+"/tiktok.provider.js")
blk=src.split("this.scopes = [",1)[1].split("];",1)[0] if "this.scopes = [" in src else ""
print("POSTIZ_TIKTOK_SCOPES="+",".join(x.strip().strip(chr(39)+",") for x in blk.splitlines() if x.strip()))
print("POSTIZ_TIKTOK_REDIRECT_SITES_USING_ORIGIN=%d" % src.count("process.env.POSTIZ_TIKTOK_OAUTH_ORIGIN ||"))
for p in ("facebook","instagram","tiktok"):
    h=r("docker","exec","postiz","sha256sum",D+"/"+p+".provider.js")[:64]
    f=(m.get("files") or {}).get(p+".provider.js") or {}
    st="OVERRIDE" if h and h==f.get("override_sha256") else "ORIGINAL" if h and h==f.get("original_sha256") else "MISMATCH"
    print("POSTIZ_PROVIDER_"+p.upper()+"="+st)'"""


NODE_PROBES = {
    "CONTABO_APP_SERVICES": {
        "alias": "nexus-contabo-ts",
        "script": ("set +e; echo HOST=$(hostname); echo DOCKER=$(systemctl is-active docker); "
                   "echo DISK_PCT=$(df --output=pcent / | tail -1 | tr -dc 0-9); "
                   "echo MEM_AVAIL_PCT=$(awk '/MemTotal/{t=$2}/MemAvailable/{a=$2}END{printf \"%d\", a*100/t}' /proc/meminfo); "
                   "echo LOAD1=$(cut -d' ' -f1 /proc/loadavg); echo CPUS=$(nproc); "
                   "echo TAILSCALE=$(tailscale status --json 2>/dev/null | python3 -c 'import json,sys; print(json.load(sys.stdin).get(\"BackendState\"))' 2>/dev/null); "
                   "echo UFW=$(sudo -n ufw status 2>/dev/null | head -1 | awk '{print $2}'); echo FAIL2BAN=$(systemctl is-active fail2ban); "
                   "echo SSHD_ROOT=$(sudo -n sshd -T 2>/dev/null | awk '/^permitrootlogin /{print $2}'); "
                   "echo SSHD_PASSWORD=$(sudo -n sshd -T 2>/dev/null | awk '/^passwordauthentication /{print $2}'); "
                   "for c in $(docker ps -a --format '{{.Names}}' 2>/dev/null); do echo CONTAINER_$c=$(docker inspect -f '{{.State.Status}}/{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' $c); done; "
                   "echo HTTP_POSTIZ=$(curl -s -o /dev/null -m 8 -w '%{http_code}' http://127.0.0.1:4007/api/public/v1/is-connected); "
                   "echo HTTP_N8N=$(curl -s -o /dev/null -m 8 -w '%{http_code}' http://127.0.0.1:5678/healthz); "
                   "echo APP_DATA_PCT=$(df --output=pcent /var/lib/docker | tail -1 | tr -dc 0-9); "
                   "echo LAST_BACKUP=$(ls -1 /opt/nexus-app-services/backups/runs 2>/dev/null | tail -1)") + POSTIZ_PROBE + POSTIZ_OAUTH_PROBE,
    },
    "ORACLE": {
        "alias": "nexus-oracle-ts",
        "script": ("set +e; echo HOST=$(hostname); "
                   "echo TAILSCALE=$(tailscale status --json 2>/dev/null | python3 -c 'import json,sys; print(json.load(sys.stdin).get(\"BackendState\"))' 2>/dev/null); "
                   "echo HERMES=$(systemctl --user is-active nexus-hermes-0225); echo NOVA=$(systemctl --user is-active nova-telegram-oracle); "
                   "echo HOST_CONTROL=$(systemctl --user is-active nexus-oracle-host-control); echo SEARXNG=$(systemctl is-active nexus-searxng); "
                   "echo FIREWALLD=$(systemctl is-active firewalld); "
                   "echo SSHD_PASSWORD=$(sudo -n sshd -T 2>/dev/null | awk '/^passwordauthentication /{print $2}'); "
                   "echo DISK_PCT=$(df --output=pcent / | tail -1 | tr -dc 0-9); echo LOAD1=$(cut -d' ' -f1 /proc/loadavg); "
                   "echo BRIDGE_LISTEN=$(ss -ltn 2>/dev/null | awk '{print $4}' | grep -oE '^127\\.0\\.0\\.1:1876[5-8]$' | cut -d: -f2 | sort -u | tr '\\n' ,)"),
    },
}

# Mac -> Oracle reverse bridges (scripts/ops/oracle_reverse_tunnel.sh). Oracle
# consumers call 127.0.0.1:<port>; the tunnel prefers Tailscale and falls back
# to the legacy public-IP ssh path. Recorded as TRANSPORT so a fallback or drop
# degrades connection health only.
ORACLE_BRIDGES = {18765: "nexus_mcp", 18767: "google_mcp", 18768: "research_mcp"}
ORACLE_TAILSCALE_IP = "100.91.191.32"
ORACLE_PUBLIC_IP = "161.153.40.41"
TRANSPORT_STATE_DIR = Path.home() / ".nexus" / "state" / "transport"


def _oracle_bridges() -> dict[str, Any]:
    bridges: dict[str, Any] = {}
    for port, label in ORACLE_BRIDGES.items():
        info: dict[str, Any] = {"port": port, "transport": "DOWN"}
        try:
            state = json.loads((TRANSPORT_STATE_DIR / f"oracle_reverse_{port}.json").read_text())
            pid = int(state["ssh_pid"])
            os.kill(pid, 0)
            out = subprocess.run(["/usr/sbin/lsof", "-nP", "-a", "-p", str(pid), "-iTCP", "-sTCP:ESTABLISHED"],
                                 capture_output=True, text=True, timeout=10, check=False).stdout
            peer = ORACLE_TAILSCALE_IP if f"->{ORACLE_TAILSCALE_IP}:22" in out else (
                ORACLE_PUBLIC_IP if f"->{ORACLE_PUBLIC_IP}:22" in out else None)
            info.update({"selected": state.get("transport"), "started_at": state.get("started_at"),
                         "transport": {ORACLE_TAILSCALE_IP: "TAILSCALE", ORACLE_PUBLIC_IP: "LEGACY_PUBLIC_FALLBACK"}.get(peer, "DOWN")})
        except FileNotFoundError:
            info["transport"] = "UNMANAGED"   # tunnel not running under the canonical helper
        except (ProcessLookupError, KeyError, ValueError, OSError, subprocess.TimeoutExpired):
            info["transport"] = "DOWN"
        bridges[label] = info
    ok = all(b["transport"] == "TAILSCALE" for b in bridges.values())
    return {"status": "PASS" if ok else "DEGRADED", "bridges": bridges}


POSTIZ_RECEIPTS = ROOT / "data/governed/distribution_provider_receipts.jsonl"
POSTIZ_ROUTER = ROOT / "scripts/nexus_agent_platform/social_provider_router.py"
POSTIZ_ADAPTER = ROOT / "scripts/distribution/postiz_provider_adapter.py"


def _postiz_governed() -> dict[str, Any]:
    """Nexus-side Postiz state: provider router/adapter present and the last
    Nexus-owned Postiz receipts (success/failure). Local reads only."""
    receipts: list[dict[str, Any]] = []
    try:
        for line in _tail_lines(POSTIZ_RECEIPTS, 65536):
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if (rec.get("provider") == "POSTIZ" or rec.get("orchestrator") == "N8N"
                    or rec.get("workflow") == "postiz_connectivity_certification"):
                receipts.append(rec)
    except OSError:
        pass
    done = [r for r in receipts if r.get("state") == "COMPLETED"]
    bad = [r for r in receipts if r.get("state") in ("FAILED", "BLOCKED")]
    router = POSTIZ_ROUTER.is_file() and POSTIZ_ADAPTER.is_file()
    return {"status": "PASS" if router else "FAIL",
            "provider_router": "PRESENT" if router else "MISSING",
            "live_publish_enabled": False,
            "last_success": done[-1].get("recorded_at") if done else None,
            "last_success_action": done[-1].get("action") if done else None,
            "last_failure": bad[-1].get("recorded_at") if bad else None,
            "last_failure_outcome": bad[-1].get("outcome") if bad else None,
            "receipt_count_tail": len(receipts)}


def _tls_context() -> Any:
    """Verifying TLS context with a real CA bundle: Homebrew OpenSSL on this Mac
    ships no cert.pem, so default contexts fail every public HTTPS check.
    Verification is never disabled."""
    import ssl
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except (ImportError, OSError):
        pass
    if Path("/etc/ssl/cert.pem").is_file():
        return ssl.create_default_context(cafile="/etc/ssl/cert.pem")
    return ssl.create_default_context()


def _fetch(url: str, timeout: float = 6) -> tuple[int | None, dict[str, str], str]:
    from urllib.error import HTTPError, URLError
    from urllib.request import Request
    try:
        with urlopen(Request(url, headers={"User-Agent": "nexus-systems-tick"}), timeout=timeout,
                     context=_tls_context()) as resp:
            return resp.status, {k.lower(): v for k, v in resp.headers.items()}, resp.read(16384).decode("utf-8", "replace")
    except HTTPError as exc:
        return exc.code, {k.lower(): v for k, v in (exc.headers or {}).items()}, ""
    except (URLError, OSError, ValueError) as exc:
        return None, {}, type(exc).__name__


def _postiz_oauth_bounce(fetch: Any = None) -> dict[str, Any]:
    """Public Meta OAuth bounce pages on POSTIZ_META_OAUTH_ORIGIN: the two
    callback paths serve the static bounce (hard-coded private destination,
    strict headers) and unrelated paths on that host return 404. Public GETs
    with no query string; nothing is sent to Postiz."""
    fetch = fetch or _fetch
    pages: dict[str, Any] = {}
    ok = True
    for p in POSTIZ_BOUNCE_PROVIDERS:
        code, hdrs, body = fetch(f"{POSTIZ_META_OAUTH_ORIGIN_EXPECTED}/integrations/social/{p}")
        good = (code == 200 and f'var t="{POSTIZ_PRIVATE_ORIGIN}/integrations/social/{p}"' in body
                and hdrs.get("content-security-policy", "").startswith("default-src 'none'")
                and hdrs.get("referrer-policy") == "no-referrer" and "no-store" in hdrs.get("cache-control", "")
                and hdrs.get("x-frame-options", "").upper() == "DENY")
        pages[p] = {"http_status": code, "valid": good, "error": None if code else body}
        ok = ok and good
    unrelated = {}
    # Real site paths too: a host rule ordered after site rules would leak them.
    for path in ("/", "/got-funding", "/privacy/nexus-postiz", "/nexus-systems-probe-unrelated"):
        code, _, body = fetch(POSTIZ_META_OAUTH_ORIGIN_EXPECTED + path)
        unrelated[path] = code if code else body
        ok = ok and code == 404
    unreachable = all(v.get("http_status") is None for v in pages.values())
    return {"status": "PASS" if ok else ("UNREACHABLE" if unreachable else "FAIL"),
            "origin": POSTIZ_META_OAUTH_ORIGIN_EXPECTED, "callback_pages": pages, "unrelated_paths": unrelated}


DISPATCHER_LABEL = "com.nexus.durable-dispatcher"
DISPATCHER_LOG = ROOT / "reports/runtime/durable_dispatcher.log"
DISPATCHER_ERROR_LOG = ROOT / "reports/runtime/durable_dispatcher_error.log"
DISPATCHER_STALE_SECONDS = 180   # 6 missed 30s intervals


def _tail_lines(path: Path, max_bytes: int = 16384) -> list[str]:
    with path.open("rb") as fh:
        fh.seek(0, os.SEEK_END)
        size = fh.tell()
        fh.seek(max(0, size - max_bytes))
        return fh.read().decode("utf-8", "replace").splitlines()[1 if size > max_bytes else 0:]


def _iso_mtime(path: Path) -> str | None:
    try:
        return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()
    except OSError:
        return None


RESEARCH_JOBS_DB = Path.home() / ".nexus/state/research/r10/research_r10_batch_c.sqlite3"
NOVA_NOTIFY_PENDING_ATTENTION_MINUTES = 30
# Read-only facts from the existing Nova consumer (no secrets, no chat ids).
NOVA_NOTIFY_PROBE = (
    "set +e; echo NOVA=$(systemctl --user is-active nova-telegram-oracle); "
    "P=$(systemctl --user show -p MainPID --value nova-telegram-oracle); "
    "echo RELEASE=$(tr '\\0' ' ' < /proc/$P/cmdline 2>/dev/null | grep -o 'releases/[^/]*' | cut -d/ -f2); "
    "echo FROZEN=$([ -e ~/.nexus/state/nova/proactive_delivery.freeze ] && echo yes || echo no); "
    "python3 -c 'import json,os,collections; s=json.load(open(os.path.expanduser(\"~/.nexus/state/nova/nova_proactive_communications.json\"))); "
    "d=[x for x in s.get(\"deliveries\",{}).values() if isinstance(x,dict)]; r=[x for x in d if x.get(\"source_receipt\")==\"R10_COMPLETION_EVENT\"]; "
    "ok=[x for x in r if x.get(\"status\")==\"SENT\"]; c=collections.Counter(x.get(\"material_state_hash\") for x in ok); "
    "print(\"LAST_SENT=\"+max((x.get(\"delivered_at\") or \"\" for x in ok), default=\"\")); "
    "print(\"FAILED=%d\" % sum(1 for x in r if x.get(\"status\")==\"FAILED\")); "
    "print(\"DUPLICATE_SENDS=%d\" % sum(v-1 for v in c.values() if v>1))' 2>/dev/null || echo LEDGER=UNREADABLE")


def _age_minutes(stamp: str | None, now: datetime) -> int | None:
    try:
        return int((now - datetime.fromisoformat(str(stamp).replace("Z", "+00:00"))).total_seconds() // 60)
    except (TypeError, ValueError):
        return None


def _nova_research_notifications() -> dict[str, Any]:
    """Research completion -> Nova -> owner delivery health. Healthy requires an
    advancing outbox, not merely a running worker: the Nov 4-14 2026 outage had
    a live worker while one undeliverable head event pinned 18 notices."""
    now = datetime.now(timezone.utc)
    out: dict[str, Any] = {}
    try:
        with sqlite3.connect(RESEARCH_RESULTS.resolve().as_uri() + "?mode=ro", uri=True, timeout=3) as con:
            con.execute("ATTACH DATABASE ? AS j", (RESEARCH_JOBS_DB.resolve().as_uri() + "?mode=ro",))
            rows = con.execute(
                "SELECT e.event_id, (SELECT updated_at FROM j.jobs WHERE job_id=e.job_id) FROM completion_events e "
                "JOIN bridge_jobs b ON b.job_id=e.job_id WHERE b.caller='NOVA_NEXUS' AND e.delivered_at IS NULL "
                "ORDER BY e.rowid").fetchall()
            last_ack = con.execute(
                "SELECT max(e.delivered_at) FROM completion_events e JOIN bridge_jobs b ON b.job_id=e.job_id "
                "WHERE b.caller='NOVA_NEXUS'").fetchone()[0]
    except sqlite3.Error as exc:
        return {"status": "FAIL", "error_class": type(exc).__name__}
    ages = [a for a in (_age_minutes(r[1], now) for r in rows) if a is not None]
    out.update({"pending_count": len(rows), "oldest_pending_age_minutes": max(ages) if ages else 0,
                "oldest_pending_event": rows[0][0] if rows else None, "last_outbox_ack_at": last_ack})
    try:
        proc = subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", "nexus-oracle-ts", NOVA_NOTIFY_PROBE],
                              capture_output=True, text=True, timeout=25, check=False)
        facts = dict(line.split("=", 1) for line in proc.stdout.splitlines() if "=" in line)
    except subprocess.TimeoutExpired:
        facts = {}
    out.update({"consumer": facts.get("NOVA") or "UNKNOWN", "consumer_release": facts.get("RELEASE") or None,
                "delivery_frozen": facts.get("FROZEN") == "yes",
                "last_successful_delivery_at": facts.get("LAST_SENT") or None,
                "delivery_failures_recorded": int(facts.get("FAILED") or 0) if facts.get("FAILED", "").isdigit() else None,
                "duplicate_sends": int(facts.get("DUPLICATE_SENDS") or 0) if facts.get("DUPLICATE_SENDS", "").isdigit() else None})
    reasons = []
    if out["consumer"] != "active":
        reasons.append("CONSUMER_NOT_ACTIVE")
    if facts.get("LEDGER") == "UNREADABLE" or out["duplicate_sends"] is None:
        reasons.append("LEDGER_UNREADABLE")
    if out["oldest_pending_age_minutes"] > NOVA_NOTIFY_PENDING_ATTENTION_MINUTES:
        reasons.append("OUTBOX_NOT_ADVANCING")
    if out["delivery_frozen"]:
        reasons.append("DELIVERY_FROZEN")
    if out["duplicate_sends"]:
        reasons.append("DUPLICATE_SENDS")
    out["reasons"] = reasons
    out["status"] = "FAIL" if "CONSUMER_NOT_ACTIVE" in reasons else ("ATTENTION" if reasons else "PASS")
    return out


R10_PLIST = Path.home() / "Library/LaunchAgents/com.nexus.research-r10.plist"
R10_GATE_KINDS = ("RESEARCH_QUALITY_GATE_STARTED", "RESEARCH_QUALITY_GATE_PASSED", "RESEARCH_QUALITY_GATE_FAILED")


def _research_quality_gate() -> dict[str, Any]:
    """R10 artifact quality gate observability (R10_ARTIFACT_QUALITY_GATE_R1). Read-only:
    the launchd plist, the R10 /health payload and the existing R10 receipts/results stores.
    ATTENTION when any artifact completed under the gate without a PASSED gate receipt."""
    import plistlib
    out: dict[str, Any] = {}
    try:
        env = (plistlib.loads(R10_PLIST.read_bytes()).get("EnvironmentVariables") or {})
        out["active_release"] = Path(str(env.get("NEXUS_R10_RELEASE") or "")).name or None
    except (OSError, ValueError):
        out["active_release"] = None
    try:
        with urlopen(RESEARCH_HEALTH, timeout=3) as response:
            body = json.loads(response.read(4096) or b"{}")
    except Exception as exc:  # never persist response bodies or exception text
        body = {}
        out["health_error_class"] = type(exc).__name__
    body = body if isinstance(body, dict) else {}
    gate = body.get("quality_gate")
    out["serving_release"] = body.get("release")
    out["quality_gate_available"] = bool(isinstance(gate, dict) and gate.get("enabled"))
    out["quality_gate_version"] = gate.get("version") if isinstance(gate, dict) else None
    try:
        with sqlite3.connect(RESEARCH_JOBS_DB.resolve().as_uri() + "?mode=ro", uri=True, timeout=3) as con:
            first = con.execute("SELECT min(created_at) FROM receipts WHERE kind='RESEARCH_QUALITY_GATE_STARTED'").fetchone()[0]
            last = con.execute("SELECT kind, job_id, created_at FROM receipts WHERE kind IN (?,?) ORDER BY created_at DESC LIMIT 1",
                               R10_GATE_KINDS[1:]).fetchone()
            since = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
            failures_24h = con.execute("SELECT count(*) FROM receipts WHERE kind='RESEARCH_QUALITY_GATE_FAILED' AND created_at>=?", (since,)).fetchone()[0]
            passes_24h = con.execute("SELECT count(*) FROM receipts WHERE kind='RESEARCH_QUALITY_GATE_PASSED' AND created_at>=?", (since,)).fetchone()[0]
            ungated, inconclusive, gated_ids = [], 0, []
            if first:
                rows = con.execute(
                    "SELECT c.job_id, c.payload, EXISTS(SELECT 1 FROM receipts p WHERE p.job_id=c.job_id AND p.kind='RESEARCH_QUALITY_GATE_PASSED') "
                    "FROM receipts c WHERE c.kind IN ('RESEARCH_COMPLETE','RESEARCH_COMPLETE_WITH_LIMITATIONS') AND c.created_at>=?", (first,)).fetchall()
                for job_id, payload, passed in rows:
                    try:
                        marker = (json.loads(payload) or {}).get("quality_gate")
                    except ValueError:
                        marker = None
                    if passed:
                        gated_ids.append(job_id)
                    elif marker == "NOT_APPLICABLE_INCONCLUSIVE_OUTCOME":
                        inconclusive += 1
                    else:
                        ungated.append(job_id)
    except sqlite3.Error as exc:
        return {**out, "status": "FAIL", "error_class": type(exc).__name__}
    missing_classification = 0
    if gated_ids:
        try:
            with sqlite3.connect(RESEARCH_RESULTS.resolve().as_uri() + "?mode=ro", uri=True, timeout=3) as con:
                for job_id in gated_ids[-20:]:
                    row = con.execute("SELECT json_extract(result_json,'$.sources[0].source_type'), "
                                      "json_extract(result_json,'$.source_classes') FROM bridge_results WHERE job_id=?", (job_id,)).fetchone()
                    if not row or not row[0] or not row[1]:
                        missing_classification += 1
        except sqlite3.Error as exc:
            return {**out, "status": "FAIL", "error_class": type(exc).__name__}
    out.update({"gate_active_since": first, "last_gate_result": last[0].rsplit("_", 1)[-1] if last else None,
                "last_gate_job": last[1] if last else None, "last_gate_at": last[2] if last else None,
                "gate_failures_24h": failures_24h, "gate_passes_24h": passes_24h,
                "completed_without_gate_pass": len(ungated), "completed_without_gate_pass_jobs": ungated[:5],
                "inconclusive_completions_not_gated": inconclusive, "gated_completions": len(gated_ids),
                "gated_results_missing_source_classification": missing_classification})
    reasons = []
    if not out["quality_gate_available"]:
        reasons.append("QUALITY_GATE_UNAVAILABLE")
    if ungated:
        reasons.append("COMPLETED_WITHOUT_GATE_PASS")
    if missing_classification:
        reasons.append("SOURCE_CLASSIFICATION_MISSING")
    if out["active_release"] and out["serving_release"] and out["active_release"] != out["serving_release"]:
        reasons.append("SERVING_RELEASE_DIFFERS_FROM_PLIST")
    out["reasons"] = reasons
    out["status"] = "ATTENTION" if reasons else "PASS"
    return out


RESEARCH_MCP_PLIST = Path.home() / "Library/LaunchAgents/com.nexus.research-mcp.plist"
DISPATCHER_PLIST = Path.home() / "Library/LaunchAgents/com.nexus.durable-dispatcher.plist"
# RESEARCH_DURABLE_HANDOFF_R1 activation instant: normal Nova Research created after this must be durably owned.
RESEARCH_DURABLE_ACTIVATED_AT = "2026-11-14T15:37:00+00:00"


def _research_durable_path() -> dict[str, Any]:
    """Durable Research path health (RESEARCH_DURABLE_HANDOFF_R1). Read-only: launchd plists, R10 /health,
    and the dispatcher release's own research_engine_handoff health audit (Nexus job <-> R17 linkage)."""
    import plistlib
    out: dict[str, Any] = {"activated_at": RESEARCH_DURABLE_ACTIVATED_AT}
    reasons: list[str] = []
    try:
        mcp_args = plistlib.loads(RESEARCH_MCP_PLIST.read_bytes()).get("ProgramArguments") or []
        mcp_release = Path(str(mcp_args[0])).parents[1] if mcp_args else None
        out["research_mcp_release"] = mcp_release.name if mcp_release else None
        out["research_mcp_durable_facade"] = bool(mcp_release and "nexus_agent_platform.research_engine_handoff"
                                                  in (mcp_release / "research_mcp/server.py").read_text(encoding="utf-8"))
    except (OSError, ValueError, IndexError):
        out["research_mcp_durable_facade"] = False
    try:
        disp = plistlib.loads(DISPATCHER_PLIST.read_bytes())
        disp_release = Path(str((disp.get("ProgramArguments") or ["", "", ""])[2])).parents[2]
        sources = str((disp.get("EnvironmentVariables") or {}).get("NEXUS_DISPATCH_ALLOWED_JOB_SOURCES") or "")
        out["dispatcher_release"] = disp_release.name
        out["dispatcher_claims_durable_research"] = ("NOVA_RESEARCH_MCP_REQUEST" in sources.split(",")
                                                     and (disp_release / "scripts/nexus_agent_platform/research_engine_handoff.py").is_file())
    except (OSError, ValueError, IndexError):
        disp_release = None
        out["dispatcher_claims_durable_research"] = False
    try:
        with urlopen(RESEARCH_HEALTH, timeout=3) as response:
            body = json.loads(response.read(4096) or b"{}")
        out["engine_release"] = body.get("release")
        out["engine_event_hold"] = bool((body.get("durable_handoff") or {}).get("event_hold"))
    except Exception as exc:  # never persist bodies or exception text
        out["engine_event_hold"] = False
        out["engine_health_error_class"] = type(exc).__name__
    out["durable_path_active"] = bool(out.get("research_mcp_durable_facade") and out.get("dispatcher_claims_durable_research")
                                      and out.get("engine_event_hold"))
    if not out["durable_path_active"]:
        reasons.append("DURABLE_RESEARCH_PATH_INACTIVE")
    audit: dict[str, Any] = {}
    if disp_release is not None:
        env = {"PATH": "/usr/bin:/bin", "HOME": str(Path.home()), "PYTHONDONTWRITEBYTECODE": "1",
               "PYTHONPATH": f"{disp_release}/scripts:{disp_release}", "NEXUS_REPO_ROOT": str(ROOT),
               "NEXUS_RESEARCH_STATE_ROOT": str(ROOT / "data")}
        try:
            proc = subprocess.run([sys.executable, "-m", "nexus_agent_platform.research_engine_handoff", "health",
                                   "--since", RESEARCH_DURABLE_ACTIVATED_AT], cwd=str(disp_release), env=env,
                                  capture_output=True, text=True, timeout=40, check=False)
            parsed = json.loads((proc.stdout.strip().splitlines() or ["{}"])[-1])
            audit = parsed.get("data") if parsed.get("ok") else {"status": "FAIL", "error": parsed.get("error")}
        except (subprocess.TimeoutExpired, ValueError, OSError) as exc:
            audit = {"status": "FAIL", "error_class": type(exc).__name__}
    out["linkage"] = audit
    if audit.get("status") == "FAIL":
        reasons.append("LINKAGE_AUDIT_FAILED")
    reasons.extend(audit.get("reasons") or [])
    out["reasons"] = reasons
    out["status"] = "ATTENTION" if reasons else "PASS"
    return out


N8N_BASE = "http://nexus-app-services.tailb1e262.ts.net:5678"
N8N_CREDENTIAL_SERVICE = "nexus/credential.n8n.nexus_control.prod.v1"
N8N_CONTINUATION_WORKFLOWS = {"continuation": "nxDurableCont001", "department_handoff": "nxDeptHandoff001",
                              "approval_wait": "nxApprovalWait01", "retry_fallback": "nxRetryFallbk001"}
CONTINUATION_STATE = ROOT / "data/runtime/continuation/sweep_state.json"
CONTINUATION_STALE_SECONDS = 1200


def _keychain(service: str, account: str) -> str:
    proc = subprocess.run(["/usr/bin/security", "find-generic-password", "-s", service, "-a", account, "-w"],
                          capture_output=True, text=True, timeout=10, check=False)
    return proc.stdout.strip()


def _nexus_continuation() -> dict[str, Any]:
    """N8N_CONTINUATION_COST_GOVERNOR_R1 health: n8n service + Nexus->n8n connectivity + workflows + Cost Governor
    policy + the dispatcher continuation sweep's own counts. ATTENTION when any project failed/paused without a next action."""
    import plistlib
    import urllib.request as _ur
    out: dict[str, Any] = {}
    reasons: list[str] = []
    try:
        with urlopen(N8N_BASE + "/healthz", timeout=5) as response:
            out["n8n_service"] = "PASS" if json.loads(response.read(512) or b"{}").get("status") == "ok" else "FAIL"
    except Exception as exc:
        out["n8n_service"] = "FAIL"; out["n8n_service_error_class"] = type(exc).__name__
    token = api_key = ""
    try:
        token = _keychain(N8N_CREDENTIAL_SERVICE, "webhook_token")
        req = _ur.Request(N8N_BASE + "/webhook/nexus-durable-continuation", method="POST",
                          data=json.dumps({"action": "health", "request_id": "systems-tick"}).encode(),
                          headers={"Content-Type": "application/json", "X-Nexus-Webhook-Token": token})
        with _ur.urlopen(req, timeout=15) as response:
            body = json.loads(response.read(4096) or b"{}")
        out["n8n_nexus_connectivity"] = "PASS" if body.get("ok") and body.get("health") else "FAIL"
        out["continuation_policy_version"] = body.get("policy_version")
    except Exception as exc:
        out["n8n_nexus_connectivity"] = "FAIL"; out["n8n_connectivity_error_class"] = type(exc).__name__
    try:
        api_key = _keychain(N8N_CREDENTIAL_SERVICE, "api_key")
        req = _ur.Request(N8N_BASE + "/api/v1/workflows?limit=100", headers={"X-N8N-API-KEY": api_key})
        with _ur.urlopen(req, timeout=15) as response:
            listed = {w.get("id"): bool(w.get("active")) for w in json.loads(response.read(400_000)).get("data", [])}
        for name, wid in N8N_CONTINUATION_WORKFLOWS.items():
            out[name + "_workflow"] = "PASS" if listed.get(wid) else ("INACTIVE" if wid in listed else "MISSING")
    except Exception as exc:
        for name in N8N_CONTINUATION_WORKFLOWS:
            out[name + "_workflow"] = "UNKNOWN"
        out["n8n_api_error_class"] = type(exc).__name__
    finally:
        token = api_key = ""
    try:
        disp = plistlib.loads(DISPATCHER_PLIST.read_bytes())
        release = Path(str((disp.get("ProgramArguments") or ["", "", ""])[2])).parents[2]
        policy = json.loads((release / "config/nexus_cost_governor_policy.json").read_text(encoding="utf-8"))
        ok = policy.get("policy_version") == "NEXUS_CONTINUATION_POLICY_V1" and all(k in policy for k in ("budgets_usd", "providers", "ventures"))
        out["cost_governor"] = "PASS" if ok else "FAIL"
        out["cost_budgets_usd"] = policy.get("budgets_usd")
        out["dispatcher_release"] = release.name
    except Exception as exc:
        out["cost_governor"] = "FAIL"; out["cost_governor_error_class"] = type(exc).__name__
    try:
        state = json.loads(CONTINUATION_STATE.read_text(encoding="utf-8"))
        last = state.get("last_summary") or {}
        ran = datetime.fromisoformat(str(state.get("last_run_at")).replace("Z", "+00:00"))
        age = (datetime.now(timezone.utc) - ran).total_seconds()
        counts = last.get("counts") or {}
        out.update({"last_sweep_at": state.get("last_run_at"), "last_sweep_age_seconds": int(age), "last_sweep_n8n": last.get("n8n"),
                    "stuck_project_count": len(last.get("failed_without_next_action") or []),
                    "failed_without_next_action_count": len(last.get("failed_without_next_action") or []),
                    "budget_blocked_count": sum(1 for a in last.get("applied") or [] if a.get("decision") == "BUDGET_BLOCKED") + int(counts.get("budget_blocked") or 0),
                    "waiting_approval_count": int(last.get("waiting_approval") or 0),
                    "long_running_healthy_count": int(counts.get("long_running_healthy") or 0),
                    "governed_projects": int(counts.get("governed") or 0), "handoff_ready_count": int(counts.get("handoff_ready") or 0),
                    "automated_research_windows": sorted((state.get("automated_windows") or {}).keys())[-3:]})
        if age > CONTINUATION_STALE_SECONDS:
            reasons.append("CONTINUATION_SWEEP_STALE")
        if out["failed_without_next_action_count"]:
            reasons.append("FAILED_WITHOUT_NEXT_ACTION")
        if last.get("n8n") == "UNAVAILABLE":
            reasons.append("N8N_UNAVAILABLE_TO_SWEEP")
    except (OSError, ValueError, TypeError) as exc:
        out["continuation_sweep"] = "NO_STATE"; out["continuation_state_error_class"] = type(exc).__name__
        reasons.append("CONTINUATION_SWEEP_NOT_RUNNING")
    for key in ("n8n_service", "n8n_nexus_connectivity", "cost_governor"):
        if out.get(key) != "PASS":
            reasons.append(key.upper() + "_FAIL")
    for name in N8N_CONTINUATION_WORKFLOWS:
        if out.get(name + "_workflow") != "PASS":
            reasons.append(name.upper() + "_WORKFLOW_" + str(out.get(name + "_workflow")))
    out["reasons"] = reasons
    out["status"] = "ATTENTION" if reasons else "PASS"
    return out


def _durable_dispatch() -> dict[str, Any]:
    """Durable dispatcher service + queue health from its own per-run receipts
    (stdout JSON lines) and launchd state. Local reads only; no Supabase call.
    Service failure is reported as SERVICE health and never removes the
    durable_dispatch capability."""
    ld = _launchd(DISPATCHER_LABEL, 30)
    receipts: list[dict[str, Any]] = []
    try:
        for line in _tail_lines(DISPATCHER_LOG):
            try:
                receipts.append(json.loads(line))
            except ValueError:
                continue
    except OSError:
        pass
    last = receipts[-1] if receipts else {}
    run = last.get("run") or {}
    health = last.get("health") or {}
    status = last.get("status") or run.get("status")
    last_receipt_at = _iso_mtime(DISPATCHER_LOG)
    age = (datetime.now(timezone.utc) - datetime.fromisoformat(last_receipt_at)).total_seconds() if last_receipt_at else None
    ok_runs = [r for r in receipts if (r.get("run") or {}).get("status") == "OK"]
    failures = [r for r in receipts if r.get("status") == "BUDGET_EXHAUSTED"]
    try:   # an empty (rotated) error log carries no failure
        error_log_at = _iso_mtime(DISPATCHER_ERROR_LOG) if DISPATCHER_ERROR_LOG.stat().st_size > 0 else None
    except OSError:
        error_log_at = None
    last_failure = max(filter(None, [error_log_at] + [r.get("at") for r in failures]), default=None)
    fresh = age is not None and age <= DISPATCHER_STALE_SECONDS
    if not ld.get("loaded") or not fresh:
        service = "FAILED"
    elif status == "OK" and str(ld.get("last_exit")) in {"0", "(never exited)", "None"}:
        service = "HEALTHY"
    else:
        service = "DEGRADED"
    queue = "ATTENTION" if int(health.get("expired_leases") or 0) > 0 else ("HEALTHY" if health else "UNKNOWN")
    return {"status": {"HEALTHY": "PASS", "DEGRADED": "ATTENTION"}.get(service, "FAIL"),
            "capability": "durable_dispatch", "capability_affected": False,
            "service_health": service, "queue_health": queue, "launchd": ld,
            "last_receipt_status": status, "last_receipt_age_seconds": int(age) if age is not None else None,
            "blocked_job_count": health.get("blocked"), "ready_job_count": last.get("ready"),
            "claimable_job_count": run.get("jobs_claimable"), "running_job_count": health.get("running"),
            "expired_leases": health.get("expired_leases"),
            "requests_used": run.get("requests_used"), "response_bytes": run.get("response_bytes"),
            "last_success": (ok_runs[-1].get("health") or {}).get("generated_at") if ok_runs else None,
            "last_failure": last_failure}


def _node_probe(env_id: str) -> dict[str, Any]:
    spec = NODE_PROBES[env_id]
    try:
        proc = subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", spec["alias"], spec["script"]],
                              capture_output=True, text=True, timeout=30, check=False)
    except subprocess.TimeoutExpired:
        return {"status": "DEGRADED", "connection": "TIMEOUT", "transport": "TAILSCALE"}
    facts = dict(line.split("=", 1) for line in proc.stdout.splitlines() if "=" in line)
    if proc.returncode != 0 or not facts.get("HOST"):
        return {"status": "DEGRADED", "connection": "CONNECTION_UNAVAILABLE", "transport": "TAILSCALE",
                "ssh_exit": proc.returncode}
    facts["connection"] = "ONLINE"
    facts["transport"] = "TAILSCALE"
    if env_id == "ORACLE":
        ok = all(facts.get(k) == "active" for k in ("HERMES", "NOVA", "FIREWALLD")) and facts.get("SSHD_PASSWORD") == "no"
    else:
        ok = (facts.get("DOCKER") == "active" and facts.get("UFW") == "active" and facts.get("FAIL2BAN") == "active"
              and facts.get("SSHD_ROOT") == "no" and facts.get("SSHD_PASSWORD") == "no"
              and int(facts.get("DISK_PCT") or 0) < 85 and int(facts.get("MEM_AVAIL_PCT") or 0) >= 10)
        ok = ok and not any(v.split("/")[0] != "running" or v.endswith("/unhealthy")
                            for k, v in facts.items() if k.startswith("CONTAINER_"))
        ok = ok and facts.get("HTTP_POSTIZ", "401") in {"200", "401"} and facts.get("HTTP_N8N", "200") == "200"
    facts["status"] = "PASS" if ok and facts.get("TAILSCALE") == "Running" else "DEGRADED"
    return facts


def _record_node_health(checks: dict[str, Any]) -> list[str]:
    """Append node rows to the existing S1 health_checks table (same 8-column
    shape as systems_engine_s1._health). TRANSPORT is recorded separately from
    SERVICE/ENVIRONMENT so connection loss never reads as capability loss."""
    stamp = _now()
    rows: list[tuple] = []
    for env_id in NODE_PROBES:
        c = checks.get(f"node_{env_id.lower()}") or {}
        conn = c.get("connection", "UNKNOWN")
        rows.append((env_id, None, "TRANSPORT", "HEALTHY" if conn == "ONLINE" and c.get("TAILSCALE") == "Running" else "DEGRADED",
                     {"transport": "TAILSCALE", "connection": conn, "tailscale": c.get("TAILSCALE"),
                      "capability_affected": False}, [f"{env_id.lower()}:tailscale-ssh"]))
        if conn != "ONLINE":
            continue
        if env_id == "ORACLE":
            for svc, key in (("hermes-0225", "HERMES"), ("nova-r54", "NOVA"), ("oracle-host-control", "HOST_CONTROL"), ("searxng", "SEARXNG")):
                rows.append((env_id, svc, "SERVICE", "HEALTHY" if c.get(key) == "active" else "DEGRADED",
                             {"state": c.get(key), "source": "maintenance_tick"}, [f"oracle:systemd:{svc}"]))
            listening = set(filter(None, (c.get("BRIDGE_LISTEN") or "").split(",")))
            for label, b in ((checks.get("oracle_bridges") or {}).get("bridges") or {}).items():
                on_oracle = str(b["port"]) in listening
                rows.append((env_id, f"bridge-{label}", "TRANSPORT",
                             "HEALTHY" if b["transport"] == "TAILSCALE" and on_oracle else "DEGRADED",
                             {"port": b["port"], "transport": b["transport"], "oracle_loopback_listener": on_oracle,
                              "started_at": b.get("started_at"), "capability_affected": False},
                             [f"mac:ssh-reverse:{b['port']}", "oracle:ss-listen"]))
        else:
            rows.append((env_id, None, "ENVIRONMENT", "HEALTHY" if c.get("status") == "PASS" else "DEGRADED",
                         {k: c.get(k) for k in ("DOCKER", "UFW", "FAIL2BAN", "SSHD_ROOT", "SSHD_PASSWORD", "TAILSCALE")},
                         ["contabo:ssh-readonly"]))
            rows.append((env_id, None, "RESOURCE_CAPACITY",
                         "HEALTHY" if int(c.get("DISK_PCT") or 0) < 85 and int(c.get("MEM_AVAIL_PCT") or 0) >= 10 else "DEGRADED",
                         {k: c.get(k) for k in ("DISK_PCT", "MEM_AVAIL_PCT", "LOAD1", "CPUS")}, ["contabo:load-memory-disk"]))
            if "POSTIZ_AUTH_API" in c:
                g = checks.get("postiz_governed") or {}
                api_ok = c.get("POSTIZ_AUTH_API") == "200"
                active = int(c.get("POSTIZ_INTEGRATIONS_ACTIVE") or 0)
                rows.append((env_id, "postiz-api", "SERVICE", "HEALTHY" if api_ok else "DEGRADED",
                             {"authenticated_http_status": c.get("POSTIZ_AUTH_API"), "source": "maintenance_tick"},
                             ["contabo:postiz-public-api:integrations"]))
                rows.append((env_id, "postiz-social-auth", "AUTHORIZATION",
                             "HEALTHY" if api_ok and active > 0 else "DEGRADED",
                             {"capability": "social_distribution_postiz",
                              "CAPABILITY": "PRESENT" if api_ok and g.get("provider_router") == "PRESENT" else "DEGRADED",
                              "AUTHORIZATION": "AUTHORIZED" if active > 0 else "DEGRADED",
                              "capability_affected": False,
                              "connected_accounts": active, "connected_providers": c.get("POSTIZ_INTEGRATION_PROVIDERS") or "",
                              "providers_app_configured": c.get("POSTIZ_PROVIDERS_CONFIGURED") or "",
                              "frontend_scheme": c.get("POSTIZ_FRONTEND_SCHEME"),
                              "provider_router": g.get("provider_router"), "live_publish_enabled": False,
                              "last_success": g.get("last_success"), "last_failure": g.get("last_failure")},
                             ["contabo:postiz-public-api:integrations", "mac:data/governed/distribution_provider_receipts.jsonl"]))
            if "POSTIZ_IMAGE" in c:
                origin = c.get("POSTIZ_META_OAUTH_ORIGIN") or ""
                prov = {p: c.get(f"POSTIZ_PROVIDER_{p.upper()}") for p in POSTIZ_META_PROVIDERS}
                issues = []
                if c.get("POSTIZ_IMAGE", "").rsplit(":", 1)[-1] != POSTIZ_EXPECTED_VERSION:
                    issues.append("POSTIZ_VERSION_DRIFT")
                if c.get("POSTIZ_IMAGE_MATCHES_MANIFEST") != "YES":
                    issues.append("POSTIZ_IMAGE_NOT_MANIFEST_IMAGE")
                issues += [f"PROVIDER_OVERRIDE_{v or 'UNKNOWN'}:{p}" for p, v in prov.items() if v != "OVERRIDE"]
                if not origin:
                    issues.append("POSTIZ_META_OAUTH_ORIGIN_MISSING")
                elif origin != POSTIZ_META_OAUTH_ORIGIN_EXPECTED:
                    issues.append("CALLBACK_ORIGIN_UNEXPECTED")
                rows.append((env_id, "postiz-meta-oauth", "CONFIGURATION", "DEGRADED" if issues else "HEALTHY",
                             {"expected_version": POSTIZ_EXPECTED_VERSION, "image": c.get("POSTIZ_IMAGE"),
                              "image_matches_manifest": c.get("POSTIZ_IMAGE_MATCHES_MANIFEST"),
                              "provider_overrides": prov, "meta_oauth_origin": origin or None,
                              "effective_callbacks": [f"{origin or POSTIZ_PRIVATE_ORIGIN}/integrations/social/{p}"
                                                      for p in POSTIZ_META_PROVIDERS],
                              "issues": issues, "capability_affected": False},
                             ["contabo:docker-inspect", "contabo:postiz/overrides/v2.25.3/MANIFEST.json"]))
            if "POSTIZ_TIKTOK_SCOPES" in c:
                t_origin = c.get("POSTIZ_TIKTOK_OAUTH_ORIGIN") or ""
                scopes = [x for x in (c.get("POSTIZ_TIKTOK_SCOPES") or "").split(",") if x]
                t_issues = []
                if c.get("POSTIZ_IMAGE", "").rsplit(":", 1)[-1] != POSTIZ_EXPECTED_VERSION:
                    t_issues.append("POSTIZ_VERSION_DRIFT")
                if c.get("POSTIZ_IMAGE_MATCHES_MANIFEST") != "YES":
                    t_issues.append("POSTIZ_IMAGE_NOT_MANIFEST_IMAGE")
                if c.get("POSTIZ_PROVIDER_TIKTOK") != "OVERRIDE":
                    t_issues.append(f"PROVIDER_OVERRIDE_{c.get('POSTIZ_PROVIDER_TIKTOK') or 'UNKNOWN'}:tiktok")
                if not t_origin:
                    t_issues.append("POSTIZ_TIKTOK_OAUTH_ORIGIN_MISSING")
                elif t_origin != POSTIZ_META_OAUTH_ORIGIN_EXPECTED:
                    t_issues.append("CALLBACK_ORIGIN_UNEXPECTED")
                if c.get("POSTIZ_TIKTOK_REDIRECT_SITES_USING_ORIGIN") != "2":
                    t_issues.append("TIKTOK_REDIRECT_NOT_OVERRIDDEN")
                if tuple(scopes) != POSTIZ_TIKTOK_EXPECTED_SCOPES:
                    t_issues.append("TIKTOK_SCOPES_UNEXPECTED")
                t_issues += [f"TIKTOK_FORBIDDEN_SCOPE:{x}" for x in scopes if x in POSTIZ_TIKTOK_FORBIDDEN_SCOPES]
                effective = (f"{t_origin}/integrations/social/tiktok" if t_origin and c.get("POSTIZ_TIKTOK_REDIRECT_SITES_USING_ORIGIN") == "2"
                             else f"{POSTIZ_PRIVATE_ORIGIN}/integrations/social/tiktok")
                rows.append((env_id, "postiz-tiktok-oauth", "CONFIGURATION", "DEGRADED" if t_issues else "HEALTHY",
                             {"expected_version": POSTIZ_EXPECTED_VERSION, "image": c.get("POSTIZ_IMAGE"),
                              "provider_override": c.get("POSTIZ_PROVIDER_TIKTOK"), "tiktok_oauth_origin": t_origin or None,
                              "requested_scopes": scopes, "video_publish_requested": "video.publish" in scopes,
                              "direct_post_possible": "video.publish" in scopes,
                              "third_party_redirect": "redirectmeto.com" in effective,
                              "effective_callback": effective, "issues": t_issues, "capability_affected": False},
                             ["contabo:docker-exec:tiktok.provider.js", "contabo:postiz/overrides/v2.25.3/MANIFEST.json"]))
            b = checks.get("postiz_oauth_bounce")
            if isinstance(b, dict) and b.get("status"):
                rows.append((env_id, "postiz-oauth-bounce", "SERVICE",
                             "HEALTHY" if b.get("status") == "PASS" else "DEGRADED",
                             {k: b.get(k) for k in ("status", "origin", "callback_pages", "unrelated_paths")}
                             | {"capability_affected": False},
                             [f"public:{POSTIZ_META_OAUTH_ORIGIN_EXPECTED}"]))
            for svc, key, ok_codes in (("postiz-http", "HTTP_POSTIZ", {"200", "401"}), ("n8n-http", "HTTP_N8N", {"200"})):
                if key in c:
                    rows.append((env_id, svc, "SERVICE", "HEALTHY" if c.get(key) in ok_codes else "DEGRADED",
                                 {"http_status": c.get(key), "note": "401 = reachable, auth-gated (expected without key)" if svc == "postiz-http" else None,
                                  "app_data_pct": c.get("APP_DATA_PCT"), "last_backup": c.get("LAST_BACKUP")},
                                 [f"contabo:{svc}"]))
            for k, v in c.items():
                if k.startswith("CONTAINER_"):
                    rows.append((env_id, k.removeprefix("CONTAINER_"), "SERVICE",
                                 "HEALTHY" if v.startswith("running") and not v.endswith("/unhealthy") else "DEGRADED",
                                 {"container_state": v}, ["contabo:docker"]))
    d = checks.get("durable_dispatch") or {}
    if d.get("service_health"):
        rows.append(("MAC_MINI", "durable-dispatcher", "SERVICE",
                     {"FAILED": "DEGRADED"}.get(d["service_health"], d["service_health"]),
                     {k: d.get(k) for k in ("capability", "capability_affected", "service_health", "queue_health",
                                            "blocked_job_count", "claimable_job_count", "ready_job_count",
                                            "last_success", "last_failure", "last_receipt_status",
                                            "last_receipt_age_seconds", "requests_used")},
                     ["mac:launchctl:" + DISPATCHER_LABEL, "mac:reports/runtime/durable_dispatcher.log"]))
    ids = []
    with sqlite3.connect(SYSTEMS_DB, timeout=5) as con:
        con.execute("PRAGMA busy_timeout=5000")
        for env_id, svc, ctype, state, payload, evidence in rows:
            cid = "health_" + uuid.uuid4().hex
            con.execute("INSERT INTO health_checks VALUES(?,?,?,?,?,?,?,?)",
                        (cid, env_id, svc, ctype, state, stamp, json.dumps(evidence), json.dumps(payload, sort_keys=True)))
            ids.append(cid)
    return ids


# Per-check budgets (seconds). Independent read-only checks run concurrently so
# one slow probe cannot starve the rest; a check that overruns is recorded as
# TIMEOUT with its measured duration and the tick still persists a receipt.
CHECK_BUDGETS = {
    "systems_s1": 10, "systems_sqlite": 20, "nexus_mcp": 60, "research_mcp": 50,
    "research_http": 10, "research_workflow": 75, "research_scheduler": 15,
    "systems_work": 45, "production_drift": 45,
    "node_contabo_app_services": 35, "node_oracle": 35, "oracle_bridges": 20,
    "durable_dispatch": 15, "postiz_governed": 10, "postiz_oauth_bounce": 30,
    "nova_research_notifications": 30,
    "research_quality_gate": 15,
    "research_durable_path": 45,
    "nexus_continuation": 45,
}
CONTINUATION_BUDGET_SECONDS = 60


def _run_checks() -> tuple[dict[str, Any], dict[str, int]]:
    import concurrent.futures as cf
    import time as _time
    # SQLite integrity runs alone first: on this spinning disk quick_check takes
    # ~1s uncontended but >20s when competing with the concurrent probes.
    s0 = _time.monotonic()
    sqlite_result = _sqlite_check(SYSTEMS_DB)
    if sqlite_result.get("error_class") == "OperationalError":
        sqlite_result["status"] = "DB_BUSY"
    pre = {"systems_sqlite": (sqlite_result, int((_time.monotonic() - s0) * 1000))}
    fns = {
        "systems_s1": lambda: _s1_health(),
        "nexus_mcp": lambda: asyncio.run(_bounded(_mcp_snapshot(), MCP_SNAPSHOT_DEADLINE_SECONDS)),
        "research_mcp": lambda: asyncio.run(_bounded(_research_mcp_snapshot(), MCP_SNAPSHOT_DEADLINE_SECONDS)),
        "research_http": lambda: _http_health(RESEARCH_HEALTH),
        "research_workflow": _workflow_snapshot,
        "research_scheduler": lambda: _launchd("com.nexus.research-r10-autonomy", 300),
        "systems_work": _pending_systems_work,
        "production_drift": _manifest_drift,
        "node_contabo_app_services": lambda: _node_probe("CONTABO_APP_SERVICES"),
        "node_oracle": lambda: _node_probe("ORACLE"),
        "oracle_bridges": _oracle_bridges,
        "durable_dispatch": _durable_dispatch,
        "postiz_governed": _postiz_governed,
        "postiz_oauth_bounce": _postiz_oauth_bounce,
        "nova_research_notifications": _nova_research_notifications,
        "research_quality_gate": _research_quality_gate,
        "research_durable_path": _research_durable_path,
        "nexus_continuation": _nexus_continuation,
    }
    started: dict[str, float] = {}
    durations: dict[str, int] = {k: v[1] for k, v in pre.items()}
    checks: dict[str, Any] = {k: v[0] for k, v in pre.items()}
    pool = cf.ThreadPoolExecutor(max_workers=len(fns), thread_name_prefix="systick")

    def timed(name: str, fn: Any) -> Any:
        started[name] = _time.monotonic()
        try:
            return fn()
        finally:
            durations[name] = int((_time.monotonic() - started[name]) * 1000)

    futures = {name: pool.submit(timed, name, fn) for name, fn in fns.items()}
    t0 = _time.monotonic()
    for name, fut in futures.items():
        remaining = CHECK_BUDGETS[name] - (_time.monotonic() - t0)
        try:
            checks[name] = fut.result(timeout=max(0.1, remaining))
        except cf.TimeoutError:
            checks[name] = {"status": "TIMEOUT", "budget_seconds": CHECK_BUDGETS[name]}
            durations.setdefault(name, int(CHECK_BUDGETS[name] * 1000))
        except Exception as exc:  # never persist exception text
            checks[name] = {"status": "FAIL", "error_class": type(exc).__name__}
    pool.shutdown(wait=False, cancel_futures=True)  # hung probe threads are abandoned; main() hard-exits
    return checks, durations


def collect() -> dict[str, Any]:
    checks, durations = _run_checks()
    failures = [name for name, check in checks.items()
                if check.get("status") in {"FAIL", "ATTENTION", "TIMEOUT", "DB_BUSY"}]
    degraded_research = checks["research_workflow"].get("status") not in {"PASS", "HEALTHY"}
    stale_paused = (checks["research_workflow"].get("oldest_paused_age_hours") or 0) > 24
    checks["recovery_needed"] = bool(failures or stale_paused)
    checks["recovery_needed_reason_count"] = len(failures) + int(stale_paused)
    checks["research_degradation_observed"] = degraded_research
    # Continuation needs the Systems DB plus an initialized, authenticated MCP
    # session exposing the systems_job_* tools; it does not need the heavy
    # systems_status snapshot or the auth-gated :18770 health route.
    core_ready = (checks["systems_s1"].get("status") in {"PASS", "AUTH_REQUIRED"}
                  and checks["systems_sqlite"].get("status") == "PASS"
                  and checks["nexus_mcp"].get("protocol_initialized") is True
                  and checks["nexus_mcp"].get("systems_read_write_surface") is True)
    if core_ready:
        import concurrent.futures as cf
        cpool = cf.ThreadPoolExecutor(max_workers=1, thread_name_prefix="systick-cont")
        try:
            continuation = cpool.submit(_resume_one_same_job).result(timeout=CONTINUATION_BUDGET_SECONDS)
        except cf.TimeoutError:
            continuation = {"status": "TIMEOUT", "attempted": None, "budget_seconds": CONTINUATION_BUDGET_SECONDS}
        except Exception as exc:
            continuation = {"status": "FAIL", "error_class": type(exc).__name__, "attempted": None}
        cpool.shutdown(wait=False, cancel_futures=True)
    else:
        continuation = {"status": "SKIPPED_CORE_HEALTH"}
    try:
        node_health_ids = _record_node_health(checks)
    except sqlite3.Error as exc:
        node_health_ids = []
        checks["node_health_persist"] = {"status": "DB_BUSY", "error_class": type(exc).__name__}
    return {"schema_version": "systems.maintenance-tick.v2", "checked_at": _now(),
            "status": "ATTENTION" if failures or stale_paused else "PASS",
            "ai_usage": "NONE", "automated_recovery": continuation.get("attempted", False),
            "mutation_performed": bool(continuation.get("attempted", False)), "continuation": continuation,
            "check_durations_ms": durations, "node_health_check_ids": node_health_ids, "checks": checks}


def persist(report: dict[str, Any]) -> None:
    receipt_id = "systick_" + uuid.uuid4().hex
    with sqlite3.connect(SYSTEMS_DB, timeout=5) as con:
        con.execute("PRAGMA busy_timeout=5000")
        con.execute("INSERT INTO receipts(receipt_id,request_id,receipt_type,created_at,payload) VALUES(?,?,?,?,?)",
                    (receipt_id, receipt_id, "SYSTEMS_MAINTENANCE_TICK", report["checked_at"],
                     json.dumps(report, sort_keys=True, separators=(",", ":"))))


def _watchdog(signum: int, frame: Any) -> None:
    # Last-resort guard: never let one tick outlive its interval and silently
    # block launchd from starting the next one.
    print(json.dumps({"status": "FAIL", "error_class": "TickWatchdogTimeout",
                      "bounded_seconds": TICK_WATCHDOG_SECONDS, "ai_usage": "NONE",
                      "mutation_performed": False}, sort_keys=True), flush=True)
    os._exit(2)


TICK_LOCK = SYSTEMS_DB.parent / "maintenance_tick.lock"


def main() -> int:
    import fcntl
    import signal
    # Overlap guard (same flock pattern as systems_workflow.py): launchd never
    # starts a second instance of this label, and this also blocks manual runs.
    TICK_LOCK.parent.mkdir(parents=True, exist_ok=True)
    lock = open(TICK_LOCK, "a+")
    try:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print(json.dumps({"status": "SKIPPED_TICK_ALREADY_RUNNING", "ai_usage": "NONE",
                          "mutation_performed": False}, sort_keys=True))
        return 0
    signal.signal(signal.SIGALRM, _watchdog)
    signal.alarm(TICK_WATCHDOG_SECONDS)
    # SIGALRM cannot run while the main thread is blocked in C-level disk I/O
    # (observed: >320s under spinning-disk I/O starvation). A daemon timer thread
    # still gets the GIL because blocking reads/lock waits release it.
    import threading
    watchdog = threading.Timer(TICK_WATCHDOG_SECONDS + 5, _watchdog, args=(0, None))
    watchdog.daemon = True
    watchdog.start()
    try:
        report = collect()
        persist(report)
        print(json.dumps({"status": report["status"], "checked_at": report["checked_at"],
                          "ai_usage": "NONE", "mutation_performed": report["mutation_performed"],
                          "check_names": sorted(report["checks"]),
                          "durations_ms": report["check_durations_ms"],
                          "recovery_needed": report["checks"]["recovery_needed"]}, sort_keys=True), flush=True)
        code = 0
    except Exception as exc:
        print(json.dumps({"status": "FAIL", "error_class": type(exc).__name__,
                          "ai_usage": "NONE", "mutation_performed": False}, sort_keys=True), flush=True)
        code = 1
    # Hard exit: abandoned probe threads (e.g. a silent MCP stream) must not keep
    # the process alive and block the next launchd interval.
    os._exit(code)


if __name__ == "__main__":
    raise SystemExit(main())
