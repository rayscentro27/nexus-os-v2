#!/usr/bin/env python3
"""Create and verify bounded Systems work orders in the existing Systems store."""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import subprocess
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.request import urlopen

from change_target_resolver import MANIFEST, post_change_check, resolve_target

DB = Path.home() / ".nexus/state/systems/systems.sqlite3"
ROOT = Path(__file__).resolve().parents[2]
_READONLY_SYSTEMS_VALIDATION = ("systems", str((ROOT / "scripts/systems/workflow_integrity.py").resolve()))
_READONLY_OPENCODE_REVIEW = ("opencode", str((Path.home() / ".config/opencode/opencode.jsonc").resolve()))

# One managed-work route to the already-running typed S1 endpoint.  There is no
# second dispatcher or generic command runner here.
MANAGED_ACTION_OPERATIONS = {
    "BOUNDED_UPGRADE": "systems.upgrade_component",
    "SAFE_CLEANUP": "systems.safe_cleanup",
    "CREDENTIAL_ROTATION": "systems.rotate_credential",
    "KAGGLE_PREP": "systems.prepare_kaggle_job",
    "SAFE_RESTART": "systems.restart_safe",
    "ROLLBACK": "systems.rollback",
    "UPGRADE": "systems.upgrade_component",
    "CLEANUP": "systems.safe_cleanup",
    "KAGGLE_JOB": "systems.prepare_kaggle_job",
    "INSTALL_TECHNOLOGY": "systems.install_technology",
    "TECHNOLOGY_HANDOFF": "systems.technology_handoff",
}
SYSTEMS_RETRY_LIMIT = 3
SYSTEMS_S1_HEALTH_URL = "http://127.0.0.1:18770/health"


def worker_scope_required(worker: str) -> bool:
    """Coding agents only receive a Systems-resolved scope envelope."""
    return str(worker).upper() in {"KILO", "OPENCODE", "CODEX"}


def classify_managed_action(action: str, action_config: dict[str, Any], *, target_resolved: bool,
                            validation: Any, rollback: Any) -> str:
    """Apply the shared maintenance policy before dispatching a typed action."""
    if not target_resolved:
        raise ValueError("TARGET_UNRESOLVED")
    facts = action_config.get("policy_facts", {})
    if not isinstance(facts, dict):
        raise ValueError("MAINTENANCE_POLICY_FACTS_INVALID")
    if facts.get("external_payment_step") is True:
        return "WAITING_EXTERNAL_BOUNDARY"
    if (action == "CREDENTIAL_ROTATION" or action == "ROLLBACK"
            or facts.get("unexpected_cost") is True or facts.get("paid_activation") is True
            or facts.get("credential_or_private_data_access") is True
            or facts.get("material_sensitive_data_movement") is True):
        return "RAY_APPROVAL_REQUIRED"
    if any(facts.get(key) is not True for key in (
            "zero_unexpected_cost", "no_paid_activation", "no_credential_access", "no_sensitive_data_movement")):
        return "RAY_APPROVAL_REQUIRED"
    if not rollback or not isinstance(validation, dict) or not validation.get("required"):
        raise ValueError("AUTONOMOUS_MAINTENANCE_CONTRACT_INCOMPLETE")
    return "AUTONOMOUS_BOUNDED"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_only_health_evidence(report: dict[str, Any], db_path: Path) -> dict[str, Any]:
    checked_at = now()
    try:
        with urlopen(SYSTEMS_S1_HEALTH_URL, timeout=3) as response:
            body = json.loads(response.read(2048) or b"{}")
            direct_status = "PASS" if response.status == 200 and str(body.get("status", "")).casefold() in {"ok", "healthy", "pass"} else "FAIL"
            direct = {"status": direct_status, "http_status": response.status}
    except Exception as exc:
        direct_status = "UNKNOWN"
        direct = {"status": direct_status, "error_class": type(exc).__name__}
    stored_status = "UNKNOWN"
    try:
        with sqlite3.connect(db_path.resolve().as_uri() + "?mode=ro", uri=True, timeout=3) as con:
            row = con.execute("SELECT payload FROM receipts WHERE receipt_type='SYSTEMS_MAINTENANCE_TICK' ORDER BY created_at DESC,rowid DESC LIMIT 1").fetchone()
        tick = json.loads(row[0]) if row else {}
        stored_status = str(tick.get("checks", {}).get("systems_s1", {}).get("status", "UNKNOWN")).upper()
        if stored_status in {"HEALTHY", "OK"}:
            stored_status = "PASS"
        elif stored_status not in {"PASS", "FAIL"}:
            stored_status = "UNKNOWN"
    except (OSError, sqlite3.Error, TypeError, json.JSONDecodeError):
        stored_status = "UNKNOWN"
    reconciliation = ("UNKNOWN" if "UNKNOWN" in {direct_status, stored_status}
                      else "PASS" if direct_status == stored_status else "FAIL")
    checks = report.get("checks", {})
    r10_status = str(checks.get("r10_http_health", {}).get("status", "UNKNOWN")).upper()
    if r10_status not in {"PASS", "FAIL"}:
        r10_status = "UNKNOWN"
    return {
        "checked_at": checked_at,
        "systems_s1_health": direct,
        "research_r10_health": {"status": r10_status, "observed_at": report.get("checked_at")},
        "stored_vs_direct_health_reconciliation": {"status": reconciliation,
            "stored_systems_s1_status": stored_status, "direct_systems_s1_status": direct_status,
            "observed_at": checked_at},
        "findings": [
            {"name": "systems_s1_health", "status": direct_status, "observed_at": checked_at},
            {"name": "research_r10_health", "status": r10_status, "observed_at": report.get("checked_at")},
            {"name": "stored_vs_direct_health_reconciliation", "status": reconciliation, "observed_at": checked_at},
        ],
    }


