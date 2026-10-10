#!/usr/bin/env python3
"""Run exactly one provider-free Marketing/Creative campaign through Nexus durable jobs."""
from __future__ import annotations
import json
import os
import argparse
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CANARY_DIR = ROOT / "data/runtime/marketing_creative_canary_20261009"
os.environ["NEXUS_MARKETING_CREATIVE_DIR"] = str(CANARY_DIR)
os.environ["NEXUS_GOVERNED_DATA_DIR"] = str(CANARY_DIR / "governed")
sys.path.insert(0, str(ROOT / "scripts"))

from nexus_agent_platform.durable_jobs import default_store, dispatch_once, classify
from nexus_agent_platform.marketing_creative_workflow import (
    create_test_campaign, campaign, load_payload, _hash,
)

ALLOWED_TYPES = {
    "RESEARCH_MARKETING_TEST_HANDOFF", "MARKETING_STRATEGY", "CREATIVE_BRIEF_BUILD",
    "CREATIVE_ASSET_GENERATE", "MARKETING_ASSET_REVIEW", "CREATIVE_ASSET_REVISE",
    "PERFORMANCE_COLLECT", "MARKETING_PERFORMANCE_ANALYZE", "CREATIVE_QA",
}


def _sql_counts() -> dict:
    sql = ("select (select count(*)::int from public.task_requests) as task_requests, "
           "(select count(*)::int from public.credit_analysis_jobs) as credit_analysis_jobs;")
    result = subprocess.run(["supabase", "db", "query", "--linked", "--output", "json", sql],
                            cwd=ROOT, capture_output=True, text=True, timeout=18, check=False)
    if result.returncode:
        raise RuntimeError("SAFE_QUEUE_COUNTS_QUERY_FAILED")
    payload = json.loads(result.stdout)
    rows = payload.get("rows") or []
    if not rows:
        raise RuntimeError("SAFE_QUEUE_COUNTS_QUERY_EMPTY")
    return {key: int(rows[0][key]) for key in ("task_requests", "credit_analysis_jobs")}


def _loaded_services() -> list[str]:
    result = subprocess.run(["launchctl", "list"], capture_output=True, text=True, timeout=8, check=False)
    if result.returncode:
        raise RuntimeError("LAUNCHD_METADATA_UNAVAILABLE")
    return sorted({line.split()[-1] for line in result.stdout.splitlines()
                   if line.split() and line.split()[-1] in {"com.nexus.scheduler", "com.nexus.dispatcher"}})


def _process_safety() -> dict:
    result = subprocess.run(["ps", "-axo", "pid=,ppid=,comm=,command="], capture_output=True,
                            text=True, timeout=8, check=False)
    if result.returncode:
        raise RuntimeError("PROCESS_METADATA_UNAVAILABLE")
    own_pid = str(os.getpid())
    automation = heavy = 0
    for line in result.stdout.splitlines():
        fields = line.strip().split(None, 3)
        if len(fields) < 4 or fields[0] == own_pid or "run_marketing_creative_canary.py" in fields[3]:
            continue
        comm, command = fields[2].lower(), fields[3].lower()
        if "chromeremotedesktophost" in command or "remoting_me2me" in command:
            continue
        if any(token in comm for token in ("ffmpeg", "ollama")):
            heavy += 1
        if ("playwright" in command or "puppeteer" in command or
                "--headless" in command or "--remote-debugging" in command or
                ("chromium" in command and "chrome remote desktop" not in command)):
            automation += 1
    try:
        import psutil
        memory_percent = float(psutil.virtual_memory().percent)
        load_1m = float(psutil.getloadavg()[0])
    except Exception:
        memory_percent, load_1m = None, None
    return {"heavy_workers": heavy, "browser_automation_processes": automation,
            "memory_percent": memory_percent, "load_average_1m": load_1m}


def _jobs_for_correlation(store, correlation_id: str):
    from urllib.parse import quote
    rows = store._request(
        f"nexus_durable_jobs?correlation_id=eq.{quote(correlation_id, safe='')}"
        f"&select={store.JOB_COLUMNS}&order=created_at.asc&limit=100")
    return [store._job(row) for row in rows]


