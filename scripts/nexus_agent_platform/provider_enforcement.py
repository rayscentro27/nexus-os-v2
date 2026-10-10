"""Small fail-closed boundary for metered and external provider actions."""
from __future__ import annotations

import os
import platform
import time
import uuid
import inspect
from functools import wraps
from datetime import datetime, timezone
from typing import Any, Callable

from .resource_spend_governor import GovernanceDenied, default_store


def execute(provider: str, service: str, action_type: str, estimate: dict[str, Any],
            operation: Callable[[], Any], *, job_id: str | None = None,
            job_type: str | None = None, project_id: str | None = None,
            correlation_id: str | None = None, purpose: str | None = None,
            actual_usage: Callable[[Any], dict[str, Any]] | None = None,
            external_ref: Callable[[Any], str | None] | None = None) -> Any:
    """Authorize, reserve, execute, reconcile, and leave a compact footprint.

    Missing job context is intentionally represented as an ad-hoc operation;
    default-deny governor policy still applies. Provider exceptions release the
    reservation and write a failure footprint before propagating.
    """
    job_id = job_id or os.environ.get("NEXUS_DURABLE_JOB_ID")
    if not job_id:
        raise GovernanceDenied("HUMAN_APPROVAL_REQUIRED", "DURABLE_JOB_ID_REQUIRED")
    correlation_id = correlation_id or os.environ.get("NEXUS_CORRELATION_ID")
    if not correlation_id:
        raise GovernanceDenied("HUMAN_APPROVAL_REQUIRED", "CORRELATION_ID_REQUIRED")
    if not os.environ.get("NEXUS_DEPARTMENT"):
        raise GovernanceDenied("HUMAN_APPROVAL_REQUIRED", "DEPARTMENT_REQUIRED")
    job_type = job_type or os.environ.get("NEXUS_JOB_TYPE", "ADHOC_PROVIDER_ACTION")
    store = default_store()
    started = datetime.now(timezone.utc)
    tick = time.monotonic()
    try:
        reservation = store.reserve(provider, service, job_type, job_id, estimate,
                                   purpose=purpose or f"{action_type}:{job_id}", project_id=project_id)
    except GovernanceDenied as exc:
        store.record_footprint({"project_id": project_id or os.environ.get("NEXUS_PROJECT_ID", "NEXUS"), "job_id": job_id,
            "correlation_id": correlation_id, "department": os.environ.get("NEXUS_DEPARTMENT"),
            "job_type": job_type, "provider": provider, "service": service,
            "action_type": action_type, "host": platform.node(), "environment": "production-off" if os.environ.get("NEXUS_DURABLE_JOB_ID") else "ad-hoc",
            "process_id": os.getpid(), "parent_process_id": os.getppid(), "worker_type": "PROVIDER_BOUNDARY",
            "start_time": started.isoformat(), "end_time": datetime.now(timezone.utc).isoformat(), "duration_seconds": 0,
            "request_count": 0, "response_bytes": 0, "tokens": 0, "gpu_seconds": 0,
            "estimated_cost": estimate.get("cost"), "actual_cost": None, "reservation_amount": 0,
            "final_usage": {}, "artifact_refs": [], "handoff_ids": [], "next_job_ids": [],
            "email_actions": 0, "social_actions": 0, "browser_actions": 0,
            "failure_codes": [exc.code], "final_state": exc.state, "recovery_action": "provider_not_called"})
        raise
    actual: dict[str, Any] = {}
    state, failure = "FAILED_RETRYABLE", ["PROVIDER_ACTION_INTERRUPTED"]
    try:
        result = operation()
        actual = actual_usage(result) if actual_usage else {k: v for k, v in estimate.items() if k not in {"billable", "budget_period"}}
        store.reconcile(reservation["reservation_id"], actual)
        state = "COMPLETED"
        failure = []
        return result
    except Exception as exc:
        if not actual:
            actual = {k: v for k, v in estimate.items() if k not in {"billable", "budget_period"}}
        try:
            store.reconcile(reservation["reservation_id"], actual)
        except Exception:
            store.release(reservation["reservation_id"])
        state = "FAILED_RETRYABLE"
        failure = [type(exc).__name__]
        raise
    finally:
        end = datetime.now(timezone.utc)
        store.record_footprint({"project_id": project_id or os.environ.get("NEXUS_PROJECT_ID", "NEXUS"), "job_id": job_id,
            "correlation_id": correlation_id, "department": os.environ.get("NEXUS_DEPARTMENT"),
            "job_type": job_type, "provider": provider, "service": service,
            "action_type": action_type, "host": platform.node(), "environment": "production-off" if os.environ.get("NEXUS_DURABLE_JOB_ID") else "ad-hoc",
            "process_id": os.getpid(), "parent_process_id": os.getppid(), "worker_type": "PROVIDER_BOUNDARY",
            "start_time": started.isoformat(), "end_time": end.isoformat(),
            "duration_seconds": round(time.monotonic() - tick, 3),
            "request_count": estimate.get("requests", 0), "response_bytes": estimate.get("bytes", 0),
            "tokens": estimate.get("tokens", 0), "gpu_seconds": estimate.get("gpu_seconds", 0),
            "runtime_seconds": estimate.get("runtime_seconds", 0), "estimated_cost": estimate.get("cost"),
            "actual_cost": actual.get("cost"), "reservation_amount": estimate,
            "final_usage": actual, "files_created": [], "artifact_refs": [], "handoff_ids": [], "next_job_ids": [],
            "email_actions": int(provider == "EMAIL_PROVIDER" and state == "COMPLETED"),
            "social_actions": int(provider == "SOCIAL_MEDIA_EXTERNAL_ACTIONS" and state == "COMPLETED"),
            "browser_actions": int(provider == "BROWSER_EXTERNAL_SERVICES" and state == "COMPLETED"),
            "external_action_refs": [external_ref(result)] if state == "COMPLETED" and external_ref and external_ref(result) else [],
            "failure_codes": failure, "retry_count": 0, "final_state": state})


