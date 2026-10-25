#!/usr/bin/env python3
"""Canonical durable department handoff client.

The canonical handoff store is the Supabase table
``public.nexus_department_handoffs`` - the existing ``research_handoffs``
relation extended in place, not a new parallel system.

Contract:

    create -> CREATED -> DELIVERED -> ACKNOWLEDGED -> PROCESSING -> COMPLETED
                                                     \\-> FAILED_RETRYABLE
                                                      \\-> FAILED_FINAL

Design rules enforced here:

* The row is the record. A handoff that is not in this table did not happen.
* Every lifecycle transition is a durable, timestamped state change.
* ``dedupe_key`` is derived deterministically from logical content, so the same
  logical handoff maps to the same key and the database unique index rejects the
  second delivery.
* A direct department-to-department message is never the only record: the
  direct send is recorded here first and carries the durable handoff id.
"""
from __future__ import annotations

import hashlib
import json
import os
import ssl
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
TABLE = "nexus_department_handoffs"
RECEIPT_DIR = ROOT / "reports/runtime/department_handoffs"

CREATED = "CREATED"
DELIVERED = "DELIVERED"
ACKNOWLEDGED = "ACKNOWLEDGED"
PROCESSING = "PROCESSING"
COMPLETED = "COMPLETED"
FAILED_RETRYABLE = "FAILED_RETRYABLE"
FAILED_FINAL = "FAILED_FINAL"

STATUS_MODEL = (CREATED, DELIVERED, ACKNOWLEDGED, PROCESSING, COMPLETED, FAILED_RETRYABLE, FAILED_FINAL)


class HandoffStoreUnavailable(RuntimeError):
    """The canonical handoff store could not be read or written.

    Raised instead of returning an empty result, so a store fault can never be
    mistaken for an empty inbox or a completed handoff.
    """
OPEN_STATUSES = (CREATED, DELIVERED, ACKNOWLEDGED, PROCESSING, FAILED_RETRYABLE)
TERMINAL_STATUSES = (COMPLETED, FAILED_FINAL)
MAX_RETRY_COUNT = 3


# --------------------------------------------------------------------------
# transport
# --------------------------------------------------------------------------
def _env() -> dict[str, str]:
    env: dict[str, str] = {}
    local = ROOT / ".env"
    allowed = {"SUPABASE_URL", "VITE_SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"}
    if local.exists():
        for line in local.read_text(errors="ignore").splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("#") and "=" in stripped:
                key, value = stripped.split("=", 1)
                name = key.strip()
                if name in allowed:
                    env[name] = value.strip().strip('"').strip("'")
    try:
        sys.path.insert(0, str(ROOT / "scripts" / "ops"))
        from nexus_runtime_env import load_runtime_env
        env.update(load_runtime_env())
    except Exception:  # noqa: BLE001
        pass
    return env


ENV = _env()
URL = (ENV.get("SUPABASE_URL") or ENV.get("VITE_SUPABASE_URL") or "").rstrip("/")
KEY = ENV.get("SUPABASE_SERVICE_ROLE_KEY", "")


def _ssl_context() -> ssl.SSLContext:
    try:
        import certifi  # type: ignore
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:  # noqa: BLE001
        return ssl.create_default_context()


def configured() -> bool:
    return bool(URL and KEY)


def _redact(text: str) -> str:
    return text.replace(KEY, "<redacted>") if KEY and text else text


def rest(method: str, path: str, body: Any = None, prefer: str | None = None) -> tuple[int, Any]:
    headers = {"apikey": KEY, "Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}
    if prefer:
        headers["Prefer"] = prefer
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(f"{URL}/rest/v1/{path}", data=data, method=method, headers=headers)
    try:
        opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=_ssl_context()))
        with opener.open(request, timeout=30) as response:
            raw = response.read().decode(errors="ignore")
            return response.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as exc:  # type: ignore[attr-defined]
        return exc.code, _redact(exc.read().decode(errors="ignore"))[:400]
    except Exception as exc:  # noqa: BLE001
        return 0, _redact(f"{type(exc).__name__}: {exc}")[:400]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


