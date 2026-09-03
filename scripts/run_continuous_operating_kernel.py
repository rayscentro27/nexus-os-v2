#!/usr/bin/env python3
"""Bounded unattended kernel exercise using the existing real Alpha reader."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from alpha.run_alpha_discovery_cycle import run as alpha_run  # noqa: E402
from nexus_agent_platform.continuous_operating_kernel import (build_program_registry, build_source_registry,
    run_cycle)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cycles", type=int, default=2)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    if not 1 <= args.cycles <= 3:
        print(json.dumps({"ok": False, "error": "cycles must be 1..3"})); return 2
    sources = build_source_registry()
    programs = build_program_registry(source_registry=sources)
    receipts = []
    for index in range(args.cycles):
        def real_research() -> dict:
            result = alpha_run(
                "AI_NEXUS",
                "Find current public evidence about safe bounded agent operations and identify the next internal improvement test.",
                None,
                ["https://modelcontextprotocol.io/specification/2025-06-18"], [], [], [], [], "LAST_30_DAYS",
            )
            return {"status": "PASS" if result.get("ok") else "DEGRADED", "research_id": result.get("research", {}).get("research_id"),
                    "content_count": result.get("content_count", 0), "no_external_action": True}
        receipts.append(run_cycle(real_research, cycle_id=f"kernel_cycle_{index + 1}", queue_empty=True, incomplete_objectives=1))
    output = {"ok": all(r["result"].get("status") == "PASS" for r in receipts), "cycles": len(receipts),
              "programs": len(programs), "sources": len(sources), "receipts": receipts,
              "no_external_action": True}
    print(json.dumps(output, indent=2) if args.json else f"Continuous kernel {'PASS' if output['ok'] else 'DEGRADED'}: {len(receipts)} cycles")
    return 0 if output["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