async def execute_async(provider: str, service: str, action_type: str, estimate: dict[str, Any],
                        operation: Callable[[], Any], **context: Any) -> Any:
    """Async twin of :func:`execute` for async provider SDKs."""
    job_id = context.pop("job_id", None) or os.environ.get("NEXUS_DURABLE_JOB_ID")
    if not job_id:
        raise GovernanceDenied("HUMAN_APPROVAL_REQUIRED", "DURABLE_JOB_ID_REQUIRED")
    correlation_id = context.pop("correlation_id", None) or os.environ.get("NEXUS_CORRELATION_ID")
    if not correlation_id:
        raise GovernanceDenied("HUMAN_APPROVAL_REQUIRED", "CORRELATION_ID_REQUIRED")
    if not os.environ.get("NEXUS_DEPARTMENT"):
        raise GovernanceDenied("HUMAN_APPROVAL_REQUIRED", "DEPARTMENT_REQUIRED")
    job_type = context.pop("job_type", None) or os.environ.get("NEXUS_JOB_TYPE", "ADHOC_PROVIDER_ACTION")
    project_id = context.pop("project_id", None)
    purpose = context.pop("purpose", None) or f"{action_type}:{job_id}"
    store = default_store()
    started = datetime.now(timezone.utc); tick = time.monotonic()
    try:
        reservation = store.reserve(provider, service, job_type, job_id, estimate,
            purpose=purpose, project_id=project_id)
    except GovernanceDenied as exc:
        store.record_footprint({"project_id":project_id or os.environ.get("NEXUS_PROJECT_ID", "NEXUS"),"job_id":job_id,"correlation_id":correlation_id,
            "job_type":job_type,"provider":provider,"service":service,"action_type":action_type,
            "host":platform.node(),"process_id":os.getpid(),"parent_process_id":os.getppid(),"worker_type":"PROVIDER_BOUNDARY","start_time":started.isoformat(),
            "end_time":datetime.now(timezone.utc).isoformat(),"failure_codes":[exc.code],
            "final_state":exc.state,"recovery_action":"provider_not_called"})
        raise
    result = None
    actual: dict[str, Any] = {}
    state, failure = "FAILED_RETRYABLE", ["PROVIDER_ACTION_INTERRUPTED"]
    try:
        result = operation()
        if inspect.isawaitable(result): result = await result
        usage_fn = context.pop("actual_usage", None)
        actual = usage_fn(result) if usage_fn else {k:v for k,v in estimate.items() if k not in {"billable","budget_period"}}
        store.reconcile(reservation["reservation_id"], actual)
        state, failure = "COMPLETED", []
        return result
    except Exception as exc:
        actual = {k:v for k,v in estimate.items() if k not in {"billable","budget_period"}}
        try: store.reconcile(reservation["reservation_id"],actual)
        except Exception: store.release(reservation["reservation_id"])
        state, failure = "FAILED_RETRYABLE", [type(exc).__name__]
        raise
    finally:
        end=datetime.now(timezone.utc)
        store.record_footprint({"project_id":project_id or os.environ.get("NEXUS_PROJECT_ID", "NEXUS"),"job_id":job_id,"correlation_id":correlation_id,
            "job_type":job_type,"provider":provider,"service":service,"action_type":action_type,
            "host":platform.node(),"process_id":os.getpid(),"start_time":started.isoformat(),"end_time":end.isoformat(),
            "duration_seconds":round(time.monotonic()-tick,3),"request_count":estimate.get("requests",0),
            "tokens":estimate.get("tokens",0),"estimated_cost":estimate.get("cost"),
            "actual_cost":actual.get("cost"),"reservation_amount":estimate,"final_usage":actual,
            "files_created":[],"artifact_refs":[],"handoff_ids":[],"next_job_ids":[],
            "email_actions":int(provider=="EMAIL_PROVIDER" and state=="COMPLETED"),
            "social_actions":int(provider=="SOCIAL_MEDIA_EXTERNAL_ACTIONS" and state=="COMPLETED"),
            "browser_actions":int(provider=="BROWSER_EXTERNAL_SERVICES" and state=="COMPLETED"),
            "failure_codes":failure,"final_state":state})