# --------------------------------------------------------------------------
# deduplication
# --------------------------------------------------------------------------
def deterministic_dedupe_key(*, source_department: str, target_department: str, handoff_type: str,
                             topic: str, source_ids: list[str] | None = None,
                             payload: dict[str, Any] | None = None,
                             logical_key: str | None = None) -> str:
    """Content-addressed key for one logical handoff.

    Deliberately excludes wall-clock time and any volatile field, so replaying
    the same logical handoff - from a retry, a second producer pass, or a
    duplicated event - yields the same key and is rejected by the database.
    """
    if logical_key:
        identity = {"logical_key": logical_key}
    else:
        stable_payload = {k: v for k, v in sorted((payload or {}).items())
                          if k not in {"observed_at", "created_at", "timestamp", "nonce"}}
        identity = {
            "source": source_department,
            "target": target_department,
            "type": handoff_type,
            "topic": topic,
            "source_ids": sorted(source_ids or []),
            "payload": stable_payload,
        }
    raw = json.dumps(identity, sort_keys=True, separators=(",", ":"), default=str)
    return "hnd_" + hashlib.sha256(raw.encode()).hexdigest()[:32]


# --------------------------------------------------------------------------
# lifecycle
# --------------------------------------------------------------------------
def create_handoff(*, source_department: str, target_department: str, handoff_type: str, topic: str,
                   payload: dict[str, Any] | None = None, source_ids: list[str] | None = None,
                   artifact_refs: list[str] | None = None, logical_key: str | None = None,
                   dedupe_key: str | None = None) -> dict[str, Any]:
    """Create one handoff, or report the existing row for the same logical work."""
    if not configured():
        return {"status": "UNAVAILABLE", "reason": "SUPABASE_NOT_CONFIGURED", "created": False}
    key = dedupe_key or deterministic_dedupe_key(
        source_department=source_department, target_department=target_department,
        handoff_type=handoff_type, topic=topic, source_ids=source_ids, payload=payload,
        logical_key=logical_key)
    existing = find_by_dedupe_key(key)
    if existing:
        return {"status": "DUPLICATE_SUPPRESSED", "created": False, "dedupe_key": key,
                "handoff_id": existing.get("handoff_id"), "handoff_status": existing.get("status"),
                "reason": "an identical logical handoff already exists"}
    now = utc_now()
    handoff_payload = dict(payload or {})
    continuation = handoff_payload.get("continuation")
    if not isinstance(continuation, dict):
        continuation = {}
    handoff_payload["continuation"] = {
        **continuation,
        "owner_department": target_department,
        "parent_goal_id": continuation.get("parent_goal_id") or handoff_payload.get("parent_goal_id") or handoff_payload.get("goal_id"),
        "next_action": continuation.get("next_action") or handoff_payload.get("next_action") or "RECEIVER_ACKNOWLEDGE_ATTACH_GOAL_AND_DERIVE_NEXT_ACTION",
        "success_criteria": continuation.get("success_criteria") or handoff_payload.get("success_criteria") or [],
    }
    row = {
        "handoff_id": f"hndo_{hashlib.sha256((key + now).encode()).hexdigest()[:24]}",
        "source_department": source_department,
        "target_department": target_department,
        "handoff_type": handoff_type,
        "topic": topic,
        "payload": handoff_payload,
        "source_ids": source_ids or [],
        "artifact_refs": artifact_refs or [],
        "status": CREATED,
        "dedupe_key": key,
        "retry_count": 0,
        "created_at": now,
        "updated_at": now,
    }
    status, body = rest("POST", TABLE, body=[row], prefer="return=representation")
    if status in (200, 201) and isinstance(body, list) and body:
        handoff_id = body[0]["handoff_id"]
        delivery = mark_delivered(handoff_id)
        return {"status": delivery.get("status", CREATED), "created": True, "dedupe_key": key,
                "handoff_id": handoff_id, "handoff_status": delivery.get("status", body[0]["status"]),
                "delivery_receipt": delivery,
                "duplicate_prevented_by": "APPLICATION_LOOKUP"}
    if status == 409 or "duplicate key" in str(body).lower():
        # The unique index is the real guard: two producers racing the same
        # logical handoff produce one row, not two.
        winner = find_by_dedupe_key(key) or {}
        return {"status": "DUPLICATE_SUPPRESSED", "created": False, "dedupe_key": key,
                "handoff_id": winner.get("handoff_id"), "handoff_status": winner.get("status"),
                "duplicate_prevented_by": "DATABASE_UNIQUE_INDEX"}
    return {"status": "CREATE_FAILED", "created": False, "http_status": status,
            "error": str(body)[:300], "dedupe_key": key}