def _connect(path: Path = DB) -> sqlite3.Connection:
    con = sqlite3.connect(path, timeout=5)
    con.execute("PRAGMA busy_timeout=5000")
    return con


def _append(con: sqlite3.Connection, job_id: str, kind: str, payload: dict[str, Any]) -> None:
    con.execute("INSERT INTO receipts(receipt_id,request_id,receipt_type,created_at,payload) VALUES(?,?,?,?,?)",
                ("sysrcpt_" + uuid.uuid4().hex[:24], job_id, kind, now(), json.dumps(payload, sort_keys=True)))


def _records(con: sqlite3.Connection, job_id: str) -> list[dict[str, Any]]:
    rows = con.execute("SELECT receipt_type,payload FROM receipts WHERE request_id=? AND receipt_type LIKE 'SYSTEMS_MANAGED_JOB%' ORDER BY created_at,rowid", (job_id,)).fetchall()
    out = []
    for kind, raw in rows:
        try:
            out.append({"kind": kind, **json.loads(raw)})
        except (TypeError, json.JSONDecodeError):
            continue
    return out


def _run_bounded_readonly(order: dict[str, Any], *, db_path: Path) -> dict[str, Any] | None:
    """Execute only existing fixed read-only probes, after target resolution."""
    if order.get("execution_agent") != "SYSTEMS_LOCAL" or order.get("approval_requirement") != "NONE_READ_ONLY":
        return None
    authorized = set(order.get("allowed_paths", []))
    component = order.get("component")
    if component == _READONLY_SYSTEMS_VALIDATION[0] and _READONLY_SYSTEMS_VALIDATION[1] in authorized:
        argv = [sys.executable, _READONLY_SYSTEMS_VALIDATION[1]]
        timeout = 120
        operation = "workflow_integrity"
    elif component == _READONLY_OPENCODE_REVIEW[0] and _READONLY_OPENCODE_REVIEW[1] in authorized:
        argv = ["opencode", "--version"]
        timeout = 15
        operation = "opencode_version_review"
    else:
        return None

    job_id = order["systems_job_id"]
    intent = record_agent_intent(job_id, order["allowed_paths"], db_path=db_path)
    if intent.get("status") != "EXECUTING":
        return intent
    try:
        completed = subprocess.run(argv, cwd=str(ROOT), capture_output=True, text=True,
                                    timeout=timeout, check=False, env=dict(os.environ))
        stdout = completed.stdout[-256_000:]
        if operation == "workflow_integrity":
            try:
                report = json.loads(stdout)
            except json.JSONDecodeError:
                raise ValueError("WORKFLOW_REPORT_INVALID")
            if not isinstance(report.get("checks"), dict) or not isinstance(report.get("check_count"), int):
                raise ValueError("WORKFLOW_REPORT_SCHEMA_INVALID")
            healthy = report.get("status") == "PASS" and completed.returncode == 0
            health_evidence = _read_only_health_evidence(report, db_path)
            findings_ok = all(item["status"] == "PASS" for item in health_evidence["findings"])
            result = {
                "summary": f"Workflow integrity check ran: {report.get('pass_count')} of {report.get('check_count')} checks passed.",
                "changes_made": [], "files_or_components_affected": ["Systems workflow integrity (read only)"],
                "validation": {"report_schema": "PASS", "probe_exit_code": completed.returncode},
                "health_result": report.get("status"), "workflow_report": report,
                **health_evidence,
                "remaining_issues": report.get("limitations", []),
                "recommendation": "NO_ACTION" if healthy and findings_ok else "REVIEW_DEGRADED_CHECKS",
                "next_action": "NO_ACTION" if healthy and findings_ok else "REVIEW_DEGRADED_CHECKS",
                "validation_pass": True,
            }
        else:
            if completed.returncode != 0 or not stdout.strip():
                raise RuntimeError("OPENCODE_VERSION_PROBE_FAILED")
            version = stdout.strip()[:100]
            result = {
                "summary": f"OpenCode version review completed; installed version is {version}.",
                "changes_made": [], "files_or_components_affected": ["OpenCode CLI version (read only)"],
                "validation": {"version_probe": "PASS"}, "health_result": "PASS",
                "remaining_issues": [], "recommendation": "NO_ACTION" if version == "1.19.5" else "TEST_FIRST",
                "validation_pass": True,
            }
        completed_order = complete_work(job_id, order["authoritative_target"], result, db_path=db_path)
        return {"operation": operation, "result": result, "completion": completed_order.get("status"),
                "post_change_drift": completed_order.get("post_change_drift")}
    except (OSError, ValueError, subprocess.SubprocessError, RuntimeError) as exc:
        failure = {"summary": f"Read-only {operation} could not be verified.", "changes_made": [],
                   "files_or_components_affected": [], "health_result": "UNVERIFIED",
                   "remaining_issues": [str(exc).split(":", 1)[0]], "validation_pass": False}
        completed_order = complete_work(job_id, order["authoritative_target"], failure, db_path=db_path)
        return {"operation": operation, "completion": completed_order.get("status"),
                "post_change_drift": completed_order.get("post_change_drift")}


