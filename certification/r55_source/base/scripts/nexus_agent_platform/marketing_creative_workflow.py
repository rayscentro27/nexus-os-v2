"""Bounded, event-driven Marketing/Creative campaign workflow.

This module composes the existing durable queue and Creative Studio. Payloads
and artifacts live outside Supabase; queue/state records carry references only.
External actions remain approval gated and are never executed by this module.
"""
from __future__ import annotations

import hashlib
import html
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from nexus_agent_platform.durable_jobs import create_next_job, default_store

ROOT = Path(__file__).resolve().parents[2]
RUNTIME = Path(os.environ.get("NEXUS_MARKETING_CREATIVE_DIR", ROOT / "data/runtime/marketing_creative"))
PAYLOADS = RUNTIME / "payloads"
REVIEWS = RUNTIME / "campaigns"
ARTIFACTS = RUNTIME / "artifacts"
MAX_AUTONOMOUS_CREATIVE_REVISIONS = 2
MARKETING_STATES = {"REQUEST_RECEIVED", "RESEARCH_REQUIRED", "STRATEGY_IN_PROGRESS", "STRATEGY_READY", "CREATIVE_BRIEF_READY", "WAITING_CREATIVE", "ASSETS_READY", "MARKETING_QA", "RAY_REVIEW_REQUIRED", "READY_FOR_CONTROLLED_PUBLISH", "PUBLISHING", "MEASURING", "ANALYZING", "ITERATION_READY", "COMPLETE", "BLOCKED", "APPROVAL_PENDING"}
CREATIVE_STATES = {"BRIEF_RECEIVED", "ASSET_PLAN", "PROVIDER_SELECTION", "GENERATING", "QA", "REVISION_REQUIRED", "READY_FOR_MARKETING", "RAY_REVIEW_REQUIRED", "BLOCKED_PROVIDER", "BLOCKED_BUDGET", "COMPLETE"}
CREATIVE_BRIEF_FIELDS = {"campaign_id", "project_id", "business_id", "target_audience", "problem", "offer", "campaign_objective", "channel", "format", "cta", "brand_constraints", "required_assets", "creative_direction", "evidence_reference_inputs", "budget_envelope", "deadline", "priority", "approval_requirement", "hook", "message", "asset_type", "dimensions", "aspect_ratio", "duration_seconds", "prohibited_elements", "provider_constraints", "acceptance_criteria", "budget_class"}
CANONICAL_WORKFLOW_STAGES = {"RESEARCH_READY", "MARKETING_STRATEGY", "CREATIVE_BRIEF", "CREATIVE_PRODUCTION", "MARKETING_REVIEW", "CREATIVE_REVISION", "APPROVAL_PENDING", "APPROVED", "PUBLISHING_READY", "PUBLISHED", "PERFORMANCE_COLLECTION", "MARKETING_ANALYSIS", "ITERATION", "COMPLETE", "FAILED", "BLOCKED"}
WORKFLOW_TRANSITIONS = {
    None: {"RESEARCH_READY"}, "RESEARCH_READY": {"MARKETING_STRATEGY", "BLOCKED"},
    "MARKETING_STRATEGY": {"CREATIVE_BRIEF", "BLOCKED"}, "CREATIVE_BRIEF": {"CREATIVE_PRODUCTION", "BLOCKED"},
    "CREATIVE_PRODUCTION": {"MARKETING_REVIEW", "BLOCKED"}, "MARKETING_REVIEW": {"CREATIVE_REVISION", "APPROVAL_PENDING", "BLOCKED"},
    "CREATIVE_REVISION": {"CREATIVE_PRODUCTION", "BLOCKED"}, "APPROVAL_PENDING": {"APPROVED", "PERFORMANCE_COLLECTION", "BLOCKED"},
    "APPROVED": {"PUBLISHING_READY", "BLOCKED"}, "PUBLISHING_READY": {"PUBLISHED", "BLOCKED"},
    "PUBLISHED": {"PERFORMANCE_COLLECTION"}, "PERFORMANCE_COLLECTION": {"MARKETING_ANALYSIS", "BLOCKED"},
    "MARKETING_ANALYSIS": {"ITERATION", "COMPLETE", "BLOCKED"}, "ITERATION": {"MARKETING_STRATEGY", "CREATIVE_BRIEF", "COMPLETE"},
    "FAILED": {"BLOCKED"}, "BLOCKED": set(), "COMPLETE": set(),
}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, sort_keys=True, indent=2, default=str) + "\n")
    os.replace(tmp, path)


