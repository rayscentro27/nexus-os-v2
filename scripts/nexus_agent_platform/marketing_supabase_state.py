"""Compact Supabase projection for Marketing/Creative campaign control state.

Creative bodies and media are deliberately excluded. The existing
``creative_campaigns.metadata`` column carries only compact workflow state and
opaque artifact/job references; all REST calls use explicit projections and
the shared job-scoped egress guard.
"""
from __future__ import annotations

import os
import uuid
from typing import Any, Mapping
from urllib.parse import quote

_STATE_FIELDS = (
    "campaign_id", "project_id", "business_id", "state", "creative_state", "source",
    "request_ref", "strategy_ref", "brief_id", "brief_ref", "asset_ids", "artifact_refs",
    "revision_count", "approval_state", "job_id", "finance_review_job_id", "finance_request_id",
    "finance_review_state", "finance_result_ref", "finance_recommendation", "finance_budget_available", "spend_authorized", "publish_job_id",
    "revision_job_id", "research_result_ref", "review_package_ref", "external_action_job_ids",
    "handoff_ids", "state_history", "creative_state_history", "landing_page_ref",
    "landing_page_version", "performance_ref", "workflow_stage", "workflow_stage_history",
    "correlation_id", "tenant_id", "research_ref", "analysis_ref", "review_refs",
    "review_decisions", "last_review_id", "publishing_handoff_ref", "publication_attempts",
    "publish_execution", "test_campaign", "creative_provider_route",
)


def configured() -> bool:
    return bool(
        (os.environ.get("SUPABASE_URL") or os.environ.get("VITE_SUPABASE_URL"))
        and os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    )


def _compact(row: Mapping[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key in _STATE_FIELDS:
        if key not in row or row[key] is None:
            continue
        value = row[key]
        if isinstance(value, str):
            result[key] = value[:500]
        elif isinstance(value, list):
            result[key] = value[:50]
        elif isinstance(value, (int, float, bool, dict)):
            result[key] = value
    return result


def save_campaign(row: Mapping[str, Any]) -> None:
    if not configured():
        return
    campaign_id = str(row.get("campaign_id") or "")
    if not campaign_id:
        raise ValueError("CAMPAIGN_ID_REQUIRED")
    metadata = _compact(row)
    body = {
        "campaign_key": campaign_id,
        "name": str(row.get("name") or row.get("objective") or f"Nexus campaign {campaign_id}")[:200],
        "goal": str(row.get("objective") or "")[:500] or None,
        "audience": str(row.get("target_audience") or "")[:300] or None,
        "offer": str(row.get("offer") or "")[:300] or None,
        "status": str(row.get("state") or "REQUEST_RECEIVED")[:80],
        "metadata": metadata,
    }
    from nexus_agent_platform.feeder_runtime import _request

    _request(
        "creative_campaigns?on_conflict=campaign_key", "POST", body,
        "resolution=merge-duplicates,return=minimal",
    )


def get_campaign(campaign_id: str) -> dict[str, Any] | None:
    if not configured():
        return None
    from nexus_agent_platform.feeder_runtime import _request

    escaped = quote(str(campaign_id), safe="")
    rows = _request(
        "creative_campaigns?campaign_key=eq." + escaped
        + "&select=campaign_key,status,metadata&limit=1"
    )
    if not rows:
        return None
    metadata = rows[0].get("metadata") or {}
    if not isinstance(metadata, dict):
        metadata = {}
    return {
        **metadata, "campaign_id": rows[0].get("campaign_key"), "state": rows[0].get("status"),
        "objective": rows[0].get("goal"), "target_audience": rows[0].get("audience"),
        "offer": rows[0].get("offer"),
    }


def record_asset_metadata(
    *, asset_id: str, campaign_id: str, project_id: str, asset_type: str,
    artifact_ref: str, sha256: str, size_bytes: int, mime_type: str,
    status: str, approval_state: str, version: int = 1,
) -> None:
    """Store a compact asset index; never send asset content or media bytes."""
    if not configured():
        return
    from nexus_agent_platform.feeder_runtime import _request

    # creative_assets.id is UUID in the legacy schema, while local asset IDs
    # are namespaced strings. Store the stable identity and object reference in
    # the compact JSON payload and leave the nullable content column empty.
    stable_uuid = str(uuid.uuid5(uuid.NAMESPACE_URL, "nexus-creative-asset:" + str(asset_id)))
    _request("creative_assets?on_conflict=id", "POST", {
        "id": stable_uuid,
        "asset_type": str(asset_type)[:80],
        "title": str(asset_type)[:200],
        "status": str(status)[:80],
        "content": None,
        "payload": {
            "asset_id": str(asset_id)[:120], "campaign_id": str(campaign_id)[:120],
            "project_id": str(project_id)[:120], "storage_provider": "LOCAL_WORKING",
            "artifact_ref": str(artifact_ref)[:500], "sha256": str(sha256)[:64],
            "size_bytes": max(0, int(size_bytes)), "mime_type": str(mime_type)[:120],
            "version": max(1, int(version)), "approval_state": str(approval_state)[:80],
        },
    }, "resolution=merge-duplicates,return=minimal")
