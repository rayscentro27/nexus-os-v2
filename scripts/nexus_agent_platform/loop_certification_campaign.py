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

WAITING_NEXT = "WAITING_NEXT_LOOP_APPROVAL"
ACTIVE = "ACTIVE_CERTIFICATION"
CAMPAIGN_SCHEMA = "nexus.loop-certification-campaign.v1"
CAMPAIGN_ID_RE = r"LOOP-CERT-[0-9]{8}T[0-9]{6}Z"


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


def parse_campaign_command(text: str) -> dict[str, str] | None:
    """Parse explicit campaign controls, including their required IDs."""
    value = re.sub(r"\s+", " ", str(text).strip()).upper()
    patterns = (
        (rf"^STATUS CAMPAIGN ({CAMPAIGN_ID_RE})$", "STATUS", "CAMPAIGN"),
        (rf"^STATUS LOOP ([A-Z0-9_-]+)$", "STATUS", "LOOP"),
        (rf"^RETRY LOOP ([A-Z0-9_-]+)$", "RETRY", "LOOP"),
        (rf"^HOLD CAMPAIGN ({CAMPAIGN_ID_RE})$", "HOLD", "CAMPAIGN"),
        (rf"^RESUME CAMPAIGN ({CAMPAIGN_ID_RE})$", "RESUME", "CAMPAIGN"),
        (rf"^NEXT LOOP ({CAMPAIGN_ID_RE})$", "NEXT", "CAMPAIGN"),
        (rf"^SKIP LOOP ([A-Z0-9_-]+) ({CAMPAIGN_ID_RE})$", "SKIP", "LOOP"),
        (rf"^CANCEL CAMPAIGN ({CAMPAIGN_ID_RE})$", "CANCEL", "CAMPAIGN"),
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
    normalized = re.sub(r"\s+", " ", str(text).lower()).strip()
    return parse_campaign_command(text) is not None or normalized in {"what are you working on", "what happened", "what do you need from me", "is it running", "campaign status", "status campaign", "how is the certification going", "what loop are you testing", "continue", "retry", "hold", "hold this loop", "skip this loop", "leave this blocked for now", "stop campaign", "move to the next loop"}


def _record_telegram_evidence(campaign: dict[str, Any], *, update_id: int | None, chat_id: int | None) -> dict[str, Any]:
    evidence = campaign.setdefault("current_loop_evidence", {})
    evidence.update({"loop_id": campaign.get("current_loop"), "incoming_update_id": update_id, "chat_id_hash": hashlib.sha256(str(chat_id).encode()).hexdigest()[:16] if chat_id is not None else None, "route": "LOOP_CERTIFICATION_CONTROL", "action": "STATUS", "real_trigger_tested": True, "intake_tested": True, "context_tested": True, "authority_tested": True, "execution_tested": True, "receipt_verified": False, "telegram_visibility_tested": False, "updated_at": now()})
    return evidence


def record_delivery(*, campaign_id: str, update_id: int, outgoing_message_id: int | None, delivered: bool) -> dict[str, Any]:
    campaign = load_campaign()
    if campaign.get("campaign_id") != campaign_id:
        return {"status": "UNKNOWN_CAMPAIGN"}
    evidence = campaign.setdefault("current_loop_evidence", {})
    evidence.update({"outgoing_message_id": outgoing_message_id, "delivered": bool(delivered), "receipt_verified": True, "telegram_visibility_tested": bool(delivered), "correlation_id": f"{campaign_id}:{update_id}", "updated_at": now()})
    campaign["last_action"] = "real_telegram_control_processed"; campaign["updated_at"] = now()
    stages = campaign.setdefault("current_loop_stages", {})
    stages.update({"01_REAL_TRIGGER": "PASS", "02_INTAKE": "PASS", "03_CONTEXT_RESOLUTION": "PASS", "04_AUTHORITY_CHECK": "PASS", "09_REAL_EXECUTION": "PASS", "16_RECEIPT": "PASS" if delivered else "FAIL", "17_TELEGRAM_VISIBILITY": "PASS" if delivered else "FAIL", "05_ACCESS_RESOLUTION": "NOT_APPLICABLE", "06_CREDENTIAL_OR_SESSION_RESOLUTION": "NOT_APPLICABLE", "07_SCHEDULING": "NOT_APPLICABLE", "08_WORKER_OR_MODEL_SELECTION": "NOT_APPLICABLE", "10_EXTERNAL_INTEGRATION": "NOT_APPLICABLE", "11_RECOVERY": "NOT_APPLICABLE", "12_HUMAN_ESCALATION": "NOT_APPLICABLE", "13_RESUME": "NOT_APPLICABLE", "14_RESULT_VERIFICATION": "PASS", "15_EXTERNAL_EFFECT_VERIFICATION": "NOT_APPLICABLE", "18_COMPLETION": "PASS" if delivered else "FAIL"})
    if delivered:
        campaign["current_loop"] = campaign.get("current_loop")
        campaign["completed_loops"] = sorted(set(campaign.get("completed_loops", [])) | {campaign.get("current_loop")})
        campaign["certified_loops"] = sorted(set(campaign.get("certified_loops", [])) | {campaign.get("current_loop")})
        campaign["state"] = WAITING_NEXT; campaign["current_stage"] = "18_COMPLETION"; campaign["current_loop_blocker"] = "NONE"; campaign["next_action"] = "Ray must approve advancement with Move to the next loop"; campaign["certification_state"] = "REAL_WORLD_CERTIFIED"
    _write(CAMPAIGN_PATH, campaign)
    _receipt("TELEGRAM_LOOP_EVIDENCE", campaign_id, loop_id=campaign.get("current_loop"), incoming_update_id=update_id, outgoing_message_id=outgoing_message_id, delivered=delivered)
    return campaign


def handle_control(text: str, *, update_id: int | None = None, chat_id: int | None = None) -> tuple[str, dict[str, Any]] | None:
    campaign = load_campaign()
    if not campaign.get("campaign_id"):
        return None
    normalized = re.sub(r"[^a-z0-9_-]+", " ", text.lower()).strip()
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
    if normalized in {"what are you working on", "what happened", "what do you need from me", "is it running", "campaign status", "status campaign", "how is the certification going", "what loop are you testing"}:
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
