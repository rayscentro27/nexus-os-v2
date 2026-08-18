#!/usr/bin/env python3
"""Generate the canonical Phase 11 Daily Brief reports."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))

from nexus_agent_platform.brief.daily_brief import write_daily_brief_reports  # noqa: E402


if __name__ == "__main__":
    print(json.dumps(write_daily_brief_reports(), indent=2, sort_keys=True))
