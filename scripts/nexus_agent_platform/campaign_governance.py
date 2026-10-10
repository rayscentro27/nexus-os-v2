"""Versioned Creative prompt and final campaign approval gates."""
from __future__ import annotations
import hashlib, json
import uuid
from datetime import datetime, timezone
from typing import Any, Mapping
from nexus_agent_platform.governed.persistence import append_record, new_id, read_records

COLLECTION = "creative_campaigns"

def _now() -> str: return datetime.now(timezone.utc).isoformat()
def _latest(record_type: str, record_id: str) -> dict[str, Any] | None:
    for row in read_records(COLLECTION, limit=2000):
        if row.get("record_type") == record_type and row.get("id") == record_id: return row
    return None

def create_creative_prompt(*, campaign_id: str, business_plan_id: str, marketing_plan_id: str, fields: Mapping[str, Any], exact_prompt: str) -> dict[str, Any]:
    required = ("target_audience", "campaign_goal", "offer", "value_proposition", "key_messages", "supported_facts", "claim_boundaries", "required_disclosures", "cta", "asset_types", "platforms", "format_requirements", "visual_direction", "video_direction", "copy_direction", "brand_requirements")
    missing = [key for key in required if key not in fields]
    if missing or not exact_prompt.strip(): raise ValueError("creative_prompt_missing:" + ",".join(missing or ["exact_prompt"]))
    pid = new_id("creative_prompt"); now = _now()
    artifact = {"record_type":"VERSIONED_CREATIVE_PROMPT", "id":pid, "creative_prompt_id":pid, "campaign_id":campaign_id, "version":1, "business_plan_id":business_plan_id, "marketing_plan_id":marketing_plan_id, **dict(fields), "exact_creative_prompt":exact_prompt, "exact_prompt_sha256":hashlib.sha256(exact_prompt.encode()).hexdigest(), "status":"WAITING_RAY_APPROVAL", "created_at":now, "updated_at":now}
    append_record(COLLECTION, artifact); return artifact

def mirror_prompt_to_ray_review(artifact: Mapping[str, Any]) -> dict[str, Any]:
    """Place the exact prompt in the existing authenticated Admin review queue."""
    from scripts.operations import nexus_handoff
    request_id = str(uuid.uuid4())
    body = {"id":request_id,"task_type":"ray_review_item","requested_by":"NEXUS_MARKETING","sensitivity":"internal_summary","allowed_data_scope":["campaign_prompt_review"],"forbidden_data":["credentials","customer_pii"],"assigned_worker_type":"ray_review","hermes_visibility":"summary","status":"requested","payload":{"review_kind":"creative_prompt_approval","creative_prompt_id":artifact.get("creative_prompt_id"),"campaign_id":artifact.get("campaign_id"),"version":artifact.get("version"),"title":f"Approve Creative prompt v{artifact.get('version')} for {artifact.get('campaign_id')}","exact_creative_prompt":artifact.get("exact_creative_prompt"),"prompt_fields":{key:artifact.get(key) for key in ("target_audience","campaign_goal","offer","value_proposition","key_messages","supported_facts","claim_boundaries","required_disclosures","cta","asset_types","platforms","format_requirements","visual_direction","video_direction","copy_direction","brand_requirements")},"exact_prompt_sha256":artifact.get("exact_prompt_sha256"),"decision_options":["APPROVE_PROMPT","REQUEST_CHANGES","REJECT_PROMPT"],"external_action_performed":False}}
    status, result = nexus_handoff.rest("POST","task_requests",body,prefer="return=representation")
    if status in (200,201):
        append_record(COLLECTION,{**dict(artifact),"admin_review_request_id":request_id,"updated_at":_now()})
    return {"status":"PASS" if status in (200,201) and isinstance(result,list) and result else "NOT_PROVEN","request_id":request_id if status in (200,201) else None,"http_status":status,"error":result if status not in (200,201) else None}

def decide_creative_prompt(creative_prompt_id: str, decision: str, *, actor: str, changes: Mapping[str, Any] | None = None) -> dict[str, Any]:
    current = _latest("VERSIONED_CREATIVE_PROMPT", creative_prompt_id)
    if not current: return {"status":"NOT_FOUND"}
    if actor.upper() not in {"RAY", "RAYMOND DAVIS"}: return {"status":"UNAUTHORIZED", "decision":decision}
    mapping = {"APPROVE_PROMPT":"APPROVED", "REQUEST_CHANGES":"CHANGES_REQUESTED", "REJECT_PROMPT":"REJECTED"}
    if decision not in mapping: return {"status":"INVALID_DECISION"}
    updated = {**current, "status":mapping[decision], "decision":decision, "decision_by":"RAY", "updated_at":_now(), "change_request":dict(changes or {})}
    append_record(COLLECTION, updated); return updated

