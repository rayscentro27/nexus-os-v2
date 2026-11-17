"""Single-invocation Modal GPU availability probe for the Nova canary.

This reuses the existing Nexus Creative Modal app name and creates no
persistent endpoint, scheduler, queue, or worker control plane.
"""
from __future__ import annotations

import os
import subprocess
import time
from datetime import datetime, timezone

import modal

app = modal.App("nexus-creative-gpu-worker")
image = modal.Image.debian_slim(python_version="3.11")


@app.function(
    image=image,
    gpu="T4",
    timeout=60,
    scaledown_window=2,
    max_containers=1,
    name="nova_gpu_probe",
)
def probe() -> dict:
    started_at = datetime.now(timezone.utc).isoformat()
    started = time.monotonic()
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        )
        gpu_name = result.stdout.strip().splitlines()[0]
    except Exception as exc:
        gpu_name = "GPU_ALLOCATED_BUT_TELEMETRY_UNAVAILABLE:" + type(exc).__name__
    return {
        "provider": "Modal",
        "app": "nexus-creative-gpu-worker",
        "function": "nova_gpu_probe",
        "gpu_name": gpu_name,
        "cuda_visible_devices_present": bool(os.environ.get("CUDA_VISIBLE_DEVICES")),
        "started_at": started_at,
        "runtime_seconds": round(time.monotonic() - started, 3),
        "result": "GPU_FUNCTION_EXECUTED",
    }


if __name__ == "__main__":
    with modal.enable_output():
        with app.run():
            print(probe.remote())