def execute_public_read(provider: str, service: str, operation: Callable[[], Any], *,
                        requests: int = 1, response_bytes: int = 0,
                        job_id: str | None = None, correlation_id: str | None = None) -> Any:
    """Run a bounded external read only inside a real governed durable job."""
    return execute(provider, service, "READ", {
        "requests": max(1, int(requests)), "bytes": max(0, int(response_bytes)),
        "billable": False, "cost": 0,
    }, operation, job_id=job_id, correlation_id=correlation_id)


def governed_modal_canary(function: Callable[..., Any]) -> Callable[..., Any]:
    """Require explicit price/policy authorization around a direct Modal canary."""
    @wraps(function)
    def wrapped(*args: Any, **kwargs: Any) -> Any:
        estimate: dict[str, Any] = {"requests": 1, "operations": 1,
            "gpu_seconds": float(os.environ.get("NEXUS_MODAL_GPU_SECONDS_ESTIMATE", "3600")),
            "runtime_seconds": float(os.environ.get("NEXUS_MODAL_RUNTIME_SECONDS_ESTIMATE", "3600")),
            "billable": True}
        try: estimate["cost"] = float(os.environ["NEXUS_MODAL_ESTIMATED_COST_PER_JOB"])
        except (KeyError, ValueError): pass
        return execute("MODAL", "nova_canary", "GPU_GENERATION", estimate,
            lambda: function(*args, **kwargs), job_id=os.environ.get("NEXUS_DURABLE_JOB_ID"),
            job_type=os.environ.get("NEXUS_JOB_TYPE", "NOVA_MODAL_CANARY"),
            correlation_id=os.environ.get("NEXUS_CORRELATION_ID"))
    return wrapped