def _run_typed_s1_handoff(order: dict[str, Any], *, db_path: Path, typed_executor: Any) -> dict[str, Any] | None:
    """Record a manifest-bound technology evaluation through the existing S1 bridge."""
    if order.get("requested_action") != "TECHNOLOGY_HANDOFF":
        return None
    config = order.get("typed_action_config") or {}
    if (not callable(typed_executor) or order.get("approval_requirement") != "NONE_TYPED_HANDOFF"
            or config.get("operation") != "systems.technology_handoff" or not config.get("payload")):
        return {"status": "TARGET_UNRESOLVED", "reason": "TYPED_HANDOFF_NOT_BOUND"}
    job_id = order["systems_job_id"]
    payload = dict(config["payload"])
    payload["source_job"] = job_id
    intent = record_agent_intent(job_id, order["allowed_paths"], db_path=db_path)
    if intent.get("status") != "EXECUTING":
        return intent
    try:
        response = typed_executor("systems.technology_handoff", environment_id="MAC_MINI",
            reason=order["objective"], idempotency_key="systems-handoff:" + job_id,
            gateway_request_id=job_id, correlation_id=job_id, payload=payload)
        if response.get("engine_status") != "RECEIVED_NOT_EXECUTED":
            raise RuntimeError("S1_HANDOFF_NOT_PERSISTED")
        result = {"summary": f"{payload['technology']} was recorded for Systems evaluation; no installation was performed.",
            "changes_made": ["Recorded one technology handoff in existing Systems S1 state."],
            "files_or_components_affected": ["Systems S1 technology handoff registry"],
            "validation": {"target_resolution": "PASS", "s1_operation": "PASS", "handoff_state": "RECEIVED_NOT_EXECUTED"},
            "health_result": "PASS", "remaining_issues": [],
            "recommendation": "BEGIN_BOUNDED_EVALUATION; installation requires a separate approved Systems project",
            "validation_pass": True, "manifest_updated": False}
        completed = complete_work(job_id, order["authoritative_target"], result, db_path=db_path)
        return {"operation": "systems.technology_handoff", "result": result,
                "completion": completed.get("status"), "post_change_drift": completed.get("post_change_drift")}
    except (OSError, ValueError, RuntimeError, TypeError) as exc:
        failure = {"summary": "Systems S1 did not confirm the technology handoff.", "changes_made": [],
            "files_or_components_affected": [], "health_result": "UNVERIFIED",
            "remaining_issues": [str(exc).split(":", 1)[0]], "validation_pass": False}
        with _connect(db_path) as con:
            _append(con, job_id, "SYSTEMS_MANAGED_JOB_EVENT",
                    {"systems_job_id": job_id, "status": "FAILED_RECOVERABLE", "result": failure})
        return {"operation": "systems.technology_handoff", "completion": "FAILED_RECOVERABLE"}


def classify_maintenance_policy(action_config: dict[str, Any], *, target_resolved: bool,
                                validation: Any, rollback: Any, typed_action: Any) -> str:
    """Classify one manifest-bounded installation before any dispatch."""
    if not target_resolved:
        raise ValueError("TARGET_UNRESOLVED")
    facts = action_config.get("policy_facts", {})
    if not isinstance(facts, dict):
        raise ValueError("MAINTENANCE_POLICY_FACTS_INVALID")
    if facts.get("external_payment_step") is True:
        return "WAITING_EXTERNAL_BOUNDARY"
    if facts.get("unexpected_cost") is True or facts.get("paid_activation") is True:
        return "RAY_APPROVAL_REQUIRED"
    if facts.get("credential_or_private_data_access") is True or facts.get("material_sensitive_data_movement") is True:
        return "RAY_APPROVAL_REQUIRED"
    if any(facts.get(key) is not True for key in (
            "zero_unexpected_cost", "no_paid_activation", "no_credential_access", "no_sensitive_data_movement")):
        return "RAY_APPROVAL_REQUIRED"
    if not rollback or not isinstance(validation, dict) or not validation.get("required"):
        raise ValueError("AUTONOMOUS_MAINTENANCE_CONTRACT_INCOMPLETE")
    if not isinstance(typed_action, dict) or typed_action.get("operation") != "systems.install_technology":
        raise ValueError("TYPED_INSTALL_ACTION_REQUIRED")
    return "AUTONOMOUS_BOUNDED"


def _manifest_record_rea_install(result: dict[str, Any], *, manifest_path: Path = MANIFEST) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["rea_mcp_installation"] = {
        "status": "INSTALLED_VALIDATED", "package": "rea-agents", "version": "6.8.0",
        "source": "https://github.com/morluto/rea", "environment": "MAC_MINI_RESEARCH",
        "client": "OpenCode 1.19.5",
        "configuration_target": str(Path.home() / ".config/opencode/opencode.jsonc"),
        "node_runtime": "24.22.1 side-by-side under ~/.nvm; active/default Node unchanged",
        "health_check": "OpenCode MCP listing + scoped REA doctor check",
        "rollback": "Restore scoped OpenCode backup and remove only the pinned REA package and side-by-side Node runtime.",
        "last_verified_at": now(),
        "systems_result": {k: result.get(k) for k in ("package_version", "node_version", "backup_path", "config_sha256_after")},
    }
    target = manifest.get("systems_managed_work", {}).get("action_targets", {}).get("INSTALL_TECHNOLOGY", {})
    target["installation_state"] = "INSTALLED_VALIDATED"
    manifest["systems_managed_work"]["execution"] = (
        "INSTALL_TECHNOLOGY resolves the Living Manifest target, classifies maintenance policy, "
        "requires a production approval reference only for RAY_APPROVAL_REQUIRED, invokes typed S1, "
        "validates, persists the managed result, and updates this manifest. AUTONOMOUS_BOUNDED requires no approval reference.")
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return manifest


