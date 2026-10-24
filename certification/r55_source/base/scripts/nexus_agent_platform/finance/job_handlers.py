"""Finance-owned bounded handlers for durable downstream review jobs."""
from __future__ import annotations

import hashlib
import json
import uuid
from typing import Any

from nexus_agent_platform.durable_jobs import create_next_job


def _budget_snapshot() -> dict[str, Any]:
    from nexus_agent_platform.resource_spend_governor import default_store

    store = default_store()
    summary = store.summary()
    providers = []
    wanted = {"SUPABASE", "EMAIL_PROVIDER", "SOCIAL_MEDIA_EXTERNAL_ACTIONS", "BROWSER_EXTERNAL_SERVICES"}
    for row in summary.get("providers", [])[:40]:
        if row.get("provider") not in wanted:
            continue
        providers.append({key: row.get(key) for key in (
            "provider", "service", "state", "autonomous_usage_allowed",
            "autonomous_spend_allowed", "approval_required", "daily_usage",
            "monthly_usage", "reserved_usage", "active_paid_jobs",
        )})
    return {
        "source": type(store).__name__,
        "status": "READ" if providers else "UNKNOWN",
        "providers": providers,
        "active_reservations": int(summary.get("active_reservations", 0) or 0),
        "read_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
    }


def _numeric_or_unknown(value: Any) -> int | float | str:
    if isinstance(value, bool):
        return "UNKNOWN"
    if isinstance(value, (int, float)):
        return value if value >= 0 else "UNKNOWN"
    if isinstance(value, str):
        try:
            parsed = float(value.strip())
            return parsed if parsed >= 0 else "UNKNOWN"
        except ValueError:
            return "UNKNOWN"
    return "UNKNOWN"


def handle_campaign_review(job, store) -> dict[str, Any]:
    """Read governed budget state, record a no-authority review, hand back to Marketing."""
    from nexus_agent_platform.finance.foundation import economic_request
    from nexus_agent_platform.marketing_creative_workflow import load_payload, store_payload

    payload = load_payload(job.payload_ref)
    campaign_id = str(payload.get("campaign_id") or "")
    if not campaign_id:
        raise ValueError("FINANCE_CAMPAIGN_ID_REQUIRED")
    budget = _budget_snapshot()
    proposed_spend = _numeric_or_unknown(payload.get("proposed_spend", "UNKNOWN"))
    request_id = "fer_" + hashlib.sha256(
        f"{campaign_id}:{payload.get('event_id', job.job_id)}".encode()
    ).hexdigest()[:20]
    decision = "DEFER_NO_SPEND_AUTHORITY"
    review = economic_request(
        requesting_department="MARKETING",
        business_reason=f"Review proposed campaign spend for {campaign_id}",
        current_limitation="Governed provider budgets are not spend authority; actual campaign budget availability is unknown.",
        proposed_spend=proposed_spend,
        expected_benefit=payload.get("expected_benefit", "UNKNOWN"),
        alternatives=list(payload.get("alternatives") or ["No-spend organic test", "Defer campaign"]),
        measurement_plan="Finance budget-state review; explicit Ray approval remains required.",
        request_id=request_id,
        resource_budget_state=budget,
        campaign_id=campaign_id,
        project_id=payload.get("project_id"),
        recommendation=decision,
    )
    result = {
        "status": "COMPLETED", "finance_request_id": review["request_id"],
        "campaign_id": campaign_id, "project_id": payload.get("project_id"),
        "recommendation": decision, "available_budget": "UNKNOWN",
        "proposed_spend": proposed_spend, "spend_authorized": False,
        "ray_approval_required": True, "resource_budget_state": budget,
        "external_action_performed": False,
    }
    try:
        from nexus_agent_platform.marketing_supabase_state import configured
        if configured():
            from nexus_agent_platform.feeder_runtime import _request

            event_id = str(uuid.uuid5(uuid.NAMESPACE_URL, "nexus-finance-review:" + request_id))
            _request("nexus_events?on_conflict=id", "POST", {
                "id": event_id, "lane": "system", "source": "FINANCE_DURABLE_WORKER",
                "action": "campaign_spend_review", "status": "info",
                "title": "Marketing campaign budget review",
                "summary": decision, "payload": {
                    "campaign_id": campaign_id, "project_id": payload.get("project_id"),
                    "finance_request_id": request_id, "recommendation": decision,
                    "available_budget": "UNKNOWN", "spend_authorized": False,
                    "ray_approval_required": True, "resource_budget_state": budget,
                }, "visible_to_ray": True, "severity": "info",
                "correlation_id": job.correlation_id,
            }, "resolution=merge-duplicates,return=minimal")
    except Exception:
        # The worker boundary will fail this job and preserve the durable state
        # if required Finance evidence cannot be persisted.
        raise
    result_ref = store_payload(result, payload_id="finance-result-" + request_id)
    child = create_next_job(
        store, job, department="MARKETING", job_type="MARKETING_FINANCE_REVIEW_RESULT",
        payload_ref=result_ref, event_id=f"finance-review-complete:{request_id}",
    )
    result["next_job_id"] = child.job_id
    return result