def classify_browser_action(action: str) -> str:
    value = action.strip().upper()
    if value in {"GET", "READ", "SEARCH", "CRAWL", "SCREENSHOT"}: return "READ_ONLY_BROWSER"
    if value in {"FILL", "CLICK", "FORM_SUBMIT", "CONTROLLED_WRITE"}: return "CONTROLLED_WRITE"
    if value in {"BUY", "PURCHASE", "PAY", "SPEND"}: return "PURCHASE_SPEND"
    if value in {"PUBLISH", "POST_PUBLIC"}: return "PUBLICATION"
    if value in {"ACCOUNT_CHANGE", "PASSWORD_CHANGE", "PERMISSION_CHANGE"}: return "ACCOUNT_CHANGE"
    return "UNKNOWN_ACTION"


def classify_email_action(action: str) -> str:
    value = action.strip().upper()
    return value if value in {"DRAFT", "TEST_SEND", "CONTROLLED_SEND", "BULK_SEND"} else "UNKNOWN_ACTION"


def classify_social_action(action: str) -> str:
    value = action.strip().upper()
    return value if value in {"READ", "DRAFT", "TEST_OR_PRIVATE_POST", "PUBLIC_POST", "COMMENT_INTERACTION", "PAID_PROMOTION"} else "UNKNOWN_ACTION"


def _action_denied(provider: str, action: str, code: str, job_id: str | None = None) -> None:
    store = default_store()
    jid = job_id or os.environ.get("NEXUS_DURABLE_JOB_ID") or "adhoc_action_" + uuid.uuid4().hex
    store.record_incident(provider, jid, code, "ACTION_DENIED_BEFORE_EXECUTION",
        project_id=os.environ.get("NEXUS_PROJECT_ID"), observed={"action_type": action})
    store.record_footprint({"project_id":os.environ.get("NEXUS_PROJECT_ID", "NEXUS"),"job_id":jid,
        "correlation_id":os.environ.get("NEXUS_CORRELATION_ID") or jid,
        "job_type":os.environ.get("NEXUS_JOB_TYPE","ADHOC_EXTERNAL_ACTION"),"provider":provider,
        "service":"external_action","action_type":action,"host":platform.node(),
        "environment":"production-off" if os.environ.get("NEXUS_DURABLE_JOB_ID") else "ad-hoc",
        "process_id":os.getpid(),"parent_process_id":os.getppid(),"worker_type":"PROVIDER_BOUNDARY",
        "start_time":datetime.now(timezone.utc).isoformat(),
        "end_time":datetime.now(timezone.utc).isoformat(),"request_count":0,
        "response_bytes":0,"tokens":0,"gpu_seconds":0,"estimated_cost":0,"actual_cost":None,
        "reservation_amount":0,"final_usage":{},"files_created":[],"artifact_refs":[],"handoff_ids":[],"next_job_ids":[],
        "email_actions":0,"social_actions":0,"browser_actions":0,
        "failure_codes":[code],"recovery_action":"external_action_not_called","final_state":"HUMAN_APPROVAL_REQUIRED"})


def authorize_browser_action(action: str, *, workflow_authorized: bool = False,
                             ray_approved: bool = False, spend_policy_authorized: bool = False) -> str:
    kind = classify_browser_action(action)
    if kind == "READ_ONLY_BROWSER": return kind
    if kind == "CONTROLLED_WRITE" and workflow_authorized: return kind
    if kind == "PURCHASE_SPEND" and workflow_authorized and ray_approved and spend_policy_authorized: return kind
    if kind == "PUBLICATION" and (workflow_authorized or ray_approved): return kind
    if kind == "ACCOUNT_CHANGE" and workflow_authorized and ray_approved: return kind
    _action_denied("BROWSER_EXTERNAL_SERVICES",kind,"BROWSER_ACTION_NOT_AUTHORIZED")
    raise GovernanceDenied("HUMAN_APPROVAL_REQUIRED", "BROWSER_ACTION_NOT_AUTHORIZED")


