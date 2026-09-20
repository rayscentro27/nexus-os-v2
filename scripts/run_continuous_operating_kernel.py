#!/usr/bin/env python3
"""Bounded unattended kernel exercise using the existing real Alpha reader."""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import multiprocessing
import subprocess
import threading
import uuid
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
from nexus_agent_platform.research_lane_scheduler import select_lane  # noqa: E402
from nexus_agent_platform.research_work_queue import concurrency_limits, default_queue, worker_bucket  # noqa: E402
from nexus_agent_platform.productivity_audit import run_productivity_audit  # noqa: E402

WAKE_TIMEOUT_SECONDS = int(os.environ.get("NEXUS_WAKE_TIMEOUT_SECONDS", "45"))
PROGRESS_PATH = ROOT / "reports/runtime/nexus_research_wake_progress.json"
EXECUTION_JOBS_PATH = ROOT / "data/runtime/research_execution_jobs.jsonl"


def _append_execution_event(execution_id: str, status: str, **values) -> None:
    """Persist scheduler/worker handoff state without making it a second queue."""
    EXECUTION_JOBS_PATH.parent.mkdir(parents=True, exist_ok=True)
    event = {"execution_id": execution_id, "status": status, "at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(), **values}
    with EXECUTION_JOBS_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, sort_keys=True) + "\n")
        handle.flush()


def _write_wake_progress(stage: str, **values) -> None:
    """Write sparse parent-side wake telemetry; never make it a new failure."""
    try:
        PROGRESS_PATH.parent.mkdir(parents=True, exist_ok=True)
        PROGRESS_PATH.write_text(json.dumps({
            "schema_version": "nexus.research-wake-progress.v1",
            "stage": stage,
            "updated_at": time.time(),
            **values,
        }, indent=2) + "\n", encoding="utf-8")
    except OSError:
        pass


def _reap_worker(process: subprocess.Popen) -> None:
    """Reap detached Research workers without making the kernel wait for them."""
    try:
        process.wait()
    except (OSError, ChildProcessError):
        pass


def _invoke_research_callback(callback, result_queue):
    """Run one wake callback in a killable child process.

    A thread timeout cannot stop a blocking provider/operator call.  The fork
    boundary is deliberately local to the existing callback and keeps the
    canonical operator/Alpha path unchanged.
    """
    try:
        result_queue.put({"ok": True, "result": callback()})
    except BaseException as exc:  # child must always return a classified result
        result_queue.put({"ok": False, "failure_class": type(exc).__name__, "exact_failure": str(exc)[:500]})


