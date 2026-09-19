#!/usr/bin/env python3
"""Idempotently project a canonical governed approval into Supabase."""
from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
import ssl
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APPROVAL_ID = "appr_f1c900e26b494b71b576877b9019b891"


def load_env() -> None:
    path = ROOT / ".env"
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        if "=" not in line or line.lstrip().startswith("#"):
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def request(path: str, method: str = "GET", body: dict | None = None):
    url = (os.environ.get("SUPABASE_URL") or os.environ.get("VITE_SUPABASE_URL", "")).rstrip("/")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        raise RuntimeError("Supabase service configuration unavailable")
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(f"{url}/rest/v1/{path}", data=data, method=method, headers={"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json", "Prefer": "return=representation"})
    try:
        import certifi
        context = ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        context = ssl.create_default_context()
    with urllib.request.urlopen(req, timeout=20, context=context) as response:
        return json.loads(response.read() or b"null")


def main() -> None:
    load_env()
    rows = [json.loads(line) for line in (ROOT / "data/governed/approvals.jsonl").read_text().splitlines() if line.strip()]
    current = next((row for row in reversed(rows) if row.get("id") == APPROVAL_ID), None)
    if not current:
        raise RuntimeError(f"Canonical approval not found: {APPROVAL_ID}")
    payload = {
        "canonical_approval_id": APPROVAL_ID,
        "company_cycle_id": current.get("input_summary", {}).get("company_cycle_id"),
        "type": "CAMPAIGN_APPROVAL",
        "reason": current.get("action_summary"),
        "what_ray_is_deciding": "Approve, reject, or request changes to the bounded campaign action.",
        "risk": current.get("risk_level", "high"),
        "scope": current.get("input_summary", {}),
        "artifact_refs": current.get("evidence_refs", []),
        "external_action_if_approved": "Resume the existing company cycle; external publication remains receipt-gated.",
        "idempotency_key": f"approval-sync:{APPROVAL_ID}",
    }
    all_rows = request("approvals?select=id,status,payload&limit=500") or []
    existing = [row for row in all_rows if (row.get("payload") or {}).get("canonical_approval_id") == APPROVAL_ID]
    record = {"lane": "system", "item_type": "CAMPAIGN_APPROVAL", "status": current.get("status", "pending"), "title": current.get("action_summary", "Campaign approval"), "summary": current.get("action_summary", "Ray approval required"), "payload": payload}
    if existing:
        remote_id = existing[0]["id"]
        result = request(f"approvals?id=eq.{remote_id}", "PATCH", record)
        action = "updated"
    else:
        result = request("approvals", "POST", record)
        remote_id = result[0]["id"] if result else None
        action = "inserted"
    print(json.dumps({"action": action, "canonical_approval_id": APPROVAL_ID, "remote_approval_id": remote_id, "company_cycle_id": payload["company_cycle_id"], "status": record["status"]}))


if __name__ == "__main__":
    main()
