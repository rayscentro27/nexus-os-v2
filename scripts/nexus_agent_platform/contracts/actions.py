"""Certified action handlers for Nexus Hermes.

Every action handler:
1. Validates required fields from TaskSpec
2. Generates idempotency key from mission_id
3. Checks for duplicate execution
4. Executes through canonical provider
5. Stores execution receipt
6. Returns typed CapabilityResult
7. Never fabricates success
"""

from __future__ import annotations

import hashlib
import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .typed import (
    CapabilityResult,
    ResultStatus,
    Scope,
    SourceInfo,
    Authorization,
    ExecutionInfo,
    ok_result,
    error_result,
    empty_result,
)


# ─── Idempotency ────────────────────────────────────────────

def _make_idempotency_key(mission_id: str, capability_id: str, version: str) -> str:
    """Generate deterministic idempotency key from mission + capability."""
    raw = f"{mission_id}:{capability_id}:{version}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def _check_idempotency(key: str, receipt_dir: str) -> Optional[Dict[str, Any]]:
    """Check if an action was already executed. Returns receipt or None."""
    receipt_path = os.path.join(receipt_dir, f"{key}.json")
    if os.path.exists(receipt_path):
        with open(receipt_path) as f:
            return json.load(f)
    return None


def _store_receipt(key: str, receipt: Dict[str, Any], receipt_dir: str) -> None:
    """Store execution receipt for idempotency."""
    os.makedirs(receipt_dir, exist_ok=True)
    receipt_path = os.path.join(receipt_dir, f"{key}.json")
    with open(receipt_path, "w") as f:
        json.dump(receipt, f, indent=2)


# ─── Email Action ────────────────────────────────────────────

RECEIPTS_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "reports", "runtime", "action_receipts"
)


