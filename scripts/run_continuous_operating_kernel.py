#!/usr/bin/env python3
"""Bounded unattended kernel exercise using the existing real Alpha reader."""
from __future__ import annotations

import argparse
import json
import os
import re
import signal
import sys
import time
import multiprocessing
import queue
import subprocess
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


def child_environment(base=None):
    """Build a network-safe environment for every kernel child process.

    NO_PROXY is process-local. It prevents urllib on macOS from falling back
    to SystemConfiguration proxy discovery (which loads _scproxy), while
    sending requests directly because this runtime does not require a proxy.
    """
    environment = dict(os.environ if base is None else base)
    environment["NO_PROXY"] = "*"
    environment["no_proxy"] = "*"
    scripts_path = str(ROOT / "scripts")
    environment["PYTHONPATH"] = scripts_path + (os.pathsep + environment["PYTHONPATH"] if environment.get("PYTHONPATH") else "")
    try:
        mode_config = json.loads((ROOT / "configs/nexus_operating_mode.json").read_text(encoding="utf-8"))
        weekend = mode_config.get("weekend_mode", {})
    except (OSError, ValueError, TypeError):
        weekend = {}
    if isinstance(weekend, dict) and weekend.get("enabled") is True:
        # Keep the existing kernel and workers, with conservative Mac limits
        # applied only while the governed weekend test is enabled.
        environment.update({
            "NEXUS_RESEARCH_MAX_TOTAL_CONCURRENCY": "1",
            "NEXUS_RESEARCH_MAX_YOUTUBE_CONCURRENCY": "1",
            "NEXUS_RESEARCH_MAX_WEB_CONCURRENCY": "1",
            "NEXUS_RESEARCH_MAX_DISCOVERY_CONCURRENCY": "1",
            "NEXUS_NOTEBOOK_MAX_BACKGROUND_SHELLS": "1",
            "MAX_BACKGROUND_SHELLS": "1",
            "MAX_PARALLEL_PYTHON_CHILDREN": "1",
        })
    return environment


# Forked callback workers inherit the parent environment rather than receiving
# a Popen env mapping, so establish the same policy before any worker can fork.
os.environ.update(child_environment())

from alpha.run_alpha_discovery_cycle import run as alpha_run  # noqa: E402
from alpha.alpha_discovery import retrieve_page  # noqa: E402
from nexus_agent_platform.governed import persistence  # noqa: E402
from nexus_agent_platform.continuous_operating_kernel import (build_program_registry, build_source_registry,
    idle_research_wake_requires_wait, market_wake_due, run_cycle)
from nexus_agent_platform.knowledge_freshness import refresh_due, refresh_once  # noqa: E402
from nexus_agent_platform.research_alpha_pipeline import evaluate_pending  # noqa: E402
from nexus_agent_platform.research_lane_scheduler import select_lane  # noqa: E402
from nexus_agent_platform.research_work_queue import (CLAIMABLE_STATUSES, concurrency_limits, default_queue,
    is_historical_backlog, parse_time, worker_bucket)  # noqa: E402
from nexus_agent_platform.productivity_audit import run_productivity_audit  # noqa: E402

# A single bounded heartbeat checks only two designated YouTube feeds, one
# small trend sample, and at most one web query. Allow the full sequential
# network timeout budget to finish while still bounding any stuck provider.
WAKE_TIMEOUT_SECONDS = int(os.environ.get("NEXUS_WAKE_TIMEOUT_SECONDS", "90"))
PROGRESS_PATH = ROOT / "reports/runtime/nexus_research_wake_progress.json"
EXECUTION_JOBS_PATH = ROOT / "data/runtime/research_execution_jobs.jsonl"


def now() -> str:
    """Canonical UTC timestamp used by the existing continuous-loop receipts."""
    return datetime.now(timezone.utc).isoformat()


def fifo_work_ready(items: list[dict], current_time: datetime) -> bool:
    """Whether the local FIFO contains immediately claimable canonical work."""
    return any(
        row.get("status") in CLAIMABLE_STATUSES
        and not is_historical_backlog(row)
        and (not parse_time(row.get("next_eligible_at")) or parse_time(row.get("next_eligible_at")) <= current_time)
        and row.get("work_class") in {"ASSIGNED", "MONITORED", "DEMAND_DISCOVERY", "GENERAL_DISCOVERY"}
        for row in items
    )


