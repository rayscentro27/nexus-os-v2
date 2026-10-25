"""Capability view built from the tools the live Nova MCP session discovers."""
from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from nova.capability_authority import capability_record

ROOT = Path(os.environ.get("NOVA_REPO_ROOT") or os.environ.get("NEXUS_REPO_ROOT")
            or Path(__file__).resolve().parents[2])
REGISTRY_PATH = ROOT / "data/runtime/nova_live_capability_registry.json"
_CACHE: dict[str, Any] = {"at": 0.0, "tools": [], "count": 0, "error": None}
_CACHE_TTL = 45.0


def _discover(force: bool = False) -> tuple[list[dict], int, str | None]:
    if not force and time.monotonic() - float(_CACHE["at"]) < _CACHE_TTL:
        return _CACHE["tools"], int(_CACHE["count"]), _CACHE["error"]
    try:
        from nova.nexus_mcp_status import list_mcp_tools
        tools, count = list_mcp_tools()
        _CACHE.update(at=time.monotonic(), tools=tools, count=count, error=None)
    except Exception as exc:
        _CACHE.update(at=time.monotonic(), tools=[], count=0, error=type(exc).__name__)
    return _CACHE["tools"], int(_CACHE["count"]), _CACHE["error"]


def _tool_set(tools: list[dict]) -> set[str]:
    return {str(row.get("name")) for row in tools if isinstance(row, dict) and row.get("name")}


def _hermes_runtime_view() -> dict[str, Any]:
    """Read safe profile metadata from the same Hermes container Nova invokes."""
    script = r'''import json,os,subprocess,yaml
d=yaml.safe_load(open('/opt/data/profiles/nova_nexus/config.yaml'))
os.environ.update({"HERMES_HOME":"/opt/data/profiles/nova_nexus","HERMES_PROFILE":"nova_nexus"})
env={**os.environ,"HERMES_HOME":"/opt/data/profiles/nova_nexus","HERMES_PROFILE":"nova_nexus"}
r=subprocess.run(["/opt/hermes/.venv/bin/hermes","tools","list","--platform","cli"],capture_output=True,text=True,env=env,timeout=20)
enabled=[]; disabled=[]
for line in r.stdout.splitlines():
 parts=line.strip().split()
 if len(parts)>=3 and parts[0] in {"✓","✗"} and parts[1] in {"enabled","disabled"}:
  (enabled if parts[1]=="enabled" else disabled).append(parts[2])
probe=subprocess.run(["/opt/hermes/.venv/bin/hermes","mcp","test","you-com"],capture_output=True,text=True,env=env,timeout=25)
connected="Connected" in probe.stdout and probe.returncode==0
metricool={"handshake":"NOT_TESTED","tool_count":0}
if (d.get("mcp_servers") or {}).get("metricool_goclear",{}).get("enabled",True):
 mc=subprocess.run(["/opt/hermes/.venv/bin/hermes","mcp","test","metricool_goclear"],capture_output=True,text=True,env=env,timeout=40)
 import re
 match=re.search(r"Tools discovered:\s*(\d+)",mc.stdout)
 metricool={"handshake":"PASS" if "Connected" in mc.stdout and mc.returncode==0 else "FAIL","tool_count":int(match.group(1)) if match else 0}
try:
 from hermes_cli.config import load_config
 from tools.approval import _get_approval_mode
 from agent.file_safety import get_safe_write_roots
 from agent.image_gen_registry import get_active_provider
 from tools.video_generation_tool import check_video_generation_requirements
 c=load_config() or {}; terminal=c.get("terminal") or {}; approvals=c.get("approvals") or {}
 provider=get_active_provider()
 image_available=bool(provider and provider.is_available())
 video_available=bool(check_video_generation_requirements())
 runtime={"approval_mode":_get_approval_mode(),"single_query_approval_mode":approvals.get("single_query_mode","deny"),"cron_approval_mode":approvals.get("cron_mode","deny"),"terminal_backend":terminal.get("backend","local"),"terminal_cwd":terminal.get("cwd","."),"command_allowlist_configured":bool(c.get("command_allowlist")),"safe_write_roots":sorted(get_safe_write_roots()),"file_read_max_chars":c.get("file_read_max_chars"),"code_execution_mode":(c.get("code_execution") or {}).get("mode","project"),"image_provider_available":image_available,"video_provider_available":video_available,"voice_enabled":bool((c.get("voice") or {}).get("enabled")),"routines_enabled":bool((d.get("routines") or {}).get("enabled"))}
except Exception as exc:
 runtime={"inspection_error":type(exc).__name__}
print(json.dumps({"browser_enabled":bool((d.get("browser") or {}).get("enabled")),"mcp_servers":{k:bool(v.get("enabled",True)) for k,v in (d.get("mcp_servers") or {}).items()},"native_tools_enabled":enabled,"native_tools_disabled":disabled,"tool_discovery_exit":r.returncode,"you_com_handshake":"PASS" if connected else "FAIL","you_com_tool_count":2 if connected else 0,"metricool":metricool,"runtime":runtime}))'''
    try:
        result = subprocess.run(["podman", "exec", "nexus-hermes-0206", "/opt/hermes/.venv/bin/python", "-c", script],
                               capture_output=True, text=True, timeout=50, check=False)
        if result.returncode == 0:
            return json.loads(result.stdout)
    except (OSError, subprocess.SubprocessError, ValueError):
        pass
    return {"status": "UNAVAILABLE"}


