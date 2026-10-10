"""Deterministic Systems watchdog and checkpointed nightly audit.

The canonical continuous kernel is the only scheduler.  This module is its
Systems workflow adapter: it discovers configured environments once, stores
the authoritative registry and run/check events in the existing Supabase
``nexus_events`` control plane, and returns observations without allowing a
probe to select lifecycle transitions.
"""
from __future__ import annotations

import json
import fcntl
import os
import re
import shutil
import ssl
import subprocess
import sys
import urllib.parse
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
LOCAL_MIRROR = ROOT / "data/governed/systems_environment_registry.json"
MAX_CHECKS_PER_WAKE = 10
NIGHTLY_LOCAL_HOUR = int(os.environ.get("NEXUS_SYSTEMS_NIGHTLY_HOUR", "2"))
SYSTEMS_STATES = ("SCHEDULED", "CHECK_DUE", "CHECK_RUNNING", "CHECK_RESULT_PERSISTED",
                 "HEALTHY_RECORDED", "ABNORMAL_EVIDENCE_COLLECTION", "AI_ANALYSIS",
                 "WORKFLOW_CLASSIFICATION", "AUTO_REPAIR_RUNNING", "SYSTEMS_PROJECT_ACTIVE",
                 "WAITING_ON_UPGRADE_CONTROL", "WAITING_ON_RESEARCH", "WAITING_ON_OTHER_DEPARTMENT",
                 "WAITING_ON_RAY", "CHECK_COMPLETE", "CHECKPOINTED", "NEXT_CHECK_READY",
                 "NIGHTLY_COMPLETE_FOR_DATE")
CHECK_STATES = frozenset({"PASS", "FAIL", "DEGRADED", "UNREACHABLE", "BLOCKED_BY_AUTH",
    "NOT_CONFIGURED", "NOT_APPLICABLE", "CHECK_ERROR", "STALE", "THRESHOLD_EXCEEDED",
    "NOT_DUE", "DEPENDENCY_UNAVAILABLE", "NOT_EXPOSED_BY_PROVIDER"})
def _closed_map_for(env_id: str) -> dict[str, str]:
    key = re.sub(r"[^A-Za-z0-9]+", "_", env_id).upper()
    return {"PASS": "PERSIST_HEALTHY_AND_CONTINUE", "FAIL": f"{key}_FAILURE_WORKFLOW",
        "DEGRADED": f"{key}_DEGRADED_RECOVERY", "UNREACHABLE": f"{key}_CONNECTIVITY_RECOVERY",
        "BLOCKED_BY_AUTH": f"{key}_APPROVED_AUTH_RECOVERY", "NOT_CONFIGURED": f"{key}_CONFIGURATION_RECOVERY",
        "NOT_APPLICABLE": "NONE_REQUIRED", "CHECK_ERROR": "SYSTEMS_CHECKER_REPAIR", "STALE": f"{key}_STALE_STATE_RECOVERY",
        "THRESHOLD_EXCEEDED": f"{key}_THRESHOLD_WORKFLOW", "NOT_DUE": "WAIT_UNTIL_NEXT_CHECK_TIME",
        "DEPENDENCY_UNAVAILABLE": "DEPENDENCY_RECOVERY", "NOT_EXPOSED_BY_PROVIDER": "NONE_REQUIRED"}
CLOSED_TRANSITIONS = {
    "PASS": {"next_workflow": "PERSIST_HEALTHY_AND_CONTINUE", "next_action_required": False},
    "FAIL": {"next_workflow": None, "next_action_required": True},
    "DEGRADED": {"next_workflow": "DEGRADED_SERVICE_RECOVERY", "next_action_required": True},
    "UNREACHABLE": {"next_workflow": "CONNECTIVITY_RECOVERY_RETRY_ONCE", "next_action_required": True},
    "BLOCKED_BY_AUTH": {"next_workflow": "APPROVED_AUTH_REFERENCE_RECOVERY_RETRY_ONCE", "next_action_required": True},
    "NOT_CONFIGURED": {"next_workflow": "CONFIGURATION_RECOVERY_OR_REGISTRY_CORRECTION", "next_action_required": True},
    "NOT_APPLICABLE": {"next_workflow": "NONE_REQUIRED", "next_action_required": False},
    "CHECK_ERROR": {"next_workflow": "CHECKER_REPAIR_RETRY_ONCE", "next_action_required": True},
    "STALE": {"next_workflow": "STALE_STATE_RECOVERY", "next_action_required": True},
    "THRESHOLD_EXCEEDED": {"next_workflow": "THRESHOLD_SPECIFIC_CAPACITY_WORKFLOW", "next_action_required": True},
    "NOT_DUE": {"next_workflow": "WAIT_UNTIL_NEXT_CHECK_TIME", "next_action_required": False},
    "DEPENDENCY_UNAVAILABLE": {"next_workflow": "DEPENDENCY_RECOVERY", "next_action_required": True},
    "NOT_EXPOSED_BY_PROVIDER": {"next_workflow": "NONE_REQUIRED", "next_action_required": False},
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime | None = None) -> str:
    return (value or _now()).isoformat()


def _next_due(now: datetime, frequency: str) -> datetime:
    local = now.astimezone()
    if frequency == "CRITICAL":
        return now + timedelta(minutes=20)
    if frequency == "DAILY":
        candidate = local.replace(hour=NIGHTLY_LOCAL_HOUR, minute=0, second=0, microsecond=0)
        return candidate if candidate > local else candidate + timedelta(days=1)
    return now + timedelta(days={"WEEKLY": 7, "MONTHLY": 30}.get(frequency, 1))


def _load_env() -> None:
    # Scheduled child processes must use the same protected runtime env source
    # as other canonical workers. A repo-local .env remains a fallback for
    # existing developer setups, but is not required by the daemon.
    try:
        import sys
        sys.path.insert(0, str(ROOT / "scripts" / "ops"))
        from nexus_runtime_env import load_runtime_env
        load_runtime_env()
    except (ImportError, OSError):
        pass
    path = ROOT / ".env"
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _supabase_request(path: str, method: str = "GET", body: dict[str, Any] | None = None) -> Any:
    _load_env()
    base = (os.environ.get("SUPABASE_URL") or os.environ.get("VITE_SUPABASE_URL") or "").rstrip("/")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not base or not key:
        raise RuntimeError("supabase_control_plane_not_configured")
    data = None if body is None else json.dumps(body, separators=(",", ":")).encode()
    request = urllib.request.Request(
        f"{base}/rest/v1/{path}", data=data, method=method,
        headers={"apikey": key, "Authorization": f"Bearer {key}",
                 "Content-Type": "application/json", "Prefer": "return=representation"},
    )
    try:
        import certifi
        context = ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        context = ssl.create_default_context()
    with urllib.request.urlopen(request, timeout=8, context=context) as response:
        raw = response.read()
        return json.loads(raw) if raw else None


def _event(action: str, payload: dict[str, Any], *, title: str, summary: str,
           correlation_id: str | None = None, event_key: str | None = None,
           event_id: str | None = None) -> dict[str, Any]:
    stable_id = event_id or (str(uuid.uuid5(uuid.NAMESPACE_URL, f"nexus-systems:{event_key}")) if event_key else None)
    body = {
        "lane": "system", "source": "canonical_systems_workflow", "action": action,
        "status": "success", "title": title, "summary": summary,
        "payload": payload, "correlation_id": correlation_id,
    }
    if stable_id:
        body["id"] = stable_id
        query = urllib.parse.urlencode({"select": "id", "id": f"eq.{stable_id}", "limit": "1"})
        existing = _supabase_request(f"nexus_events?{query}") or []
        value = _supabase_request(f"nexus_events?id=eq.{stable_id}", "PATCH", body) if existing else _supabase_request("nexus_events", "POST", body)
    else:
        value = _supabase_request("nexus_events", "POST", body)
    if not isinstance(value, list) or not value:
        raise RuntimeError(f"supabase_write_not_confirmed:{action}")
    return value[0]


def _latest_event(action: str) -> dict[str, Any] | None:
    # Resolve the registry/run through a local event-ID pointer, then read the
    # authoritative payload by Supabase primary key. This avoids table scans
    # over the large append-only nexus_events ledger.
    pointer_paths = []
    if action == "systems_environment_registry_snapshot":
        pointer_paths.append(LOCAL_MIRROR)
    if action == "systems_nightly_run":
        pointer_paths.append(ROOT / "data/runtime/systems_nightly_run_pointer.json")
    for pointer_path in pointer_paths:
        try:
            pointer = json.loads(pointer_path.read_text())
            event_id = pointer.get("event_id")
            if event_id:
                query = urllib.parse.urlencode({"select": "id,created_at,payload,correlation_id",
                                                "id": f"eq.{event_id}", "limit": "1"})
                rows = _supabase_request(f"nexus_events?{query}") or []
                if rows:
                    return rows[0]
        except Exception:
            pass
    query = urllib.parse.urlencode({"select": "id,created_at",
                                    "action": f"eq.{action}", "status": "eq.success",
                                    "order": "created_at.desc", "limit": "1"})
    try:
        rows = _supabase_request(f"nexus_events?{query}") or []
        if not rows:
            return None
        by_id = urllib.parse.urlencode({"select": "id,created_at,payload,correlation_id",
                                        "id": f"eq.{rows[0]['id']}", "limit": "1"})
        full = _supabase_request(f"nexus_events?{by_id}") or []
        return full[0] if full else None
    except Exception:
        return None