def _run_typed_s1_install(order: dict[str, Any], *, db_path: Path, typed_executor: Any) -> dict[str, Any] | None:
    if order.get("requested_action") != "INSTALL_TECHNOLOGY":
        return None
    config = order.get("typed_action_config") or {}
    policy = order.get("maintenance_classification")
    if (not callable(typed_executor) or policy not in {"AUTONOMOUS_BOUNDED", "RAY_APPROVAL_REQUIRED"}
            or config.get("operation") != "systems.install_technology" or not isinstance(config.get("payload"), dict)):
        return {"status": "TARGET_UNRESOLVED", "reason": "TYPED_INSTALL_NOT_BOUND"}
    job_id = order["systems_job_id"]
    payload = dict(config["payload"])
    payload["policy_classification"] = policy
    reference = config.get("approval_reference")
    if policy == "RAY_APPROVAL_REQUIRED":
        if not reference:
            return {"status": "WAITING_APPROVAL", "reason": "RAY_APPROVAL_REFERENCE_REQUIRED"}
        payload["approval_reference"] = reference
    elif reference:
        return {"status": "FAILED_RECOVERABLE", "reason": "AUTONOMOUS_ACTION_MUST_NOT_REQUIRE_APPROVAL"}
    intent = record_agent_intent(job_id, order["allowed_paths"], db_path=db_path)
    if intent.get("status") != "EXECUTING":
        return intent
    try:
        response = typed_executor("systems.install_technology", environment_id="MAC_MINI",
            reason=order["objective"], idempotency_key="systems-install:" + job_id,
            gateway_request_id=job_id, correlation_id=job_id, payload=payload)
        if response.get("engine_status") != "INSTALLED_VALIDATED":
            s1_result = response.get("data") if isinstance(response.get("data"), dict) else {}
            failure_code = s1_result.get("failure_code")
            installer_diagnostics = s1_result.get("installer_diagnostics")
            if not isinstance(failure_code, str) or not failure_code.isascii() or not failure_code.replace("_", "").isalnum() or len(failure_code) > 96:
                failure_code = response.get("verification") or response.get("engine_status") or "S1_INSTALL_NOT_CONFIRMED"
            failure = {"summary": "Systems did not confirm the native installation and scoped validation.",
                "changes_made": [], "files_or_components_affected": order["allowed_paths"],
                "validation": {"s1_operation": response.get("engine_status")},
                "health_result": "UNVERIFIED", "remaining_issues": [failure_code],
                "validation_pass": False, "manifest_updated": False}
            if isinstance(installer_diagnostics, dict):
                # S1 applies the shared secret redactor before returning this bounded evidence.
                failure["installer_diagnostics"] = installer_diagnostics
            with _connect(db_path) as con:
                _append(con, job_id, "SYSTEMS_MANAGED_JOB_EVENT",
                        {"systems_job_id": job_id, "status": "FAILED_RECOVERABLE", "result": failure})
            return {"operation": "systems.install_technology", "completion": "FAILED_RECOVERABLE", "result": failure}
        result = response.get("data") or {}
        result = {"summary": "REA MCP was installed for OpenCode using the pinned native package and a side-by-side supported Node runtime.",
            "changes_made": ["Installed rea-agents 6.8.0 and added the native REA-owned OpenCode MCP registration."],
            "files_or_components_affected": order["allowed_paths"],
            "validation": result.get("validation", {}), "health_result": "PASS", "remaining_issues": [],
            "recommendation": "RUN_ONE_READ_ONLY_REA_VALUE_TEST", "validation_pass": True,
            "manifest_updated": False, **result}
        manifest_backup_dir = Path.home() / ".nexus/backups/systems-install-technology" / job_id
        manifest_backup_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        manifest_backup = manifest_backup_dir / "NEXUS_LIVING_MANIFEST.v1.json"
        shutil.copy2(MANIFEST, manifest_backup)
        _manifest_record_rea_install(result)
        result["manifest_updated"] = True
        result["manifest_backup_path"] = str(manifest_backup)
        completed = complete_work(job_id, order["authoritative_target"], result, db_path=db_path)
        return {"operation": "systems.install_technology", "result": result,
                "completion": completed.get("status"), "post_change_drift": completed.get("post_change_drift")}
    except (OSError, ValueError, RuntimeError, TypeError, subprocess.SubprocessError) as exc:
        failure = {"summary": "Systems S1 install operation failed safely.", "changes_made": [],
            "files_or_components_affected": [], "health_result": "UNVERIFIED",
            "remaining_issues": [str(exc).split(":", 1)[0]], "validation_pass": False}
        with _connect(db_path) as con:
            _append(con, job_id, "SYSTEMS_MANAGED_JOB_EVENT",
                    {"systems_job_id": job_id, "status": "FAILED_RECOVERABLE", "result": failure})
        return {"operation": "systems.install_technology", "completion": "FAILED_RECOVERABLE", "result": failure}


