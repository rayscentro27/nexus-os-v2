#!/usr/bin/env python3
"""Report external-compute readiness without exposing environment values."""
from __future__ import annotations

import importlib.util
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def check() -> dict:
    root = Path(os.environ.get("NEXUS_KAGGLE_WORKDIR", tempfile.gettempdir()))
    usage = shutil.disk_usage(root if root.exists() else Path.home())
    gpu = None
    nvidia = shutil.which("nvidia-smi")
    if nvidia:
        run = subprocess.run([nvidia, "--query-gpu=name", "--format=csv,noheader"], capture_output=True, text=True, timeout=5)
        gpu = run.stdout.strip().splitlines() if run.returncode == 0 else []
    kaggle = bool(os.environ.get("KAGGLE_KERNEL_RUN_TYPE"))
    return {"status": "KAGGLE_READY" if kaggle else "LOCAL_TOOLING_READY_PLATFORM_UNVERIFIED", "kaggle_runtime_detected": kaggle, "python": platform.python_version(), "system": platform.system(), "machine": platform.machine(), "cpu_count": os.cpu_count(), "gpu_count": len(gpu or []), "gpu_names": gpu or [], "workdir_exists": root.exists(), "free_storage_bytes": usage.free, "libraries": {name: importlib.util.find_spec(name) is not None for name in ("numpy", "pandas", "torch")}, "outbound_network_assumed": False}


def main() -> int:
    result = check()
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
