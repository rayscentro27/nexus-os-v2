"""Small durable receipts for calls crossing the shared MCP gateway."""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path


def record(*, request_id: str, correlation_id: str, engine: str, operation: str,
           authorization: str, result: dict, started_at: str) -> dict:
    if not request_id or not correlation_id or len(request_id) > 128 or len(correlation_id) > 128:
        raise ValueError("GATEWAY_RECEIPT_IDS_INVALID")
    root_value = os.getenv("NEXUS_GATEWAY_RECEIPT_DIR") or os.getenv("NEXUS_MCP_RECEIPT_DIR")
    if root_value:
        root = Path(root_value).expanduser().resolve()
    else:
        from nexus_agent_platform.runtime.paths import nexus_research_state_path
        root = nexus_research_state_path("runtime", "gateway_receipts").resolve()
    root.mkdir(parents=True, exist_ok=True)
    receipt_id = "gwrcpt_" + hashlib.sha256((engine + "\0" + operation + "\0" + request_id).encode()).hexdigest()[:32]
    receipt = {
        "schema": "nexus.gateway.receipt.v1", "receipt_id": receipt_id,
        "gateway_request_id": request_id, "correlation_id": correlation_id,
        "engine": engine, "operation": operation, "actor": "NOVA_NEXUS",
        "authorization": authorization,
        "action_result": {k: result[k] for k in ("status", "health", "approval_required") if k in result},
        "evidence_refs": result.get("evidence_refs", [])[:100] if isinstance(result.get("evidence_refs"), list) else [],
        "mutation_count": int(result.get("mutation_count", 0) or 0),
        "approval_reference": result.get("approval_reference"),
        "started_at": started_at,
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }
    target = root / (receipt_id + ".json")
    if target.exists():
        existing = json.loads(target.read_text(encoding="utf-8"))
        if existing.get("correlation_id") != correlation_id:
            raise ValueError("GATEWAY_REQUEST_ID_REPLAY_CONFLICT")
        return existing
    temporary = target.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(receipt, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    os.replace(temporary, target)
    return receipt