def bounded_wake(callback, timeout_seconds=WAKE_TIMEOUT_SECONDS, command=None, env=None):
    """Dispatch a worker and return; long research is never a scheduler wait."""
    if command:
        started = time.monotonic()
        execution_id = (env or {}).get("NEXUS_EXECUTION_ID") or f"research_exec_{uuid.uuid4().hex[:20]}"
        log_dir = ROOT / "reports/runtime/research_dispatch"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / f"{execution_id}.log"
        try:
            _append_execution_event(execution_id, "QUEUED", worker="research_operator_worker", timeout_seconds=timeout_seconds, log_path=str(log_path))
            with log_path.open("w", encoding="utf-8") as log:
                # Workers are autonomous children, never interactive command
                # sessions.  Detach stdin explicitly so launch contexts with
                # a closed/invalid fd 0 cannot abort Python before the worker
                # reaches its bounded Research handler.
                process = subprocess.Popen(command, cwd=ROOT, env=env, stdin=subprocess.DEVNULL,
                                           stdout=log, stderr=subprocess.STDOUT, text=True, start_new_session=True)
            _append_execution_event(execution_id, "DISPATCHED", pid=process.pid, worker="research_operator_worker")
            # The worker is intentionally detached from stdin/session, but it
            # remains a child of this daemon. Reap it asynchronously so a
            # completed or failed job cannot accumulate as a zombie.
            threading.Thread(target=_reap_worker, args=(process,), daemon=True,
                             name=f"reap-{execution_id}").start()
            _write_wake_progress("WORK_DISPATCHED", execution_id=execution_id, pid=process.pid)
            return {"status": "DISPATCHED", "execution_mode": "REAL", "task_processing": "DELEGATED",
                    "execution_id": execution_id, "worker_pid": process.pid,
                    "selected_lane_id": (env or {}).get("NEXUS_SELECTED_LANE_ID"),
                    "selected_lane_name": (env or {}).get("NEXUS_SELECTED_LANE_NAME"),
                    "selection_reason": (env or {}).get("NEXUS_SELECTED_LANE_REASON"),
                    "scheduler_wait_seconds": round(time.monotonic() - started, 3),
                    "next_action": "worker persists evidence and Alpha result asynchronously"}
        except OSError as exc:
            _append_execution_event(execution_id, "FAILED_RETRYABLE", error=str(exc)[:500], failure_class="DISPATCH_FAILURE")
            return {"status": "DEGRADED", "failure_class": "OPERATOR_START_FAILURE",
                    "exact_failure": str(exc), "recovery_attempt": "operator start classified",
                    "recovery_result": "CONTINUE_NEXT_WAKE",
                    "next_action": "preserve work and select another due lane"}
    context = multiprocessing.get_context("fork")
    result_queue = context.Queue(maxsize=1)
    process = context.Process(target=_invoke_research_callback, args=(callback, result_queue))
    started = time.monotonic()
    process.start()
    process.join(timeout_seconds)
    if process.is_alive():
        process.terminate()
        process.join(5)
        return {
            "status": "DEGRADED",
            "failure_class": "WAKE_TIMEOUT",
            "exact_failure": f"wake exceeded {timeout_seconds}s operator/Alpha boundary",
            "recovery_attempt": "terminated isolated callback; preserve work for next wake",
            "recovery_result": "CONTINUE_NEXT_WAKE",
            "next_action": "defer timed-out work and select another due lane",
            "duration_seconds": round(time.monotonic() - started, 3),
        }
    if not result_queue.empty():
        payload = result_queue.get()
        if payload.get("ok"):
            result = payload.get("result") or {}
            result.setdefault("status", "PASS")
            result["wake_boundary_seconds"] = round(time.monotonic() - started, 3)
            return result
        return {
            "status": "DEGRADED",
            "failure_class": payload.get("failure_class", "CALLBACK_FAILURE"),
            "exact_failure": payload.get("exact_failure", "isolated callback failed"),
            "recovery_attempt": "callback failure classified",
            "recovery_result": "CONTINUE_NEXT_WAKE",
            "next_action": "preserve work and select another due lane",
        }
    return {
        "status": "DEGRADED",
        "failure_class": "CALLBACK_NO_RESULT",
        "exact_failure": f"isolated callback exited without a result (exit={process.exitcode})",
        "recovery_attempt": "callback boundary closed",
        "recovery_result": "CONTINUE_NEXT_WAKE",
        "next_action": "preserve work and select another due lane",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cycles", type=int, default=2)
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--interval-seconds", type=int, default=1200)
    parser.add_argument("--max-cycles", type=int, default=0)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    if not args.daemon and not 1 <= args.cycles <= 6:
        print(json.dumps({"ok": False, "error": "cycles must be 1..6"})); return 2
    if args.interval_seconds < 30:
        print(json.dumps({"ok": False, "error": "interval-seconds must be >= 30"})); return 2
    sources = build_source_registry()
    programs = build_program_registry(source_registry=sources)
    receipts = []
    limit = args.max_cycles if args.daemon and args.max_cycles > 0 else (args.cycles if not args.daemon else None)
    index = 0
    batch_started = 0
    batch_counts = {"youtube": 0, "web": 0, "discovery": 0}
    audit_results = []
    limits = concurrency_limits()
    while limit is None or index < limit:
        audit = run_productivity_audit(startup=(index == 0), force=False)
        if audit.get("status") != "SKIPPED_INTERVAL":
            audit_results.append(audit)
        if args.daemon and batch_started >= limits["total"]:
            time.sleep(args.interval_seconds)
            batch_started = 0
            batch_counts = {"youtube": 0, "web": 0, "discovery": 0}
        # Do not scan the append-only Alpha content ledger on every unattended
        # wake.  It is an optional maintenance input and can grow independently
        # of the Research heartbeat; a full-file read here previously held the
        # operating kernel in I/O before it could dispatch Research.  Scheduled
        # Research remains the liveness-critical path.  The bounded foreground
        # mode retains the existing freshness refresh behavior.
        stale_records = [] if args.daemon else [r for r in persistence.read_records("alpha_content") if refresh_due(r)]
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
                # A department action must not suppress the Research
                # heartbeat. If this wake served another department, run one
                # bounded public-research cycle as the intelligence step for
                # the same wake and persist both results in the receipt.
                if not any(str(action).startswith("research.") for action in operator.get("actions_executed", [])):
                    research = alpha_run(
                        "AI_NEXUS" if index % 2 == 0 else "BUSINESS",
                        "Identify one current, evidence-backed Nexus capability or business question that should be investigated next.",
                        None,
                        ["https://modelcontextprotocol.io/specification/2025-06-18"], [], [], [], [], "LAST_30_DAYS",
                    )
                    result["heartbeat_research"] = {
                        "status": "PASS" if research.get("ok") else "DEGRADED",
                        "research_id": research.get("research", {}).get("research_id"),
                        "content_count": research.get("content_count", 0),
                    }
                    result["status"] = "PASS" if result.get("status") not in {"FAILED", "DEGRADED"} and research.get("ok") else result.get("status", "DEGRADED")
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
        execution_id = f"research_exec_{uuid.uuid4().hex[:20]}"
        operator_command = [sys.executable, str(ROOT / "scripts/research/run_dispatched_research_job.py"), "--execution-id", execution_id, "--timeout-seconds", str(int(os.environ.get("NEXUS_RESEARCH_JOB_TIMEOUT_SECONDS", "180")))]
        # Batch counters protect this daemon's foreground loop, but priority
        # work is claimed before the detached worker starts and can therefore
        # outlive/re-enter the loop boundary. Include live queue leases in the
        # same bucket decision so a restart or detached child cannot launch a
        # second web/discovery/youtube job past its configured cap.
        blocked_buckets = {bucket for bucket, count in batch_counts.items() if count >= limits[bucket]}
        live_bucket_counts = {bucket: 0 for bucket in limits if bucket != "total"}
        queue_snapshot = default_queue()
        queue_snapshot.recover_expired_leases()
        for active_item in queue_snapshot.load().get("items", []):
            if active_item.get("status") == "IN_PROGRESS":
                bucket = worker_bucket(active_item)
                if bucket in live_bucket_counts:
                    live_bucket_counts[bucket] += 1
        blocked_buckets.update(bucket for bucket, count in live_bucket_counts.items() if count >= limits[bucket])
        lane = select_lane(reason="priority_work_class", blocked_buckets=blocked_buckets)
        if lane.get("work_id"):
            bucket = worker_bucket(lane)
            if batch_counts[bucket] >= limits[bucket]:
                # This is a defensive guard for a race between selector and
                # parent bookkeeping. Normal selection excludes full buckets.
                default_queue().release(str(lane["work_id"]), reason=f"{bucket}_concurrency_cap")
                receipt = run_cycle(lambda: {"status": "NO_ACTION_REQUIRED", "execution_mode": "SUPERVISED",
                                             "selection_reason": f"{bucket}_concurrency_cap",
                                             "selected_work_class": lane.get("selected_work_class")},
                                    cycle_id=f"kernel_cycle_{index + 1}", queue_empty=True,
                                    incomplete_objectives=1, interval_seconds=args.interval_seconds,
                                    scheduler="ACTIVE_DAEMON" if args.daemon else "ACTIVE_IN_PROCESS_CYCLE")
                receipts.append(receipt)
                index += 1
                batch_started += 1
                continue
        if lane.get("no_source_selected"):
            receipt = run_cycle(lambda: {"status": "NO_ACTION_REQUIRED", "execution_mode": "REAL",
                                         "task_processing": "SUPERVISED", "selection_reason": lane.get("selection_reason"),
                                         "selected_work_class": lane.get("selected_work_class")},
                                cycle_id=f"kernel_cycle_{index + 1}", queue_empty=True,
                                incomplete_objectives=0, interval_seconds=args.interval_seconds,
                                scheduler="ACTIVE_DAEMON" if args.daemon else "ACTIVE_IN_PROCESS_CYCLE")
            receipts.append(receipt)
            index += 1
            batch_started += 1
            if args.daemon and (limit is None or index < limit):
                if batch_started >= limits["total"]:
                    time.sleep(args.interval_seconds)
                    batch_started = 0
                    batch_counts = {"youtube": 0, "web": 0, "discovery": 0}
            continue
        operator_env = {**os.environ, "NEXUS_SELECTED_LANE_ID": lane["lane_id"],
                        "NEXUS_SELECTED_LANE_NAME": lane["name"],
                        "NEXUS_SELECTED_LANE_REASON": lane["selection_reason"],
                        "NEXUS_SELECTED_WORK_CLASS": lane.get("selected_work_class", "DISCOVERY"),
                        "NEXUS_MISSION_ID": str((lane.get("mission_item") or {}).get("mission_id", "")),
                        "NEXUS_MISSION_ITEM_ID": str((lane.get("mission_item") or {}).get("item_id", "")),
                        "NEXUS_SELECTED_LANE_WHY": json.dumps({
                            "materiality": lane.get("materiality_basis", {}),
                            "age": lane.get("age_basis", {}),
                            "progression": lane.get("progression_basis", {}),
                            "fairness": lane.get("fairness_basis", {}),
                            "alternatives": lane.get("alternatives_considered", []),
                        }, sort_keys=True),
                        "NEXUS_EXECUTION_ID": execution_id,
                        "NEXUS_WORK_ID": str(lane.get("work_id", "")),
                        "NEXUS_WORK_ITEM_JSON": json.dumps(lane, sort_keys=True, default=str) if lane.get("work_id") else ""}
        _write_wake_progress("WORK_SELECTED", cycle_id=f"kernel_cycle_{index + 1}", selected_lane_id=lane["lane_id"])
        receipt = run_cycle(lambda: bounded_wake(real_research, command=operator_command, timeout_seconds=int(os.environ.get("NEXUS_RESEARCH_JOB_TIMEOUT_SECONDS", "180")), env=operator_env), cycle_id=f"kernel_cycle_{index + 1}", queue_empty=True,
                                  incomplete_objectives=1, stale_claims=len(stale_records), interval_seconds=args.interval_seconds,
                                  scheduler="ACTIVE_DAEMON" if args.daemon else "ACTIVE_IN_PROCESS_CYCLE")
        _write_wake_progress("WAKE_FINALIZING", cycle_id=f"kernel_cycle_{index + 1}", result_status=receipt["result"].get("status"))
        receipts.append(receipt)
        index += 1
        batch_started += 1
        batch_counts[worker_bucket(lane)] += 1
        if args.daemon and (limit is None or index < limit):
            if batch_started >= limits["total"]:
                time.sleep(args.interval_seconds)
                batch_started = 0
                batch_counts = {"youtube": 0, "web": 0, "discovery": 0}
        # Non-daemon invocations intentionally honor --cycles. The previous
        # unconditional break made a requested second wake unreachable.
    successful_statuses = {"PASS", "COMPLETED", "COMPLETED_WITH_FINDINGS", "NO_ACTION_REQUIRED"}
    output = {"ok": bool(receipts) and all(r["result"].get("status") in successful_statuses for r in receipts), "cycles": len(receipts),
              "programs": len(programs), "sources": len(sources), "receipts": receipts,
              "productivity_audits": audit_results,
              "no_external_action": True}
    print(json.dumps(output, indent=2) if args.json else f"Continuous kernel {'PASS' if output['ok'] else 'DEGRADED'}: {len(receipts)} cycles")
    return 0 if output["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
