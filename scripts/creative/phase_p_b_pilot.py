"""Bounded Phase P-B GPU image certification runner.

This runner has exactly one live inference path.  Exact repeats are suppressed
from the canonical Creative Studio asset store before the Modal provider is
called.  It never prints credentials, prompts, or binary payloads.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from nexus_agent_platform.creative.gpu import (  # noqa: E402
    accept_image_result,
    build_image_job,
    validate_image_job,
)
from nexus_agent_platform.creative.studio import (  # noqa: E402
    persist_creative_asset,
    persist_creative_receipt,
)
from nexus_agent_platform.governed.persistence import read_records  # noqa: E402
from nexus_agent_platform.providers.modal_provider import ModalRemoteWorkerProvider  # noqa: E402


BRIEF_ID = "brief_07f075d4a5f5428bb61232456620010b"
GROWTH_ID = "growth_c774e2e42583448b844c4a97a80f5dcf"
OPPORTUNITY_ID = "opp_5700d95807d82a3bab55c23d"
EVIDENCE_REFS = ["ev-8874c37fddb5461287d2"]
PROMPT = (
    "Clean editorial illustration of a clear professional pathway through an "
    "open gateway representing business funding readiness, modern navy and "
    "gold business aesthetic, no text, no logo, no identifiable person, no "
    "financial documents, calm trustworthy composition."
)
NEGATIVE = (
    "text, letters, logo, watermark, person, face, document, bank statement, "
    "credit report, nudity, violence, gore, hate, political imagery, blur, distortion"
)
SEED = 184729
ARTIFACT_DIR = ROOT / "data" / "runtime" / "creative_studio" / "generated" / "phase-p-b"


def request_fingerprint(job: dict) -> str:
    import hashlib

    body = {k: job[k] for k in ("capability", "source", "policy", "limits", "correlation")}
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def main() -> int:
    job = build_image_job(
        brief_id=BRIEF_ID,
        growth_id=GROWTH_ID,
        opportunity_id=OPPORTUNITY_ID,
        evidence_refs=EVIDENCE_REFS,
        prompt=PROMPT,
        negative_prompt=NEGATIVE,
        seed=SEED,
    )
    valid, reason = validate_image_job(job)
    if not valid:
        raise RuntimeError(reason)
    fingerprint = request_fingerprint(job)
    existing = next(
        (row for row in read_records("creative_assets")
         if row.get("render", {}).get("request_fingerprint") == fingerprint
         or row.get("input_fingerprint") == fingerprint),
        None,
    )
    if existing:
        print(json.dumps({"status": "DUPLICATE_SUPPRESSED", "asset_id": existing.get("asset_id"), "gpu_inference": False}))
        return 0

    provider = ModalRemoteWorkerProvider(
        profile="goclearonline",
        app_name="nexus-creative-gpu-worker",
        function_name="generate",
        timeout=240,
    )
    result = provider.submit(job)
    if result.get("status") != "SUCCESS":
        print(json.dumps({"status": result.get("status"), "gpu_inference": True, "error": (result.get("error") or {}).get("classification", "unknown")}))
        return 2

    asset = accept_image_result(job, result, artifact_dir=ARTIFACT_DIR)
    persisted = persist_creative_asset(asset)
    receipt = persist_creative_receipt({
        "creative_job_id": job["job_id"],
        "brief_id": BRIEF_ID,
        "asset_id": persisted["asset_id"],
        "asset_type": "STATIC_IMAGE",
        "generator": "modal.comfyui",
        "workflow_id": asset["render"]["workflow_id"],
        "model_id": asset["render"]["model_id"],
        "status": "SUCCESS",
        "artifact_ref": asset["render"]["artifact_ref"],
        "file_hash": asset["file_hash"],
        "quality_score": asset["quality_score"],
        "approval_state": "NEEDS_RAY_REVIEW",
        "usage": result.get("usage", {}),
        "external_action_performed": False,
    })
    changed = dict(job)
    changed["job_id"] = "fixture-material-change"
    changed["correlation"] = dict(job["correlation"], seed=SEED + 1)
    print(json.dumps({
        "status": "SUCCESS",
        "gpu_inference": True,
        "asset_id": persisted["asset_id"],
        "receipt_id": receipt["receipt_id"],
        "artifact_ref": asset["render"]["artifact_ref"],
        "file_hash": asset["file_hash"],
        "model_hash": asset["render"]["model_hash"],
        "workflow_hash": asset["render"]["workflow_hash"],
        "duration_ms": result.get("duration_ms"),
        "material_change_fingerprint_diff": request_fingerprint(changed) != fingerprint,
        "approval_state": "NEEDS_RAY_REVIEW",
        "external_action_performed": False,
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