def _run_typed_s1_maintenance(order: dict[str, Any], *, db_path: Path, typed_executor: Any) -> dict[str, Any] | None:
    """Dispatch the remaining manifest-bound maintenance classes to typed S1."""
    action = str(order.get("requested_action") or "")
    operation = MANAGED_ACTION_OPERATIONS.get(action)
    if operation is None or action in {"INSTALL_TECHNOLOGY", "TECHNOLOGY_HANDOFF", "UPGRADE_REVIEW", "VALIDATION", "MAINTENANCE"}:
        return None
    config = order.get("typed_action_config") or {}
    if not callable(typed_executor) or config.get("operation") != operation or not isinstance(config.get("payload"), dict):
        return {"status": "TARGET_UNRESOLVED", "reason": "TYPED_ACTION_NOT_BOUND"}
    policy = order.get("maintenance_classification")
    if policy == "WAITING_EXTERNAL_BOUNDARY":
        update = {"systems_job_id": order["systems_job_id"], "status": "WAITING_EXTERNAL_BOUNDARY",
                  "result": {"summary": "This Systems action is waiting on an external or provider step.",
                             "validation_pass": False, "health_result": "UNVERIFIED"}}
        with _connect(db_path) as con:
            _append(con, order["systems_job_id"], "SYSTEMS_MANAGED_JOB_EVENT", update)
        return {"operation": operation, "completion": update["status"], "result": update["result"]}
    if policy == "RAY_APPROVAL_REQUIRED" and not config.get("approval_reference"):
        update = {"systems_job_id": order["systems_job_id"], "status": "WAITING_APPROVAL",
                  "result": {"summary": "This Systems action requires an explicit approval reference.",
                             "validation_pass": False, "health_result": "UNVERIFIED"}}
        with _connect(db_path) as con:
            _append(con, order["systems_job_id"], "SYSTEMS_MANAGED_JOB_EVENT", update)
        return {"operation": operation, "completion": update["status"], "result": update["result"]}
    if policy not in {"AUTONOMOUS_BOUNDED", "RAY_APPROVAL_REQUIRED"}:
        return {"status": "TARGET_UNRESOLVED", "reason": "MAINTENANCE_POLICY_NOT_CLASSIFIED"}

    job_id = order["systems_job_id"]
    payload = dict(config["payload"])
    payload["policy_classification"] = policy
    if isinstance(payload.get("job"), dict) and payload["job"].get("job_id") == "$SYSTEMS_JOB_ID":
        payload["job"]["job_id"] = job_id
    if policy == "RAY_APPROVAL_REQUIRED":
        reference = config.get("approval_reference")
        if not isinstance(reference, str) or not reference.startswith("sysapproval_"):
            return {"status": "WAITING_APPROVAL", "reason": "RAY_APPROVAL_REFERENCE_REQUIRED"}
        payload["approval_reference"] = reference
    elif config.get("approval_reference"):
        return {"status": "FAILED_RECOVERABLE", "reason": "AUTONOMOUS_ACTION_MUST_NOT_REQUIRE_APPROVAL"}

    intent = record_agent_intent(job_id, order["allowed_paths"], db_path=db_path)
    if intent.get("status") != "EXECUTING":
        return intent
    try:
        response = typed_executor(operation, environment_id=config.get("target_environment", "MAC_MINI"),
            service_id=config.get("service_id"), reason=order["objective"],
            idempotency_key="systems-action:" + job_id, gateway_request_id=job_id,
            correlation_id=job_id, payload=payload)
        engine_status = str(response.get("engine_status") or response.get("status") or "UNKNOWN")
        s1_result = response.get("data") if isinstance(response.get("data"), dict) else {}
        if engine_status in {"WAITING_EXTERNAL_BOUNDARY", "APPROVAL_REQUIRED", "APPROVAL_REJECTED"}:
            state = "WAITING_EXTERNAL_BOUNDARY" if engine_status == "WAITING_EXTERNAL_BOUNDARY" else "WAITING_APPROVAL"
            update = {"systems_job_id": job_id, "status": state,
                      "result": {"summary": "Systems safely held the requested action at its approval boundary.",
                                 "validation": {"s1_operation": engine_status}, "health_result": "UNVERIFIED",
                                 "remaining_issues": [engine_status], "validation_pass": False}}
            with _connect(db_path) as con:
                _append(con, job_id, "SYSTEMS_MANAGED_JOB_EVENT", update)
            return {"operation": operation, "completion": state, "result": update["result"]}
        passed = engine_status in {"DRY_RUN_VALIDATED", "PREPARED", "NO_SAFE_CLEANUP_TARGETS", "NO_RESTART_REQUIRED", "VERIFIED"}
        result = {
            "summary": str(s1_result.get("summary") or f"Systems {action.lower()} action returned {engine_status}."),
            "changes_made": s1_result.get("changes_made", []),
            "files_or_components_affected": s1_result.get("files_or_components_affected", order["allowed_paths"]),
            "validation": s1_result.get("validation", {"s1_operation": engine_status}),
            "health_result": s1_result.get("health_result", "PASS" if passed else "UNVERIFIED"),
            "remaining_issues": s1_result.get("remaining_issues", [] if passed else [engine_status]),
            "recommendation": s1_result.get("recommendation"),
            "validation_pass": passed,
            "manifest_updated": False,
        }
        if not passed:
            attempt = int(order.get("_systems_attempt_number", 1))
            retryable = (engine_status == "FAILED_RECOVERABLE" and attempt < SYSTEMS_RETRY_LIMIT
                         and s1_result.get("mutation_performed") is False
                         and s1_result.get("retry_evidence") in {"TRANSIENT_PROVIDER_OR_SERVICE_UNAVAILABLE", "TRANSIENT_RESOURCE_BUSY"})
            with _connect(db_path) as con:
                _append(con, job_id, "SYSTEMS_MANAGED_JOB_EVENT",
                        {"systems_job_id": job_id, "status": "FAILED_RECOVERABLE", "result": result,
                         "retry": {"attempt": attempt, "max_attempts": SYSTEMS_RETRY_LIMIT,
                                   "retryable": retryable, "reason": "S1_REPORTED_RECOVERABLE" if retryable else "NONTRANSIENT_OR_LIMIT_REACHED",
                                   "not_before": (datetime.now(timezone.utc) + timedelta(seconds=min(300, 30 * (2 ** (attempt - 1)))).isoformat()
                                                  if retryable else None)}})
            return {"operation": operation, "completion": "FAILED_RECOVERABLE", "result": result}
        completed = complete_work(job_id, order["authoritative_target"], result, db_path=db_path)
        return {"operation": operation, "result": result, "completion": completed.get("status"),
                "post_change_drift": completed.get("post_change_drift")}
    except (OSError, ValueError, RuntimeError, TypeError, subprocess.SubprocessError) as exc:
        attempt = int(order.get("_systems_attempt_number", 1))
        error_code = str(exc).split(":", 1)[0]
        # A lost bridge response is ambiguous about whether S1 acted. Never replay it automatically.
        retryable = False
        failure = {"summary": "Systems could not complete the bounded typed action.", "changes_made": [],
                   "files_or_components_affected": [], "health_result": "UNVERIFIED",
                   "remaining_issues": [error_code], "validation_pass": False}
        with _connect(db_path) as con:
            _append(con, job_id, "SYSTEMS_MANAGED_JOB_EVENT",
                    {"systems_job_id": job_id, "status": "FAILED_RECOVERABLE", "result": failure,
                     "retry": {"attempt": attempt, "max_attempts": SYSTEMS_RETRY_LIMIT,
                               "retryable": retryable, "reason": "TRANSIENT_TRANSPORT" if retryable else "NONTRANSIENT_OR_LIMIT_REACHED",
                               "not_before": (datetime.now(timezone.utc) + timedelta(seconds=min(300, 30 * (2 ** (attempt - 1)))).isoformat()
                                              if retryable else None)}})
        return {"operation": operation, "completion": "FAILED_RECOVERABLE", "result": failure}


