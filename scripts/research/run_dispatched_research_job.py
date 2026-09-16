#!/usr/bin/env python3
"""Worker-side Research execution for a non-blocking scheduled wake."""
from __future__ import annotations

import argparse
import json
import os
import signal
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
JOBS = ROOT / "data/runtime/research_execution_jobs.jsonl"
sys.path.insert(0, str(ROOT / "scripts"))
from alpha.run_alpha_discovery_cycle import run as alpha_run  # noqa: E402
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
    parser.add_argument("--timeout-seconds", type=int, default=180)
    args = parser.parse_args()
    execution_id = args.execution_id
    event(execution_id, "CLAIMED", worker_id="research_operator_worker", attempt_count=1)
    event(execution_id, "RUNNING", worker_id="research_operator_worker", timeout_seconds=args.timeout_seconds)
    def timeout_handler(signum, frame):
        raise TimeoutError(f"per-job timeout after {args.timeout_seconds}s")
    try:
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(args.timeout_seconds)
        # This is the existing bounded, read-only Alpha reader. It is
        # deliberately independent of the Active Operator singleton so the
        # scheduler's delegation path cannot be blocked by operator overlap.
        result = alpha_run(
            os.environ.get("NEXUS_SELECTED_LANE_ID", "AI_NEXUS"),
            "Find current public evidence about safe bounded agent operations and identify the next internal improvement test.",
            None,
            ["https://modelcontextprotocol.io/specification/2025-06-18"], [], [], [], [], "LAST_30_DAYS",
        )
        alpha_result = evaluate_pending(max_items=20)
        signal.alarm(0)
    except TimeoutError as exc:
        signal.alarm(0)
        event(execution_id, "FAILED_RETRYABLE", worker_id="research_operator_worker", error=str(exc), failure_class="PROVIDER_OR_ALPHA_TIMEOUT", retry_after="next scheduled wake")
        return 124
    except Exception as exc:
        signal.alarm(0)
        event(execution_id, "FAILED_RETRYABLE", worker_id="research_operator_worker", error=str(exc)[:500], failure_class="RESEARCH_WORKER_FAILURE", retry_after="next scheduled wake")
        return 1
    event(execution_id, "EVIDENCE_READY", worker_id="research_operator_worker", result_status="PASS" if result.get("ok") else "DEGRADED", research_id=result.get("research", {}).get("research_id"), content_count=result.get("content_count", 0))
    event(execution_id, "ALPHA_PENDING", worker_id="alpha_validation_worker", next_action="evaluate persisted evidence asynchronously")
    event(execution_id, "ALPHA_RUNNING", worker_id="alpha_validation_worker", evaluations_created=alpha_result.get("evaluated_count", 0))
    event(execution_id, "COMPLETED" if result.get("ok") else "FAILED_RETRYABLE", worker_id="alpha_validation_worker", alpha_status="COMPLETED", evaluations_created=alpha_result.get("evaluated_count", 0), next_action="continue next scheduled research wake")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
