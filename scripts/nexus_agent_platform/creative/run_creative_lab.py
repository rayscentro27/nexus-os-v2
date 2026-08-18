#!/usr/bin/env python3
"""Run the Nexus Creative Lab proof and emit markdown reports."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))

from nexus_agent_platform.creative.lab import write_creative_lab_reports  # noqa: E402


def main() -> int:
    report = write_creative_lab_reports()
    print(json.dumps({
        "ok": True,
        "territory_count": report["territory_count"],
        "recommended_territory": report["recommended_territory"]["concept_name"],
        "ai_calls": report["ai_calls"],
        "build_spec_created": bool(report["build_spec"]),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
