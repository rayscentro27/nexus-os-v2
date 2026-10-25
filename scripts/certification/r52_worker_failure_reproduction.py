#!/usr/bin/env python3
"""Offline reproduction of the captured r51 egress/cleanup failure and r52 guard."""
from __future__ import annotations

import json
import os
import tempfile
from unittest.mock import patch
from pathlib import Path

from nexus_agent_platform import job_worker_once, supabase_egress_guard as guard


CAPTURED_R51_TOTAL_BYTES = 15_069_905
CAPTURED_R51_LARGEST_RESPONSE_BYTES = 14_893_899
NORMAL_RESPONSE_BUDGET_BYTES = 2_000_000


def reproduce() -> dict[str, object]:
    previous_dir = guard.JOB_EGRESS_DIR
    old_env = {key: os.environ.get(key) for key in (
        "NEXUS_DURABLE_JOB_ID", "NEXUS_DURABLE_EXECUTION_ID", "NEXUS_JOB_BUDGET")}
    try:
        with tempfile.TemporaryDirectory(prefix="r52-egress-repro-") as tmp:
            guard.JOB_EGRESS_DIR = Path(tmp)
            os.environ["NEXUS_DURABLE_JOB_ID"] = "job-r52-repro"
            os.environ["NEXUS_DURABLE_EXECUTION_ID"] = "attempt-1"
            os.environ["NEXUS_JOB_BUDGET"] = json.dumps({
                "max_requests": 120, "max_response_bytes": NORMAL_RESPONSE_BUDGET_BYTES})
            guard.record_request("GET", "research_proactive_memory?select=payload&limit=4",
                200, CAPTURED_R51_LARGEST_RESPONSE_BYTES, rows=4, trace=False)
            snapshot = guard.job_egress_snapshot("job-r52-repro")
            r51_over_budget = snapshot.get("attempt_response_bytes", 0) > NORMAL_RESPONSE_BUDGET_BYTES
            try:
                guard.preflight_request("GET", "nexus_durable_jobs?job_id=eq.job-r52-repro&select=job_id,state&limit=1")
                r51_cleanup_blocked = False
            except guard.JobEgressBudgetExceeded:
                r51_cleanup_blocked = True

            # Simulate a fresh r52 execution with the compact current-state
            # projection. The response is deliberately small and bounded.
            (Path(tmp) / "job-r52-repro.json").unlink(missing_ok=True)
            os.environ["NEXUS_DURABLE_EXECUTION_ID"] = "attempt-2"
            guard.preflight_request("GET", "research_proactive_memory?memory_kind=in.(RESEARCH_CASE,PROACTIVE_RESEARCH_CASE)&select=memory_id,memory_kind,recorded_at&limit=100")
            guard.record_request("GET", "research_proactive_memory?memory_kind=in.(RESEARCH_CASE,PROACTIVE_RESEARCH_CASE)&select=memory_id,memory_kind,recorded_at&limit=100",
                                 200, 24_000, rows=100, trace=False)
            compact_bytes = guard.job_egress_snapshot("job-r52-repro").get("attempt_response_bytes", 0)
            # Model the cap crossing on a later governed request: exact-job
            # cleanup remains available while Research data access is denied.
            guard._update_job_egress(method="GET", path="research_sources?select=id&limit=1",
                                     response_bytes=NORMAL_RESPONSE_BUDGET_BYTES, rows=1)
            with patch.object(guard, "_trusted_cleanup_caller", return_value="PACKAGED_WORKER"):
                with job_worker_once._worker_cleanup_scope("job-r52-repro", "worker-r52-repro", attempt=1):
                    guard.preflight_request("GET", "nexus_durable_jobs?job_id=eq.job-r52-repro&attempt_count=eq.1&select=job_id,state&limit=1")
                    cleanup_allowed = True
                    try:
                        guard.preflight_request("GET", "research_proactive_memory?memory_id=eq.x&select=payload&limit=1")
                        research_after_budget_denied = False
                    except guard.JobEgressBudgetExceeded:
                        research_after_budget_denied = True
            return {
                "r51_total_response_bytes": CAPTURED_R51_TOTAL_BYTES,
                "r51_largest_response_bytes": CAPTURED_R51_LARGEST_RESPONSE_BYTES,
                "r51_over_budget": r51_over_budget,
                "r51_cleanup_blocked": r51_cleanup_blocked,
                "r52_compact_response_bytes": compact_bytes,
                "r52_cleanup_allowed": cleanup_allowed,
                "r52_research_after_budget_denied": research_after_budget_denied,
                "r52_failure_resolved": all((r51_over_budget, r51_cleanup_blocked,
                    compact_bytes < NORMAL_RESPONSE_BUDGET_BYTES, cleanup_allowed,
                    research_after_budget_denied)),
            }
    finally:
        guard.JOB_EGRESS_DIR = previous_dir
        for key, value in old_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


if __name__ == "__main__":
    print(json.dumps(reproduce(), sort_keys=True))