def _read(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return default


def store_payload(payload: Mapping[str, Any], *, payload_id: str | None = None) -> str:
    """Persist bounded request data off-queue and return an opaque reference."""
    payload_id = payload_id or "payload_" + _hash(payload)[:24]
    _write(PAYLOADS / f"{payload_id}.json", dict(payload))
    return payload_id


def load_payload(payload_ref: str | None) -> dict[str, Any]:
    if not payload_ref:
        raise ValueError("PAYLOAD_REFERENCE_REQUIRED")
    value = _read(PAYLOADS / f"{Path(payload_ref).name}.json")
    if not isinstance(value, dict):
        raise ValueError("PAYLOAD_REFERENCE_NOT_FOUND")
    return value


def _campaign_path(campaign_id: str) -> Path:
    return RUNTIME / "state" / f"{_hash(campaign_id)[:32]}.json"


def campaign(campaign_id: str) -> dict[str, Any] | None:
    row = _read(_campaign_path(campaign_id))
    if row is not None:
        return row
    try:
        from nexus_agent_platform.marketing_supabase_state import get_campaign
        return get_campaign(campaign_id)
    except Exception:
        # Local review remains available when a remote control-plane read is
        # unavailable. The durable worker records the incident at its boundary.
        return None


def _save_campaign(row: Mapping[str, Any]) -> dict[str, Any]:
    value = {**dict(row), "updated_at": now()}
    if value.get("state") not in MARKETING_STATES:
        raise ValueError(f"INVALID_MARKETING_STATE:{value.get('state')}")
    if value.get("creative_state") and value["creative_state"] not in CREATIVE_STATES:
        raise ValueError(f"INVALID_CREATIVE_STATE:{value.get('creative_state')}")
    if value.get("workflow_stage") and value["workflow_stage"] not in CANONICAL_WORKFLOW_STAGES:
        raise ValueError(f"INVALID_CAMPAIGN_STAGE:{value['workflow_stage']}")
    _write(_campaign_path(str(value["campaign_id"])), value)
    from nexus_agent_platform.marketing_supabase_state import save_campaign
    save_campaign(value)
    return value


def _set_stage(row: dict[str, Any], stage: str) -> None:
    if stage not in CANONICAL_WORKFLOW_STAGES:
        raise ValueError(f"INVALID_CAMPAIGN_STAGE:{stage}")
    current = row.get("workflow_stage")
    if stage != current and stage not in WORKFLOW_TRANSITIONS.get(current, set()):
        raise ValueError(f"INVALID_CAMPAIGN_TRANSITION:{current or 'START'}->{stage}")
    if stage != current:
        row["workflow_stage"] = stage
        row.setdefault("workflow_stage_history", []).append(stage)


def create_request(payload: Mapping[str, Any], *, source: str = "RAY") -> dict[str, Any]:
    """Create an explicit Marketing request; Atlas and Nova share this route."""
    campaign_id = str(payload.get("campaign_id") or "campaign_" + _hash([source, payload])[:20])
    if payload.get("request_kind") == "CREATE_ASSET" and not payload.get("existing_campaign_id"):
        raise ValueError("ASSET_REQUEST_REQUIRES_EXISTING_CAMPAIGN")
    ref = store_payload({**dict(payload), "source": source}, payload_id="request_" + _hash(campaign_id)[:24])
    store = default_store()
    job = store.enqueue("MARKETING", "MARKETING_STRATEGY", payload_ref=ref,
                        correlation_id=str(payload.get("correlation_id") or _hash(campaign_id)[:24]),
                        idempotency_key=f"marketing-request:{campaign_id}")
    row = _save_campaign({"campaign_id": campaign_id, "project_id": payload.get("project_id", "goclear"),
                          "business_id": payload.get("business_id", "goclear"), "state": "REQUEST_RECEIVED",
                          "source": source, "request_ref": ref, "strategy_ref": None, "brief_id": None,
                          "asset_ids": [], "revision_count": 0, "approval_state": "PENDING",
                          "job_id": job.job_id, "created_at": now()})
    return {"campaign": row, "job_id": job.job_id}


def atlas_opportunity_intake(opportunity: Mapping[str, Any]) -> dict[str, Any]:
    """Atlas requests marketing strategy; it cannot invoke Creative directly."""
    return create_request({**dict(opportunity), "request_kind": "CREATE_CAMPAIGN"}, source="ATLAS")


def classify_nova_request(text: str, *, existing_campaign_id: str | None = None) -> str:
    value = text.strip().lower()
    if any(x in value for x in ("research why", "research whether", "investigate")):
        return "SEND_TO_RESEARCH"
    if any(x in value for x in ("revise", "another version", "variation")):
        return "REVISE_ASSET" if existing_campaign_id else "DISCUSS"
    if any(x in value for x in ("make an asset", "create an asset", "create_asset")):
        return "CREATE_ASSET" if existing_campaign_id else "DISCUSS"
    if any(x in value for x in ("campaign", "marketing", "advert")):
        return "CREATE_CAMPAIGN"
    return "DISCUSS"


def ray_nova_intake(text: str, *, campaign_id: str | None = None,
                    strategy_inputs: Mapping[str, Any] | None = None) -> dict[str, Any]:
    kind = classify_nova_request(text, existing_campaign_id=campaign_id)
    if kind == "CREATE_CAMPAIGN":
        return {"classification": kind, **create_request(strategy_inputs or {"objective": text}, source="NOVA_ON_BEHALF_OF_RAY")}
    if kind == "CREATE_ASSET":
        return {"classification": kind, "campaign_id": campaign_id, "status": "EXISTING_BRIEF_REQUIRED"}
    if kind == "REVISE_ASSET":
        return {"classification": kind, "campaign_id": campaign_id, "status": "RAY_REVIEW_REQUIRED"}
    if kind == "SEND_TO_RESEARCH":
        return {"classification": kind, "status": "RESEARCH_REQUEST_REQUIRED", "campaign_id": campaign_id}
    return {"classification": kind, "status": "DISCUSSION_ONLY", "campaign_id": campaign_id}


def _enqueue(store, parent, department: str, job_type: str, campaign_id: str, event: str, payload: Mapping[str, Any]):
    handoff_id = "handoff_" + _hash([parent.job_id, campaign_id, event, job_type])[:24]
    current = campaign(campaign_id) or {}
    next_stage = {"MARKETING_STRATEGY": "MARKETING_STRATEGY", "CREATIVE_BRIEF_BUILD": "CREATIVE_BRIEF",
                  "CREATIVE_ASSET_GENERATE": "CREATIVE_PRODUCTION", "CREATIVE_ASSET_REVISE": "CREATIVE_REVISION",
                  "MARKETING_ASSET_REVIEW": "MARKETING_REVIEW", "PERFORMANCE_COLLECT": "PERFORMANCE_COLLECTION",
                  "MARKETING_PERFORMANCE_ANALYZE": "MARKETING_ANALYSIS"}.get(job_type)
    input_ref = payload.get("input_artifact_ref") or payload.get("strategy_ref") or payload.get("brief_ref") or payload.get("research_ref") or payload.get("performance_ref")
    stamped = {**dict(payload), "campaign_id": campaign_id, "project_id": payload.get("project_id") or current.get("project_id"),
               "job_id": None, "correlation_id": parent.correlation_id, "tenant_id": parent.tenant_id,
               "department": department, "workflow_stage": payload.get("workflow_stage") or next_stage,
               "input_artifact_ref": input_ref, "handoff_id": handoff_id,
               "created_at": now(), "updated_at": now(), "test_campaign": bool(parent.governance_context.get("test_campaign"))}
    ref = store_payload(stamped, payload_id="event_" + _hash([parent.job_id, campaign_id, event])[:24])
    child = create_next_job(store, parent, department=department, job_type=job_type,
                            payload_ref=ref, event_id=f"{campaign_id}:{event}")
    stamped["job_id"] = child.job_id
    stamped["output_artifact_ref"] = ref
    stamped["receipt_id"] = child.receipt_ref
    _write(PAYLOADS / f"{Path(ref).name}.json", stamped)
    _write(RUNTIME / "handoffs" / f"{handoff_id}.json", stamped)
    return child


def create_test_campaign(*, store=None, campaign_id: str | None = None) -> dict[str, Any]:
    """Create one provider-free Research→Marketing workflow canary job."""
    store = store or default_store()
    campaign_id = campaign_id or "campaign-canary-" + _hash([now(), os.getpid()])[:12]
    correlation_id = "corr_" + _hash([campaign_id, "marketing-creative-canary"])[:24]
    test_payload = {
        "campaign_id": campaign_id, "project_id": "goclear", "business_id": "goclear",
        "target_audience": "small business owners preparing for funding",
        "problem": "owners are unsure which records to prepare first",
        "offer": "readiness review", "objective": "explain a practical readiness path",
        "channels": ["INTERNAL_TEST"], "cta": "Review the readiness checklist",
        "evidence_refs": ["test://customer-insight/1"],
        "research_insight": {
            "customer_need": "A clear order for preparing business records",
            "complaint_or_pain_point": "Uncertainty about which documents to gather",
            "target_audience": "small business owners preparing for funding",
            "source_evidence_refs": ["test://customer-insight/1"],
            "market_opportunity": "Provide an educational readiness checklist",
            "channel": "INTERNAL_TEST", "offer_fit": "readiness review",
            "confidence": "TEST_FIXTURE", "constraints": ["No funding guarantees", "No external publication"],
            "recommended_marketing_angle": "Show the next preparation step",
        },
        "required_assets": ["LANDING_PAGE_COPY"], "brand_constraints": ["No guaranteed funding or approval claims"],
        "max_creative_revision_loops": 2,
    }
    ref = store_payload(test_payload, payload_id="research-test-" + _hash(campaign_id)[:20])
    governance = {"test_campaign": True, "resource_class": "LIGHTWEIGHT_INTERNAL",
                  "providers_allowed": [], "external_actions_allowed": False, "spend_allowed": False}
    job = store.enqueue("RESEARCH", "RESEARCH_MARKETING_TEST_HANDOFF", payload_ref=ref,
                        correlation_id=correlation_id, idempotency_key=f"marketing-test-research:{campaign_id}",
                        budget_envelope={"max_requests": 120, "max_response_bytes": 100000,
                                         "max_tokens": 0, "max_gpu_seconds": 0,
                                         "max_runtime_seconds": 120, "max_resource_creations": 0,
                                         "max_estimated_cost": 0.0, "max_retries": 1},
                        governance_context=governance)
    return {"campaign_id": campaign_id, "job_id": job.job_id, "correlation_id": correlation_id,
            "research_payload_ref": ref, "test_campaign": True}


def handle_job(job, store=None) -> dict[str, Any]:
    """Execute a single internal job; each transition emits at most one next job."""
    store = store or default_store()
    payload = load_payload(job.payload_ref)
    campaign_id = str(payload.get("campaign_id") or payload.get("existing_campaign_id") or "")
    if not campaign_id:
        raise ValueError("CAMPAIGN_ID_REQUIRED")
    row = campaign(campaign_id) or {"campaign_id": campaign_id, "project_id": payload.get("project_id", "goclear"), "business_id": payload.get("business_id", "goclear"), "asset_ids": [], "revision_count": 0, "approval_state": "PENDING", "created_at": now(), "correlation_id": job.correlation_id, "tenant_id": job.tenant_id, "handoff_ids": [], "workflow_stage_history": []}
    next_job = None
    if job.job_type == "CREATIVE_QA" and payload.get("failure_canary"):
        if not job.governance_context.get("test_campaign") or not job.governance_context.get("failure_canary"):
            raise PermissionError("CONTROLLED_FAILURE_REQUIRES_TEST_GOVERNANCE_CONTEXT")
        raise ValueError("CONTROLLED_CANARY_MISSING_ARTIFACT")
    elif job.job_type == "RESEARCH_MARKETING_TEST_HANDOFF":
        if not job.governance_context.get("test_campaign") or job.governance_context.get("providers_allowed") != []:
            raise PermissionError("TEST_RESEARCH_HANDOFF_REQUIRES_PROVIDER_FREE_CONTEXT")
        required_research = ("customer_need", "complaint_or_pain_point", "target_audience", "source_evidence_refs", "market_opportunity", "channel", "offer_fit", "confidence", "constraints", "recommended_marketing_angle")
        insight = payload.get("research_insight") or {}
        if any(not insight.get(key) for key in required_research):
            raise ValueError("RESEARCH_HANDOFF_CONTRACT_INCOMPLETE")
        research_ref = "research_" + _hash([campaign_id, "test-insight"])[:24]
        research = {**insight, "artifact_id": research_ref, "campaign_id": campaign_id,
                    "project_id": row.get("project_id"), "job_id": job.job_id,
                    "correlation_id": job.correlation_id, "department": "RESEARCH",
                    "workflow_stage": "RESEARCH_READY", "data_class": "TEST",
                    "created_at": now(), "receipt_id": "receipt-pending:" + job.job_id}
        store_payload(research, payload_id=research_ref)
        _set_stage(row, "RESEARCH_READY")
        row.update(state="STRATEGY_IN_PROGRESS", research_ref=research_ref,
                   test_campaign=True, job_id=job.job_id, correlation_id=job.correlation_id,
                   strategy_inputs={key: payload.get(key) for key in ("target_audience", "problem", "offer", "objective", "cta", "channels", "evidence_refs", "required_assets", "brand_constraints")})
        next_job = _enqueue(store, job, "MARKETING", "MARKETING_STRATEGY", campaign_id,
                            "research-marketing-handoff", {**row["strategy_inputs"], "research_ref": research_ref,
                            "target_audience": insight["target_audience"], "project_id": row.get("project_id"),
                            "workflow_stage": "MARKETING_STRATEGY", "input_artifact_ref": research_ref})
        row["strategy_job_id"] = next_job.job_id
    elif job.job_type == "MARKETING_STRATEGY":
        # Strategy inputs are supplied by the authorized requester/Atlas packet;
        # this persists a structured plan and does not call an external model.
        required = ("target_audience", "problem", "offer", "objective", "cta")
        missing = [key for key in required if not payload.get(key)]
        if missing:
            row.update(state="RESEARCH_REQUIRED", missing_strategy_fields=missing)
            _save_campaign(row)
            return {"status": "BLOCKED", "reason": "STRATEGY_INPUTS_REQUIRED", "missing": missing}
        strategy = {key: payload.get(key) for key in ("target_audience", "problem", "offer", "objective", "channels", "cta", "funnel_strategy", "email_strategy", "social_strategy", "measurement_plan", "recommended_budget", "evidence_refs", "brand_constraints", "required_assets", "priority", "deadline")}
        strategy.update({"campaign_id": campaign_id, "project_id": row.get("project_id"), "job_id": job.job_id,
            "correlation_id": job.correlation_id, "department": "MARKETING", "workflow_stage": "MARKETING_STRATEGY",
            "receipt_id": "receipt-pending:" + job.job_id, "created_at": now(), "approval_required": True, "paid_ads_default_deny": True})
        strategy.update({"customer_problem": payload.get("problem"), "value_proposition": payload.get("value_proposition") or "A clearer, evidence-aware readiness path.",
            "channel": payload.get("channels", ["INTERNAL_TEST"]), "primary_cta": payload.get("cta"),
            "message_angle": payload.get("message_angle") or payload.get("objective"),
            "content_format": payload.get("required_assets", ["LANDING_PAGE_COPY"]),
            "creative_requirements": payload.get("required_assets", ["LANDING_PAGE_COPY"]),
            "brand_requirements": payload.get("brand_constraints", []),
            "compliance_constraints": ["No guaranteed funding or approval claims", "Ray approval required before publication"],
            "budget_class": payload.get("budget_class", "ZERO_SPEND_INTERNAL"),
            "success_metrics": payload.get("success_metrics", ["CTA clarity", "disclaimer present", "artifact traceability"])})
        ref = store_payload(strategy, payload_id="strategy_" + _hash(campaign_id)[:24])
        if row.get("workflow_stage") == "RESEARCH_READY": _set_stage(row, "MARKETING_STRATEGY")
        row.update(state="STRATEGY_READY", strategy_ref=ref,
                   state_history=list(row.get("state_history", [])) + ["STRATEGY_IN_PROGRESS", "STRATEGY_READY"])
        next_job = _enqueue(store, job, "CREATIVE", "CREATIVE_BRIEF_BUILD", campaign_id, "strategy-ready", {"campaign_id": campaign_id, "strategy_ref": ref, "input_artifact_ref": ref, "business_id": row.get("business_id"), "project_id": row.get("project_id")})
        row.update(state="WAITING_CREATIVE",
                   state_history=list(row.get("state_history", [])) + ["WAITING_CREATIVE"])
        paid_budget = payload.get("paid_ad_budget") or payload.get("paid_campaign_budget")
        if paid_budget is not None and str(paid_budget).strip().upper() not in {"", "0", "0.0", "UNKNOWN", "NONE"}:
            finance_job = request_finance_review(campaign_id, job.job_id,
                business_reason=f"Review paid campaign budget for {campaign_id}", proposed_spend=paid_budget,
                expected_benefit=payload.get("expected_benefit", "UNKNOWN"))
            row["finance_review_job_id"] = finance_job["job_id"]
    elif job.job_type == "CREATIVE_BRIEF_BUILD":
        if row.get("test_campaign"):
            _set_stage(row, "CREATIVE_BRIEF")
        strategy = load_payload(payload.get("strategy_ref"))
        from nexus_agent_platform.creative.studio import build_creative_brief_from_growth, persist_creative_brief
        growth = {"growth_id": campaign_id, "topic": strategy.get("objective"), "objective": strategy.get("objective"), "target_audience": strategy.get("target_audience"), "target_offer": strategy.get("offer"), "primary_cta": strategy.get("cta"), "business_id": row.get("business_id"), "evidence_refs": strategy.get("evidence_refs", []), "status": "INTERNAL_DRAFT"}
        brief = build_creative_brief_from_growth(growth)
        brief.update({"campaign_id": campaign_id, "project_id": row.get("project_id"), "target_audience": strategy.get("target_audience"), "offer": strategy.get("offer"), "cta": strategy.get("cta"), "problem": strategy.get("problem"),
                      "campaign_objective": strategy.get("objective"), "channel": strategy.get("channels", []),
                      "format": strategy.get("required_assets", ["LANDING_PAGE_COPY", "VIDEO_STORYBOARD"]),
                      "brand_constraints": strategy.get("brand_constraints", []),
                      "required_assets": strategy.get("required_assets", ["LANDING_PAGE_COPY", "VIDEO_STORYBOARD"]),
                      "creative_direction": strategy.get("creative_direction", "evidence-aware, internal draft; preserve approved offer and CTA"),
                      "evidence_reference_inputs": strategy.get("evidence_refs", []),
                      "budget_envelope": {"max_estimated_cost": 0, "max_revisions": MAX_AUTONOMOUS_CREATIVE_REVISIONS},
                      "deadline": strategy.get("deadline"), "priority": strategy.get("priority", 50),
                      "approval_requirement": "RAY_APPROVAL_BEFORE_CONTROLLED_PUBLISH", "approval_required": True})
        brief.update({"hook": strategy.get("message_angle") or strategy.get("objective"),
                      "message": strategy.get("objective"), "asset_type": (strategy.get("required_assets") or ["LANDING_PAGE_COPY"])[0],
                      "dimensions": "1080x1080", "aspect_ratio": "1:1", "duration_seconds": None,
                      "prohibited_elements": ["guaranteed funding", "guaranteed approval", "unsupported outcomes"],
                      "provider_constraints": {"provider": "LOCAL_DETERMINISTIC", "expected_cost": 0,
                          "resource_class": "LIGHTWEIGHT_INTERNAL", "authorization": "TEST_ONLY", "fallback": "DENY"},
                      "acceptance_criteria": ["brief match", "explicit CTA", "adjacent educational disclaimer", "no prohibited claims"],
                      "budget_class": strategy.get("budget_class", "ZERO_SPEND_INTERNAL")})
        brief.update({"job_id": job.job_id, "correlation_id": job.correlation_id,
                      "department": "CREATIVE", "workflow_stage": "CREATIVE_BRIEF",
                      "receipt_id": "receipt-pending:" + job.job_id, "prompt_or_brief_ref": row.get("strategy_ref")})
        missing_brief = sorted(field for field in CREATIVE_BRIEF_FIELDS if field not in brief)
        if missing_brief:
            raise ValueError("CREATIVE_BRIEF_CONTRACT_MISSING:" + ",".join(missing_brief))
        saved = persist_creative_brief(brief)
        brief_ref = store_payload(saved, payload_id="brief_" + _hash(saved["creative_brief_id"])[:24])
        row.update(state="WAITING_CREATIVE", creative_state="BRIEF_RECEIVED", brief_id=saved["creative_brief_id"], brief_ref=brief_ref,
                   state_history=list(row.get("state_history", [])) + ["CREATIVE_BRIEF_READY", "WAITING_CREATIVE"])
        next_job = _enqueue(store, job, "CREATIVE", "CREATIVE_ASSET_GENERATE", campaign_id, "brief-ready", {"campaign_id": campaign_id, "brief_id": saved["creative_brief_id"], "brief_ref": brief_ref, "input_artifact_ref": brief_ref, "project_id": row.get("project_id")})
    elif job.job_type in {"CREATIVE_ASSET_GENERATE", "CREATIVE_ASSET_REVISE", "CREATIVE_QA"}:
        if job.job_type == "CREATIVE_ASSET_REVISE" and int(row.get("revision_count", 0)) >= MAX_AUTONOMOUS_CREATIVE_REVISIONS:
            row.update(state="RAY_REVIEW_REQUIRED", approval_state="READY_FOR_RAY_REVIEW")
            _save_campaign(row)
            return {"status": "BLOCKED", "reason": "REVISION_LIMIT_REACHED"}
        from nexus_agent_platform.creative.studio import build_copy_asset, build_storyboard_asset, persist_creative_asset
        # Carry an opaque local brief reference so workers never scan campaign history.
        brief = load_payload(payload.get("brief_ref"))
        if brief.get("creative_brief_id") != payload.get("brief_id"):
            raise ValueError("CREATIVE_BRIEF_REFERENCE_MISMATCH")
        if row.get("test_campaign"):
            _set_stage(row, "CREATIVE_PRODUCTION")
        row["creative_provider_route"] = {"provider": "LOCAL_DETERMINISTIC", "model": None,
            "expected_cost": 0, "resource_class": "LIGHTWEIGHT_INTERNAL",
            "authorization": "TEST_ONLY" if row.get("test_campaign") else "LOCAL_NO_PROVIDER",
            "fallback": "DENY_UNKNOWN_PROVIDER", "provider_call": False}
        creative_state_history = list(row.get("creative_state_history", [])) + ["ASSET_PLAN", "PROVIDER_SELECTION", "GENERATING", "QA"]
        if payload.get("feedback"):
            brief = {**brief, "revision_feedback": str(payload["feedback"])[:1000]}
        generated = [build_copy_asset(brief)]
        if not row.get("test_campaign"):
            generated.append(build_storyboard_asset(brief))
        for asset in generated:
            asset.update({"campaign_id": campaign_id, "project_id": row.get("project_id"),
                          "job_id": job.job_id, "correlation_id": job.correlation_id,
                          "department": "CREATIVE", "workflow_stage": "CREATIVE_PRODUCTION",
                          "prompt_or_brief_ref": payload.get("brief_ref"),
                          "receipt_id": "receipt-pending:" + job.job_id})
        generated = [persist_creative_asset(asset) for asset in generated]
        refs = []
        for asset in generated:
            refs.append(LocalArtifactStore().put_json(asset, campaign_id, asset["asset_id"]))
        from nexus_agent_platform.marketing_supabase_state import record_asset_metadata
        for asset, artifact_ref in zip(generated, refs):
            record_asset_metadata(
                asset_id=asset["asset_id"], campaign_id=campaign_id,
                project_id=str(row.get("project_id") or "NEXUS"),
                asset_type=asset["asset_type"], artifact_ref=artifact_ref["artifact_ref"],
                sha256=artifact_ref["sha256"], size_bytes=artifact_ref["size_bytes"],
                mime_type=artifact_ref["mime_type"], status=asset["status"],
                approval_state=asset["approval_state"],
                version=int(row.get("revision_count", 0)) + (2 if job.job_type == "CREATIVE_ASSET_REVISE" else 1),
            )
        row.update(state="ASSETS_READY", creative_state="READY_FOR_MARKETING", creative_state_history=creative_state_history + ["READY_FOR_MARKETING"],
                   state_history=list(row.get("state_history", [])) + ["ASSETS_READY", "MARKETING_QA"],
                   asset_ids=list(dict.fromkeys([*row.get("asset_ids", []), *[a["asset_id"] for a in generated]])), revision_count=int(row.get("revision_count", 0)) + (job.job_type == "CREATIVE_ASSET_REVISE"), artifact_refs=[*row.get("artifact_refs", []), *refs])
        next_job = _enqueue(store, job, "MARKETING", "MARKETING_ASSET_REVIEW", campaign_id, "creative-assets-ready", {"campaign_id": campaign_id, "brief_id": payload.get("brief_id"), "asset_ids": row["asset_ids"], "input_artifact_ref": refs[-1]["artifact_ref"], "project_id": row.get("project_id")})
    elif job.job_type == "MARKETING_ASSET_REVIEW":
        package = build_review_package(campaign_id, payload)
        if row.get("test_campaign"):
            _set_stage(row, "MARKETING_REVIEW")
            revision = int(row.get("revision_count", 0))
            asset_id = (payload.get("asset_ids") or [])[-1]
            asset_path = ARTIFACTS / _hash(campaign_id)[:24] / f"{_hash(asset_id)[:24]}.json"
            asset_record = _read(asset_path, {}) or {}
            content = asset_record.get("content") if isinstance(asset_record.get("content"), dict) else {}
            criteria = {"brief_match": asset_record.get("creative_brief_id") == row.get("brief_id"),
                        "cta_present": bool(content.get("cta")),
                        "cta_clarity": bool(content.get("revision_applied")) if revision else False,
                        "disclaimer_present": bool(content.get("disclaimer")),
                        "prohibited_claims_absent": not any(term in json.dumps({key: value for key, value in content.items() if key != "disclaimer"}).lower() for term in ("guaranteed funding", "guaranteed approval")),
                        "internal_only": bool(content.get("internal_only"))}
            decision = "ACCEPT" if all(criteria.values()) else "REVISE"
            reasons = [] if decision == "ACCEPT" else ["Clarify the concrete next step in the CTA and keep the educational disclaimer adjacent."]
            review_id = "review_" + _hash([campaign_id, asset_id, decision])[:24]
            review = {"review_id": review_id, "campaign_id": campaign_id, "asset_id": asset_id,
                      "job_id": job.job_id, "correlation_id": job.correlation_id,
                      "department": "MARKETING", "decision": decision, "score": 92 if decision == "ACCEPT" else 78,
                      "acceptance_criteria_results": criteria,
                      "revision_reasons": reasons, "marketing_notes": "Structured deterministic canary review; internal test only.",
                      "next_stage": "CREATIVE_REVISION" if decision == "REVISE" else "APPROVAL_PENDING",
                      "created_at": now(), "receipt_id": "receipt-pending:" + job.job_id}
            review_ref = store_payload(review, payload_id=review_id)
            row.setdefault("review_refs", []).append(review_ref)
            row.setdefault("review_decisions", []).append(decision)
            row["review_package_ref"] = str(package)
            row["last_review_id"] = review_id
            if decision == "REVISE":
                if revision >= MAX_AUTONOMOUS_CREATIVE_REVISIONS:
                    _set_stage(row, "BLOCKED")
                    row.update(state="BLOCKED", approval_state="HUMAN_REVIEW_REQUIRED")
                else:
                    _set_stage(row, "CREATIVE_REVISION")
                    row.update(state="MARKETING_QA", creative_state="REVISION_REQUIRED")
                    next_job = _enqueue(store, job, "CREATIVE", "CREATIVE_ASSET_REVISE", campaign_id,
                        f"marketing-revise:{review_id}", {"campaign_id": campaign_id, "brief_id": row["brief_id"],
                        "brief_ref": row["brief_ref"], "feedback": reasons[0], "input_artifact_ref": (row.get("artifact_refs") or [{}])[-1].get("artifact_ref", asset_id),
                        "workflow_stage": "CREATIVE_REVISION", "review_id": review_id})
            else:
                _set_stage(row, "APPROVAL_PENDING")
                row.update(state="APPROVAL_PENDING", creative_state="COMPLETE", approval_state="PENDING_RAY_APPROVAL",
                           review_package_ref=str(package), publication_attempts=0, publish_execution="BLOCKED_BY_APPROVAL")
                handoff_id = "handoff_" + _hash([campaign_id, "publishing-ready", job.job_id])[:24]
                publishing = {"handoff_id": handoff_id, "campaign_id": campaign_id,
                    "project_id": row.get("project_id"), "job_id": job.job_id,
                    "correlation_id": job.correlation_id, "department": "MARKETING",
                    "workflow_stage": "PUBLISHING_READY", "marketing_accepted_asset_refs": row.get("artifact_refs", []),
                    "marketing_accepted_copy_ref": row.get("artifact_refs", [None])[-1],
                    "channel": "INTERNAL_TEST", "target_destination": "NONE",
                    "approval_state": "PENDING_RAY_APPROVAL", "publishing_policy": "NO_EXTERNAL_ACTION",
                    "required_credentials": [], "budget_authorization_state": "NONE",
                    "execution_state": "BLOCKED_BY_APPROVAL", "publication_attempts": 0,
                    "created_at": now(), "receipt_id": "receipt-pending:" + job.job_id}
                publish_ref = store_payload(publishing, payload_id=handoff_id)
                _write(RUNTIME / "handoffs" / f"{handoff_id}.json", publishing)
                row["publishing_handoff_ref"] = publish_ref
                row.setdefault("handoff_ids", []).append(handoff_id)
                if job.governance_context.get("test_campaign"):
                    metrics = {"data_class": "TEST", "impressions": 0, "views": 0, "clicks": 0,
                        "ctr": None, "leads": 0, "conversions": 0, "cost": 0,
                        "cpa": None, "revenue": 0, "roas": None, "engagement": 0,
                        "asset_performance": "NOT_PUBLISHED", "channel_performance": "NOT_PUBLISHED"}
                    next_job = _enqueue(store, job, "MARKETING", "PERFORMANCE_COLLECT", campaign_id,
                        "synthetic-test-performance", {"campaign_id": campaign_id, "test_metrics": metrics,
                        "input_artifact_ref": publish_ref, "workflow_stage": "PERFORMANCE_COLLECTION"})
        else:
            row.update(state="RAY_REVIEW_REQUIRED", creative_state="COMPLETE", approval_state="READY_FOR_RAY_REVIEW", review_package_ref=str(package),
                       state_history=list(row.get("state_history", [])) + ["RAY_REVIEW_REQUIRED"])
    elif job.job_type == "MARKETING_FINANCE_REVIEW_RESULT":
        row.update(
            finance_review_state="REVIEW_COMPLETE",
            finance_request_id=payload.get("finance_request_id"),
            finance_result_ref=job.payload_ref,
            finance_recommendation=payload.get("recommendation", "UNKNOWN"),
            finance_budget_available=payload.get("available_budget", "UNKNOWN"),
            spend_authorized=False,
        )
    elif job.job_type in {"MARKETING_RESEARCH_REQUEST", "LANDING_PAGE_BUILD", "LANDING_PAGE_VERIFY", "PERFORMANCE_COLLECT", "MARKETING_PERFORMANCE_ANALYZE"}:
        if job.job_type == "MARKETING_RESEARCH_REQUEST":
            result = request_research(campaign_id, job.job_id,
                question=str(payload.get("question") or payload.get("evidence_gap") or "Verify the supplied audience, competitor, channel, customer, keyword, offer, or creative trend evidence gap."),
                evidence_gap_id=str(payload.get("evidence_gap_id") or _hash(payload)[:24]))
            next_job = store.get(result["job_id"])
            row = campaign(campaign_id) or row
            saved = _save_campaign(row)
            return {"status": "COMPLETED", "campaign_id": campaign_id, "state": saved["state"], "next_job_id": next_job.job_id, "external_action_performed": False}
        event = {"MARKETING_RESEARCH_REQUEST": ("RESEARCH", "RESEARCH_GAP_VERIFY"), "LANDING_PAGE_BUILD": ("CREATIVE", "LANDING_PAGE_VERIFY"), "LANDING_PAGE_VERIFY": None, "PERFORMANCE_COLLECT": ("MARKETING", "MARKETING_PERFORMANCE_ANALYZE"), "MARKETING_PERFORMANCE_ANALYZE": None}.get(job.job_type)
        if job.job_type == "LANDING_PAGE_VERIFY":
            row["landing_page_verification"] = {"status": "VERIFIED_LOCAL_FIXTURE", "page_ref": payload.get("page_ref"), "cta": payload.get("cta")}
            row["state"] = "MARKETING_QA"
        elif job.job_type == "PERFORMANCE_COLLECT" and job.governance_context.get("test_campaign"):
            metrics = payload.get("test_metrics")
            if not isinstance(metrics, dict) or metrics.get("data_class") != "TEST" or any(float(metrics.get(key) or 0) != 0 for key in ("cost", "revenue", "impressions", "views", "clicks", "leads", "conversions")):
                raise PermissionError("TEST_PERFORMANCE_MUST_BE_ZEROED_SYNTHETIC_DATA")
            if row.get("workflow_stage") == "APPROVAL_PENDING": _set_stage(row, "PERFORMANCE_COLLECTION")
            performance_id = "performance_" + _hash([campaign_id, job.job_id])[:24]
            performance_ref = store_payload({"artifact_id": performance_id, "campaign_id": campaign_id,
                "job_id": job.job_id, "correlation_id": job.correlation_id, "department": "MARKETING",
                "workflow_stage": "PERFORMANCE_COLLECTION", "data_class": "TEST", "metrics": metrics,
                "created_at": now(), "receipt_id": "receipt-pending:" + job.job_id}, payload_id=performance_id)
            row.update(state="ANALYZING", performance_ref=performance_ref)
            payload = {**payload, "performance_ref": performance_ref}
        elif job.job_type == "MARKETING_PERFORMANCE_ANALYZE":
            if job.governance_context.get("test_campaign"):
                if row.get("workflow_stage") == "PERFORMANCE_COLLECTION": _set_stage(row, "MARKETING_ANALYSIS")
                performance = load_payload(payload.get("performance_ref"))
                if performance.get("data_class") != "TEST": raise PermissionError("NON_TEST_PERFORMANCE_ARTIFACT_NOT_ALLOWED_IN_CANARY")
                analysis = {"artifact_id": "analysis_" + _hash([campaign_id, job.job_id])[:24],
                    "campaign_id": campaign_id, "job_id": job.job_id, "correlation_id": job.correlation_id,
                    "department": "MARKETING", "workflow_stage": "MARKETING_ANALYSIS", "data_class": "TEST",
                    "what_worked": "The readiness message retained an explicit next step and educational disclaimer.",
                    "what_failed": "No real performance observations exist because the asset was not published.",
                    "hypothesis": "A clearer next step may improve engagement if later approved and published.",
                    "next_action": "Review the iteration proposal; do not launch another campaign automatically.",
                    "strategy_change": "Retain educational readiness framing.",
                    "creative_change": "Keep the CTA explicit and the disclaimer adjacent.",
                    "channel_change": "None; test channel is internal only.", "continue_iterate_complete": "ITERATE",
                    "recommendation": "ITERATE", "summary": "Internal test analysis; no production performance inferred.",
                    "performance_ref": payload.get("performance_ref"), "created_at": now()}
                row["analysis_ref"] = store_payload(analysis, payload_id=analysis["artifact_id"])
                _set_stage(row, "ITERATION")
            else:
                analysis = {"recommendation": payload.get("recommendation", "RAY_REVIEW"), "summary": payload.get("summary", ""), "created_at": now()}
            row["performance_analysis"] = analysis
            row["state"] = "ITERATION_READY" if analysis["recommendation"] == "ITERATE" else "COMPLETE"
            row["state_history"] = list(row.get("state_history", [])) + ["ANALYZING", row["state"]]
        else:
            row.update(state="BLOCKED" if not event else row.get("state", "REQUEST_RECEIVED"))
        if event:
            next_job = _enqueue(store, job, *event, campaign_id, f"{job.job_type.lower()}-complete", {**payload, "campaign_id": campaign_id, "workflow_stage": "MARKETING_ANALYSIS" if job.job_type == "PERFORMANCE_COLLECT" and job.governance_context.get("test_campaign") else payload.get("workflow_stage")})
    elif job.job_type in {"MARKETING_PUBLISH_PREP", "CONTROLLED_EMAIL_SEND", "CONTROLLED_SOCIAL_POST"}:
        # This bounded adapter prepares governed jobs only; no external action here.
        if job.job_type == "MARKETING_PUBLISH_PREP":
            row.update(state="READY_FOR_CONTROLLED_PUBLISH", publish_jobs_prepared=True, external_action_performed=False)
            for channel in payload.get("channels", []):
                value = str(channel).upper()
                action = "CONTROLLED_EMAIL_SEND" if "EMAIL" in value else "CONTROLLED_SOCIAL_POST" if any(term in value for term in ("SOCIAL", "META", "INSTAGRAM", "FACEBOOK", "TIKTOK", "YOUTUBE")) else None
                if action:
                    child = _enqueue(store, job, "MARKETING", action, campaign_id, f"controlled-action:{value}", {"campaign_id": campaign_id, "channel": channel, "approval_state": row.get("approval_state"), "action_classification": "TEST"})
                    row.setdefault("external_action_job_ids", []).append(child.job_id)
        else:
            row.update(state="BLOCKED", external_action_performed=False)
            _save_campaign(row)
            return {"status": "BLOCKED", "reason": "EXTERNAL_ACTION_DISABLED_IN_LOCAL_CERTIFICATION", "campaign_id": campaign_id}
    else:
        raise ValueError("UNSUPPORTED_MARKETING_CREATIVE_JOB")
    saved = _save_campaign(row)
    return {"status": "COMPLETED", "campaign_id": campaign_id, "state": saved["state"], "next_job_id": next_job.job_id if next_job else None, "external_action_performed": False}


def record_job_receipt(job, receipt_id: str) -> None:
    """Attach the durable queue receipt to its local handoff/artifact record."""
    try:
        payload = load_payload(job.payload_ref)
    except (ValueError, OSError):
        payload = {}
    handoff_id = payload.get("handoff_id")
    if handoff_id:
        path = RUNTIME / "handoffs" / f"{Path(str(handoff_id)).name}.json"
        handoff = _read(path)
        if _attach_handoff_receipt(handoff, job.job_id, receipt_id):
            handoff["updated_at"] = now()
            _write(path, handoff)
    campaign_id = str(payload.get("campaign_id") or "")
    row = campaign(campaign_id) if campaign_id else None
    if not row and job.job_type == "RESEARCH_MARKETING_TEST_HANDOFF":
        row = campaign(str(payload.get("campaign_id") or ""))
    if row:
        refs = [row.get(key) for key in ("research_ref", "strategy_ref", "brief_ref", "performance_ref", "analysis_ref", "publishing_handoff_ref")]
        refs.extend(row.get("review_refs", []))
        artifact_paths = [ref for ref in (row.get("artifact_refs") or []) if isinstance(ref, dict)]
        for ref in refs:
            if ref:
                try:
                    artifact = load_payload(str(ref))
                except (ValueError, OSError):
                    artifact = None
                if artifact and artifact.get("job_id") == job.job_id:
                    artifact["receipt_id"] = receipt_id
                    artifact["updated_at"] = now()
                    store_payload(artifact, payload_id=str(ref))
                    if artifact.get("handoff_id"):
                        _write(RUNTIME / "handoffs" / f"{Path(str(artifact['handoff_id'])).name}.json", artifact)
        for ref in artifact_paths:
            location = ref.get("artifact_ref", "")
            if not str(location).startswith("local://"):
                continue
            path = ARTIFACTS / Path(str(location)[8:])
            artifact = _read(path)
            if artifact and artifact.get("job_id") == job.job_id:
                artifact["receipt_id"] = receipt_id
                artifact["updated_at"] = now()
                _write(path, artifact)


def _attach_handoff_receipt(handoff: dict[str, Any] | None, job_id: str, receipt_id: str) -> bool:
    """Never attach a retry's receipt to a prior attempt's handoff record."""
    if not handoff or handoff.get("job_id") != job_id:
        return False
    handoff["receipt_id"] = receipt_id
    return True


class LocalArtifactStore:
    provider = "LOCAL_WORKING"

    def put_json(self, value: Mapping[str, Any], campaign_id: str, artifact_id: str) -> dict[str, Any]:
        raw = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
        digest = hashlib.sha256(raw).hexdigest()
        path = ARTIFACTS / _hash(campaign_id)[:24] / f"{_hash(artifact_id)[:24]}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_bytes(raw)
        return {"storage_provider": self.provider, "artifact_ref": "local://" + path.relative_to(ARTIFACTS).as_posix(), "sha256": digest, "size_bytes": len(raw), "mime_type": "application/json"}


class R2ArtifactStore:
    """Optional S3-compatible R2 adapter; never selected without explicit config."""
    provider = "CLOUDFLARE_R2"

    @staticmethod
    def available(environ: Mapping[str, str] | None = None) -> bool:
        env = environ or os.environ
        return all(env.get(x) for x in ("R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_BUCKET"))

    def put(self, source: Path, object_key: str) -> dict[str, Any]:
        if not self.available():
            raise RuntimeError("R2_CONFIGURATION_UNAVAILABLE")
        import boto3  # optional dependency, only loaded for explicitly configured R2
        env = os.environ
        client = boto3.client("s3", endpoint_url=f"https://{env['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com", aws_access_key_id=env["R2_ACCESS_KEY_ID"], aws_secret_access_key=env["R2_SECRET_ACCESS_KEY"])
        client.upload_file(str(source), env["R2_BUCKET"], object_key)
        return {"storage_provider": self.provider, "artifact_ref": object_key, "size_bytes": source.stat().st_size}


def build_review_package(campaign_id: str, payload: Mapping[str, Any]) -> Path:
    row = campaign(campaign_id) or {}
    folder = REVIEWS / _hash(campaign_id)[:24] / "review"
    folder.mkdir(parents=True, exist_ok=True)
    summary = {"campaign_id": campaign_id, "project_id": row.get("project_id"), "state": "READY_FOR_RAY_REVIEW", "approval_state": "READY_FOR_RAY_REVIEW", "asset_ids": payload.get("asset_ids", []), "approval_channel": "CODEX_LOCAL_REVIEW", "external_action_performed": False}
    (folder / "campaign_summary.md").write_text("# Campaign review\n\n" + "\n".join(f"- {k}: {v}" for k, v in summary.items()) + "\n")
    _write(folder / "asset_manifest.json", {"campaign_id": campaign_id, "assets": payload.get("asset_ids", []), "artifact_refs": row.get("artifact_refs", [])})
    copy_lines = ["# Copy variants", "", "Internal review only.", ""]
    for media_dir in ("images", "videos", "audio"):
        (folder / media_dir).mkdir(exist_ok=True)
    for asset_id in payload.get("asset_ids", [])[:20]:
        source = ARTIFACTS / _hash(campaign_id)[:24] / f"{_hash(asset_id)[:24]}.json"
        asset = _read(source, {})
        kind = str(asset.get("asset_type", "ASSET"))
        if kind == "LANDING_PAGE_COPY":
            content = asset.get("content", {})
            copy_lines.extend([f"## {asset_id}", "", *(f"- {x}" for x in content.get("headline_options", [])), "", str(content.get("body", "")), "", f"CTA: {content.get('cta', '')}", f"Disclaimer: {content.get('disclaimer', '')}", ""])
        elif kind == "VIDEO_STORYBOARD":
            _write(folder / "videos" / f"{_hash(asset_id)[:16]}.json", asset)
        elif kind.startswith("IMAGE"):
            _write(folder / "images" / f"{_hash(asset_id)[:16]}.json", asset)
    (folder / "copy_variants.md").write_text("\n".join(copy_lines))
    strategy = load_payload(row.get("strategy_ref")) if row.get("strategy_ref") else {}
    page = "<!doctype html><meta charset='utf-8'><title>" + html.escape(str(strategy.get("objective", "Campaign preview"))) + "</title><main><h1>" + html.escape(str(strategy.get("offer", ""))) + "</h1><p>" + html.escape(str(strategy.get("problem", ""))) + "</p><a href='#'>" + html.escape(str(strategy.get("cta", ""))) + "</a><p>Internal preview only. No external publishing.</p></main>"
    (folder / "landing_page_preview.html").write_text(page)
    _write(folder / "approval_status.json", {"campaign_id": campaign_id, "state": "READY_FOR_RAY_REVIEW", "channel": "CODEX_LOCAL_REVIEW", "updated_at": now()})
    return folder


def explicit_ray_decision(campaign_id: str, command: str, *, feedback: str = "", actor: str = "ray") -> dict[str, Any]:
    decisions = {"APPROVE_CAMPAIGN": "APPROVED_BY_RAY", "APPROVE_ASSET": "APPROVED_BY_RAY", "REQUEST_REVISION": "REVISION_REQUESTED_BY_RAY", "REJECT_VERSION": "REJECTED_BY_RAY"}
    if command not in decisions:
        raise ValueError("EXPLICIT_RAY_COMMAND_REQUIRED")
    row = campaign(campaign_id)
    if not row or row.get("approval_state") != "READY_FOR_RAY_REVIEW":
        raise ValueError("CAMPAIGN_NOT_AWAITING_RAY_REVIEW")
    state = decisions[command]
    row.update(approval_state=state, ray_feedback=feedback[:1000], approval_actor=actor, approval_command=command)
    if state == "APPROVED_BY_RAY":
        row["state"] = "READY_FOR_CONTROLLED_PUBLISH"
        store = default_store()
        parent = store.get(row.get("job_id"))
        if parent:
            strategy = load_payload(row.get("strategy_ref")) if row.get("strategy_ref") else {}
            job = _enqueue(store, parent, "MARKETING", "MARKETING_PUBLISH_PREP", campaign_id, f"ray-approved:{command}", {"campaign_id": campaign_id, "approval_state": state, "channels": strategy.get("channels", [])})
            row["publish_job_id"] = job.job_id
    elif state == "REVISION_REQUESTED_BY_RAY":
        if int(row.get("revision_count", 0)) >= MAX_AUTONOMOUS_CREATIVE_REVISIONS:
            row["state"] = "RAY_REVIEW_REQUIRED"
        else:
            row["state"] = "MARKETING_QA"
            row["creative_state"] = "REVISION_REQUIRED"
            store = default_store()
            parent = store.get(row.get("job_id"))
            if parent and row.get("brief_id") and row.get("brief_ref"):
                job = _enqueue(store, parent, "CREATIVE", "CREATIVE_ASSET_REVISE", campaign_id,
                    f"ray-revision:{int(row.get('revision_count', 0)) + 1}",
                    {"campaign_id": campaign_id, "brief_id": row["brief_id"], "brief_ref": row["brief_ref"], "feedback": feedback[:1000]})
                row["revision_job_id"] = job.job_id
    else:
        row["state"] = "BLOCKED"
    _save_campaign(row)
    folder = REVIEWS / _hash(campaign_id)[:24] / "review"
    _write(folder / "approval_status.json", {"campaign_id": campaign_id, "state": state, "command": command, "updated_at": now()})
    return row


def health(campaign_id: str) -> dict[str, Any]:
    row = campaign(campaign_id)
    return {key: row.get(key) for key in ("campaign_id", "project_id", "state", "approval_state", "job_id", "asset_ids", "revision_count")} if row else {}


def publication_result_event(campaign_id: str, parent_job_id: str, *, result_ref: str,
                             mock: bool = False) -> dict[str, Any]:
    """Persist an execution receipt event and enqueue bounded measurement work.

    ``mock=True`` is reserved for local certification fixtures. Real callers
    must invoke this only after the governed external-action worker completes.
    """
    if mock and os.environ.get("NEXUS_CERTIFICATION_MODE", "").lower() not in {"1", "true", "yes"}:
        raise PermissionError("MOCK_PUBLICATION_EVENT_REQUIRES_CERTIFICATION_MODE")
    row = campaign(campaign_id)
    if not row or row.get("approval_state") != "APPROVED_BY_RAY":
        raise PermissionError("RAY_APPROVAL_REQUIRED")
    store = default_store()
    parent = store.get(parent_job_id)
    if not parent:
        raise ValueError("PARENT_JOB_NOT_FOUND")
    row.update(state="MEASURING", publication_result_ref=result_ref, publication_result_mock=bool(mock),
               state_history=list(row.get("state_history", [])) + ["PUBLISHING", "MEASURING"])
    _save_campaign(row)
    child = _enqueue(store, parent, "MARKETING", "PERFORMANCE_COLLECT", campaign_id,
                     f"publication-complete:{result_ref}", {"campaign_id": campaign_id, "publication_result_ref": result_ref, "mock": bool(mock)})
    return {"status": "MEASUREMENT_QUEUED", "next_job_id": child.job_id}


def request_research(campaign_id: str, parent_job_id: str, *, question: str,
                     evidence_gap_id: str) -> dict[str, Any]:
    """Create one durable Research request for a specific evidence gap."""
    if not question.strip() or not evidence_gap_id.strip():
        raise ValueError("RESEARCH_GAP_CONTRACT_REQUIRED")
    row = campaign(campaign_id)
    if not row:
        raise ValueError("CAMPAIGN_NOT_FOUND")
    store = default_store()
    parent = store.get(parent_job_id)
    if not parent:
        raise ValueError("PARENT_JOB_NOT_FOUND")
    work_id = "marketing-research-" + _hash([campaign_id, evidence_gap_id])[:24]
    from nexus_agent_platform.research_work_queue import ResearchWorkQueue
    ResearchWorkQueue().enqueue(work_id=work_id, work_class="ASSIGNED", status="QUEUED",
        source_type="RESEARCH_OBJECTIVE", source_id=campaign_id, objective_id=campaign_id,
        title=f"Marketing evidence gap: {question[:160]}", question=question[:1200],
        research_question=question[:1200], objective=question[:1200],
        department_target="MARKETING", requested_by="MARKETING_DURABLE_WORKFLOW",
        parent_request_id=campaign_id, dedup_key=f"marketing:{campaign_id}:{evidence_gap_id}")
    map_path = RUNTIME / "research_campaign_refs.json"
    mapping = _read(map_path, {}) or {}
    mapping[work_id] = {"campaign_id": campaign_id, "evidence_gap_id": evidence_gap_id}
    _write(map_path, mapping)
    child = create_next_job(store, parent, department="RESEARCH", job_type="MARKETING_RESEARCH_GAP_VERIFY",
                            payload_ref=work_id, event_id=f"{campaign_id}:research-gap:{evidence_gap_id}")
    row.update(state="RESEARCH_REQUIRED", research_job_id=child.job_id)
    _save_campaign(row)
    return {"status": "RESEARCH_QUEUED", "job_id": child.job_id}


def request_finance_review(campaign_id: str, parent_job_id: str, *, business_reason: str,
                           proposed_spend: Any = "UNKNOWN", expected_benefit: Any = "UNKNOWN") -> dict[str, Any]:
    """Route material campaign budget proposals to Finance without authority to spend."""
    row = campaign(campaign_id)
    store = default_store()
    parent = store.get(parent_job_id)
    if not row or not parent:
        raise ValueError("CAMPAIGN_OR_PARENT_JOB_NOT_FOUND")
    payload = {"campaign_id": campaign_id, "project_id": row.get("project_id"), "business_reason": business_reason,
               "current_limitation": "Proposed campaign spend requires independent Finance review.",
               "proposed_spend": proposed_spend, "expected_benefit": expected_benefit,
               "event_id": f"finance-review:{campaign_id}"}
    child = _enqueue(store, parent, "FINANCE", "FINANCE_CAMPAIGN_REVIEW", campaign_id,
                     f"finance-review:{_hash(payload)[:20]}", payload)
    return {"status": "FINANCE_REVIEW_QUEUED", "job_id": child.job_id}


def research_completed_event(job, *, result_ref: str) -> dict[str, Any]:
    mapping = _read(RUNTIME / "research_campaign_refs.json", {}) or {}
    info = mapping.get(job.payload_ref)
    if not info:
        raise ValueError("MARKETING_RESEARCH_CORRELATION_NOT_FOUND")
    campaign_id = info["campaign_id"]
    row = campaign(campaign_id)
    if not row or not row.get("strategy_ref"):
        raise ValueError("MARKETING_STRATEGY_NOT_FOUND")
    strategy = load_payload(row["strategy_ref"])
    refs = list(strategy.get("evidence_refs") or [])
    refs.append(result_ref)
    strategy["evidence_refs"] = list(dict.fromkeys(refs))[:20]
    strategy["research_gap_closed"] = info["evidence_gap_id"]
    strategy_ref = store_payload(strategy, payload_id="strategy_research_" + _hash([campaign_id, info["evidence_gap_id"]])[:24])
    child = _enqueue(default_store(), job, "MARKETING", "MARKETING_STRATEGY", campaign_id,
                     f"research-closed:{info['evidence_gap_id']}", {"campaign_id": campaign_id, "strategy_ref": strategy_ref,
                     "target_audience": strategy.get("target_audience"), "problem": strategy.get("problem"),
                     "offer": strategy.get("offer"), "objective": strategy.get("objective"), "cta": strategy.get("cta"),
                     "channels": strategy.get("channels"), "evidence_refs": strategy["evidence_refs"]})
    row.update(state="STRATEGY_IN_PROGRESS", research_result_ref=result_ref)
    _save_campaign(row)
    return {"status": "MARKETING_STRATEGY_RESUMED", "next_job_id": child.job_id}


def durable_handoff_event(parent_job_id: str, *, handoff_ref: str, to_department: str,
                          workflow_permits: bool, event_id: str) -> dict[str, Any]:
    """Adapt an already persisted formal handoff into dispatcher-owned delivery."""
    if not workflow_permits:
        raise PermissionError("WORKFLOW_DOES_NOT_PERMIT_HANDOFF")
    if not handoff_ref or ":" not in handoff_ref:
        raise ValueError("PERSISTED_HANDOFF_REFERENCE_REQUIRED")
    store = default_store()
    parent = store.get(parent_job_id)
    if not parent:
        raise ValueError("PARENT_JOB_NOT_FOUND")
    child = create_next_job(store, parent, department=to_department.upper(), job_type="HANDOFF_DELIVERY",
                            payload_ref=handoff_ref, event_id=f"formal-handoff:{event_id}")
    return {"status": "HANDOFF_DELIVERY_QUEUED", "job_id": child.job_id}
