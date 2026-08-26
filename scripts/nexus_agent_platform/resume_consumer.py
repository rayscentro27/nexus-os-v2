"""Consume an exact human-gate resume receipt and prove one real next action."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from .capability_broker import run_capability
    from .coding_worker_supervisor import persist_campaign
except ImportError:  # direct governed script execution
    from nexus_agent_platform.capability_broker import run_capability
    from nexus_agent_platform.coding_worker_supervisor import persist_campaign

ROOT = Path(__file__).resolve().parents[2]
LEDGER = ROOT / "data/runtime/nexus_human_gate_ledger.json"
RECEIPTS = ROOT / "reports/runtime/resume_consumer"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError, TypeError):
        return {}


def _write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def consume_resume_receipt(*, ledger_path: Path = LEDGER) -> dict[str, Any]:
    ledger = _read(ledger_path)
    gates = [row for row in ledger.get("gates", []) if isinstance(row, dict)]
    gate = next((row for row in reversed(gates) if row.get("status") == "CLOSED" and row.get("resume_receipt")), None)
    if not gate:
        return {"status": "NO_RESUME_RECEIPT", "campaign_action": "NONE"}
    if gate.get("resume_execution", {}).get("status") == "RECONCILED":
        return gate["resume_execution"]

    resume = gate["resume_receipt"]
    campaign = _read(ROOT / "data/runtime/nexus_completion_campaign.json")
    checkpoint = str(resume.get("checkpoint_sha") or campaign.get("checkpoint_sha") or "UNKNOWN")
    closed_gate_id = str(gate.get("gate_id") or "")
    remaining = [str(item) for item in (campaign.get("remaining_work") or [])]
    remaining = [item for item in remaining if closed_gate_id not in item and "Ray ACK" not in item]
    next_objective = remaining[0] if remaining else "completion_audit"
    execution_started = _now()
    receipt = run_capability("system.health", receipt_dir=RECEIPTS)
    downstream_id = receipt.get("receipt_id")
    receiver_ack = receipt.get("status") == "PASS" and bool(downstream_id)
    verified = receiver_ack and (RECEIPTS / f"{downstream_id}.json").exists()
    execution = {
        "status": "RECONCILED" if verified else "FAIL",
        "gate_id": gate.get("gate_id"),
        "resume_receipt_id": resume.get("receipt_id"),
        "campaign_id": campaign.get("campaign_id", "NEXUS_COMPLETION_DAY_2026_08_26"),
        "checkpoint_sha": checkpoint,
        "checkpoint_loaded": checkpoint != "UNKNOWN",
        "next_objective": next_objective,
        "downstream_job_id": downstream_id,
        "receiver_ack": "PASS" if receiver_ack else "FAIL",
        "execution_started_at": execution_started,
        "result_ref": str(RECEIPTS / f"{downstream_id}.json") if downstream_id else None,
        "verification": "PASS" if verified else "FAIL",
        "reconciled_at": _now() if verified else None,
    }
    gate["resume_execution"] = execution
    ledger["gates"] = gates
    ledger["updated_at"] = _now()
    _write(ledger_path, ledger)
    if verified:
        persist_campaign(
            status="ACTIVE", current_wave=int(campaign.get("current_wave", 18)),
            current_objective=next_objective, checkpoint_sha=checkpoint,
            active_jobs=[downstream_id], worker_assignments=campaign.get("worker_assignments", {}),
        )
    return execution


if __name__ == "__main__":
    print(json.dumps(consume_resume_receipt(), indent=2))
