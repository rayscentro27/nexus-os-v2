"""Bounded Nova-facing Systems operator tools for the existing Nexus MCP."""
from __future__ import annotations

import json
import os
import re
import sqlite3
import subprocess
import sys
from pathlib import Path
from typing import Any, Literal

from .auth import authorize_action, authorize_read


READ_TOOLS = {
    "systems_status", "systems_job_status", "systems_job_result",
    "systems_upgrade_review", "systems_cleanup_scan",
    "systems_credential_status", "systems_kaggle_status",
    "systems_ai_usage_summary",
}
ACTION_CLASSES = {
    "UPGRADE_REVIEW", "UPGRADE", "INSTALL_TECHNOLOGY", "CLEANUP",
    "CREDENTIAL_ROTATION", "KAGGLE_JOB", "REPAIR", "VALIDATION", "MAINTENANCE",
    "TECHNOLOGY_HANDOFF",
}
FINAL_STATES = {"COMPLETED", "COMPLETED_WITH_LIMITATIONS", "FAILED", "FAILED_RECOVERABLE", "ROLLED_BACK"}
JOB_ID_RE = re.compile(r"^sysjob_[a-f0-9]{24}$")
MAX_REPORT_BYTES = 256_000


def _repo_root() -> Path:
    root = Path(os.environ.get("NEXUS_REPO_ROOT", "")).expanduser().resolve()
    if not root.is_dir() or not (root / "docs/systems/NEXUS_LIVING_MANIFEST.v1.json").is_file():
        raise RuntimeError("SYSTEMS_REPO_ROOT_UNAVAILABLE")
    return root


def _manifest() -> dict[str, Any]:
    return json.loads((_repo_root() / "docs/systems/NEXUS_LIVING_MANIFEST.v1.json").read_text())


def _safe(value: Any, *, include_internal_ids: bool = False) -> Any:
    """Apply the shared Systems output redactor when available."""
    root = _repo_root()
    sys.path.insert(0, str(root / "scripts/systems"))
    try:
        from secret_guard import redact_text
        safe_value = json.loads(redact_text(json.dumps(value, ensure_ascii=False, default=str)))
        if include_internal_ids:
            return safe_value
        return _strip_internal_ids(safe_value)
    except (ImportError, ValueError, TypeError):
        return {"status": "REDACTION_UNAVAILABLE"}


def _strip_internal_ids(value: Any) -> Any:
    internal_ref = re.compile(r"\b(?:sysjob_[a-f0-9]{24}|job_[A-Za-z0-9_-]{8,}|(?:sys)?rcpt_[A-Za-z0-9_-]+|queue_[A-Za-z0-9_-]+|sysapproval_[a-f0-9]{48})\b")
    hidden = {"systems_job_id", "job_id", "request_id", "receipt", "receipt_id", "claim_id", "worker_id", "database_id", "approval_reference"}
    if isinstance(value, dict):
        return {key: _strip_internal_ids(item) for key, item in value.items() if key.casefold() not in hidden}
    if isinstance(value, list):
        return [_strip_internal_ids(item) for item in value]
    if isinstance(value, str):
        return internal_ref.sub("[internal reference]", value)
    return value


def _latest_nova_job_id(objective: str = "") -> str | None:
    """Resolve a Nova-submitted job internally for ID-free status/result polling."""
    rows = [row for row in _work_rows()
            if row["order"].get("requested_by") == "NOVA_VIA_NEXUS_MCP"
            and (not objective.strip() or objective.strip().casefold() in str(row["order"].get("objective", "")).casefold())]
    return str(rows[-1]["id"]) if rows else None


def _managed_module():
    root = _repo_root()
    sys.path.insert(0, str(root / "scripts/systems"))
    import managed_work
    return managed_work


def _existing_s1_typed_request(operation: str, **arguments: Any) -> dict[str, Any]:
    from .systems_bridge import request
    return request(operation, **arguments)