def _capability_inventory(hermes_view: dict[str, Any], toolset: list[str],
                          mcp: dict[str, Any], google: dict[str, Any]) -> list[dict[str, Any]]:
    """Describe the deployed executor surface without equating installed with usable."""
    enabled = set(hermes_view.get("native_tools_enabled", []))
    disabled = set(hermes_view.get("native_tools_disabled", []))
    active = set(toolset)
    runtime = hermes_view.get("runtime", {})
    mcp_servers = hermes_view.get("mcp_servers", {})

    def row(name: str, category: str, source: str, installed: bool,
            configured: bool, profile_enabled: bool, active_now: bool,
            safe: bool, approval: str, boundary: str, blocker: str | None,
            health: str | None = None, *, authorized: bool | None = True,
            read_authority: str = "NONE", write_authority: str = "NONE",
            cost_class: str = "ZERO_INCREMENTAL_COST",
            consequence_class: str = "INTERNAL_REVERSIBLE",
            last_known_good: bool | None = None,
            last_verified_at: str | None = None,
            last_error: str | None = None) -> dict[str, Any]:
        runtime_health = ("PASS" if active_now else "UNKNOWN") if health is None else str(health)
        available = bool(installed and configured and authorized is not False)
        if blocker in {"AUTH_REQUIRED", "NOT_AUTHORIZED"}:
            authorized = False
        authority = capability_record(
            name=name, installed=installed, configured=configured, authorized=authorized,
            available=available, runtime_health=runtime_health,
            read_authority=read_authority, write_authority=write_authority,
            cost_class=cost_class, consequence_class=consequence_class,
            boundary=boundary, last_known_good=last_known_good,
            last_verified_at=last_verified_at, last_error=last_error or blocker,
        )
        state = authority["status"]
        return {"capability": name, "category": category, "source": source,
                "installed": installed, "configured": configured,
                "available_in_wider_hermes_profile": profile_enabled,
                "active_in_live_nova_session": active_now,
                "safe_for_nova": safe, "approval_requirement": approval,
                "execution_boundary": boundary, "status": state,
                "health": runtime_health, "current_blocker": blocker,
                "authority": authority}

    native = lambda key: key in enabled or key in disabled
    profile = lambda key: key in enabled
    active_mcp = lambda key: bool(mcp_servers.get(key)) and key in active
    browser_profile = bool(hermes_view.get("browser_enabled"))
    terminal_configured = bool(runtime.get("terminal_backend"))
    image_provider = bool(runtime.get("image_provider_available"))
    video_provider = bool(runtime.get("video_provider_available"))
    registry = [
        row("web_search", "WEB", "Hermes native web", native("web"), profile("web"), profile("web"), "web" in active, True, "READ_ONLY", "Public web search and page reading only", None, "PASS" if "web" in active else "UNKNOWN", read_authority="PUBLIC_WEB_READ", write_authority="NONE", last_known_good=True if "web" in active else None),
        row("browser_automation", "BROWSER", "Hermes native browser", native("browser"), False, browser_profile, "browser" in active, False, "OWNER_APPROVAL_FOR_INTERACTION", "Interactive account actions remain gated; public search/page reading is separately available through web_search", "Interactive browser toolset is not exposed to Nova"),
        row("file_document_pdf", "FILES_AND_DOCUMENTS", "Hermes native file tools", native("file"), False, profile("file"), "file" in active, False, "Use Nexus path-scoped workspace tools", "Unrestricted Hermes profile filesystem is not exposed to Nova", "A separate Nexus workspace tool provides bounded file access"),
        row("terminal", "LOCAL_EXECUTION", "Hermes native terminal", native("terminal"), False, profile("terminal"), "terminal" in active, False, "Use bounded Nexus Systems/Coding assignments", "Unrestricted Hermes shell is not exposed", "A separate Nexus bounded executor is available"),
        row("code_execution", "CODE_EXECUTION", "Hermes native execute_code", native("code_execution"), False, profile("code_execution"), "code_execution" in active, False, "Use bounded Nexus coding assignments", f"Hermes execute_code mode={runtime.get('code_execution_mode','UNKNOWN')}; single-query approval policy={runtime.get('single_query_approval_mode','deny')}", "A separate Nexus bounded coding executor is available"),
        row("image_generation", "IMAGE", "Hermes image_gen provider", native("image_gen"), image_provider, profile("image_gen"), "image_gen" in active, False, "Provider/cost approval required before generation", "Hermes image provider adapter", "No active image provider is configured/available" if not image_provider else "Image generation is outside Nova's active allowlist"),
        row("video_generation", "VIDEO", "Hermes video_gen provider", native("video_gen"), video_provider, profile("video_gen"), "video_gen" in active, False, "Provider/cost approval required before generation", "Hermes video generation provider adapter", "Video toolset is disabled and no provider is available" if not video_provider else "Video generation is outside Nova's active allowlist"),
        row("audio_speech", "AUDIO_AND_SPEECH", "Hermes TTS/STT", native("tts") or native("stt"), bool(runtime.get("voice_enabled")), profile("tts") or profile("stt"), bool(active.intersection({"tts", "stt"})), False, "Provider/cost approval required", "Hermes speech provider", "Voice is disabled and TTS/STT are outside Nova's active allowlist"),
        row("vision", "VISION", "Hermes native vision", native("vision"), True, profile("vision"), "vision" in active, False, "Read-only input; provider/resource policy applies", "Hermes vision model/provider", "Vision is outside Nova's active allowlist"),
        row("remote_execution", "REMOTE_EXECUTION", "Nexus governed worker plane", "nexus_assign_research" in set(mcp.get("tools", [])), True, True, mcp.get("handshake") == "PASS", True, "Nexus job governance and department policy", "Durable Nexus MCP actions and department workers", None if mcp.get("handshake") == "PASS" else "Nexus MCP unavailable", mcp.get("handshake")),
        row("notifications", "NOTIFICATIONS", "Nexus Nova proactive delivery", True, True, True, True, True, "Governed event delivery; external content follows notification policy", "Nexus durable event → Nova Telegram delivery", None, "PREVIOUS_DELIVERY_VERIFIED"),
        row("scheduled_actions", "SCHEDULING", "Hermes cron/routines", native("cronjob"), bool((hermes_view.get("runtime") or {}).get("routines_enabled")), profile("cronjob"), "cronjob" in active, False, "Owner approval required; cron approval policy is deny", "Hermes cron scheduler", "Cronjob tool is outside Nova allowlist; routines are disabled"),
        row("skills", "SKILLS", "Hermes skills", native("skills"), native("skills"), profile("skills"), "skills" in active, False, "Approval required for install/configuration changes", "Hermes profile skill registry", "Skills are outside Nova's active allowlist"),
        row("nexus_mcp", "MCP", "Configured Nexus MCP endpoint", True, True, True, active_mcp("nexus_mcp_remote"), True, "Per-tool Nexus read/action governance", "Nexus MCP bridge and durable department workers", None if mcp.get("handshake") == "PASS" else "Nexus MCP handshake failed", mcp.get("handshake")),
        row("you_com_mcp", "MCP", "Configured You.com MCP endpoint", True, True, True, active_mcp("you-com"), True, "Provider policy and query bounds", "Hermes MCP client", None if hermes_view.get("you_com_handshake") == "PASS" else "You.com handshake failed", hermes_view.get("you_com_handshake")),
        row("metricool_mcp", "MCP", "Configured Metricool GoClear MCP endpoint", True, bool(mcp_servers.get("metricool_goclear")), bool(mcp_servers.get("metricool_goclear")), active_mcp("metricool_goclear"), False, "Owner approval before scheduling or publishing; read-only analytics can be considered separately", "Hermes OAuth MCP; exposes analytics plus scheduled-post mutations", "Connected with 9 tools but outside Nova allowlist; mutating post-scheduling tools require governed approval", (hermes_view.get("metricool") or {}).get("handshake")),
        row("google_workspace", "GOOGLE", "Google Workspace through canonical Nexus MCP adapter", bool(google.get("tools")), bool(google.get("tools")), True, bool(google.get("tools")) and mcp.get("handshake") == "PASS", True, "Read/write operations use per-operation MCP receipts and consequence boundaries", "Nexus MCP → Google Workspace adapter → canonical Google credential; Drive remains drive.file scoped", "AUTH_REQUIRED" if google.get("authentication") == "AUTH_REQUIRED" else None, google.get("authentication"), authorized=google.get("authentication") != "AUTH_REQUIRED", read_authority="GMAIL_CALENDAR_DRIVE_WITH_GRANTED_SCOPES", write_authority="CALENDAR_EVENTS; DRIVE_FILE; GMAIL_REQUIRES_GMAIL_MODIFY", cost_class="NO_INCREMENTAL_API_BILLING", consequence_class="INTERNAL_REVERSIBLE_WITH_EXTERNAL_SEND_APPROVAL", last_known_good=all((google.get("last_known_good") or {}).get(name) for name in ("GMAIL", "CALENDAR", "DRIVE")), last_verified_at=google.get("observed_at"), last_error=(google.get("current_runtime_health") or {}).get("last_error")),
    ]
    names = set(mcp.get("tools", []))
    workspace_read = "nexus_read_workspace_file" in names
    workspace_write = "nexus_write_workspace_artifact" in names
    registry.extend([
        row("browser_public_read", "BROWSER", "Hermes public web search/page reader", "web" in enabled,
            "web" in enabled, "web" in enabled, "web" in active, True,
            "Read-only public browsing; no purchases, publishing, account changes, or external sends",
            "Public internet search and page reading", None, "PASS" if "web" in active else "UNKNOWN",
            read_authority="PUBLIC_WEB_READ", write_authority="NONE", consequence_class="PUBLIC_READ_ONLY",
            last_known_good=True if "web" in active else None),
        row("local_file_read", "FILES", "Nexus bounded workspace file MCP", workspace_read,
            workspace_read, workspace_read, workspace_read, True,
            "Allowlisted Nexus roots; credential and key paths denied; UTF-8 reads capped at 1 MB",
            "Repository files only after resolved-path containment checks", None if workspace_read else "Nexus file-read tool not discovered",
            "PASS" if workspace_read and mcp.get("handshake") == "PASS" else "UNKNOWN",
            read_authority="APPROVED_NEXUS_ROOTS", consequence_class="INTERNAL_READ"),
        row("local_file_write", "FILES", "Nexus bounded artifact MCP", workspace_write,
            workspace_write, workspace_write, workspace_write, True,
            "New artifacts only under reports/nova_internal; data/runtime remains read-only; no overwrite; 100 KB maximum",
            "Approved Nexus internal artifact roots", None if workspace_write else "Nexus artifact tool not discovered",
            "PASS" if workspace_write and mcp.get("handshake") == "PASS" else "UNKNOWN",
            write_authority="APPROVED_INTERNAL_ARTIFACTS", consequence_class="INTERNAL_REVERSIBLE"),
        row("terminal_code", "LOCAL_EXECUTION", "Nexus bounded Systems/Coding assignments",
            "nexus_assign_bounded_coding_task" in names or "nexus_assign_department_query" in names,
            True, True, mcp.get("handshake") == "PASS", True,
            "Per-request durable assignment, scoped worker boundaries; no raw shell or credential access",
            "Nexus Systems and bounded coding worker execution", None if mcp.get("handshake") == "PASS" else "Nexus MCP unavailable",
            mcp.get("handshake"), read_authority="BOUNDED_INTERNAL_DIAGNOSTICS",
            write_authority="BOUNDED_CODE_OR_INTERNAL_WORK_PRODUCT",
            consequence_class="INTERNAL_REVERSIBLE_WITH_APPROVAL_FOR_PRODUCTION"),
    ])
    google_tools = set(google.get("tools", []))
    google_services = google.get("services") or {}
    google_auth_ok = google.get("authorization_state") == "AUTHORIZED"
    google_last_good = google.get("last_known_good") or {}
    google_health = (google.get("current_runtime_health") or {}).get("by_service") or {}
    for service_name, read_tools, write_tool, read_label, write_label in (
        ("GMAIL", {"gmail_search", "gmail_read_message", "gmail_read_thread"}, "gmail_create_draft", "GMAIL_READ", "GMAIL_WRITE"),
        ("CALENDAR", {"calendar_search_events", "calendar_read_event", "calendar_get_availability"}, "calendar_create_private_event", "CALENDAR_READ", "CALENDAR_WRITE"),
        ("DRIVE", {"drive_search", "drive_read_file"}, "drive_create_nexus_file", "DRIVE_READ", "DRIVE_WRITE"),
    ):
        read_present = bool(read_tools & google_tools)
        write_present = write_tool in google_tools
        authorized = bool((google_services.get(service_name) or {}).get("authorized", google_auth_ok))
        read_state = row(read_label, "GOOGLE", f"Canonical Nexus Google adapter {service_name} read surface",
            read_present, read_present, True, read_present and mcp.get("handshake") == "PASS", True,
            "Read-only request with bounded results and receipt", "Existing canonical OAuth grant; current runtime probe may be UNKNOWN",
            "AUTH_REQUIRED" if not authorized else None, google_health.get(service_name, "UNKNOWN"),
            authorized=authorized, read_authority="GRANTED_GOOGLE_READ_SCOPE", write_authority="NONE",
            cost_class="NO_INCREMENTAL_API_BILLING", consequence_class="READ_ONLY",
            last_known_good=google_last_good.get(service_name),
            last_verified_at=(google_services.get(service_name) or {}).get("last_verified_at"),
            last_error=(google_services.get(service_name) or {}).get("last_error"))
        registry.append(read_state)
        inspected_write = (google_services.get(service_name) or {}).get("write_authorized")
        if inspected_write is None and google.get("granted_scope_names"):
            granted = set(google["granted_scope_names"])
            inspected_write = ("gmail.modify" in granted if service_name == "GMAIL" else
                               "calendar.events" in granted if service_name == "CALENDAR" else
                               "drive.file" in granted if service_name == "DRIVE" else None)
        write_authorized = bool(inspected_write) if inspected_write is not None else None
        if service_name == "GMAIL":
            write_blocker = (None if write_authorized else
                "GOOGLE_WRITE_SCOPE_MISSING:https://www.googleapis.com/auth/gmail.modify" if write_authorized is False else
                "GOOGLE_SCOPE_INSPECTION_REQUIRED")
        elif service_name == "CALENDAR":
            write_blocker = None if write_present and write_authorized is True else ("calendar write tool not discovered" if not write_present else "GOOGLE_SCOPE_INSPECTION_REQUIRED")
        else:
            write_blocker = ("APPROVED_DRIVE_FOLDER_NOT_CONFIGURED" if write_present and not os.getenv("NEXUS_GOOGLE_DRIVE_FOLDER_ID") else
                             "drive write tool not discovered" if not write_present else
                             "GOOGLE_SCOPE_INSPECTION_REQUIRED" if write_authorized is None else None)
        write_configured = (write_present and write_authorized is True
                            and (service_name != "DRIVE" or bool(os.getenv("NEXUS_GOOGLE_DRIVE_FOLDER_ID"))))
        registry.append(row(write_label, "GOOGLE", f"Canonical Nexus Google adapter {service_name} bounded write surface",
            write_present, write_configured,
            True, write_present and mcp.get("handshake") == "PASS", True,
            "Per-operation receipt; external or destructive consequences remain gated",
            ("Unsent owner-only drafts and allowlisted organization; Gmail send is not exposed" if service_name == "GMAIL" else
             "Private event create/update without attendees" if service_name == "CALENDAR" else
             "Nexus-owned text files under configured approved folder; drive.file scope only"),
            write_blocker, "UNKNOWN", authorized=write_authorized,
            read_authority="NONE", write_authority="BOUNDED_INTERNAL_MUTATION",
            cost_class="NO_INCREMENTAL_API_BILLING",
            consequence_class="INTERNAL_REVERSIBLE_WITH_APPROVAL_FOR_EXTERNAL_OR_DESTRUCTIVE_ACTIONS",
            last_known_good=None, last_error=write_blocker))
    return registry


