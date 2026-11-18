"""Fail-closed registry and router for Creative execution environments.

Model selection remains in ``creative.model_router``. This module selects only
the execution location and never calls a provider or starts a worker.
"""
from __future__ import annotations

import os
import shutil
from typing import Any, Mapping


def _present(name: str) -> bool:
    return bool(os.environ.get(name))


def registry() -> list[dict[str, Any]]:
    ffmpeg = shutil.which("ffmpeg")
    # Remotion's JS package cannot be checked with Python importlib. The
    # executable and license state are the runtime gates used here.
    node = shutil.which("node")
    remotion_active = bool(node and os.path.exists("node_modules/@remotion/renderer")
                           and os.environ.get("NEXUS_REMOTION_LICENSE_STATUS") == "APPROVED")
    modal_active = _present("MODAL_TOKEN_ID") and _present("MODAL_TOKEN_SECRET")
    runpod_active = _present("RUNPOD_API_KEY")
    # This is the only currently usable production path: deterministic internal
    # copy/storyboard planning, not image/video rendering.
    return [
        {"environment_id": "LOCAL_DETERMINISTIC_MEDIA_WORKER", "name": "Nexus deterministic Creative artifact worker", "type": "LOCAL_WORKER", "location": "Mac Nexus durable job worker", "supported_media_types": ["COPY", "STORYBOARD"], "supported_formats": ["JSON", "TEXT", "MARKDOWN"], "quality_profiles": ["INTERNAL_REVIEW", "STANDARD"], "cost_rank": 0, "latency_rank": 0, "requires_brand": False, "active": True, "authority": "Active dispatcher release includes MARKETING_CREATIVE handler; limited to deterministic non-binary artifacts", "cost_model": "ZERO_PROVIDER_COST", "temp_storage": "Local workflow artifact directory", "canonical_storage": False, "health": "WORKER_ENTRYPOINT_ACTIVE_NON_BINARY_ONLY", "approval_required": False},
        {"environment_id": "REMOTION", "name": "Remotion render worker", "type": "RENDERER", "location": "Nexus worker host", "supported_media_types": ["VIDEO"], "supported_formats": ["MP4"], "quality_profiles": ["STANDARD", "HIGH"], "cost_rank": 1, "latency_rank": 1, "requires_brand": True, "active": remotion_active, "authority": "Existing Creative renderer; license gate", "cost_model": "LOCAL_COMPUTE", "temp_storage": "Worker-local render directory", "canonical_storage": False, "health": "AVAILABLE" if remotion_active else "NOT_VERIFIED_OR_LICENSE_BLOCKED", "approval_required": True},
        {"environment_id": "CI_RUNNER", "name": "CI runner", "type": "BUILD_WORKER", "location": "Configured CI", "supported_media_types": ["IMAGE", "VIDEO", "COPY"], "supported_formats": ["PNG", "MP4", "JSON"], "quality_profiles": ["STANDARD"], "cost_rank": 1, "latency_rank": 2, "requires_brand": False, "active": False, "authority": "No Creative execution registration found", "cost_model": "UNKNOWN", "temp_storage": "Ephemeral runner", "canonical_storage": False, "health": "NOT_CONNECTED", "approval_required": True},
        {"environment_id": "EXTERNAL_IMAGE_PROVIDER", "name": "External image provider", "type": "PROVIDER", "location": "External", "supported_media_types": ["IMAGE"], "supported_formats": ["PNG", "JPG", "WEBP"], "quality_profiles": ["STANDARD", "HIGH"], "cost_rank": 3, "latency_rank": 2, "requires_brand": False, "active": False, "authority": "No approved active Creative route verified", "cost_model": "UNKNOWN", "temp_storage": "Provider output URL", "canonical_storage": False, "health": "NOT_CONFIGURED", "approval_required": True},
        {"environment_id": "EXTERNAL_VIDEO_PROVIDER", "name": "External video provider", "type": "PROVIDER", "location": "External", "supported_media_types": ["VIDEO"], "supported_formats": ["MP4"], "quality_profiles": ["STANDARD", "HIGH"], "cost_rank": 4, "latency_rank": 3, "requires_brand": False, "active": False, "authority": "No approved active Creative route verified", "cost_model": "UNKNOWN", "temp_storage": "Provider output URL", "canonical_storage": False, "health": "NOT_CONFIGURED", "approval_required": True},
        {"environment_id": "RUNPOD", "name": "RunPod", "type": "GPU_WORKER", "location": "RunPod", "supported_media_types": ["IMAGE", "VIDEO"], "active": False, "authority": "No active Creative adapter/health proof", "cost_model": "METERED", "temp_storage": "Ephemeral GPU worker", "canonical_storage": False, "health": "NOT_REGISTERED" if not runpod_active else "CREDENTIAL_PRESENT_ADAPTER_UNVERIFIED", "approval_required": True},
        {"environment_id": "MODAL", "name": "Modal", "type": "GPU_WORKER", "location": "Modal", "supported_media_types": ["IMAGE", "VIDEO", "VOICE"], "active": False, "authority": "Existing Modal capability is not an active Creative route", "cost_model": "METERED", "temp_storage": "Ephemeral GPU worker", "canonical_storage": False, "health": "NOT_REGISTERED" if not modal_active else "CREDENTIAL_PRESENT_ADAPTER_UNVERIFIED", "approval_required": True},
        {"environment_id": "TTS_PROVIDER", "name": "TTS provider", "type": "PROVIDER", "location": "External", "supported_media_types": ["AUDIO"], "active": False, "authority": "No Creative-specific approved active route verified", "cost_model": "UNKNOWN", "temp_storage": "Provider output URL", "canonical_storage": False, "health": "NOT_CONFIGURED", "approval_required": True},
        {"environment_id": "AVATAR_PROVIDER", "name": "Avatar provider", "type": "PROVIDER", "location": "External", "supported_media_types": ["VIDEO"], "active": False, "authority": "No Creative-specific approved active route verified", "cost_model": "UNKNOWN", "temp_storage": "Provider output URL", "canonical_storage": False, "health": "NOT_CONFIGURED", "approval_required": True},
    ]