def resume_recoverable_work(job_id: str, *, typed_executor: Any, db_path: Path = DB) -> dict[str, Any]:
    """Retry a due transient failure on the same persisted Systems job, at most twice after its first attempt."""
    with _connect(db_path) as con:
        rows = _records(con, job_id)
    if not rows:
        return {"status": "NOT_FOUND"}
    order = rows[0]
    latest = rows[-1]
    retry = latest.get("retry") if isinstance(latest.get("retry"), dict) else {}
    config = order.get("typed_action_config") if isinstance(order.get("typed_action_config"), dict) else {}
    attempt = int(retry.get("attempt", 0))
    if latest.get("status") != "FAILED_RECOVERABLE" or retry.get("retryable") is not True:
        return {"status": "NOT_ELIGIBLE"}
    if order.get("maintenance_classification") != "AUTONOMOUS_BOUNDED" or config.get("approval_reference"):
        return {"status": "GOVERNANCE_BOUNDARY_NOT_AUTORETRIED"}
    if attempt >= SYSTEMS_RETRY_LIMIT:
        return {"status": "RETRY_LIMIT_REACHED"}
    not_before = retry.get("not_before")
    if not_before:
        try:
            if datetime.fromisoformat(str(not_before)) > datetime.now(timezone.utc):
                return {"status": "NOT_DUE"}
        except ValueError:
            return {"status": "RETRY_SCHEDULE_INVALID"}
    resumed = dict(order)
    resumed["_systems_attempt_number"] = attempt + 1
    with _connect(db_path) as con:
        _append(con, job_id, "SYSTEMS_MANAGED_JOB_EVENT", {
            "systems_job_id": job_id, "status": "RUNNING", "stage": "SAME_JOB_RETRY",
            "retry": {"attempt": attempt + 1, "max_attempts": SYSTEMS_RETRY_LIMIT}})
    result = _run_typed_s1_maintenance(resumed, db_path=db_path, typed_executor=typed_executor)
    return result or {"status": "FAILED_FINAL", "reason": "NO_REGISTERED_CONTINUATION_HANDLER"}


def next_ready_readonly_job(*, db_path: Path = DB) -> str | None:
    """Return one exact READY job supported by the deterministic local probes."""
    try:
        with _connect(db_path) as con:
            ids = [row[0] for row in con.execute(
                "SELECT request_id FROM receipts WHERE receipt_type LIKE 'SYSTEMS_MANAGED_JOB%' "
                "GROUP BY request_id ORDER BY MIN(rowid)")]
            for job_id in reversed(ids):
                rows = _records(con, str(job_id))
                if not rows:
                    continue
                order, latest = rows[0], rows[-1]
                state = str(latest.get("status", order.get("status", ""))).upper()
                if state not in {"READY", "READY_FOR_AGENT"}:
                    continue
                if not _eligible_readonly_validation(order):
                    continue
                allowed = set(order.get("allowed_paths", []))
                component = order.get("component")
                if ((component == _READONLY_SYSTEMS_VALIDATION[0] and allowed == {_READONLY_SYSTEMS_VALIDATION[1]})
                        or (component == _READONLY_OPENCODE_REVIEW[0] and allowed == {_READONLY_OPENCODE_REVIEW[1]})):
                    return str(job_id)
    except (OSError, sqlite3.Error):
        return None
    return None


def _eligible_readonly_validation(order: dict[str, Any]) -> bool:
    action = order.get("requested_action")
    legacy_readonly_validation = not action and order.get("change_class") == "READ_ONLY_REVIEW"
    return bool((action in {"VALIDATION", "MAINTENANCE"} or legacy_readonly_validation)
        and order.get("execution_agent") == "SYSTEMS_LOCAL"
        and order.get("approval_requirement") == "NONE_READ_ONLY"
        and isinstance(order.get("authoritative_target"), dict)
        and order["authoritative_target"].get("authority_check") == "PASS")