def _google_probe(tool_names: set[str]) -> dict[str, str]:
    """Use bounded read-only searches; return statuses only, never message data."""
    from nova.nexus_mcp_status import call_mcp_tool
    outcomes: dict[str, str] = {}
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=7)
    probes = {
        "GMAIL": ("gmail_search", {"query": "newer_than:30d", "max_results": 1}),
        "CALENDAR": ("calendar_search_events", {"start_time": start.isoformat(), "end_time": end.isoformat(), "max_results": 1}),
        "DRIVE": ("drive_search", {"query": "GoClear", "max_results": 1}),
    }
    for key, (tool, args) in probes.items():
        if tool not in tool_names:
            outcomes[key] = "NOT_CONFIGURED"
            continue
        try:
            result, _ = call_mcp_tool(tool, args)
            data = result.get("data") if isinstance(result, dict) and isinstance(result.get("data"), dict) else result
            message = json.dumps(data, ensure_ascii=False).casefold()
            if any(token in message for token in ("not authenticated", "unauthorized", "invalid_grant", "reauth", "auth_required")):
                outcomes[key] = "AUTH_REQUIRED"
            elif "refresherror" in message:
                outcomes[key] = "AUTH_REQUIRED"
            elif isinstance(data, dict) and str(data.get("status", "")).casefold() in {"error", "failed", "unavailable"}:
                outcomes[key] = "DEGRADED"
            else:
                outcomes[key] = "READ_TEST_PASS"
        except Exception as exc:
            outcomes[key] = "DEGRADED:" + type(exc).__name__
    return outcomes