def _discover_registry() -> list[dict[str, Any]]:
    """Build the initial registry only from present, configured Nexus assets."""
    now = _now()
    entries: list[dict[str, Any]] = []

    def add(env_id: str, name: str, kind: str, owner: str, profile: str,
            criticality: str = "DAILY", frequency: str = "DAILY", dependencies: list[str] | None = None,
            cost: bool = False, quota: bool = False, version: bool = False, notes: str = "") -> None:
        profile_workflow = _closed_map_for(env_id)
        entries.append({"environment_id": env_id, "name": name, "type": kind,
                        "host": "localhost" if kind in {"HOST", "RUNTIME"} else None,
                        "owner_department": owner, "active": True, "criticality": criticality,
                        "check_profile": profile, "check_frequency": frequency,
                        "last_check": None, "next_check": _iso(now), "last_known_good": None,
                        "dependencies": dependencies or [], "cost_tracked": cost,
                        "quota_tracked": quota, "version_tracked": version,
                        "notebook_id": None, "current_state": "NOT_CONFIGURED", "notes": notes,
                        "probe_revision": 3, "closed_state_map": profile_workflow,
                        "created_at": _iso(now), "updated_at": _iso(now)})

    add("local_host", "Nexus Mac host", "HOST", "SYSTEMS", "HOST_PROFILE", "CRITICAL", "CRITICAL",
        notes="Registered from the active local canonical runtime host.")
    add("nexus_canonical_runtime", "Nexus canonical runtime", "RUNTIME", "SYSTEMS", "SERVICE_PROFILE", "CRITICAL", "CRITICAL",
        ["local_host"], notes="Canonical checkout containing the active scheduler entrypoint.")
    add("canonical_scheduler", "Nexus continuous operating kernel", "SERVICE", "SYSTEMS", "WORKFLOW_PROFILE", "CRITICAL", "CRITICAL",
        ["nexus_canonical_runtime"], notes="Existing com.nexus.continuous-loop launchd service.")
    add("supabase_control_plane", "Supabase control plane", "PROVIDER", "SYSTEMS", "PROVIDER_PROFILE", "CRITICAL", "CRITICAL",
        ["nexus_canonical_runtime"], notes="Existing configured Supabase nexus_events control plane.")
    add("supabase_egress_guard", "Supabase REST egress guard", "RUNTIME", "SYSTEMS", "WORKFLOW_PROFILE", "CRITICAL", "CRITICAL",
        ["nexus_canonical_runtime"], notes="Local daily REST response-byte guard; no query values or credentials are stored.")
    if (ROOT / "configs/notebooklm_automation_registry.json").is_file():
        add("notebooklm", "NotebookLM automation", "PROVIDER", "RESEARCH", "NOTEBOOK_PROFILE", "DAILY", "DAILY",
            ["supabase_control_plane"], notes="Configured by the existing NotebookLM automation registry.")
    if (ROOT / "scripts/research/research_case_engine.py").is_file():
        add("research_runtime", "Research case runtime", "SERVICE", "RESEARCH", "SERVICE_PROFILE", "CRITICAL", "CRITICAL",
            ["nexus_canonical_runtime", "supabase_control_plane"], notes="Registered from the active case runtime module.")
    if (ROOT / "scripts/nexus_agent_platform/feeder_runtime.py").is_file():
        add("feeder_opportunity_intake_runtime", "External feeders and Ray/Nova opportunity intake", "SERVICE", "SYSTEMS", "WORKFLOW_PROFILE", "CRITICAL", "CRITICAL",
            ["nexus_canonical_runtime", "supabase_control_plane", "research_runtime"], notes="Bounded intake worker runs inside com.nexus.continuous-loop; health and counts are persisted to nexus_feeder_system_registry.")
    if (ROOT / "scripts/operations/department_handoff_continuation.py").is_file():
        add("department_continuation_runtime", "Department continuation runtime", "SERVICE", "SYSTEMS", "WORKFLOW_PROFILE", "CRITICAL", "CRITICAL",
            ["nexus_canonical_runtime", "supabase_control_plane"], notes="Registered from the active directive continuation module.")
    if (ROOT / "configs/nexus_credential_registry.json").is_file():
        add("webull_provider", "Webull PaperTrade OpenAPI", "PROVIDER", "TRADING", "PROVIDER_PROFILE", "DAILY", "DAILY",
            ["supabase_control_plane"], notes="Existing configured provider credential registry entry; no secret values stored.")
    if shutil.which("hermes") or (Path.home() / ".local/bin/hermes").exists():
        add("hermes_mac", "Mac Hermes runtime and local bridge", "SERVICE", "SYSTEMS", "SERVICE_PROFILE",
            "CRITICAL", "CRITICAL", ["local_host"], version=True,
            notes="Discovered from the installed Hermes CLI and active local Hermes bridge/runtime processes.")
    if (ROOT / "configs/oanda_connector_policy.json").is_file():
        add("oanda_practice", "OANDA Practice", "PROVIDER", "TRADING", "PROVIDER_PROFILE", "DAILY", "DAILY",
            ["supabase_control_plane"], notes="Existing configured OANDA connector policy.")
    oci_config = Path.home() / ".oci/config"
    if oci_config.is_file():
        add("oracle_cloud", "Oracle Cloud tenancy", "CLOUD", "SYSTEMS", "CLOUD_PROFILE", "WEEKLY", "WEEKLY",
            ["nexus_canonical_runtime"], cost=True, notes="Existing OCI config file detected; no config contents read into registry.")
    if oci_config.is_file() and (ROOT / "scripts/ops/check_remote_stack_health.py").is_file():
        add("hermes_oracle", "Oracle Hermes runtime", "SERVICE", "SYSTEMS", "SERVICE_PROFILE",
            "CRITICAL", "DAILY", ["oracle_cloud"], cost=True, version=True,
            notes="Discovered from the configured read-only Oracle Hermes runtime health probe.")
    if (ROOT / "netlify.toml").is_file() and (ROOT / "netlify").is_dir():
        add("netlify_deployment", "Netlify deployment configuration", "PROVIDER", "SYSTEMS", "PROVIDER_PROFILE", "WEEKLY", "WEEKLY",
            ["nexus_canonical_runtime"], version=True, notes="Deployment configuration is present in canonical checkout.")
    if (ROOT / "configs/research_source_registry.json").is_file() and (ROOT / "configs/youtube_channel_portfolio.json").is_file():
        add("source_monitors", "Research and YouTube source monitors", "SERVICE", "RESEARCH", "SERVICE_PROFILE", "DAILY", "DAILY",
            ["research_runtime", "nexus_canonical_runtime"], notes="Configured Research source registry and YouTube channel portfolio are present.")
    if (ROOT / "artifacts").is_dir():
        add("artifact_storage", "Nexus artifact storage", "STORAGE", "SYSTEMS", "HOST_PROFILE", "DAILY", "DAILY",
            ["nexus_canonical_runtime"], notes="Canonical artifacts directory exists on the local host.")
    if (ROOT / "reports/runtime").is_dir():
        add("log_storage", "Nexus runtime log storage", "STORAGE", "SYSTEMS", "HOST_PROFILE", "DAILY", "DAILY",
            ["nexus_canonical_runtime"], notes="Canonical reports/runtime directory exists on the local host.")
    try:
        remote = subprocess.run(["git", "remote", "get-url", "origin"], cwd=ROOT, capture_output=True, text=True, timeout=3, check=False)
    except (OSError, subprocess.TimeoutExpired):
        remote = None
    if remote is not None and remote.returncode == 0:
        raw = remote.stdout.strip()
        parsed = urllib.parse.urlparse(raw if "://" in raw else f"ssh://{raw}")
        if parsed.hostname and parsed.hostname.lower() in {"github.com", "www.github.com"}:
            add("github_remote", "GitHub canonical repository remote", "PROVIDER", "SYSTEMS", "PROVIDER_PROFILE", "WEEKLY", "WEEKLY",
                ["nexus_canonical_runtime"], version=True, notes="Git origin host is GitHub; remote URL and credentials are not stored.")
    # Enumerate the active launchd services instead of duplicating a scheduler
    # inventory in this module. The canonical scheduler entry is represented
    # above; each additional loaded Nexus service is registered once here.
    rc, launchd = _command(["/bin/launchctl", "list"], timeout=10)
    if rc == 0:
        for line in launchd.splitlines():
            parts = line.split()
            if len(parts) < 3:
                continue
            label = parts[-1]
            if label == "com.nexus.continuous-loop" or not (label.startswith("com.nexus.") or label == "cf.hermes.gateway"):
                continue
            env_id = "launchd_" + re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")
            add(env_id, label, "SERVICE", "SYSTEMS", "SERVICE_PROFILE",
                "CRITICAL" if label in {"cf.hermes.gateway", "com.nexus.nexus-mcp-bridge"} else "DAILY",
                "CRITICAL" if label in {"cf.hermes.gateway", "com.nexus.nexus-mcp-bridge"} else "DAILY",
                ["local_host"], notes="Discovered from the active launchd service registry.")
    # Provider credential references are configuration facts, not proof that a
    # credential resolves. Register each configured provider as a monitored
    # capability without copying any secret material.
    try:
        credential_config = json.loads((ROOT / "configs/nexus_credential_registry.json").read_text())
        for item in credential_config.get("credentials", []):
            provider = str(item.get("provider") or "").strip().lower()
            if not provider or provider in {"webull", "oanda", "supabase"}:
                continue
            env_id = f"provider_{re.sub(r'[^a-z0-9]+', '_', provider).strip('_')}"
            if any(row["environment_id"] == env_id for row in entries):
                continue
            add(env_id, f"{provider.title()} provider capability", "PROVIDER", "SYSTEMS", "PROVIDER_PROFILE",
                "WEEKLY", "WEEKLY", ["supabase_control_plane"],
                cost=provider in {"openrouter", "groq", "openai", "anthropic", "tavily", "serpapi"},
                quota=provider in {"openrouter", "groq", "openai", "anthropic", "tavily", "serpapi"},
                notes="Discovered from configured provider credential metadata; no secret values stored.")
    except (OSError, ValueError, TypeError):
        pass
    try:
        from nexus_agent_platform.temporary_worker_framework import provider_registry
        providers = provider_registry()
        for provider in ("modal", "kaggle"):
            if provider not in providers:
                continue
            env_id = f"worker_provider_{provider}"
            if any(row["environment_id"] == env_id for row in entries):
                continue
            add(env_id, f"{provider.title()} worker provider", "PROVIDER", "SYSTEMS", "CLOUD_PROFILE",
                "WEEKLY", "WEEKLY", ["nexus_canonical_runtime"], cost=True, quota=True,
                notes="Discovered from the existing Systems temporary-worker provider registry.")
    except Exception:
        pass
    return entries


def load_registry() -> tuple[list[dict[str, Any]], bool]:
    event = _latest_event("systems_environment_registry_snapshot")
    if event and isinstance(event.get("payload", {}).get("environments"), list):
        registry = event["payload"]["environments"]
        known = {row.get("environment_id") for row in registry}
        additions = [row for row in _discover_registry() if row.get("environment_id") not in known]
        # Migrate prior config-only observations to the closed-state contract.
        probe_revision_changed = False
        for row in registry:
            env_id = str(row.get("environment_id") or "")
            if row.get("probe_revision") != 3 or row.get("closed_state_map") != _closed_map_for(env_id):
                row.update({"probe_revision": 3, "closed_state_map": _closed_map_for(env_id),
                            "current_state": "NOT_CONFIGURED", "evidence_status": "PARTIAL",
                            "reason": "Closed-state health probe migration is due.",
                            "next_workflow": f"{env_id.upper()}_CLOSED_CHECK_MIGRATION",
                            "last_check": None, "next_check": _iso(), "updated_at": _iso()})
                probe_revision_changed = True
        if additions:
            registry.extend(additions)
        if additions or probe_revision_changed:
            saved = _event("systems_environment_registry_snapshot", {"schema_version": 1,
                "authoritative": True, "environments": registry}, title="Systems registry discovery update",
                summary=f"Registered {len(additions)} new environments and invalidated {int(probe_revision_changed)} prior config-only health records.", event_id=str(event["id"]))
            verify = _latest_event("systems_environment_registry_snapshot")
            if not verify or verify.get("id") != saved.get("id"):
                raise RuntimeError("systems_registry_discovery_readback_mismatch")
            LOCAL_MIRROR.parent.mkdir(parents=True, exist_ok=True)
            LOCAL_MIRROR.write_text(json.dumps({"authority": "SUPABASE:nexus_events", "event_id": saved["id"],
                "updated_at": _iso(), "environments": registry}, indent=2) + "\n")
        return registry, True
    # First-run bootstrap is based only on detected canonical resources. If a
    # prior canonical run left a verified local projection without its event
    # pointer, republish that exact projection and verify it by stable ID.
    registry = []
    try:
        cached = json.loads(LOCAL_MIRROR.read_text())
        if cached.get("authority") == "SUPABASE:nexus_events" and isinstance(cached.get("environments"), list):
            registry = cached["environments"]
    except (OSError, ValueError, TypeError):
        pass
    if not registry:
        registry = _discover_registry()
    known = {row.get("environment_id") for row in registry}
    registry.extend(row for row in _discover_registry() if row.get("environment_id") not in known)
    saved = _event("systems_environment_registry_snapshot",
                   {"schema_version": 1, "authoritative": True, "environments": registry},
                   title="Systems environment registry initialized",
                   summary=f"Registered {len(registry)} discovered Nexus environments.", event_key="environment-registry")
    LOCAL_MIRROR.parent.mkdir(parents=True, exist_ok=True)
    LOCAL_MIRROR.write_text(json.dumps({"authority": "SUPABASE:nexus_events", "event_id": saved["id"],
                                        "updated_at": _iso(), "environments": registry}, indent=2) + "\n")
    readback = _latest_event("systems_environment_registry_snapshot")
    if not readback or readback.get("id") != saved.get("id"):
        raise RuntimeError("systems_registry_readback_mismatch")
    LOCAL_MIRROR.parent.mkdir(parents=True, exist_ok=True)
    LOCAL_MIRROR.write_text(json.dumps({"authority": "SUPABASE:nexus_events", "event_id": saved["id"],
                                        "updated_at": _iso(), "environments": registry}, indent=2) + "\n")
    return registry, True


def _command(args: list[str], timeout: int = 8) -> tuple[int | None, str]:
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=timeout, check=False)
        return result.returncode, (result.stdout or "")[-20000:]
    except Exception as exc:
        return None, type(exc).__name__


