#!/usr/bin/env python3
"""Run the verified builder proof and emit reports."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))

from nexus_agent_platform.builders.runtime import write_builder_reports  # noqa: E402


def main() -> int:
    report = write_builder_reports()
    print(json.dumps({
        "ok": report["ok"],
        "selected_worker": report["selected_worker"]["worker_id"],
        "status": report["result"]["status"],
        "ledger_path": report["ledger_path"],
        "zero_token_execution": report["zero_token_execution"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