def _previous_google_state() -> dict[str, Any]:
    """Retain known authorization/read evidence across transient probe failures."""
    try:
        value = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
        google = value.get("google") or {}
        if isinstance(google, dict):
            return google
    except (OSError, ValueError, TypeError):
        pass
    return {}


def _google_health(read_tests: dict[str, str]) -> dict[str, Any]:
    by_service = {}
    for name in ("GMAIL", "CALENDAR", "DRIVE"):
        result = read_tests.get(name)
        if result == "READ_TEST_PASS":
            by_service[name] = "PASS"
        elif result == "AUTH_REQUIRED":
            by_service[name] = "AUTH_REQUIRED"
        elif result and result.startswith("DEGRADED"):
            by_service[name] = "DEGRADED"
        else:
            by_service[name] = "UNKNOWN"
    values = set(by_service.values())
    overall = ("PASS" if values == {"PASS"} else "AUTH_REQUIRED" if "AUTH_REQUIRED" in values
               else "DEGRADED" if "DEGRADED" in values else "UNKNOWN")
    return {"overall": overall, "by_service": by_service}


def build_live_registry(*, probe_google: bool = False, force: bool = False) -> dict[str, Any]:
    previous_google = _previous_google_state()
    tools, count, error = _discover(force=force)
    try:
        from nova.approved_mcp_registry import discover_approved_mcp
        approved_mcp = discover_approved_mcp(force=force)
    except Exception as exc:
        approved_mcp = {"servers": [], "tools": [], "error": type(exc).__name__}
    names = _tool_set(tools)
    status = "AVAILABLE" if not error else "DEGRADED"
    mcp = {"status": status, "handshake": "PASS" if not error else "FAIL",
           "tool_count": count, "tools": sorted(names), "error": error}
    google_names = {name for name in names if name.startswith(("gmail_", "calendar_", "drive_"))}
    prior_lkg = previous_google.get("last_known_good") or {}
    last_known_good = {name: bool(prior_lkg.get(name, False)) for name in ("GMAIL", "CALENDAR", "DRIVE")}
    prior_services = previous_google.get("services") or {}
    authorization_state = str(previous_google.get("authorization_state") or
                              ("AUTHORIZED" if previous_google.get("authentication") in {"PASS", "AUTHORIZED"}
                               else "UNKNOWN"))
    google = {"status": "AVAILABLE" if google_names else "NOT_CONFIGURED",
              "tools": sorted(google_names), "authentication": authorization_state,
              "authorization_state": authorization_state,
              "last_known_good": last_known_good,
              "last_known_good_source": previous_google.get("last_known_good_source", "UNKNOWN"),
              "last_known_good_at": previous_google.get("last_known_good_at", "UNKNOWN"),
              "current_runtime_health": {"overall": "UNKNOWN",
                  "by_service": {name: "UNKNOWN" for name in ("GMAIL", "CALENDAR", "DRIVE")},
                  "last_error": None},
              "services": {name: {
                  "authorized": bool((prior_services.get(name) or {}).get("authorized", authorization_state == "AUTHORIZED")),
                  "last_known_good": last_known_good[name],
                  "last_verified_at": (prior_services.get(name) or {}).get("last_verified_at", "UNKNOWN"),
                  "current_runtime_health": "UNKNOWN",
                  "last_error": (prior_services.get(name) or {}).get("last_error"),
                  "canonical_path": str(REGISTRY_PATH),
              } for name in ("GMAIL", "CALENDAR", "DRIVE")},
              "canonical_path": str(REGISTRY_PATH)}
    if probe_google and google_names and not error:
        google["scope_inspection"] = "UNKNOWN"
        if "google_get_authority" in names:
            try:
                from nova.nexus_mcp_status import call_mcp_tool
                authority_result, _ = call_mcp_tool("google_get_authority", {})
                authority_item = next(iter(authority_result.get("items", [])), {})
                if authority_result.get("status") == "ok" and authority_item.get("authorization_state") == "AUTHORIZED":
                    google["scope_inspection"] = "PASS"
                    google["authorization_state"] = "AUTHORIZED"
                    google["granted_scope_names"] = authority_item.get("granted_scope_names", [])
                    google["write_capabilities"] = {
                        "GMAIL": "AVAILABLE_WITH_CONTROLS" if authority_item.get("gmail_write") else "NOT_AUTHORIZED",
                        "CALENDAR": "AVAILABLE_WITH_CONTROLS" if authority_item.get("calendar_write") else "NOT_AUTHORIZED",
                        "DRIVE": "AVAILABLE_WITH_CONTROLS" if authority_item.get("drive_access") else "NOT_AUTHORIZED",
                    }
                    for service_name, key in (("GMAIL", "gmail_write"), ("CALENDAR", "calendar_write"), ("DRIVE", "drive_access")):
                        service = google["services"].setdefault(service_name, {})
                        service["write_authorized"] = bool(authority_item.get(key))
                else:
                    google["scope_inspection"] = "UNKNOWN"
                    google["scope_inspection_error"] = authority_result.get("error")
            except Exception as exc:
                google["scope_inspection_error"] = type(exc).__name__
        google["read_tests"] = _google_probe(names)
        health = _google_health(google["read_tests"])
        checked_at = datetime.now(timezone.utc).isoformat()
        for name, result in google["read_tests"].items():
            service = google["services"].setdefault(name, {})
            if result == "READ_TEST_PASS":
                last_known_good[name] = True
                service.update(authorized=True, last_known_good=True, last_verified_at=checked_at, last_error=None)
            elif result and result != "NOT_CONFIGURED":
                service["last_error"] = result
            service["current_runtime_health"] = health["by_service"].get(name, "UNKNOWN")
        google["last_known_good"] = last_known_good
        google["current_runtime_health"] = {**health,
            "last_error": {name: result for name, result in google["read_tests"].items()
                           if result != "READ_TEST_PASS" and result != "NOT_CONFIGURED"} or None}
        for name in ("GMAIL", "CALENDAR", "DRIVE"):
            service = google["services"][name]
            service["last_known_good"] = last_known_good[name]
            service["canonical_path"] = str(REGISTRY_PATH)
    department_records: list[dict[str, Any]] = []
    try:
        source = json.loads((ROOT / "data/runtime/nexus_department_registry.json").read_text())
        for row in source.get("departments", []):
            if isinstance(row, dict):
                department_records.append({"canonical_name": row.get("department_id"),
                    "user_facing_name": row.get("name"), "registry_health": row.get("status"),
                    "workers": row.get("workers", []), "capabilities": row.get("capabilities", [])})
    except (OSError, ValueError, TypeError):
        pass
    assignments = [name for name in ("nexus_assign_research", "nexus_assign_department_query") if name in names]
    specialists = [name for name in ("nexus_delegate_specialist",) if name in names]
    hermes_view = _hermes_runtime_view()
    try:
        from nexus_agent_platform.bridge.oracle_hermes_cli import ORACLE_TOOLSET
        toolset = ORACLE_TOOLSET.split(",")
    except (ImportError, AttributeError):
        toolset = []
    tool_records = []
    for row in tools:
        if not isinstance(row, dict) or not row.get("name"):
            continue
        description = str(row.get("description") or "")
        mode = "READ_ONLY" if "read only" in description.casefold() or "read-only" in description.casefold() else (
            "GOVERNED_ACTION" if any(word in description.casefold() for word in ("queue", "assignment", "create")) else "UNKNOWN"
        )
        tool_records.append({"server_id": "nexus_mcp_remote", "name": row["name"], "description": description[:500],
                             "input_schema": row.get("input_schema", {}), "operation_class": mode})
    for row in approved_mcp.get("tools", []):
        if not isinstance(row, dict) or not row.get("name"):
            continue
        # Nexus tools were already read from the Nexus MCP status adapter above.
        # Keep one canonical record per server/tool in Nova's inventory.
        if row.get("server_id") == "nexus_mcp_remote":
            continue
        tool_records.append({"server_id": row.get("server_id"), "name": row["name"],
            "description": str(row.get("description") or "")[:500],
            "input_schema": row.get("input_schema", {}),
            "annotations": row.get("annotations", {}),
            "operation_class": row.get("read_write_class", "UNKNOWN"),
            "cost_class": row.get("cost_class", "UNKNOWN"),
            "write_allowed": row.get("write_allowed", False)})
    registry = {"source": "live Nexus MCP tool discovery plus deployed Hermes profile and canonical department registry",
            "observed_at": datetime.now(timezone.utc).isoformat(),
            "nexus_mcp": mcp, "google": google, "approved_mcp": approved_mcp,
            "tool_registry": tool_records,
            "hermes": {"status": "CONFIGURED" if toolset else "UNAVAILABLE", "toolset": toolset,
                       "browser_profile_enabled": hermes_view.get("browser_enabled", "UNKNOWN"),
                       "native_tools_enabled_in_profile": hermes_view.get("native_tools_enabled", []),
                       "native_tools_disabled_in_profile": hermes_view.get("native_tools_disabled", []),
                       "configured_mcp_servers": hermes_view.get("mcp_servers", {}),
                       "you_com_handshake": hermes_view.get("you_com_handshake", "NOT_TESTED"),
                       "you_com_tool_count": hermes_view.get("you_com_tool_count", 0),
                       "browser_action_test": "NOT_IN_NOVA_ALLOWLIST" if "browser" not in toolset else "NOT_TESTED",
                       "nova_allowlist_limits": "Only the named toolsets in toolset are exposed to this Nova invocation."},
            "mcp_inventory": {"servers": approved_mcp.get("servers", []),
                              "total_tools": sum(int(row.get("tool_count", 0)) for row in approved_mcp.get("servers", [])),
                              "error": approved_mcp.get("error")},
            "nexus_execution": {"durable_assignment_tools": assignments,
                                "read_only_specialist_tool": specialists},
            "capabilities": _capability_inventory(hermes_view, toolset, mcp, google),
            "departments": department_records,
            "availability_notes": [
                "A discovered MCP tool is callable surface, not proof that its provider authentication or operation succeeds.",
                "The specialist delegation tool is read-only; it does not create a durable department job.",
                "Durable department assignment is exposed for Research and for the bounded Alpha/Systems query action.",
            ]}
    try:
        REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_path = tempfile.mkstemp(prefix=".nova-capabilities-", suffix=".tmp", dir=str(REGISTRY_PATH.parent))
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(registry, stream, ensure_ascii=False, indent=2, sort_keys=True)
            stream.write("\n")
        os.replace(temp_path, REGISTRY_PATH)
    except OSError:
        pass
    return registry