def _run_json(path: str, *, timeout: int = 35, args: tuple[str, ...] = ()) -> dict[str, Any]:
    script = _repo_root() / path
    result = subprocess.run([sys.executable, str(script), *args], capture_output=True, text=True,
                            timeout=timeout, check=False, cwd=str(_repo_root()))
    output = result.stdout[-MAX_REPORT_BYTES:]
    try:
        payload = json.loads(output)
    except (json.JSONDecodeError, TypeError):
        return {"status": "UNAVAILABLE", "error": "SYSTEMS_PROBE_OUTPUT_INVALID"}
    payload["process_exit_code"] = result.returncode
    return payload


def _work_db() -> Path:
    return Path.home() / ".nexus/state/systems/systems.sqlite3"


def _work_rows() -> list[dict[str, Any]]:
    path = _work_db()
    if not path.is_file():
        return []
    with sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=3) as con:
        rows = con.execute("SELECT request_id,receipt_type,payload FROM receipts WHERE receipt_type LIKE 'SYSTEMS_MANAGED_JOB%' ORDER BY created_at,rowid").fetchall()
    grouped: dict[str, list[dict[str, Any]]] = {}
    for job_id, kind, raw in rows:
        try:
            record = {"kind": kind, **json.loads(raw)}
        except (TypeError, json.JSONDecodeError):
            continue
        grouped.setdefault(str(job_id), []).append(record)
    return [{"id": job_id, "order": records[0], "latest": records[-1]}
            for job_id, records in grouped.items() if records]


def _public_state(value: str) -> str:
    return {
        "READY_FOR_AGENT": "READY", "EXECUTING": "RUNNING", "VALIDATING": "RUNNING",
        "WAITING_APPROVAL": "WAITING_EXTERNAL_BOUNDARY", "TARGET_UNRESOLVED": "FAILED_RECOVERABLE",
        "INTENT_REJECTED": "FAILED_RECOVERABLE", "FAILED": "FAILED_RECOVERABLE",
    }.get(value, value if value in FINAL_STATES else "READY")


def resolve_action_target(manifest: dict[str, Any], action: str, component: str) -> dict[str, Any] | None:
    """Return only the preconfigured component/path scope for one action."""
    if action not in ACTION_CLASSES:
        return None
    config = manifest.get("systems_managed_work", {}).get("action_targets", {}).get(action)
    if not isinstance(config, dict) or config.get("component") != component:
        return None
    files = config.get("requested_files")
    return config if isinstance(files, list) and files else None


def _job_summary(row: dict[str, Any], include_internal_id: bool = False) -> dict[str, Any]:
    order, latest = row["order"], row["latest"]
    state = latest.get("status", order.get("status", "UNKNOWN"))
    result = latest.get("result") or order.get("result") or {}
    summary = {
        "state": _public_state(str(state)), "objective": order.get("objective"),
        "component": order.get("component"), "current_stage": latest.get("stage") or latest.get("kind"),
        "worker": order.get("execution_agent"), "started_at": latest.get("started_at"),
        "completed_at": latest.get("completed_at"),
        "approval_state": order.get("approval_requirement"),
        "validation_state": (latest.get("post_change_drift") or {}).get("post_change_drift_check") or
                            (result.get("validation_pass") if isinstance(result, dict) else None),
        "remaining_issue": (result.get("remaining_issue") or result.get("resolution_error")) if isinstance(result, dict) else None,
    }
    if include_internal_id:
        summary["systems_job_id"] = row["id"]
    return summary


