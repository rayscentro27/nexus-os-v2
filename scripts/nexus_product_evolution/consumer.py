"""Receipt-backed Product Evolution handoff for the canonical scheduler.

This is an adapter to the existing Phase 15 dispatch, not a scheduler. It
claims queued receipts under one lock and records an honest blocker when no
bounded execution adapter is registered for that mission.
"""
from __future__ import annotations

import fcntl
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[2]
RECEIPT_DIR = ROOT / "reports/product_evolution"
LOCK_PATH = ROOT / "data/runtime/product_evolution_dispatch.lock"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write(path: Path, value: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")
        temporary = Path(handle.name)
    os.replace(temporary, path)


def _claim(path: Path, scheduler_instance: str) -> Dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    result = value.get("result") or {}
    if result.get("status") != "QUEUED":
        return {"mission_id": result.get("mission_id"), "status": result.get("status"), "claimed": False}
    now = _now()
    dispatch = result.get("dispatch") or {}
    result.update({
        "status": "RUNNING",
        "current_stage": "DISPATCH_CLAIMED",
        "updated_at": now,
        "dispatch": {**dispatch, "pickup_state": "PICKED_UP", "claimed_at": now, "scheduler_instance": scheduler_instance, "last_dispatch_observation": now},
    })
    _write(path, {**value, "result": result})
    return {"mission_id": result.get("mission_id"), "status": "RUNNING", "claimed": True, "receipt_path": str(path)}


def consume_queued_missions(*, scheduler_instance: str, receipt_dir: Path = RECEIPT_DIR) -> Dict[str, Any]:
    """Claim each queued mission once during an existing governed dispatch.

    No arbitrary mission execution is inferred from a Telegram contract. A
    claimed mission is marked BLOCKED until a bounded surface-specific adapter
    is explicitly registered; this prevents silent indefinite RUNNING state.
    """
    receipt_dir.mkdir(parents=True, exist_ok=True)
    claimed: List[Dict[str, Any]] = []
    blocked: List[Dict[str, Any]] = []
    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOCK_PATH.open("w", encoding="utf-8") as lock:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return {"consumer": "phase15_product_evolution_dispatch", "status": "SKIPPED_LOCKED", "claimed": [], "blocked": []}
        for path in sorted(receipt_dir.glob("*.json")):
            try:
                item = _claim(path, scheduler_instance)
            except (OSError, ValueError, TypeError):
                continue
            if not item.get("claimed"):
                continue
            claimed.append(item)
            value = json.loads(path.read_text(encoding="utf-8"))
            result = value.get("result") or {}
            now = _now()
            result.update({"status": "BLOCKED", "current_stage": "DISPATCH_CLAIMED", "blocker": "EXECUTION_ADAPTER_MISSING", "updated_at": now})
            dispatch = result.get("dispatch") or {}
            result["dispatch"] = {**dispatch, "last_dispatch_observation": "Claimed by canonical Phase 15 dispatcher; no bounded Product Evolution execution adapter is registered."}
            _write(path, {**value, "result": result})
            blocked.append({"mission_id": result.get("mission_id"), "status": "BLOCKED", "reason": result["blocker"]})
        fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
    return {"consumer": "phase15_product_evolution_dispatch", "status": "COMPLETED", "claimed": claimed, "blocked": blocked}