def _close_observation(env: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    """Translate probe evidence into one closed operational state and route."""
    old = result.get("status")
    env_id = str(env.get("environment_id") or "")
    state = old if old in CHECK_STATES else None
    reason = result.get("reason")
    next_workflow = result.get("next_workflow")
    evidence_status = result.get("evidence_status", "COMPLETE")
    confidence = result.get("confidence", "HIGH")
    if state is None:
        state = "CHECK_ERROR"
        evidence_status = "PARTIAL"
        confidence = "LOW"
        reason = reason or "Probe returned a state outside the closed operational state set."
        next_workflow = "SYSTEMS_CHECKER_REPAIR"
    finding = result.get("finding") or {}
    if finding.get("type") == "WEBULL_CREDENTIAL_REFERENCE_UNRESOLVED":
        state, next_workflow = "BLOCKED_BY_AUTH", "WEBULL_APPROVED_CREDENTIAL_REFERENCE_RECOVERY"
        reason = "Approved credential references did not resolve all required components."
    elif finding.get("type") == "OCI_READONLY_CLIENT_UNAVAILABLE":
        state, next_workflow = "CHECK_ERROR", "ORACLE_READONLY_CLIENT_RECOVERY"
        reason = "The OCI configuration exists but the scheduled read-only inventory client is unavailable."
        result.update({"target_state": "NOT_MEASURED", "checker_state": "CHECK_ERROR"})
    for item in result.get("checks", []):
        item_state = item.get("workflow_state")
        if item_state not in CHECK_STATES:
            value = item.get("value")
            if value is None or (isinstance(value, str) and value in {"NOT_MEASURED", "UNREADABLE"}):
                item["workflow_state"] = "CHECK_ERROR"
                item["evidence_status"] = "PARTIAL"
                item["confidence"] = "LOW"
                item["target_state"] = "NOT_MEASURED"
                item["checker_state"] = "CHECK_ERROR"
                item["next_workflow"] = "SYSTEMS_CHECKER_REPAIR"
                item["next_action_required"] = True
            else:
                item["workflow_state"] = ("CHECK_ERROR" if item.get("abnormal") and isinstance(value, str) and value in {"NOT_MEASURED", "UNREADABLE"}
                                          else "FAIL" if item.get("abnormal") else "PASS")
                item["evidence_status"] = "COMPLETE"
                item["confidence"] = "HIGH"
                item["next_workflow"] = _closed_map_for(env_id)[item["workflow_state"]]
                item["next_action_required"] = CLOSED_TRANSITIONS[item["workflow_state"]]["next_action_required"]
        item.pop("abnormal", None)
        item_state = item["workflow_state"]
        if item_state == "CHECK_ERROR":
            item.setdefault("target_state", "NOT_MEASURED")
            item.setdefault("checker_state", "CHECK_ERROR")
        item.setdefault("next_workflow", _closed_map_for(env_id)[item_state])
        item.setdefault("next_action_required", CLOSED_TRANSITIONS[item_state]["next_action_required"])
        if item_state in {"FAIL", "DEGRADED", "UNREACHABLE", "BLOCKED_BY_AUTH", "NOT_CONFIGURED",
                          "CHECK_ERROR", "STALE", "THRESHOLD_EXCEEDED", "DEPENDENCY_UNAVAILABLE"}:
            # A closed state is only useful when its route is specific to this
            # environment/check. Never persist the generic transition-table
            # placeholder as an operational destination.
            if item["next_workflow"] in {"DEGRADED_SERVICE_RECOVERY",
                                         "CONNECTIVITY_RECOVERY_RETRY_ONCE",
                                         "APPROVED_AUTH_REFERENCE_RECOVERY_RETRY_ONCE",
                                         "CONFIGURATION_RECOVERY_OR_REGISTRY_CORRECTION",
                                         "CHECKER_REPAIR_RETRY_ONCE", "STALE_STATE_RECOVERY",
                                         "THRESHOLD_SPECIFIC_CAPACITY_WORKFLOW", "DEPENDENCY_RECOVERY"}:
                item["next_workflow"] = _closed_map_for(env_id)[item_state]
        item.setdefault("reason", f"Check completed with {item_state}.")
    # The environment result reflects the highest-priority non-pass check;
    # individual measurements retain their own independent closed states.
    check_priority = ["UNREACHABLE", "CHECK_ERROR", "BLOCKED_BY_AUTH", "FAIL", "DEGRADED",
                      "THRESHOLD_EXCEEDED", "STALE", "NOT_CONFIGURED", "DEPENDENCY_UNAVAILABLE",
                      "NOT_EXPOSED_BY_PROVIDER", "NOT_APPLICABLE", "NOT_DUE", "PASS"]
    if result.get("checks"):
        candidates = [x for x in result["checks"] if x["workflow_state"] in CHECK_STATES]
        if state != "PASS":
            candidates.append({"workflow_state": state, "next_workflow": next_workflow or CLOSED_TRANSITIONS[state]["next_workflow"],
                               "reason": reason or f"Environment-level workflow condition: {state}.",
                               "next_action_required": CLOSED_TRANSITIONS[state]["next_action_required"]})
        selected = min(candidates,
                       key=lambda x: check_priority.index(x["workflow_state"]))
        state = selected["workflow_state"]
        next_workflow = selected["next_workflow"]
        reason = selected.get("reason")
    if finding.get("type") == "WEBULL_CREDENTIAL_REFERENCE_UNRESOLVED":
        state, next_workflow = "BLOCKED_BY_AUTH", "WEBULL_APPROVED_CREDENTIAL_REFERENCE_RECOVERY"
        reason = "Approved credential references did not resolve all required components."
    elif finding.get("type") == "OCI_READONLY_CLIENT_UNAVAILABLE":
        state, next_workflow = "CHECK_ERROR", "ORACLE_READONLY_CLIENT_RECOVERY"
        reason = "The OCI configuration exists but the scheduled read-only inventory client is unavailable."
        result.update({"target_state": "NOT_MEASURED", "checker_state": "CHECK_ERROR"})
    elif finding.get("type") == "OPEN_SYSTEMS_DIRECTIVE_AWAITING_CLAIM":
        state, next_workflow = "STALE", "SYSTEMS_DIRECTIVE_CLAIM_RECOVERY"
        reason = "An existing Systems directive is open and has not been claimed."
    transition = CLOSED_TRANSITIONS[state]
    result["status"] = state
    result["workflow_state"] = state
    result["evidence_status"] = evidence_status
    result["confidence"] = confidence
    result["reason"] = reason or (finding.get("type") if finding else f"{state} observation recorded")
    result["next_workflow"] = next_workflow or transition["next_workflow"] or _closed_map_for(env_id)[state]
    if state in {"FAIL", "DEGRADED", "UNREACHABLE", "BLOCKED_BY_AUTH", "NOT_CONFIGURED",
                 "CHECK_ERROR", "STALE", "THRESHOLD_EXCEEDED", "DEPENDENCY_UNAVAILABLE"}:
        if result["next_workflow"] in {"DEGRADED_SERVICE_RECOVERY",
                                       "CONNECTIVITY_RECOVERY_RETRY_ONCE",
                                       "APPROVED_AUTH_REFERENCE_RECOVERY_RETRY_ONCE",
                                       "CONFIGURATION_RECOVERY_OR_REGISTRY_CORRECTION",
                                       "CHECKER_REPAIR_RETRY_ONCE", "STALE_STATE_RECOVERY",
                                       "THRESHOLD_SPECIFIC_CAPACITY_WORKFLOW", "DEPENDENCY_RECOVERY"}:
            result["next_workflow"] = _closed_map_for(env_id)[state]
    result["next_action_required"] = transition["next_action_required"]
    if state == "CHECK_ERROR":
        result.setdefault("target_state", "NOT_MEASURED")
        result.setdefault("checker_state", "CHECK_ERROR")
    result["next_check_time"] = env.get("next_check") or _iso(_now() + timedelta(minutes=20))
    if state not in CHECK_STATES or (transition["next_action_required"] and not result["next_workflow"]):
        raise RuntimeError(f"systems_check_not_closed:{env_id}:{state}")
    return result


def _probe(env: dict[str, Any]) -> dict[str, Any]:
    env_id = env["environment_id"]
    result: dict[str, Any] = {"environment_id": env_id, "checked_at": _iso(), "status": "PASS", "checks": []}

    def check(name: str, value: Any, *, abnormal: bool = False, state: str | None = None,
              next_workflow: str | None = None, evidence_status: str = "COMPLETE",
              confidence: str = "HIGH", reason: str | None = None) -> None:
        workflow_state = state or ("FAIL" if abnormal else "PASS")
        if workflow_state not in CHECK_STATES:
            raise RuntimeError(f"undeclared_systems_check_state:{env_id}:{name}:{workflow_state}")
        item = {"check": name, "value": value, "abnormal": abnormal,
                "workflow_state": workflow_state,
                "evidence_status": evidence_status, "confidence": confidence}
        item["next_workflow"] = next_workflow or _closed_map_for(env_id)[workflow_state]
        if reason:
            item["reason"] = reason
        result["checks"].append(item)
        if abnormal:
            result["status"] = state or "FAIL"

    if env_id == "hermes_mac":
        rc, process_list = _command(["/bin/ps", "-axo", "command"], timeout=4)
        process_present = rc == 0 and any(token in process_list for token in
            ("hermes-gateway-adapter.js", "services.nexus_mcp.http_server", ".local/bin/hermes"))
        check("HERMES_MAC_PROCESS", process_present, abnormal=not process_present,
              state="FAIL" if not process_present else "PASS",
              next_workflow="HERMES_MAC_RUNTIME_RECOVERY" if not process_present else None,
              reason="Local Hermes bridge/runtime process matched." if process_present else "No approved local Hermes process matched.")
        hermes_bin = shutil.which("hermes") or str(Path.home() / ".local/bin/hermes")
        if Path(hermes_bin).exists():
            version_rc, version_out = _command([hermes_bin, "--version"], timeout=4)
            version_ok = version_rc == 0 and bool(version_out.strip())
            check("HERMES_MAC_VERSION", version_out.splitlines()[0][:160] if version_ok else "NOT_MEASURED",
                  abnormal=not version_ok, state="PASS" if version_ok else "CHECK_ERROR",
                  next_workflow=None if version_ok else "HERMES_MAC_CHECKER_REPAIR",
                  evidence_status="COMPLETE" if version_ok else "PARTIAL", confidence="HIGH" if version_ok else "LOW",
                  reason="Version query completed." if version_ok else "Hermes version command did not complete within the bounded check.")
            result["hermes_mac_version"] = version_out.splitlines()[0][:160] if version_ok else None
        else:
            check("HERMES_MAC_VERSION", "NOT_MEASURED", abnormal=True, state="NOT_CONFIGURED",
                  next_workflow="HERMES_MAC_CLI_CONFIGURATION", evidence_status="PARTIAL", confidence="HIGH",
                  reason="Hermes CLI path is not configured on this host.")
        # A read-only MCP listener probe proves transport only; it does not issue
        # an LLM request or claim provider/model health.
        try:
            request = urllib.request.Request("http://127.0.0.1:18765/mcp", method="GET")
            with urllib.request.urlopen(request, timeout=2) as response:
                code = response.status
        except urllib.error.HTTPError as exc:
            code = exc.code
        except Exception as exc:
            code = None
            result["hermes_mac_runtime_error_class"] = type(exc).__name__
        listener_ok = code in {200, 401, 405, 406}
        check("HERMES_MAC_RUNTIME", {"process_present": process_present, "mcp_listener_http": code},
              abnormal=not listener_ok, state="PASS" if listener_ok else "UNREACHABLE",
              next_workflow=None if listener_ok else "HERMES_MAC_RUNTIME_RECOVERY",
              evidence_status="TRANSPORT_ONLY" if listener_ok else "PARTIAL", confidence="HIGH" if listener_ok else "MEDIUM",
              reason="Local Hermes bridge process is present and the MCP listener responds." if listener_ok else "Local Hermes MCP listener did not answer the bounded probe.")
        function_state = "BLOCKED_BY_AUTH" if code == 401 else "PASS" if code in {200, 405, 406} else "UNREACHABLE"
        check("HERMES_MAC_FUNCTION_TEST", f"HTTP_{code}" if code is not None else "NOT_MEASURED",
              abnormal=function_state != "PASS", state=function_state,
              next_workflow="HERMES_MAC_AUTHENTICATED_FUNCTION_TEST" if code == 401 else None if function_state == "PASS" else "HERMES_MAC_RUNTIME_RECOVERY",
              evidence_status="AUTH_GATE_RESPONDED" if code == 401 else "TRANSPORT_ONLY" if function_state == "PASS" else "PARTIAL",
              confidence="HIGH" if listener_ok else "MEDIUM",
              reason="MCP endpoint responded with an auth challenge; no credentialed tool call or provider inference was attempted." if code == 401 else
              "MCP listener responded; no provider inference was requested." if function_state == "PASS" else "MCP listener did not answer the bounded read-only probe.")
        check("HERMES_MAC_PROVIDER_HEALTH", "NOT_MEASURED", abnormal=True, state="NOT_CONFIGURED",
              next_workflow="HERMES_MAC_PROVIDER_HEALTH_PROBE_CONFIGURATION", evidence_status="PARTIAL", confidence="HIGH",
              reason="No approved zero-cost provider health probe is registered; no model request was issued.")
        return _close_observation(env, result)
    if env_id == "hermes_oracle":
        rc, output = _command([sys.executable, str(ROOT / "scripts/ops/check_remote_stack_health.py")], timeout=22)
        try:
            payload = json.loads(output) if rc == 0 else {}
        except ValueError:
            payload = {}
        oracle = payload.get("oracle", {})
        host_ok = oracle.get("status") == "PASS"
        check("HERMES_ORACLE_HOST_REACHABLE", host_ok, abnormal=not host_ok,
              state="PASS" if host_ok else "UNREACHABLE", next_workflow=None if host_ok else "ORACLE_CONNECTIVITY_RECOVERY",
              evidence_status="COMPLETE" if host_ok else "PARTIAL", reason="Bounded read-only SSH probe completed." if host_ok else "Read-only SSH probe did not complete.")
        container = str(oracle.get("hermes") or "")
        container_ok = container.startswith("running:")
        check("HERMES_ORACLE_CONTAINER", "RUNNING" if container_ok else "NOT_MEASURED", abnormal=not container_ok,
              state="PASS" if container_ok else "FAIL", next_workflow=None if container_ok else "HERMES_CONTAINER_RECOVERY",
              evidence_status="COMPLETE" if container_ok else "PARTIAL", reason="Existing Hermes container is running." if container_ok else "Hermes container state was not running or not returned.")
        version = str(oracle.get("hermes_version") or "")
        version_ok = bool(version)
        check("HERMES_ORACLE_VERSION", version if version_ok else "NOT_MEASURED", abnormal=not version_ok,
              state="PASS" if version_ok else "CHECK_ERROR", next_workflow=None if version_ok else "HERMES_ORACLE_CHECKER_REPAIR",
              evidence_status="COMPLETE" if version_ok else "PARTIAL", reason="Remote version query completed." if version_ok else "Hermes version query did not return a value.")
        health_ok = oracle.get("hermes_health") in {"HTTP_200", "PASS"}
        check("HERMES_ORACLE_FUNCTION_TEST", oracle.get("hermes_health") or "NOT_MEASURED", abnormal=not health_ok,
              state="PASS" if health_ok else "DEGRADED", next_workflow=None if health_ok else "HERMES_ORACLE_RUNTIME_RECOVERY",
              evidence_status="HEALTH_ENDPOINT_ONLY" if health_ok else "PARTIAL", reason="Hermes health endpoint returned HTTP 200; no model request was issued." if health_ok else "Hermes health endpoint did not return HTTP 200.")
        result.update({"hermes_oracle_host_state": "PASS" if host_ok else "UNREACHABLE",
            "hermes_oracle_container_state": "PASS" if container_ok else "FAIL",
            "hermes_oracle_runtime_state": "PASS" if container_ok and health_ok else "DEGRADED",
            "hermes_oracle_version_state": "PASS" if version_ok else "CHECK_ERROR",
            "hermes_oracle_version": version if version_ok else None,
            "hermes_oracle_function_state": "PASS" if health_ok else "DEGRADED"})
        return _close_observation(env, result)

    if env_id == "local_host":
        rc, out = _command(["/usr/bin/uptime"])
        check("uptime_command", "AVAILABLE" if rc == 0 else "NOT_MEASURED", abnormal=rc != 0,
              state="PASS" if rc == 0 else "CHECK_ERROR", next_workflow=None if rc == 0 else "MAC_HOST_CHECKER_REPAIR",
              evidence_status="COMPLETE" if rc == 0 else "PARTIAL")
        boot_rc, boot_out = _command(["/usr/sbin/sysctl", "-n", "kern.boottime"])
        check("last_reboot", boot_out.strip() if boot_rc == 0 else "NOT_MEASURED", abnormal=boot_rc != 0,
              state="PASS" if boot_rc == 0 else "CHECK_ERROR", next_workflow=None if boot_rc == 0 else "MAC_HOST_CHECKER_REPAIR",
              evidence_status="COMPLETE" if boot_rc == 0 else "PARTIAL")
        prior = env.get("last_check")
        crash_root = Path("/Library/Logs/DiagnosticReports")
        crash_files = []
        if crash_root.is_dir() and prior:
            try:
                since = datetime.fromisoformat(str(prior).replace("Z", "+00:00")).timestamp()
                crash_files = [p.name for p in crash_root.iterdir() if p.is_file() and p.stat().st_mtime > since]
            except Exception:
                check("crash_since_last_check", "NOT_MEASURED", abnormal=True, state="CHECK_ERROR",
                      next_workflow="MAC_CRASH_LOG_CHECKER_REPAIR", evidence_status="PARTIAL")
        if not any(item["check"] == "crash_since_last_check" for item in result["checks"]):
            check("crash_since_last_check", bool(crash_files), abnormal=bool(crash_files),
                  state="FAIL" if crash_files else "PASS", next_workflow="MAC_CRASH_WORKFLOW" if crash_files else None,
                  reason="New diagnostic reports found since the prior check." if crash_files else "No new diagnostic reports found since the prior check.")
        try:
            load1, _, _ = os.getloadavg()
            cores = os.cpu_count() or 1
            cpu_over = load1 > max(cores * 1.5, 4)
            check("cpu_state", {"load_1m": load1, "logical_cores": cores}, abnormal=cpu_over,
                  state="THRESHOLD_EXCEEDED" if cpu_over else "PASS", next_workflow="MAC_CAPACITY_WORKFLOW" if cpu_over else None)
        except Exception as exc:
            check("cpu_state", type(exc).__name__, abnormal=True, state="CHECK_ERROR", next_workflow="MAC_HOST_CHECKER_REPAIR",
                  evidence_status="PARTIAL", confidence="LOW")
        total_rc, total_out = _command(["/usr/sbin/sysctl", "-n", "hw.memsize"])
        vm_rc, vm_out = _command(["/usr/bin/vm_stat"])
        try:
            total_bytes = int(total_out.strip())
            page_size = int(re.search(r"page size of (\d+) bytes", vm_out).group(1))
            pages = {name: int(value.replace(".", "")) for name, value in re.findall(r"Pages ([a-z ]+):\s+(\d+)\.", vm_out)}
            available = sum(pages.get(k, 0) for k in ("free", "inactive", "speculative", "purgeable")) * page_size
            used_fraction = 1 - (available / total_bytes)
            memory_state = "THRESHOLD_EXCEEDED" if used_fraction >= 0.90 else "PASS"
            check("memory_state", {"used_fraction": round(used_fraction, 4), "total_bytes": total_bytes},
                  abnormal=memory_state != "PASS", state=memory_state,
                  next_workflow="MEMORY_CAPACITY_WORKFLOW" if memory_state != "PASS" else None)
        except Exception as exc:
            check("memory_state", type(exc).__name__, abnormal=True, state="CHECK_ERROR", next_workflow="MAC_MEMORY_CHECKER_REPAIR",
                  evidence_status="PARTIAL", confidence="LOW")
        swap_rc, swap_out = _command(["/usr/sbin/sysctl", "vm.swapusage"])
        swap_match = re.search(r"used\s*=\s*([0-9.]+)([MG])", swap_out)
        if swap_rc == 0 and swap_match:
            swap_gb = float(swap_match.group(1)) * (1 if swap_match.group(2) == "G" else 0.001)
            swap_state = "THRESHOLD_EXCEEDED" if swap_gb >= 4 else "PASS"
            check("swap_state", {"used_gb": swap_gb}, abnormal=swap_state != "PASS", state=swap_state,
                  next_workflow="MEMORY_CAPACITY_WORKFLOW" if swap_state != "PASS" else None)
        else:
            check("swap_state", "NOT_MEASURED", abnormal=True, state="CHECK_ERROR", next_workflow="MAC_SWAP_CHECKER_REPAIR",
                  evidence_status="PARTIAL", confidence="LOW")
        net_rc, net_out = _command(["/sbin/route", "-n", "get", "default"])
        check("network_state", "PASS" if net_rc == 0 else "NOT_MEASURED", abnormal=net_rc != 0,
              state="PASS" if net_rc == 0 else "UNREACHABLE", next_workflow=None if net_rc == 0 else "MAC_NETWORK_RECOVERY",
              evidence_status="COMPLETE" if net_rc == 0 else "PARTIAL")
        rc, out = _command(["/bin/df", "-k", str(ROOT)])
        free_kb = None
        if rc == 0:
            try:
                free_kb = int(out.splitlines()[-1].split()[3])
            except (ValueError, IndexError):
                pass
        disk_state = "CHECK_ERROR" if free_kb is None else "THRESHOLD_EXCEEDED" if free_kb < 2_000_000 else "PASS"
        check("canonical_disk_free_kb", free_kb if free_kb is not None else "NOT_MEASURED",
              abnormal=disk_state != "PASS", state=disk_state,
              next_workflow="MAC_DISK_CHECKER_REPAIR" if disk_state == "CHECK_ERROR" else "STORAGE_CAPACITY_WORKFLOW" if disk_state == "THRESHOLD_EXCEEDED" else None,
              evidence_status="COMPLETE" if free_kb is not None else "PARTIAL")
    elif env_id == "nexus_canonical_runtime":
        check("checkout_present", ROOT.is_dir(), abnormal=not ROOT.is_dir())
        check("scheduler_entrypoint_present", (ROOT / "scripts/run_continuous_operating_kernel.py").is_file(), abnormal=not (ROOT / "scripts/run_continuous_operating_kernel.py").is_file())
    elif env_id == "canonical_scheduler":
        rc, out = _command(["/bin/launchctl", "list"])
        loaded = rc == 0 and "com.nexus.continuous-loop" in out
        # launchctl output can exceed the capped tail; query the exact label too.
        exact_rc, exact = _command(["/bin/launchctl", "list", "com.nexus.continuous-loop"])
        loaded = loaded or exact_rc == 0 and "com.nexus.continuous-loop" in exact
        check("canonical_scheduler_loaded", loaded, abnormal=not loaded)
    elif env_id == "supabase_control_plane":
        query = urllib.parse.urlencode({"select": "id", "limit": "1"})
        try:
            rows = _supabase_request(f"nexus_events?{query}")
            check("supabase_read", "PASS" if isinstance(rows, list) else "NOT_MEASURED", abnormal=not isinstance(rows, list))
        except Exception as exc:
            check("supabase_read", type(exc).__name__, abnormal=True)
    elif env_id == "supabase_egress_guard":
        try:
            sys.path.insert(0, str(ROOT / "scripts"))
            from nexus_agent_platform.supabase_egress_guard import snapshot as egress_snapshot, safe_mode_enabled, set_safe_mode
            sample = egress_snapshot()
            if sample.get("state") == "CRITICAL" and not safe_mode_enabled():
                set_safe_mode(True, reason="SYSTEMS_CRITICAL_EGRESS_THRESHOLD")
            sample["safe_mode_enabled"] = safe_mode_enabled()
            state = str(sample.get("state") or "NORMAL")
            mapped = {"NORMAL": "PASS", "ELEVATED": "DEGRADED", "HIGH": "THRESHOLD_EXCEEDED", "CRITICAL": "THRESHOLD_EXCEEDED"}.get(state, "CHECK_ERROR")
            check("daily_supabase_rest_response_bytes", {key: sample.get(key) for key in
                  ("day", "request_count", "approx_bytes", "large_query_count", "retry_count", "cache_hits", "cache_lookups", "state", "thresholds_bytes", "safe_mode_enabled")},
                  abnormal=mapped != "PASS", state=mapped,
                  next_workflow="SUPABASE_EGRESS_BUDGET_REVIEW" if mapped in {"DEGRADED", "THRESHOLD_EXCEEDED"} else None,
                  evidence_status="LOCAL_RESPONSE_BODY_ESTIMATE", confidence="MEDIUM",
                  reason="Counts Python client response bodies only; provider billing metrics and frontend requests are not included.")
        except Exception as exc:
            check("egress_guard_read", type(exc).__name__, abnormal=True, state="CHECK_ERROR",
                  next_workflow="SUPABASE_EGRESS_GUARD_RECOVERY", evidence_status="PARTIAL", confidence="LOW")
    elif env_id == "notebooklm":
        try:
            settings_rows = _supabase_request("research_notebooklm_automation_settings?settings_id=eq.NOTEBOOKLM_RESEARCH&select=settings_id,enabled,automation_mode,preferred_path,public_sources_only,sensitive_client_data_allowed,destructive_notebook_actions_allowed,sharing_actions_allowed,max_imported_sources_per_pass,max_research_passes_per_gap,max_gaps_per_notebook_session") or []
            sessions = _supabase_request("research_notebooklm_sessions?select=research_session_id,status,automation_path,started_at,completed_at,sources_imported&order=started_at.desc&limit=20") or []
            gaps = _supabase_request("nexus_feeder_research_gaps?select=status&limit=100") or []
            if not settings_rows:
                check("notebooklm_automation_settings", "NOT_CONFIGURED", abnormal=True, state="NOT_CONFIGURED",
                      next_workflow="NOTEBOOK_RESEARCH_RECOVERY", evidence_status="PARTIAL")
                return _close_observation(env, result)
            settings = settings_rows[0]
            mode = settings.get("automation_mode")
            safe = (mode == "AUTO_OPERATOR_BOUNDED" and bool(settings.get("enabled")) and
                    settings.get("preferred_path") == "CLI" and settings.get("public_sources_only") is True and
                    not settings.get("sensitive_client_data_allowed") and
                    not settings.get("destructive_notebook_actions_allowed") and not settings.get("sharing_actions_allowed") and
                    int(settings.get("max_imported_sources_per_pass", 99)) <= 5 and
                    int(settings.get("max_research_passes_per_gap", 99)) <= 2 and
                    int(settings.get("max_gaps_per_notebook_session", 99)) <= 5)
            check("notebooklm_automation_settings", {"mode": mode, "enabled": bool(settings.get("enabled")),
                "path": settings.get("preferred_path"), "public_sources_only": settings.get("public_sources_only"),
                "limits": [settings.get("max_imported_sources_per_pass"), settings.get("max_research_passes_per_gap"), settings.get("max_gaps_per_notebook_session")]},
                abnormal=not safe, state="PASS" if safe else "DEGRADED",
                next_workflow=None if safe else "NOTEBOOK_RESEARCH_RECOVERY")
            cli = Path.home() / ".nexus/venvs/notebooklm-py/bin/notebooklm"
            cli_rc, cli_output = _command([str(cli), "doctor"], timeout=90) if cli.is_file() else (None, "CLI_NOT_CONFIGURED")
            auth_pass = cli_rc == 0 and "All checks passed" in cli_output
            cli_state = "PASS" if auth_pass else ("NOT_CONFIGURED" if not cli.is_file() else "BLOCKED_BY_AUTH" if cli_rc not in (None, 0) else "CHECK_ERROR")
            check("notebooklm_cli_auth", "PASS" if auth_pass else cli_state,
                  abnormal=not auth_pass, state=cli_state,
                  next_workflow=None if auth_pass else "NOTEBOOK_CLI_RECOVERY",
                  evidence_status="COMPLETE" if auth_pass else "PARTIAL", confidence="HIGH" if auth_pass else "MEDIUM")
            latest = sessions[0] if sessions else {}
            open_count = sum(row.get("status") in {"OPEN", "IN_PROGRESS"} for row in gaps)
            last_import_session = next((session for session in sessions if any(
                row.get("indexing_status") == "ready" for row in (session.get("sources_imported") or []))), {})
            imported = bool(last_import_session)
            idle = not latest and not open_count
            check("notebooklm_source_search", "IDLE_HEALTHY" if idle else latest.get("status", "NO_SESSION"),
                  abnormal=bool(latest and latest.get("status") not in {"COMPLETED", "RESEARCH_REQUIRED"}),
                  state="PASS" if idle or latest.get("status") in {"COMPLETED", "RESEARCH_REQUIRED"} else "DEGRADED",
                  next_workflow=None if idle or latest.get("status") in {"COMPLETED", "RESEARCH_REQUIRED"} else "NOTEBOOK_RESEARCH_RECOVERY")
            check("notebooklm_source_import", "PASS" if imported else ("IDLE_HEALTHY" if idle else "RESEARCH_REQUIRED"),
                  abnormal=not imported and not idle, state="PASS" if imported or idle else "DEGRADED",
                  next_workflow=None if imported or idle else "NOTEBOOK_IMPORT_RECOVERY")
            check("notebooklm_indexing", "PASS" if imported else ("IDLE_HEALTHY" if idle else "NOT_CONFIRMED"),
                  abnormal=not imported and not idle, state="PASS" if imported or idle else "DEGRADED",
                  next_workflow=None if imported or idle else "NOTEBOOK_INDEXING_RECOVERY")
            returned = latest.get("status") in {"COMPLETED", "RESEARCH_REQUIRED"}
            check("notebooklm_reanalysis_and_return", "PASS" if returned else ("IDLE_HEALTHY" if idle else "NOT_CONFIRMED"),
                  abnormal=not idle and not returned, state="PASS" if idle or returned else "DEGRADED",
                  next_workflow=None if idle or returned else "RESEARCH_RETURN_RECOVERY")
            result.update({"automation_mode": mode, "active_path": settings.get("preferred_path"),
                "last_notebook_research_at": latest.get("started_at"), "last_source_imported_at": last_import_session.get("completed_at") if imported else None,
                "last_indexing_success_at": last_import_session.get("completed_at") if imported else None,
                "last_return_to_feeder_at": latest.get("completed_at") if latest.get("status") in {"COMPLETED", "RESEARCH_REQUIRED"} else None,
                "open_notebook_gaps": open_count, "completed_notebook_gaps": sum(row.get("status") == "COMPLETED" for row in gaps),
                "blocked_notebook_gaps": sum(row.get("status") == "BLOCKED_EXTERNAL" for row in gaps),
                "failed_notebook_gaps": sum(row.get("status") == "FAILED_RETRYABLE" for row in gaps),
                "last_research_session_id": latest.get("research_session_id"), "new_browser_created": False})
        except Exception as exc:
            check("notebooklm_automation_probe", type(exc).__name__, abnormal=True, state="CHECK_ERROR",
                  next_workflow="NOTEBOOK_RESEARCH_RECOVERY", evidence_status="PARTIAL", confidence="LOW")
    elif env_id == "research_runtime":
        progress = ROOT / "reports/runtime/nexus_research_wake_progress.json"
        check("research_runtime_configured", (ROOT / "scripts/research/research_case_engine.py").is_file())
        check("last_research_progress_present", progress.is_file(), abnormal=not progress.is_file())
        if progress.is_file():
            try:
                payload = json.loads(progress.read_text())
                progress_state = payload.get("state") or payload.get("status")
                recognized = {"ACTIVE", "RUNNING", "WAITING", "COMPLETED", "COMPLETE", "IDLE", "SCHEDULED", "HEARTBEAT"}
                progress_state_valid = str(progress_state or "").strip().upper() in recognized
                check("last_research_progress_state", progress_state if progress_state_valid else "STATE_NOT_RECOGNIZED",
                      abnormal=not progress_state_valid, state="PASS" if progress_state_valid else "DEGRADED",
                      next_workflow=None if progress_state_valid else "RESEARCH_PROGRESS_STATE_REPAIR",
                      evidence_status="COMPLETE" if progress_state_valid else "PARTIAL", confidence="HIGH" if progress_state_valid else "MEDIUM",
                      reason="Research progress state is recognized." if progress_state_valid else "Progress record contains no recognized runtime state; preserve the record and repair its producer.")
            except Exception:
                check("last_research_progress_state", "UNREADABLE", abnormal=True)
    elif env_id == "department_continuation_runtime":
        check("continuation_entrypoint_present", (ROOT / "scripts/operations/department_handoff_continuation.py").is_file(), abnormal=not (ROOT / "scripts/operations/department_handoff_continuation.py").is_file())
        try:
            from research import research_case_engine as cases
            case = cases.get_case_control("rcase_98d9635c39cf3ae5a4")
            directives = (case or {}).get("department_requests", [])
            open_systems = [row for row in directives if row.get("department") == "SYSTEMS" and row.get("status") == "OPEN"]
            check("active_systems_directives", len(open_systems))
            if open_systems:
                result["status"] = "STALE"
                result["finding"] = {"type": "OPEN_SYSTEMS_DIRECTIVE_AWAITING_CLAIM", "case_id": case.get("case_id") or case.get("id"),
                                     "directive_id": open_systems[0].get("request_id"), "classification": "SYSTEMS_PROJECT",
                                     "next_action": "Canonical scheduler claims the existing directive.",
                                     "next_workflow": "SYSTEMS_DIRECTIVE_CLAIM_RECOVERY"}
        except Exception as exc:
            check("company_case_read", type(exc).__name__, abnormal=True)
    elif env_id == "webull_provider":
        try:
            from nexus_agent_platform.credential_control_plane import resolve
            payload = resolve("credential.webull.openapi.prod.v1")
            components = {key: bool(value.get("selected")) for key, value in (payload.get("components") or {}).items()}
            found = bool(components) and all(components.values())
            check("credential_components_present", components)
            if not found:
                result.update({"status": "BLOCKED_BY_AUTH", "finding": {"type": "WEBULL_CREDENTIAL_REFERENCE_UNRESOLVED",
                    "classification": "SYSTEMS_PROJECT", "next_action": "Continue the existing approved-location recovery directive; do not rotate credentials.",
                    "next_workflow": "WEBULL_APPROVED_CREDENTIAL_REFERENCE_RECOVERY"}})
        except Exception as exc:
            check("credential_resolver", type(exc).__name__, abnormal=True)
    elif env_id == "oanda_practice":
        check("connector_policy_present", (ROOT / "configs/oanda_connector_policy.json").is_file())
        check("practice_execution_only", True)
        result.update({"status": "NOT_CONFIGURED", "evidence_status": "PARTIAL", "confidence": "MEDIUM",
                       "reason": "Practice connector policy is present; a read-only authenticated health probe is not registered.",
                       "next_workflow": "OANDA_READONLY_HEALTH_PROBE_CONFIGURATION"})
    elif env_id == "oracle_cloud":
        config = Path.home() / ".oci/config"
        check("oci_config_present", config.is_file(), abnormal=not config.is_file(),
              state="PASS" if config.is_file() else "BLOCKED_BY_AUTH",
              next_workflow=None if config.is_file() else "ORACLE_APPROVED_AUTH_REFERENCE_RECOVERY")
        cli_available = shutil.which("oci") is not None
        check("read_only_inventory_capability", cli_available, abnormal=not cli_available,
              state="PASS" if cli_available else "CHECK_ERROR",
              next_workflow=None if cli_available else "ORACLE_READONLY_CLIENT_RECOVERY",
              reason="Read-only inventory CLI is available." if cli_available else "OCI config exists but the CLI is missing from the scheduled runtime.")
        if not cli_available:
            result["finding"] = {"type": "OCI_READONLY_CLIENT_UNAVAILABLE", "classification": "SYSTEMS_PROJECT",
                "project_id": "ORACLE_COST_AND_CAPACITY",
                "next_action": "Recover the previously working OCI SDK environment or repair an isolated read-only OCI client, then run list-only instance and volume inventory using existing ~/.oci/config; do not modify resources."}
        rc, health_text = _command([sys.executable, str(ROOT / "scripts/ops/check_remote_stack_health.py")], timeout=22)
        try:
            remote = json.loads(health_text) if rc == 0 else {}
        except ValueError:
            remote = {}
        remote_oracle = remote.get("oracle", {})
        host_reachable = remote_oracle.get("status") == "PASS"
        check("ORACLE_HOST_REACHABLE", host_reachable, abnormal=not host_reachable,
              state="PASS" if host_reachable else "UNREACHABLE",
              next_workflow=None if host_reachable else "ORACLE_CONNECTIVITY_RECOVERY",
              evidence_status="COMPLETE" if host_reachable else "PARTIAL",
              reason="Read-only SSH host probe completed." if host_reachable else "Read-only SSH host probe failed.")
        tunnel_ok = remote.get("local_oracle_tunnel") == "PASS"
        check("ORACLE_TUNNEL_STATE", remote.get("local_oracle_tunnel") or "NOT_MEASURED", abnormal=not tunnel_ok,
              state="PASS" if tunnel_ok else "UNREACHABLE", next_workflow=None if tunnel_ok else "ORACLE_TUNNEL_CONNECTIVITY_RECOVERY",
              evidence_status="COMPLETE" if tunnel_ok else "PARTIAL")
        resource_inventory_state = "PASS" if cli_available else "CHECK_ERROR"
        check("ORACLE_STORAGE_INVENTORY", "MEASURED" if cli_available else "NOT_MEASURED", abnormal=not cli_available,
              state=resource_inventory_state, next_workflow=None if cli_available else "ORACLE_READONLY_CLIENT_RECOVERY",
              evidence_status="COMPLETE" if cli_available else "PARTIAL",
              reason="OCI inventory capability is available." if cli_available else "Volumes and capacity were not measured because the read-only OCI client is unavailable.")
        check("ORACLE_COST_VISIBILITY", "VERIFIED_CHARGE_NOT_AVAILABLE", abnormal=not cli_available,
              state="CHECK_ERROR" if not cli_available else "NOT_EXPOSED_BY_PROVIDER",
              next_workflow="ORACLE_READONLY_CLIENT_RECOVERY" if not cli_available else "NONE_REQUIRED",
              evidence_status="PARTIAL" if not cli_available else "RESOURCE_INVENTORY_ONLY",
              reason="No billing amount is exposed by the read-only inventory route; no charge is inferred.")
        result["oracle_resource_risk"] = "INSTANCE_AND_VOLUME_INVENTORY_NOT_MEASURED"
        result["verified_charge"] = "NOT_AVAILABLE_FROM_CURRENT_READONLY_ROUTE"
    elif env_id == "netlify_deployment":
        check("deployment_config_present", (ROOT / "netlify.toml").is_file())
        check("netlify_cli_available", shutil.which("netlify") is not None)
        result.update({"status": "NOT_CONFIGURED", "evidence_status": "PARTIAL", "confidence": "MEDIUM",
                       "reason": "Deployment config and CLI presence were checked; authenticated read-only health probe is not registered.",
                       "next_workflow": "NETLIFY_READONLY_HEALTH_PROBE_CONFIGURATION"})
    elif env_id == "github_remote":
        check("github_remote_configured", True)
        result.update({"status": "NOT_CONFIGURED", "evidence_status": "PARTIAL", "confidence": "MEDIUM",
                       "reason": "Git remote configuration is present; authenticated remote health probe is not registered.",
                       "next_workflow": "GITHUB_READONLY_HEALTH_PROBE_CONFIGURATION"})
    elif env_id == "source_monitors":
        source_config = (ROOT / "configs/research_source_registry.json").is_file()
        youtube_config = (ROOT / "configs/youtube_channel_portfolio.json").is_file()
        monitor_state = (ROOT / "data/runtime/alpha_source_registry.json").is_file()
        check("research_source_registry_present", source_config, abnormal=not source_config)
        check("youtube_channel_registry_present", youtube_config, abnormal=not youtube_config)
        check("durable_monitor_state_present", monitor_state, abnormal=not monitor_state)
    elif env_id in {"artifact_storage", "log_storage"}:
        target = ROOT / ("artifacts" if env_id == "artifact_storage" else "reports/runtime")
        usage = shutil.disk_usage(target)
        check("storage_path_present", target.is_dir(), abnormal=not target.is_dir())
        check("filesystem_free_bytes", usage.free, abnormal=usage.free < 2_000_000_000)
    elif env_id.startswith("launchd_"):
        label = env.get("name")
        rc, out = _command(["/bin/launchctl", "list", str(label)])
        active = rc == 0 and str(label) in out
        check("launchd_service_loaded", active, abnormal=not active)
        if not active:
            result["finding"] = {"type": "REGISTERED_SERVICE_NOT_LOADED", "classification": "SYSTEMS_PROJECT",
                                  "next_action": f"Inspect the existing launchd service {label} and restore its approved runtime if still required."}
    elif env_id.startswith("provider_") or env_id.startswith("worker_provider_"):
        provider = env_id.removeprefix("provider_").removeprefix("worker_provider_")
        config = json.loads((ROOT / "configs/nexus_credential_registry.json").read_text())
        refs = [str(item.get("credential_id")) for item in config.get("credentials", [])
                if str(item.get("provider") or "").lower() == provider]
        try:
            from nexus_agent_platform.credential_control_plane import resolve
            components = []
            for reference in refs:
                resolved = resolve(reference)
                components.append({"credential_reference": reference,
                    "components_present": {key: bool(value.get("selected")) for key, value in resolved.get("components", {}).items()}})
            check("credential_reference_count", len(refs))
            check("credential_components", components)
            components_missing = any(not item.get("components_present") or not all(item["components_present"].values()) for item in components)
            result.update({"status": "BLOCKED_BY_AUTH" if components_missing else "NOT_CONFIGURED",
                           "evidence_status": "PARTIAL", "confidence": "MEDIUM",
                           "reason": "Approved credential reference is incomplete." if components_missing else
                           "Credential references are present but an authenticated provider health probe is not registered.",
                           "next_workflow": "APPROVED_AUTH_REFERENCE_RECOVERY" if components_missing else
                           f"{provider.upper()}_HEALTH_PROBE_CONFIGURATION"})
        except Exception as exc:
            check("credential_reference_resolution", type(exc).__name__)
            result.update({"status": "CHECK_ERROR", "evidence_status": "PARTIAL", "confidence": "LOW",
                           "reason": "Credential reference resolver failed before provider authentication could be tested.",
                           "next_workflow": "SYSTEMS_CREDENTIAL_RESOLVER_REPAIR", "target_state": "NOT_MEASURED", "checker_state": "CHECK_ERROR"})
    else:
        check("registered_profile", env.get("check_profile"))
        result.update({"status": "NOT_CONFIGURED", "evidence_status": "PARTIAL", "confidence": "LOW",
                       "reason": "No environment-specific deterministic health probe is registered.",
                       "next_workflow": f"{env_id.upper()}_CHECK_PROFILE_CONFIGURATION"})
    return _close_observation(env, result)


def _repair_actionable_incident_envelopes(run_id: str) -> int:
    """Upgrade older generic abnormal records to concrete safe Systems work."""
    from nexus_agent_platform.governed import persistence
    incidents = persistence.read_records("systems_incidents")
    latest: dict[str, dict[str, Any]] = {}
    for row in incidents:
        incident_id = str(row.get("incident_id") or "")
        if incident_id and incident_id not in latest:
            latest[incident_id] = row
    repaired = 0
    for row in latest.values():
        if row.get("systems_run_id") != run_id or row.get("environment_id") != "oracle_cloud":
            continue
        finding = row.get("finding") or {}
        if finding.get("type") == "OCI_READONLY_CLIENT_UNAVAILABLE":
            continue
        corrected = {**finding, "type": "OCI_READONLY_CLIENT_UNAVAILABLE",
            "classification": "SYSTEMS_PROJECT", "project_id": "ORACLE_COST_AND_CAPACITY",
            "next_action": "Recover the previously working OCI SDK environment or repair an isolated read-only OCI client, then run list-only instance and volume inventory using existing ~/.oci/config; do not modify resources."}
        row = {**row, "finding": corrected, "next_action": corrected["next_action"],
               "status": "ACTIONABLE_NOW", "updated_at": _iso(),
               "repair_reason": "Replaced generic fallback with exact read-only OCI capability repair."}
        persistence.append_record("systems_incidents", row)
        _event("systems_finding_classified", {"systems_run_id": run_id, "environment_id": "oracle_cloud",
            "finding": corrected, "workflow_state": "CHECK_ERROR", "finding_class": "SYSTEMS_PROJECT",
            "next_workflow": "ORACLE_READONLY_CLIENT_RECOVERY", "actionable": True,
            "next_action": corrected["next_action"]}, title="Systems Oracle continuation repaired",
            summary="Recorded the exact safe OCI read-only inventory repair action.",
            correlation_id=run_id, event_key=f"finding:{run_id}:oracle_cloud:action-repair")
        repaired += 1
    if repaired:
        _event("systems_project_active", {"systems_run_id": run_id, "system_project_id": "ORACLE_COST_AND_CAPACITY",
            "owner": "SYSTEMS", "status": "ACTIVE", "next_action": corrected["next_action"],
            "notebook_id": None, "notebook_sync": "NOT_CONFIGURED"},
            title="Systems project active: Oracle cost and capacity",
            summary="Oracle read-only inventory is an active Systems project with a concrete safe next action.",
            correlation_id=run_id, event_key=f"project:{run_id}:ORACLE_COST_AND_CAPACITY")
    return repaired


def _persist_observation(run_id: str, observation: dict[str, Any]) -> dict[str, Any]:
    saved = _event("systems_environment_check", {"systems_run_id": run_id, "observation": observation},
                   title=f"Systems check: {observation['environment_id']}",
                   summary=f"{observation['environment_id']} deterministic status {observation['status']}.",
                   correlation_id=run_id,
                   event_key=f"check:{run_id}:{observation['environment_id']}:{observation['checked_at']}")
    query = urllib.parse.urlencode({"select": "id,payload", "id": f"eq.{saved['id']}", "limit": "1"})
    rows = _supabase_request(f"nexus_events?{query}") or []
    if not rows or rows[0].get("payload") != saved.get("payload"):
        raise RuntimeError("systems_observation_readback_mismatch")
    return saved


def run_systems_cycle(*, scheduler: str, worker_id: str, max_checks: int = MAX_CHECKS_PER_WAKE) -> dict[str, Any]:
    """Called by the existing canonical continuous kernel on each scheduled wake."""
    now = _now()
    registry, _ = load_registry()
    active = [row for row in registry if row.get("active")]
    date_key = now.astimezone().date().isoformat()
    due = [row for row in active if row.get("check_frequency") == "CRITICAL" and
           (not row.get("last_check") or datetime.fromisoformat(row["last_check"].replace("Z", "+00:00")) + timedelta(minutes=20) <= now)]
    for row in active:
        frequency = row.get("check_frequency")
        if frequency == "CRITICAL":
            continue
        last = datetime.fromisoformat(row["last_check"].replace("Z", "+00:00")) if row.get("last_check") else None
        if frequency == "DAILY":
            due_today = not last or last.astimezone().date().isoformat() < date_key
        else:
            age_days = {"WEEKLY": 7, "MONTHLY": 30}.get(frequency, 1)
            due_today = not last or last + timedelta(days=age_days) <= now
        if due_today:
            due.append(row)
    frequency_rank = {"CRITICAL": 0, "DAILY": 1, "WEEKLY": 2, "MONTHLY": 3}
    due.sort(key=lambda row: (frequency_rank.get(str(row.get("criticality") or row.get("check_frequency")), 4),
        -int(bool(row.get("cost_tracked"))), -len(row.get("dependencies") or []),
        int(row.get("current_state") == "PASS"), str(row.get("environment_id") or "")))
    latest = _latest_event("systems_nightly_run")
    run = (latest or {}).get("payload", {}).get("run") if latest else None
    if not run:
        # Recover the already completed run from the canonical scheduler's
        # durable receipt and the registry's Supabase-verified per-environment
        # checkpoints. Immediately write the reconstructed checkpoint back to
        # Supabase under stable identity so subsequent resumes read Supabase.
        receipt_path = ROOT / "data/runtime/company_case_directive_runtime.jsonl"
        try:
            for line in reversed(receipt_path.read_text(encoding="utf-8", errors="ignore").splitlines()[-100:]):
                row = json.loads(line)
                prior = (row.get("result") or {}).get("systems_workflow") or {}
                if prior.get("status") != "COMPLETE_FOR_DATE" or not str(prior.get("systems_run_id", "")).startswith("sysrun_"):
                    continue
                completed_rows = [env for env in active if env.get("last_check") and
                                  datetime.fromisoformat(env["last_check"].replace("Z", "+00:00")).astimezone().date().isoformat() == date_key]
                run = {"systems_run_id": prior["systems_run_id"], "run_date": date_key,
                       "started_at": prior.get("checkpoint"), "last_checkpoint": prior.get("checkpoint"),
                       "status": "COMPLETE_FOR_DATE", "total_environments_due": len(completed_rows),
                       "environments_completed": len(completed_rows), "environments_remaining": 0,
                       "total_checks_planned": len(completed_rows), "checks_completed": len(completed_rows),
                       "checks_remaining": 0, "current_environment": None, "current_check": None,
                       "healthy_checks": prior.get("healthy_no_ai", 0), "abnormal_checks": prior.get("abnormal_checks", 0),
                       "ai_analyses": prior.get("ai_analyses", 0), "auto_repairs_attempted": 0,
                       "auto_repairs_succeeded": 0, "incidents_created": prior.get("abnormal_checks", 0),
                       "systems_projects_updated": 0, "handoffs_created": 0,
                       "environment_cursor": len(completed_rows), "check_cursor": 0,
                       "completed_environment_ids": [env["environment_id"] for env in completed_rows],
                       "migrated_from_verified_scheduler_receipt": True}
                saved_run = _event("systems_nightly_run", {"run": run}, title="Systems audit checkpoint migrated",
                    summary="Re-persisted the scheduler-verified audit checkpoint under stable identity.",
                    correlation_id=run["systems_run_id"], event_key=f"run:{run['systems_run_id']}")
                pointer = ROOT / "data/runtime/systems_nightly_run_pointer.json"
                pointer.parent.mkdir(parents=True, exist_ok=True)
                pointer.write_text(json.dumps({"event_id": saved_run["id"], "systems_run_id": run["systems_run_id"]}) + "\n")
                break
        except (OSError, ValueError, TypeError):
            run = None
    # Bootstrap the first audit on the first existing scheduler wake. Future
    # nightly audits begin at the governed local hour; incomplete runs always
    # resume under their original run id, even across a date boundary.
    start_new_nightly = (not run) or (run.get("status") == "COMPLETE_FOR_DATE" and
        run.get("run_date") != date_key and now.astimezone().hour >= NIGHTLY_LOCAL_HOUR)
    if start_new_nightly:
        run = {"systems_run_id": f"sysrun_{uuid.uuid4().hex[:16]}", "run_date": date_key,
               "started_at": _iso(now), "last_checkpoint": _iso(now), "status": "RUNNING",
               "total_environments_due": len(due), "environments_completed": 0,
               "environments_remaining": len(due), "total_checks_planned": len(due),
               "checks_completed": 0, "checks_remaining": len(due), "current_environment": None,
               "current_check": None, "healthy_checks": 0, "abnormal_checks": 0,
               "ai_analyses": 0, "auto_repairs_attempted": 0, "auto_repairs_succeeded": 0,
               "incidents_created": 0, "systems_projects_updated": 0, "handoffs_created": 0,
               "environment_cursor": 0, "check_cursor": 0, "completed_environment_ids": [],
               "scheduler": scheduler, "worker_id": worker_id}
        saved_run = _event("systems_nightly_run", {"run": run}, title="Systems nightly audit started",
               summary=f"Started checkpointed audit for {date_key}; {len(due)} environments due.", correlation_id=run["systems_run_id"],
               event_key=f"run:{run['systems_run_id']}")
        pointer = ROOT / "data/runtime/systems_nightly_run_pointer.json"
        pointer.parent.mkdir(parents=True, exist_ok=True)
        pointer.write_text(json.dumps({"event_id": saved_run["id"], "systems_run_id": run["systems_run_id"]}) + "\n")
    elif run.get("status") == "COMPLETE_FOR_DATE":
        already = set(run.get("completed_environment_ids") or [])
        invalid_checkpoints = {row["environment_id"] for row in active
                               if row["environment_id"] in already and
                               (not row.get("last_check") or row.get("probe_revision") != 3 or row.get("current_state") not in CHECK_STATES)}
        if invalid_checkpoints:
            already.difference_update(invalid_checkpoints)
            run["completed_environment_ids"] = sorted(already)
            run["environments_completed"] = len(already)
            run["checks_completed"] = len(already)
            retained = [row for row in active if row.get("environment_id") in already]
            run["healthy_checks"] = sum(1 for row in retained if row.get("current_state") == "PASS")
            run["abnormal_checks"] = sum(1 for row in retained if row.get("current_state") not in CHECK_STATES - {"PASS", "NOT_APPLICABLE", "NOT_DUE", "NOT_EXPOSED_BY_PROVIDER"})
            run["environments_checked"] = run["healthy_checks"]
            run["environments_skipped_with_valid_reason"] = 0
            run["environments_failed_with_continuation"] = run["abnormal_checks"]
        newly_due = [row for row in due if row["environment_id"] not in already]
        if newly_due:
            run["status"] = "RESUMING"
            run["total_environments_due"] = int(run.get("environments_completed", 0)) + len(newly_due)
            run["total_checks_planned"] = run["total_environments_due"]
            run["environments_remaining"] = len(newly_due)
            run["checks_remaining"] = len(newly_due)
            run["last_checkpoint"] = _iso()
            _event("systems_nightly_run", {"run": run}, title="Systems audit resumed for newly registered environments",
                   summary=f"Resumed {run['systems_run_id']} for {len(newly_due)} newly due environments.", correlation_id=run["systems_run_id"],
                   event_key=f"run:{run['systems_run_id']}")
    run_id = run["systems_run_id"]
    completed = set(run.get("completed_environment_ids") or [])
    run["environments_checked"] = int(run.get("healthy_checks", 0))
    run.setdefault("environments_skipped_with_valid_reason", 0)
    run["environments_failed_with_continuation"] = int(run.get("abnormal_checks", 0))
    run["coverage_accounting"] = {"checked": run["environments_checked"],
        "skipped_with_valid_reason": int(run.get("environments_skipped_with_valid_reason", 0)),
        "failed_with_continuation": run["environments_failed_with_continuation"],
        "due": int(run.get("total_environments_due", 0))}
    run["coverage_pass"] = (run["coverage_accounting"]["checked"] +
        run["coverage_accounting"]["skipped_with_valid_reason"] +
        run["coverage_accounting"]["failed_with_continuation"] +
        int(run.get("environments_remaining", 0)) == run["coverage_accounting"]["due"])
    if run.get("status") == "COMPLETE_FOR_DATE" and run.get("coverage_pass"):
        saved_run = _event("systems_nightly_run", {"run": run}, title="Systems nightly audit coverage reconciled",
            summary=f"Coverage reconciled: {run['environments_checked']} checked, {run['environments_skipped_with_valid_reason']} valid skips, {run['environments_failed_with_continuation']} failures continued.",
            correlation_id=run_id, event_key=f"run:{run_id}")
        pointer = ROOT / "data/runtime/systems_nightly_run_pointer.json"
        pointer.write_text(json.dumps({"event_id": saved_run["id"], "systems_run_id": run_id}) + "\n")
        report = {"systems_run_id": run_id, "run_date": run.get("run_date"),
            "run_start": run.get("started_at"), "run_end": run.get("completed_at"),
            "active_environments": len(active), "environments_due": run["total_environments_due"],
            "environments_checked": run["environments_checked"],
            "environments_skipped_with_valid_reason": run["environments_skipped_with_valid_reason"],
            "environments_failed_with_continuation": run["environments_failed_with_continuation"],
                "total_checks": run.get("deterministic_checks_total", 0), "healthy_checks": run["healthy_checks"],
            "abnormal_checks": run["abnormal_checks"], "ray_decisions_required": 0}
        _event("systems_morning_report", report, title=f"Systems morning report {run.get('run_date')}",
            summary="Reconciled Systems audit executive report.", correlation_id=run_id,
            event_key=f"report:{run_id}")
    completed_state_rows = [row for row in active if row.get("environment_id") in completed]
    closed_no_action = {"NOT_APPLICABLE", "NOT_DUE", "NOT_EXPOSED_BY_PROVIDER"}
    run["healthy_checks"] = sum(1 for row in completed_state_rows if row.get("current_state") == "PASS")
    run["abnormal_checks"] = sum(1 for row in completed_state_rows
        if row.get("current_state") in CHECK_STATES - {"PASS"} - closed_no_action)
    run["environments_checked"] = run["healthy_checks"]
    run["environments_skipped_with_valid_reason"] = sum(1 for row in completed_state_rows if row.get("current_state") in closed_no_action)
    run["environments_failed_with_continuation"] = run["abnormal_checks"]
    run["coverage_accounting"] = {"due": int(run.get("total_environments_due", 0)),
        "checked": run["environments_checked"], "failed_with_continuation": run["environments_failed_with_continuation"],
        "skipped_with_valid_reason": run["environments_skipped_with_valid_reason"]}
    run["coverage_pass"] = (run["coverage_accounting"]["checked"] + run["coverage_accounting"]["failed_with_continuation"] +
        run["coverage_accounting"]["skipped_with_valid_reason"] + int(run.get("environments_remaining", 0)) == run["coverage_accounting"]["due"])
    current_run_event = _latest_event("systems_nightly_run")
    if current_run_event:
        saved_run = _event("systems_nightly_run", {"run": run}, title="Systems nightly audit closed-state accounting",
            summary=f"Closed coverage: {run['environments_checked']} PASS, {run['environments_failed_with_continuation']} routed, {run['environments_skipped_with_valid_reason']} valid exclusions.",
            correlation_id=run_id, event_id=str(current_run_event["id"]))
        (ROOT / "data/runtime/systems_nightly_run_pointer.json").write_text(
            json.dumps({"event_id": saved_run["id"], "systems_run_id": run_id}) + "\n")
    if run.get("status") == "COMPLETE_FOR_DATE":
        report = {"systems_run_id": run_id, "run_date": run.get("run_date"), "run_start": run.get("started_at"),
            "run_end": run.get("completed_at"), "active_environments": len(active), "environments_due": run.get("total_environments_due"),
            "environments_checked": run["environments_checked"], "environments_skipped_with_valid_reason": run["environments_skipped_with_valid_reason"],
            "environments_failed_with_continuation": run["environments_failed_with_continuation"],
            "total_checks": run.get("deterministic_checks_total", 0), "healthy_checks": run["healthy_checks"],
            "abnormal_checks": run["abnormal_checks"], "top_findings": run.get("top_findings", []), "ray_decisions_required": 0}
        _event("systems_morning_report", report, title=f"Systems morning report {run.get('run_date')}",
            summary=f"{report['environments_checked']} PASS, {report['environments_failed_with_continuation']} routed conditions, no silent exclusions.",
            correlation_id=run_id, event_key=f"report:{run_id}")
    _repair_actionable_incident_envelopes(run_id)
    audit_complete = run.get("status") == "COMPLETE_FOR_DATE"
    if audit_complete:
        watchdog_rows = [row for row in active if row.get("check_frequency") == "CRITICAL" and
                         (not row.get("last_check") or datetime.fromisoformat(row["last_check"].replace("Z", "+00:00")) + timedelta(minutes=20) <= now)]
        watch_results = []
        for env in watchdog_rows:
            observation = _probe(env)
            saved = _persist_observation(run_id, observation)
            watch_results.append({"event_id": saved["id"], **observation})
            env["last_check"] = observation["checked_at"]
            env["next_check"] = _iso(now + timedelta(minutes=20))
            env["current_state"] = observation["status"]
        if watchdog_rows:
            latest_registry = _latest_event("systems_environment_registry_snapshot")
            persisted = latest_registry.get("payload", {}).get("environments", registry) if latest_registry else registry
            for target in persisted:
                updated = next((x for x in watchdog_rows if x["environment_id"] == target.get("environment_id")), None)
                if updated:
                    target.update({key: updated[key] for key in ("last_check", "next_check", "current_state")})
            saved_registry = _event("systems_environment_registry_snapshot", {"schema_version": 1, "authoritative": True,
                "environments": persisted}, title="Systems watchdog registry update", summary="Updated critical environment health timestamps.",
                event_id=str(latest_registry["id"]) if latest_registry else None,
                event_key=None if latest_registry else "environment-registry")
            LOCAL_MIRROR.write_text(json.dumps({"authority": "SUPABASE:nexus_events", "event_id": saved_registry.get("id"),
                "updated_at": _iso(), "environments": persisted}, indent=2) + "\n")
        return {"status": "COMPLETE_FOR_DATE", "systems_run_id": run_id, "scheduler": scheduler,
                "worker_id": worker_id, "registry_count": len(registry), "active_environments": len(active),
                "environments_due": 0, "environments_checked_this_wake": sum(1 for item in watch_results if item.get("status") == "PASS"),
                "checks_executed": sum(len(item.get("checks", [])) for item in watch_results),
                "healthy_no_ai": sum(1 for item in watch_results if item.get("status") == "PASS"),
                "abnormal_checks": sum(1 for item in watch_results if item.get("next_action_required")),
                "observations": watch_results, "checkpoint": run.get("last_checkpoint"),
                "next_environment": None, "next_check": "CRITICAL_WATCHDOG",
                "coverage_pass": (run.get("environments_checked", 0) + run.get("environments_skipped_with_valid_reason", 0) +
                                  run.get("environments_failed_with_continuation", 0) + run.get("environments_remaining", 0) ==
                                  run.get("total_environments_due", 0)),
                "morning_report_created": True, "ai_analyses": 0, "systems_continued": True}
    todo = [row for row in due if row["environment_id"] not in completed]
    batch = todo[:max(1, max_checks)]
    observations: list[dict[str, Any]] = []
    deterministic = 0
    healthy = 0
    abnormal = 0
    skipped = 0
    for index, env in enumerate(batch):
        run.update({"current_environment": env["environment_id"], "current_check": env.get("check_profile"),
                    "environment_cursor": run.get("checks_completed", 0), "check_cursor": 0})
        observation = _probe(env)
        deterministic += len(observation.get("checks", []))
        run["deterministic_checks_total"] = int(run.get("deterministic_checks_total", 0)) + len(observation.get("checks", []))
        saved = _persist_observation(run_id, observation)
        observations.append({"event_id": saved["id"], **observation})
        completed.add(env["environment_id"])
        env["last_check"] = observation["checked_at"]
        env["next_check"] = _iso(_next_due(now, str(env.get("check_frequency") or "DAILY")))
        env["current_state"] = observation["status"]
        env["last_known_good"] = observation if observation["status"] == "PASS" else env.get("last_known_good")
        if observation["status"] == "PASS":
            healthy += 1
            run["healthy_checks"] += 1
            run["environments_checked"] += 1
        elif observation["status"] in {"NOT_APPLICABLE", "NOT_DUE", "NOT_EXPOSED_BY_PROVIDER"} and not observation.get("next_action_required"):
            skipped += 1
            run["environments_skipped_with_valid_reason"] += 1
        else:
            abnormal += 1
            run["abnormal_checks"] += 1
            run["environments_failed_with_continuation"] += 1
            finding = observation.get("finding") or {"type": "CLOSED_STATE_CONTINUATION", "classification": "SYSTEMS_PROJECT",
                "workflow_state": observation["status"], "reason": observation.get("reason"),
                "next_workflow": observation.get("next_workflow"),
                "next_action": f"Execute {observation.get('next_workflow')} for {env['environment_id']}; then persist and continue the audit."}
            finding_event = _event("systems_finding_classified", {"systems_run_id": run_id,
                "environment_id": env["environment_id"], "finding": finding,
                "workflow_state": observation["workflow_state"],
                "finding_class": finding.get("classification", "SYSTEMS_PROJECT"),
                "next_workflow": observation.get("next_workflow"),
                "actionable": bool(observation.get("next_action_required")),
                "next_action": finding.get("next_action") or f"Execute {observation.get('next_workflow')} for {env['environment_id']}; then continue the audit."},
                title=f"Systems finding: {env['name']}", summary=f"Closed state {observation['workflow_state']} routes to {observation.get('next_workflow')}.",
                correlation_id=run_id, event_key=f"finding:{run_id}:{env['environment_id']}:{observation['checked_at']}")
            # Keep a compact local incident projection for existing Systems tools.
            from nexus_agent_platform.governed import persistence
            incident_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"nexus-systems-incident:{run_id}:{env['environment_id']}"))
            existing_incident = next((row for row in persistence.read_records("systems_incidents")
                                      if row.get("incident_id") == incident_id), None)
            if not existing_incident:
                persistence.append_record("systems_incidents", {"incident_id": incident_id,
                "systems_run_id": run_id, "environment_id": env["environment_id"], "finding": finding,
                "status": "ACTIONABLE_NOW", "finding_event_id": finding_event.get("id"),
                "next_action": finding.get("next_action"), "created_at": _iso()})
            run["incidents_created"] += 1
            run.setdefault("top_findings", []).append({"environment_id": env["environment_id"],
                "workflow_state": observation["workflow_state"], "reason": observation.get("reason"),
                "next_workflow": observation.get("next_workflow")})
        run["checks_completed"] = int(run.get("deterministic_checks_total", 0))
        run["environments_completed"] = len(completed)
        run["completed_environment_ids"] = sorted(completed)
        run["environments_remaining"] = max(0, run["total_environments_due"] - run["environments_completed"])
        run["checks_remaining"] = run["environments_remaining"]
        run["last_completed_environment"] = env["environment_id"]
        run["next_environment"] = batch[index + 1]["environment_id"] if index + 1 < len(batch) else (todo[index + 1]["environment_id"] if index + 1 < len(todo) else None)
        run["last_checkpoint"] = _iso()
        run["status"] = "RUNNING" if run["environments_remaining"] else "COMPLETE_FOR_DATE"
        if run["status"] == "COMPLETE_FOR_DATE":
            run["total_checks_planned"] = int(run.get("deterministic_checks_total", 0))
            run["checks_completed"] = int(run.get("deterministic_checks_total", 0))
            run["checks_remaining"] = 0
            run["completed_at"] = _iso()
        run["environments_checked"] = int(run.get("healthy_checks", 0))
        run["environments_failed_with_continuation"] = int(run.get("abnormal_checks", 0))
        run["environments_skipped_with_valid_reason"] = int(run.get("environments_skipped_with_valid_reason", 0))
        run["coverage_accounting"] = {"due": int(run.get("total_environments_due", 0)),
            "checked": run["environments_checked"],
            "failed_with_continuation": run["environments_failed_with_continuation"],
            "skipped_with_valid_reason": run["environments_skipped_with_valid_reason"]}
        run["coverage_pass"] = (run["coverage_accounting"]["checked"] +
            run["coverage_accounting"]["failed_with_continuation"] +
            run["coverage_accounting"]["skipped_with_valid_reason"] +
            run["environments_remaining"] == run["coverage_accounting"]["due"])
        saved_run = _event("systems_nightly_run", {"run": run}, title="Systems nightly audit checkpoint",
               summary=f"Checkpointed {run['checks_completed']}/{run['total_checks_planned']} environment checks.", correlation_id=run_id,
               event_key=f"run:{run_id}")
        pointer = ROOT / "data/runtime/systems_nightly_run_pointer.json"
        pointer.write_text(json.dumps({"event_id": saved_run["id"], "systems_run_id": run_id}) + "\n")
        # The current registry snapshot remains one authoritative row in Supabase.
        registry_event = _latest_event("systems_environment_registry_snapshot")
        updated_registry = registry_event.get("payload", {}).get("environments", registry) if registry_event else registry
        for registered in updated_registry:
            if registered.get("environment_id") == env["environment_id"]:
                registered.update({k: env[k] for k in ("last_check", "next_check", "current_state", "last_known_good", "updated_at") if k in env})
        registry_saved = _event("systems_environment_registry_snapshot", {"schema_version": 1, "authoritative": True,
            "environments": updated_registry}, title="Systems environment registry updated",
            summary=f"Updated check state for {env['environment_id']}.",
            event_id=str(registry_event["id"]) if registry_event else None,
            event_key=None if registry_event else "environment-registry")
        LOCAL_MIRROR.parent.mkdir(parents=True, exist_ok=True)
        LOCAL_MIRROR.write_text(json.dumps({"authority": "SUPABASE:nexus_events", "updated_at": _iso(),
                                            "event_id": registry_saved.get("id"), "environments": updated_registry}, indent=2) + "\n")
    completed_state_rows = [row for row in active if row.get("environment_id") in completed]
    closed_no_action = {"NOT_APPLICABLE", "NOT_DUE", "NOT_EXPOSED_BY_PROVIDER"}
    run["healthy_checks"] = sum(1 for row in completed_state_rows if row.get("current_state") == "PASS")
    run["abnormal_checks"] = sum(1 for row in completed_state_rows
        if row.get("current_state") in CHECK_STATES - {"PASS"} - closed_no_action)
    run["environments_checked"] = run["healthy_checks"]
    run["environments_skipped_with_valid_reason"] = sum(1 for row in completed_state_rows if row.get("current_state") in closed_no_action)
    run["environments_failed_with_continuation"] = run["abnormal_checks"]
    run["coverage_accounting"] = {"due": int(run.get("total_environments_due", 0)),
        "checked": run["environments_checked"],
        "failed_with_continuation": run["environments_failed_with_continuation"],
        "skipped_with_valid_reason": run["environments_skipped_with_valid_reason"]}
    run["coverage_pass"] = (run["coverage_accounting"]["checked"] +
        run["coverage_accounting"]["failed_with_continuation"] +
        run["coverage_accounting"]["skipped_with_valid_reason"] +
        int(run.get("environments_remaining", 0)) == run["coverage_accounting"]["due"])
    latest_run_event = _latest_event("systems_nightly_run")
    if latest_run_event:
        saved_run = _event("systems_nightly_run", {"run": run}, title="Systems nightly audit closed-state accounting",
            summary=f"Closed coverage: {run['environments_checked']} PASS, {run['environments_failed_with_continuation']} routed, {run['environments_skipped_with_valid_reason']} valid exclusions.",
            correlation_id=run_id, event_id=str(latest_run_event["id"]))
        pointer = ROOT / "data/runtime/systems_nightly_run_pointer.json"
        pointer.write_text(json.dumps({"event_id": saved_run["id"], "systems_run_id": run_id}) + "\n")
    # A wake that completed the final environment creates a concise morning report.
    report_created = False
    if run.get("status") == "COMPLETE_FOR_DATE":
        report = {"systems_run_id": run_id, "run_date": run["run_date"], "run_start": run["started_at"],
                  "run_end": run.get("completed_at"), "active_environments": len(active),
                  "environments_due": run["total_environments_due"], "environments_checked": run.get("environments_checked", 0),
                  "environments_skipped_with_valid_reason": run.get("environments_skipped_with_valid_reason", 0),
                  "environments_failed_with_continuation": run.get("environments_failed_with_continuation", 0),
                  "total_checks": run.get("deterministic_checks_total", deterministic), "healthy_checks": run["healthy_checks"],
                  "abnormal_checks": run["abnormal_checks"], "top_findings": run.get("top_findings", []),
                  "ray_decisions_required": 0}
        _event("systems_morning_report", report, title=f"Systems morning report {run['run_date']}",
               summary=f"{report['environments_checked']} due environments accounted for; {report['abnormal_checks']} abnormal.", correlation_id=run_id,
               event_key=f"report:{run_id}")
        report_created = True
    return {"status": run.get("status"), "systems_run_id": run_id, "scheduler": scheduler,
            "worker_id": worker_id, "registry_count": len(registry), "active_environments": len(active),
            "environments_due": run["total_environments_due"], "environments_checked_this_wake": healthy,
            "checks_executed": deterministic, "healthy_no_ai": healthy, "abnormal_checks": abnormal,
            "environments_skipped_with_valid_reason": skipped,
            "environments_failed_with_continuation": abnormal,
            "observations": observations, "checkpoint": run.get("last_checkpoint"),
            "next_environment": run.get("next_environment"), "next_check": run.get("current_check"),
            "coverage_pass": (run.get("environments_checked", 0) + run.get("environments_skipped_with_valid_reason", 0) +
                              run.get("environments_failed_with_continuation", 0) + run.get("environments_remaining", 0) ==
                              run.get("total_environments_due", 0)),
            "morning_report_created": report_created, "ai_analyses": 0,
            "systems_continued": True}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--scheduled-cycle", action="store_true")
    parser.add_argument("--scheduler", default="com.nexus.continuous-loop")
    parser.add_argument("--worker-id", default=f"systems-{os.getpid()}")
    args = parser.parse_args()
    if not args.scheduled_cycle:
        parser.error("--scheduled-cycle is required")
    lock_path = ROOT / "data/runtime/systems_workflow.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+") as lock_file:
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            result = {"status": "SYSTEMS_CHECK_ALREADY_RUNNING", "scheduler": args.scheduler,
                      "worker_id": args.worker_id, "next_action": "RESUME_AFTER_ACTIVE_CHECKPOINT"}
        else:
            result = run_systems_cycle(scheduler=args.scheduler, worker_id=args.worker_id)
    print(json.dumps(result, sort_keys=True, default=str))
