#!/usr/bin/env python3
"""Run the deterministic Alpha open-source scout proof."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from nexus_agent_platform.research.open_source_scout import write_open_source_scout_reports  # noqa: E402


def main() -> int:
    report = write_open_source_scout_reports()
    print(json.dumps({
        "ok": True,
        "selected_candidate": report["selected_candidate"]["project"],
        "ai_executions": report["metrics"]["ai_executions"],
        "unique_candidates": report["deduped_sources"],
        "canonical_opportunity_id": report["opportunity_input"]["id"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