def find_by_dedupe_key(key: str) -> dict[str, Any] | None:
    status, body = rest("GET", f"{TABLE}?dedupe_key=eq.{key}&select=*")
    if status == 200 and isinstance(body, list) and body:
        return body[0]
    return None


def get_handoff(handoff_id: str) -> dict[str, Any] | None:
    status, body = rest("GET", f"{TABLE}?handoff_id=eq.{handoff_id}&select=*")
    if status == 200 and isinstance(body, list) and body:
        return body[0]
    return None


def list_inbox(*, target_department: str, statuses: tuple[str, ...] = (CREATED, DELIVERED, ACKNOWLEDGED),
               limit: int = 50) -> list[dict[str, Any]]:
    """Durable retrieval. An offline consumer simply does not call this.

    A query error is raised rather than reported as an empty inbox: a silent
    empty list would be indistinguishable from "nothing is waiting", which is
    exactly the conclusion this path must never get wrong.
    """
    if not configured():
        raise HandoffStoreUnavailable("handoff store is not configured")
    path = (f"{TABLE}?target_department=eq.{target_department}"
            f"&status=in.({','.join(statuses)})"
            f"&order=created_at.asc&limit={limit}&select=*")
    status, body = rest("GET", path)
    if status != 200 or not isinstance(body, list):
        raise HandoffStoreUnavailable(f"inbox query failed (HTTP {status}): {str(body)[:200]}")
    return body


def _transition(handoff_id: str, expected: tuple[str, ...], updates: dict[str, Any]) -> dict[str, Any]:
    """Compare-and-set lifecycle transition. A stale state never overwrites."""
    current = get_handoff(handoff_id)
    if not current:
        return {"status": "NOT_FOUND", "handoff_id": handoff_id}
    if current.get("status") not in expected:
        return {"status": "TRANSITION_REJECTED", "handoff_id": handoff_id,
                "current_status": current.get("status"), "expected_any_of": list(expected)}
    if updates.get("status") == ACKNOWLEDGED:
        current_payload = current.get("payload") if isinstance(current.get("payload"), dict) else {}
        continuation = current_payload.get("continuation") if isinstance(current_payload.get("continuation"), dict) else {}
        work_order_id = current.get("receiving_work_order_id") or continuation.get("work_order_id")
        if not current.get("target_department") or not continuation.get("receiver_goal_id") or not work_order_id or not continuation.get("next_action"):
            return {"status": "ACKNOWLEDGMENT_REJECTED", "handoff_id": handoff_id,
                    "reason": "receiver_goal_work_order_and_next_action_required"}
        order_status, orders = rest("GET", f"task_requests?id=eq.{work_order_id}&select=id,payload&limit=1")
        if order_status != 200 or not isinstance(orders, list) or not orders:
            return {"status": "ACKNOWLEDGMENT_REJECTED", "handoff_id": handoff_id,
                    "reason": "durable_work_order_readback_required"}
        order_payload = orders[0].get("payload") if isinstance(orders[0].get("payload"), dict) else {}
        if order_payload.get("handoff_id") != handoff_id or order_payload.get("goal_id") != continuation.get("receiver_goal_id"):
            return {"status": "ACKNOWLEDGMENT_REJECTED", "handoff_id": handoff_id,
                    "reason": "work_order_ownership_mismatch"}
    payload = {**updates, "updated_at": utc_now()}
    status, body = rest("PATCH", f"{TABLE}?handoff_id=eq.{handoff_id}&status=in.({','.join(expected)})",
                        body=payload, prefer="return=representation")
    if status in (200, 204):
        refreshed = get_handoff(handoff_id) or {}
        return {"status": refreshed.get("status", "UPDATED"), "handoff_id": handoff_id,
                "previous_status": current.get("status")}
    return {"status": "TRANSITION_FAILED", "handoff_id": handoff_id, "http_status": status,
            "error": str(body)[:200]}


def mark_delivered(handoff_id: str) -> dict[str, Any]:
    return _transition(handoff_id, (CREATED,), {"status": DELIVERED, "delivered_at": utc_now()})