def create_prompt_revision(creative_prompt_id: str, *, fields: Mapping[str, Any], exact_prompt: str) -> dict[str, Any]:
    previous = _latest("VERSIONED_CREATIVE_PROMPT", creative_prompt_id)
    if not previous or previous.get("status") != "CHANGES_REQUESTED": raise ValueError("prompt_revision_requires_changes_requested")
    new = {**previous, **dict(fields), "version":int(previous.get("version", 1))+1, "exact_creative_prompt":exact_prompt, "exact_prompt_sha256":hashlib.sha256(exact_prompt.encode()).hexdigest(), "status":"WAITING_RAY_APPROVAL", "decision":None, "decision_by":None, "created_at":_now(), "updated_at":_now(), "supersedes":creative_prompt_id}
    # A revision is a new durable artifact identity; the prior version remains visible.
    new_id_value = new_id("creative_prompt"); new["id"] = new_id_value; new["creative_prompt_id"] = new_id_value
    append_record(COLLECTION, new)
    from scripts.operations import nexus_handoff
    if nexus_handoff.configured():
        review = mirror_prompt_to_ray_review(new)
        if review.get("status") == "PASS":
            new = {**new, "admin_review_request_id": review["request_id"], "updated_at": _now()}
            append_record(COLLECTION, new)
    return new

def prompt_generation_gate(creative_prompt_id: str) -> dict[str, Any]:
    row = _latest("VERSIONED_CREATIVE_PROMPT", creative_prompt_id)
    allowed = bool(row and row.get("status") == "APPROVED" and row.get("decision_by") == "RAY")
    status = row.get("status") if row else "NOT_FOUND"
    if row and not allowed and row.get("admin_review_request_id"):
        from scripts.operations import nexus_handoff
        code, result = nexus_handoff.rest("GET",f"task_requests?id=eq.{row['admin_review_request_id']}&select=id,status,payload&limit=1")
        request = result[0] if code == 200 and isinstance(result,list) and result else {}
        payload = request.get("payload") or {}; decision=(payload.get("ray_approval") or {})
        allowed = request.get("status")=="done" and payload.get("review_kind")=="creative_prompt_approval" and decision.get("decision")=="APPROVE_PROMPT" and bool(decision.get("actor_user_id"))
        if allowed: status="APPROVED_BY_AUTHENTICATED_RAY_REVIEW"
    return {"allowed":allowed, "status":status, "reason":"RAY_APPROVED_EXACT_PROMPT" if allowed else "WAITING_FOR_RAY_APPROVAL", "exact_prompt_sha256":row.get("exact_prompt_sha256") if row else None, "exact_creative_prompt":row.get("exact_creative_prompt") if row else None}

def create_campaign_ready_record(*, campaign_id: str, package: Mapping[str, Any]) -> dict[str, Any]:
    required = ("opportunity", "offer", "audience", "strategy", "final_copy", "final_assets", "platforms", "schedule", "requested_spend", "claims_disclosures", "tracking")
    missing = [key for key in required if key not in package]
    row = {"record_type":"CAMPAIGN_APPROVAL", "id":campaign_id, "campaign_id":campaign_id, "status":"CAMPAIGN_READY_FOR_RAY" if not missing else "INCOMPLETE_NOT_READY", "package":dict(package), "missing_fields":missing, "created_at":_now(), "external_execution_allowed":False}
    append_record(COLLECTION,row); return row

def campaign_external_gate(campaign_id: str) -> dict[str, Any]:
    row = _latest("CAMPAIGN_APPROVAL", campaign_id)
    approved = bool(row and row.get("status")=="APPROVED_CAMPAIGN" and row.get("decision_by")=="RAY" and not row.get("missing_fields"))
    return {"allowed":approved, "status":row.get("status") if row else "NOT_FOUND", "reason":"EXACT_RAY_CAMPAIGN_APPROVAL_REQUIRED" if not approved else "APPROVED_NOT_PUBLISHED", "external_execution_performed":False}

def marketing_post_approval_state(campaign_id: str) -> dict[str, Any]:
    gate=campaign_external_gate(campaign_id)
    return {"campaign_id":campaign_id,"status":"READY_TO_SCHEDULE_AFTER_RAY_APPROVAL" if gate.get("allowed") else "WAITING_FOR_COMPLETE_CAMPAIGN_AND_RAY_APPROVAL","external_publish_performed":False,"next_action":"PREPARE_AUTHORIZED_SCHEDULE_AND_TRACKING" if gate.get("allowed") else "COMPLETE_CAMPAIGN_PACKAGE_AND_REQUEST_RAY_APPROVAL"}

def decide_campaign(campaign_id: str, decision: str, *, actor: str) -> dict[str, Any]:
    row=_latest("CAMPAIGN_APPROVAL",campaign_id)
    if not row:return {"status":"NOT_FOUND"}
    if actor.upper() not in {"RAY","RAYMOND DAVIS"}:return {"status":"UNAUTHORIZED"}
    mapped={"APPROVE_CAMPAIGN":"APPROVED_CAMPAIGN","REQUEST_CHANGES":"CAMPAIGN_CHANGES_REQUESTED","REJECT_CAMPAIGN":"CAMPAIGN_REJECTED"}
    if decision not in mapped:return {"status":"INVALID_DECISION"}
    if decision=="APPROVE_CAMPAIGN" and row.get("missing_fields"):return {"status":"INCOMPLETE_NOT_READY","missing_fields":row.get("missing_fields")}
    updated={**row,"status":mapped[decision],"decision_by":"RAY","decision":decision,"updated_at":_now(),"external_execution_allowed":False};append_record(COLLECTION,updated);return updated
