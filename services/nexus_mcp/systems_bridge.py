"""Narrow HMAC-authenticated client for the local Systems S1 API."""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone

BASE_URL = "http://127.0.0.1:18770/v1/request"
ENVIRONMENTS = {"MAC_MINI", "ORACLE", "SUPABASE", "SAAS_API", "DISPOSABLE_SANDBOX"}
READ_OPERATIONS = {
    "health": "systems.health", "status": "systems.status",
    "incidents": "systems.incidents", "incident": "systems.incident",
    "version_status": "systems.version_status", "environment_status": "systems.environment_status",
    "technology_status": "systems.technology_status", "service_status": "systems.service_status",
    "release_status": "systems.release_status", "receipt": "systems.receipt",
    "workload_placement": "systems.workload_placement",
}


def request(operation: str, *, environment_id: str = "MAC_MINI", service_id: str | None = None,
            reason: str = "Nova Systems query", idempotency_key: str | None = None,
            approval_context: dict | None = None, payload: dict | None = None,
            gateway_request_id: str | None = None, correlation_id: str | None = None) -> dict:
    if operation not in set(READ_OPERATIONS.values()) | {"systems.restart_safe", "systems.rollback", "systems.technology_handoff", "systems.install_technology", "systems.upgrade_component", "systems.safe_cleanup", "systems.rotate_credential", "systems.prepare_kaggle_job", "systems.approval_request", "systems.approval_decide", "systems.approval_status", "systems.approval_validate"}:
        raise ValueError("SYSTEMS_OPERATION_NOT_ALLOWLISTED")
    if environment_id not in ENVIRONMENTS:
        raise ValueError("SYSTEMS_ENVIRONMENT_NOT_ALLOWLISTED")
    if service_id is not None and (not isinstance(service_id, str) or not service_id or len(service_id) > 128):
        raise ValueError("SYSTEMS_SERVICE_ID_INVALID")
    if payload is not None and (not isinstance(payload, dict) or len(json.dumps(payload)) > 4096):
        raise ValueError("SYSTEMS_PAYLOAD_INVALID")
    explicit = os.environ.get("NEXUS_SYSTEMS_BRIDGE_SECRET", "")
    token = os.environ.get("NEXUS_MCP_BRIDGE_TOKEN", "")
    secret = explicit.encode() if explicit else hmac.new(token.encode(), b"nexus.systems.bridge.v1", hashlib.sha256).digest() if token else b""
    if len(secret) < 32:
        raise RuntimeError("SYSTEMS_BRIDGE_SECRET_UNAVAILABLE")
    gateway_request_id = gateway_request_id or ("nova-gateway-" + uuid.uuid4().hex)
    correlation_id = correlation_id or gateway_request_id
    for label, value in (("gateway_request_id", gateway_request_id), ("correlation_id", correlation_id)):
        if not isinstance(value, str) or not value or len(value) > 128:
            raise ValueError("SYSTEMS_" + label.upper() + "_INVALID")
    started_at = datetime.now(timezone.utc).isoformat()
    body_obj = {
        # Systems receipts use this request ID, which makes the gateway request
        # discoverable from the durable receipt without changing the S1 API.
        "request_id": gateway_request_id,
        "caller": "NOVA_NEXUS", "operation": operation, "environment_id": environment_id,
        "scope": "nova-typed-systems-bridge", "idempotency_key": idempotency_key or uuid.uuid4().hex,
        "approval_context": approval_context or {}, "reason": reason[:300], "payload": payload or {},
    }
    if service_id is not None:
        body_obj["service_id"] = service_id
    if (operation in {"systems.restart_safe", "systems.rollback"}
            and environment_id == "DISPOSABLE_SANDBOX"
            and isinstance(service_id, str) and service_id.startswith("test-")):
        # This fixed marker is only issued for registered disposable fixtures;
        # no caller-supplied approval context can authorize production work.
        body_obj["approval_context"] = {"approval": "DISPOSABLE_TEST_APPROVED"}
    body = json.dumps(body_obj, separators=(",", ":")).encode()
    if len(body) > 8192:
        raise ValueError("SYSTEMS_REQUEST_TOO_LARGE")
    timestamp = str(int(time.time()))
    nonce = uuid.uuid4().hex
    signing = timestamp.encode() + b"." + nonce.encode() + b"." + body
    signature = hmac.new(secret, signing, hashlib.sha256).hexdigest()
    req = urllib.request.Request(BASE_URL, data=body, headers={
        "Content-Type": "application/json", "X-Nexus-Timestamp": timestamp,
        "X-Nexus-Nonce": nonce, "X-Nexus-Signature": signature,
    })
    try:
        # A complete deterministic health scan includes a bounded SSH probe
        # to Oracle and can exceed the ordinary read timeout. Keep that one
        # operation bounded at 45 seconds; other typed calls remain at 10.
        bridge_timeout = 58 if operation == "systems.health" else 1800 if operation == "systems.install_technology" else 30 if operation == "systems.technology_handoff" else 10
        with urllib.request.urlopen(req, timeout=bridge_timeout) as response:
            if response.status != 200:
                raise RuntimeError("SYSTEMS_BRIDGE_HTTP_ERROR")
            raw = response.read(65537)
    except (urllib.error.URLError, TimeoutError) as exc:
        raise RuntimeError("SYSTEMS_BRIDGE_UNAVAILABLE") from exc
    if len(raw) > 65536:
        raise RuntimeError("SYSTEMS_BRIDGE_RESPONSE_TOO_LARGE")
    value = json.loads(raw)
    result = value.get("result") if isinstance(value, dict) else None
    if not isinstance(result, dict):
        raise RuntimeError("SYSTEMS_BRIDGE_RESPONSE_INVALID")
    receipt = result.get("receipt")
    engine_status = result.get("status")
    return {**result, "schema": "nexus.gateway.response.v1",
            "gateway_request_id": gateway_request_id,
            "parent_request_id": None, "correlation_id": correlation_id,
            "engine": "SYSTEMS_S1", "operation": operation,
            "engine_status": engine_status,
            "status": "APPROVAL_REQUIRED" if result.get("approval_required") else "COMPLETED",
            "result_summary": result.get("result_summary") or {
                k: result[k] for k in ("status", "health", "overall_status") if k in result
            },
            "evidence_refs": result.get("evidence_refs", []),
            "receipt_id": result.get("receipt_id") or (receipt.get("receipt_id") if isinstance(receipt, dict) else None),
            "approval_required": bool(result.get("approval_required", False)),
            "error_class": result.get("error_class"),
            "retryable": bool(result.get("retryable", False)),
            "started_at": started_at,
            "completed_at": datetime.now(timezone.utc).isoformat()}