def acknowledge(handoff_id: str, *, acknowledged_by: str, note: str = "") -> dict[str, Any]:
    now = utc_now()
    current = get_handoff(handoff_id) or {}
    payload = current.get("payload")
    if not isinstance(payload, dict):
        payload = {}
    continuation = payload.get("continuation") if isinstance(payload.get("continuation"), dict) else {}
    receiver_goal_id = continuation.get("receiver_goal_id")
    work_order_id = current.get("receiving_work_order_id") or continuation.get("work_order_id")
    next_action = continuation.get("next_action")
    if not current.get("target_department") or not receiver_goal_id or not work_order_id or not next_action:
        return {"status": "ACKNOWLEDGMENT_REJECTED", "handoff_id": handoff_id,
                "reason": "receiver_goal_work_order_and_next_action_required"}
    order_status, orders = rest("GET", f"task_requests?id=eq.{work_order_id}&select=id,payload,status&limit=1")
    if order_status != 200 or not isinstance(orders, list) or not orders:
        return {"status": "ACKNOWLEDGMENT_REJECTED", "handoff_id": handoff_id,
                "reason": "durable_work_order_readback_required"}
    order_payload = orders[0].get("payload") if isinstance(orders[0].get("payload"), dict) else {}
    if order_payload.get("handoff_id") != handoff_id or order_payload.get("goal_id") != receiver_goal_id:
        return {"status": "ACKNOWLEDGMENT_REJECTED", "handoff_id": handoff_id,
                "reason": "work_order_ownership_mismatch"}
    payload["acknowledgement"] = {"by": acknowledged_by, "at": now, "note": note}
    return _transition(handoff_id, (DELIVERED, ACKNOWLEDGED), {
        "status": ACKNOWLEDGED, "acknowledged_at": now, "payload": payload,
    })


def start_processing(handoff_id: str) -> dict[str, Any]:
    return _transition(handoff_id, (ACKNOWLEDGED, FAILED_RETRYABLE), {
        "status": PROCESSING, "processing_started_at": utc_now()})


def record_result(handoff_id: str, *, ok: bool, result_ref: str | None = None,
                  error: str | None = None) -> dict[str, Any]:
    """Terminal or retryable completion with an explicit retry ceiling."""
    current = get_handoff(handoff_id) or {}
    attempts = int(current.get("retry_count") or 0)
    if ok:
        return _transition(handoff_id, (PROCESSING,), {
            "status": COMPLETED, "processed_at": utc_now(),
            "processing_result_ref": result_ref, "last_error": None})
    exhausted = attempts + 1 >= MAX_RETRY_COUNT
    return _transition(handoff_id, (PROCESSING,), {
        "status": FAILED_FINAL if exhausted else FAILED_RETRYABLE,
        "processed_at": utc_now(),
        "retry_count": attempts + 1,
        "last_error": (error or "unspecified failure")[:800],
        "processing_result_ref": result_ref,
    })


def write_receipt(handoff_id: str, receipt: dict[str, Any]) -> str:
    RECEIPT_DIR.mkdir(parents=True, exist_ok=True)
    path = RECEIPT_DIR / f"{handoff_id}.json"
    path.write_text(json.dumps(receipt, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    return str(path.relative_to(ROOT))


def get_receipt(handoff_id: str) -> dict[str, Any] | None:
    path = RECEIPT_DIR / f"{handoff_id}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except ValueError:
        return None


def record_direct_message(*, source_department: str, target_department: str, topic: str,
                          message: str, channel: str, logical_key: str,
                          delivery_ref: str | None = None) -> dict[str, Any]:
    """A direct department message is only allowed alongside a durable receipt.

    The canonical handoff row is written first and its id is embedded in the
    message, so the direct channel is an accelerator, never the only record.
    """
    handoff = create_handoff(
        source_department=source_department, target_department=target_department,
        handoff_type="DIRECT_MESSAGE", topic=topic, logical_key=logical_key,
        payload={"channel": channel, "message": message, "delivery_ref": delivery_ref},
        source_ids=[logical_key])
    return {
        "durable_receipt": handoff,
        "direct_send_permitted": handoff.get("created") or handoff.get("status") == "DUPLICATE_SUPPRESSED",
        "handoff_id": handoff.get("handoff_id"),
        "rule": "DIRECT_MESSAGE_REQUIRES_DURABLE_HANDOFF_RECEIPT",
    }


if __name__ == "__main__":
    print(json.dumps({"table": TABLE, "configured": configured(), "status_model": list(STATUS_MODEL),
                      "dedupe": "deterministic_content_key + database unique index"}, indent=2))
