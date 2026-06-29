#!/usr/bin/env python3
"""Compatibility entrypoint for one safe internal Nexus daily cycle."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent


def main() -> int:
    return subprocess.call([
        sys.executable, str(ROOT / "scripts" / "activation" / "run_nexus_full_activation.py"),
        "--run-all", "--json",
    ], cwd=ROOT)


if __name__ == "__main__":
    raise SystemExit(main())
