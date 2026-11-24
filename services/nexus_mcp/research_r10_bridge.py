"""Bounded Research R10 tools exposed through the shared Nexus MCP gateway."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone
from .gateway_receipts import record as record_gateway_receipt
from typing import Any

BASE_URL = "http://127.0.0.1:18766/v1/research/"
OPERATIONS = {
    "start", "status", "result", "continue", "cancel",
    "search_library", "completion_events",
}
WRITE_OPERATIONS = {"start", "continue", "cancel", "completion_events"}
MAX_REQUEST_BYTES = 16_384
MAX_RESPONSE_BYTES = 65_536


def call(operation: str, gateway_request_id: str, correlation_id: str,
         payload: dict[str, Any] | None = None) -> dict[str, Any]:
    if operation not in OPERATIONS:
        raise ValueError("R10_OPERATION_NOT_ALLOWLISTED")
    for label, value in (("gateway_request_id", gateway_request_id), ("correlation_id", correlation_id)):
        if not isinstance(value, str) or not value or len(value) > 128:
            raise ValueError(label.upper() + "_INVALID")
    body = dict(payload or {})
    if len(json.dumps(body, separators=(",", ":")).encode()) > MAX_REQUEST_BYTES:
        raise ValueError("R10_REQUEST_TOO_LARGE")
    if operation == "start":
        body.setdefault("request_id", gateway_request_id)
        if not body.get("idempotency_key"):
            raise ValueError("R10_IDEMPOTENCY_KEY_REQUIRED")
    elif operation == "continue":
        body.setdefault("request_id", gateway_request_id)
        if not body.get("job_id"):
            raise ValueError("R10_JOB_ID_REQUIRED")
    elif operation in {"result", "cancel", "completion_events"} and not body.get("job_id"):
        raise ValueError("R10_JOB_ID_REQUIRED")

    token = os.environ.get("NEXUS_MCP_BRIDGE_TOKEN", "")
    if len(token) < 32:
        raise RuntimeError("R10_BRIDGE_CREDENTIAL_UNAVAILABLE")
    encoded = json.dumps(body, separators=(",", ":")).encode()
    started_at = datetime.now(timezone.utc).isoformat()
    request = urllib.request.Request(
        BASE_URL + operation,
        data=encoded,
        headers={
            "Authorization": "Bearer " + token,
            "X-Nexus-Caller": "NOVA_NEXUS",
            "X-Nexus-Capability": "research",
            "X-Nexus-Gateway-Request-ID": gateway_request_id,
            "X-Nexus-Correlation-ID": correlation_id,
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=12) as response:
            if response.status not in ({200, 202} if operation in {"start", "continue"} else {200}):
                raise RuntimeError("R10_HTTP_STATUS_UNEXPECTED")
            raw = response.read(MAX_RESPONSE_BYTES + 1)
    except urllib.error.HTTPError as exc:
        if exc.code == 401:
            raise PermissionError("R10_AUTHENTICATION_FAILED") from None
        if exc.code == 403:
            raise PermissionError("R10_CAPABILITY_DENIED") from None
        if exc.code == 429:
            raise RuntimeError("R10_RATE_LIMITED") from None
        if exc.code >= 500:
            raise RuntimeError("R10_ENGINE_FAILURE") from None
        raise ValueError("R10_REQUEST_REJECTED") from None
    except (urllib.error.URLError, TimeoutError) as exc:
        raise RuntimeError("R10_ENGINE_UNAVAILABLE") from exc
    if len(raw) > MAX_RESPONSE_BYTES:
        raise RuntimeError("R10_RESPONSE_TOO_LARGE")
    try:
        result = json.loads(raw)
    except (ValueError, TypeError) as exc:
        raise RuntimeError("R10_RESPONSE_INVALID") from exc
    if not isinstance(result, dict):
        raise RuntimeError("R10_RESPONSE_INVALID")
    result["gateway_request_id"] = gateway_request_id
    result["correlation_id"] = correlation_id
    result["engine"] = "RESEARCH_R10"
    result["operation"] = "research." + operation
    result.setdefault("schema", "nexus.gateway.response.v1")
    result.setdefault("parent_request_id", None)
    result.setdefault("status", "ACCEPTED" if operation in {"start", "continue"} and result.get("accepted") else "COMPLETED")
    result.setdefault("result_summary", {k: result[k] for k in ("summary", "status", "job_id") if k in result})
    result.setdefault("evidence_refs", result.get("evidence_refs", []))
    receipt = result.get("receipt")
    result.setdefault("engine_receipt_id", receipt.get("receipt_id") if isinstance(receipt, dict) else None)
    result.setdefault("approval_required", bool(result.get("approval_required", False)))
    result.setdefault("error_class", None)
    result.setdefault("retryable", False)
    result.setdefault("started_at", started_at)
    result.setdefault("completed_at", datetime.now(timezone.utc).isoformat())
    return result


def register(mcp) -> None:
    from .auth import authorize_action, authorize_read

    def checked(tool_name: str, operation: str, gateway_request_id: str,
                correlation_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        (authorize_action if operation in WRITE_OPERATIONS else authorize_read)(tool_name)
        started_at = datetime.now(timezone.utc).isoformat()
        result = call(operation, gateway_request_id, correlation_id, payload)
        receipt = record_gateway_receipt(
            request_id=gateway_request_id, correlation_id=correlation_id,
            engine="RESEARCH_R10", operation="research." + operation,
            authorization="SAFE_ACTION" if operation in WRITE_OPERATIONS else "READ_ONLY",
            result=result, started_at=started_at,
        )
        result["receipt_id"] = receipt["receipt_id"]
        result["gateway_receipt"] = receipt
        return result

    @mcp.tool(name="nexus_research_start", description="Start one bounded Research R10 job through the shared Nexus gateway. Requires a unique gateway_request_id, correlation_id, and idempotency_key. Research executes on Mac; the tool returns a compact job receipt.")
    def start(gateway_request_id: str, correlation_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return checked("nexus_research_start", "start", gateway_request_id, correlation_id, payload)

    @mcp.tool(name="nexus_research_status", description="Read Research R10 status through the shared Nexus gateway. Provide a job_id for exact status or omit it for a bounded recent-job list.")
    def status(gateway_request_id: str, correlation_id: str, job_id: str = "") -> dict[str, Any]:
        return checked("nexus_research_status", "status", gateway_request_id, correlation_id, {"job_id": job_id} if job_id else {})

    @mcp.tool(name="nexus_research_result", description="Read a compact attributable result for one exact Research R10 job.")
    def result(gateway_request_id: str, correlation_id: str, job_id: str) -> dict[str, Any]:
        return checked("nexus_research_result", "result", gateway_request_id, correlation_id, {"job_id": job_id})

    @mcp.tool(name="nexus_research_continue", description="Continue one existing Research R10 job. The exact job ID is required; the same job is resumed.")
    def continue_job(gateway_request_id: str, correlation_id: str, job_id: str) -> dict[str, Any]:
        return checked("nexus_research_continue", "continue", gateway_request_id, correlation_id, {"job_id": job_id})

    @mcp.tool(name="nexus_research_cancel", description="Cancel one exact Research R10 job. This is a bounded Research action and does not access the host system.")
    def cancel(gateway_request_id: str, correlation_id: str, job_id: str) -> dict[str, Any]:
        return checked("nexus_research_cancel", "cancel", gateway_request_id, correlation_id, {"job_id": job_id})

    @mcp.tool(name="nexus_research_search_library", description="Search validated local Research R10 insights. Read only; does not create a Research job.")
    def search_library(gateway_request_id: str, correlation_id: str, query: str, limit: int = 10) -> dict[str, Any]:
        if not isinstance(query, str) or len(query) > 256:
            raise ValueError("R10_QUERY_INVALID")
        return checked("nexus_research_search_library", "search_library", gateway_request_id, correlation_id,
                    {"query": query, "limit": max(1, min(int(limit), 20))})

    @mcp.tool(name="nexus_research_completion_events", description="Consume at most the pending completion event for one exact Research R10 job. Returns the existing completion receipt and does not start or duplicate work.")
    def completion_events(gateway_request_id: str, correlation_id: str, job_id: str) -> dict[str, Any]:
        return checked("nexus_research_completion_events", "completion_events", gateway_request_id, correlation_id, {"job_id": job_id})
