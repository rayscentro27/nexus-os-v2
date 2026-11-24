#!/usr/bin/env python3
"""Run and persist one private LivePortrait idle canary through Modal L4."""
from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.environ["MODAL_PROFILE"] = "goclearonline"

import modal
from deploy.modal.nova_portrait_renderer_canary import app, idle_canary, REFERENCE_SHA256


from scripts.nexus_agent_platform.provider_enforcement import governed_modal_canary

@governed_modal_canary
def main() -> dict:
    reference_path = ROOT / "assets/nova/avatar/nova_reference.png"
    output_path = ROOT / "artifacts/nova/portrait-renderer/nova_portrait_idle_canary.mp4"
    receipt_path = ROOT / "artifacts/nova/portrait-renderer/nova_portrait_idle_canary.json"
    if output_path.exists() or receipt_path.exists():
        raise FileExistsError("refusing_to_overwrite_existing_portrait_canary")
    reference_bytes = reference_path.read_bytes()
    reference_hash = hashlib.sha256(reference_bytes).hexdigest()
    if reference_hash != REFERENCE_SHA256:
        raise RuntimeError("approved_reference_hash_mismatch")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with modal.enable_output(), app.run():
        remote = idle_canary.remote(reference_bytes, reference_hash)
    video = remote.pop("video_bytes")
    output_path.write_bytes(video)
    remote.update({
        "created_at": datetime.now(timezone.utc).isoformat(),
        "artifact": str(output_path.relative_to(ROOT)),
        "artifact_size_bytes": len(video),
        "local_sha256": hashlib.sha256(video).hexdigest(),
        "license_mode": "PRIVATE_TEST_ONLY",
        "production_provider": False,
    })
    receipt_path.write_text(json.dumps(remote, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in remote.items() if k != "driver_asset"}, indent=2))
    return remote


if __name__ == "__main__":
    main()