def authorize_email_action(action: str, *, workflow_authorized: bool = False,
                           approved_test_recipient: bool = False,
                           campaign_approved: bool = False,
                           limits_configured: bool = False) -> str:
    kind = classify_email_action(action)
    if kind == "DRAFT": return kind
    if kind == "TEST_SEND" and approved_test_recipient: return kind
    if kind == "CONTROLLED_SEND" and workflow_authorized: return kind
    if kind == "BULK_SEND" and campaign_approved and limits_configured: return kind
    _action_denied("EMAIL_PROVIDER",kind,"EMAIL_ACTION_NOT_AUTHORIZED")
    raise GovernanceDenied("HUMAN_APPROVAL_REQUIRED", "EMAIL_ACTION_NOT_AUTHORIZED")


def authorize_social_action(action: str, *, workflow_authorized: bool = False,
                            ray_approved: bool = False,
                            spend_policy_authorized: bool = False,
                            private_test_authorized: bool = False) -> str:
    kind = classify_social_action(action)
    if kind in {"READ", "DRAFT"}: return kind
    if kind == "TEST_OR_PRIVATE_POST" and private_test_authorized: return kind
    if kind in {"PUBLIC_POST", "COMMENT_INTERACTION"} and workflow_authorized: return kind
    if kind == "PAID_PROMOTION" and workflow_authorized and ray_approved and spend_policy_authorized: return kind
    _action_denied("SOCIAL_MEDIA_EXTERNAL_ACTIONS",kind,"SOCIAL_ACTION_NOT_AUTHORIZED")
    raise GovernanceDenied("HUMAN_APPROVAL_REQUIRED", "SOCIAL_ACTION_NOT_AUTHORIZED")


def authorize_telegram_action(chat_id: Any, *, action: str = "SEND",
                              workflow_authorized: bool = False) -> str:
    value = str(chat_id or "")
    if action.strip().upper() not in {"SEND", "SENDMESSAGE"}:
        _action_denied("TELEGRAM", action, "TELEGRAM_ACTION_NOT_AUTHORIZED")
        raise GovernanceDenied("HUMAN_APPROVAL_REQUIRED", "TELEGRAM_ACTION_NOT_AUTHORIZED")
    def listed(name: str) -> set[str]:
        return {x.strip() for x in os.environ.get(name, "").split(",") if x.strip()}
    if value in listed("NEXUS_TELEGRAM_INTERNAL_CHAT_IDS"):
        return "INTERNAL_SYSTEM_NOTIFICATION"
    if value in listed("NEXUS_TELEGRAM_RAY_CHAT_IDS"):
        return "RAY_NOTIFICATION"
    if value in listed("NEXUS_TELEGRAM_CLIENT_CHAT_IDS") and workflow_authorized:
        return "CLIENT_EXTERNAL_MESSAGE"
    if value.startswith("-"):
        category = "BROADCAST"
    else:
        category = "CLIENT_EXTERNAL_MESSAGE"
    _action_denied("TELEGRAM", category, "TELEGRAM_RECIPIENT_NOT_AUTHORIZED")
    raise GovernanceDenied("HUMAN_APPROVAL_REQUIRED", "TELEGRAM_RECIPIENT_NOT_AUTHORIZED")


def execute_telegram_delivery(chat_id: Any, operation: Callable[[], Any], *,
                             action: str = "SEND", workflow_authorized: bool = False,
                             job_id: str | None = None, job_type: str = "TELEGRAM_DELIVERY",
                             external_ref: Callable[[Any], str | None] | None = None) -> Any:
    category = authorize_telegram_action(chat_id, action=action, workflow_authorized=workflow_authorized)
    jid = job_id or os.environ.get("NEXUS_DURABLE_JOB_ID")
    return execute("TELEGRAM", "bot_delivery", category,
        {"requests": 1, "operations": 1, "billable": False}, operation,
        job_id=jid, job_type=job_type,
        correlation_id=os.environ.get("NEXUS_CORRELATION_ID") or jid,
        external_ref=external_ref)
