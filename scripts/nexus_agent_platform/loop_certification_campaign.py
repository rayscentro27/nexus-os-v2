"""Sequential, human-gated real-world loop certification campaign.

This controller owns campaign state and gates only.  It does not turn registry
configuration or fixtures into certification, and it never auto-advances to a
second major loop.
"""
from __future__ import annotations

import hashlib
import json
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]
PROCESS_REGISTRY = ROOT / "data/operations/nexus_process_registry.json"
CAMPAIGN_PATH = ROOT / "data/runtime/nexus_loop_certification_campaign.json"
CERT_REGISTRY_PATH = ROOT / "reports/certification/nexus_loop_certification_registry_latest.json"
RECEIPTS_PATH = ROOT / "reports/runtime/nexus_loop_certification_receipts.jsonl"
SYSTEM_HEALTH_REPORT_PATH = ROOT / "reports/runtime/nexus_system_health_latest.json"
SYSTEM_HEALTH_RECEIPT_DIR = ROOT / "reports/runtime/nexus_active_operator_receipts"
SUPABASE_REPORT_PATH = ROOT / "reports/supabase/nexus_supabase_browser_verification_latest.md"
SUPABASE_RECEIPT_DIR = ROOT / "reports/runtime/nexus_active_operator_receipts"

WAITING_NEXT = "WAITING_NEXT_LOOP_APPROVAL"
ACTIVE = "ACTIVE_CERTIFICATION"
CAMPAIGN_SCHEMA = "nexus.loop-certification-campaign.v1"
# Parsing accepts an explicit identifier token first; persisted-state
# resolution below is the authority.  This prevents an unknown identifier
# from becoming an ordinary conversational message.
IDENTIFIER_RE = r"[A-Z0-9][A-Z0-9_-]{0,80}"

