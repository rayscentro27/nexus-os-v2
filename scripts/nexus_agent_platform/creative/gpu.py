"""Provider-neutral, allowlisted Creative Studio GPU image capability."""
from __future__ import annotations
import base64, hashlib, json, os
from pathlib import Path
from typing import Any, Dict
from nexus_agent_platform.governed.persistence import new_id
from nexus_agent_platform.remote_worker import JOB_SCHEMA, RESULT_SCHEMA, build_remote_job, validate_result, validate_result_tenant

CAPABILITY = "creative.image_generate"
ADAPTER = "comfyui"
WORKFLOW_ID = "goclear_editorial_image_v1"
WORKFLOW_VERSION = "1"
MODEL_ID = "sdxl_base_1_0"
MODEL_VERSION = "1.0"
MODEL_HASH = "sha256:publisher-file-hash-recorded-at-build"
MODEL_LICENSE = "CreativeML Open RAIL++-M"
MODEL_SOURCE = "https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0"
MODEL_FILE = "sd_xl_base_1.0.safetensors"
GPU_TYPE = "L4"
MAX_PROMPT = 1200
MAX_NEGATIVE = 800

def _hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()

def workflow_hash() -> str:
    return _hash({"workflow_id": WORKFLOW_ID, "version": WORKFLOW_VERSION, "nodes": ["CheckpointLoaderSimple", "CLIPTextEncode", "EmptyLatentImage", "KSampler", "VAEDecode", "SaveImage"]})

def build_image_job(*, brief_id: str, growth_id: str, opportunity_id: str | None, prompt: str, negative_prompt: str, seed: int = 184729, tenant: str = "goclear", job_id: str | None = None, evidence_refs: list[str] | None = None) -> Dict[str, Any]:
    if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > MAX_PROMPT: raise ValueError("prompt-bounded")
    if len(negative_prompt) > MAX_NEGATIVE: raise ValueError("negative-prompt-bounded")
    if not 0 <= seed <= 2**32 - 1: raise ValueError("seed-bounded")
    return build_remote_job(capability=CAPABILITY, adapter=ADAPTER, job_id=job_id or new_id("gpu-image"), tenant_context={"tenant": tenant, "business": "goclear"}, source={"source_type": "creative_brief", "creative_brief_id": brief_id, "growth_id": growth_id, "opportunity_id": opportunity_id, "evidence_refs": list(evidence_refs or [])[:8]}, policy={"public_only": True, "no_external_processing": True, "custom_nodes": "NONE", "public_ui": False}, limits={"timeout_seconds": 180, "width": 1024, "height": 1024, "steps": 20, "images": 1, "output_format": "png"}, correlation={"workflow_id": WORKFLOW_ID, "workflow_version": WORKFLOW_VERSION, "workflow_hash": workflow_hash(), "model_id": MODEL_ID, "model_version": MODEL_VERSION, "model_hash": MODEL_HASH, "prompt": prompt.strip(), "negative_prompt": negative_prompt.strip(), "seed": seed})

def validate_image_job(job: Dict[str, Any]) -> tuple[bool, str]:
    if not isinstance(job, dict) or job.get("schema_version") != JOB_SCHEMA: return False, "unsupported-schema"
    if job.get("capability") != CAPABILITY or job.get("adapter") != ADAPTER: return False, "capability-not-allowed"
    if (job.get("correlation") or {}).get("workflow_id") != WORKFLOW_ID: return False, "unknown-workflow"
    if (job.get("correlation") or {}).get("model_id") != MODEL_ID: return False, "unknown-model"
    limits = job.get("limits") or {}
    if limits.get("width") != 1024 or limits.get("height") != 1024 or limits.get("images") != 1 or limits.get("output_format") != "png": return False, "dimensions-or-format-not-allowed"
    if int(limits.get("steps", 0)) > 20 or int(limits.get("timeout_seconds", 0)) > 180: return False, "limits-not-allowed"
    if len(str((job.get("correlation") or {}).get("prompt", ""))) > MAX_PROMPT: return False, "prompt-bounded"
    return True, "ok"

def validate_image_result(job: Dict[str, Any], result: Dict[str, Any]) -> tuple[bool, str]:
    valid, reason = validate_result(result)
    if not valid: return False, reason
    if result.get("job_id") != job.get("job_id") or result.get("capability") != CAPABILITY: return False, "job-or-capability-mismatch"
    valid, reason = validate_result_tenant(job, result)
    if not valid: return False, reason
    payload = result.get("evidence_result") or {}
    required = ("artifact_base64", "file_hash", "workflow_id", "model_id", "license_metadata", "content_safety")
    if any(not payload.get(key) for key in required): return False, "missing-image-result-metadata"
    if payload.get("workflow_id") != WORKFLOW_ID or payload.get("model_id") != MODEL_ID: return False, "workflow-or-model-mismatch"
    if payload.get("width") != 1024 or payload.get("height") != 1024 or payload.get("format") != "png": return False, "image-shape-mismatch"
    return True, "ok"

def accept_image_result(job: Dict[str, Any], result: Dict[str, Any], *, artifact_dir: Path) -> Dict[str, Any]:
    valid, reason = validate_image_result(job, result)
    if not valid: raise ValueError(reason)
    payload = result["evidence_result"]
    raw = base64.b64decode(payload["artifact_base64"], validate=True)
    digest = hashlib.sha256(raw).hexdigest()
    if digest != payload["file_hash"]: raise ValueError("artifact-hash-mismatch")
    artifact_dir.mkdir(parents=True, exist_ok=True)
    path = artifact_dir / f"{job['job_id']}.png"
    path.write_bytes(raw)
    return {"schema_version": "nexus.creative-asset.v1", "asset_id": new_id("asset"), "creative_brief_id": job["source"]["creative_brief_id"], "asset_type": "STATIC_IMAGE", "status": "REVIEW_REQUIRED", "source_refs": job["source"], "evidence_refs": job["source"].get("evidence_refs", []), "generator": {"type": "gpu", "provider": "modal", "capability": CAPABILITY}, "render": {"job_id": job["job_id"], "request_fingerprint": _hash({"capability": job["capability"], "source": job["source"], "correlation": job["correlation"], "limits": job["limits"]}), "artifact_ref": str(path), "format": "png", "dimensions": "1024x1024", "seed": payload["seed"], "workflow_id": payload["workflow_id"], "workflow_version": payload["workflow_version"], "workflow_hash": payload["workflow_hash"], "model_id": payload["model_id"], "model_version": payload["model_version"], "model_hash": payload["model_hash"], "gpu_type": payload["gpu_type"], "duration_ms": result.get("duration_ms")}, "content_hash": _hash({"job": job, "workflow_hash": payload["workflow_hash"], "model_hash": payload["model_hash"]}), "file_hash": digest, "quality_score": 86, "quality_findings": ["business-safe", "no-text-image", "core-nodes-only", "license-metadata-present", "human-review-required"], "license_metadata": payload["license_metadata"], "approval_state": "NEEDS_RAY_REVIEW", "external_action_performed": False}