def send_approved_email(
    taskspec: Dict[str, Any],
    mission_id: str,
    tenant: str = "goclear",
) -> CapabilityResult:
    """Send an approved email via Resend.

    Required fields in taskspec:
    - recipient: email address
    - subject: email subject
    - body: email body (plain text or HTML)

    Optional fields:
    - reply_to: reply-to address
    - template_id: Resend template ID
    - related_mission: linked mission ID
    """
    capability_id = "send_approved_email"
    version = "v1"
    handler_id = "actions.send_approved_email"

    # Validate required fields
    recipient = taskspec.get("recipient", "").strip()
    subject = taskspec.get("subject", "").strip()
    body = taskspec.get("body", "").strip()

    missing = []
    if not recipient:
        missing.append("recipient")
    if not subject:
        missing.append("subject")
    if not body:
        missing.append("body")

    if missing:
        return error_result(
            capability_id=capability_id,
            capability_version=version,
            definition_id="",
            error=f"Missing required fields: {', '.join(missing)}",
            status=ResultStatus.INVALID.value,
            handler_id=handler_id,
            tenant=tenant,
            trace_id=mission_id,
        )

    # Validate email format (basic check)
    if "@" not in recipient or "." not in recipient.split("@")[-1]:
        return error_result(
            capability_id=capability_id,
            capability_version=version,
            definition_id="",
            error="Invalid recipient email format",
            status=ResultStatus.INVALID.value,
            handler_id=handler_id,
            tenant=tenant,
            trace_id=mission_id,
        )

    # Check idempotency
    idempotency_key = _make_idempotency_key(mission_id, capability_id, version)
    existing = _check_idempotency(idempotency_key, RECEIPTS_DIR)
    if existing:
        return CapabilityResult(
            status=existing.get("status", ResultStatus.OK.value),
            capability_id=capability_id,
            capability_version=version,
            definition_id="",
            data=existing.get("data", {}),
            source=SourceInfo(source_id="resend_api", source_type="provider_api"),
            scope=Scope(tenant=tenant),
            authorization=Authorization(decision="allowed"),
            execution=ExecutionInfo(
                handler_id=handler_id,
                fallback_used=False,
                retry_count=0,
            ),
            trace_id=mission_id,
            warnings=["Duplicate execution - returning cached receipt"],
        )

    # Execute via Resend Edge Function
    try:
        import httpx

        supabase_url = os.environ.get("SUPABASE_URL") or os.environ.get("VITE_SUPABASE_URL")
        supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

        if not supabase_url or not supabase_key:
            return error_result(
                capability_id=capability_id,
                capability_version=version,
                definition_id="",
                error="Supabase credentials not configured",
                status=ResultStatus.UNAVAILABLE.value,
                handler_id=handler_id,
                tenant=tenant,
                trace_id=mission_id,
            )

        # Call the send-client-email Edge Function
        url = f"{supabase_url}/functions/v1/send-client-email"
        headers = {
            "Authorization": f"Bearer {supabase_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "to": recipient,
            "subject": subject,
            "body": body,
            "type": "status_update",
            "idempotency_key": idempotency_key,
        }

        response = httpx.post(url, json=payload, headers=headers, timeout=30.0)

        if response.status_code == 200:
            result_data = response.json()
            receipt = {
                "status": ResultStatus.OK.value,
                "provider": "resend",
                "provider_status": "accepted",
                "provider_request_id": result_data.get("id", ""),
                "idempotency_key": idempotency_key,
                "recipient_domain": recipient.split("@")[-1],
                "subject_hash": hashlib.sha256(subject.encode()).hexdigest()[:16],
                "executed_at": datetime.now(timezone.utc).isoformat(),
                "mission_id": mission_id,
            }
            _store_receipt(idempotency_key, receipt, RECEIPTS_DIR)

            return ok_result(
                capability_id=capability_id,
                capability_version=version,
                definition_id="",
                data={
                    "status": "accepted",
                    "provider_request_id": result_data.get("id", ""),
                    "recipient_domain": recipient.split("@")[-1],
                },
                source_id="resend_api",
                source_type="provider_api",
                query_id="POST /functions/v1/send-client-email",
                handler_id=handler_id,
                tenant=tenant,
                trace_id=mission_id,
            )
        else:
            return error_result(
                capability_id=capability_id,
                capability_version=version,
                definition_id="",
                error=f"Provider rejected: HTTP {response.status_code}",
                status=ResultStatus.UNAVAILABLE.value,
                handler_id=handler_id,
                tenant=tenant,
                trace_id=mission_id,
            )

    except httpx.TimeoutException:
        return error_result(
            capability_id=capability_id,
            capability_version=version,
            definition_id="",
            error="Provider timeout",
            status=ResultStatus.UNAVAILABLE.value,
            handler_id=handler_id,
            tenant=tenant,
            trace_id=mission_id,
        )
    except Exception as exc:
        return error_result(
            capability_id=capability_id,
            capability_version=version,
            definition_id="",
            error=f"Execution failed: {str(exc)}",
            status=ResultStatus.UNAVAILABLE.value,
            handler_id=handler_id,
            tenant=tenant,
            trace_id=mission_id,
        )


# ─── Schedule Report Action ──────────────────────────────────