def capability_context_for_request(message: str) -> str:
    """Return a fresh, concise tool view only when the request needs one."""
    text = message.casefold()
    is_capability_query = bool(re.search(r"\b(?:tools|capabilit|mcp|canary|servers?|what can you|can you use|connected to google|access to google|available right now)\b", text))
    is_google_request = bool(re.search(r"\b(?:google|gmail|email|calendar|drive|appointment)\b", text))
    is_executor_request = bool(re.search(r"\b(?:browser|website|web page|landing page|video|image|creative|trading|forex|marketing|finance|research|systems|notebooklm|pdf|document|file|runtime|code|terminal|diagnostic|audio|speech|vision|skill|schedule|metricool)\b", text))
    is_action_verb = bool(re.search(r"\b(?:create|make|add|update|change|edit|modify|delete|remove|read|show|get|list|find|open|check|inspect)\b", text))
    if not is_capability_query and not is_google_request and not is_executor_request and not is_action_verb:
        return ""
    needs_connection_check = is_capability_query and is_google_request
    registry = build_live_registry(probe_google=needs_connection_check)
    context = "LIVE CAPABILITY REGISTRY (fresh MCP discovery; do not infer beyond this evidence):\n" + json.dumps(registry, ensure_ascii=False, default=str)[:9000]
    try:
        from nova.approved_mcp_registry import resolve_approved_mcp_tool_request
        candidate = resolve_approved_mcp_tool_request(message, owner_authorized=True)
        if candidate:
            metadata = {k: candidate.get(k) for k in ("server_id", "name", "description", "input_schema", "read_write_class", "cost_class", "external_effect", "production_effect", "destructive", "reversible", "sandbox_only", "policy")}
            context += "\nAPPROVED MCP ACTION CANDIDATE (policy evaluated before model invocation):\n" + json.dumps(metadata, ensure_ascii=False, default=str)
            context += ("\nFor this explicit action, call this exact approved server/tool once using its live schema. "
                        "Do not claim completion unless the tool returns a receipt ID; echo the returned resource ID and receipt ID exactly.")
    except Exception:
        pass
    return context


