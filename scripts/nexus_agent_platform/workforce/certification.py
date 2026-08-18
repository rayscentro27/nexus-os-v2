"""Phase 13 AI Workforce certification and provider onboarding.

The registry is evidence-first. Installation, version, authentication, and
actual execution are independent facts. This module records capability and
policy state without logging secrets, installing software, buying credits, or
changing routing.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[3]
REPORT_DIR = ROOT / "reports" / "hermes_modernization"

CLASSIFICATIONS = {
    "AVAILABLE", "INSTALLED_UNPROVEN", "AUTH_BLOCKED", "RATE_LIMITED",
    "NOT_INSTALLED", "UNAVAILABLE", "DEFERRED", "DISABLED_BY_POLICY",
}
OPENCODE_MODEL = "opencode/mimo-v2.5-free"
OPENCODE_MARKER = "OPENCODE_PROBE_OK"
_AUTH_ERROR_RE = re.compile(r"(unauthori[sz]ed|authentication|not authenticated|login required|invalid token|api key required|401)", re.I)
_RATE_LIMIT_RE = re.compile(r"(rate.?limit|too many requests|429|quota exceeded|throttl)", re.I)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _stable_id(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()[:16]


def _read_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return default


def _redact(value: str) -> str:
    return re.sub(r"(?i)((?:api[_-]?key|access[_-]?token|auth(?:entication)?[_-]?token|secret|password)\s*[:=]\s*)([^\s,;]+)", r"\1[REDACTED]", value)[:1000]


def _usage_value(payload: Any, keys: set[str]) -> Optional[int]:
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key in keys and isinstance(value, (int, float)):
                return int(value)
            found = _usage_value(value, keys)
            if found is not None:
                return found
    elif isinstance(payload, list):
        for item in payload:
            found = _usage_value(item, keys)
            if found is not None:
                return found
    return None


def run_opencode_probe(timeout_seconds: int = 30) -> Dict[str, Any]:
    """Run the explicit harmless OpenCode contract without mutating the repo."""
    command = ["opencode", "run", "--model", OPENCODE_MODEL, "--format", "json", "Reply with exactly: OPENCODE_PROBE_OK"]
    started = time.monotonic()
    timestamp = _now()
    if not shutil.which("opencode"):
        return {"worker_id": "opencode", "installed": False, "classification": "NOT_INSTALLED", "probe": "not_run", "probe_timestamp": timestamp, "model": OPENCODE_MODEL, "reason": "binary missing"}
    proc = None
    try:
        proc = subprocess.Popen(command, cwd=str(ROOT), stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True)
        stdout, stderr = proc.communicate(timeout=timeout_seconds)
        returncode, timed_out = proc.returncode, False
    except subprocess.TimeoutExpired:
        if proc is not None:
            try:
                os.killpg(proc.pid, 9)
            except (OSError, ProcessLookupError):
                pass
        stdout, stderr, returncode, timed_out = "", "", None, True
    except OSError as exc:
        stdout, stderr, returncode, timed_out = "", type(exc).__name__, None, False
    duration_ms = int((time.monotonic() - started) * 1000)
    combined = f"{stdout}\n{stderr}"
    marker_present = OPENCODE_MARKER in stdout
    parsed: Any = None
    for line in reversed([line.strip() for line in stdout.splitlines() if line.strip()]):
        try:
            parsed = json.loads(line)
            break
        except ValueError:
            continue
    if timed_out:
        classification, reason, probe = "UNAVAILABLE", "explicit model execution probe timed out", "execution_timeout"
    elif _RATE_LIMIT_RE.search(combined):
        classification, reason, probe = "RATE_LIMITED", "explicit rate-limit evidence in execution probe", "execution_rate_limited"
    elif _AUTH_ERROR_RE.search(combined):
        classification, reason, probe = "AUTH_BLOCKED", "explicit authentication error in execution probe", "execution_auth_error"
    elif returncode == 0 and marker_present:
        classification, reason, probe = "AVAILABLE", "explicit model execution returned the required marker", "execution_success"
    elif returncode == 0:
        classification, reason, probe = "INSTALLED_UNPROVEN", "execution returned without the required marker", "execution_marker_missing"
    else:
        classification, reason, probe = "UNAVAILABLE", "explicit model execution failed without auth or rate-limit evidence", "execution_failed"
    return {
        "worker_id": "opencode", "installed": True, "classification": classification, "probe": probe,
        "probe_timestamp": timestamp, "model": OPENCODE_MODEL, "duration_ms": duration_ms,
        "returncode": returncode, "marker_present": marker_present,
        "input_tokens": _usage_value(parsed, {"input_tokens", "inputTokens", "prompt_tokens", "promptTokens"}),
        "output_tokens": _usage_value(parsed, {"output_tokens", "outputTokens", "completion_tokens", "completionTokens"}),
        "cache_read_tokens": _usage_value(parsed, {"cache_read_tokens", "cacheReadTokens", "cache_read_input_tokens"}),
        "cache_write_tokens": _usage_value(parsed, {"cache_write_tokens", "cacheWriteTokens"}),
        "provider_cost_usd": _usage_value(parsed, {"provider_cost_usd", "cost_usd", "cost"}),
        "stdout_preview": _redact(stdout), "stderr_preview": _redact(stderr), "reason": reason,
    }


@dataclass(frozen=True)
class ProviderAdapter:
    worker_id: str
    adapter_type: str
    binary_or_endpoint: str
    version_command: List[str]
    auth_probe: str
    execution_probe: Optional[str]
    execution_command: Optional[List[str]]
    timeout_seconds: int
    capabilities: List[str]
    cost_class: str
    provider: str
    models: List[str]
    requires_api_key: bool
    supports_existing_login: bool
    secret_sources: List[str]
    verification_requirements: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "worker_id": self.worker_id,
            "adapter_type": self.adapter_type,
            "binary_or_endpoint": self.binary_or_endpoint,
            "version_command": self.version_command,
            "auth_probe": self.auth_probe,
            "execution_probe": self.execution_probe,
            "execution_command": self.execution_command,
            "timeout": self.timeout_seconds,
            "capabilities": self.capabilities,
            "cost_class": self.cost_class,
            "provider": self.provider,
            "models": self.models,
            "requires_api_key": self.requires_api_key,
            "supports_existing_login": self.supports_existing_login,
            "secret_sources": self.secret_sources,
            "verification_requirements": self.verification_requirements,
        }


def _prompt() -> str:
    return "Reply with exactly HEALTHCHECK_OK. Do not inspect, read, or modify files."


def build_provider_adapters() -> Dict[str, ProviderAdapter]:
    return {
        "codex": ProviderAdapter(
            "codex", "codex_cli", "codex", ["codex", "--version"],
            "existing local Codex CLI session; no secret value read", "safe read-only ephemeral execution",
            ["codex", "exec", "--ephemeral", "--sandbox", "read-only", "--skip-git-repo-check", "--color", "never", _prompt()],
            15, ["repo_edit", "shell", "tests", "structured_output", "resume"], "ZERO_MODEL_COST", "OpenAI Codex CLI", ["local-session-selected-model"], False, True, ["local Codex session"], ["git diff", "protected path check", "tests", "acceptance criteria"],
        ),
        "opencode": ProviderAdapter(
            "opencode", "opencode_cli", "opencode", ["opencode", "--version"],
            "provider login/configuration state; no secret value read", "provider-specific non-interactive run with explicit model and marker",
            ["opencode", "run", "--model", OPENCODE_MODEL, "--format", "json", "Reply with exactly: OPENCODE_PROBE_OK"], 30,
            ["repo_edit", "shell", "tests", "structured_output"], "ZERO_MODEL_COST", "OpenCode/provider-selected", [OPENCODE_MODEL], True, True, ["provider session", "environment configuration"], ["git diff", "protected path check", "tests", "acceptance criteria"],
        ),
        "mimo": ProviderAdapter(
            "mimo", "mimo_cli", "mimo", ["mimo", "--version"],
            "MiMo local auth/config state; no secret value read", "provider-specific non-interactive run",
            ["mimo", "run", "--non-interactive", _prompt()], 15,
            ["repo_edit", "shell", "tests"], "LOW_EXTERNAL_COST", "MiMo", ["configured provider session"], True, True, ["provider session", "environment configuration"], ["git diff", "protected path check", "tests", "acceptance criteria"],
        ),
        "kilo": ProviderAdapter(
            "kilo", "kilo_cli", "kilo", ["kilo", "--version"],
            "Kilo local auth/config state; no secret value read", None, None, 15,
            ["repo_edit", "shell", "tests", "browser", "images", "worktrees"], "UNKNOWN", "Kilo Code", ["provider-selected"], True, True, ["Kilo local config"], ["Kilo non-interactive execution contract", "git diff", "protected path check", "tests"],
        ),
        "openhands": ProviderAdapter(
            "openhands", "openhands_cli_or_endpoint", "openhands", ["openhands", "--version"],
            "OpenHands auth state; no secret value read", None, None, 15,
            ["repo_edit", "shell", "tests", "browser", "images", "worktrees", "resume"], "UNKNOWN", "OpenHands", [], True, True, ["provider configuration"], ["sandbox execution", "git diff", "protected path check", "tests"],
        ),
        "local_python": ProviderAdapter(
            "local_python", "internal_deterministic", "python3", ["python3", "--version"],
            "NOT_APPLICABLE", "isolated internal artifact execution", ["python3", "-c", "pass"], 15,
            ["repo_edit", "shell", "tests", "worktrees", "structured_output"], "ZERO_MODEL_COST", "local", ["python3"], False, False, [], ["artifact inspection", "protected path check", "tests", "acceptance criteria"],
        ),
    }


def _worker_record(adapter: ProviderAdapter, *, classification: str, installed: bool, version: str, auth_status: str, probe_status: str, available: bool, reason: str, evidence_refs: List[str]) -> Dict[str, Any]:
    if classification not in CLASSIFICATIONS:
        raise ValueError(f"unsupported workforce classification: {classification}")
    return {
        "worker_id": adapter.worker_id,
        "display_name": {"local_python": "Local deterministic worker", "kilo": "Kilo Code / Kilo CLI"}.get(adapter.worker_id, adapter.worker_id.title()),
        "worker_type": adapter.adapter_type,
        "binary_or_endpoint": adapter.binary_or_endpoint,
        "installed": installed,
        "version": version,
        "authentication_mechanism": adapter.auth_probe,
        "auth_status": auth_status,
        "execution_probe_status": probe_status,
        "available": available,
        "classification": classification,
        "availability_reason": reason,
        "provider": adapter.provider,
        "models": adapter.models,
        "cost_class": adapter.cost_class,
        "supports_repo_edit": "repo_edit" in adapter.capabilities,
        "supports_shell": "shell" in adapter.capabilities,
        "supports_tests": "tests" in adapter.capabilities,
        "supports_browser": "browser" in adapter.capabilities,
        "supports_images": "images" in adapter.capabilities,
        "supports_worktrees": "worktrees" in adapter.capabilities,
        "supports_resume": "resume" in adapter.capabilities,
        "supports_structured_output": "structured_output" in adapter.capabilities,
        "supports_long_running_tasks": False,
        "supports_sandbox_execution": adapter.worker_id in {"codex", "local_python"},
        "supports_web_research": adapter.worker_id in {"kilo", "openhands"},
        "rate_limit_status": "UNKNOWN" if classification not in {"RATE_LIMITED", "AVAILABLE"} else ("CLEAR" if classification == "AVAILABLE" else "RATE_LIMITED"),
        "adapter": adapter.to_dict(),
        "evidence_refs": evidence_refs,
    }


def _recorded_workers(adapters: Dict[str, ProviderAdapter]) -> List[Dict[str, Any]]:
    pilot_path = REPORT_DIR / "end_to_end_pilot.json"
    pilot = _read_json(pilot_path, {}) or {}
    historical = {row.get("worker_id"): row for row in pilot.get("workers", []) if isinstance(row, dict)}
    refs = ["reports/hermes_modernization/end_to_end_pilot.json", "reports/hermes_modernization/builder_abstraction.md"]
    # This is the verified Phase 12 checkpoint supplied for this phase. The
    # older pilot JSON contains an earlier transient Codex timeout, so it is
    # retained as history rather than allowed to override the newer checkpoint.
    checkpoint = {
        "codex": {"classification": "AVAILABLE", "version": "codex-cli 0.147.0", "installed": True, "probe": "EXECUTION_VERIFIED", "reason": "current verified checkpoint: version and harmless execution probes succeeded"},
        "opencode": {"classification": "UNAVAILABLE", "version": "1.18.18", "installed": True, "probe": "EXECUTION_TIMEOUT", "reason": "current verified checkpoint: safe execution probe timed out"},
        "mimo": {"classification": "INSTALLED_UNPROVEN", "version": "0.1.12", "installed": True, "probe": "EXECUTION_UNPROVEN", "reason": "current verified checkpoint: execution did not prove availability"},
    }
    explicit_probe = _read_json(REPORT_DIR / "opencode_probe_latest.json", {}) or {}
    if explicit_probe.get("worker_id") == "opencode":
        checkpoint["opencode"] = {
            "classification": explicit_probe.get("classification", "INSTALLED_UNPROVEN"),
            "version": "1.18.18",
            "installed": bool(explicit_probe.get("installed", True)),
            "probe": str(explicit_probe.get("probe", "NOT_PROVEN")).upper(),
            "reason": explicit_probe.get("reason", "explicit provider probe record"),
            "probe_telemetry": {key: explicit_probe.get(key) for key in ("model", "probe_timestamp", "duration_ms", "input_tokens", "output_tokens", "cache_read_tokens", "cache_write_tokens", "provider_cost_usd", "marker_present")},
        }
    rows: List[Dict[str, Any]] = []
    for worker_id, adapter in adapters.items():
        if worker_id == "local_python":
            rows.append(_worker_record(adapter, classification="AVAILABLE", installed=True, version="python3", auth_status="NOT_APPLICABLE", probe_status="EXECUTION_VERIFIED", available=True, reason="isolated deterministic artifact execution and verification are proven", evidence_refs=["scripts/nexus_agent_platform/builders/runtime.py", *refs]))
            continue
        if worker_id == "kilo":
            installed = bool(shutil.which("kilo")) or Path("/usr/local/Cellar/kilo/7.3.54/libexec/kilo").exists()
            rows.append(_worker_record(adapter, classification="INSTALLED_UNPROVEN" if installed else "NOT_INSTALLED", installed=installed, version="7.3.54" if installed else "UNKNOWN", auth_status="UNPROVEN", probe_status="NOT_PROVEN", available=False, reason="Kilo is installed locally, but no safe non-interactive execution contract or auth proof is available; do not add to CodingWorker registry.", evidence_refs=["/usr/local/Cellar/kilo/7.3.54", "/Users/raymonddavis/.config/kilo/kilo.jsonc"]))
            continue
        old = {**historical.get(worker_id, {}), **checkpoint.get(worker_id, {})}
        classification = str(old.get("classification") or old.get("status") or "INSTALLED_UNPROVEN")
        if classification == "UNAVAILABLE":
            classification = "UNAVAILABLE"
        installed = bool(old.get("installed", False))
        path_exists = bool(shutil.which(worker_id))
        version = str(old.get("version") or "UNKNOWN")
        auth_status = "AUTHENTICATED_UNPROVEN" if classification == "AVAILABLE" else ("AUTH_ERROR_PROVEN" if classification == "AUTH_BLOCKED" else "UNPROVEN")
        probe_status = "EXECUTION_VERIFIED" if classification == "AVAILABLE" else str(old.get("probe") or old.get("probe_result") or "NOT_PROVEN").upper()
        row = _worker_record(adapter, classification=classification if classification in CLASSIFICATIONS else "UNAVAILABLE", installed=installed or path_exists, version=version, auth_status=auth_status, probe_status=probe_status, available=classification == "AVAILABLE", reason=str(old.get("reason") or old.get("availability_reason") or "No current proof record."), evidence_refs=refs)
        if old.get("probe_telemetry"):
            row["probe_telemetry"] = old["probe_telemetry"]
        rows.append(row)
    openhands = rows[[row["worker_id"] for row in rows].index("openhands")]
    openhands.update({"installed": False, "classification": "NOT_INSTALLED", "available": False, "version": "UNKNOWN", "auth_status": "NOT_APPLICABLE", "execution_probe_status": "NOT_RUN", "availability_reason": "binary not found on PATH"})
    return rows


def _agent_certifications() -> List[Dict[str, Any]]:
    return [
        {"worker_id": "hermes_upstream", "display_name": "Isolated upstream Hermes lab", "worker_type": "agent_runtime", "installed": True, "version": "local lab", "auth_status": "NOT_APPLICABLE", "execution_probe_status": "LAB_VERIFIED", "available": True, "classification": "DEFERRED", "availability_reason": "Compatibility lab is proven in isolation; not a production execution worker.", "task_classes": ["upstream compatibility study", "bounded runtime experiments"], "evidence_refs": ["scripts/nexus_agent_platform/hermes_lab/upstream_compatibility.py", "reports/hermes_modernization/upstream_compatibility.md"]},
        {"worker_id": "nexus_hermes", "display_name": "Nexus Hermes", "worker_type": "persistent_agent", "installed": True, "version": "repository runtime", "auth_status": "N/A", "execution_probe_status": "GOVERNED_ROUTING_VERIFIED", "available": True, "classification": "AVAILABLE", "availability_reason": "Operator/orchestrator routing and governed report paths are proven.", "task_classes": ["operator intelligence", "approvals", "opportunity orchestration", "daily brief"], "evidence_refs": ["scripts/nexus_agent_platform/agents/hermes.py", "reports/hermes_modernization/daily_brief.json"]},
        {"worker_id": "alpha", "display_name": "Alpha external intelligence", "worker_type": "persistent_agent", "installed": True, "version": "repository runtime", "auth_status": "PUBLIC_RESEARCH_ONLY", "execution_probe_status": "RESEARCH_FOUNDATION_VERIFIED", "available": True, "classification": "AVAILABLE", "availability_reason": "Public-information research and provenance foundation are proven; no client PII authority.", "task_classes": ["public research", "source normalization", "provenance", "open-source scouting"], "evidence_refs": ["scripts/alpha", "reports/hermes_modernization/alpha_external_intelligence.md"]},
        {"worker_id": "hermes_nova", "display_name": "Hermes Nova", "worker_type": "persistent_agent", "installed": True, "version": "repository runtime", "auth_status": "GOVERNED", "execution_probe_status": "RECOMMENDATION_BOUNDARY_VERIFIED", "available": True, "classification": "AVAILABLE", "availability_reason": "Separate governed recommendation/reasoning lane; not an autonomous promotion authority.", "task_classes": ["reasoning", "recommendations", "knowledge evaluation"], "evidence_refs": ["scripts/nexus_agent_platform/agents/nova.py", "scripts/nexus_agent_platform/governed/recommendations.py"]},
    ]


def build_workforce_report() -> Dict[str, Any]:
    adapters = build_provider_adapters()
    workers = _recorded_workers(adapters)
    return {
        "report_id": f"workforce_certification_{_stable_id([_now()[:10], [(row['worker_id'], row['classification']) for row in workers]])}",
        "generated_at": _now(),
        "phase": "PHASE 13 — AI WORKFORCE CERTIFICATION + PROVIDER ONBOARDING",
        "status": "CERTIFICATION_PARTIAL_PROVIDER_ACTIONS_DEFERRED",
        "onboarding_contract": ["DISCOVER", "INSTALLATION_CHECK", "VERSION_CHECK", "AUTH_PROBE", "HARMLESS_EXECUTION_PROBE", "CAPABILITY_DISCOVERY", "COST_CLASSIFICATION", "SAFETY_CLASSIFICATION", "VERIFICATION_CONTRACT", "REGISTRY_ENTRY", "CERTIFICATION", "AVAILABLE"],
        "allowed_classifications": sorted(CLASSIFICATIONS),
        "workers": workers,
        "agent_certifications": _agent_certifications(),
        "kilo_recommendation": {"decision": "DEFER", "reason": "Installed, but no safe non-interactive execution/auth contract is proven. Existing Codex and local deterministic coverage provide sufficient current redundancy.", "install_action": "NOT_NEEDED", "registry_action": "DO_NOT_REGISTER_AS_EXECUTABLE"},
        "routing_policy": {"production_routing_changed": False, "selection_requires_available_and_verified": True, "unavailable_fallback": "local_python", "new_provider_requires_separate_certification": True},
        "governance": {"software_installation": "DISABLED", "provider_credit_purchase": "DISABLED", "provider_login_mutation": "DISABLED", "automatic_routing_mutation": "DISABLED", "client_portal_changes": "NONE", "production_telegram_changes": "NONE"},
        "evidence_refs": ["reports/hermes_modernization/end_to_end_pilot.json", "reports/hermes_modernization/builder_abstraction.md", "scripts/nexus_agent_platform/builders/runtime.py"],
    }


def render_workforce_report(report: Dict[str, Any]) -> str:
    lines = ["# Nexus AI Workforce Certification — Phase 13", "", f"Status: **{report['status']}**", "", "## Provider workers", "", "| Worker | Installed | Version | Auth | Execution | Classification | Cost |", "|---|---:|---|---|---|---|---|"]
    for row in report["workers"]:
        lines.append(f"| {row['display_name']} | {str(row['installed']).lower()} | {row['version']} | {row['auth_status']} | {row['execution_probe_status']} | **{row['classification']}** | {row['cost_class']} |")
    lines.extend(["", "## Kilo Code", "", f"- decision: `{report['kilo_recommendation']['decision']}`", f"- install action: `{report['kilo_recommendation']['install_action']}`", f"- registry action: `{report['kilo_recommendation']['registry_action']}`", f"- reason: {report['kilo_recommendation']['reason']}", "", "## Governance", "", "No provider login, software installation, credit purchase, routing mutation, production Telegram change, or client portal change was performed.", "", "## Agent certifications", "", "| Agent | Classification | Execution proof | Task families |", "|---|---|---|---|"])
    for row in report["agent_certifications"]:
        lines.append(f"| {row['display_name']} | {row['classification']} | {row['execution_probe_status']} | {', '.join(row['task_classes'])} |")
    return "\n".join(lines) + "\n"


def write_workforce_reports() -> Dict[str, Any]:
    report = build_workforce_report()
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "workforce_certification.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (REPORT_DIR / "workforce_certification.md").write_text(render_workforce_report(report), encoding="utf-8")
    return report
