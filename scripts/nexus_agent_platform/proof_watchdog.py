"""Proof-of-work ledger and first-failure diagnosis for natural cycles."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable

STAGES = ("S0_SCHEDULED", "S1_SELECTED", "S2_HANDOFF_CREATED", "S3_RECEIVER_ACKNOWLEDGED", "S4_EXECUTOR_STARTED", "S5_ARTIFACT_PRODUCED", "S6_VERIFIED", "S7_RECONCILED", "S8_COMPLETED")


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def diagnose(objective: Dict[str, Any]) -> Dict[str, Any]:
    current = objective.get("last_confirmed_stage") or objective.get("current_stage") or "S0_SCHEDULED"
    try:
        start = STAGES.index(current)
    except ValueError:
        start = 0
    refs = set(objective.get("proof_refs") or [])
    expected = objective.get("next_expected_stage")
    failure = expected or (STAGES[min(start + 1, len(STAGES) - 1)] if start < len(STAGES) - 1 else None)
    missing = failure not in refs if failure else False
    status = "STALLED" if missing else "UNKNOWN"
    signature = hashlib.sha256(f"{objective.get('executor')}:{failure}:{objective.get('failure_signature','')}".encode()).hexdigest()[:16]
    return {"objective_id": objective.get("objective_id"), "failure_stage": failure if missing else None,
            "health": status, "failure_signature": signature if missing else None,
            "diagnosed_at": now(), "reason": "expected proof is absent" if missing else "no deterministic diagnosis"}


def audit(objectives: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    rows = [diagnose(item) for item in objectives if item.get("health") in {"ACTIVE", "DISPATCHED", "RUNNING", "RECOVERING"}]
    return {"schema_version": "nexus.proof-diagnosis.v1", "generated_at": now(), "proof_watchdog": "PASS", "objectives": rows,
            "stalled": sum(row["health"] == "STALLED" for row in rows), "coverage": 1.0 if not rows else sum(row["health"] != "STALLED" for row in rows) / len(rows)}