def run_market_intelligence_wake(cycle_number: int) -> dict:
    """Run one bounded market-intelligence wake from the existing daemon.

    This is an additive bridge only: the heartbeat owns its existing durable
    seed registry, deterministic lane rotation, receipts, and interpretation
    trigger.  It does not create another queue or scheduler.
    """
    try:
        from research.run_market_intelligence_heartbeat import cycle, seed_topics
        topics = seed_topics()
        if not topics:
            return {"status": "FAILED_RETRYABLE", "error": "no_enabled_heartbeat_seeds"}
        # The heartbeat already bounds each collector with a killable
        # lane-level child. Do not wrap the whole heartbeat in another child:
        # nested process boundaries exceed the Mac's one-worker limit.
        result = cycle(cycle_number, followup=False, topics=topics)
        from research.proactive_research_memory import close_due_research_cases
        case_lifecycle = close_due_research_cases(limit=50)
        if result.get("status") == "DEGRADED":
            return {**result, "case_lifecycle": case_lifecycle}
        return {
            "status": result.get("status", "COMPLETED"),
            "heartbeat_run_id": result.get("heartbeat_run_id"),
            "topics": result.get("topics", topics),
            "lanes_attempted": result.get("lanes_attempted", 0),
            "lanes_completed": result.get("lanes_completed", 0),
            "lanes_failed": result.get("lanes_failed", 0),
            "supabase_readback": result.get("supabase_readback", False),
            "case_lifecycle": case_lifecycle,
        }
    except Exception as exc:  # one lane/process failure must not kill the daemon
        return {"status": "FAILED_RETRYABLE", "error": f"{type(exc).__name__}: {str(exc)[:300]}"}


def run_pulse_schedule_tick() -> dict:
    """Check Pulse's durable due-time registry during every canonical kernel cycle."""
    try:
        from research.pulse_runtime import tick
        return tick(max_jobs=1)
    except Exception as exc:  # Pulse failures are isolated from the existing scheduler.
        return {"status": "CHECK_ERROR", "error": type(exc).__name__, "next_workflow": "PULSE_SCHEDULER_RECOVERY"}