def register_systems_operator_tools(mcp: Any) -> None:
    @mcp.tool(name="systems_status", description="Read the current Systems health, managed-work counts, upgrade/cleanup/credential/Kaggle readiness, Research authoritative-state health, and Living Manifest validation. Read only; no internal identifiers or secrets.")
    def systems_status() -> dict[str, Any]:
        authorize_read("systems_status")
        manifest = _manifest()
        jobs = _work_rows()
        report = _run_json("scripts/systems/workflow_integrity.py")
        validation = _run_json("scripts/systems/phase1_runtime.py", args=("--validate-only",))
        counts: dict[str, int] = {}
        for row in jobs:
            state = _public_state(str(row["latest"].get("status", row["order"].get("status", "UNKNOWN"))))
            counts[state] = counts.get(state, 0) + 1
        checks = report.get("checks", {})
        return _safe({
            "status": "DEGRADED" if report.get("status") != "HEALTHY" or validation.get("validation") != "PASS" else "HEALTHY",
            "workflow_integrity": {"status": report.get("status"), "check_count": report.get("check_count"),
                                   "pass_count": report.get("pass_count"), "checks": checks},
            "managed_jobs": {"active_count": sum(v for k, v in counts.items() if k in {"RUNNING", "WAITING_EXTERNAL_BOUNDARY"}),
                             "pending_count": counts.get("READY", 0), "states": counts},
            "upgrade_projects": [p.get("component") for p in manifest.get("upgrade_manager", {}).get("registry", [])],
            "cleanup": manifest.get("environment_cleanup_project", {}),
            "credential_rotation": {k: manifest.get("credential_rotation_project", {}).get(k)
                                     for k in ("status", "credential_reference_count", "rotation_ready_count", "rotation_not_ready_count")},
            "kaggle": {"status": manifest.get("kaggle_capability", {}).get("status"), "platform_certified": False},
            "research_authority": manifest.get("change_target_registry", {}).get("components", {}).get("research", {}),
            "living_manifest": {"validation": validation.get("validation", "UNKNOWN"),
                                "errors": validation.get("validation_errors", [])},
        })

    @mcp.tool(name="systems_ai_usage_summary", description=(
        "Read-only AI-usage accounting from the governed AI usage ledger: who used AI, which provider/model, token "
        "counts where known, failed/fallback/retry counts, current provider health and quota/alert state, and the "
        "Codex capacity-reserve state. Answers 'how much AI are we using', 'who is using the most', 'is Codex healthy', "
        "'did Research hit provider failures today', 'how many Nova conversations used fallback'. No secrets, no spend."))
    def systems_ai_usage_summary(window: Literal["today", "last_7_days", "all"] = "today") -> dict[str, Any]:
        authorize_read("systems_ai_usage_summary")
        root = _repo_root()
        sys.path.insert(0, str(root / "scripts"))
        try:
            from nexus_agent_platform.runtime import ai_usage_ledger as led
        except ImportError:
            return {"status": "AI_USAGE_LEDGER_UNAVAILABLE"}
        return _safe(led.usage_summary(window))

    @mcp.tool(name="systems_job_create", description="Create one bounded Systems work order. Actions and target files come only from Living Manifest action-target configuration; Systems runs the target resolver and rejects unresolved/out-of-scope targets. Systems continues deterministic validation through its maintenance tick. Never repeat internal job or receipt identifiers to Ray; use systems_job_status or systems_job_result without an ID to read the latest Nova-submitted job.")
    def systems_job_create(objective: str, component: str, requested_action: Literal[
        "UPGRADE_REVIEW", "UPGRADE", "INSTALL_TECHNOLOGY", "CLEANUP",
        "CREDENTIAL_ROTATION", "KAGGLE_JOB", "REPAIR", "VALIDATION", "MAINTENANCE",
        "TECHNOLOGY_HANDOFF"],
        environment: str = "", preferred_execution_worker: Literal["NONE", "SYSTEMS_LOCAL", "CODEX", "OPENCODE"] = "NONE",
        approval_reference: str = "") -> dict[str, Any]:
        authorize_action("systems_job_create")
        if not objective.strip() or len(objective) > 2000:
            return {"status": "REJECTED", "reason": "OBJECTIVE_INVALID"}
        manifest = _manifest()
        config = resolve_action_target(manifest, requested_action, component)
        if not config:
            return {"status": "TARGET_UNRESOLVED", "reason": "ACTION_COMPONENT_NOT_CONFIGURED", "job_created": False}
        files = config.get("requested_files")
        if not isinstance(files, list) or not files:
            return {"status": "TARGET_UNRESOLVED", "reason": "ACTION_TARGETS_NOT_CONFIGURED", "job_created": False}
        worker = preferred_execution_worker if preferred_execution_worker != "NONE" else config.get("execution_agent", "NONE")
        if worker not in {"NONE", "SYSTEMS_LOCAL", "CODEX", "OPENCODE"}:
            return {"status": "REJECTED", "reason": "WORKER_NOT_ALLOWLISTED"}
        authority = manifest.get("change_target_registry", {}).get("components", {}).get(component, {})
        resolved_environment = environment or config.get("target_environment") or authority.get("environment", "")
        safe_handoff = requested_action == "TECHNOLOGY_HANDOFF"
        safe_install = requested_action == "INSTALL_TECHNOLOGY"
        mutative = requested_action not in {"UPGRADE_REVIEW", "VALIDATION", "MAINTENANCE", "TECHNOLOGY_HANDOFF"}
        approval = ("NONE_TYPED_HANDOFF" if safe_handoff else
                    "POLICY_CLASSIFIED" if safe_install else
                    "RAY_APPROVAL_REQUIRED_BEFORE_MUTATION" if mutative else "NONE_READ_ONLY")
        typed_config = config.get("typed_action", {}) if (safe_handoff or safe_install) else {}
        if safe_install:
            config_path = str(Path.home() / ".config/opencode/opencode.jsonc")
            node_root = str(Path.home() / ".nvm/versions/node/v24.22.1")
            typed_config = {"operation": "systems.install_technology", "payload": {
                "technology_name": config["technology_name"], "technology_source": config["technology_source"],
                "target_environment": "MAC_MINI", "target_component": "OpenCode / REA integration",
                "target_scope": config_path, "native_install_method": "NVM_PINNED_NODE_24_22_1_NPM_GLOBAL_REA_6_8_0_OPENCODE_SETUP",
                "configuration_targets": [config_path], "allowed_paths": [config_path, node_root],
                "prohibited_paths": ["~/.config/opencode/auth.json", "data/runtime/research_work_queue.json",
                                     "Research runtime paths", "historical releases"],
                "health_check": config["health_check"],
                "rollback_or_uninstall_method": "Restore exact OpenCode config backup; npm uninstall REA; nvm uninstall 24.22.1",
                "node_version": "24.22.1", "node_install_path": node_root,
                "package_name": "rea-agents", "package_version": "6.8.0"}}
        work = _managed_module().create_work_order(
            component=component, objective=objective, requested_files=files,
            requested_by="NOVA_VIA_NEXUS_MCP", environment=resolved_environment,
            change_class=config.get("change_class", "READ_ONLY_REVIEW" if not mutative else "CLASS_1_SMALL_PATCH"),
            execution_agent=worker, approval_requirement=approval,
            validation={"required": ["target_resolution", "focused_validation", "post_change_drift_check"]},
            rollback=config.get("rollback", "Restore the recorded scoped backup; verify health before closing."),
            manifest=manifest, requested_action=requested_action,
            typed_action_config=typed_config,
            typed_executor=_existing_s1_typed_request if (safe_handoff or safe_install) else None,
            approval_reference=approval_reference or None,
        )
        safe = {"status": _public_state(work["status"]), "objective": objective,
                "component": component, "requested_action": requested_action,
                "target_resolution": work["authoritative_target"].get("authority_check"),
                "approval_requirement": work.get("approval_requirement", approval),
                "maintenance_classification": work.get("maintenance_classification"),
                "job_created": work["status"] != "TARGET_UNRESOLVED",
                "next_step": ("The existing S1 technology handoff was recorded; no software was installed."
                              if work.get("status") in {"COMPLETED", "COMPLETED_WITH_LIMITATIONS"} and safe_handoff
                              else "Systems completed the bounded installation and validation."
                              if work.get("status") in {"COMPLETED", "COMPLETED_WITH_LIMITATIONS"} and safe_install
                              else "The existing Systems maintenance tick will claim eligible deterministic validation work.")}
        return _safe(safe)

    @mcp.tool(name="systems_job_status", description="Read a Systems work state. Omit the ID to read the latest Nova-submitted job, or supply an objective substring to select one. Do not repeat internal IDs to Ray unless diagnostics are requested.")
    def systems_job_status(systems_job_id: str = "", objective: str = "", include_internal_id: bool = False) -> dict[str, Any]:
        authorize_read("systems_job_status")
        systems_job_id = systems_job_id.strip() or _latest_nova_job_id(objective) or ""
        if not JOB_ID_RE.fullmatch(systems_job_id):
            return {"status": "NOT_FOUND"}
        try:
            data = _managed_module().get_work(systems_job_id)
        except KeyError:
            return {"status": "NOT_FOUND"}
        row = {"id": systems_job_id, "order": data["work_order"], "latest": data["events"][-1] if data["events"] else data["work_order"]}
        return _safe(_job_summary(row, include_internal_id), include_internal_ids=include_internal_id)

    @mcp.tool(name="systems_job_result", description="Read one Systems result. Omit the ID to retrieve the latest Nova-submitted job, or supply an objective substring to select one. No secret values or internal identifiers are returned unless diagnostics are explicitly requested.")
    def systems_job_result(systems_job_id: str = "", objective: str = "", include_internal_id: bool = False) -> dict[str, Any]:
        authorize_read("systems_job_result")
        systems_job_id = systems_job_id.strip() or _latest_nova_job_id(objective) or ""
        if not JOB_ID_RE.fullmatch(systems_job_id):
            return {"status": "NOT_FOUND"}
        try:
            data = _managed_module().get_work(systems_job_id)
        except KeyError:
            return {"status": "NOT_FOUND"}
        order = data["work_order"]
        latest = data["events"][-1] if data["events"] else order
        result = latest.get("result") or order.get("result") or {}
        response = {"status": _public_state(str(latest.get("status", order.get("status", "UNKNOWN")))),
                    "summary": result.get("summary") or order.get("objective"),
                    "changes_made": result.get("changes_made", []),
                    "files_or_components_affected": result.get("files_or_components_affected", order.get("allowed_paths", [])),
                    "validation": result.get("validation", latest.get("post_change_drift")),
                    "health_result": result.get("health_result"),
                    "rollback_available": bool(order.get("rollback")),
                    "living_manifest_updated": bool(result.get("manifest_updated", False)),
                    "remaining_issues": result.get("remaining_issues", []),
                    "recommendation": result.get("recommendation"),
                    "approval_requirement": order.get("approval_requirement"),
                    "checked_at": result.get("checked_at"),
                    "systems_s1_health": result.get("systems_s1_health"),
                    "research_r10_health": result.get("research_r10_health"),
                    "stored_vs_direct_health_reconciliation": result.get("stored_vs_direct_health_reconciliation"),
                    "findings": result.get("findings", []),
                    "next_action": result.get("next_action") or result.get("recommendation")}
        workflow_report = result.get("workflow_report")
        if isinstance(workflow_report, dict):
            response["workflow_integrity"] = {
                "checked_at": workflow_report.get("checked_at"),
                "status": workflow_report.get("status", "UNKNOWN"),
                "pass_count": workflow_report.get("pass_count"),
                "check_count": workflow_report.get("check_count"),
                "checks": workflow_report.get("checks", {}),
                "next_action": result.get("recommendation", "REVIEW")}
            if not isinstance(result.get("systems_s1_health"), dict):
                current = _managed_module()._read_only_health_evidence(workflow_report, _work_db())
                response.update({
                    "checked_at": current.get("checked_at"),
                    "systems_s1_health": current.get("systems_s1_health", {"status": "UNKNOWN"}),
                    "research_r10_health": current.get("research_r10_health", {"status": "UNKNOWN"}),
                    "stored_vs_direct_health_reconciliation": current.get("stored_vs_direct_health_reconciliation", {"status": "UNKNOWN"}),
                    "findings": current.get("findings", []),
                    "next_action": result.get("recommendation", "REVIEW"),
                })
        if include_internal_id:
            response["systems_job_id"] = systems_job_id
        return _safe(response, include_internal_ids=include_internal_id)

    @mcp.tool(name="systems_upgrade_review", description="Read the recorded current/reviewed component versions and upgrade recommendation from the Living Manifest. Does not install or upgrade anything.")
    def systems_upgrade_review(component: str = "OpenCode") -> dict[str, Any]:
        authorize_read("systems_upgrade_review")
        manifest = _manifest()
        rows = manifest.get("upgrade_manager", {}).get("registry", [])
        row = next((x for x in rows if str(x.get("component", "")).casefold() == component.casefold()), None)
        if not row:
            return {"status": "NOT_FOUND", "component": component}
        if component.casefold() == "opencode":
            try:
                current = subprocess.run(["opencode", "--version"], capture_output=True, text=True,
                                         timeout=10, check=True).stdout.strip()[:80]
                if current:
                    row = {**row, "current_version": current}
            except (OSError, subprocess.SubprocessError):
                row = {**row, "current_version": "UNVERIFIED"}
        recommendation_text = str(row.get("upgrade_recommendation", ""))
        recommendation = "NO_ACTION" if "none" in recommendation_text.lower() or "1.19.5" in recommendation_text else "TEST_FIRST"
        return _safe({k: row.get(k) for k in ("component", "current_version", "latest_reviewed_version", "upgrade_type", "upgrade_risk", "upgrade_recommendation", "compatibility_concern")}
                     | {"recommendation": recommendation, "review_is_read_only": True})

    @mcp.tool(name="systems_cleanup_scan", description="Return the recorded cleanup classifications. Read only; does not delete or archive anything.")
    def systems_cleanup_scan() -> dict[str, Any]:
        authorize_read("systems_cleanup_scan")
        cleanup = _manifest().get("environment_cleanup_project", {})
        return _safe({"status": cleanup.get("status", "NOT_RECORDED"),
                      "classifications": {"SAFE_DELETE": cleanup.get("safe_delete", 0),
                                          "SAFE_ARCHIVE": cleanup.get("safe_archive", 0),
                                          "KEEP_ACTIVE": cleanup.get("keep_active", 0),
                                          "KEEP_RECOVERY": cleanup.get("keep_recovery", 0),
                                          "DEPENDENCY_CHECK_REQUIRED": cleanup.get("unknown_cleanup", 0),
                                          "UNKNOWN": cleanup.get("unknown_cleanup", 0)},
                      "deletion_performed": False, "note": cleanup.get("classification")})

    @mcp.tool(name="systems_credential_status", description="Read credential reference metadata only. Secret/token values are never loaded or returned.")
    def systems_credential_status() -> dict[str, Any]:
        authorize_read("systems_credential_status")
        manifest = _manifest()
        registry_path = _repo_root() / str(manifest.get("credential_registry", {}).get("source", "configs/nexus_credential_registry.json"))
        registry = json.loads(registry_path.read_text()) if registry_path.is_file() else {"credentials": []}
        managed_records = {str(x.get("credential_reference")): x for x in
                           manifest.get("credential_registry", {}).get("records", [])}
        rows = []
        for item in registry.get("credentials", []):
            ref = str(item.get("credential_id") or "")
            recorded = managed_records.get(ref, {})
            rows.append({"credential_reference": item.get("credential_id"), "provider": item.get("provider"),
                         "consumer_count": len(recorded.get("consumer_components", item.get("required_components", []))),
                         "rotation_classification": recorded.get("rotation_class", "UNKNOWN"),
                         "rotation_readiness": "NOT_READY",
                         "last_rotation": recorded.get("last_rotation", "UNKNOWN"),
                         "exposure_status": recorded.get("exposure_status", "NOT_ASSESSED")})
        debt = manifest.get("credential_rotation_project", {})
        return _safe({"reference_count": len(rows), "rotation_ready_count": debt.get("rotation_ready_count", 0),
                      "rotation_not_ready_count": debt.get("rotation_not_ready_count", len(rows)),
                      "records": rows})

    @mcp.tool(name="systems_kaggle_status", description="Read local Kaggle tooling readiness, platform certification, workload contract and limits. Does not upload data, use credentials, or launch a workload.")
    def systems_kaggle_status() -> dict[str, Any]:
        authorize_read("systems_kaggle_status")
        manifest = _manifest()
        health = _run_json("scripts/systems/kaggle_healthcheck.py", timeout=20)
        capability = manifest.get("kaggle_capability", {})
        return _safe({"local_tooling_ready": health.get("status"), "platform_certified": False,
                      "job_contract": capability.get("contract"), "recent_workload_state": "NONE_RECORDED",
                      "known_limitations": ["No Kaggle runtime/account connection verified.",
                                            "Kaggle is ephemeral and must not hold Nexus durable state or secrets."],
                      "health": health})