def schedule_report(
    taskspec: Dict[str, Any],
    mission_id: str,
    tenant: str = "goclear",
) -> CapabilityResult:
    """Schedule a report for future execution.

    Required fields in taskspec:
    - report_definition: report type or template
    - execution_time: ISO 8601 datetime
    - timezone: IANA timezone (default: America/Phoenix)

    Optional fields:
    - recurrence: none, daily, weekly, monthly
    - delivery_channel: telegram (default)
    - delivery_recipient: chat ID or channel
    - report_format: executive_brief, technical_details
    """
    capability_id = "schedule_report"
    version = "v1"
    handler_id = "actions.schedule_report"

    # Validate required fields
    report_def = taskspec.get("report_definition", "").strip()
    execution_time = taskspec.get("execution_time", "").strip()
    tz = taskspec.get("timezone", "America/Phoenix").strip()

    missing = []
    if not report_def:
        missing.append("report_definition")
    if not execution_time:
        missing.append("execution_time")

    if missing:
        return error_result(
            capability_id=capability_id,
            capability_version=version,
            definition_id="",
            error=f"Missing required fields: {', '.join(missing)}",
            status=ResultStatus.INVALID.value,
            handler_id=handler_id,
            tenant=tenant,
            trace_id=mission_id,
        )

    # Parse execution time
    try:
        exec_dt = datetime.fromisoformat(execution_time.replace("Z", "+00:00"))
    except ValueError:
        return error_result(
            capability_id=capability_id,
            capability_version=version,
            definition_id="",
            error="Invalid execution_time format (use ISO 8601)",
            status=ResultStatus.INVALID.value,
            handler_id=handler_id,
            tenant=tenant,
            trace_id=mission_id,
        )

    # Check idempotency
    idempotency_key = _make_idempotency_key(mission_id, capability_id, version)
    existing = _check_idempotency(idempotency_key, RECEIPTS_DIR)
    if existing:
        return CapabilityResult(
            status=existing.get("status", ResultStatus.OK.value),
            capability_id=capability_id,
            capability_version=version,
            definition_id="",
            data=existing.get("data", {}),
            source=SourceInfo(source_id="temporal_adapter", source_type="temporal_workflow"),
            scope=Scope(tenant=tenant),
            authorization=Authorization(decision="allowed"),
            execution=ExecutionInfo(handler_id=handler_id),
            trace_id=mission_id,
            warnings=["Duplicate execution - returning cached receipt"],
        )

    # Store schedule definition
    schedule_id = f"sch_{uuid.uuid4().hex[:12]}"
    receipt = {
        "status": ResultStatus.OK.value,
        "schedule_id": schedule_id,
        "report_definition": report_def,
        "execution_time": exec_dt.isoformat(),
        "timezone": tz,
        "recurrence": taskspec.get("recurrence", "none"),
        "delivery_channel": taskspec.get("delivery_channel", "telegram"),
        "idempotency_key": idempotency_key,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "mission_id": mission_id,
        "workflow_status": "scheduled",
    }
    _store_receipt(idempotency_key, receipt, RECEIPTS_DIR)

    # Also store the schedule definition for the worker to pick up
    schedules_dir = os.path.join(
        os.path.dirname(__file__), "..", "..", "data", "runtime", "scheduled_reports"
    )
    os.makedirs(schedules_dir, exist_ok=True)
    schedule_path = os.path.join(schedules_dir, f"{schedule_id}.json")
    with open(schedule_path, "w") as f:
        json.dump(receipt, f, indent=2)

    return ok_result(
        capability_id=capability_id,
        capability_version=version,
        definition_id="",
        data={
            "schedule_id": schedule_id,
            "execution_time": exec_dt.isoformat(),
            "timezone": tz,
            "report_definition": report_def,
            "status": "scheduled",
        },
        source_id="temporal_adapter",
        source_type="temporal_workflow",
        query_id=f"schedule:{schedule_id}",
        handler_id=handler_id,
        tenant=tenant,
        trace_id=mission_id,
    )


# ─── Work Order Action ──────────────────────────────────────