def run_due_tradingview_monitor() -> dict:
    """Use the existing Alpha source registry and bounded TradingView cycle."""
    registry_path = ROOT / "data/runtime/alpha_source_registry.json"
    try:
        rows = json.loads(registry_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return {"status": "REGISTRY_UNAVAILABLE"}
    source = next((row for row in rows if isinstance(row, dict)
        and row.get("source_id") == "tradingview_editors_picks"), None)
    if not source or not source.get("enabled") or not source.get("monitoring_enabled"):
        return {"status": "SOURCE_DISABLED_OR_MISSING"}
    due = source.get("next_check")
    try:
        due_at = datetime.fromisoformat(str(due).replace("Z", "+00:00")) if due else None
    except ValueError:
        due_at = None
    if due_at and due_at > datetime.now(timezone.utc):
        return {"status": "NOT_DUE", "next_check": due}
    script = ROOT / "scripts/research/run_tradingview_research_cycle.py"
    try:
        completed = subprocess.run([sys.executable, str(script)], cwd=ROOT,
            stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=180,
            env=child_environment())
    except subprocess.TimeoutExpired:
        return {"status": "TIMEOUT", "source_id": "tradingview_editors_picks",
                "next_action": "RETRY_ON_NEXT_SCHEDULED_WAKE"}
    if completed.returncode != 0:
        return {"status": "FAILED", "source_id": "tradingview_editors_picks",
                "error_tail": completed.stderr[-500:]}
    try:
        receipt = json.loads(completed.stdout)
    except (ValueError, TypeError):
        receipt = {"stdout_tail": completed.stdout[-500:]}
    return {"status": "COMPLETED", "source_id": "tradingview_editors_picks",
            "receipt": receipt}


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
        env = child_environment(env)
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
    os.environ.update(child_environment())
    context = multiprocessing.get_context("fork")
    result_queue = context.Queue(maxsize=1)
    process = context.Process(target=_invoke_research_callback, args=(callback, result_queue))
    started = time.monotonic()
    process.start()
    # Consume while the child is running. Joining first can deadlock when a
    # legitimate callback result is larger than the multiprocessing pipe:
    # the child waits for the queue feeder to flush while the parent waits for
    # the child to exit. The callback may already have persisted its receipt.
    deadline = started + max(1, timeout_seconds)
    payload = None
    while time.monotonic() < deadline:
        remaining = max(0.01, deadline - time.monotonic())
        try:
            payload = result_queue.get(timeout=min(0.25, remaining))
            break
        except queue.Empty:
            if not process.is_alive():
                break
    if payload is None and process.is_alive():
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
    process.join(5)
    if payload is not None:
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


def fifo_queue_wake(item: dict, *, execution_id: str, timeout_seconds: int) -> dict:
    """Run one already-claimed FIFO assignment before rereading the queue."""
    log_dir = ROOT / "reports/runtime/research_dispatch"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"{execution_id}.log"
    command = [sys.executable, str(ROOT / "scripts/research/run_dispatched_research_job.py"),
               "--execution-id", execution_id, "--timeout-seconds", str(timeout_seconds)]
    env = child_environment({**os.environ,
           "NEXUS_FIFO_QUEUE": "1",
           "NEXUS_WORK_ID": str(item.get("work_id", "")),
           "NEXUS_OBJECTIVE_ID": str(item.get("objective_id") or ""),
           "NEXUS_SELECTED_LANE_ID": str(item.get("lane_id") or "FIFO_RESEARCH"),
           "NEXUS_SELECTED_LANE_NAME": "Universal FIFO Research",
           "NEXUS_SELECTED_LANE_REASON": "queue_sequence_ascending",
           "NEXUS_SELECTED_WORK_CLASS": str(item.get("work_class") or "GENERAL_DISCOVERY"),
           "NEXUS_WORK_ITEM_JSON": json.dumps(item, sort_keys=True, default=str),
           "NEXUS_PARENT_REQUEST_ID": str(item.get("parent_request_id") or ""),
           "NEXUS_MARKETING_OBJECTIVE_ID": str(item.get("marketing_objective_id") or "")})
    started = time.monotonic()
    def settle_if_stranded(error: str, blocker_type: str) -> None:
        try:
            current = next((row for row in default_queue().load().get("items", [])
                            if row.get("work_id") == item.get("work_id")), None)
            if current and current.get("status") == "IN_PROGRESS":
                default_queue().settle(
                    str(item.get("work_id")), "FAILED_RETRYABLE",
                    result={"error": error, "execution_id": execution_id},
                    blocker_type=blocker_type,
                )
        except Exception as exc:
            _append_execution_event(execution_id, "QUEUE_SETTLE_DEGRADED", error=str(exc)[:300])
    try:
        with log_path.open("w", encoding="utf-8") as log:
            process = subprocess.Popen(command, cwd=ROOT, env=env, stdin=subprocess.DEVNULL,
                                       stdout=log, stderr=subprocess.STDOUT, text=True,
                                       start_new_session=True)
            try:
                exit_code = process.wait(timeout=timeout_seconds + 10)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(process.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                try:
                    exit_code = process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    exit_code = process.wait(timeout=5)
                settle_if_stranded(f"worker exceeded {timeout_seconds + 10}s", "FIFO_WORKER_TIMEOUT")
                return {"status": "DEGRADED", "execution_mode": "REAL", "task_processing": "TIMEOUT",
                        "execution_id": execution_id, "worker_pid": process.pid, "worker_exit_code": exit_code,
                        "queue_sequence": item.get("queue_sequence"), "work_id": item.get("work_id"),
                        "log_path": str(log_path), "failure_class": "FIFO_WORKER_TIMEOUT",
                        "duration_seconds": round(time.monotonic() - started, 3)}
        if exit_code != 0:
            settle_if_stranded(f"worker exited with code {exit_code}", "FIFO_WORKER_FAILURE")
        return {"status": "PASS" if exit_code == 0 else "DEGRADED",
                "execution_mode": "REAL", "task_processing": "COMPLETED",
                "execution_id": execution_id, "worker_exit_code": exit_code,
                "queue_sequence": item.get("queue_sequence"), "work_id": item.get("work_id"),
                "log_path": str(log_path), "duration_seconds": round(time.monotonic() - started, 3),
                "selected_lane_id": "FIFO_RESEARCH", "selection_reason": "queue_sequence_ascending"}
    except Exception as exc:
        settle_if_stranded(f"FIFO worker dispatch failed: {str(exc)[:300]}", "FIFO_WORKER_DISPATCH_FAILURE")
        return {"status": "DEGRADED", "execution_mode": "REAL", "task_processing": "FAILED_RETRYABLE",
                "execution_id": execution_id, "worker_exit_code": None,
                "queue_sequence": item.get("queue_sequence"), "work_id": item.get("work_id"),
                "log_path": str(log_path), "failure_class": "FIFO_WORKER_DISPATCH_FAILURE",
                "duration_seconds": round(time.monotonic() - started, 3)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cycles", type=int, default=2)
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--interval-seconds", type=int, default=1200)
    parser.add_argument("--max-cycles", type=int, default=0)
    parser.add_argument("--feeder-canary", action="store_true", help="Run bounded feeder work inside this kernel wake after Systems; skip unrelated lane dispatch.")
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
    # Continue the existing durable heartbeat sequence after a governed
    # service restart instead of reusing an earlier cycle identifier.
    prior_heartbeat = {}
    try:
        prior_heartbeat = json.loads((ROOT / "data/runtime/research_heartbeat.json").read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        prior_heartbeat = {}
    prior_cycle = str(prior_heartbeat.get("cycle_id") or "")
    if prior_cycle.startswith("kernel_cycle_"):
        try:
            index = int(prior_cycle.rsplit("_", 1)[1])
        except ValueError:
            index = 0
    # The heartbeat can temporarily hold a FIFO worker id. Preserve the
    # kernel's high-water mark from its existing latest receipt and weekend
    # report snapshots so that handoff between worker ids never reuses a
    # kernel cycle identifier.
    for evidence_path in [ROOT / "reports/runtime/continuous_operating_kernel_latest.json",
                          *sorted((ROOT / "reports/weekend").glob("NEXUS_WEEKEND_AUTONOMY_REPORT_*.txt"))]:
        try:
            raw = evidence_path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for match in re.findall(r"kernel_cycle_(\d+)", raw):
            index = max(index, int(match))
    cycles_run = 0
    batch_started = 0
    batch_counts = {"youtube": 0, "web": 0, "discovery": 0}
    # A daemon restart is not itself a scheduled Market Intelligence trigger.
    # Starting at "now" avoids replaying the full collector on every launch;
    # the first normal market wake remains due after the configured interval.
    market_last_run = time.monotonic() if args.daemon else 0.0
    audit_results = []
    limits = concurrency_limits()
    while limit is None or cycles_run < limit:
        # One opaque correlation ID per canonical wake; children inherit it.
        # Do not reuse an operator-provided ID because this boundary owns wake identity.
        os.environ["NEXUS_WAKE_ID"] = f"wake_{uuid.uuid4().hex[:16]}"
        os.environ["NEXUS_WORKER_ID"] = f"continuous-kernel-{os.getpid()}-{index + 1}"
        os.environ["NEXUS_KERNEL_PHASE"] = "PULSE_SCHEDULER_CHECK"
        # Existing scheduler only: check durable Pulse due times on every
        # canonical cycle, independent of Research FIFO activity.
        pulse_result = run_pulse_schedule_tick()
        audit_results.append({"pulse_schedule_tick": pulse_result})
        os.environ["NEXUS_KERNEL_PHASE"] = "SYSTEMS_CHECK"
        # Systems is schedule/condition initiated and runs under this same
        # canonical scheduler. Its checks are deterministic; exceptions are
        # isolated so a failed environment never interrupts company work.
        try:
            systems_process = subprocess.run(
                [sys.executable, "-m", "nexus_agent_platform.systems_workflow", "--scheduled-cycle",
                 "--scheduler", "com.nexus.continuous-loop", "--worker-id",
                 f"continuous-kernel-{os.getpid()}-systems-{index + 1}"],
                cwd=str(ROOT), env=child_environment(), capture_output=True, text=True,
                timeout=int(os.environ.get("NEXUS_SYSTEMS_CHECK_TIMEOUT_SECONDS", "75")), check=False)
            systems_result = json.loads(systems_process.stdout) if systems_process.returncode == 0 else {
                "status": "SYSTEMS_WORKFLOW_DEGRADED", "return_code": systems_process.returncode,
                "error_class": "SYSTEMS_CHILD_FAILED", "diagnostic_tail": (systems_process.stderr or "")[-1200:],
                "next_action": "RETRY_ON_NEXT_CANONICAL_WAKE"}
        except Exception as exc:
            systems_result = {"status": "SYSTEMS_WORKFLOW_DEGRADED", "error_class": type(exc).__name__,
                              "next_action": "RETRY_ON_NEXT_CANONICAL_WAKE"}
        # The feeder consumes work inside this one canonical wake. It is not a
        # competing scheduler: source intake, questionnaire execution, Research
        # return reconciliation, and health receipts all share this kernel.
        try:
            os.environ["NEXUS_KERNEL_PHASE"] = "FEEDER_SCHEDULER_CHECK"
            feeder_env=child_environment()
            feeder_process=subprocess.run([sys.executable,str(ROOT/"scripts/nexus_agent_platform/feeder_runtime.py"),"process-once"],cwd=str(ROOT),env=feeder_env,capture_output=True,text=True,timeout=int(os.environ.get("NEXUS_FEEDER_WAKE_TIMEOUT_SECONDS","360")),check=False)
            feeder_result=json.loads(feeder_process.stdout) if feeder_process.returncode==0 else {"status":"DEGRADED","error_class":"FEEDER_WORKER_FAILED","diagnostic_tail":(feeder_process.stderr or "")[-800:],"next_workflow":"FEEDER_QUEUE_RECOVERY"}
        except Exception as exc:
            feeder_result={"status":"CHECK_ERROR","error_class":type(exc).__name__,"next_workflow":"FEEDER_QUEUE_RECOVERY"}
        systems_receipt_path = ROOT / "data/runtime/systems_workflow_runs.jsonl"
        systems_receipt_path.parent.mkdir(parents=True, exist_ok=True)
        with systems_receipt_path.open("a", encoding="utf-8") as systems_receipt_stream:
            systems_receipt_stream.write(json.dumps({"at": datetime.now(timezone.utc).isoformat(),
                "scheduler": "com.nexus.continuous-loop", "worker_id": f"continuous-kernel-{os.getpid()}-systems-{index + 1}",
                "result": systems_result,"feeder_runtime":feeder_result}, sort_keys=True, default=str) + "\n")
        if args.feeder_canary:
            index += 1
            cycles_run += 1
            receipt = run_cycle(lambda: {"status":feeder_result.get("status","CHECK_ERROR"),"execution_mode":"SUPERVISED","task_processing":"FEEDER_PRODUCTION_PATH_BOUNDED_WAKE","systems_status":systems_result.get("status"),"feeder_runtime":feeder_result,"production_path_bounded_wake":True,"natural_schedule_proof":False},cycle_id=f"feeder_canary_cycle_{uuid.uuid4().hex[:12]}",queue_empty=feeder_result.get("status")=="IDLE_HEALTHY",incomplete_objectives=0,interval_seconds=args.interval_seconds,scheduler="ACTIVE_IN_PROCESS_CYCLE")
            receipts.append(receipt)
            continue
        # Company Case directives have priority over general discovery. They
        # remain in the authoritative case row and are atomically claimed by
        # the existing department continuation runtime before FIFO/lane work.
        try:
            from operations.department_handoff_continuation import process_next_company_case_directive
            directive_result = process_next_company_case_directive(
                worker_id=f"continuous-kernel-{os.getpid()}-cycle-{index + 1}")
        except Exception as exc:
            import traceback
            directive_result = {"status": "DIRECTIVE_RUNTIME_DEGRADED",
                                "error_class": type(exc).__name__,
                                "missing_module": (getattr(exc, "name", None) or str(exc)[:180]) if isinstance(exc, ModuleNotFoundError) else None,
                                "error_frames": [frame.strip() for frame in traceback.format_tb(exc.__traceback__)[-4:]],
                                "next_action": "RETRY_ON_NEXT_SCHEDULED_WAKE"}
        # Due source refreshes are independent company intelligence work. Do
        # not suppress a due TradingView scan merely because another Company
        # Case directive was returned/claimed during this wake; the monitor
        # itself is due-gated and bounded, so checking it here does not create
        # duplicate scans or a second scheduler.
        if directive_result.get("status") != "DIRECTIVE_RUNTIME_DEGRADED":
            directive_result["tradingview_monitor"] = run_due_tradingview_monitor()
        directive_log = ROOT / "data/runtime/company_case_directive_runtime.jsonl"
        directive_result["systems_workflow"] = systems_result
        directive_log.parent.mkdir(parents=True, exist_ok=True)
        with directive_log.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps({"at": datetime.now(timezone.utc).isoformat(), "scheduler": "ACTIVE_DAEMON" if args.daemon else "ACTIVE_IN_PROCESS_CYCLE",
                "worker_id": f"continuous-kernel-{os.getpid()}-cycle-{index + 1}",
                "result": directive_result}, sort_keys=True, default=str) + "\n")
        if directive_result.get("status") == "EXECUTED":
            receipt = run_cycle(lambda: {**directive_result, "execution_mode": "REAL",
                "task_processing": "COMPANY_CASE_DIRECTIVE", "selected_by": "CANONICAL_CONTINUOUS_RUNTIME"},
                cycle_id=f"case_directive_cycle_{index + 1}", queue_empty=False,
                incomplete_objectives=1, interval_seconds=args.interval_seconds,
                scheduler="ACTIVE_DAEMON" if args.daemon else "ACTIVE_IN_PROCESS_CYCLE")
            receipts.append(receipt)
            index += 1
            cycles_run += 1
            continue
        # The existing queue remains the continuous consumer. A due live item
        # is claimed before discovery; archived historical work is inert until
        # an explicit reactivation and the canonical priority order applies.
        fifo_queue = default_queue()
        fifo_queue.migrate_fifo()
        current_time = datetime.now(timezone.utc)
        fifo_work_ready_now = fifo_work_ready(fifo_queue.load().get("items", []), current_time)
        if args.daemon and not fifo_work_ready_now and market_wake_due(
                market_last_run, time.monotonic(), args.interval_seconds):
            os.environ["NEXUS_KERNEL_PHASE"] = "MARKET_HEARTBEAT"
            market_result = run_market_intelligence_wake(index + 1)
            audit_results.append({"market_intelligence_heartbeat": market_result})
            market_last_run = time.monotonic()
        # The production queue is the sole normal Research admission path.
        # Claim by canonical priority, preserving FIFO within each tier, then
        # reread the same durable queue after synchronous execution.
        fifo_item = fifo_queue.claim_next(
            worker_id=f"continuous-fifo-{os.getpid()}",
            allowed_classes=("ASSIGNED", "MONITORED", "DEMAND_DISCOVERY", "GENERAL_DISCOVERY"),
        )
        if fifo_item:
            execution_id = f"research_fifo_{uuid.uuid4().hex[:20]}"
            configured_timeout = int(os.environ.get("NEXUS_RESEARCH_JOB_TIMEOUT_SECONDS", "180"))
            # Long local YouTube ASR is already chunked and independently
            # bounded. Give only YouTube video jobs enough wall-clock budget
            # to finish their finite chunk sequence; other FIFO work keeps
            # the existing bound.
            youtube_job = str(fifo_item.get("source_type", "")).upper() == "YOUTUBE_VIDEO"
            if fifo_item.get("research_processor") == "notebooklm_research_worker":
                fifo_timeout = max(configured_timeout, 3600)
            else:
                fifo_timeout = max(configured_timeout, 360) if youtube_job else configured_timeout
            fifo_result = fifo_queue_wake(
                fifo_item, execution_id=execution_id,
                timeout_seconds=fifo_timeout,
            )
            receipt = run_cycle(lambda: fifo_result, cycle_id=f"fifo_cycle_{index + 1}",
                                queue_empty=False, incomplete_objectives=1,
                                interval_seconds=args.interval_seconds,
                                scheduler="ACTIVE_FIFO_DAEMON" if args.daemon else "ACTIVE_FIFO_CYCLE")
            receipts.append(receipt)
            index += 1
            cycles_run += 1
            # No interval sleep here: follow-ups/retries are appended at the
            # tail and become visible on the next claim.
            continue
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
                cycles_run += 1
                batch_started += 1
                continue
        if lane.get("no_source_selected"):
            def proactive_discovery():
                os.environ["NEXUS_KERNEL_PHASE"] = "PROACTIVE_DISCOVERY"
                from research.notebooklm_research_worker import run_proactive_discovery_cycle
                result = run_proactive_discovery_cycle(force=False)
                result.update({"execution_mode": "REAL", "task_processing": "DISCOVERY_MODE",
                               "queue_empty_does_not_stop": True})
                return result
            def run_proactive_once():
                discovery = bounded_wake(proactive_discovery, timeout_seconds=WAKE_TIMEOUT_SECONDS)
                did_work = bool(discovery.get("selected_task") or
                                (discovery.get("monitored_source_refresh") or {}).get("channels_checked") or
                                (discovery.get("open_trend_discovery") or {}).get("queries_run") or
                                (discovery.get("rotating_proactive_search") or {}).get("queries_run"))
                return {"status": "PASS" if did_work else "NO_ACTION_REQUIRED", "execution_mode": "REAL",
                        "task_processing": "DISCOVERY_MODE" if did_work else "SUPERVISED",
                        "selection_reason": lane.get("selection_reason"),
                        "selected_work_class": lane.get("selected_work_class"),
                        "proactive_discovery": discovery,
                        "next_action": "RUN_BOUNDED_AUTONOMOUS_DISCOVERY" if not did_work else "PROCESS_DISCOVERED_RESEARCH_WORK"}
            receipt = run_cycle(run_proactive_once,
                                cycle_id=f"kernel_cycle_{index + 1}", queue_empty=True,
                                incomplete_objectives=0, interval_seconds=args.interval_seconds,
                                scheduler="ACTIVE_DAEMON" if args.daemon else "ACTIVE_IN_PROCESS_CYCLE")
            receipts.append(receipt)
            index += 1
            cycles_run += 1
            batch_started += 1
            if args.daemon and (limit is None or index < limit):
                queue_after_wake = default_queue().load().get("items", [])
                if idle_research_wake_requires_wait(
                        daemon=True,
                        queue_work_ready=fifo_work_ready(queue_after_wake, datetime.now(timezone.utc)),
                        batch_started=batch_started, batch_limit=limits["total"]):
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
                        "NEXUS_OBJECTIVE_ID": str(lane.get("scheduler_objective_id") or lane.get("objective_id") or ""),
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
        cycles_run += 1
        batch_started += 1
        batch_counts[worker_bucket(lane)] += 1
        if args.daemon and (limit is None or index < limit):
            if batch_started >= limits["total"]:
                time.sleep(args.interval_seconds)
                batch_started = 0
                batch_counts = {"youtube": 0, "web": 0, "discovery": 0}
        # Non-daemon invocations intentionally honor --cycles. The previous
        # unconditional break made a requested second wake unreachable.
    successful_statuses = {"PASS", "COMPLETED", "COMPLETED_WITH_FINDINGS", "NO_ACTION_REQUIRED", "IDLE_HEALTHY"}
    output = {"ok": bool(receipts) and all(r["result"].get("status") in successful_statuses for r in receipts), "cycles": len(receipts),
              "programs": len(programs), "sources": len(sources), "receipts": receipts,
              "productivity_audits": audit_results,
              "no_external_action": True}
    print(json.dumps(output, indent=2) if args.json else f"Continuous kernel {'PASS' if output['ok'] else 'DEGRADED'}: {len(receipts)} cycles")
    return 0 if output["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