def render_capability_answer(message: str) -> str:
    """Answer capability inventory questions from current discovered evidence."""
    probe_google = bool(re.search(r"\b(?:google|gmail|email|calendar|drive|appointment)\b", message.casefold()))
    registry = build_live_registry(probe_google=probe_google, force=True)
    if registry["nexus_mcp"]["handshake"] != "PASS":
        return f"I couldn't verify the live capability list because Nexus MCP discovery failed ({registry['nexus_mcp']['error']}). I won't claim those tools are available."
    return summarize_capability_registry(registry, message)


def summarize_capability_registry(registry: dict[str, Any], message: str) -> str:
    """Produce a concise owner-level answer from the current capability snapshot."""
    if registry.get("nexus_mcp", {}).get("handshake") != "PASS":
        error = registry.get("nexus_mcp", {}).get("error") or "unknown error"
        return f"I couldn't verify the live capability list because Nexus MCP discovery failed ({error}). I won't claim those tools are available."
    names = set(registry["nexus_mcp"]["tools"])
    capabilities = registry.get("capabilities", [])
    lowered = message.casefold()
    by_name = {row.get("capability"): row for row in capabilities}

    if re.search(r"\b(?:mcp\s+servers?|servers?\s+can you access|which mcp)\b", lowered):
        servers = (registry.get("approved_mcp") or {}).get("servers", [])
        visible = [row for row in servers if row.get("approved") and row.get("connected")]
        if visible:
            entries = [f"{row.get('server_name') or row.get('server_id')} — {row.get('tool_count', 0)} tools"
                       for row in visible]
            return "Approved MCP servers currently connected: " + "; ".join(entries) + "."
        return "I couldn't verify the approved MCP server inventory from the live profile."

    def state(name: str) -> str:
        return str(by_name.get(name, {}).get("status", "UNAVAILABLE"))

    def google_read_status() -> str:
        google = registry.get("google", {})
        health = google.get("current_runtime_health") or {}
        return str(health.get("overall") or "UNKNOWN")

    google_status = google_read_status()
    google_ok = google_status == "PASS"

    if re.search(r"\b(?:google|gmail|email|calendar|drive|appointment)\b", lowered):
        if not any(name.startswith(("gmail_", "calendar_", "drive_")) for name in names):
            return "Google services are not exposed to this Nova session."
        google = registry.get("google", {})
        last_good = google.get("last_known_good") or {}
        services = google.get("services") or {}
        checks = (google.get("current_runtime_health") or {}).get("by_service") or {}
        service_requested = next((name for name, pattern in (
            ("GMAIL", r"\b(?:gmail|email)\b"), ("CALENDAR", r"\bcalendar\b"), ("DRIVE", r"\bdrive\b"))
            if re.search(pattern, lowered)), None)
        if service_requested and re.search(r"\b(?:authorized|connected)\b", lowered):
            state = services.get(service_requested) or {}
            answer = "Yes" if state.get("authorized") else "Authorization status is unknown"
            return (f"{answer}. Nexus records {service_requested.title()} authorization as "
                    f"{'authorized' if state.get('authorized') else 'unknown'} and last-known-good as "
                    f"{'yes' if last_good.get(service_requested) else 'unknown'}. Current runtime health is "
                    f"{checks.get(service_requested, 'UNKNOWN')}.")
        check_text = ", ".join(f"{name.title()} {checks.get(name, 'UNKNOWN')}" for name in ("GMAIL", "CALENDAR", "DRIVE"))
        previous_text = ", ".join(f"{name.title()} {'YES' if last_good.get(name) else 'UNKNOWN'}" for name in ("GMAIL", "CALENDAR", "DRIVE"))
        auth = google.get("authorization_state", "UNKNOWN")
        return ("Nexus exposes Gmail, Google Calendar, and Google Drive through the canonical Google adapter. "
                f"Google authorization state: {auth}; last-known-good reads: {previous_text}; "
                f"current runtime health: {(google.get('current_runtime_health') or {}).get('overall', 'UNKNOWN')} ({check_text}). "
                "Calendar event writes are supported by the granted calendar.events scope. Drive writes are limited to app-created/selected files under the configured Nexus folder using drive.file. Gmail draft/organization writes require gmail.modify; that scope is not in the current grant, so Gmail writes remain unavailable until Ray authorizes it. External email send is not exposed.")
    if re.search(r"\b(?:browser|web page|website|site)\b", lowered):
        if state("browser_public_read") in {"AVAILABLE", "AVAILABLE_WITH_CONTROLS"} or state("web_search") in {"AVAILABLE", "AVAILABLE_WITH_CONTROLS"}:
            return ("Public web search and page reading are available with controls. Interactive account actions, purchases, publishing, and external sends are not exposed without their separate approval path.")
        return "I couldn't verify an active web or browser capability in this session."
    if re.search(r"\b(?:file|files|document|pdf|spreadsheet)\b", lowered):
        if "drive_search" in names and google_ok:
            return "Google Drive has a governed read path through Nexus. Nexus workspace file reads are separately bounded to approved repository roots and deny credentials and keys. Drive file creation is limited by drive.file to app-created or user-selected files in the configured Nexus folder."
        if "drive_search" in names and google_status == "AUTH_REQUIRED":
            return "Drive has a governed read-only route through Nexus, but its Google authorization needs renewal. The Hermes file tool is inactive because its reads are not path-scoped and could reach profile credentials."
        if "drive_search" in names:
            return "Drive is exposed through Nexus, but its current read check is degraded. The Hermes file tool is inactive because its reads are not path-scoped and could reach profile credentials."
        return "The Hermes file tool is installed but inactive because reads are not path-scoped and could reach profile credentials."
    if re.search(r"\b(?:terminal|code|diagnostic|run a script)\b", lowered):
        return ("Nexus provides bounded Systems diagnostics and governed coding assignments. Those run as durable internal jobs with receipts and scoped work boundaries; unrestricted shell, credential access, destructive system operations, spending, and production changes are not exposed as direct commands.")
    if re.search(r"\b(?:video|image|creative|make videos)\b", lowered):
        image = "unavailable because no image provider is configured" if state("image_generation") == "UNAVAILABLE" else "available only through an approved provider"
        video = "unavailable; the tool is disabled and no provider is configured" if state("video_generation") == "UNAVAILABLE" else "available only through an approved provider"
        return f"Image generation is {image}. Video generation is {video}. Nova can route supported creative work through Nexus departments."
    if "notebooklm" in lowered or "research" in lowered:
        if "nexus_assign_notebooklm_runtime_canary" in names:
            return "Research, Systems, and Alpha have governed Nexus assignment paths. NotebookLM is used through Nexus Research; Nova has no direct NotebookLM operation tool."
    if re.search(r"\b(?:metricool|social post|schedule a post|publish)\b", lowered):
        return "Metricool is connected in the wider Hermes profile but inactive in Nova's session. It exposes post scheduling, which requires an approved governed publishing path."
    if re.search(r"\b(?:tools|capabilit|what can you|what do you have|available right now)\b", lowered):
        google = registry.get("google", {})
        last_good = google.get("last_known_good") or {}
        google_summary = ("Google authorization is " + str(google.get("authorization_state", "UNKNOWN")) +
            "; prior Gmail/Calendar/Drive read checks are " + "/".join(
                "last-known-good" if last_good.get(name) else "not recorded"
                for name in ("GMAIL", "CALENDAR", "DRIVE")) +
            "; current runtime health is " + google_status + ".")
        return (f"Nexus MCP is connected with {registry['nexus_mcp']['tool_count']} tools. I can use receipt-backed Research, Systems, and Alpha assignments, public web search/page reading, bounded Nexus workspace files, and governed Google Workspace reads. "
                f"{google_summary} Internal file writes are limited to new Nexus artifacts; code work uses bounded durable assignments rather than unrestricted shell. Gmail writes require an additional Google scope; external mail send, public publishing, purchases, and destructive changes stay gated. No image provider is configured, and video generation is disabled.")
    return f"Nexus MCP is connected with {registry['nexus_mcp']['tool_count']} tools, and web search is active."