def create_work_order(
    taskspec: Dict[str, Any],
    mission_id: str,
    tenant: str = "goclear",
) -> CapabilityResult:
    """Create a work order in Supabase.

    Required fields in taskspec:
    - title: work order title
    - description: what needs to be done
    - source_context: origin of the request

    Optional fields:
    - owner: assigned team/person
    - priority: low, medium, high, critical
    - due_date: ISO 8601 date
    - linked_opportunity: opportunity ID
    - linked_research: research run ID
    - linked_report: report ID
    - assigned_agent: hermes, alpha, nexus
    """
    capability_id = "create_work_order"
    version = "v1"
    handler_id = "actions.create_work_order"

    # Validate required fields
    title = taskspec.get("title", "").strip()
    description = taskspec.get("description", "").strip()
    source_context = taskspec.get("source_context", "").strip()

    missing = []
    if not title:
        missing.append("title")
    if not description:
        missing.append("description")
    if not source_context:
        missing.append("source_context")

    if missing:
        return error_result(
            capability_id=capability_id,
            capability_version=version,
            definition_id="",
            error=f"Missing required fields: {', '.join(missing)}",
            status=ResultStatus.INVALID.value,
            handler_id=handler_id,
            tenant=tenant,
            trace_id=mission_id,
        )

    # Check idempotency
    idempotency_key = _make_idempotency_key(mission_id, capability_id, version)
    existing = _check_idempotency(idempotency_key, RECEIPTS_DIR)
    if existing:
        return CapabilityResult(
            status=existing.get("status", ResultStatus.OK.value),
            capability_id=capability_id,
            capability_version=version,
            definition_id="",
            data=existing.get("data", {}),
            source=SourceInfo(source_id="supabase", source_type="supabase_table"),
            scope=Scope(tenant=tenant),
            authorization=Authorization(decision="allowed"),
            execution=ExecutionInfo(handler_id=handler_id),
            trace_id=mission_id,
            warnings=["Duplicate execution - returning cached receipt"],
        )

    # Create work order via Supabase
    try:
        import httpx

        supabase_url = os.environ.get("SUPABASE_URL") or os.environ.get("VITE_SUPABASE_URL")
        supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

        if not supabase_url or not supabase_key:
            return error_result(
                capability_id=capability_id,
                capability_version=version,
                definition_id="",
                error="Supabase credentials not configured",
                status=ResultStatus.UNAVAILABLE.value,
                handler_id=handler_id,
                tenant=tenant,
                trace_id=mission_id,
            )

        work_order_id = f"wo_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()

        # Insert into task_requests table (closest to work orders)
        url = f"{supabase_url}/rest/v1/task_requests"
        headers = {
            "Authorization": f"Bearer {supabase_key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }
        payload = {
            "workspace_id": tenant,
            "task_type": "work_order",
            "requested_by": "hermes",
            "approved_by_ray": False,
            "sensitivity": taskspec.get("priority", "medium"),
            "assigned_worker_type": taskspec.get("assigned_agent", "nexus"),
            "hermes_visibility": "status_only",
            "status": "pending",
            "payload": {
                "work_order_id": work_order_id,
                "title": title,
                "description": description,
                "source_context": source_context,
                "owner": taskspec.get("owner", ""),
                "priority": taskspec.get("priority", "medium"),
                "due_date": taskspec.get("due_date", ""),
                "linked_opportunity": taskspec.get("linked_opportunity", ""),
                "linked_research": taskspec.get("linked_research", ""),
                "linked_report": taskspec.get("linked_report", ""),
                "idempotency_key": idempotency_key,
                "created_at": now,
            },
        }

        response = httpx.post(url, json=payload, headers=headers, timeout=30.0)

        if response.status_code in (200, 201):
            result_data = response.json()
            record_id = result_data[0].get("id") if result_data else ""

            receipt = {
                "status": ResultStatus.OK.value,
                "work_order_id": work_order_id,
                "record_id": record_id,
                "title": title,
                "status": "pending",
                "idempotency_key": idempotency_key,
                "created_at": now,
                "mission_id": mission_id,
            }
            _store_receipt(idempotency_key, receipt, RECEIPTS_DIR)

            return ok_result(
                capability_id=capability_id,
                capability_version=version,
                definition_id="",
                data={
                    "work_order_id": work_order_id,
                    "record_id": record_id,
                    "title": title,
                    "status": "pending",
                },
                source_id="supabase",
                source_type="supabase_table",
                query_id="POST /rest/v1/task_requests",
                handler_id=handler_id,
                tenant=tenant,
                trace_id=mission_id,
            )
        else:
            return error_result(
                capability_id=capability_id,
                capability_version=version,
                definition_id="",
                error=f"Storage rejected: HTTP {response.status_code}",
                status=ResultStatus.UNAVAILABLE.value,
                handler_id=handler_id,
                tenant=tenant,
                trace_id=mission_id,
            )

    except httpx.TimeoutException:
        return error_result(
            capability_id=capability_id,
            capability_version=version,
            definition_id="",
            error="Storage timeout",
            status=ResultStatus.UNAVAILABLE.value,
            handler_id=handler_id,
            tenant=tenant,
            trace_id=mission_id,
        )
    except Exception as exc:
        return error_result(
            capability_id=capability_id,
            capability_version=version,
            definition_id="",
            error=f"Execution failed: {str(exc)}",
            status=ResultStatus.UNAVAILABLE.value,
            handler_id=handler_id,
            tenant=tenant,
            trace_id=mission_id,
        )
