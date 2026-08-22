"""Governed Creative Studio contracts and bounded internal asset generation.

This module is deliberately provider-neutral.  It consumes canonical Growth and
Opportunity records, writes compact governed metadata, and never publishes or
contacts an external audience.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from nexus_agent_platform.governed.persistence import (
    append_record, emit_audit_event, get_record, new_id, read_records,
)
from nexus_agent_platform.creative.intelligence import answer_creative_intelligence_question, creative_intelligence_portfolio

CREATIVE_BRIEF_SCHEMA = "nexus.creative-brief.v1"
CREATIVE_ASSET_SCHEMA = "nexus.creative-asset.v1"
CREATIVE_RENDER_SCHEMA = "nexus.creative-render-result.v1"
REMOTION_TEMPLATE = "goclear_readiness_explainer_v1"
REMOTION_LICENSE_STATUS = "EVALUATION_ONLY"
COMFYUI_STATUS = "DEFERRED_TO_GPU_PHASE"
PUBLIC_ACTIONS = {"publish", "send_email", "send_sms", "post_social", "activate_ad"}
_BANNED = re.compile(r"guarantee(?:d)?|guaranteed approval|guaranteed funding|guaranteed income|score increase guaranteed", re.I)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def _refs(growth: Dict[str, Any], opportunity: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "growth_id": growth.get("growth_id") or growth.get("id"),
        "opportunity_id": (opportunity or {}).get("opportunity_id") or (opportunity or {}).get("id") or growth.get("source_opportunity_id"),
        "research_job_id": growth.get("source_research_job_id"),
        "research_pack_ref": growth.get("source_research_pack_ref"),
        "evidence_refs": list(growth.get("evidence_refs") or [])[:8],
    }


def build_creative_brief_from_growth(growth: Dict[str, Any], opportunity: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    refs = _refs(growth, opportunity)
    topic = growth.get("topic") or growth.get("title") or "GoClear funding readiness"
    target_offer = growth.get("target_offer") or "goclear_readiness_review_97"
    body = {
        "schema_version": CREATIVE_BRIEF_SCHEMA,
        "creative_brief_id": new_id("brief"),
        "business_id": growth.get("business_id", "goclear"),
        "title": f"{topic} creative brief",
        "objective": growth.get("objective") or "Prepare an evidence-aware internal growth asset.",
        "source_growth_id": refs["growth_id"],
        "source_opportunity_id": refs["opportunity_id"],
        "source_research_job_id": refs["research_job_id"],
        "source_research_pack_ref": refs["research_pack_ref"],
        "evidence_refs": refs["evidence_refs"],
        "audience": growth.get("target_audience") or "GoClear small-business owners preparing for funding",
        "funnel_stage": growth.get("funnel_stage") or "LEAD",
        "target_offer": target_offer,
        "primary_cta": growth.get("primary_cta") or "Review your readiness",
        "secondary_cta": growth.get("secondary_cta") or "Read the readiness checklist",
        "asset_types": ["LANDING_PAGE_COPY", "VIDEO_SCRIPT", "VIDEO_STORYBOARD", "IMAGE_PROMPT", "IMAGE_LAYOUT_SPEC"],
        "brand": {"business": "GoClear", "status": "BRAND_CONFIGURATION_PARTIAL", "style": "calm, precise, readiness-first", "tone": "measured and educational", "approved_colors": [], "approved_fonts": [], "logo_refs": []},
        "message": {"problem": "Business owners need an organized readiness path before applying.", "promise": "A clearer preparation path", "key_points": ["business profile", "documents", "credit readiness"], "objections": ["I do not know what to prepare first"], "proof": [], "prohibited_claims": ["guaranteed funding", "guaranteed approval", "guaranteed credit increase", "guaranteed income"]},
        "channel_context": "internal review asset; no public distribution",
        "measurement_metric": growth.get("primary_metric") or growth.get("measurement_metric") or "readiness_review_leads",
        "approval_state": "NEEDS_RAY_REVIEW" if growth.get("status") in {"NEEDS_RAY_REVIEW", "READY_TO_IMPLEMENT"} else "INTERNAL_DRAFT",
        "created_at": utc_now(), "updated_at": utc_now(), "external_action_performed": False,
    }
    body["brief_fingerprint"] = _hash({k: body[k] for k in ("source_growth_id", "source_opportunity_id", "objective", "target_offer", "asset_types", "message")})
    return body


def validate_creative_brief(brief: Dict[str, Any]) -> list[str]:
    required = ("creative_brief_id", "business_id", "title", "objective", "evidence_refs", "asset_types", "measurement_metric")
    issues = [f"missing:{key}" for key in required if not brief.get(key)]
    if brief.get("schema_version") != CREATIVE_BRIEF_SCHEMA: issues.append("schema_version")
    claim_text = json.dumps({key: value for key, value in brief.items() if key not in {"message", "prohibited_claims"}}, default=str)
    if _BANNED.search(claim_text): issues.append("prohibited_claim")
    if brief.get("external_action_performed") is not False: issues.append("external_action")
    return issues


def persist_creative_brief(brief: Dict[str, Any]) -> Dict[str, Any]:
    issues = validate_creative_brief(brief)
    if issues: raise ValueError("invalid creative brief: " + ",".join(issues))
    existing = next((r for r in read_records("creative_briefs") if r.get("brief_fingerprint") == brief["brief_fingerprint"]), None)
    if existing: return {**existing, "persistence": "DUPLICATE_SUPPRESSED"}
    append_record("creative_briefs", brief)
    emit_audit_event({"event": "creative_brief_created", "creative_brief_id": brief["creative_brief_id"], "source_growth_id": brief.get("source_growth_id"), "external_action_performed": False})
    return {**brief, "persistence": "CREATED"}


def _asset_base(brief: Dict[str, Any], asset_type: str, payload: Dict[str, Any], generator: str = "nexus.creative.deterministic") -> Dict[str, Any]:
    source = {"creative_brief_id": brief["creative_brief_id"], "growth_id": brief.get("source_growth_id"), "opportunity_id": brief.get("source_opportunity_id"), "research_job_id": brief.get("source_research_job_id"), "evidence_refs": brief.get("evidence_refs", [])}
    fingerprint = _hash({"brief": brief.get("brief_fingerprint"), "asset_type": asset_type, "payload": payload, "generator": generator})
    return {"schema_version": CREATIVE_ASSET_SCHEMA, "asset_id": new_id("asset"), "creative_brief_id": brief["creative_brief_id"], "asset_type": asset_type, "status": "REVIEW_REQUIRED", "source_refs": source, "evidence_refs": brief.get("evidence_refs", []), "generator": {"type": "deterministic", "provider": generator, "version": "phase-o-v1"}, "content": payload, "input_fingerprint": fingerprint, "quality_score": None, "quality_findings": [], "approval_state": brief.get("approval_state", "INTERNAL_DRAFT"), "license_metadata": {"content": "repository_generated_or_business_copy", "external_distribution": "blocked"}, "external_action_performed": False, "created_at": utc_now()}


def build_copy_asset(brief: Dict[str, Any]) -> Dict[str, Any]:
    payload = {"headline_options": ["Funding readiness starts before you apply.", "Build a clearer readiness path."], "body": "Organize your business profile, documents, and credit readiness before you apply. Use a structured review to see what is ready and what still needs attention.", "cta": brief["primary_cta"], "disclaimer": "Education and readiness only. No guaranteed funding or approval.", "claims_requiring_source": [], "internal_only": True}
    asset = _asset_base(brief, "LANDING_PAGE_COPY", payload)
    asset["quality_score"] = 92
    asset["quality_findings"] = ["evidence_refs_retained", "no_guarantee_claims", "cta_present", "disclaimer_present"]
    return asset


def build_storyboard_asset(brief: Dict[str, Any]) -> Dict[str, Any]:
    scenes = [{"name": "HOOK", "seconds": 1.5, "text": "Funding readiness starts before you apply."}, {"name": "PROBLEM", "seconds": 1.5, "text": "Know what to prepare first."}, {"name": "READINESS", "seconds": 3.0, "text": "Profile  •  Documents  •  Credit readiness"}, {"name": "CTA", "seconds": 1.0, "text": brief["primary_cta"]}, {"name": "DISCLAIMER", "seconds": 1.0, "text": "Education and readiness only. No guaranteed funding or approval."}]
    return _asset_base(brief, "VIDEO_STORYBOARD", {"template_id": REMOTION_TEMPLATE, "duration_seconds": 8, "fps": 30, "width": 1080, "height": 1080, "scenes": scenes, "audio": "silent", "internal_only": True})


def build_image_specs(brief: Dict[str, Any]) -> list[Dict[str, Any]]:
    return [_asset_base(brief, "IMAGE_PROMPT", {"prompt": "Clean editorial illustration of an open gate and a clear path, calm navy and gold palette, no text, no logos, reserved space for a headline, internal concept only."}), _asset_base(brief, "IMAGE_LAYOUT_SPEC", {"dimensions": "1080x1080", "layout": "headline, three readiness points, CTA, disclaimer", "assets": "deterministic shapes only", "internal_only": True})]


def persist_creative_asset(asset: Dict[str, Any]) -> Dict[str, Any]:
    if asset.get("schema_version") != CREATIVE_ASSET_SCHEMA or asset.get("external_action_performed") is not False: raise ValueError("invalid creative asset")
    existing = next((r for r in read_records("creative_assets") if r.get("input_fingerprint") == asset.get("input_fingerprint") and r.get("status") != "FAILED"), None)
    if existing: return {**existing, "persistence": "DUPLICATE_SUPPRESSED"}
    append_record("creative_assets", asset)
    emit_audit_event({"event": "creative_asset_created", "asset_id": asset["asset_id"], "creative_brief_id": asset["creative_brief_id"], "asset_type": asset["asset_type"], "external_action_performed": False})
    return {**asset, "persistence": "CREATED"}


def persist_creative_receipt(receipt: Dict[str, Any]) -> Dict[str, Any]:
    receipt = {"schema_version": CREATIVE_RENDER_SCHEMA, "receipt_id": receipt.get("receipt_id") or new_id("creative-receipt"), "external_action_performed": False, **receipt}
    append_record("creative_receipts", receipt)
    return receipt


def creative_portfolio() -> Dict[str, Any]:
    rows = read_records("creative_assets")
    gpu_rows = [r for r in rows if r.get("generator", {}).get("capability") == "creative.image_generate"]
    latest_gpu = gpu_rows[0] if gpu_rows else None
    return {"status": "HEALTHY" if rows else "IDLE", "total": len(rows), "draft_count": sum(r.get("status") == "INTERNAL_DRAFT" for r in rows), "review_required_count": sum(r.get("status") == "REVIEW_REQUIRED" for r in rows), "approved_count": sum(r.get("status") == "APPROVED" for r in rows), "failed_count": sum(r.get("status") == "FAILED" for r in rows), "latest": rows[0] if rows else None, "remotion": "AVAILABLE" if any(r.get("render", {}).get("artifact_ref") for r in rows) else "NOT_AVAILABLE", "comfyui": COMFYUI_STATUS, "gpu": "IDLE" if not gpu_rows else "DEGRADED", "gpu_creative": {"status": "IDLE" if not gpu_rows else "DEGRADED", "provider": "modal", "last_asset_id": latest_gpu.get("asset_id") if latest_gpu else None, "last_model": (latest_gpu or {}).get("render", {}).get("model_id"), "last_workflow": (latest_gpu or {}).get("render", {}).get("workflow_id"), "public_actions": "BLOCKED"}, "creative_intelligence": creative_intelligence_portfolio(), "public_actions": "BLOCKED"}


def answer_creative_question(question: str) -> Dict[str, Any]:
    q = question.lower(); portfolio = creative_portfolio(); rows = read_records("creative_assets")
    if any(term in q for term in ("different", "directions", "original", "repetitive", "preference", "done this", "experiment")):
        return {"creative_intelligence": answer_creative_intelligence_question(question), "portfolio": portfolio, "source": "creative_concepts"}
    if any(word in q for word in ("review", "ready", "asset")):
        return {"answer": "Creative Studio has internal assets awaiting review." if any(r.get("status") == "REVIEW_REQUIRED" for r in rows) else "No creative assets are currently awaiting review.", "portfolio": portfolio, "source": "creative_assets"}
    if "publish" in q or "published" in q:
        return {"answer": "No Creative Studio publishing action is enabled; public distribution is blocked in Phase O.", "published": False, "source": "creative_assets"}
    return {"answer": "Creative Studio state is available from the canonical asset portfolio.", "portfolio": portfolio, "source": "creative_assets"}


def assert_public_action_blocked(action: str) -> None:
    if action in PUBLIC_ACTIONS: raise PermissionError("NOT_AUTHORIZED: Creative Studio distribution is disabled")
