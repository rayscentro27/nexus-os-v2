#!/usr/bin/env python3
"""Bounded unattended kernel exercise using the existing real Alpha reader."""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from alpha.run_alpha_discovery_cycle import run as alpha_run  # noqa: E402
from alpha.alpha_discovery import retrieve_page  # noqa: E402
from nexus_agent_platform.governed import persistence  # noqa: E402
from nexus_agent_platform.continuous_operating_kernel import (build_program_registry, build_source_registry,
    run_cycle)
from nexus_agent_platform.knowledge_freshness import refresh_due, refresh_once  # noqa: E402
from nexus_agent_platform.research_alpha_pipeline import evaluate_pending  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cycles", type=int, default=2)
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--interval-seconds", type=int, default=1200)
    parser.add_argument("--max-cycles", type=int, default=0)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    if not args.daemon and not 1 <= args.cycles <= 3:
        print(json.dumps({"ok": False, "error": "cycles must be 1..3"})); return 2
    if args.interval_seconds < 30:
        print(json.dumps({"ok": False, "error": "interval-seconds must be >= 30"})); return 2
    sources = build_source_registry()
    programs = build_program_registry(source_registry=sources)
    receipts = []
    limit = args.max_cycles if args.daemon and args.max_cycles > 0 else (args.cycles if not args.daemon else None)
    index = 0
    while limit is None or index < limit:
        stale_records = [r for r in persistence.read_records("alpha_content") if refresh_due(r)]
        def real_research() -> dict:
            # Active Operator is the canonical goal-to-work dispatcher.  The
            # continuous supervisor must invoke it; a heartbeat-only cycle is
            # not company execution.  It uses the existing bounded, read-only
            # Research adapter and governed receipts.
            from operations.nexus_active_operator_runner import run_once as operator_run_once
            os.environ["NEXUS_OPERATOR_CYCLE_ID"] = f"kernel_cycle_{index + 1}_{int(time.time())}"
            operator = operator_run_once(dry_run=False, mode="live")
            executed = operator.get("safe_action_results", [])
            if executed:
                result = dict(executed[0].get("result", {}))
                result["operator_run_id"] = operator.get("operator_run_id")
                result["execution_mode"] = "REAL"
                result["task_processing"] = "COMPLETED"
                result["last_real_output"] = operator.get("completed_at")
                return result
            refresh = None
            if stale_records:
                refresh = refresh_once(stale_records[0], retrieve_page)
            result = alpha_run(
                "AI_NEXUS",
                "Find current public evidence about safe bounded agent operations and identify the next internal improvement test.",
                None,
                ["https://modelcontextprotocol.io/specification/2025-06-18"], [], [], [], [], "LAST_30_DAYS",
            )
            alpha_result = evaluate_pending(max_items=20)
            return {"status": "PASS" if result.get("ok") else "DEGRADED", "research_id": result.get("research", {}).get("research_id"),
                    "content_count": result.get("content_count", 0), "alpha_evaluations_created": alpha_result.get("evaluated_count", 0), "stale_refresh": refresh, "no_external_action": True}
        receipts.append(run_cycle(real_research, cycle_id=f"kernel_cycle_{index + 1}", queue_empty=True,
                                  incomplete_objectives=1, stale_claims=len(stale_records), interval_seconds=args.interval_seconds,
                                  scheduler="ACTIVE_DAEMON" if args.daemon else "ACTIVE_IN_PROCESS_CYCLE"))
        index += 1
        if args.daemon and (limit is None or index < limit):
            time.sleep(args.interval_seconds)
        elif not args.daemon:
            break
    output = {"ok": bool(receipts) and all(r["result"].get("status") == "PASS" for r in receipts), "cycles": len(receipts),
              "programs": len(programs), "sources": len(sources), "receipts": receipts,
              "no_external_action": True}
    print(json.dumps(output, indent=2) if args.json else f"Continuous kernel {'PASS' if output['ok'] else 'DEGRADED'}: {len(receipts)} cycles")
    return 0 if output["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