def resume_ready_readonly_work(job_id: str, *, db_path: Path = DB) -> dict[str, Any]:
    """Atomically claim and run one already-persisted deterministic read-only job."""
    with _connect(db_path) as con:
        con.execute("BEGIN IMMEDIATE")
        rows = _records(con, job_id)
        if not rows:
            con.rollback()
            return {"status": "NOT_FOUND"}
        order, latest = rows[0], rows[-1]
        state = str(latest.get("status", order.get("status", ""))).upper()
        if state not in {"READY", "READY_FOR_AGENT"}:
            con.rollback()
            return {"status": "NOT_ELIGIBLE"}
        if not _eligible_readonly_validation(order):
            con.rollback()
            return {"status": "NOT_ELIGIBLE"}
        allowed = set(order.get("allowed_paths", []))
        component = order.get("component")
        expected = (_READONLY_SYSTEMS_VALIDATION if component == "systems"
                    else _READONLY_OPENCODE_REVIEW if component == "opencode" else None)
        if expected is None or allowed != {expected[1]}:
            con.rollback()
            return {"status": "TARGET_UNRESOLVED"}
        try:
            manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
            fresh_scope = resolve_target(manifest, str(component), str(order.get("objective", "")), [expected[1]])
            if fresh_scope.get("authority_check") != "PASS" or set(fresh_scope.get("authorized_files", [])) != allowed:
                raise ValueError("TARGET_SCOPE_CHANGED")
        except (OSError, ValueError, json.JSONDecodeError):
            con.rollback()
            return {"status": "TARGET_UNRESOLVED"}
        order = dict(order)
        order["authoritative_target"] = fresh_scope
        order["allowed_paths"] = [expected[1]]
        _append(con, job_id, "SYSTEMS_MANAGED_JOB_EVENT", {
            "systems_job_id": job_id, "status": "RUNNING", "stage": "READY_JOB_CLAIM",
            "claimed_at": now(), "execution_agent": "SYSTEMS_LOCAL", "ai_usage": "NONE"})
        con.commit()
    result = _run_bounded_readonly(order, db_path=db_path)
    if result is None:
        with _connect(db_path) as con:
            _append(con, job_id, "SYSTEMS_MANAGED_JOB_EVENT", {
                "systems_job_id": job_id, "status": "FAILED_RECOVERABLE",
                "result": {"summary": "No registered deterministic Systems validation handler matched this work order.",
                           "health_result": "UNVERIFIED", "validation_pass": False,
                           "remaining_issues": ["NO_REGISTERED_READ_ONLY_HANDLER"]}})
        return {"status": "FAILED_RECOVERABLE", "same_job": True, "attempted": True}
    return {"status": str(result.get("completion") or result.get("status", "UNKNOWN")),
            "same_job": True, "attempted": True, "ai_usage": "NONE"}


def create_work_order(*, component: str, objective: str, requested_files: list[str], requested_by: str,
                      environment: str, change_class: str, execution_agent: str,
                      approval_requirement: str, validation: Any, rollback: Any,
                      manifest: dict[str, Any] | None = None, db_path: Path = DB,
                      requested_action: str = "", typed_action_config: dict[str, Any] | None = None,
                      typed_executor: Any = None, approval_reference: str | None = None) -> dict[str, Any]:
    job_id = "sysjob_" + uuid.uuid4().hex[:24]
    try:
        scope = resolve_target(manifest or json.loads(MANIFEST.read_text()), component, objective, requested_files)
        status = "READY_FOR_AGENT"
        error = None
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        scope = {"component": component, "target_confirmation": "FAIL", "authority_check": "FAIL", "authorized_files": []}
        status = "TARGET_UNRESOLVED"
        error = str(exc).split(":", 1)[0]
    registry = (manifest or json.loads(MANIFEST.read_text())).get("change_target_registry", {})
    component_record = registry.get("components", {}).get(component, {})
    prohibited = component_record.get("do_not_patch_paths", []) + registry.get("global_do_not_patch_paths", [])
    # Historical assets are explicit denies even if the component's broad path
    # pattern would otherwise match them.
    prohibited += component_record.get("historical_only_paths", [])
    post_validation = {"required": ["focused_validation", "live_health_when_applicable", "post_change_drift_check"],
                       "scope_plan": {k: scope.get(k) for k in ("authorized_files", "baseline_sha256", "workspace_status_before_fingerprint", "workspace_status_available")}}
    order = {
        "systems_job_id": job_id, "requested_by": requested_by, "objective": objective,
        "component": component, "environment": environment, "change_class": change_class,
        "requested_action": requested_action, "typed_action_config": typed_action_config or {},
        "approval_requirement": approval_requirement, "authoritative_target": scope,
        "allowed_paths": scope.get("authorized_files", []),
        "prohibited_paths": prohibited, "do_not_patch_paths": prohibited,
        "expected_service": scope.get("authoritative_service"),
        "expected_database": scope.get("authoritative_database"),
        "execution_agent": execution_agent, "validation": validation, "rollback": rollback,
        "post_change_validation": post_validation,
        "status": status, "result": {"resolution_error": error} if error else None,
        "manifest_update_required": True,
    }
    if requested_action == "INSTALL_TECHNOLOGY" and status != "TARGET_UNRESOLVED":
        try:
            order["maintenance_classification"] = classify_maintenance_policy(
                (manifest or json.loads(MANIFEST.read_text())).get("systems_managed_work", {}).get("action_targets", {}).get("INSTALL_TECHNOLOGY", {}),
                target_resolved=True, validation=validation, rollback=rollback, typed_action=order["typed_action_config"])
            order["approval_requirement"] = order["maintenance_classification"]
            if order["maintenance_classification"] == "WAITING_EXTERNAL_BOUNDARY":
                status = "WAITING_EXTERNAL_BOUNDARY"
            elif order["maintenance_classification"] == "RAY_APPROVAL_REQUIRED" and not approval_reference:
                status = "WAITING_APPROVAL"
            else:
                order["typed_action_config"]["approval_reference"] = approval_reference
            order["status"] = status
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            order["status"] = status = "TARGET_UNRESOLVED"
            order["result"] = {"resolution_error": str(exc).split(":", 1)[0]}
    elif requested_action in MANAGED_ACTION_OPERATIONS and requested_action not in {"TECHNOLOGY_HANDOFF", "INSTALL_TECHNOLOGY"} and status != "TARGET_UNRESOLVED":
        try:
            action_config = (manifest or json.loads(MANIFEST.read_text())).get("systems_managed_work", {}).get("action_targets", {}).get(requested_action, {})
            order["maintenance_classification"] = classify_managed_action(
                requested_action, action_config, target_resolved=True, validation=validation, rollback=rollback)
            order["approval_requirement"] = order["maintenance_classification"]
            if order["maintenance_classification"] == "WAITING_EXTERNAL_BOUNDARY":
                status = "WAITING_EXTERNAL_BOUNDARY"
            elif order["maintenance_classification"] == "RAY_APPROVAL_REQUIRED" and not approval_reference:
                status = "WAITING_APPROVAL"
            elif order["maintenance_classification"] == "RAY_APPROVAL_REQUIRED":
                order["typed_action_config"]["approval_reference"] = approval_reference
            order["status"] = status
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            order["status"] = status = "TARGET_UNRESOLVED"
            order["result"] = {"resolution_error": str(exc).split(":", 1)[0]}
    elif approval_reference:
        order["typed_action_config"]["approval_reference"] = approval_reference
    with _connect(db_path) as con:
        _append(con, job_id, "SYSTEMS_MANAGED_JOB", order)
    execution = (_run_typed_s1_install(order, db_path=db_path, typed_executor=typed_executor)
                 if requested_action == "INSTALL_TECHNOLOGY" and status == "READY_FOR_AGENT" else None)
    if execution is None and requested_action in MANAGED_ACTION_OPERATIONS:
        execution = _run_typed_s1_maintenance(order, db_path=db_path, typed_executor=typed_executor)
    if execution is None:
        execution = _run_typed_s1_handoff(order, db_path=db_path, typed_executor=typed_executor)
    if execution is None:
        execution = _run_bounded_readonly(order, db_path=db_path)
    if execution is not None:
        order["execution"] = execution
        order["status"] = execution.get("completion", order["status"])
        if execution.get("result"):
            order["result"] = execution["result"]
    return order