LOOP_CERTIFICATION_CONTRACTS: dict[str, dict[str, Any]] = {
    "telegram_operator": {
        "required_evidence_types": {"TELEGRAM_CAMPAIGN_CONTROL_RECEIVED", "AUTHORIZED_CHAT", "CAMPAIGN_RESOLVED", "CAMPAIGN_RESPONSE_DELIVERED", "CORRELATION_RECEIPT"},
        "applicable_stages": ["01_REAL_TRIGGER", "02_INTAKE", "03_CONTEXT_RESOLUTION", "04_AUTHORITY_CHECK", "09_REAL_EXECUTION", "14_RESULT_VERIFICATION", "16_RECEIPT", "17_TELEGRAM_VISIBILITY", "18_COMPLETION"],
        "not_applicable_stages": ["05_ACCESS_RESOLUTION", "06_CREDENTIAL_OR_SESSION_RESOLUTION", "07_SCHEDULING", "08_WORKER_OR_MODEL_SELECTION", "10_EXTERNAL_INTEGRATION", "11_RECOVERY", "12_HUMAN_ESCALATION", "13_RESUME", "15_EXTERNAL_EFFECT_VERIFICATION"],
        "completion_summary": "A real Telegram campaign-control request was authorized, resolved against canonical campaign state, delivered, and correlated with a Telegram receipt.",
    },
    "hermes_router": {
        "required_evidence_types": {"REAL_TELEGRAM_MESSAGE_RECEIVED", "AUTHORIZED_CHAT", "HERMES_ROUTER_SELECTED", "EXPLICIT_CONTROL_OBJECT_RESOLVED", "CANONICAL_STATE_RETURNED", "READ_ONLY_REQUEST_NO_MUTATION", "REAL_RESPONSE_DELIVERED", "CORRELATION_RECEIPT"},
        "applicable_stages": ["01_REAL_TRIGGER", "02_INTAKE", "03_CONTEXT_RESOLUTION", "04_AUTHORITY_CHECK", "14_RESULT_VERIFICATION", "16_RECEIPT", "17_TELEGRAM_VISIBILITY", "18_COMPLETION"],
        "not_applicable_stages": ["05_ACCESS_RESOLUTION", "06_CREDENTIAL_OR_SESSION_RESOLUTION", "07_SCHEDULING", "08_WORKER_OR_MODEL_SELECTION", "09_REAL_EXECUTION", "10_EXTERNAL_INTEGRATION", "11_RECOVERY", "12_HUMAN_ESCALATION", "13_RESUME", "15_EXTERNAL_EFFECT_VERIFICATION"],
        "completion_summary": "A real Telegram operational request was authorized, routed deterministically to its control object, resolved against canonical state, returned read-only, and delivered with correlation evidence.",
    },
    "system_health": {
        "required_evidence_types": {"REAL_TELEGRAM_MESSAGE_RECEIVED", "AUTHORIZED_CHAT", "SYSTEM_HEALTH_PROCESS_RESOLVED", "SYSTEM_HEALTH_RUN_STARTED", "SYSTEM_HEALTH_RUN_COMPLETED", "CANONICAL_HEALTH_REPORT_WRITTEN", "CANONICAL_HEALTH_RECEIPT_WRITTEN", "READ_ONLY_OR_INTERNAL_SAFE_EXECUTION", "REAL_RESPONSE_DELIVERED", "CORRELATION_RECEIPT"},
        "applicable_stages": ["01_REAL_TRIGGER", "02_INTAKE", "03_CONTEXT_RESOLUTION", "04_AUTHORITY_CHECK", "09_REAL_EXECUTION", "14_RESULT_VERIFICATION", "16_RECEIPT", "17_TELEGRAM_VISIBILITY", "18_COMPLETION"],
        "not_applicable_stages": ["05_ACCESS_RESOLUTION", "06_CREDENTIAL_OR_SESSION_RESOLUTION", "07_SCHEDULING", "08_WORKER_OR_MODEL_SELECTION", "10_EXTERNAL_INTEGRATION", "11_RECOVERY", "12_HUMAN_ESCALATION", "13_RESUME", "15_EXTERNAL_EFFECT_VERIFICATION"],
        "completion_summary": "A real authorized Telegram request triggered the canonical System Health Check, the registered internal runner completed, fresh canonical health report and receipt artifacts were produced and verified, and the result was delivered back through Telegram with correlation evidence.",
    },
    "supabase_verification": {
        "required_evidence_types": {"REAL_TELEGRAM_MESSAGE_RECEIVED", "AUTHORIZED_CHAT", "SUPABASE_PROCESS_RESOLVED", "SUPABASE_RUN_STARTED", "SERVER_GOVERNED_READ_VERIFIED", "BROWSER_SAFE_CONFIG_VERIFIED", "NO_SERVICE_ROLE_FRONTEND_EXPOSURE", "BROWSER_SUPABASE_READ_VERIFIED", "AUTHENTICATED_SESSION_VERIFIED", "RLS_TENANT_ISOLATION_VERIFIED", "SUPABASE_RUN_COMPLETED", "CANONICAL_SUPABASE_REPORT_WRITTEN", "CANONICAL_SUPABASE_RECEIPT_WRITTEN", "READ_ONLY_NO_DATABASE_MUTATION", "REAL_RESPONSE_DELIVERED", "CORRELATION_RECEIPT"},
        "applicable_stages": ["01_REAL_TRIGGER", "02_INTAKE", "03_CONTEXT_RESOLUTION", "04_AUTHORITY_CHECK", "05_ACCESS_RESOLUTION", "06_CREDENTIAL_OR_SESSION_RESOLUTION", "09_REAL_EXECUTION", "10_EXTERNAL_INTEGRATION", "14_RESULT_VERIFICATION", "15_EXTERNAL_EFFECT_VERIFICATION", "16_RECEIPT", "17_TELEGRAM_VISIBILITY", "18_COMPLETION"],
        "not_applicable_stages": ["07_SCHEDULING", "08_WORKER_OR_MODEL_SELECTION", "11_RECOVERY", "12_HUMAN_ESCALATION", "13_RESUME"],
        "completion_summary": "A real authorized Telegram request ran the bounded Supabase verification, proved governed server connectivity and safe browser configuration without exposing a service-role secret, verified the authenticated browser read and tenant isolation, performed no writes, and returned a correlated receipt.",
    },
}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return default


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")
        temporary = Path(handle.name)
    temporary.replace(path)


def _receipt(event: str, campaign_id: str, **details: Any) -> None:
    RECEIPTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with RECEIPTS_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"campaign_id": campaign_id, "event": event, "created_at": now(), **details}, sort_keys=True) + "\n")


def inventory_registered_loops() -> list[dict[str, Any]]:
    rows = _read(PROCESS_REGISTRY, [])
    if not isinstance(rows, list):
        rows = rows.get("processes", []) if isinstance(rows, dict) else []
    result = []
    for row in rows:
        if not isinstance(row, dict) or not row.get("process_id"):
            continue
        last = str(row.get("last_status") or "").lower()
        state = "BLOCKED" if last == "blocked" or row.get("enabled") is False else "NOT_TESTED"
        result.append({
            "loop_id": row["process_id"], "loop_name": row.get("name", row["process_id"]),
            "purpose": row.get("next_action") or row.get("category", "registered Nexus process"),
            "owner": row.get("owner", "Nexus"), "configured": True,
            "enabled": bool(row.get("enabled")), "scheduled": row.get("schedule_type") not in {None, "manual", "on_demand"},
            "runtime_state": row.get("last_status", "UNKNOWN"), "dependencies": row.get("dependencies", []),
            "external_systems": row.get("external_systems", []), "mutation_capability": row.get("blocked_actions", []),
            "human_gate_required": bool(row.get("approval_required")), "recovery_capable": bool(row.get("recovery_capable", False)),
            "engineering_dependent": bool(row.get("engineering_dependent", False)), "last_real_execution": row.get("last_run_at"),
            "current_certification": state,
        })
    return result


