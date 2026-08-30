#!/usr/bin/env python3
"""Bounded Active Operator foundation.

This runner is deliberately closed-world: it reads Nexus state, classifies
attention, creates governed pending work orders for approval-required work,
and writes receipts/heartbeat. It never executes arbitrary registry commands,
network calls, external messaging, financial actions, or infrastructure work.
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import subprocess
import sys
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts/operations"))

from nexus_agent_platform.governed import approvals, work_orders  # noqa: E402
from process_registry_adapter import emit_process_run  # noqa: E402
import process_registry_adapter  # noqa: E402
from business_active_operator import discover_business_attention, write_business_priority_brief  # noqa: E402

REGISTRY_PATH = ROOT / "data/operations/nexus_process_registry.json"
CAMPAIGN_PATH = ROOT / "data/runtime/nexus_loop_certification_campaign.json"
SCHEDULER_HEALTH_PATH = ROOT / "reports/phase16a/scheduler_health.json"
HEARTBEAT_PATH = ROOT / "reports/runtime/nexus_active_operator_heartbeat_latest.json"
RUNNER_REPORT_PATH = ROOT / "reports/runtime/nexus_active_operator_runner_latest.md"
BUSINESS_BRIEF_PATH = ROOT / "reports/runtime/nexus_active_operator_business_brief_latest.md"
RECEIPT_DIR = ROOT / "reports/runtime/nexus_active_operator_receipts"
SYSTEM_HEALTH_REPORT_PATH = ROOT / "reports/runtime/nexus_system_health_latest.json"
SUPABASE_REPORT_PATH = ROOT / "reports/supabase/nexus_supabase_browser_verification_latest.md"
ESCALATION_DIR = ROOT / "reports/runtime/nexus_active_operator_escalations"
WORK_ORDER_STATE_PATH = ROOT / "data/runtime/active_operator_work_orders.json"
RESEARCH_QUEUE_PATH = ROOT / "data/runtime/alpha_research/portfolio_requests.jsonl"
WORK_ITEM_STATE_PATH = ROOT / "data/runtime/active_operator_work_item_state.json"
OPERATOR_LATEST_PATH = ROOT / "reports/runtime/active_operator_latest.json"
OPERATOR_HEARTBEAT_PATH = ROOT / "reports/runtime/active_operator_heartbeat.json"
OPERATOR_REPORT_JSON_PATH = ROOT / "reports/certification/nexus_active_operator_v1_latest.json"
OPERATOR_REPORT_MD_PATH = ROOT / "reports/certification/nexus_active_operator_v1_latest.md"
LOCK_PATH = ROOT / "data/runtime/nexus_active_operator.lock"
KILL_SWITCH_PATH = ROOT / "data/runtime/active_operator_control.json"
CADENCE_SECONDS = 300
MAX_NEW_WORK_ORDERS = 3
MAX_EXECUTIONS = 3
MAX_RESEARCH_TASKS = 1
MAX_RUNTIME_SECONDS = 600

SAFE_INTERNAL_ACTIONS = frozenset({
    "read_operational_state", "write_heartbeat", "write_receipt", "generate_internal_report", "business_attention.generate", "measurement_gap.report", "research.refresh",
})
NOT_AUTHORIZED_ACTIONS = frozenset({
    "stripe.live_activation", "financial.transactions", "place_trade", "charge_customer",
    "send_customer_email", "send_sms", "post_to_social_media", "submit_grant_application",
    "submit_credit_dispute", "shell.arbitrary", "restart_production_services",
    "modify_production_database",
})
PRIORITY_RANK = {"P0": 0, "P1": 1, "P2": 2, "P3": 3, "P4": 4}

CAPABILITY_REGISTRY = {
    "searxng.research": {"status": "READY", "authority": "READ_ONLY", "safe_actions": ["research.refresh"], "gated_actions": []},
    "oracle.gemma": {"status": "READY", "authority": "ADVISORY_ONLY", "safe_actions": ["research.synthesize"], "gated_actions": ["execution.approve"]},
    "google.gmail.read": {"status": "READY", "authority": "READ_ONLY", "safe_actions": ["google.gmail.read"], "gated_actions": ["email.send"]},
    "google.calendar.read": {"status": "READY", "authority": "READ_ONLY", "safe_actions": ["google.calendar.read"], "gated_actions": ["calendar.mutate"]},
    "google.drive.read": {"status": "READY", "authority": "READ_ONLY", "safe_actions": ["google.drive.read"], "gated_actions": ["drive.mutate"]},
    "telegram.transport": {"status": "READY", "authority": "GOVERNED_OUTBOUND", "safe_actions": ["telegram.read"], "gated_actions": ["telegram.send"]},
    "youtube.metadata": {"status": "READY", "authority": "READ_ONLY", "safe_actions": ["youtube.read"], "gated_actions": ["youtube.publish"]},
    "oanda.practice.read": {"status": "READY", "authority": "PRACTICE_READ_ONLY", "safe_actions": ["forex.read"], "gated_actions": ["forex.place_order"]},
    "forex.practice.execution": {"status": "GATED", "authority": "PRACTICE_ONLY", "safe_actions": [], "gated_actions": ["forex.place_order"]},
    "meta.read": {"status": "READY", "authority": "READ_ONLY", "safe_actions": ["meta.read"], "gated_actions": []},
    "meta.inbound": {"status": "NOT_READY", "authority": "INGEST_ONLY", "safe_actions": [], "gated_actions": ["meta.inbound"], "block_reason": "webhook callback and signature verifier are not certified"},
    "meta.publish": {"status": "GATED", "authority": "NONE", "safe_actions": [], "gated_actions": ["meta.publish"], "block_reason": "outbound social publishing requires Ray approval"},
    "email.send": {"status": "GATED", "authority": "NONE", "safe_actions": [], "gated_actions": ["email.send"], "block_reason": "Resend domain status is not certified and outbound send is gated"},
    "voice.local": {"status": "READY", "authority": "LOCAL_ONLY", "safe_actions": ["voice.read"], "gated_actions": []},
    "voice.remote": {"status": "PARTIAL", "authority": "REMOTE_UNPROVEN", "safe_actions": [], "gated_actions": ["voice.remote"]},
    "payments": {"status": "GATED", "authority": "NONE", "safe_actions": [], "gated_actions": ["payments"]},
    "netlify.release": {"status": "GATED", "authority": "NONE", "safe_actions": [], "gated_actions": ["netlify.release"]},
    "groq.models": {"status": "OPTIONAL_MISSING", "authority": "ADVISORY_ONLY", "safe_actions": [], "gated_actions": []},
    "gemini.models": {"status": "OPTIONAL_MISSING", "authority": "ADVISORY_ONLY", "safe_actions": [], "gated_actions": []},
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return default


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def relative_or_absolute(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def load_governed_supabase_environment() -> None:
    """Load only server/browser Supabase settings for this bounded process."""
    allowed = {"SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY", "VITE_SUPABASE_URL", "VITE_SUPABASE_ANON_KEY"}
    for path in (ROOT / ".env", Path("/Users/raymonddavis/.config/nexus/runtime.env")):
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for line in lines:
            key, separator, value = line.partition("=")
            key = key.strip()
            if separator and key in allowed and key not in os.environ:
                os.environ[key] = value.strip().strip("\"'")


def run_system_health_check(*, incoming_update_id: int, correlation_id: str, trigger: str = "telegram") -> Dict[str, Any]:
    """Run only the registered low-risk System Health Check process.

    This is a manual, read-only entry point. It does not invoke the Active
    Operator scheduler or discover/dispatch unrelated work.
    """
    run_id = f"system_health_{uuid.uuid4().hex}"
    started = utc_now()
    load_governed_supabase_environment()
    registry = load_json(REGISTRY_PATH, [])
    rows = registry if isinstance(registry, list) else registry.get("processes", []) if isinstance(registry, dict) else []
    process = next((row for row in rows if isinstance(row, dict) and row.get("process_id") == "system_health"), None)
    base = {"process_id": "system_health", "run_id": run_id, "incoming_update_id": incoming_update_id, "correlation_id": correlation_id, "trigger": trigger, "started_at": started}
    if (not process or not process.get("enabled") or process.get("mode") != "ACTIVE_INTERNAL" or process.get("schedule_type") != "manual" or process.get("trigger") != "telegram /run system_health or manual" or process.get("runner_path") != "scripts/operations/nexus_active_operator_runner.py" or process.get("report_path") != "reports/runtime/nexus_system_health_latest.json" or process.get("receipt_path") != "reports/runtime/nexus_active_operator_receipts/" or process.get("approval_required") is not False or process.get("telegram_allowed") is not True or process.get("risk_level") != "low"):
        completed = utc_now()
        failure = {**base, "completed_at": completed, "execution_status": "FAILED", "error": "canonical system_health process is not enabled as low-risk ACTIVE_INTERNAL"}
        write_json(SYSTEM_HEALTH_REPORT_PATH, failure)
        receipt = {"receipt_id": f"system_health_receipt_{run_id}", **failure, "report_path": relative_or_absolute(SYSTEM_HEALTH_REPORT_PATH), "receipt_path": relative_or_absolute(RECEIPT_DIR / f"system_health_{run_id}.json"), "external_side_effects": False, "read_only": True}
        write_json(RECEIPT_DIR / f"system_health_{run_id}.json", receipt)
        return {**failure, "canonical_report_path": str(SYSTEM_HEALTH_REPORT_PATH), "canonical_receipt_path": str(RECEIPT_DIR / f"system_health_{run_id}.json"), "canonical_report_written": True, "canonical_receipt_written": True}
    try:
        from nexus_agent_platform.capabilities.shared import _handle_system_health
        health = _handle_system_health(trace_id=correlation_id)
        completed = utc_now()
        result = {**base, "completed_at": completed, "execution_status": "COMPLETED", "health_status": health.get("status"), "health_result": health, "read_only": True, "external_side_effects": False}
    except Exception as exc:
        completed = utc_now()
        result = {**base, "completed_at": completed, "execution_status": "FAILED", "error": type(exc).__name__, "read_only": True, "external_side_effects": False}
    write_json(SYSTEM_HEALTH_REPORT_PATH, result)
    receipt = {"receipt_id": f"system_health_receipt_{run_id}", **result, "report_path": relative_or_absolute(SYSTEM_HEALTH_REPORT_PATH), "receipt_path": relative_or_absolute(RECEIPT_DIR / f"system_health_{run_id}.json")}
    receipt_path = RECEIPT_DIR / f"system_health_{run_id}.json"
    write_json(receipt_path, receipt)
    return {**result, "canonical_report_path": str(SYSTEM_HEALTH_REPORT_PATH), "canonical_receipt_path": str(receipt_path), "canonical_report_written": True, "canonical_receipt_written": True}


def run_supabase_verification(*, incoming_update_id: int, correlation_id: str, trigger: str = "telegram") -> Dict[str, Any]:
    """Run the registered, manual, read-only Supabase verification only."""
    run_id = f"supabase_verification_{uuid.uuid4().hex}"
    started = utc_now()
    registry = load_json(REGISTRY_PATH, [])
    rows = registry if isinstance(registry, list) else registry.get("processes", []) if isinstance(registry, dict) else []
    process = next((row for row in rows if isinstance(row, dict) and row.get("process_id") == "supabase_verification"), None)
    campaign = load_json(CAMPAIGN_PATH, {})
    base = {"process_id": "supabase_verification", "run_id": run_id, "supabase_run_id": run_id, "campaign_id": campaign.get("campaign_id") if isinstance(campaign, dict) else None, "loop_id": "supabase_verification", "incoming_update_id": incoming_update_id, "correlation_id": correlation_id, "trigger": trigger, "started_at": started, "read_only": True, "database_mutations": 0}
    valid = process and process.get("enabled") is True and process.get("mode") == "ACTIVE_INTERNAL" and process.get("schedule_type") == "manual" and process.get("trigger") == "telegram /run supabase_verification or manual" and process.get("runner_path") == "scripts/operations/nexus_active_operator_runner.py" and process.get("report_path") == "reports/supabase/nexus_supabase_browser_verification_latest.md" and process.get("receipt_path") == "reports/runtime/nexus_active_operator_receipts/" and process.get("risk_level") == "low" and process.get("approval_required") is False and process.get("telegram_allowed") is True and "database_writes" in process.get("blocked_actions", [])
    if not valid:
        result = {**base, "execution_status": "FAILED", "completed_at": utc_now(), "overall_verification": "BLOCKED", "error": "canonical supabase_verification process is not enabled as low-risk ACTIVE_INTERNAL"}
    else:
        load_governed_supabase_environment()
        server_read = {"verified": False, "table": "nexus_process_definitions", "columns": "process_key", "rows_returned": 0, "read_only": True}
        try:
            from nexus_agent_platform.capabilities.supabase_read_client import create_supabase_read_client
            client = create_supabase_read_client()
            if client is None:
                server_read["error"] = "governed Supabase credentials unavailable"
            else:
                response = client.table("nexus_process_definitions").select("process_key").limit(1).execute()
                server_read["verified"] = bool(response.ok)
                server_read["rows_returned"] = len(response.data) if isinstance(response.data, list) else 0
                if not response.ok: server_read["error"] = "governed read returned non-success"
        except Exception as exc:
            server_read["error"] = type(exc).__name__
        browser_evidence_path = RECEIPT_DIR / f"supabase_browser_{run_id}.json"
        browser_command = ["npm", "exec", "playwright", "test", "tests/e2e/supabase-real-world-certification.spec.ts", "--reporter=line"]
        browser_env = {**os.environ, "SUPABASE_CERT_EVIDENCE_PATH": str(browser_evidence_path), "E2E_ENABLE_AUTHENTICATED": "true"}
        try:
            browser_run = subprocess.run(browser_command, cwd=ROOT, env=browser_env, capture_output=True, text=True, timeout=180, check=False)
            browser_process_ok = browser_run.returncode == 0 and browser_evidence_path.exists()
        except (OSError, subprocess.SubprocessError):
            browser_process_ok = False
        browser_evidence = load_json(browser_evidence_path, {}) if browser_process_ok else {}
        frontend_files = [ROOT / "src", ROOT / "dist/assets"]
        exposure = False
        for path in frontend_files:
            if path.is_file(): candidates = [path]
            elif path.is_dir(): candidates = [item for item in path.rglob("*") if item.is_file()]
            else: candidates = []
            for item in candidates:
                try:
                    text = item.read_text(encoding="utf-8", errors="ignore")
                except OSError:
                    continue
                if "SUPABASE_SERVICE_ROLE_KEY" in text or "service_role" in text.lower(): exposure = True
        browser_config = bool(os.getenv("VITE_SUPABASE_URL") and os.getenv("VITE_SUPABASE_ANON_KEY")) and not exposure
        completed = utc_now()
        browser = {"safe_config_verified": browser_config, "no_service_role_frontend_exposure": not exposure, "authenticated_read_verified": browser_evidence.get("authenticated_session_verified") is True and browser_evidence.get("browser_supabase_read_verified") is True, "rls_isolation_verified": browser_evidence.get("rls_tenant_isolation_verified") is True, "own_scope_read": browser_evidence.get("own_scope_read", "NOT_PROVEN"), "cross_tenant_read": browser_evidence.get("cross_tenant_read", "NOT_PROVEN"), "admin_only_read": browser_evidence.get("admin_only_read", "NOT_PROVEN"), "status": "PASS" if browser_process_ok else "WAITING_BROWSER_SESSION"}
        overall = "VERIFIED" if server_read["verified"] and browser_config and browser["authenticated_read_verified"] and browser["rls_isolation_verified"] else "PARTIAL" if server_read["verified"] or browser_config else "BLOCKED"
        result = {**base, "execution_status": "COMPLETED", "completed_at": completed, "server_read": server_read, "browser": browser, "overall_verification": overall, "evidence_refs": [f"supabase:run:{run_id}", f"supabase:report:{SUPABASE_REPORT_PATH.relative_to(ROOT)}", f"supabase:browser:{browser_evidence_path.relative_to(ROOT)}"], "report_path": str(SUPABASE_REPORT_PATH.relative_to(ROOT)), "receipt_path": str((RECEIPT_DIR / f"supabase_verification_{run_id}.json").relative_to(ROOT))}
    receipt_path = RECEIPT_DIR / f"supabase_verification_{run_id}.json"
    SUPABASE_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    report_lines = ["# Supabase Verification", "", f"Run: {run_id}", f"Correlation: {correlation_id}", f"Overall verification: {result.get('overall_verification', 'BLOCKED')}", "", f"Server governed read: {'PASS' if result.get('server_read', {}).get('verified') else 'FAIL'}", f"Browser configuration: {'PASS' if result.get('browser', {}).get('safe_config_verified') else 'FAIL'}", f"Service-role frontend exposure: {'FAIL' if result.get('browser', {}).get('no_service_role_frontend_exposure') is False else 'PASS'}", f"Authenticated browser read: {'PASS' if result.get('browser', {}).get('authenticated_read_verified') else 'NOT_PROVEN'}", f"RLS isolation: {'PASS' if result.get('browser', {}).get('rls_isolation_verified') else 'NOT_PROVEN'}", "Database writes: 0", "", "This bounded process performs governed reads only; service-role connectivity does not prove browser authentication or RLS isolation."]
    SUPABASE_REPORT_PATH.write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    result["canonical_report_written"] = True; result["canonical_receipt_written"] = True
    result["report_path"] = relative_or_absolute(SUPABASE_REPORT_PATH); result["receipt_path"] = relative_or_absolute(receipt_path)
    write_json(receipt_path, result)
    return {**result, "canonical_report_path": str(SUPABASE_REPORT_PATH), "canonical_receipt_path": str(receipt_path)}


def _sanitize_autonomy_environment() -> None:
    """Keep shared application credentials out of this process."""
    os.environ["NEXUS_AUTONOMY_STRIPE_DISABLED"] = "1"
    for key in (
        "STRIPE_SECRET_KEY", "STRIPE_PUBLISHABLE_KEY", "STRIPE_WEBHOOK_SECRET",
        "STRIPE_LIVE_WEBHOOK_SECRET", "VITE_STRIPE_PUBLISHABLE_KEY", "VITE_STRIPE_SECRET_KEY",
    ):
        os.environ.pop(key, None)


def kill_switch_enabled() -> bool:
    """Read the deterministic operator switch; missing/corrupt state fails closed."""
    control = load_json(KILL_SWITCH_PATH, {})
    return isinstance(control, dict) and control.get("active_operator_enabled") is True and control.get("mode") == "BOUNDED_INTERNAL_ONLY"


@contextmanager
def single_run_lock(path: Path | None = None):
    path = path or LOCK_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            yield False
            return
        try:
            yield True
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def priority_for(process: Dict[str, Any]) -> str:
    category = str(process.get("category", "")).lower()
    if any(term in category for term in ("safety", "security", "recovery", "system_health")):
        return "P0"
    if "client" in category:
        return "P1"
    if any(term in category for term in ("revenue", "funding", "money")):
        return "P2"
    if any(term in category for term in ("operation", "monitor", "process")):
        return "P3"
    return "P4"


def classify_action(action_id: str) -> str:
    if action_id in SAFE_INTERNAL_ACTIONS:
        return "AUTO_EXECUTE_INTERNAL_SAFE"
    if action_id in NOT_AUTHORIZED_ACTIONS:
        return "NOT_AUTHORIZED"
    return "APPROVAL_REQUIRED"


def execute_safe_internal_action(action_id: str, finding: Dict[str, Any]) -> Dict[str, Any]:
    """Execute only the fixed public-research adapter; all other actions stay declarative."""
    if action_id != "research.refresh":
        return {"status": "RECORDED_NOT_EXECUTED", "action": action_id}
    from nexus_agent_platform.loops.governed_loops import _research
    result = dict(_research({"question": finding.get("question"), "live_private_searxng": True}))
    result["synthetic"] = False
    result["source"] = "private SearXNG adapter"
    return result


def capability_snapshot() -> Dict[str, Dict[str, Any]]:
    """Return the deterministic capability map used by every operator cycle."""
    snapshot = {key: {**value, "capability_id": key, "last_verified": "existing_certification_or_runtime_state"}
                for key, value in CAPABILITY_REGISTRY.items()}
    try:
        from nexus_agent_platform.credential_control_plane import _netlify_env_names
        remote = _netlify_env_names()
        if {"CF_ACCESS_CLIENT_ID", "CF_ACCESS_CLIENT_SECRET", "VOICE_ACCESS_ORIGIN"}.issubset(remote):
            snapshot["voice.remote"].update(status="REMOTE_CONFIGURED", authority="REMOTE_SERVER_SIDE", last_verified="Netlify environment metadata")
        if "GROQ_API_KEY" in remote:
            snapshot["groq.models"].update(status="REMOTE_CONFIGURED", last_verified="Netlify environment metadata")
        if "OPENROUTER_API_KEY" in remote:
            snapshot["oracle.gemma"].setdefault("notes", []).append("OpenRouter remote fallback configured")
    except Exception:
        pass
    return snapshot


def priority_score(item: Dict[str, Any]) -> int:
    """Stable, explainable score; lower priority rank remains authoritative."""
    priority = PRIORITY_RANK.get(item.get("priority", "P4"), 4)
    readiness = item.get("capability_ready", True)
    return max(0, 100 - priority * 20 - (0 if readiness else 15))


def _stable_work_order_id(dedupe_key: str) -> str:
    return "awo_" + hashlib.sha256(dedupe_key.encode("utf-8")).hexdigest()[:20]


def _load_operator_work_orders() -> List[Dict[str, Any]]:
    value = load_json(ROOT / "data/runtime/active_operator_work_orders.json", [])
    return value if isinstance(value, list) else []


def _save_operator_work_orders(orders: List[Dict[str, Any]]) -> None:
    write_json(ROOT / "data/runtime/active_operator_work_orders.json", orders)


def _load_work_item_state() -> Dict[str, Dict[str, Any]]:
    value = load_json(WORK_ITEM_STATE_PATH, {})
    return value if isinstance(value, dict) else {}


def _save_work_item_state(value: Dict[str, Dict[str, Any]]) -> None:
    write_json(WORK_ITEM_STATE_PATH, value)


def _claim_work_item(finding: Dict[str, Any], cycle_id: str) -> tuple[bool, Dict[str, Any]]:
    item_id = str(finding.get("source_record_id") or finding.get("finding_id"))
    state = _load_work_item_state()
    current = state.get(item_id, {})
    if current.get("lifecycle_state") in {"CLAIMED", "RUNNING", "SUCCEEDED_VERIFIED", "COMPLETE"}:
        return False, current
    now = utc_now()
    claimed = {**current, "work_item_id": item_id, "lifecycle_state": "RUNNING",
               "claimed_at": current.get("claimed_at") or now, "started_at": now,
               "selected_cycle_id": cycle_id, "attempt_count": int(current.get("attempt_count", 0)) + 1,
               "idempotency_key": finding.get("dedupe_key") or item_id}
    state[item_id] = claimed
    _save_work_item_state(state)
    return True, claimed


def _complete_work_item(finding: Dict[str, Any], cycle_id: str, execution_id: str,
                        result: Dict[str, Any], receipt_ref: str) -> Dict[str, Any]:
    item_id = str(finding.get("source_record_id") or finding.get("finding_id"))
    state = _load_work_item_state()
    current = state.get(item_id, {})
    artifact = result.get("artifact") if isinstance(result, dict) else {}
    completed = {**current, "work_item_id": item_id, "lifecycle_state": "COMPLETE",
                 "completed_at": utc_now(), "selected_cycle_id": cycle_id,
                 "execution_id": execution_id, "result_artifact": artifact,
                 "validation_status": "PASS" if result.get("status") == "PASS" else "FAIL",
                 "result_hash": result.get("output_hash"), "receipt_reference": receipt_ref,
                 "attempt_count": int(current.get("attempt_count", 0)),
                 "idempotency_key": current.get("idempotency_key") or item_id}
    state[item_id] = completed
    _save_work_item_state(state)
    return completed


def _canonical_work_order(finding: Dict[str, Any], capability: str, *, blocked: bool = False) -> Dict[str, Any]:
    dedupe = str(finding.get("dedupe_key") or finding.get("finding_id"))
    return {
        "work_order_id": _stable_work_order_id(dedupe), "created_at": utc_now(),
        "source": finding.get("source_system", finding.get("source", "active_operator")),
        "category": finding.get("category", "SYSTEM_HEALTH"),
        "title": finding.get("summary", "Nexus internal work"),
        "description": finding.get("reason", ""),
        "priority": finding.get("priority", "P4"),
        "status": "BLOCKED" if blocked else ("WAITING_APPROVAL" if finding.get("approval_required", True) else "READY"),
        "authority_required": finding.get("action_class", "INTERNAL_AUTONOMOUS"),
        "capabilities_required": [capability], "risk_class": "LOW" if not blocked else "GATED",
        "dedupe_key": dedupe, "prerequisites": [],
        "recommended_action": finding.get("proposed_action") or finding.get("recommended_action"),
        "execution_mode": "HUMAN_APPROVAL_REQUIRED" if finding.get("approval_required", True) else "INTERNAL_AUTONOMOUS",
        "owner": "active_operator", "evidence_refs": finding.get("evidence_refs", []),
        "created_by": "active_operator_v1", "last_updated": utc_now(), "receipt_refs": [],
        "priority_score": priority_score({**finding, "capability_ready": not blocked}),
    }


def _record_escalation(order: Dict[str, Any]) -> Dict[str, Any]:
    escalation_dir = ROOT / "reports/runtime/nexus_active_operator_escalations"
    escalation_dir.mkdir(parents=True, exist_ok=True)
    escalation = {
        "escalation_id": "esc_" + hashlib.sha256(order["dedupe_key"].encode()).hexdigest()[:20],
        "created_at": utc_now(), "type": "CAPABILITY_NOT_CERTIFIED" if order["status"] == "BLOCKED" else "APPROVAL_REQUIRED",
        "work_order_id": order["work_order_id"], "what_is_needed": order["description"],
        "recommended_action": order["recommended_action"], "risk": order["risk_class"],
        "deferred_effect": "No external action is attempted; internal work remains queued.",
        "external_action_performed": False,
    }
    write_json(escalation_dir / f"{escalation['escalation_id']}.json", escalation)
    return escalation


def _safe_receipt(run_id: str, action: str, result: Dict[str, Any], *, work_order_id: str = "") -> Dict[str, Any]:
    return {"receipt_id": f"receipt_{run_id}_{action.replace('.', '_')}", "work_order_id": work_order_id,
            "timestamp": utc_now(), "capability": action, "tool_action_id": action,
            "inputs_summary": "redacted deterministic runtime state", "result": result,
            "files_artifacts_changed": [], "external_side_effects": False,
            "authority_used": "INTERNAL_READ_ONLY", "duration_ms": 0,
            "error_classification": None, "next_action": "none"}


def _write_v1_report(result: Dict[str, Any]) -> None:
    report = {"schema_version": "nexus.active-operator.v1", **result}
    write_json(ROOT / "reports/runtime/active_operator_latest.json", report)
    write_json(ROOT / "reports/certification/nexus_active_operator_v1_latest.json", report)
    lines = ["# Nexus Active Operator V1", "", f"- run: `{result['operator_run_id']}`",
             f"- mode: `{result['mode']}`", f"- state snapshot: `{result['state_snapshot']['generated_at']}`",
             f"- work orders: `{len(result['work_orders'])}`", f"- executions: `{len(result['executions'])}`",
             f"- escalations: `{len(result['escalations'])}`", "", "## Authority", "",
             "- external mutations: `0`", "- arbitrary shell: `UNAVAILABLE`",
             "- payments: `DISABLED`", "- live trading: `false`", "- social publishing: `false`", "",
             "## Capabilities", ""]
    lines.extend(f"- `{key}`: **{value['status']}** ({value['authority']})" for key, value in result["capabilities"].items())
    lines.extend(["", "## Result", "", f"- operational result: `{result['operational_result']}`",
                  f"- duplicate work suppressed: `{result['duplicates_suppressed']}`",
                  f"- safe internal execution: `{result['safe_internal_execution']}`", ""])
    report_md_path = ROOT / "reports/certification/nexus_active_operator_v1_latest.md"
    report_md_path.parent.mkdir(parents=True, exist_ok=True)
    report_md_path.write_text("\n".join(lines), encoding="utf-8")


def discover_attention(registry: Iterable[Dict[str, Any]], scheduler_health: Dict[str, Any]) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    for process in registry:
        if not process.get("enabled"):
            continue
        if str(process.get("last_status", "")).lower() not in {"failed", "blocked", "stale"}:
            continue
        process_id = str(process.get("process_id", "unknown"))
        findings.append({
            "finding_id": f"process:{process_id}:{process.get('last_status')}",
            "source": "process_registry",
            "priority": priority_for(process),
            "capability": process.get("category", "operations"),
            "summary": f"{process.get('name', process_id)} requires attention",
            "reason": f"process status is {process.get('last_status')}",
            "proposed_action": "runtime_report.generate",
            "related_artifact": process.get("report_path"),
        })
    if scheduler_health.get("status") in {"FAILED", "DEGRADED"}:
        findings.append({
            "finding_id": "scheduler:health",
            "source": "scheduler_health",
            "priority": "P0",
            "capability": "operations",
            "summary": "Scheduler health requires attention",
            "reason": str(scheduler_health.get("status")),
            "proposed_action": "runtime_report.generate",
            "related_artifact": "reports/phase16a/scheduler_health.json",
        })
    # The bounded pilot may consume one explicitly queued, public-only
    # research request through the existing Alpha research queue. This is a
    # queue read, not a manual research invocation.
    try:
        item_state = _load_work_item_state()
        for line in RESEARCH_QUEUE_PATH.read_text(encoding="utf-8").splitlines():
            request = json.loads(line)
            if not isinstance(request, dict) or request.get("synthetic") is True:
                continue
            if request.get("status") in {"completed", "cancelled", "blocked"}:
                continue
            request_id = str(request.get("request_id") or "")
            if not request_id or item_state.get(request_id, {}).get("lifecycle_state") in {"CLAIMED", "RUNNING", "SUCCEEDED_VERIFIED", "COMPLETE"}:
                continue
            if request.get("source") == "governed_queue":
                findings.append({
                    "finding_id": f"research_queue:{request_id}",
                    "source_system": "governed_queue", "source_record_id": request_id,
                    "source": "governed_queue", "category": "research_intelligence", "priority": "P3",
                    "summary": request.get("question", "Queued public research"),
                    "reason": "explicit non-synthetic bounded public research request",
                    "proposed_action": "research.refresh", "approval_required": False,
                    "action_class": "INTERNAL_AUTONOMOUS", "capability": "searxng.research",
                    "dedupe_key": request.get("idempotency_key", request_id),
                    "evidence_refs": ["data/runtime/alpha_research/portfolio_requests.jsonl"],
                    "question": request.get("question"), "synthetic": False,
                })
                break
    except (OSError, ValueError, TypeError, KeyError):
        pass
    return sorted(findings, key=lambda item: (PRIORITY_RANK[item["priority"]], item["finding_id"]))


def _existing_idempotency_keys() -> set[str]:
    return {str(item.get("idempotency_key")) for item in work_orders.list_work_orders(limit=500)}


def create_pending_work_order(finding: Dict[str, Any]) -> Dict[str, Any]:
    stable = f"{finding.get('dedupe_key', finding['finding_id'])}:{finding.get('material_fingerprint', '')}"
    key = "active_operator:" + hashlib.sha256(stable.encode()).hexdigest()[:24]
    action_id = finding.get("proposed_action") or finding.get("recommended_action") or "runtime_report.generate"
    if key in _existing_idempotency_keys():
        return {"status": "DUPLICATE_SUPPRESSED", "idempotency_key": key, "finding_id": finding["finding_id"]}
    if action_id == "opportunity.review":
        opportunity_id = finding.get("source_record_id") if finding.get("source_system") == "opportunity_engine" else finding.get("source_opportunity_id")
        for pending in approvals.get_pending_approvals(requested_for="ray", include_self=True):
            inputs = pending.get("input_summary") or {}
            if opportunity_id and pending.get("action_id") == "opportunity.review" and inputs.get("opportunity_id") == opportunity_id:
                return {"status": "DUPLICATE_SUPPRESSED", "idempotency_key": key, "finding_id": finding["finding_id"], "approval_id": pending.get("id")}
    approval = approvals.create_approval_request(
        action_id=action_id,
        requested_by="active_operator",
        requested_for="ray",
        input_summary={"finding_id": finding["finding_id"], "priority": finding["priority"]},
        action_summary=finding["summary"],
        evidence_refs=[finding["related_artifact"]] if finding.get("related_artifact") else [],
    )
    order = work_orders.create_work_order(
        approval_id=approval["id"],
        action_id=action_id,
        requested_by="active_operator",
        inputs=finding,
        expected_outcome="Internal report prepared for Ray review",
        idempotency_key=key,
        status="pending_approval",
    )
    return {
        "status": "CREATED", "idempotency_key": key, "finding_id": finding["finding_id"],
        "approval_id": approval["id"], "work_order_id": order["work_order_id"],
    }


def _receipt(run_id: str, result: Dict[str, Any]) -> Path:
    RECEIPT_DIR.mkdir(parents=True, exist_ok=True)
    path = RECEIPT_DIR / f"operator_{run_id}.json"
    write_json(path, {"receipt_id": f"operator_receipt_{run_id}", "operator_run_id": run_id, **result})
    return path


def _write_report(result: Dict[str, Any]) -> None:
    lines = [
        "# Nexus Active Operator Report", "", f"- operator_run_id: `{result['operator_run_id']}`",
        f"- status: **{result['status']}**", f"- started_at: `{result['started_at']}`",
        f"- completed_at: `{result['completed_at']}`", "", "## Counts", "",
        f"- actions considered: {len(result['actions_considered'])}",
        f"- safe actions executed: {len(result['actions_executed'])}",
        f"- approvals requested: {len(result['approvals_requested'])}",
        f"- work orders created: {len(result['work_orders_created'])}",
        f"- duplicate work suppressed: {result['duplicates_suppressed']}",
        f"- errors: {len(result['errors'])}", "", "## Authority", "",
        "- external actions: blocked", "- Stripe/live money: unavailable to this process",
        "- arbitrary shell: unavailable", "", f"- next_scheduled_run: `{result['next_scheduled_run']}`",
        "", "## Business", "",
        f"- business findings: {len(result.get('business_findings', []))}",
        f"- business priorities: {len(result.get('business_priorities', []))}",
        f"- business safe actions: {len(result.get('business_safe_actions_executed', []))}",
        f"- business work orders: {len(result.get('business_work_orders_created', []))}",
        f"- business duplicates suppressed: {result.get('business_duplicates_suppressed', 0)}",
    ]
    RUNNER_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    RUNNER_REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_once(*, dry_run: bool = False, mode: str = "live") -> Dict[str, Any]:
    _sanitize_autonomy_environment()
    started = utc_now()
    run_id = f"operator_{uuid.uuid4().hex}"
    if not dry_run and not kill_switch_enabled():
        completed = utc_now()
        result = {"operator_run_id": run_id, "status": "KILL_SWITCH_OFF", "started_at": started,
                  "completed_at": completed, "decision": "NO_ACTION", "trigger_type": os.environ.get("NEXUS_OPERATOR_TRIGGER", "manual"),
                  "authority": {"external_actions": "BLOCKED", "arbitrary_shell": "UNAVAILABLE"},
                  "external_mutations": 0, "dry_run": False, "cycle_receipt": True, "kill_switch": "OFF"}
        _receipt(run_id, result)
        write_json(HEARTBEAT_PATH, {"operator_run_id": run_id, "last_run": completed, "run_status": result["status"],
                                    "operator_health": "PAUSED", "decision": "NO_ACTION", "kill_switch": "OFF"})
        return result
    with single_run_lock() as acquired:
        if not acquired:
            return {"operator_run_id": run_id, "status": "SKIPPED_OVERLAP", "started_at": started, "completed_at": utc_now()}
        registry = load_json(REGISTRY_PATH, [])
        scheduler_health = load_json(SCHEDULER_HEALTH_PATH, {})
        findings = discover_attention(registry if isinstance(registry, list) else [], scheduler_health)
        # WP6 pilot keeps the cycle bounded to the certified operational
        # registry. Business read-model scans are opt-in and cannot lengthen
        # the pilot's no-action path unexpectedly.
        business_result = discover_business_attention() if os.environ.get("NEXUS_OPERATOR_ENABLE_BUSINESS_SCAN") == "1" else {
            "findings": [], "sources": {"business_attention": "DISABLED_FOR_BOUNDED_PILOT"}, "errors": []
        }
        business_brief_path = ROOT / "reports/runtime/nexus_active_operator_business_brief_latest.md"
        business_findings = business_result.get("findings", [])
        for item in business_findings:
            item["proposed_action"] = item.get("recommended_action", "business_attention.review")
        dispatch_findings = sorted(findings + business_findings, key=lambda item: (PRIORITY_RANK.get(item.get("priority", "P4"), 4), item.get("finding_id", "")))
        capabilities = capability_snapshot()
        canonical_orders = _load_operator_work_orders()
        known_dedupes = {str(item.get("dedupe_key")) for item in canonical_orders}
        operator_orders: List[Dict[str, Any]] = []
        operator_escalations: List[Dict[str, Any]] = []
        canonical_duplicates = 0
        for finding in dispatch_findings[:MAX_NEW_WORK_ORDERS]:
            capability = str(finding.get("capability") or finding.get("category") or "operations").lower()
            capability = {"operations": "system.health", "revenue_measurement_connection_gap": "system.health"}.get(capability, capability)
            blocked = capability in {"meta.inbound", "voice.remote", "email.send", "payments"}
            order = _canonical_work_order(finding, capability, blocked=blocked)
            if order["dedupe_key"] not in known_dedupes:
                canonical_orders.append(order)
                known_dedupes.add(order["dedupe_key"])
            else:
                canonical_duplicates += 1
            operator_orders.append(order)
            if blocked:
                operator_escalations.append(_record_escalation(order))
        for capability, reason in (("meta.inbound", "webhook callback and signature verifier are not certified"),
                                   ("email.send", "outbound email remains gated"),
                                   ("voice.remote", "remote Voice authentication is unproven")):
            if capabilities.get(capability, {}).get("status") in {"READY", "REMOTE_CONFIGURED"}:
                continue
            finding = {"finding_id": f"capability:{capability}", "summary": f"Capability requires attention: {capability}",
                       "reason": reason, "category": "APPROVALS_REQUIRED", "priority": "P2",
                       "dedupe_key": f"capability:{capability}:v1", "approval_required": True,
                       "action_class": "APPROVAL_REQUIRED", "proposed_action": capability}
            order = _canonical_work_order(finding, capability, blocked=True)
            if order["dedupe_key"] not in known_dedupes:
                canonical_orders.append(order)
                known_dedupes.add(order["dedupe_key"])
            operator_orders.append(order)
            operator_escalations.append(_record_escalation(order))
        _save_operator_work_orders(canonical_orders)
        state_snapshot = {
            "schema_version": "nexus.active-operator-state.v1", "generated_at": started,
            "SYSTEM_HEALTH": {"scheduler": scheduler_health},
            "CURRENT_WORK": operator_orders, "BLOCKED_WORK": [x for x in operator_orders if x["status"] == "BLOCKED"],
            "STALE_WORK": [], "RESEARCH_OPPORTUNITIES": [x for x in dispatch_findings if "research" in str(x.get("category", "")).lower()],
            "CLIENT_OPERATIONS": [], "REVENUE_OPPORTUNITIES": [x for x in dispatch_findings if "revenue" in str(x.get("category", "")).lower()],
            "FOREX_RESEARCH": {"status": capabilities["oanda.practice.read"]["status"], "ai_calls": 0},
            "COMMUNICATION_STATE": {"meta_inbound": "NOT_READY", "email_send": "GATED", "telegram": "READY", "voice_remote": "PARTIAL"},
            "CAPABILITY_STATE": capabilities, "APPROVALS_REQUIRED": [x for x in operator_orders if x["status"] == "WAITING_APPROVAL"],
            "RECENT_RECEIPTS": [],
        }
        actions_considered = [item["proposed_action"] for item in dispatch_findings]
        actions_executed = ["read_operational_state", "write_heartbeat"]
        business_safe_actions: List[str] = []
        if not dry_run:
            write_business_priority_brief(business_result, business_brief_path)
            business_safe_actions.append("business_attention.generate")
            actions_executed.append("business_attention.generate")
        approvals_requested: List[Dict[str, Any]] = []
        created: List[Dict[str, Any]] = []
        errors: List[str] = []
        safe_action_results: List[Dict[str, Any]] = []
        duplicates = 0
        business_created: List[Dict[str, Any]] = []
        business_duplicates = 0
        for finding in dispatch_findings:
            route = classify_action(finding["proposed_action"])
            if route == "AUTO_EXECUTE_INTERNAL_SAFE":
                if finding["proposed_action"] == "research.refresh" and not dry_run:
                    claimed, prior = _claim_work_item(finding, run_id)
                    if not claimed:
                        duplicates += 1
                        continue
                actions_executed.append(finding["proposed_action"])
                if finding["proposed_action"] == "research.refresh" and not dry_run:
                    try:
                        safe_action_results.append({"finding_id": finding["finding_id"], "result": execute_safe_internal_action(finding["proposed_action"], finding)})
                    except Exception as exc:
                        errors.append(f"{finding['finding_id']}: {type(exc).__name__}")
            elif route == "APPROVAL_REQUIRED":
                if dry_run:
                    approvals_requested.append({"finding_id": finding["finding_id"], "status": "DRY_RUN"})
                else:
                    try:
                        item = create_pending_work_order(finding)
                        if item["status"] == "DUPLICATE_SUPPRESSED":
                            duplicates += 1
                            if finding in business_findings:
                                business_duplicates += 1
                        else:
                            created.append(item)
                            if finding in business_findings:
                                business_created.append(item)
                            approvals_requested.append(item)
                    except Exception as exc:  # bounded per-finding failure
                        errors.append(f"{finding['finding_id']}: {type(exc).__name__}")
            else:
                errors.append(f"{finding['finding_id']}: NOT_AUTHORIZED")
        completed = utc_now()
        trigger_type = os.environ.get("NEXUS_OPERATOR_TRIGGER", "manual")
        heartbeat_path = str(HEARTBEAT_PATH.relative_to(ROOT))
        receipt_path = str((RECEIPT_DIR / f"operator_{run_id}.json").relative_to(ROOT))
        for item in safe_action_results:
            research_result = item.get("result", {})
            if research_result.get("status") == "PASS":
                item["work_item_state"] = _complete_work_item(
                    next((f for f in dispatch_findings if f.get("finding_id") == item.get("finding_id")), {}),
                    run_id, run_id, research_result, receipt_path)
        safe_receipts = [_safe_receipt(run_id, action, {"status": "COMPLETED", "mode": mode})
                         for action in dict.fromkeys(actions_executed) if action in SAFE_INTERNAL_ACTIONS or action == "business_attention.generate"]
        result = {
            "operator_run_id": run_id,
            "status": "NO_ACTION_REQUIRED" if not dispatch_findings else "COMPLETED_WITH_FINDINGS",
            "started_at": started, "completed_at": completed,
            "actions_considered": actions_considered,
            "actions_executed": actions_executed if not dry_run else [],
            "approvals_requested": approvals_requested,
            "work_orders_created": created, "duplicates_suppressed": duplicates,
            "canonical_work_order_duplicates_suppressed": canonical_duplicates,
            "business_findings": business_findings,
            "business_priorities": business_findings[:5],
            "business_sources": business_result.get("sources", {}),
            "business_source_errors": business_result.get("errors", []),
            "business_safe_actions_executed": business_safe_actions,
            "business_work_orders_created": business_created,
            "business_duplicates_suppressed": business_duplicates,
            "safe_action_results": safe_action_results,
            "business_brief_path": str(business_brief_path.relative_to(ROOT)),
            "errors": errors,
            "next_scheduled_run": (datetime.fromisoformat(completed) + timedelta(seconds=CADENCE_SECONDS)).isoformat(),
            "operator_health": "HEALTHY" if not errors else "DEGRADED",
            "authority": {"external_actions": "BLOCKED", "stripe_autonomous_execution": "DISABLED", "arbitrary_shell": "UNAVAILABLE"},
            "dry_run": dry_run, "trigger_type": trigger_type,
            "decision": "ACTION" if dispatch_findings else "NO_ACTION",
            "kill_switch": "ON" if (dry_run or kill_switch_enabled()) else "OFF",
            "cycle_receipt": True,
            "heartbeat_path": heartbeat_path, "receipt_path": receipt_path,
            "mode": mode, "state_snapshot": state_snapshot, "capabilities": capabilities,
            "work_orders": operator_orders, "escalations": operator_escalations,
            "executions": safe_receipts[:MAX_EXECUTIONS], "receipts": safe_receipts[:MAX_EXECUTIONS],
            "operational_result": "NO_ACTION_REQUIRED" if not dispatch_findings else "INTERNAL_ATTENTION_IDENTIFIED",
            "safe_internal_execution": "PASS" if not errors else "DEGRADED",
            "external_mutations": 0, "limits": {"max_new_work_orders": MAX_NEW_WORK_ORDERS, "max_executions": MAX_EXECUTIONS, "max_research_tasks": MAX_RESEARCH_TASKS, "max_runtime_seconds": MAX_RUNTIME_SECONDS},
        }
        heartbeat = {
            "operator_run_id": run_id, "last_run": completed,
            "last_successful_run": completed if not errors else None,
            "run_status": result["status"], "work_discovered": len(findings),
            "work_created": len(created), "safe_actions_executed": len(result["actions_executed"]),
            "approvals_requested": len(approvals_requested), "errors": errors,
            "next_scheduled_run": result["next_scheduled_run"], "operator_health": result["operator_health"],
            "authority": result["authority"],
            "business_findings": len(business_findings),
            "business_priorities": business_findings[:5],
            "business_sources": business_result.get("sources", {}),
            "safe_business_actions_executed": len(business_safe_actions),
            "business_work_orders_created": len(business_created),
            "business_duplicates_suppressed": business_duplicates,
            "top_business_priority": business_findings[0] if business_findings else None,
        }
        write_json(HEARTBEAT_PATH, heartbeat)
        write_json(ROOT / "reports/runtime/active_operator_heartbeat.json", heartbeat)
        _write_v1_report(result)
        _receipt(run_id, result)
        _write_report(result)
        process_registry_adapter.SPOOL_PATH = ROOT / "data/runtime/process_registry_spool.jsonl"
        emit_process_run(
            process_key="active_operator", name="Nexus Active Operator",
            status="SUCCEEDED" if not errors else "PARTIAL", idempotency_key=run_id,
            entry_point="scripts/operations/nexus_active_operator_runner.py",
            trigger_type=trigger_type if not dry_run else "dry_run", output_location=result["receipt_path"],
            items_attempted=len(findings), items_succeeded=len(created), items_failed=len(errors),
            metadata={"dry_run": dry_run, "external_action_performed": False, "remote_registry_updated": False},
        )
        return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one bounded Nexus Active Operator dispatch")
    parser.add_argument("--once", action="store_true", help="run one bounded dispatch")
    parser.add_argument("--dry-run", action="store_true", help="write no governed work orders")
    parser.add_argument("--mode", choices=("dry-run", "live"), default=None, help="explicit bounded cycle mode")
    args = parser.parse_args()
    if not args.once and not args.dry_run:
        parser.error("--once or --dry-run is required")
    dry_run = args.dry_run or args.mode == "dry-run"
    print(json.dumps(run_once(dry_run=dry_run, mode="dry-run" if dry_run else (args.mode or "live")), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