def record_agent_intent(job_id: str, intended_paths: list[str], *, db_path: Path = DB) -> dict[str, Any]:
    with _connect(db_path) as con:
        rows = _records(con, job_id)
        if not rows:
            raise KeyError("SYSTEMS_JOB_NOT_FOUND")
        order = rows[0]
        intended = {str(Path(x).expanduser().resolve(strict=False)) for x in intended_paths}
        allowed = set(order.get("allowed_paths", []))
        if not intended or not intended.issubset(allowed):
            update = {"systems_job_id": job_id, "status": "INTENT_REJECTED", "intended_paths": sorted(intended), "reason": "TARGET_CONFLICT"}
        else:
            update = {"systems_job_id": job_id, "status": "EXECUTING", "intended_paths": sorted(intended)}
        _append(con, job_id, "SYSTEMS_MANAGED_JOB_EVENT", update)
    return update


def complete_work(job_id: str, scope_plan: dict[str, Any], result: dict[str, Any], *, db_path: Path = DB) -> dict[str, Any]:
    drift = post_change_check(scope_plan)
    passed = drift.get("post_change_drift_check") == "PASS" and result.get("validation_pass") is True
    health = str(result.get("health_result") or "").upper()
    final_state = ("COMPLETED" if health in {"PASS", "HEALTHY"} else "COMPLETED_WITH_LIMITATIONS") if passed else "VALIDATING"
    update = {"systems_job_id": job_id, "status": final_state,
              "result": result, "post_change_drift": drift}
    with _connect(db_path) as con:
        if not _records(con, job_id):
            raise KeyError("SYSTEMS_JOB_NOT_FOUND")
        _append(con, job_id, "SYSTEMS_MANAGED_JOB_EVENT", update)
    return update


def get_work(job_id: str, *, db_path: Path = DB) -> dict[str, Any]:
    with _connect(db_path) as con:
        rows = _records(con, job_id)
    if not rows:
        raise KeyError("SYSTEMS_JOB_NOT_FOUND")
    return {"work_order": rows[0], "events": rows[1:], "current_status": rows[-1].get("status", rows[0].get("status"))}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    create = sub.add_parser("create")
    for name in ("component", "objective", "requested-by", "environment", "change-class", "execution-agent", "files-json", "validation-json", "rollback-json"):
        create.add_argument("--" + name, required=True)
    create.add_argument("--approval-requirement", default="NONE_RECORDED")
    status = sub.add_parser("status"); status.add_argument("systems_job_id")
    intent = sub.add_parser("intent"); intent.add_argument("systems_job_id"); intent.add_argument("--paths-json", required=True)
    a = p.parse_args()
    try:
        if a.command == "create":
            result = create_work_order(component=a.component, objective=a.objective,
                requested_files=json.loads(a.files_json), requested_by=a.requested_by,
                environment=a.environment, change_class=a.change_class, execution_agent=a.execution_agent,
                approval_requirement=a.approval_requirement, validation=json.loads(a.validation_json), rollback=json.loads(a.rollback_json))
        elif a.command == "status": result = get_work(a.systems_job_id)
        else: result = record_agent_intent(a.systems_job_id, json.loads(a.paths_json))
        print(json.dumps(result, sort_keys=True, default=str))
        return 0
    except (OSError, ValueError, json.JSONDecodeError, KeyError, sqlite3.Error) as exc:
        print(json.dumps({"status": "FAILED", "error": str(exc).split(":", 1)[0]}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
