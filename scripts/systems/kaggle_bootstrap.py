#!/usr/bin/env python3
"""Prepare a bounded, disposable Kaggle workload directory."""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

try:
    from secret_guard import redact
except ImportError:
    from scripts.systems.secret_guard import redact

PACKAGE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*(?:==[A-Za-z0-9_.+-]+)?$")
SAFE_ENV = ("PATH", "HOME", "TMPDIR", "LANG", "LC_ALL", "CUDA_VISIBLE_DEVICES")


def bootstrap(workdir: Path, packages: list[str] | None = None) -> dict:
    workdir = workdir.expanduser().resolve()
    workdir.mkdir(parents=True, exist_ok=True)
    (workdir / "inputs").mkdir(exist_ok=True)
    (workdir / "outputs").mkdir(exist_ok=True)
    installed = []
    for package in packages or []:
        if not PACKAGE_RE.fullmatch(package) or package.startswith("-"):
            raise ValueError("PACKAGE_SPEC_NOT_ALLOWED")
        env = {key: os.environ[key] for key in SAFE_ENV if key in os.environ}
        run = subprocess.run([sys.executable, "-m", "pip", "install", "--disable-pip-version-check", package], capture_output=True, text=True, timeout=600, check=False, env=env)
        if run.returncode:
            raise RuntimeError("PACKAGE_INSTALL_FAILED:" + redact(run.stderr[-1200:]))
        installed.append(package)
    return redact({"status": "READY", "workdir": str(workdir), "python": sys.version.split()[0], "kaggle_runtime_detected": bool(os.environ.get("KAGGLE_KERNEL_RUN_TYPE")), "package_install_count": len(installed), "safe_environment_names": [k for k in SAFE_ENV if k in os.environ]})


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--workdir", type=Path, default=Path(os.environ.get("NEXUS_KAGGLE_WORKDIR", "./nexus-kaggle-job")))
    p.add_argument("--package", action="append", default=[])
    a = p.parse_args()
    try:
        print(json.dumps(bootstrap(a.workdir, a.package), sort_keys=True))
        return 0
    except (OSError, ValueError, RuntimeError) as exc:
        print(json.dumps({"status": "FAILED", "error": redact(str(exc))}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