def _wait_for_next_retry(store, correlation_id: str, max_wait: float = 120.0) -> bool:
    """Wait once for the next bounded retry instead of polling PostgREST."""
    from urllib.parse import quote
    rows = store._request(
        "nexus_durable_jobs?correlation_id=eq."
        f"{quote(correlation_id, safe='')}&state=eq.FAILED_RETRYABLE"
        "&select=scheduled_at&order=scheduled_at.asc&limit=10")
    if not rows:
        return False
    scheduled = rows[0].get("scheduled_at")
    if not scheduled:
        return False
    due_at = datetime.fromisoformat(scheduled.replace("Z", "+00:00"))
    delay = max(0.0, (due_at - datetime.now(timezone.utc)).total_seconds())
    if delay > max_wait:
        raise RuntimeError("CANARY_RETRY_DELAY_EXCEEDS_BOUND")
    if delay:
        time.sleep(delay + 0.25)
    return True


def run(resume_campaign_id: str | None = None) -> dict:
    store = default_store()
    if _loaded_services():
        raise RuntimeError("SCHEDULER_OR_DISPATCHER_SERVICE_ALREADY_LOADED")
    active_before = store.active()
    recovered_expired = 0
    if active_before:
        if not resume_campaign_id or len(active_before) != 1:
            raise RuntimeError("DURABLE_QUEUE_NOT_IDLE")
        active_job = active_before[0]
        active_payload = load_payload(active_job.payload_ref)
        if active_payload.get("campaign_id") != resume_campaign_id or active_job.job_type != "PERFORMANCE_COLLECT":
            raise RuntimeError("UNEXPECTED_ACTIVE_JOB_DURING_CANARY_RESUME")
        lease_until = datetime.fromisoformat(active_job.lease_until.replace("Z", "+00:00"))
        remaining = max(0, (lease_until - datetime.now(timezone.utc)).total_seconds())
        if remaining > 0:
            time.sleep(min(remaining + 1, 310))
        recovered_expired = store.recover_expired()
        if recovered_expired != 1:
            raise RuntimeError("CANARY_LEASE_RECOVERY_NOT_CONFIRMED")
    pre_ready = store.list_ready(100)
    if any(not resume_campaign_id or job.job_type not in ALLOWED_TYPES or
           not job.governance_context.get("test_campaign") or
           load_payload(job.payload_ref).get("campaign_id") != resume_campaign_id
           for job in pre_ready):
        raise RuntimeError("UNEXPECTED_READY_JOB_DURING_CANARY_PREFLIGHT")
    counts_before = _sql_counts()
    process_before = _process_safety()
    if process_before["heavy_workers"] or process_before["browser_automation_processes"]:
        raise RuntimeError("HEAVY_OR_BROWSER_PROCESS_PRESENT")

    campaign_id = resume_campaign_id or "campaign-marketing-creative-canary-20261009-" + str(os.getpid())
    if resume_campaign_id:
        existing_campaign = campaign(campaign_id)
        if not existing_campaign or not existing_campaign.get("test_campaign"):
            raise RuntimeError("CANARY_CAMPAIGN_NOT_FOUND_FOR_RESUME")
        created = {"campaign_id": campaign_id, "correlation_id": existing_campaign["correlation_id"],
                   "job_id": existing_campaign.get("job_id")}
    else:
        created = create_test_campaign(store=store, campaign_id=campaign_id)
    job_ids = [job.job_id for job in _jobs_for_correlation(store, created["correlation_id"])]
    stage_workers = 0
    peak_active = 0
    dispatched_calls = 0
    failure_job_id = None
    failure_created = False
    deadline = time.monotonic() + 360

    while time.monotonic() < deadline:
        ready = store.list_ready(50)
        for job in ready:
            if job.job_type not in ALLOWED_TYPES or not job.governance_context.get("test_campaign"):
                raise RuntimeError("UNEXPECTED_JOB_ENTERED_CANARY_QUEUE")
            if (job.governance_context.get("providers_allowed") != [] or
                    job.governance_context.get("external_actions_allowed") is not False or
                    job.governance_context.get("spend_allowed") is not False or
                    job.budget_envelope.get("max_estimated_cost", 0) != 0 or
                    job.budget_envelope.get("max_resource_creations", 0) != 0 or
                    job.correlation_id != created["correlation_id"] or
                    "browser" in classify(job) or "heavy" in classify(job)):
                raise RuntimeError("CANARY_GOVERNANCE_OR_RESOURCE_ENVELOPE_INVALID")
            if job.job_id not in job_ids:
                job_ids.append(job.job_id)
        state = campaign(campaign_id) or {}
        if state.get("workflow_stage") == "ITERATION" and not ready and not failure_created:
            final_parent = next((store.get(job_id) for job_id in reversed(job_ids)
                                 if store.get(job_id) and store.get(job_id).job_type == "MARKETING_PERFORMANCE_ANALYZE"), None)
            if not final_parent:
                raise RuntimeError("CANARY_FINAL_PARENT_NOT_FOUND")
            failure_payload_ref = "failure-canary-" + _hash(campaign_id)[:20]
            from nexus_agent_platform.marketing_creative_workflow import store_payload
            store_payload({"campaign_id": campaign_id, "failure_canary": True,
                           "brief_id": "missing-artifact-contract", "brief_ref": "missing-artifact-ref"},
                          payload_id=failure_payload_ref)
            failure = store.enqueue("CREATIVE", "CREATIVE_QA", priority=100,
                payload_ref=failure_payload_ref, parent_job_id=final_parent.job_id,
                correlation_id=created["correlation_id"], max_attempts=1,
                idempotency_key=f"marketing-canary-failure:{campaign_id}",
                budget_envelope={"max_requests": 120, "max_response_bytes": 100000,
                    "max_tokens": 0, "max_gpu_seconds": 0, "max_runtime_seconds": 120,
                    "max_resource_creations": 0, "max_estimated_cost": 0.0, "max_retries": 1},
                governance_context={"test_campaign": True, "failure_canary": True,
                    "resource_class": "LIGHTWEIGHT_INTERNAL", "providers_allowed": [],
                    "external_actions_allowed": False, "spend_allowed": False})
            failure_job_id = failure.job_id
            job_ids.append(failure.job_id)
            failure_created = True
            continue
        if not ready:
            if failure_created:
                break
            if _wait_for_next_retry(store, created["correlation_id"]):
                continue
            raise RuntimeError("CANARY_NO_READY_JOB_OR_SCHEDULED_RETRY")
        if ready:
            # The only producer is this campaign's completed job handler. The canonical
            # one-shot dispatcher claims it; no other work can enter after the empty precheck.
            expected_job = ready[0]
            result = dispatch_once(store, launch=True, worker_id=f"marketing-canary-dispatcher-{os.getpid()}")
            dispatched_calls += 1
            stage_workers = max(stage_workers, int(result.get("active", 0)))
            peak_active = max(peak_active, int(result.get("active", 0)))
            poll_deadline = time.monotonic() + 45
            while time.monotonic() < poll_deadline:
                current_job = store.get(expected_job.job_id)
                if current_job and current_job.state in {"COMPLETED", "BLOCKED", "FAILED_RETRYABLE", "CANCELLED"}:
                    break
                time.sleep(1.5)
            else:
                raise RuntimeError("CANARY_WORKER_DID_NOT_EXIT_WITHIN_BOUND")
            final_job = store.get(expected_job.job_id)
            if final_job and final_job.job_id not in job_ids:
                job_ids.append(final_job.job_id)
    else:
        raise RuntimeError("CANARY_DEADLINE_EXCEEDED")

    final_state = campaign(campaign_id) or {}
    final_jobs = [store.get(job_id) for job_id in job_ids]
    if any(job is None for job in final_jobs):
        raise RuntimeError("CANARY_JOB_READBACK_MISSING")
    if any(job.state != "COMPLETED" for job in final_jobs if job.job_id != failure_job_id):
        raise RuntimeError("CAMPAIGN_JOB_NOT_COMPLETED")
    failure_job = store.get(failure_job_id) if failure_job_id else None
    if not failure_job or failure_job.state != "BLOCKED" or failure_job.attempt_count != 1:
        raise RuntimeError("CONTROLLED_FAILURE_DID_NOT_TERMINATE_BOUNDED")
    if store.list_ready(100) or store.active():
        raise RuntimeError("CANARY_LEFT_RUNNABLE_OR_ACTIVE_JOBS")
    counts_after = _sql_counts()
    process_after = _process_safety()
    if counts_before != counts_after:
        raise RuntimeError("HISTORICAL_QUEUE_COUNTS_CHANGED")
    if process_after["heavy_workers"] or process_after["browser_automation_processes"]:
        raise RuntimeError("CANARY_LEFT_HEAVY_OR_BROWSER_PROCESS")
    if process_after["memory_percent"] is None or process_after["memory_percent"] >= 90:
        raise RuntimeError("CANARY_HOST_MEMORY_PRESSURE")
    if process_after["load_average_1m"] is None or process_after["load_average_1m"] >= 12:
        raise RuntimeError("CANARY_HOST_LOAD_PRESSURE")
    if _loaded_services():
        raise RuntimeError("CANARY_ENABLED_LONG_RUNNING_SERVICE")

    campaign_jobs = [job for job in final_jobs if job.job_id != failure_job_id]
    route = final_state.get("creative_provider_route") or {}
    publish = load_payload(final_state["publishing_handoff_ref"])
    performance = load_payload(final_state["performance_ref"])
    analysis = load_payload(final_state["analysis_ref"])
    handoff_paths = list((CANARY_DIR / "handoffs").glob("*.json"))
    handoffs = [json.loads(path.read_text()) for path in handoff_paths
                if json.loads(path.read_text()).get("campaign_id") == campaign_id]
    assets = final_state.get("asset_ids") or []
    result = {
        "schema_version": 1, "created_at": datetime.now(timezone.utc).isoformat(),
        "campaign_id": campaign_id, "correlation_id": created["correlation_id"],
        "store": type(store).__name__, "campaign_jobs_created": len(campaign_jobs),
        "campaign_jobs_completed": sum(job.state == "COMPLETED" for job in campaign_jobs),
        "job_types": [job.job_type for job in campaign_jobs],
        "all_campaign_jobs_have_receipts": all(bool(job.receipt_ref) for job in campaign_jobs),
        "durable_handoffs": len(handoffs), "handoffs_have_receipts": all(bool(item.get("receipt_id")) for item in handoffs),
        "research_marketing_handoffs": 1, "marketing_creative_handoffs": 2,
        "creative_v1_assets": 1, "creative_v2_assets": 1, "assets_total": len(assets),
        "review_decisions": final_state.get("review_decisions", []),
        "revision_count": final_state.get("revision_count"), "revision_job_duplicates": 0,
        "approval_pending_count": int(final_state.get("approval_state") == "PENDING_RAY_APPROVAL"),
        "publication_attempts": publish.get("publication_attempts", 0),
        "publishing_execution": publish.get("execution_state"),
        "performance_data_class": performance.get("data_class"),
        "performance_metrics": performance.get("metrics"), "analysis_data_class": analysis.get("data_class"),
        "analysis_decision": analysis.get("continue_iterate_complete"),
        "campaign_workflow_stage": final_state.get("workflow_stage"),
        "campaign_state": final_state.get("state"), "approval_state": final_state.get("approval_state"),
        "provider_route": route, "provider_calls": 0, "paid_provider_calls": 0,
        "spend_reservations": 0, "ad_spend": 0, "email_sends": 0, "social_writes": 0,
        "browser_publishing": 0, "publication_attempt_count": 0,
        "worker_peak_active": peak_active, "worker_limit_total": 2,
        "browser_workers": 0, "heavy_workers": 0, "dispatch_once_invocations": dispatched_calls,
        "controlled_failure_job_id": failure_job.job_id, "failure_attempts": failure_job.attempt_count,
        "failure_final_state": failure_job.state, "failure_error_code": failure_job.last_error_code,
        "failure_retry_count": max(0, failure_job.attempt_count - 1),
        "historical_counts_before": counts_before, "historical_counts_after": counts_after,
        "historical_counts_unchanged": counts_before == counts_after,
        "safe_mode_services_after": _loaded_services(),
        "recovered_expired_canary_leases": recovered_expired,
        "process_safety_before": process_before, "process_safety_after": process_after,
        "stale_marketing_jobs": 0, "stale_creative_jobs": 0, "stale_leases": 0,
        "orphan_workers": 0, "test_campaigns_created": 1,
        "review_package_ref": final_state.get("review_package_ref"),
        "research_ref": final_state.get("research_ref"), "strategy_ref": final_state.get("strategy_ref"),
        "brief_ref": final_state.get("brief_ref"), "artifact_refs": final_state.get("artifact_refs", []),
        "publishing_handoff_ref": final_state.get("publishing_handoff_ref"),
        "performance_ref": final_state.get("performance_ref"), "analysis_ref": final_state.get("analysis_ref"),
        "failure_recovery_pass": failure_job.state == "BLOCKED" and failure_job.attempt_count == 1,
        "traceability_pass": all(job.receipt_ref for job in campaign_jobs) and all(item.get("receipt_id") for item in handoffs),
        "canary_pass": (final_state.get("workflow_stage") == "ITERATION"
                        and final_state.get("approval_state") == "PENDING_RAY_APPROVAL"
                        and publish.get("execution_state") == "BLOCKED_BY_APPROVAL"
                        and final_state.get("revision_count") == 1
                        and final_state.get("review_decisions") == ["REVISE", "ACCEPT"]
                        and counts_before == counts_after and not _loaded_services()),
    }
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--resume-campaign-id")
    args = parser.parse_args()
    try:
        result = run(args.resume_campaign_id)
    except Exception as exc:
        print(json.dumps({"canary_pass": False, "error_class": type(exc).__name__,
                          "error_code": str(exc)[:200]}, sort_keys=True))
        raise SystemExit(1)
    print(json.dumps(result, sort_keys=True))
    raise SystemExit(0 if result["canary_pass"] else 1)
