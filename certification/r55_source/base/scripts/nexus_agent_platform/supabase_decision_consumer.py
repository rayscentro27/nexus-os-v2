"""Consume Ray decisions from the shared Supabase control plane.

This is a consumer of the existing canonical continuous runtime, not a new
scheduler. It is idempotent on the remote event id and writes the local
canonical checkpoint plus a remote receipt event.
"""
from __future__ import annotations

import json
import os
import ssl
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
AUDIT = ROOT / "data/governed/audit.jsonl"


def _env() -> None:
    path = ROOT / ".env"
    if path.exists():
        for line in path.read_text().splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _request(path: str, method: str = "GET", body: dict[str, Any] | None = None) -> Any:
    _env()
    base = (os.environ.get("SUPABASE_URL") or os.environ.get("VITE_SUPABASE_URL", "")).rstrip("/")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not base or not key:
        return None
    data = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(f"{base}/rest/v1/{path}", data=data, method=method, headers={"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json", "Prefer": "return=representation"})
    try:
        try:
            import certifi
            context = ssl.create_default_context(cafile=certifi.where())
        except ImportError:
            context = ssl.create_default_context()
        with urllib.request.urlopen(request, timeout=15, context=context) as response:
            return json.loads(response.read() or b"null")
    except Exception:
        return None


def _audit_ids() -> set[str]:
    if not AUDIT.exists():
        return set()
    ids = set()
    for line in AUDIT.read_text().splitlines():
        try:
            row = json.loads(line)
            if row.get("remote_event_id"):
                ids.add(str(row["remote_event_id"]))
        except json.JSONDecodeError:
            pass
    return ids


def _append(row: dict[str, Any]) -> None:
    AUDIT.parent.mkdir(parents=True, exist_ok=True)
    with AUDIT.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")


def sync_approval(approval: dict[str, Any]) -> dict[str, Any] | None:
    """Project one canonical governed approval, preserving one logical id."""
    payload = {
        "canonical_approval_id": approval.get("id"),
        "company_cycle_id": (approval.get("input_summary") or {}).get("company_cycle_id"),
        "type": "CAMPAIGN_APPROVAL" if approval.get("action_id") == "client.sends" else "GOVERNED_APPROVAL",
        "reason": approval.get("action_summary"),
        "what_ray_is_deciding": "Approve, reject, or request changes to the bounded action.",
        "risk": approval.get("risk_level", "unknown"),
        "scope": approval.get("input_summary", {}),
        "artifact_refs": approval.get("evidence_refs", []),
        "external_action_if_approved": "Resume the existing company cycle; external publication remains receipt-gated.",
        "idempotency_key": f"approval-sync:{approval.get('id')}",
    }
    try:
        all_rows = _request("approvals?select=id,payload&limit=500") or []
        existing = [row for row in all_rows if (row.get("payload") or {}).get("canonical_approval_id") == approval.get("id")]
        record = {"lane": "system", "item_type": payload["type"], "status": approval.get("status", "pending"), "title": approval.get("action_summary", "Governed approval"), "summary": approval.get("action_summary", "Ray approval required"), "payload": payload}
        if existing:
            return _request(f"approvals?id=eq.{existing[0]['id']}", "PATCH", record)
        return _request("approvals", "POST", record)
    except Exception:
        return None


def consume_pending_decisions() -> dict[str, Any]:
    events = _request("nexus_events?select=id,created_at,action,status,payload,correlation_id&action=eq.ray_decision_recorded&status=eq.success&order=created_at.asc&limit=100") or []
    consumed = _audit_ids()
    results = []
    for event in events if isinstance(events, list) else []:
        event_id = str(event.get("id", ""))
        if not event_id or event_id in consumed:
            continue
        payload = event.get("payload") or {}
        cycle_id = payload.get("company_cycle_id") or event.get("correlation_id")
        decision = payload.get("decision")
        if not cycle_id or decision not in {"approved", "rejected", "revise"}:
            continue
        cycle_path = ROOT / "data/runtime/company_cycles" / f"{cycle_id}.json"
        if not cycle_path.exists():
            continue
        state = json.loads(cycle_path.read_text())
        if decision == "approved":
            state.update({"campaign_approval_status": "APPROVED", "current_stage": "SOCIAL", "status": "WAITING_EXTERNAL"})
            state.setdefault("stages", {})["SOCIAL"] = {"status": "BLOCKED_EXTERNAL", "owner": "social_distribution", "latest_result": "No authenticated configured GoClear posting account is present.", "next_action": "Connect or select an approved account."}
            next_action = "Continue Social and Email receipt validation."
        elif decision == "revise":
            state.update({"campaign_approval_status": "REQUEST_CHANGES", "current_stage": "DEPARTMENTS", "status": "ACTIVE"})
            next_action = "Route revision feedback to the assigned department."
        else:
            state.update({"campaign_approval_status": "REJECTED", "current_stage": "ADMIN_APPROVAL", "status": "REJECTED"})
            next_action = "Cycle closed unless Ray reopens it."
        state.setdefault("stages", {})["ADMIN_APPROVAL"] = {"status": "PASS_REAL" if decision == "approved" else decision.upper(), "latest_result": payload.get("feedback") or decision, "next_action": next_action}
        cycle_path.write_text(json.dumps(state, indent=2) + "\n")
        receipt = {"event": "RAY_DECISION_CONSUMED", "remote_event_id": event_id, "approval_id": payload.get("approval_id"), "company_cycle_id": cycle_id, "decision": decision, "resumed_stage": state["current_stage"], "recorded_at": event.get("created_at")}
        _append(receipt)
        _request("nexus_events", "POST", {"lane": "system", "source": "canonical_runtime", "action": "ray_decision_consumed", "status": "success", "title": "Ray decision consumed", "summary": f"Canonical runtime consumed {decision}.", "payload": receipt, "correlation_id": cycle_id})
        results.append(receipt)
    return {"status": "CONSUMED" if results else "NO_NEW_DECISIONS", "count": len(results), "receipts": results}


if __name__ == "__main__":
    print(json.dumps(consume_pending_decisions(), indent=2))