def _ordered(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    # Control and shared health are first; this is an order over the registry,
    # not permission to execute any loop.
    rank = {"telegram_operator": 0, "hermes_router": 1, "system_health": 2, "supabase_verification": 3, "research_intelligence": 4, "repo_intelligence": 5}
    return sorted(rows, key=lambda row: (rank.get(row["loop_id"], 10), row["loop_id"]))


def load_campaign() -> dict[str, Any]:
    value = _read(CAMPAIGN_PATH, {})
    return value if isinstance(value, dict) else {}


def start_campaign() -> dict[str, Any]:
    existing = load_campaign()
    if existing.get("campaign_id") and existing.get("state") not in {"STOPPED", "COMPLETED"}:
        return existing
    loops = _ordered(inventory_registered_loops())
    campaign_id = "LOOP-CERT-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    current = loops[0] if loops else {}
    campaign = {
        "schema_version": CAMPAIGN_SCHEMA, "campaign_id": campaign_id, "state": ACTIVE,
        "current_loop": current.get("loop_id"), "current_stage": "01_REAL_TRIGGER",
        "completed_loops": [], "certified_loops": [], "blocked_loops": [], "skipped_loops": [],
        "human_waiting_loops": [], "last_action": "campaign_created", "next_action": "perform the real trigger for the current loop", "current_loop_blocker": "NONE",
        "next_retry": None, "loop_order": [row["loop_id"] for row in loops], "inventory": loops,
        "outstanding_repairs": [{"repair_id": "VOICE-001", "work_order_id": "wo_b5a3b90892804ec79164159997caf264", "state": "WAITING_WORKER", "reason": "NO_CERTIFIED_AI_ENGINEERING_WORKER"}],
        "safety": {"active_operator_paused": True, "live_trading": False, "payment_authority": False, "auto_social_publishing": False},
        "created_at": now(), "updated_at": now(),
    }
    _write(CAMPAIGN_PATH, campaign)
    _write(CERT_REGISTRY_PATH, {"schema_version": "nexus.loop-certification-registry.v1", "campaign_id": campaign_id, "updated_at": now(), "loops": [{**row, "campaign_id": campaign_id, "real_trigger_tested": False, "context_tested": False, "authority_tested": False, "access_tested": False, "worker_or_model_tested": False, "execution_tested": False, "recovery_tested": False, "human_escalation_tested": False, "resume_tested": False, "external_effect_tested": False, "receipt_verified": False, "telegram_visibility_tested": False, "certification_state": row["current_certification"], "certified_at": None} for row in loops]})
    _receipt("CAMPAIGN_CREATED", campaign_id, current_loop=current.get("loop_id"), loop_count=len(loops))
    return campaign


def status_text() -> str:
    campaign = load_campaign()
    if not campaign.get("campaign_id"):
        return "No loop certification campaign is active."
    inventory = campaign.get("inventory", [])
    certified = len(campaign.get("certified_loops", []))
    blocker = campaign.get("current_loop_blocker") or "NONE"
    repair = campaign.get("outstanding_repairs") or []
    repair_line = "\n".join(f"Outstanding unrelated repair: {item.get('repair_id')} — {item.get('state')}" for item in repair)
    return (f"Campaign: {campaign['campaign_id']}\nCertified: {certified} / {len(inventory)}\n"
            f"Current loop: {campaign.get('current_loop', 'NONE')}\nState: {campaign.get('state', 'UNKNOWN')}\n"
            f"Current stage: {campaign.get('current_stage', 'UNKNOWN')}\n"
            f"What Nexus is doing: {campaign.get('next_action', 'UNKNOWN')}\n"
            f"Current blocker: {blocker}\n"
            f"Do you need me? {'YES' if campaign.get('human_waiting_loops') else 'NO'}\n"
            f"{repair_line}\nNext loop: not started. Advancement requires Ray approval.").replace("\n\nNext loop", "\nNext loop")


def certification_contract(loop_id: str | None) -> dict[str, Any]:
    return LOOP_CERTIFICATION_CONTRACTS.get(str(loop_id), {"required_evidence_types": set(), "applicable_stages": [], "not_applicable_stages": []})


def parse_campaign_command(text: str) -> dict[str, str] | None:
    """Parse explicit campaign controls, including their required IDs."""
    value = re.sub(r"\s+", " ", str(text).strip()).upper()
    patterns = (
        (rf"^STATUS CAMPAIGN ({IDENTIFIER_RE})$", "STATUS", "CAMPAIGN"),
        (rf"^STATUS LOOP ({IDENTIFIER_RE})$", "STATUS", "LOOP"),
        (rf"^RETRY LOOP ({IDENTIFIER_RE})$", "RETRY", "LOOP"),
        (rf"^HOLD CAMPAIGN ({IDENTIFIER_RE})$", "HOLD", "CAMPAIGN"),
        (rf"^RESUME CAMPAIGN ({IDENTIFIER_RE})$", "RESUME", "CAMPAIGN"),
        (rf"^NEXT LOOP ({IDENTIFIER_RE})$", "NEXT", "CAMPAIGN"),
        (rf"^SKIP LOOP ({IDENTIFIER_RE}) ({IDENTIFIER_RE})$", "SKIP", "LOOP"),
        (rf"^CANCEL CAMPAIGN ({IDENTIFIER_RE})$", "CANCEL", "CAMPAIGN"),
    )
    for pattern, action, object_type in patterns:
        match = re.fullmatch(pattern, value)
        if match:
            result = {"action": action, "object_type": object_type, "campaign_id": match.group(1) if object_type == "CAMPAIGN" else load_campaign().get("campaign_id", "")}
            if object_type == "LOOP":
                result["loop_id"] = match.group(1)
                if action == "SKIP":
                    result["campaign_id"] = match.group(2)
            return result
    return None


def campaign_control_intent(text: str) -> bool:
    normalized = _normalize_natural(text)
    return parse_campaign_command(text) is not None or normalized in {"what are you working on", "what happened", "what do you need from me", "is it running", "campaign status", "status campaign", "what is the campaign status", "how is the certification going", "do you need me", "what loop are you testing", "continue", "retry", "hold", "hold this loop", "skip this loop", "leave this blocked for now", "stop campaign", "move to the next loop"}


def _normalize_natural(text: str) -> str:
    value = str(text).strip().lower().replace("’", "'")
    value = value.replace("what's", "what is").replace("what're", "what are")
    return re.sub(r"[^a-z0-9_-]+", " ", value).strip()


def _record_telegram_evidence(campaign: dict[str, Any], *, update_id: int | None, chat_id: int | None) -> dict[str, Any]:
    evidence = campaign.setdefault("current_loop_evidence", {})
    evidence.update({"loop_id": campaign.get("current_loop"), "incoming_update_id": update_id, "chat_id_hash": hashlib.sha256(str(chat_id).encode()).hexdigest()[:16] if chat_id is not None else None, "route": "LOOP_CERTIFICATION_CONTROL", "action": "STATUS", "real_trigger_tested": True, "intake_tested": True, "context_tested": True, "authority_tested": True, "execution_tested": True, "receipt_verified": False, "telegram_visibility_tested": False, "updated_at": now()})
    return evidence


def _hermes_router_evidence(metadata: Mapping[str, Any], response_text: str, *, update_id: int, delivered: bool, outgoing_message_id: int | None) -> set[str]:
    state = str(metadata.get("state") or "")
    evidence = {"REAL_TELEGRAM_MESSAGE_RECEIVED", "AUTHORIZED_CHAT", "REAL_RESPONSE_DELIVERED" if delivered else ""}
    if metadata.get("route") == "GOVERNED_REPAIR_CONTROL":
        evidence.add("HERMES_ROUTER_SELECTED")
    control = metadata.get("control_object") or {}
    if control.get("object_type") == "REPAIR" and control.get("object_id") == metadata.get("repair_id"):
        evidence.add("EXPLICIT_CONTROL_OBJECT_RESOLVED")
    if metadata.get("repair_id") == "VOICE-001" and metadata.get("work_order_id") == "wo_b5a3b90892804ec79164159997caf264" and state == "WAITING_WORKER" and metadata.get("read_only") is True and metadata.get("repair_executed") is False and "No repair was executed" in response_text:
        evidence.update({"CANONICAL_STATE_RETURNED", "READ_ONLY_REQUEST_NO_MUTATION"})
    if outgoing_message_id is not None and delivered:
        evidence.add("CORRELATION_RECEIPT")
    return {item for item in evidence if item}


def _system_health_evidence(metadata: Mapping[str, Any], *, incoming_update_id: int, correlation_id: str, delivered: bool, outgoing_message_id: int | None) -> set[str]:
    evidence = {"REAL_TELEGRAM_MESSAGE_RECEIVED", "AUTHORIZED_CHAT"}
    if metadata.get("process_id") == "system_health":
        evidence.add("SYSTEM_HEALTH_PROCESS_RESOLVED")
    report = _read(SYSTEM_HEALTH_REPORT_PATH, {})
    receipt_path = Path(str(metadata.get("canonical_receipt_path") or ""))
    receipt = _read(receipt_path, {}) if receipt_path.is_absolute() else {}
    run_id = metadata.get("system_health_run_id")
    if run_id and metadata.get("system_health_run_started") and report.get("run_id") == run_id and report.get("incoming_update_id") == incoming_update_id and report.get("correlation_id") == correlation_id:
        evidence.add("SYSTEM_HEALTH_RUN_STARTED")
        if report.get("execution_status") == "COMPLETED":
            evidence.add("SYSTEM_HEALTH_RUN_COMPLETED")
    if report.get("run_id") == run_id and metadata.get("canonical_report_written") is True:
        evidence.add("CANONICAL_HEALTH_REPORT_WRITTEN")
    if receipt.get("run_id") == run_id and receipt.get("incoming_update_id") == incoming_update_id and receipt.get("correlation_id") == correlation_id and metadata.get("canonical_receipt_written") is True:
        evidence.add("CANONICAL_HEALTH_RECEIPT_WRITTEN")
    if metadata.get("read_only") is True and metadata.get("external_side_effects") is False and report.get("execution_status") == "COMPLETED":
        evidence.add("READ_ONLY_OR_INTERNAL_SAFE_EXECUTION")
    if delivered and outgoing_message_id is not None:
        evidence.update({"REAL_RESPONSE_DELIVERED", "CORRELATION_RECEIPT"})
    return evidence


def _supabase_evidence(metadata: Mapping[str, Any], *, delivered: bool, outgoing_message_id: int | None) -> set[str]:
    evidence = {"REAL_TELEGRAM_MESSAGE_RECEIVED", "AUTHORIZED_CHAT"}
    if metadata.get("process_id") == "supabase_verification": evidence.add("SUPABASE_PROCESS_RESOLVED")
    if metadata.get("supabase_run_started") is True: evidence.add("SUPABASE_RUN_STARTED")
    for key, evidence_type in (("server_read_verified", "SERVER_GOVERNED_READ_VERIFIED"), ("browser_safe_config_verified", "BROWSER_SAFE_CONFIG_VERIFIED"), ("no_service_role_frontend_exposure", "NO_SERVICE_ROLE_FRONTEND_EXPOSURE"), ("browser_read_verified", "BROWSER_SUPABASE_READ_VERIFIED"), ("authenticated_session_verified", "AUTHENTICATED_SESSION_VERIFIED"), ("rls_isolation_verified", "RLS_TENANT_ISOLATION_VERIFIED"), ("supabase_run_completed", "SUPABASE_RUN_COMPLETED"), ("canonical_report_written", "CANONICAL_SUPABASE_REPORT_WRITTEN"), ("canonical_receipt_written", "CANONICAL_SUPABASE_RECEIPT_WRITTEN"), ("read_only", "READ_ONLY_NO_DATABASE_MUTATION")):
        if metadata.get(key) is True: evidence.add(evidence_type)
    if delivered and outgoing_message_id is not None:
        evidence.update({"REAL_RESPONSE_DELIVERED", "CORRELATION_RECEIPT"})
    return evidence


def _update_registry_for_loop(campaign: dict[str, Any], evidence: Mapping[str, Any], stage_results: Mapping[str, str]) -> None:
    registry = _read(CERT_REGISTRY_PATH, {})
    if not isinstance(registry, dict):
        return
    loop_id = campaign.get("current_loop")
    for row in registry.get("loops", []):
        if row.get("campaign_id") == campaign.get("campaign_id") and row.get("loop_id") == loop_id:
            row.update({"evidence_refs": evidence.get("evidence_refs", []), "incoming_update_id": evidence.get("incoming_update_id"), "outgoing_message_id": evidence.get("outgoing_message_id"), "route": evidence.get("route"), "control_object": evidence.get("control_object"), "applicable_stages": certification_contract(loop_id).get("applicable_stages", []), "stage_results": dict(stage_results)})
            if loop_id in campaign.get("certified_loops", []):
                row.update({"certification_state": "REAL_WORLD_CERTIFIED", "real_world_certified": True, "certified_at": campaign.get("certified_at")})
    registry["updated_at"] = now()
    _write(CERT_REGISTRY_PATH, registry)


def observe_runtime_event(*, campaign_id: str, current_loop: str | None, incoming_update_id: int, route: str, outcome: str | None, metadata: Mapping[str, Any], response_text: str, outgoing_message_id: int | None, delivered: bool) -> dict[str, Any]:
    """Observe a real runtime event and certify only the active loop contract."""
    if metadata.get("test_event"):
        return {"status": "IGNORED_TEST_EVENT"}
    campaign = load_campaign()
    if campaign.get("campaign_id") != campaign_id or campaign.get("current_loop") != current_loop:
        return {"status": "IGNORED_WRONG_CAMPAIGN_OR_LOOP"}
    contract = certification_contract(current_loop)
    timestamp = now()
    correlation_id = f"{campaign_id}:{incoming_update_id}"
    event_metadata = {**metadata, "route": route}
    control_object = event_metadata.get("control_object")
    if current_loop == "hermes_router":
        observed = _hermes_router_evidence(event_metadata, response_text, update_id=incoming_update_id, delivered=delivered, outgoing_message_id=outgoing_message_id)
    elif current_loop == "system_health":
        observed = _system_health_evidence(event_metadata, incoming_update_id=incoming_update_id, correlation_id=correlation_id, delivered=delivered, outgoing_message_id=outgoing_message_id)
    elif current_loop == "supabase_verification":
        observed = _supabase_evidence(event_metadata, delivered=delivered, outgoing_message_id=outgoing_message_id)
    else:
        # Campaign status is observable but does not newly certify a loop.
        observed = {"TELEGRAM_CAMPAIGN_CONTROL_RECEIVED", "AUTHORIZED_CHAT", "CAMPAIGN_RESOLVED", "CAMPAIGN_RESPONSE_DELIVERED", "CORRELATION_RECEIPT"} if metadata.get("campaign_control_action") == "STATUS" and delivered and outgoing_message_id is not None else set()
    evidence = campaign.setdefault("loop_evidence", {})
    prior_types = set(evidence.get("evidence_types", [])) if evidence.get("contract_loop") == current_loop else set()
    combined_types = prior_types | observed
    evidence.update({"contract_loop": current_loop, "loop_id": current_loop, "incoming_update_id": incoming_update_id if observed else evidence.get("incoming_update_id"), "outgoing_message_id": outgoing_message_id if observed else evidence.get("outgoing_message_id"), "route": route if observed else evidence.get("route", route), "outcome": outcome if observed else evidence.get("outcome", outcome), "control_object": control_object if observed else evidence.get("control_object"), "evidence_types": sorted(combined_types), "evidence_refs": sorted(set(evidence.get("evidence_refs", [])) | {f"telegram:update:{incoming_update_id}", f"telegram:outgoing:{outgoing_message_id}" if outgoing_message_id is not None else "telegram:outgoing:UNAVAILABLE"}), "correlation_id": correlation_id if observed else evidence.get("correlation_id", correlation_id), "delivered": bool(delivered) if observed else evidence.get("delivered", False), "timestamp": timestamp})
    stage_results = {stage: "NOT_APPLICABLE" for stage in contract.get("not_applicable_stages", [])}
    stage_map = {"01_REAL_TRIGGER": "REAL_TELEGRAM_MESSAGE_RECEIVED", "02_INTAKE": "REAL_TELEGRAM_MESSAGE_RECEIVED", "03_CONTEXT_RESOLUTION": "SUPABASE_PROCESS_RESOLVED" if current_loop == "supabase_verification" else "EXPLICIT_CONTROL_OBJECT_RESOLVED", "04_AUTHORITY_CHECK": "AUTHORIZED_CHAT", "05_ACCESS_RESOLUTION": "SERVER_GOVERNED_READ_VERIFIED", "06_CREDENTIAL_OR_SESSION_RESOLUTION": "AUTHENTICATED_SESSION_VERIFIED", "10_EXTERNAL_INTEGRATION": "SERVER_GOVERNED_READ_VERIFIED", "14_RESULT_VERIFICATION": "CANONICAL_SUPABASE_REPORT_WRITTEN" if current_loop == "supabase_verification" else "CANONICAL_STATE_RETURNED", "15_EXTERNAL_EFFECT_VERIFICATION": "READ_ONLY_NO_DATABASE_MUTATION", "16_RECEIPT": "CORRELATION_RECEIPT", "17_TELEGRAM_VISIBILITY": "REAL_RESPONSE_DELIVERED", "18_COMPLETION": "REAL_RESPONSE_DELIVERED"}
    for stage, required in stage_map.items():
        if stage in contract.get("applicable_stages", []):
            stage_results[stage] = "PASS" if required in combined_types else "FAIL"
    if "09_REAL_EXECUTION" in contract.get("applicable_stages", []):
        required = "SYSTEM_HEALTH_RUN_COMPLETED" if current_loop == "system_health" else "SUPABASE_RUN_COMPLETED" if current_loop == "supabase_verification" else "CAMPAIGN_RESPONSE_DELIVERED"
        stage_results["09_REAL_EXECUTION"] = "PASS" if required in combined_types else "FAIL"
    campaign["current_loop_evidence"] = evidence
    campaign.setdefault("campaign_messages", []).append({"campaign_id": campaign_id, "loop_id": current_loop, "incoming_update_id": incoming_update_id, "outgoing_message_id": outgoing_message_id, "correlation_id": correlation_id, "route": route, "action": metadata.get("campaign_control_action") or "RUNTIME_EVENT", "delivered": bool(delivered), "timestamp": timestamp})
    campaign["current_loop_stages"] = stage_results
    campaign["last_action"] = "runtime_event_observed"
    complete = bool(contract.get("required_evidence_types") and contract["required_evidence_types"].issubset(combined_types))
    newly_certified = complete and campaign.get("state") in {ACTIVE, "ACTIVE"} and current_loop not in campaign.get("certified_loops", [])
    if newly_certified:
        campaign["certified_loops"] = sorted(set(campaign.get("certified_loops", [])) | {current_loop})
        campaign["completed_loops"] = sorted(set(campaign.get("completed_loops", [])) | {current_loop})
        campaign["state"] = WAITING_NEXT
        campaign["current_stage"] = "18_COMPLETION"
        campaign["current_loop_blocker"] = "NONE"
        campaign["next_action"] = "Ray must approve advancement with Move to the next loop"
        campaign["certification_state"] = "REAL_WORLD_CERTIFIED"
        campaign["real_world_certified"] = True
        campaign["certified_at"] = timestamp
    if current_loop not in campaign.get("certified_loops", []):
        campaign["current_loop_certification_state"] = "NOT_CERTIFIED"
    campaign["updated_at"] = timestamp
    _write(CAMPAIGN_PATH, campaign)
    _update_registry_for_loop(campaign, evidence, stage_results)
    _receipt("RUNTIME_EVENT_OBSERVED", campaign_id, loop_id=current_loop, incoming_update_id=incoming_update_id, outgoing_message_id=outgoing_message_id, route=route, evidence_types=sorted(observed), certified=newly_certified)
    return {**campaign, "observed_evidence": sorted(observed), "newly_certified": newly_certified, "correlation_id": correlation_id}


def record_delivery(*, campaign_id: str, update_id: int, outgoing_message_id: int | None, delivered: bool) -> dict[str, Any]:
    campaign = load_campaign()
    if campaign.get("campaign_id") != campaign_id:
        return {"status": "UNKNOWN_CAMPAIGN"}
    return observe_runtime_event(campaign_id=campaign_id, current_loop=campaign.get("current_loop"), incoming_update_id=update_id, route="LOOP_CERTIFICATION_CONTROL", outcome="ANSWERED", metadata={"campaign_control_action": "STATUS"}, response_text="", outgoing_message_id=outgoing_message_id, delivered=delivered)


def record_campaign_message(*, campaign_id: str, loop_id: str | None, incoming_update_id: int, outgoing_message_id: int | None, correlation_id: str, action: str, delivered: bool) -> None:
    """Persist a campaign-linked Telegram message without changing campaign state."""
    campaign = load_campaign()
    if campaign.get("campaign_id") != campaign_id:
        return
    campaign.setdefault("campaign_messages", []).append({"campaign_id": campaign_id, "loop_id": loop_id, "incoming_update_id": incoming_update_id, "outgoing_message_id": outgoing_message_id, "correlation_id": correlation_id, "route": "LOOP_CERTIFICATION_CONTROL", "action": action, "delivered": bool(delivered), "timestamp": now()})
    campaign["updated_at"] = now()
    _write(CAMPAIGN_PATH, campaign)


def notification_already_sent(*, campaign_id: str, notification_type: str, requested_action: str, state_key: str) -> bool:
    campaign = load_campaign()
    return any(item.get("campaign_id") == campaign_id and item.get("notification_type") == notification_type and item.get("requested_action") == requested_action and item.get("state_key") == state_key and item.get("delivered") for item in campaign.get("campaign_notifications", []))


def record_notification(*, campaign_id: str, notification_type: str, requested_action: str, state_key: str, delivered: bool) -> None:
    campaign = load_campaign()
    if campaign.get("campaign_id") != campaign_id:
        return
    campaign.setdefault("campaign_notifications", []).append({"campaign_id": campaign_id, "notification_type": notification_type, "requested_action": requested_action, "state_key": state_key, "delivered": bool(delivered), "timestamp": now()})
    campaign["updated_at"] = now()
    _write(CAMPAIGN_PATH, campaign)


def completion_text(campaign: Mapping[str, Any]) -> str:
    loop_id = str(campaign.get("current_loop") or "UNKNOWN")
    loop = next((row for row in campaign.get("inventory", []) if row.get("loop_id") == loop_id), {})
    loop_name = loop.get("loop_name", loop_id)
    order = campaign.get("loop_order", [])
    next_loop_id = order[order.index(loop_id) + 1] if loop_id in order and order.index(loop_id) + 1 < len(order) else "None"
    next_loop = next((row.get("loop_name", next_loop_id) for row in campaign.get("inventory", []) if row.get("loop_id") == next_loop_id), next_loop_id)
    evidence = campaign.get("loop_evidence", {}).get("evidence_types", [])
    summary = certification_contract(loop_id).get("completion_summary") or f"Evidence types: {', '.join(evidence)}."
    return (f"Loop certification complete.\n\nLoop:\n{loop_name}\n\nResult:\nREAL-WORLD CERTIFIED\n\n"
            f"What was proven:\n{summary}\n\n"
            f"Next loop:\n{next_loop}\n\nNothing has started on the next loop.\n\nReply:\nMove to the next loop\n\nor:\nHold")


def handle_control(text: str, *, update_id: int | None = None, chat_id: int | None = None) -> tuple[str, dict[str, Any]] | None:
    campaign = load_campaign()
    if not campaign.get("campaign_id"):
        return None
    normalized = _normalize_natural(text)
    parsed = parse_campaign_command(text)
    if parsed:
        if parsed.get("campaign_id") and parsed["campaign_id"] != campaign.get("campaign_id"):
            return (f"I could not find campaign {parsed['campaign_id']}. No campaign state was changed.", {"route": "LOOP_CERTIFICATION_CONTROL", "outcome": "UNKNOWN_CAMPAIGN", "campaign_id": parsed["campaign_id"]})
        if parsed["action"] == "STATUS":
            if parsed["object_type"] == "LOOP" and parsed.get("loop_id") != campaign.get("current_loop"):
                return (f"Loop {parsed['loop_id']} is not the current campaign loop. No state was changed.", {"route": "LOOP_CERTIFICATION_CONTROL", "outcome": "LOOP_NOT_CURRENT"})
            evidence = _record_telegram_evidence(campaign, update_id=update_id, chat_id=chat_id)
            return status_text(), {"route": "LOOP_CERTIFICATION_CONTROL", "outcome": "ANSWERED", "campaign_id": campaign["campaign_id"], "campaign_control_action": "STATUS", "campaign_incoming_update_id": update_id, "campaign_evidence": evidence}
        if parsed["action"] == "NEXT":
            normalized = "move to the next loop"
        elif parsed["action"] == "HOLD":
            normalized = "hold this loop"
        elif parsed["action"] == "CANCEL":
            normalized = "stop campaign"
        elif parsed["action"] == "SKIP":
            return ("The current loop must be completed or explicitly held before it can be skipped.", {"route": "LOOP_CERTIFICATION_GATE", "outcome": "NOT_READY"})
        else:
            return (status_text(), {"route": "LOOP_CERTIFICATION_CONTROL", "outcome": "NO_AUTO_EXECUTION", "campaign_id": campaign["campaign_id"]})
    if normalized in {"what are you working on", "what happened", "what do you need from me", "is it running", "campaign status", "status campaign", "what is the campaign status", "how is the certification going", "do you need me", "what loop are you testing"}:
        evidence = _record_telegram_evidence(campaign, update_id=update_id, chat_id=chat_id)
        return status_text(), {"route": "LOOP_CERTIFICATION_STATUS", "campaign_id": campaign["campaign_id"], "campaign_control_action": "STATUS", "campaign_incoming_update_id": update_id, "campaign_evidence": evidence}
    if normalized in {"hold", "hold this loop", "skip this loop", "leave this blocked for now", "stop campaign"}:
        action = "stop_requested" if normalized == "stop campaign" else "hold_requested"
        campaign["state"] = "STOPPED" if action == "stop_requested" else WAITING_NEXT
        campaign["last_action"] = action; campaign["next_action"] = "Ray must explicitly choose whether to resume or move to the next loop"
        campaign["updated_at"] = now(); _write(CAMPAIGN_PATH, campaign); _receipt(action.upper(), campaign["campaign_id"], current_loop=campaign.get("current_loop"))
        return ("Campaign is paused. No loop was started or advanced.", {"route": "LOOP_CERTIFICATION_GATE", "campaign_id": campaign["campaign_id"], "state": campaign["state"]})
    if normalized == "move to the next loop":
        if campaign.get("state") != WAITING_NEXT:
            return ("The current loop is not complete, so I cannot advance yet.", {"route": "LOOP_CERTIFICATION_GATE", "outcome": "NOT_READY"})
        order = campaign.get("loop_order", []); current = campaign.get("current_loop");
        if current in order and order.index(current) + 1 < len(order):
            campaign["current_loop"] = order[order.index(current) + 1]; campaign["current_stage"] = "01_REAL_TRIGGER"; campaign["state"] = ACTIVE; campaign["last_action"] = "ray_approved_next_loop"; campaign["next_action"] = "perform the real trigger for the current loop"; campaign["updated_at"] = now(); _write(CAMPAIGN_PATH, campaign); _receipt("NEXT_LOOP_APPROVED", campaign["campaign_id"], current_loop=campaign["current_loop"])
            return (f"Approved. The next loop is {campaign['current_loop']}. Nothing else has started.", {"route": "LOOP_CERTIFICATION_GATE", "outcome": "ADVANCED"})
        return ("There is no remaining registered loop to advance to.", {"route": "LOOP_CERTIFICATION_GATE", "outcome": "COMPLETE"})
    if normalized in {"continue", "retry"}:
        return status_text(), {"route": "LOOP_CERTIFICATION_STATUS", "outcome": "NO_AUTO_EXECUTION"}
    return None


def campaign_digest() -> str:
    return hashlib.sha256(json.dumps(load_campaign(), sort_keys=True).encode()).hexdigest()[:16]
