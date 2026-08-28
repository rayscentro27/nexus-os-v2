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
        "human_waiting_loops": [], "last_action": "campaign_created", "next_action": "perform the real trigger for the current loop",
        "next_retry": None, "loop_order": [row["loop_id"] for row in loops], "inventory": loops,
        "current_repair": {"repair_id": "VOICE-001", "work_order_id": "wo_b5a3b90892804ec79164159997caf264", "state": "WAITING_WORKER", "reason": "NO_CERTIFIED_AI_ENGINEERING_WORKER"},
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
    return (f"You need to handle: {campaign.get('current_loop', 'NONE')}\n\n"
            f"Campaign: {campaign['campaign_id']}\nCertified: {certified} / {len(inventory)}\n"
            f"Current loop: {campaign.get('current_loop', 'NONE')}\nState: {campaign.get('state', 'UNKNOWN')}\n"
            f"What Nexus is doing: {campaign.get('next_action', 'UNKNOWN')}\n"
            f"Current blocker: {campaign.get('current_repair', {}).get('reason', 'NONE')}\n"
            f"Do you need me? {'YES' if campaign.get('human_waiting_loops') else 'NO'}\n"
            "Next loop: held until the current loop is complete and Ray approves advancement.")


def handle_control(text: str) -> tuple[str, dict[str, Any]] | None:
    campaign = load_campaign()
    if not campaign.get("campaign_id"):
        return None
    normalized = re.sub(r"[^a-z0-9_-]+", " ", text.lower()).strip()
    if normalized in {"what are you working on", "what happened", "what do you need from me", "is it running", "campaign status", "status campaign"}:
        return status_text(), {"route": "LOOP_CERTIFICATION_STATUS", "campaign_id": campaign["campaign_id"]}
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
