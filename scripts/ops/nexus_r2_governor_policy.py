#!/usr/bin/env python3
"""Provision and verify only the exact Nexus R2 governor scopes."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from nexus_agent_platform.creative.r2_governance import ensure_r2_governor_policies
from nexus_agent_platform.resource_spend_governor import default_store


def main() -> int:
    result = ensure_r2_governor_policies(default_store())
    print(json.dumps(result, sort_keys=True))
    return 0 if result["all_verified"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