def storage_registry() -> list[dict[str, Any]]:
    import sys
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[3] / "scripts/ops"))
    from nexus_runtime_env import load_runtime_env, presence_report
    load_runtime_env(allowed_keys={"R2_ACCOUNT_ID", "R2_BUCKET"})
    report = {item["variable"]: bool(item["configured"]) for item in presence_report(
        ["R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_BUCKET"])}
    r2_configured = all(report.values())
    metadata_configured = bool((_present("SUPABASE_URL") or _present("VITE_SUPABASE_URL")) and _present("SUPABASE_SERVICE_ROLE_KEY"))
    return [
        {"system": "CLOUDFLARE_R2", "role": "CANONICAL_MEDIA_BYTES", "configured": r2_configured, "health": "CONFIGURED_NOT_RUNTIME_VERIFIED" if r2_configured else "CANONICAL_STORAGE_UNAVAILABLE", "bucket": os.environ.get("R2_BUCKET") if r2_configured else None, "bucket_exists": "UNKNOWN", "s3_endpoint": f"https://{os.environ.get('R2_ACCOUNT_ID')}.r2.cloudflarestorage.com" if r2_configured else None, "authority": "Nexus canonical runtime environment", "public_access_policy": "UNKNOWN_UNTIL_BUCKET_INSPECTED", "signed_url_support": "IMPLEMENTED_NOT_RUNTIME_VERIFIED"},
        {"system": "SUPABASE", "role": "CANONICAL_METADATA_AND_WORKFLOW_STATE", "configured": metadata_configured, "health": "CONFIGURED" if metadata_configured else "METADATA_STORE_UNAVAILABLE"},
    ]


