#!/usr/bin/env python3
"""Independent Alpha validation worker for persisted Research evidence."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
JOBS = ROOT / "data/runtime/research_execution_jobs.jsonl"
sys.path.insert(0, str(ROOT / "scripts"))
from nexus_agent_platform.research_alpha_pipeline import evaluate_pending  # noqa: E402


def event(execution_id: str, status: str, **values) -> None:
    JOBS.parent.mkdir(parents=True, exist_ok=True)
    row = {"execution_id": execution_id, "status": status, "at": datetime.now(timezone.utc).isoformat(), **values}
    with JOBS.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")
        handle.flush()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execution-id", required=True)
    args = parser.parse_args()
    event(args.execution_id, "ALPHA_RUNNING", worker_id="alpha_validation_worker")
    result = evaluate_pending(max_items=20)
    event(args.execution_id, "ALPHA_COMPLETED", worker_id="alpha_validation_worker", evaluations_created=result.get("evaluated_count", 0), next_action="continue next scheduled research wake")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
