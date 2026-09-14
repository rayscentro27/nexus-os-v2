"""Phase 1 Creative design-engine contracts.

This module owns routing and lifecycle data only. It does not generate visual
design. Specialist workers create artifacts; Ray approves them; Codex only
implements an approved, frozen contract.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from hashlib import sha256
from typing import Any, Mapping

SURFACES = {
    "PRODUCT_UI", "ADMIN_DASHBOARD", "CLIENT_PORTAL", "LANDING_PAGE",
    "MARKETING_SITE", "CAMPAIGN_PAGE", "SEO_MICROSITE", "VISUAL_ASSET", "DESIGN_QA",
    "EXISTING_REACT_VISUAL_EDIT",
}
STATES = {
    "REQUESTED", "BRIEF_CREATED", "WORKER_SELECTED", "DESIGNING", "DESIGN_READY",
    "QA_REVIEW", "REVISION_REQUIRED", "READY_FOR_RAY", "APPROVED", "FROZEN",
    "READY_FOR_IMPLEMENTATION", "IMPLEMENTING", "VISUAL_QA",
    "READY_FOR_FINAL_ACCEPTANCE", "COMPLETE", "HUMAN_GATED", "EXTERNAL_GATED",
    "FAILED_RETRYABLE", "FAILED_TERMINAL",
}
TRANSITIONS = {
    "REQUESTED": {"BRIEF_CREATED", "HUMAN_GATED", "FAILED_RETRYABLE"},
    "BRIEF_CREATED": {"WORKER_SELECTED", "HUMAN_GATED", "FAILED_RETRYABLE"},
    "WORKER_SELECTED": {"DESIGNING", "FAILED_RETRYABLE"},
    "DESIGNING": {"DESIGN_READY", "FAILED_RETRYABLE"},
    "DESIGN_READY": {"QA_REVIEW", "REVISION_REQUIRED", "READY_FOR_RAY"},
    "QA_REVIEW": {"REVISION_REQUIRED", "READY_FOR_RAY", "FAILED_RETRYABLE"},
    "REVISION_REQUIRED": {"DESIGNING", "HUMAN_GATED"},
    "READY_FOR_RAY": {"APPROVED", "REVISION_REQUIRED", "HUMAN_GATED"},
    "APPROVED": {"FROZEN"},
    "FROZEN": {"READY_FOR_IMPLEMENTATION"},
    "READY_FOR_IMPLEMENTATION": {"IMPLEMENTING"},
    "IMPLEMENTING": {"VISUAL_QA", "FAILED_RETRYABLE"},
    "VISUAL_QA": {"READY_FOR_FINAL_ACCEPTANCE", "IMPLEMENTING", "FAILED_RETRYABLE"},
    "READY_FOR_FINAL_ACCEPTANCE": {"COMPLETE", "HUMAN_GATED"},
    "FAILED_RETRYABLE": {"REQUESTED", "DESIGNING", "HUMAN_GATED"},
}

WORKER_BY_SURFACE = {
    "PRODUCT_UI": "penpot", "ADMIN_DASHBOARD": "penpot", "CLIENT_PORTAL": "penpot",
    "LANDING_PAGE": "openpage", "CAMPAIGN_PAGE": "openpage", "SEO_MICROSITE": "openpage",
    "MARKETING_SITE": "webstudio", "VISUAL_ASSET": "existing_creative_asset_worker",
    "DESIGN_QA": "impeccable", "EXISTING_REACT_VISUAL_EDIT": "onlook",
    "CUSTOM_PAGE_BUILDER": "grapesjs",
}

NEXUS_TOKENS = {
    "BRAND_NAVY": "#182B45", "BRAND_CYAN": "#326BCE", "BRAND_TEAL": "#2D8057",
    "SURFACE_DARK": "#101318", "SURFACE_LIGHT": "#F7F8FA", "TEXT_PRIMARY": "#101318",
    "TEXT_SECONDARY": "#697483", "STATUS_SUCCESS": "#2D8057", "STATUS_WARNING": "#B97820",
    "STATUS_ERROR": "#B44949", "TYPE_DISPLAY": "32/38 650", "TYPE_HEADING": "24/30 650",
    "TYPE_BODY": "14/21 450", "TYPE_META": "12/17 500", "SPACE_1": "4px",
    "SPACE_2": "8px", "SPACE_3": "12px", "SPACE_4": "16px", "SPACE_5": "20px",
    "SPACE_6": "24px", "RADIUS_SM": "8px", "RADIUS_MD": "10px", "RADIUS_PANEL": "18px",
    "SHADOW_PANEL": "overlay-only",
}


def classify_surface(request: str, *, explicit: str | None = None) -> dict[str, Any]:
    if explicit and explicit in SURFACES:
        surface = explicit
    else:
        text = request.lower()
        if "existing react" in text or "react visual" in text:
            surface = "EXISTING_REACT_VISUAL_EDIT"
        elif "admin" in text or "dashboard" in text:
            surface = "ADMIN_DASHBOARD"
        elif "client portal" in text:
            surface = "CLIENT_PORTAL"
        elif "landing" in text or "campaign page" in text or "affiliate page" in text:
            surface = "LANDING_PAGE" if "campaign" not in text else "CAMPAIGN_PAGE"
        elif "seo" in text or "microsite" in text:
            surface = "SEO_MICROSITE"
        elif "marketing site" in text or "website" in text:
            surface = "MARKETING_SITE"
        elif "qa" in text or "critique" in text:
            surface = "DESIGN_QA"
        elif "hero" in text or "graphic" in text or "icon" in text:
            surface = "VISUAL_ASSET"
        else:
            surface = "PRODUCT_UI"
    return {
        "surface_type": surface,
        "recommended_worker": WORKER_BY_SURFACE[surface],
        "required_approval": "RAY" if surface != "DESIGN_QA" else "CREATIVE",
        "implementation_path": "Codex only after APPROVED → FROZEN",
    }


def create_design_project(title: str, business_objective: str, request: str, *, requested_by: str = "department", **refs: Any) -> dict[str, Any]:
    routing = classify_surface(request, explicit=refs.pop("surface_type", None))
    project_id = "design-" + sha256(f"{title}|{business_objective}|{routing['surface_type']}".encode()).hexdigest()[:16]
    return {
        "design_project_id": project_id, "title": title, "business_objective": business_objective,
        "surface_type": routing["surface_type"], "audience": refs.pop("audience", "TBD by Creative"),
        "brand": "Nexus/GoClear", "requested_by": requested_by, **refs,
        "visual_direction": {}, "information_architecture": [], "layout_sections": [],
        "component_requirements": [], "data_requirements": [], "color_tokens": NEXUS_TOKENS,
        "typography_tokens": {}, "spacing_tokens": {}, "radius_tokens": {}, "icon_rules": {},
        "asset_requirements": [], "asset_references": [], "responsive_rules": [],
        "interaction_rules": [], "accessibility_requirements": [],
        "design_worker": routing["recommended_worker"], "design_artifact_type": "editable_specialist_artifact",
        "design_artifact_location": refs.pop("design_artifact_location", None),
        "design_qa_status": "NOT_STARTED", "ray_approval_status": "PENDING", "design_frozen": False,
        "implementation_agent": "Codex", "implementation_status": "NOT_STARTED",
        "visual_comparison_status": "NOT_STARTED", "final_acceptance_status": "PENDING",
        "state": "REQUESTED", "routing": routing,
    }


def transition(project: Mapping[str, Any], target: str) -> dict[str, Any]:
    current = project["state"]
    if target not in STATES or target not in TRANSITIONS.get(current, set()):
        raise ValueError(f"invalid_design_project_transition:{current}->{target}")
    updated = dict(project)
    updated["state"] = target
    if target == "APPROVED": updated["ray_approval_status"] = "APPROVED"
    if target == "FROZEN": updated["design_frozen"] = True
    return updated


def implementation_contract(project: Mapping[str, Any]) -> dict[str, Any]:
    if project.get("state") != "FROZEN" or not project.get("design_frozen"):
        raise ValueError("implementation_requires_frozen_approved_design")
    return {key: project.get(key) for key in (
        "design_project_id", "design_artifact_location", "color_tokens", "typography_tokens",
        "spacing_tokens", "radius_tokens", "component_requirements", "layout_sections",
        "responsive_rules", "asset_references", "interaction_rules", "data_requirements",
        "accessibility_requirements", "icon_rules") } | {
        "instruction": "IMPLEMENT THIS DESIGN.", "do_not_change_rules": [
            "Do not invent layout, branding, graphics, hierarchy, or replacement assets.",
            "Make only bounded functional, accessibility, and responsive corrections.",
        ]}


def route_department_request(work_order: Mapping[str, Any]) -> dict[str, Any]:
    request = str(work_order.get("objective") or work_order.get("title") or "")
    return create_design_project(request or "Untitled Creative request", request, request,
                                requested_by=str(work_order.get("department", "department")),
                                source_work_order_id=work_order.get("work_order_id"))


def route_asset(project: Mapping[str, Any], asset_type: str, *, source: str = "existing_brand_library", file_reference: str | None = None) -> dict[str, Any]:
    """Bind an asset source to a project without generating or approving art."""
    asset_id = "asset-" + sha256(f"{project.get('design_project_id')}|{asset_type}|{source}|{file_reference or ''}".encode()).hexdigest()[:16]
    return {
        "asset_id": asset_id, "design_project_id": project.get("design_project_id"), "asset_type": asset_type,
        "source": source, "version": "1", "approval_status": "PENDING", "file_reference": file_reference,
    }


def adapter_contract(worker: str) -> dict[str, Any]:
    operations = {
        "penpot": ["create_design_project", "create_page", "create_frame", "create_component", "apply_tokens", "insert_asset", "create_responsive_variant", "export_design_metadata", "fetch_design_artifact"],
        "openpage": ["create_site_config", "add_page", "add_section", "apply_theme", "insert_asset", "bind_content", "create_responsive_rules", "export_preview", "export_site_config"],
        "onlook": ["connect_repo", "open_route", "inspect_components", "apply_visual_change", "capture_preview", "persist_change_reference"],
        "impeccable": ["critique", "record_findings", "request_revision"],
        "grapesjs": ["create_editor_project", "add_block", "apply_style", "export_html"],
        "webstudio": ["create_site", "create_page", "apply_theme", "export_project"],
    }
    return {"worker": worker, "operations": operations.get(worker, []), "status": "INTERFACE_ONLY_NOT_CONNECTED"}