def route(work_order: Mapping[str, Any], *, environments: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    required = ("work_order_id", "campaign_id", "asset_type", "format", "quality_profile", "model_profile", "budget_class", "approval_state")
    missing = [key for key in required if not work_order.get(key)]
    if missing:
        return {"status": "BLOCKED", "error_code": "WORK_ORDER_CONTEXT_MISSING", "missing": missing, "environment": None}
    kind = str(work_order["asset_type"]).upper()
    media = "STORYBOARD" if "STORYBOARD" in kind else "COPY" if any(x in kind for x in ("COPY", "TEXT", "BRIEF")) else "VIDEO" if "VIDEO" in kind or "REMOTION" in kind else "IMAGE" if "IMAGE" in kind or "SVG" in kind else kind
    approval = str(work_order.get("approval_state") or "").upper()
    approved = approval in {"APPROVED", "APPROVED_FOR_INTERNAL_GENERATION"}
    if approval in {"REJECTED", "DENIED", "REVOKED", "EXPIRED"}:
        return {"status": "BLOCKED", "error_code": "APPROVAL_POLICY_BLOCK", "environment": None, "asset_type": media}
    candidates = [row for row in (environments if environments is not None else registry())
        if row.get("active") and not row.get("canonical_storage")
        and media in row.get("supported_media_types", [])
        and str(work_order.get("format") or "").upper() in row.get("supported_formats", [])
        and str(work_order.get("quality_profile") or "").upper() in row.get("quality_profiles", [])
        and (not row.get("requires_brand") or bool(work_order.get("brand_id")))
        and (not row.get("approval_required") or approved)
        and (str(work_order.get("budget_class") or "").upper() != "ZERO_SPEND_INTERNAL" or int(row.get("cost_rank", 0)) == 0)]
    if not candidates and any(row.get("active") and row.get("approval_required") for row in (environments if environments is not None else registry())) and not approved:
        return {"status": "BLOCKED", "error_code": "APPROVAL_POLICY_BLOCK", "environment": None, "asset_type": media}
    if not candidates:
        return {"status": "UNAVAILABLE", "error_code": "NO_APPROVED_EXECUTION_ENVIRONMENT", "environment": None, "asset_type": media}
    candidates.sort(key=lambda row: (int(row.get("cost_rank", 99)), int(row.get("latency_rank", 99))))
    profile = str(work_order["model_profile"])
    return {"status": "ROUTED", "environment": candidates[0]["environment_id"], "asset_type": media, "model_profile": profile, "model_route": "NOT_REQUIRED" if profile == "DETERMINISTIC_NO_MODEL" else "MODEL_MANAGER_REQUIRED", "cost_rank": candidates[0].get("cost_rank"), "latency_rank": candidates[0].get("latency_rank"), "temporary_storage": candidates[0].get("temp_storage")}


def resolve_model_profile(profile: str) -> dict[str, Any]:
    """Delegate provider/model choice to the existing Model Manager route."""
    try:
        from nexus_agent_platform.creative.model_router import select_task_route
        selected = select_task_route(profile)
    except Exception:
        return {"status": "UNAVAILABLE", "profile": profile, "provider": None, "model": None}
    if not isinstance(selected, dict) or selected.get("status") not in {"AVAILABLE", "PASS"}:
        return {"status": "UNAVAILABLE", "profile": profile, "provider": None, "model": None}
    route = selected.get("selected") or selected.get("primary_spec") or selected
    return {"status": "AVAILABLE", "profile": profile, "provider": route.get("provider"), "model": route.get("model") or route.get("model_id"), "source": "NEXUS_MODEL_MANAGER"}


def plan(work_order: Mapping[str, Any], *, environments: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Select execution environment, then resolve any required model profile."""
    decision = route(work_order, environments=environments)
    if decision.get("status") != "ROUTED" or decision.get("model_route") == "NOT_REQUIRED":
        return decision
    model = resolve_model_profile(str(work_order.get("model_profile") or ""))
    if model.get("status") != "AVAILABLE":
        return {**decision, "status": "UNAVAILABLE", "error_code": "MODEL_PROFILE_UNAVAILABLE", "environment": None, "model_selection": model}
    return {**decision, "model_selection": model}


def route_authorized(work_order: Mapping[str, Any], *, agent_id: str, bot_id: str,
                     runtime_health: Mapping[str, str], environments: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Production-facing route with canonical identity and live-health gates.

    The older ``route`` helper remains a pure policy preview for existing
    callers/tests. Executors must use this function before dispatch.
    """
    from nexus_agent_platform.agent_control_plane import AuthorizationDenied, authorize
    profile = str(work_order.get("model_profile") or "")
    if profile == "DETERMINISTIC_NO_MODEL":
        profile = "NO_MODEL"
    try:
        authorize(agent_id=agent_id, bot_id=bot_id, model_profile=profile)
    except AuthorizationDenied as exc:
        return {"status": "BLOCKED", "error_code": str(exc), "environment": None}
    preview = plan(work_order, environments=environments)
    if preview.get("status") not in {"ROUTED", "AVAILABLE"}:
        return preview
    selected = preview.get("environment")
    if not selected:
        return {**preview, "status": "UNAVAILABLE", "error_code": "NO_EXECUTION_ENVIRONMENT"}
    try:
        authorize(agent_id=agent_id, bot_id=bot_id, environment_id=selected,
                  runtime_health=dict(runtime_health))
    except AuthorizationDenied as exc:
        return {**preview, "status": "UNAVAILABLE", "error_code": str(exc), "environment": None}
    return preview
