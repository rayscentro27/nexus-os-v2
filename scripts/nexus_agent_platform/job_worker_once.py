#!/usr/bin/env python3
"""One bounded job process; adapters reuse existing Research/feeder entry points."""
from __future__ import annotations
import argparse
import json
import subprocess
import sys
import os
import re
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = Path(__file__).resolve().parent
# Direct script execution prepends this package directory to sys.path. Remove
# it before importing stdlib `platform`, otherwise this package's platform.py
# shadows the standard library module.
sys.path = [entry for entry in sys.path if Path(entry or ".").resolve() != SCRIPT_DIR]
sys.path.insert(0, str(ROOT / "scripts"))
import platform
from nexus_agent_platform.durable_jobs import default_store, JobError, handler_route

JOB_BUDGET={"max_requests":120,"max_response_bytes":2_000_000,"max_tokens":12_000,"max_gpu_seconds":0,
            "max_runtime_seconds":900,"max_resource_creations":0,"max_estimated_cost":0.0,"max_retries":3}
ACTIVE_RESERVATIONS={}


def _lifecycle(job_id: str, stage: str, *, job=None, worker_id: str | None = None, **details):
    try:
        from nexus_agent_platform.worker_lifecycle import emit
        return emit(job_id, stage, attempt=getattr(job, "attempt_count", None),
                    worker_id=worker_id, **details)
    except Exception:
        return None


@contextmanager
def _worker_cleanup_scope(job_id: str, worker_id: str, reservation_id: str | None = None):
    """Enter the guard's cleanup capability only from this worker module."""
    from nexus_agent_platform.supabase_egress_guard import worker_cleanup_scope
    with worker_cleanup_scope(job_id, worker_id, reservation_id):
        yield

def _result_json(stdout):
    try: return json.loads(stdout)
    except (ValueError,TypeError): return {}


def _bounded_result_summary(result: dict, *, completed_at: str | None = None) -> dict:
    """Project a readable but size-bounded department result for status reads."""
    answer = result.get("answer") or result.get("summary") or result.get("report") or result.get("result_summary")
    if isinstance(answer, (dict, list)):
        answer = json.dumps(answer, ensure_ascii=False, default=str)
    return {
        "answer": str(answer or "Worker completed without a formatted result summary.")[:6000],
        "evidence": result.get("evidence") if isinstance(result.get("evidence"), (dict, list)) else None,
        "artifact_ref": result.get("artifact_ref") or result.get("department_receipt_path"),
        "department_receipt_id": result.get("department_receipt_id"),
        "completed_at": completed_at or datetime.now(timezone.utc).isoformat(),
    }


def _is_under_nexus_runtime_root(path: Path) -> bool:
    """Allow files reached through canonical state symlinks in a clean release."""
    try:
        resolved = Path(path).resolve()
    except (OSError, RuntimeError):
        return False
    roots = {ROOT.resolve()}
    try:
        from nexus_agent_platform.runtime.paths import (
            get_nexus_repo_root, nexus_data_path, nexus_research_state_root,
        )
        roots.add(get_nexus_repo_root().resolve())
        # Immutable releases may expose the canonical data directory through a
        # packaged data symlink. The worker may read those durable payloads,
        # while remaining unable to import application code from the checkout.
        roots.add(nexus_data_path().resolve())
        # In deployed releases, the shared runtime subtree itself can be a
        # symlink even when the top-level data directory is a real directory.
        roots.add(nexus_data_path("runtime").resolve())
        roots.add(nexus_research_state_root().resolve())
    except (ImportError, OSError, RuntimeError):
        pass
    return any(resolved.is_relative_to(root) for root in roots)


def hydrate_research_assignment_scope(work_item: dict, governance_context: dict) -> tuple[dict, str | None]:
    """Carry the durable semantic contract into the worker without guessing."""
    hydrated = dict(work_item)
    context = governance_context if isinstance(governance_context, dict) else {}
    durable_intent = str(context.get("requested_intent") or "").strip().upper()
    queue_intent = str(hydrated.get("requested_intent") or "").strip().upper()
    if durable_intent and queue_intent and durable_intent != queue_intent:
        return hydrated, "RESEARCH_INTENT_CONTRACT_MISMATCH"
    for key in ("requested_intent", "routed_intent", "execution_path", "objective_type", "research_scope",
                "original_objective", "original_source_url", "original_source_type", "current_research_context"):
        if not hydrated.get(key) and context.get(key):
            hydrated[key] = context[key]
    return hydrated, None

def _release_reservation(governor, reservation, job_id):
    """Release job envelope reservations when a handler exits before reconcile."""
    try:
        governor.release(reservation["reservation_id"])
    finally:
        ACTIVE_RESERVATIONS.pop(job_id, None)


def _settle_capacity_wait(job, worker_id: str, store, reservation: dict,
                         governor, reason: str) -> None:
    """Keep the objective alive while returning this job to retryable wait."""
    job_id = str(job.job_id)
    try:
        from nexus_agent_platform.research_work_queue import default_queue
        default_queue().settle(job.payload_ref, "WAITING", result={
            "objective_id": (job.governance_context or {}).get("objective_id"),
            "reason": reason, "objective_terminated": False}, blocker_type=reason)
    except Exception as exc:
        _lifecycle(job_id, "CAPACITY_WORK_ITEM_SETTLE_FAILED", job=job,
                   worker_id=worker_id, exception_type=type(exc).__name__)
        raise
    with _worker_cleanup_scope(job_id, worker_id, reservation.get("reservation_id")):
        store.transition(job_id, "FAILED_RETRYABLE", worker_id=worker_id,
            error_code=reason,
            error_summary="Research objective remains queued until an execution slot is available.")
        _release_reservation(governor, reservation, job_id)
    _lifecycle(job_id, "JOB_TERMINAL_TRANSITION", job=job, worker_id=worker_id,
               state="FAILED_RETRYABLE", reason=reason)

def _egress_delta(current: dict, previous: dict) -> dict:
    """Return only this worker attempt's egress; snapshots are cumulative per job."""
    return {key:max(0,int(current.get(key,0) or 0)-int(previous.get(key,0) or 0))
            for key in ("request_count","response_bytes")}

def _footprint(job,store,started_wall,started_cpu,final_state,failure=None,receipt_hash=None):
    try:
        from nexus_agent_platform.supabase_egress_guard import job_egress_snapshot
        egress=job_egress_snapshot(job.job_id)
    except Exception: egress={}
    try:
        import resource
        peak_memory=int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    except Exception: peak_memory=None
    try:
        from nexus_agent_platform.resource_spend_governor import default_store as governor_store
        governor=governor_store()
        workflow_context={}
        try:
            from nexus_agent_platform.marketing_creative_workflow import load_payload, campaign
            request=load_payload(job.payload_ref) if job.job_type in {
                "MARKETING_STRATEGY","MARKETING_RESEARCH_REQUEST","MARKETING_CAMPAIGN_BUILD",
                "CREATIVE_BRIEF_BUILD","CREATIVE_ASSET_GENERATE","CREATIVE_ASSET_REVISE",
                "CREATIVE_QA","MARKETING_ASSET_REVIEW","MARKETING_PUBLISH_PREP",
                "CONTROLLED_EMAIL_SEND","CONTROLLED_SOCIAL_POST","LANDING_PAGE_BUILD",
                "LANDING_PAGE_VERIFY","PERFORMANCE_COLLECT","MARKETING_PERFORMANCE_ANALYZE",
                "RESEARCH_MARKETING_TEST_HANDOFF",
                "FINANCE_CAMPAIGN_REVIEW"} else {}
            campaign_id=request.get("campaign_id") or request.get("existing_campaign_id")
            state=campaign(campaign_id) if campaign_id else None
            if state:
                workflow_context={"campaign_id":campaign_id,"project_id":state.get("project_id"),
                    "artifact_refs":state.get("artifact_refs",[]),"revision_count":state.get("revision_count",0),
                    "approval_state":state.get("approval_state"),"next_job_ids":state.get("external_action_job_ids",[]),
                    "handoff_ids":state.get("handoff_ids",[])}
        except Exception:
            workflow_context={}
        return governor.record_footprint({
            "project_id":workflow_context.get("project_id") or "NEXUS","campaign_id":workflow_context.get("campaign_id"),"job_id":job.job_id,"correlation_id":job.correlation_id,"department":job.department,"job_type":job.job_type,
            "host":platform.node(),"environment":"macOS" if platform.system()=="Darwin" else platform.system(),"process_id":os.getpid(),"parent_process_id":os.getppid(),
            "worker_type":"DURABLE_JOB_WORKER","start_time":started_wall,"end_time":time.time(),"duration_seconds":round(time.time()-started_wall,3),
            "providers_used":[x for x in os.environ.get("NEXUS_PROVIDERS_USED","").split(",") if x],"services_used":[x for x in os.environ.get("NEXUS_SERVICES_USED","").split(",") if x],
            "models_used":[x for x in os.environ.get("NEXUS_MODELS_USED","").split(",") if x],"request_count":egress.get("request_count",0),
            "response_bytes":egress.get("response_bytes",0),"tokens":int(os.environ.get("NEXUS_JOB_TOKENS_USED","0") or 0),
            "gpu_seconds":float(os.environ.get("NEXUS_JOB_GPU_SECONDS","0") or 0),"cpu_time_seconds":round(time.process_time()-started_cpu,3),
            "peak_memory_bytes":peak_memory,"estimated_cost":float(os.environ.get("NEXUS_JOB_ESTIMATED_COST","0") or 0),"actual_cost":None,
            "files_created":[],"artifact_refs":workflow_context.get("artifact_refs",[]),"handoff_ids":workflow_context.get("handoff_ids",[]),"next_job_ids":workflow_context.get("next_job_ids",[]),"revision_count":workflow_context.get("revision_count",0),"approval_state":workflow_context.get("approval_state"),"email_actions":0,"social_actions":0,"browser_actions":0,
            "failure_codes":[str(failure)[:120]] if failure else [],"retry_count":job.attempt_count,"recovery_action":None,"final_state":final_state,
            "receipt_hash":receipt_hash or getattr(store.get(job.job_id),"result_hash",None)})
    except Exception as exc:
        print(json.dumps({"footprint_persist_error":type(exc).__name__}),file=sys.stderr)
        return None


def _execute_queued_advisor(payload, job):
    from nexus_agent_platform.research_room.production_controller import execute_queued_advisor
    return execute_queued_advisor(payload, worker_job_id=job.job_id)


def _persist_advisor_worker_failure(payload, job, error):
    from nexus_agent_platform.research_room.production_controller import record_queued_advisor_worker_failure
    return record_queued_advisor_worker_failure(payload, worker_job_id=job.job_id, error=error)


def execute_research_room_advisor(job, payload):
    """Run the dedicated durable Research Room Advisor handler."""
    try:
        if (job.department.upper() != "RESEARCH"
                or (job.governance_context or {}).get("source") != "RESEARCH_ROOM_ADVISOR"):
            raise JobError("RESEARCH_ROOM_ADVISOR_GOVERNANCE_CONTEXT_INVALID")
        if not isinstance(payload, dict) or not payload:
            raise JobError("RESEARCH_ROOM_ADVISOR_PAYLOAD_REQUIRED")
        return _execute_queued_advisor(payload, job)
    except Exception as exc:
        if isinstance(payload, dict) and payload.get("attempt_id") and payload.get("identity"):
            _persist_advisor_worker_failure(payload, job, exc)
        raise


def execute_routed_job(job, route, payload):
    """Dispatch one Advisor job without entering a generic Research executor."""
    if route != "RESEARCH_ROOM_ADVISOR" or job.job_type != "RESEARCH_ROOM_ADVISOR":
        raise JobError("RESEARCH_ROOM_ADVISOR_ROUTE_MISMATCH")
    return execute_research_room_advisor(job, payload)


def open_mcp_research_intake_case(assigned_work: dict) -> dict:
    """Open/join the Case Engine record before an MCP mission continues."""
    from nexus_agent_platform.research_assignment_executor import execute_assignment
    opened = execute_assignment(assigned_work)
    status = str(opened.get("status") or "").upper()
    if status == "WAITING_FOR_CAPACITY":
        return {"status": status, "reason": opened.get("reason") or "MAX_ACTIVE_DEEP_CASES_REACHED",
            "retryable": True, "objective_terminated": False, "case_created": False}
    case_id = str(opened.get("case_id") or (opened.get("result") or {}).get("case_id") or "")
    if status != "CONTINUATION_REQUIRED" or not case_id:
        return {"status": "BLOCKED", "reason": opened.get("reason") or "RESEARCH_CASE_NOT_VERIFIED",
            "case_created": False}
    return {"status": "CASE_OPENED", "case_id": case_id,
        "execution_path": opened.get("execution_path") or "RESEARCH_INTAKE",
        "requested_intent": opened.get("requested_intent"),
        "routed_intent": opened.get("routed_intent"), "case_created": True}

def run(job_id: str, worker_id: str, store) -> dict:
    from nexus_agent_platform.durable_objective_control import (
        ACTIVE_CAMPAIGN_PATH, authorize_job_start, load_active_campaign,
    )
    # Production workers must recover campaign identity before side effects.
    # Local SQLite jobs are isolated test/development fixtures and intentionally
    # do not inherit the host's active owner campaign.
    from nexus_agent_platform.durable_jobs import SupabaseJobStore
    campaign_state = (load_active_campaign()
                      if isinstance(store, SupabaseJobStore) and ACTIVE_CAMPAIGN_PATH.exists()
                      else None)
    job = store.get(job_id)
    if not job or job.state != "CLAIMED" or job.claimed_by != worker_id:
        raise JobError("CLAIM_NOT_OWNED")
    _lifecycle(job_id,"JOB_LOADED",job=job,worker_id=worker_id,state=job.state)
    _lifecycle(job_id,"CLAIM_VERIFIED",job=job,worker_id=worker_id,attempt_count=job.attempt_count)
    original_transition = store.transition
    def transition_with_lifecycle(*args, **kwargs):
        transition_job = str(args[0] if args else kwargs.get("job_id") or job_id)
        transition_state = str(args[1] if len(args) > 1 else kwargs.get("state") or "")
        transitioned = original_transition(*args, **kwargs)
        if transition_job == job_id and transition_state in {"WAITING", "FAILED_RETRYABLE", "BLOCKED", "COMPLETED", "CANCELLED"}:
            _lifecycle(job_id,"JOB_TERMINAL_TRANSITION",job=job,worker_id=worker_id,
                       state=getattr(transitioned,"state",transition_state))
        return transitioned
    store.transition = transition_with_lifecycle
    # Central host/research readiness gate: keep the same durable job and its
    # objective lineage, but do not begin handler/provider work while blocked.
    from nexus_agent_platform.stability_supervisor import (
        SupervisorStateStore, get_host_execution_gate,
    )
    gate = get_host_execution_gate()
    heavy_job = job.department.upper() == "RESEARCH" or any(
        marker in job.job_type.upper() for marker in
        ("BROWSER", "NOTEBOOKLM", "LARGE_MODEL", "VIDEO", "MEDIA", "GPU", "CREDIT_REPORT_ANALYSIS")
    )
    if heavy_job and (not gate["heavy_work_allowed"] or
                      (job.department.upper() == "RESEARCH" and not gate["research_execution_allowed"])):
        supervisor_state = SupervisorStateStore()
        active_incidents = supervisor_state.active_global_host_incidents()
        context = job.governance_context or {}
        objective_id = context.get("owner_objective_id") or context.get("objective_id")
        if objective_id and active_incidents:
            supervisor_state.add_dependent_objective(
                active_incidents[0]["event_id"], objective_id=str(objective_id),
                project_id=context.get("project_id") or context.get("work_id"),
                job_id=job.job_id, case_id=context.get("case_id") or context.get("research_case_id"),
                department=job.department, reason="HOST_EXECUTION_GATE_BLOCKED",
            )
        store.transition(job_id, "BLOCKED", worker_id=worker_id,
                         error_code="HOST_EXECUTION_GATE_BLOCKED",
                         error_summary=",".join(gate["reason_codes"])[:300])
        return {"status": "BLOCKED", "reason": "HOST_EXECUTION_GATE_BLOCKED",
                "job_id": job.job_id, "objective_id": objective_id,
                "host_gate": gate}
    # Resolve the job's declared execution class before invoking its handler.
    # A workflow may have deterministic steps and a separately classified
    # reasoning call; this job-level declaration records its primary executor.
    from nexus_agent_platform.workflow_execution import job_execution_record
    execution_payload = {}
    if job.payload_ref:
        try:
            payload_path = (ROOT / job.payload_ref).resolve()
            if _is_under_nexus_runtime_root(payload_path) and payload_path.is_file():
                candidate = json.loads(payload_path.read_text(encoding="utf-8"))
                execution_payload = candidate if isinstance(candidate, dict) else {}
        except (OSError, ValueError):
            execution_payload = {}
    execution_record = job_execution_record(job.job_type, job.department, execution_payload)
    _lifecycle(job_id,"EXECUTION_CONTRACT_READY",job=job,worker_id=worker_id,
               execution_class=execution_record.get("execution_class"),
               model_call_required=execution_record.get("model_call_required"))
    if campaign_state and campaign_state.get("CAMPAIGN_STATUS") in {"ACTIVE", "IN_PROGRESS"}:
        try:
            authorize_job_start(job, store=store)
        except Exception as exc:
            store.transition(job_id, "BLOCKED", worker_id=worker_id,
                             error_code="ACTIVE_CAMPAIGN_IDENTITY_MISMATCH",
                             error_summary=str(exc)[:300])
            return {"status": "BLOCKED", "reason": "ACTIVE_CAMPAIGN_IDENTITY_MISMATCH",
                    "campaign_id": campaign_state.get("CAMPAIGN_ID"), "job_id": job_id}
    store.transition(job_id, "RUNNING", worker_id=worker_id)
    _lifecycle(job_id,"RUNNING_TRANSITION_COMPLETE",job=job,worker_id=worker_id,state="RUNNING")
    started_wall=time.time(); started_cpu=time.process_time()
    budget=dict(JOB_BUDGET)
    if isinstance(job.budget_envelope,dict): budget.update({k:v for k,v in job.budget_envelope.items() if k in budget})
    os.environ["NEXUS_JOB_BUDGET"]=json.dumps(budget,separators=(",",":"))
    # Establish job identity before the governor call so authorization traffic
    # and deny-path footprints are attributed to this job as well.
    os.environ["NEXUS_DURABLE_JOB_ID"] = job.job_id
    os.environ["NEXUS_JOB_CORRELATION_ID"] = job.correlation_id
    os.environ["NEXUS_CORRELATION_ID"] = job.correlation_id
    os.environ["NEXUS_DEPARTMENT"] = job.department
    os.environ["NEXUS_JOB_TYPE"] = job.job_type
    os.environ["NEXUS_EXECUTION_CLASS"] = execution_record["execution_class"]
    os.environ["NEXUS_MODEL_CALL_REQUIRED"] = "YES" if execution_record["model_call_required"] else "NO"
    execution_context = {**(job.governance_context or {}), "execution_contract": execution_record}
    store.set_governance_context(job_id, execution_context)
    _lifecycle(job_id,"JOB_ENVIRONMENT_READY",job=job,worker_id=worker_id)
    governance_context=job.governance_context or {}
    if governance_context.get("research_case_persistence") == "LOCAL_UNTIL_COMPACT_HANDOFF":
        os.environ["NEXUS_RESEARCH_CASE_LOCAL_ONLY"]="1"
    repair_attempt_total=int(governance_context.get("repair_attempt_total", 0) or 0)
    os.environ["NEXUS_JOB_ATTEMPT_COUNT"] = str(repair_attempt_total + job.attempt_count)
    execution_id = uuid.uuid4().hex
    os.environ["NEXUS_DURABLE_EXECUTION_ID"] = execution_id
    os.environ["NEXUS_JOB_PAYLOAD_REF"] = job.payload_ref or ""
    os.environ["NEXUS_OWNER_OBJECTIVE_ID"] = str((job.governance_context or {}).get("owner_objective_id") or "")
    from nexus_agent_platform.supabase_egress_guard import job_egress_snapshot
    prior_egress=job_egress_snapshot(job.job_id)
    _lifecycle(job_id,"EGRESS_SNAPSHOT_READY",job=job,worker_id=worker_id,
               request_count=prior_egress.get("attempt_request_count",0),
               response_bytes=prior_egress.get("attempt_response_bytes",0))
    # Supabase egress limits apply to this leased execution attempt. Aggregate
    # totals remain persisted for receipts and provider reconciliation, while
    # a repaired job can retry after an earlier bounded attempt consumed its
    # allowance.
    remaining_requests=max(0,int(budget["max_requests"])-int(prior_egress.get("attempt_request_count",0)))
    remaining_bytes=max(0,int(budget["max_response_bytes"])-int(prior_egress.get("attempt_response_bytes",0)))
    from nexus_agent_platform.resource_spend_governor import default_store as default_governor_store, GovernanceDenied
    governor=default_governor_store()
    try:
        if remaining_requests < 1 or remaining_bytes < 1:
            raise GovernanceDenied("HARD_STOP","JOB_BUDGET_EXHAUSTED")
        # Reserve the measured control-plane portion of this job envelope, not
        # the entire remaining envelope. Provider adapters reserve their own
        # usage separately; reserving every remaining request here starves a
        # governed provider call before it can execute. The local egress guard
        # still enforces the full per-job ceiling, and final reconciliation
        # records actual Supabase requests/bytes.
        envelope_requests=min(remaining_requests,6)
        envelope_bytes=min(remaining_bytes,8192)
        from nexus_agent_platform.research_assignment_intent import governor_policy_job_type
        policy_job_type = governor_policy_job_type(
            job.job_type,
            nova_research_assignment=(job.department == "RESEARCH" and
                (job.governance_context or {}).get("source") == "NOVA_MCP_RESEARCH_ASSIGNMENT"),
        )
        _lifecycle(job_id,"GOVERNANCE_RESERVATION_START",job=job,worker_id=worker_id,resource="SUPABASE")
        reservation=governor.reserve("SUPABASE","durable_worker",policy_job_type,job.job_id,
            {"requests":envelope_requests,"bytes":envelope_bytes,"cost":0},
            purpose=f"durable-job-envelope:run-{execution_id}")
        _lifecycle(job_id,"GOVERNANCE_RESERVATION_COMPLETE",job=job,worker_id=worker_id,result="GRANTED")
    except GovernanceDenied as exc:
        # A transient quota/concurrency throttle is a defer condition, not a
        # terminal workflow blocker. Persist bounded backoff so the durable
        # dispatcher can retry after capacity returns.
        state = "FAILED_RETRYABLE" if exc.state == "THROTTLED" else "BLOCKED"
        store.transition(job_id,state,worker_id=worker_id,error_code=exc.code,error_summary=exc.state)
        _footprint(job,store,started_wall,started_cpu,state,exc.code)
        return {"status":state,"job_type":job.job_type,"reason":exc.code,"governor_state":exc.state}
    ACTIVE_RESERVATIONS[job_id]=(governor,reservation["reservation_id"],prior_egress)
    route = handler_route(job.job_type)
    _lifecycle(job_id,"ROUTE_SELECTED",job=job,worker_id=worker_id,route=route,job_type=job.job_type)
    assigned_work = None
    if route == "INTERNAL_CANARY":
        from nexus_agent_platform.internal_canary import execute_internal_canary
        result = execute_internal_canary(job)
    elif route == "NOVA_CONTROL_ACTION":
        payload_path = (ROOT / str(job.payload_ref or "")).resolve()
        if not _is_under_nexus_runtime_root(payload_path) or not payload_path.is_file():
            raise JobError("NOVA_CONTROL_ACTION_PAYLOAD_INVALID")
        control_payload = json.loads(payload_path.read_text(encoding="utf-8"))
        task_text = str(control_payload.get("task") or "").strip()
        if not task_text or control_payload.get("spend_allowed") or control_payload.get("external_actions_allowed"):
            raise JobError("NOVA_CONTROL_ACTION_SCOPE_INVALID")
        if job.job_type == "NOVA_CREATIVE_ASSET":
            from nexus_agent_platform.creative import studio
            asset_result = studio.create_internal_logo_asset("Nexus Test", task_text, asset_id=job.job_id)
            asset = asset_result["asset"]
            result = {"status": "COMPLETED", "department": "CREATIVE", "asset_id": asset["asset_id"],
                "creative_brief_id": asset["creative_brief_id"], "asset_type": asset["asset_type"],
                "artifact_path": asset_result["artifact_path"], "creative_receipt_id": asset_result["receipt"]["receipt_id"],
                "result_summary": {"name": asset.get("content", {}).get("name"), "format": "SVG",
                    "artifact_path": asset_result["artifact_path"]},
                "external_action_performed": False, "approval_state": asset.get("approval_state")}
        elif job.job_type == "NOVA_BOUNDED_CODING_TASK":
            from nexus_agent_platform.coding_worker_supervisor import CodingTask, OpenCodeExecuteAdapter
            relative_workspace = f"tmp/nova_coding_jobs/{job.job_id}/"
            # Clean runtime releases are intentionally not Git checkouts. Use
            # the canonical source checkout for lineage when available; the
            # adapter will fall back to a disposable initialized workspace
            # when the release itself cannot host a Git worktree.
            git_root = Path(os.environ.get("NEXUS_REPO_ROOT", str(ROOT))).resolve()
            try:
                checkpoint = subprocess.run(["git", "rev-parse", "HEAD"], cwd=git_root,
                    capture_output=True, text=True, timeout=10, check=True).stdout.strip()
            except (OSError, subprocess.SubprocessError):
                release_hash = ROOT / "RELEASE_SOURCE_HASH"
                checkpoint = release_hash.read_text(encoding="utf-8").strip() if release_hash.is_file() else "clean-release"
            task = CodingTask(task_id=job.job_id, objective_id=job.correlation_id,
                prompt=(task_text + " Create a Python file under the allowed temporary workspace and run it once. "
                        "Do not modify any other files."), allowed_paths=(relative_workspace,),
                protected_paths=("scripts/", "services/", "configs/", "data/", "src/"),
                acceptance=("create requested Python file", "execute Python file once"),
                checkpoint_sha=checkpoint, job_id=job.job_id, worker_role="CODING_AND_SYSTEM_REPAIR_ONLY")
            previous_model = os.environ.get("NEXUS_OPENCODE_MODEL")
            os.environ["NEXUS_OPENCODE_MODEL"] = "opencode/mimo-v2.6-flash-free"
            try:
                execution = OpenCodeExecuteAdapter().execute(task, timeout=120)
            finally:
                if previous_model is None:
                    os.environ.pop("NEXUS_OPENCODE_MODEL", None)
                else:
                    os.environ["NEXUS_OPENCODE_MODEL"] = previous_model
            result = {"status": "COMPLETED" if execution.get("status") == "PASS" and execution.get("execution", {}).get("returncode") == 0 else "BLOCKED",
                "department": "OPENCODE", "worker": execution.get("worker_id"),
                "execution": execution, "result_summary": execution.get("execution", {}).get("stdout"),
                "external_action_performed": False}
            if result["status"] != "COMPLETED":
                result["reason"] = execution.get("failure_class") or "OPENCODE_TASK_FAILED"
                python_run = execution.get("execution") or {}
                result["error_summary"] = json.dumps({
                    "failure_class": execution.get("failure_class"),
                    "runner_returncode": execution.get("returncode"),
                    "runner_stdout": str(execution.get("stdout") or "")[-700:],
                    "runner_stderr": str(execution.get("stderr") or "")[-700:],
                    "python_execution": {key: python_run.get(key) for key in
                        ("returncode", "stdout", "stderr", "error", "file") if python_run.get(key) is not None},
                    "files_changed": execution.get("files_changed", []),
                }, default=str)[:1400]
        else:
            raise JobError("NOVA_CONTROL_ACTION_TYPE_INVALID")
    elif route == "NEEDLE_RESEARCH":
        from nexus_agent_platform.needle_research_workflow import handle_job
        result = handle_job(job, store)
    elif route == "MARKETING_CREATIVE":
        from nexus_agent_platform.marketing_creative_workflow import handle_job
        result = handle_job(job, store)
    elif route == "COMPANY_CERTIFICATION":
        from nexus_agent_platform.company_certification_workflow import handle_job
        result = handle_job(job, store)
    elif route == "REAL_WORLD_V2":
        from nexus_agent_platform.real_world_v2_workflow import handle_job
        result = handle_job(job, store)
    elif route == "V5_OWNER_RESEARCH":
        from nexus_agent_platform.v5_owner_workflow import handle_job
        result = handle_job(job)
    elif route == "NOVA_COMMUNICATION":
        if not job.payload_ref:
            store.transition(job_id,"BLOCKED",worker_id=worker_id,error_code="NOVA_COMMUNICATION_PAYLOAD_REQUIRED")
            _release_reservation(governor,reservation,job_id)
            return {"status":"BLOCKED","reason":"NOVA_COMMUNICATION_PAYLOAD_REQUIRED"}
        payload_path=(ROOT/job.payload_ref).resolve()
        if not _is_under_nexus_runtime_root(payload_path) or not payload_path.is_file():
            store.transition(job_id,"BLOCKED",worker_id=worker_id,error_code="NOVA_COMMUNICATION_PAYLOAD_INVALID")
            _release_reservation(governor,reservation,job_id)
            return {"status":"BLOCKED","reason":"NOVA_COMMUNICATION_PAYLOAD_INVALID"}
        payload=json.loads(payload_path.read_text(encoding="utf-8"))
        if job.job_type == "NOVA_RESEARCH_RESULT_NOTICE":
            event=payload.get("event")
            completed_job_id=str(payload.get("completed_research_job_id") or "")
            completed_job=store.get(completed_job_id) if completed_job_id else None
            if (not isinstance(event,dict) or event.get("event_type")!="SIGNIFICANT_RESEARCH"
                    or not event.get("department_receipt_id") or not event.get("source")
                    or not completed_job or completed_job.department!="RESEARCH"
                    or completed_job.state!="COMPLETED" or not completed_job.receipt_ref
                    or payload.get("completed_research_receipt_id")!=completed_job.receipt_ref):
                store.transition(job_id,"BLOCKED",worker_id=worker_id,error_code="NOVA_RESEARCH_NOTICE_EVIDENCE_INVALID")
                _release_reservation(governor,reservation,job_id)
                return {"status":"BLOCKED","reason":"NOVA_RESEARCH_NOTICE_EVIDENCE_INVALID"}
            from nova.proactive_communications import process_once
            communication=process_once(events=[event])
            sent=any(row.get("status")=="SENT" for row in communication.get("results",[]))
            result={"status":"COMPLETED" if sent else "BLOCKED","communication":communication,
                    "event_type":"SIGNIFICANT_RESEARCH","research_job_id":completed_job_id,
                    "research_receipt_id":completed_job.receipt_ref,
                    "evidence_class":"NOVA_DURABLE_RESEARCH_COMPLETION_NOTICE"}
        elif job.job_type == "NOVA_SYSTEMS_RESULT_NOTICE":
            event=payload.get("event")
            completed_job_id=str(payload.get("completed_systems_job_id") or "")
            completed_job=store.get(completed_job_id) if completed_job_id else None
            if (not isinstance(event,dict) or event.get("event_type")!="SYSTEMS_RESULT"
                    or not event.get("department_receipt_id") or not event.get("source")
                    or not completed_job or completed_job.department!="SYSTEMS"
                    or completed_job.state!="COMPLETED" or not completed_job.receipt_ref
                    or payload.get("completed_systems_receipt_id")!=completed_job.receipt_ref):
                store.transition(job_id,"BLOCKED",worker_id=worker_id,error_code="NOVA_SYSTEMS_NOTICE_EVIDENCE_INVALID")
                _release_reservation(governor,reservation,job_id)
                return {"status":"BLOCKED","reason":"NOVA_SYSTEMS_NOTICE_EVIDENCE_INVALID"}
            from nova.proactive_communications import process_once
            communication=process_once(events=[event])
            sent=any(row.get("status")=="SENT" for row in communication.get("results",[]))
            result={"status":"COMPLETED" if sent else "BLOCKED","communication":communication,
                    "event_type":"SYSTEMS_RESULT","systems_job_id":completed_job_id,
                    "systems_receipt_id":completed_job.receipt_ref,
                    "evidence_class":"NOVA_DURABLE_SYSTEMS_COMPLETION_NOTICE"}
        elif job.job_type == "NOVA_ALPHA_RESULT_NOTICE":
            event=payload.get("event")
            completed_job_id=str(payload.get("completed_alpha_job_id") or "")
            completed_job=store.get(completed_job_id) if completed_job_id else None
            if (not isinstance(event,dict) or event.get("event_type")!="ALPHA_RESULT"
                    or not event.get("department_receipt_id") or not event.get("source")
                    or not completed_job or completed_job.department!="ALPHA"
                    or completed_job.state!="COMPLETED" or not completed_job.receipt_ref
                    or payload.get("completed_alpha_receipt_id")!=completed_job.receipt_ref):
                store.transition(job_id,"BLOCKED",worker_id=worker_id,error_code="NOVA_ALPHA_NOTICE_EVIDENCE_INVALID")
                _release_reservation(governor,reservation,job_id)
                return {"status":"BLOCKED","reason":"NOVA_ALPHA_NOTICE_EVIDENCE_INVALID"}
            from nova.proactive_communications import process_once
            communication=process_once(events=[event])
            sent=any(row.get("status")=="SENT" for row in communication.get("results",[]))
            result={"status":"COMPLETED" if sent else "BLOCKED","communication":communication,
                    "event_type":"ALPHA_RESULT","alpha_job_id":completed_job_id,
                    "alpha_receipt_id":completed_job.receipt_ref,
                    "evidence_class":"NOVA_DURABLE_ALPHA_COMPLETION_NOTICE"}
        elif job.job_type == "NOVA_ALPHA_ASSIGNMENT_NOTICE":
            event=payload.get("event")
            alpha_job_id=str(payload.get("alpha_job_id") or "")
            alpha_job=store.get(alpha_job_id) if alpha_job_id else None
            if (not isinstance(event,dict) or event.get("event_type")!="ALPHA_ASSIGNED"
                    or event.get("alpha_job_id")!=alpha_job_id
                    or not alpha_job or alpha_job.department!="ALPHA"
                    or alpha_job.job_type!="NEXUS_DEPARTMENT_QUERY"
                    or alpha_job.state not in {"READY","CLAIMED","RUNNING","COMPLETED"}):
                store.transition(job_id,"BLOCKED",worker_id=worker_id,error_code="NOVA_ALPHA_ASSIGNMENT_NOTICE_INVALID")
                _release_reservation(governor,reservation,job_id)
                return {"status":"BLOCKED","reason":"NOVA_ALPHA_ASSIGNMENT_NOTICE_INVALID"}
            from nova.proactive_communications import process_once
            communication=process_once(events=[event])
            sent=any(row.get("status")=="SENT" for row in communication.get("results",[]))
            result={"status":"COMPLETED" if sent else "BLOCKED","communication":communication,
                    "event_type":"ALPHA_ASSIGNED","alpha_job_id":alpha_job_id,
                    "evidence_class":"NOVA_DURABLE_ALPHA_ASSIGNMENT_NOTICE"}
        else:
            if payload.get("event_type")!="RESOURCE_ALARM" or not payload.get("event_id"):
                store.transition(job_id,"BLOCKED",worker_id=worker_id,error_code="NOVA_COMMUNICATION_CONTRACT_INVALID")
                _release_reservation(governor,reservation,job_id)
                return {"status":"BLOCKED","reason":"NOVA_COMMUNICATION_CONTRACT_INVALID"}
            from nova.proactive_communications import retry_retained_resource_alert
            delivered=retry_retained_resource_alert(str(payload["event_id"]))
            if delivered.get("status")!="SENT":
                result={"status":"BLOCKED","delivery":delivered,"evidence_class":"NOVA_RETAINED_EVENT_RETRY"}
            else:
                result={"status":"COMPLETED","delivery":delivered,"evidence_class":"NOVA_RETAINED_EVENT_RETRY"}
    elif route == "NOVA_V6_COMMUNICATION":
        if not job.payload_ref:
            raise JobError("V6_NOVA_COMMUNICATION_PAYLOAD_REQUIRED")
        payload_path=(ROOT/job.payload_ref).resolve()
        if not _is_under_nexus_runtime_root(payload_path) or not payload_path.is_file():
            raise JobError("V6_NOVA_COMMUNICATION_PAYLOAD_INVALID")
        payload=json.loads(payload_path.read_text(encoding="utf-8"))
        state=load_active_campaign()
        event=payload.get("event") if isinstance(payload,dict) else None
        if (not isinstance(event,dict)
                or event.get("event_type") not in {"V6_STARTED","RESEARCH_STARTED","RESEARCH_COMPLETE","TOP_3_BUSINESSES_SELECTED",
                    "BUSINESS_PLAN_1_COMPLETE","BUSINESS_PLAN_2_COMPLETE","BUSINESS_PLAN_3_COMPLETE",
                    "CAMPAIGN_1_COMPLETE","CAMPAIGN_2_COMPLETE","CAMPAIGN_3_COMPLETE","VIDEO_COMPLETE",
                    "FOREX_RESEARCH_COMPLETE","STRATEGY_1_BACKTEST_COMPLETE","STRATEGY_2_BACKTEST_COMPLETE",
                    "PAPER_TRADING_STARTED","NEEDLE_INSTALLED","V6_COMPLETE","RAY_ACTION_REQUIRED"}
                or event.get("campaign_id")!=state.get("CAMPAIGN_ID")
                or payload.get("owner_objective_id")!=state.get("OWNER_OBJECTIVE_ID")):
            raise JobError("V6_NOVA_EVENT_CAMPAIGN_CONTRACT_INVALID")
        from nova.proactive_communications import process_once
        communication=process_once(events=[event])
        sent=any(row.get("status")=="SENT" for row in communication.get("results",[]))
        result={"status":"COMPLETED" if sent else "BLOCKED","communication":communication,
                "event_type":event.get("event_type"),"campaign_id":state.get("CAMPAIGN_ID"),
                "evidence_class":"NOVA_V6_REAL_OWNER_COMMUNICATION"}
    elif route == "V5_INTEGRATION_CHECK":
        artifact_ref=f"reports/certification/v5/jobs/results/{job.job_id}.json"
        artifact_path=ROOT/artifact_ref
        artifact_path.parent.mkdir(parents=True,exist_ok=True)
        if job.job_type=="V5_REMOTE_STACK_HEALTH_CHECK":
            from ops.check_remote_stack_health import collect_report
            report=collect_report()
            result={"status":"COMPLETED","check":"READ_ONLY_REMOTE_STACK_HEALTH",
                "artifact_ref":artifact_ref,"report":report,"evidence_class":"LIVE_SYSTEMS_INTEGRATION_CHECK"}
        elif job.job_type=="V5_OPENCODE_MODEL_BENCHMARK":
            from nexus_agent_platform.coding_worker_supervisor import (
                CodingTask, OpenCodeExecuteAdapter, select_worker, worker_discovery,
            )
            payload_path=(ROOT/job.payload_ref).resolve() if job.payload_ref else None
            if not payload_path or not _is_under_nexus_runtime_root(payload_path) or not payload_path.is_file():
                raise JobError("OPENCODE_BENCHMARK_PAYLOAD_INVALID")
            payload=json.loads(payload_path.read_text(encoding="utf-8"))
            if payload.get("model")!="opencode/mimo-v2.6-flash-free": raise JobError("OPENCODE_MODEL_NOT_APPROVED_FREE_ROUTE")
            workers=worker_discovery(); workers["codex"]["state"]="RATE_LIMITED"
            task=CodingTask(task_id=job.job_id,objective_id=job.governance_context.get("owner_objective_id"),
                prompt="Create reports/runtime/opencode_v5_probe.txt containing exactly OPENCODE_V5_FREE_MODEL_PROBE_OK.",
                allowed_paths=("reports/runtime/",),protected_paths=("src/","data/","configs/"),
                acceptance=("exact marker exists","no protected paths changed","deterministic benchmark"),
                checkpoint_sha=payload["checkpoint_sha"],campaign_id=job.governance_context.get("campaign_id"),
                owner_objective_id=job.governance_context.get("owner_objective_id"),
                objective_version=job.governance_context.get("objective_version"),job_id=job.job_id,
                worker_role="CODING_AND_SYSTEM_REPAIR_ONLY")
            selected=select_worker(task,workers,unavailable=(),probe_installed_unproven=True)
            if selected!="opencode": raise JobError("OPENCODE_FAILOVER_SELECTION_FAILED")
            prior_model=os.environ.get("NEXUS_OPENCODE_MODEL")
            os.environ["NEXUS_OPENCODE_MODEL"]=payload["model"]
            try: benchmark=OpenCodeExecuteAdapter().execute(task,timeout=90)
            finally:
                if prior_model is None: os.environ.pop("NEXUS_OPENCODE_MODEL",None)
                else: os.environ["NEXUS_OPENCODE_MODEL"]=prior_model
            result={"status":"COMPLETED" if benchmark.get("status")=="PASS" and benchmark.get("independent_verification") else "BLOCKED",
                "check":"CODEX_RATE_LIMIT_TO_REAL_OPENCODE_FAILOVER","selected_worker":selected,
                "model":payload["model"],"simulation":"CODEX_RATE_LIMITED; OPENCODE_EXECUTED_FOR_REAL",
                "benchmark":benchmark,"artifact_ref":artifact_ref,"evidence_class":"REAL_OPENCODE_ISOLATED_WORKTREE"}
        elif job.job_type=="V5_TRADING_MARKET_SCAN":
            sys.path.insert(0,str(ROOT/"scripts"/"trading"))
            from forex_research_scanner import scan
            report=scan()
            artifact_ref="reports/runtime/forex_research_latest.json"
            result={"status":"COMPLETED" if report.get("market_health",{}).get("status")=="FOREX_MARKET_HEALTHY" else "BLOCKED",
                "check":"OANDA_PRACTICE_READ_ONLY_FOREX_SCAN","artifact_ref":artifact_ref,
                "report":report,"evidence_class":"LIVE_PRACTICE_MARKET_RESEARCH"}
        else: raise JobError("UNREGISTERED_V5_INTEGRATION_CHECK")
        artifact_path.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    elif route == "V6_INTEGRATION_CHECK":
        from nexus_agent_platform.durable_objective_control import load_active_campaign
        state=load_active_campaign()
        if (state.get("CAMPAIGN_ID")!="NEXUS-REAL-WORLD-OWNER-V6-20261010"
                or state.get("OWNER_OBJECTIVE_ID")!="ownerobj_nexus_real_world_owner_v6_20261010"
                or job.job_type!="V6_OANDA_PRACTICE_SCAN"):
            raise JobError("V6_INTEGRATION_CAMPAIGN_CONTRACT_INVALID")
        from trading.oanda_demo_common import PRACTICE_HOST, environment, mask
        current=environment()
        account_discovery={"status":"NOT_REQUIRED" if current.get("account_id_present") else "NOT_ATTEMPTED",
                           "account_count":None,"selected_single_account":False,"candidates":[]}
        if not current.get("live_endpoint_configured") and current.get("token_present") and not current.get("account_id_present"):
            from alpha.alpha_live_research import http_json
            headers={"Authorization":f"Bearer {current['token']}","Accept-Datetime-Format":"RFC3339"}
            ok,http_status,data,error,latency=http_json("GET",PRACTICE_HOST+"/v3/accounts",headers,timeout=20)
            accounts=data.get("accounts",[]) if ok and isinstance(data,dict) else []
            from urllib.parse import quote as quote_path
            candidates=[]
            for account in accounts[:8]:
                account_id=str(account.get("id") or "") if isinstance(account,dict) else ""
                tags=account.get("tags",[]) if isinstance(account,dict) else []
                detail={"account_id_masked":mask(account_id),"tags":tags if isinstance(tags,list) else []}
                if account_id:
                    details_ok,details_status,details_data,details_error,details_latency=http_json(
                        "GET",PRACTICE_HOST+"/v3/accounts/"+quote_path(account_id,safe=""),headers,timeout=20)
                    summary=details_data.get("account",{}) if details_ok and isinstance(details_data,dict) else {}
                    detail.update({"details_http_status":details_status,"currency":summary.get("currency"),
                        "alias":summary.get("alias"),"account_type":summary.get("type"),
                        "details_error":details_error,"details_latency_ms":details_latency,
                        "is_default_tagged":any("default" in str(tag).lower() for tag in (tags if isinstance(tags,list) else []))})
                candidates.append({**detail,"_account_id":account_id})
            defaults=[row for row in candidates if row.get("is_default_tagged")]
            primaries=[row for row in candidates if str(row.get("alias") or "").strip().lower()=="primary"]
            usd=[row for row in candidates if str(row.get("currency") or "").upper()=="USD"]
            selected=(candidates[0] if len(candidates)==1 else defaults[0] if len(defaults)==1 else primaries[0] if len(primaries)==1 else usd[0] if len(usd)==1 else None)
            account_discovery={"status":"DISCOVERED" if selected else "AMBIGUOUS" if len(accounts)>1 else "FAILED",
                "http_status":http_status,"latency_ms":latency,"account_count":len(accounts),
                "selected_single_account":bool(selected),"selection_basis":"sole_account" if len(candidates)==1 and selected else "unique_default_tag" if selected and selected in defaults else "unique_primary_alias" if selected and selected in primaries else "unique_usd_practice_account" if selected and selected in usd else None,
                "candidates":[{k:v for k,v in row.items() if k!="_account_id"} for row in candidates],"error":error}
            if selected:
                private=Path.home()/".config/nexus/oanda_practice_account.json"
                private.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
                private.write_text(json.dumps({"environment":"practice","account_id":str(selected["_account_id"]),
                    "source":"authenticated OANDA fxPractice /v3/accounts","discovered_at":datetime.now(timezone.utc).isoformat()},sort_keys=True)+"\n",encoding="utf-8")
                private.chmod(0o600)
        sys.path.insert(0,str(ROOT/"scripts"/"trading"))
        from forex_research_scanner import scan
        report=scan()
        artifact_ref=f"reports/certification/v6/jobs/results/{job.job_id}.json"
        artifact_path=ROOT/artifact_ref
        artifact_path.parent.mkdir(parents=True,exist_ok=True)
        result={"status":"COMPLETED","check":"V6_OANDA_PRACTICE_READ_ONLY_FOREX_SCAN",
            "account_discovery":account_discovery,"market_scan_status":report.get("market_health",{}).get("status"),
            "report":report,"artifact_ref":artifact_ref,"live_trading":False,"orders_placed":0,
            "evidence_class":"NEXUS_TRADING_PRACTICE_MARKET_RESEARCH"}
        artifact_path.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    elif route == "DEPARTMENT_QUERY":
        if not job.payload_ref:
            store.transition(job_id, "BLOCKED", worker_id=worker_id,
                             error_code="DEPARTMENT_QUERY_PAYLOAD_REQUIRED")
            _release_reservation(governor, reservation, job_id)
            return {"status": "BLOCKED", "reason": "DEPARTMENT_QUERY_PAYLOAD_REQUIRED"}
        payload_path=(ROOT / job.payload_ref).resolve()
        if not _is_under_nexus_runtime_root(payload_path) or not payload_path.is_file():
            store.transition(job_id, "BLOCKED", worker_id=worker_id,
                             error_code="DEPARTMENT_QUERY_PAYLOAD_INVALID")
            _release_reservation(governor, reservation, job_id)
            return {"status": "BLOCKED", "reason": "DEPARTMENT_QUERY_PAYLOAD_INVALID"}
        payload=json.loads(payload_path.read_text(encoding="utf-8"))
        question=payload.get("question") if isinstance(payload,dict) else None
        if not isinstance(question,str) or not question.strip() or len(question)>240:
            store.transition(job_id, "BLOCKED", worker_id=worker_id,
                             error_code="DEPARTMENT_QUERY_CONTRACT_INVALID")
            _release_reservation(governor, reservation, job_id)
            return {"status": "BLOCKED", "reason": "DEPARTMENT_QUERY_CONTRACT_INVALID"}
        if job.department.upper() == "ALPHA":
            source_job_id=str(payload.get("source_research_job_id") or "")
            source_job=store.get(source_job_id) if source_job_id else None
            source_receipt_id=str(payload.get("source_department_receipt_id") or "")
            artifact_ref=str(payload.get("source_artifact_ref") or "")
            artifact_path=(ROOT/artifact_ref).resolve()
            if (payload.get("department")!="ALPHA" or not source_job or source_job.department.upper()!="RESEARCH"
                    or source_job.state!="COMPLETED" or not source_job.receipt_ref
                    or source_job.receipt_ref!=payload.get("source_durable_receipt_id")
                    or not source_receipt_id or not _is_under_nexus_runtime_root(artifact_path) or not artifact_path.is_file()):
                store.transition(job_id,"BLOCKED",worker_id=worker_id,error_code="ALPHA_SOURCE_LINEAGE_INVALID")
                _release_reservation(governor,reservation,job_id)
                return {"status":"BLOCKED","reason":"ALPHA_SOURCE_LINEAGE_INVALID"}
            from nexus_agent_platform.alpha_model_review import review_existing_research_artifact
            alpha=review_existing_research_artifact(artifact_path=artifact_path,
                source_job_id=source_job_id,source_receipt_id=source_receipt_id,
                request=str(payload.get("request") or question))
            if alpha.get("status")!="COMPLETE":
                raise RuntimeError("ALPHA_EXECUTION_FAILED: "+str(alpha.get("error") or alpha.get("status")))
            evaluation=alpha.get("evaluation") if isinstance(alpha.get("evaluation"),dict) else {}
            strengths=evaluation.get("strengths") or []
            weaknesses=evaluation.get("weaknesses") or []
            alpha_text=("ALPHA REVIEW — Microsoft Project business example\n\n"
                + "STRENGTHS\n" + "\n".join(f"{i+1}. {x}" for i,x in enumerate(strengths[:3]))
                + "\n\nWEAKNESSES\n" + "\n".join(f"{i+1}. {x}" for i,x in enumerate(weaknesses[:3]))
                + f"\n\nSTRONGEST ASSUMPTION\n{evaluation.get('strongest_assumption') or 'Not supplied by Alpha.'}"
                + f"\n\nWEAKEST ASSUMPTION\n{evaluation.get('weakest_assumption') or 'Not supplied by Alpha.'}"
                + f"\n\nIMPROVEMENT\n{evaluation.get('one_improvement') or 'Not supplied by Alpha.'}"
                + f"\n\nWHY INTERESTING\n{evaluation.get('why_interesting') or 'Not supplied by Alpha.'}"
                + f"\n\nEVIDENCE LIMITATION\n{evaluation.get('reasoning_summary') or 'See Alpha evaluation artifact.'}")
            routed={"status":"success","data":{"answer":alpha_text,"alpha_review":alpha,
                "department_receipt_id":alpha.get("receipt",{}).get("receipt_id"),
                "source_research_job_id":source_job_id}}
        else:
            from nexus_agent_platform.department_router import execute as execute_department
            routed=execute_department(question,input_source="owner_campaign")
        if job.department.upper() == "ALPHA":
            data=routed.get("data") if isinstance(routed.get("data"),dict) else {}
            result={"status":"COMPLETED","question":question,"department_route":"NEXUS_ALPHA_MODEL_REVIEW",
                "department_receipt_id":data.get("department_receipt_id"),"answer":data.get("answer"),
                "alpha_review":data.get("alpha_review"),"source_research_job_id":data.get("source_research_job_id"),
                "evidence_class":"GOVERNED_LIVE_ALPHA_REVIEW"}
        else:
            if not routed:
                store.transition(job_id, "BLOCKED", worker_id=worker_id,
                                 error_code="DEPARTMENT_ROUTE_NOT_EXECUTED")
                _release_reservation(governor, reservation, job_id)
                _footprint(job, store, started_wall, started_cpu, "BLOCKED", "DEPARTMENT_ROUTE_NOT_EXECUTED")
                return {"status":"BLOCKED","reason":"DEPARTMENT_ROUTE_NOT_EXECUTED"}
            response,metadata=routed
            if metadata.get("outcome")!="ANSWERED" or metadata.get("execution_status")!="SUCCEEDED_VERIFIED":
                route_error=str(metadata.get("error") or "DEPARTMENT_EXECUTION_NOT_VERIFIED")[:300]
                store.transition(job_id, "BLOCKED", worker_id=worker_id,
                                 error_code="DEPARTMENT_EXECUTION_NOT_VERIFIED",
                                 error_summary=route_error)
                _release_reservation(governor, reservation, job_id)
                _footprint(job, store, started_wall, started_cpu, "BLOCKED", route_error)
                return {"status":"BLOCKED","reason":"DEPARTMENT_EXECUTION_NOT_VERIFIED",
                        "department_route":metadata.get("route"),"error":metadata.get("error")}
            result={"status":"COMPLETED","question":question,"department_route":metadata.get("route"),
                "run_id":metadata.get("run_id"),"department_receipt_id":metadata.get("receipt_id"),
                "department_receipt_path":metadata.get("receipt_path"),"answer":response,
                "evidence_class":"GOVERNED_LIVE_RESEARCH" if metadata.get("capability_id")=="searxng.research" else "GOVERNED_DEPARTMENT_RESULT"}
    elif route == "NOTEBOOKLM_DISCOVERY":
        if not job.payload_ref:
            store.transition(job_id,"BLOCKED",worker_id=worker_id,error_code="NOTEBOOKLM_DISCOVERY_PAYLOAD_REQUIRED")
            _release_reservation(governor,reservation,job_id)
            return {"status":"BLOCKED","reason":"NOTEBOOKLM_DISCOVERY_PAYLOAD_REQUIRED"}
        payload_path=(ROOT / job.payload_ref).resolve()
        if not _is_under_nexus_runtime_root(payload_path) or not payload_path.is_file():
            store.transition(job_id,"BLOCKED",worker_id=worker_id,error_code="NOTEBOOKLM_DISCOVERY_PAYLOAD_INVALID")
            _release_reservation(governor,reservation,job_id)
            return {"status":"BLOCKED","reason":"NOTEBOOKLM_DISCOVERY_PAYLOAD_INVALID"}
        payload=json.loads(payload_path.read_text(encoding="utf-8"))
        from nexus_agent_platform.notebooklm_discovery import (
            execute_discovery, execute_import_and_synthesize, execute_runtime_canary,
            execute_dedicated_research_canary,
            execute_full_research_canary,
        )
        if payload.get("operation") == "FULL_RESEARCH_NOTEBOOK_NEEDLE_CANARY" and job.job_type == "NEXUS_NOTEBOOKLM_RUNTIME_CANARY":
            result=execute_full_research_canary(job,payload)
        elif payload.get("operation") == "DEDICATED_RESEARCH_WEB_CANARY" and job.job_type == "NEXUS_NOTEBOOKLM_RUNTIME_CANARY":
            result = execute_dedicated_research_canary(job, payload)
        elif payload.get("operation") == "RUNTIME_CANARY" and job.job_type == "NEXUS_NOTEBOOKLM_RUNTIME_CANARY":
            result = execute_runtime_canary(job, payload)
        elif payload.get("operation") in {"IMPORT_AND_SYNTHESIZE","LIST_SOURCES"}:
            result=execute_import_and_synthesize(job,payload)
        else:
            result=execute_discovery(job,payload)
        if result.get("status")!="COMPLETED":
            if result.get("status")=="WAITING_RESOURCE_WINDOW":
                wait={key:result.get(key) for key in ("resource","capability","policy_state","resume_condition","checkpoint_preserved","provider","service","policy_job_type","budget_period") if result.get(key) is not None}
                store.set_governance_context(job_id,{**execution_context,"resource_wait":wait})
                store.transition(job_id,"WAITING",worker_id=worker_id)
                _footprint(job,store,started_wall,started_cpu,"WAITING",result.get("reason"))
                _release_reservation(governor,reservation,job_id)
                return result
            store.transition(job_id,"BLOCKED",worker_id=worker_id,
                             error_code=result.get("reason","NOTEBOOKLM_DISCOVERY_FAILED"),
                             error_summary=str(result.get("error_summary") or "")[:400])
            _release_reservation(governor,reservation,job_id)
            _footprint(job,store,started_wall,started_cpu,"BLOCKED",result.get("reason"))
            return result
    elif route == "RESEARCH_ROOM_ADVISOR":
        result = execute_routed_job(job, route, execution_payload)
    elif route == "RESEARCH":
        _lifecycle(job_id,"ROUTE_SELECTED",job=job,worker_id=worker_id,route="RESEARCH",job_type=job.job_type)
        # The existing dispatched Research runner remains the business-logic owner.
        # Payload references are resolved by that runner in a subsequent adapter call.
        if not job.payload_ref:
            result = {"status": "BLOCKED", "reason": "PAYLOAD_REFERENCE_REQUIRED", "job_type": job.job_type}
            store.transition(job_id, "BLOCKED", worker_id=worker_id)
            _release_reservation(governor, reservation, job_id)
            return result
        os.environ["NEXUS_WORK_ID"] = job.payload_ref
        # The dispatched Research worker must receive the exact assigned
        # queue item. Without this hydration it falls back to a scheduled
        # source, so an owner-requested objective can silently become unrelated
        # discovery work.
        from nexus_agent_platform.research_work_queue import default_queue
        assigned_work = next((item for item in default_queue().load().get("items", [])
                              if item.get("work_id") == job.payload_ref), None)
        if assigned_work is None:
            parent_source = str((job.governance_context or {}).get("source") or "")
            if parent_source in {"NOVA_MCP_RESEARCH_ASSIGNMENT", "RESEARCH_PARENT_CONTINUATION"}:
                store.transition(job_id, "BLOCKED", worker_id=worker_id,
                                 error_code="RESEARCH_WORK_ITEM_NOT_FOUND",
                                 error_summary="durable payload_ref has no matching assigned Research item")
                _footprint(job, store, started_wall, started_cpu, "BLOCKED", "RESEARCH_WORK_ITEM_NOT_FOUND")
                _release_reservation(governor, reservation, job_id)
                return {"status": "BLOCKED", "job_type": job.job_type,
                        "reason": "RESEARCH_WORK_ITEM_NOT_FOUND"}
            # Scheduled/legacy Research jobs use their existing runner, which
            # resolves payload_ref itself. Keep a minimal envelope for common
            # logging/dispatch; never use this fallback for an owner assignment
            # or a parent continuation, where missing scope must fail closed.
            assigned_work = {"work_id": job.payload_ref,
                "requested_intent": (job.governance_context or {}).get("requested_intent"),
                "routed_intent": (job.governance_context or {}).get("routed_intent"),
                "execution_path": (job.governance_context or {}).get("execution_path")}
        # The durable assignment envelope and queue row must agree. The
        # worker never reconstructs a missing semantic intent from title text.
        assigned_work, scope_error = hydrate_research_assignment_scope(assigned_work, job.governance_context)
        if scope_error:
            store.transition(job_id, "BLOCKED", worker_id=worker_id,
                             error_code=scope_error,
                             error_summary="durable assignment intent conflicts with Research work-item intent")
            _footprint(job, store, started_wall, started_cpu, "BLOCKED", scope_error)
            _release_reservation(governor, reservation, job_id)
            return {"status": "BLOCKED", "job_type": job.job_type, "reason": scope_error}
        _lifecycle(job_id,"WORK_ITEM_HYDRATED",job=job,worker_id=worker_id,
                   work_id=assigned_work.get("work_id"),objective_id=assigned_work.get("objective_id"),
                   project_id=assigned_work.get("project_id") or assigned_work.get("work_id"))
        _lifecycle(job_id,"INTENT_VALIDATED",job=job,worker_id=worker_id,
                   intent=assigned_work.get("requested_intent"))
        os.environ["NEXUS_WORK_ITEM_JSON"] = json.dumps(assigned_work, separators=(",", ":"))
        research_parent_source = str((job.governance_context or {}).get("source") or "")
        if (job.job_type == "RESEARCH_INTAKE"
                and research_parent_source == "RESEARCH_PARENT_CONTINUATION"):
            # One durable child represents one parent-selected stage. The
            # stage adapter runs at the common result-consumption boundary
            # below, after its input and lease have been validated.
            result = {"status": "COMPLETED", "job_type": job.job_type,
                      "research_parent_action": (job.governance_context or {}).get("research_parent_action"),
                      "objective_id": (job.governance_context or {}).get("objective_id")}
            completed = None
        elif (job.job_type == "RESEARCH_INTAKE"
                and research_parent_source == "NOVA_MCP_RESEARCH_ASSIGNMENT"
                and str(assigned_work.get("requested_intent") or "").upper() == "RESEARCH_MISSION"):
            # The MCP intake job owns opening/joining the canonical Research
            # Case Engine record. This is a local write; Advisor/source work is
            # deferred to later governed turns.
            _lifecycle(job_id,"PRE_CASE_INPUTS_READY",job=job,worker_id=worker_id,
                       objective_id=assigned_work.get("objective_id"),work_id=assigned_work.get("work_id"),
                       project_id=assigned_work.get("project_id") or assigned_work.get("work_id"))
            _lifecycle(job_id,"CASE_OPEN_START",job=job,worker_id=worker_id)
            case_open = open_mcp_research_intake_case(assigned_work)
            _lifecycle(job_id,"CASE_OPEN_RETURNED",job=job,worker_id=worker_id,
                       status=case_open.get("status"),case_id=case_open.get("case_id"),reason=case_open.get("reason"))
            if case_open["status"] == "WAITING_FOR_CAPACITY":
                result = {"status": "WAITING_FOR_CAPACITY", "reason": case_open["reason"],
                    "objective_id": assigned_work.get("objective_id"),
                    "retryable": True, "objective_terminated": False}
            elif case_open["status"] != "CASE_OPENED":
                result = {"status": "BLOCKED", "reason": case_open.get("reason") or "RESEARCH_CASE_NOT_VERIFIED",
                    "job_type": job.job_type, "objective_id": assigned_work.get("objective_id")}
            else:
                assigned_work["research_case_id"] = case_open["case_id"]
                assigned_work["case_id"] = case_open["case_id"]
                os.environ["NEXUS_WORK_ITEM_JSON"] = json.dumps(assigned_work, separators=(",", ":"))
                os.environ["NEXUS_JOB_SOURCE"] = research_parent_source
                _lifecycle(job_id,"RESEARCH_EXECUTION_START",job=job,worker_id=worker_id)
                completed = subprocess.run([sys.executable, str(ROOT / "scripts/research/run_dispatched_research_job.py"),
                                            "--execution-id", job.job_id], cwd=ROOT,
                                           capture_output=True, text=True, timeout=900, check=False)
                if completed.returncode:
                    raise RuntimeError(f"RESEARCH_INTAKE_EXIT_{completed.returncode}: {completed.stderr[-300:]}")
                _lifecycle(job_id,"RESEARCH_EXECUTION_COMPLETE",job=job,worker_id=worker_id,
                           child_returncode=completed.returncode)
                intake_result = _result_json(completed.stdout)
                if str(intake_result.get("status") or "").upper() != "RESEARCH_CONTINUATION_REQUIRED":
                    result = {"status": "BLOCKED", "reason": intake_result.get("reason") or "RESEARCH_INTAKE_CONTRACT_MISSING",
                              "child_result": intake_result, "job_type": job.job_type}
                else:
                    intake_result["case_id"] = case_open["case_id"]
                    result = {"status": "COMPLETED", "job_type": job.job_type,
                        "objective_id": assigned_work.get("objective_id"), "case_id": case_open["case_id"],
                        "child_result": intake_result,
                        "requested_intent": assigned_work.get("requested_intent"),
                        "routed_intent": intake_result.get("routed_intent"),
                        "execution_path": intake_result.get("execution_path")}
            completed = None
        elif (job.job_type == "RESEARCH_INTAKE"
                and research_parent_source == "NOVA_RESEARCH_CONTINUATION"
                and str(assigned_work.get("requested_intent") or "").upper() == "RESEARCH_MISSION"):
            # A Nova continuation without a source URL is a Research objective,
            # not a scheduled web-source item. Reuse the governed Research
            # Intake adapter so it opens/joins the objective's case without
            # entering generic public-web acquisition and exhausting the job's
            # response-byte envelope before meaningful work begins.
            from nexus_agent_platform.research_assignment_executor import execute_assignment
            routed = execute_assignment(assigned_work)
            case_id = str(routed.get("case_id") or "")
            if (str(routed.get("status") or "").upper() != "CONTINUATION_REQUIRED"
                    or not case_id):
                result = {"status": "BLOCKED", "job_type": job.job_type,
                    "objective_id": assigned_work.get("objective_id"),
                    "requested_intent": assigned_work.get("requested_intent"),
                    "execution_path": routed.get("execution_path") or "RESEARCH_INTAKE",
                    "reason": routed.get("reason") or "RESEARCH_CASE_NOT_VERIFIED"}
                from nexus_agent_platform.research_work_queue import default_queue
                default_queue().settle(job.payload_ref, "FAILED_RETRYABLE",
                    result={"error": result["reason"], "execution_path": result["execution_path"]},
                    blocker_type="RESEARCH_CASE_NOT_VERIFIED")
            else:
                intake_result = {key: routed.get(key) for key in (
                    "status", "case_id", "execution_path", "requested_intent", "routed_intent",
                    "notebook_id", "notebooklm_selected") if routed.get(key) is not None}
                intake_result["next_action"] = routed.get("next_action") or "RESEARCH_SOURCE_ACQUISITION_AND_EVIDENCE_GATHERING"
                assigned_work["research_case_id"] = case_id
                assigned_work["case_id"] = case_id
                assigned_work["current_stage"] = "RESEARCH_CASE_OPENED"
                assigned_work["last_checkpoint"] = "RESEARCH_INTAKE_VERIFIED"
                from nexus_agent_platform.research_work_queue import default_queue
                queue = default_queue()
                queue.upsert(assigned_work)
                queue.settle(job.payload_ref, "COMPLETE", result=intake_result)
                result = {"status": "COMPLETED", "job_type": job.job_type,
                    "objective_id": assigned_work.get("objective_id"), "case_id": case_id,
                    "requested_intent": assigned_work.get("requested_intent"),
                    "routed_intent": routed.get("routed_intent"),
                    "execution_path": routed.get("execution_path") or "RESEARCH_INTAKE",
                    "research_stage": "RESEARCH_CASE_OPENED", "child_result": intake_result,
                    "new_research_job_created": False}
            completed = None
        elif ((job.governance_context or {}).get("source") == "NOVA_MCP_RESEARCH_ASSIGNMENT"
                and job.job_type in {"RESEARCH_GAP_VERIFY", "RESEARCH_RUNTIME_INSPECT", "NOTEBOOKLM_RESEARCH"}):
            # Semantic intent chooses the bounded Research executor. Only an
            # explicit PUBLIC_RESEARCH_SEARCH intent may invoke SearXNG.
            from nexus_agent_platform.research_assignment_executor import execute_assignment
            from nexus_agent_platform.research_assignment_intent import result_contract

            def _public_search(question: str):
                from nexus_agent_platform.department_router import execute as execute_department
                bounded = str(question or "").strip()[:240]
                if not re.match(r"(?i)^research\b", bounded):
                    bounded = "Research " + bounded
                is_owner_campaign = (job.governance_context or {}).get("owner_objective_id") == "ownerobj_nexus_full_owner_real_world_v5_6fb82fd9"
                routed = execute_department(bounded[:240], input_source="owner_campaign" if is_owner_campaign else "telegram")
                if not routed:
                    return None
                answer, metadata = routed
                if metadata.get("outcome") != "ANSWERED" or metadata.get("execution_status") != "SUCCEEDED_VERIFIED":
                    return None
                return {"answer": answer, "department_route": metadata.get("route"),
                        "capability_id": metadata.get("capability_id"), "receipt_id": metadata.get("receipt_id"),
                        "receipt_path": metadata.get("receipt_path"), "execution_status": metadata.get("execution_status")}

            routed = execute_assignment(assigned_work, public_search=_public_search)
            fulfillment = routed.get("task_fulfillment") or result_contract(
                requested_intent=str(assigned_work.get("requested_intent") or "UNKNOWN_RESEARCH_INTENT"),
                routed_intent=str(routed.get("routed_intent") or "UNKNOWN_RESEARCH_INTENT"),
                execution_path=str(routed.get("execution_path") or "UNDECLARED"),
                status=str(routed.get("status") or "BLOCKED"), result=routed.get("result"),
                blocker=routed.get("reason"))
            routed_intent = str(routed.get("routed_intent") or fulfillment.get("routed_intent") or "UNKNOWN_RESEARCH_INTENT")
            waiting_for_capacity = str(routed.get("status") or "").upper() == "WAITING_FOR_CAPACITY"
            result = {"status": "COMPLETED" if fulfillment.get("task_fulfilled") else
                                "WAITING" if waiting_for_capacity else "BLOCKED",
                      "job_type": job.job_type, "department": "RESEARCH", "executing_component": "NEXUS_RESEARCH",
                      "objective_id": assigned_work.get("objective_id"),
                      "requested_intent": assigned_work.get("requested_intent"), "routed_intent": routed_intent,
                      "execution_path": routed.get("execution_path") or fulfillment.get("execution_path"),
                      "task_fulfillment": fulfillment, "result": routed.get("result"),
                      "reason": routed.get("reason") or fulfillment.get("routing_blocker"),
                      "public_search_performed": bool(routed.get("public_search_performed", False))}
            from nexus_agent_platform.research_work_queue import default_queue
            failed_item = dict(assigned_work)
            failed_item["last_result"] = {"final_status": "RESEARCH_COMPLETE" if fulfillment.get("task_fulfilled") else
                "WAITING_FOR_CAPACITY" if waiting_for_capacity else "RESEARCH_TASK_NOT_FULFILLED",
                "requested_intent": assigned_work.get("requested_intent"), "routed_intent": routed_intent,
                "execution_path": result["execution_path"], "task_fulfillment": fulfillment,
                "result": routed.get("result"), "blocker": result.get("reason"),
                "objective_terminated": False if waiting_for_capacity else None}
            failed_item["last_attempt"] = {"job_id": job_id, "attempt": job.attempt_count,
                "at": datetime.now(timezone.utc).isoformat()}
            default_queue().upsert(failed_item)
            if fulfillment.get("task_fulfilled"):
                default_queue().settle(job.payload_ref, "COMPLETE", result=failed_item["last_result"])
            elif waiting_for_capacity:
                default_queue().settle(job.payload_ref, "WAITING", result=failed_item["last_result"],
                    blocker_type="MAX_ACTIVE_DEEP_CASES_REACHED")
            else:
                default_queue().settle(job.payload_ref, "BLOCKED_EXTERNAL", result=failed_item["last_result"])
            # Continue through the common governed receipt/footprint writer.
            completed=None
        else:
            # Full missions enter the existing Research intake runner. That
            # workflow owns source acquisition and selects optional digestion
            # tools after inspecting the source; the MCP assignment worker
            # does not force every mission through NotebookLM.
            completed = subprocess.run([sys.executable, str(ROOT / "scripts/research/run_dispatched_research_job.py"), "--execution-id", job.job_id],
                                       cwd=ROOT, capture_output=True, text=True, timeout=900, check=False)
        if completed is not None and completed.returncode:
            # Research emits structured failure details on stdout. Preserve
            # both streams in the durable error so provider/policy failures
            # can be repaired without guessing from an empty stderr tail.
            raise RuntimeError(
                f"RESEARCH_EXIT_{completed.returncode}: "
                f"stdout_tail={completed.stdout[-700:]} stderr_tail={completed.stderr[-500:]}"
            )
        if completed is None:
            progression={"status":"NEXUS_RESEARCH_DEPARTMENT_COMPLETED"}
        elif completed is None and result.get("status") == "COMPLETED" and job.job_type == "RESEARCH_GAP_VERIFY":
            from nexus_agent_platform.feeder_runtime import continue_research_gap
            progression=continue_research_gap(job.payload_ref)
        elif job.job_type=="MARKETING_RESEARCH_GAP_VERIFY":
            from nexus_agent_platform.marketing_creative_workflow import research_completed_event
            progression=research_completed_event(job,result_ref=f"research-result:{job.payload_ref}")
        else: progression={"status":"NO_AUTOMATIC_NEXT_STAGE"}
        if completed is not None:
            result = {"status": "COMPLETED", "job_type": job.job_type, "stdout_tail": completed.stdout[-1000:],"progression":progression}
    elif route == "FEEDER":
        runtime=ROOT / "scripts/nexus_agent_platform/feeder_runtime.py"
        if job.job_type == "FEEDER_RESEARCH_CONTINUATION":
            command=[sys.executable,str(runtime),"continue-source","--source-id",job.payload_ref or ""]
        else:
            command=[sys.executable,str(runtime),"process-once","--feeder-type",job.job_type,"--source-id",job.payload_ref or ""]
        if not job.payload_ref:
            store.transition(job_id,"BLOCKED",worker_id=worker_id)
            raise JobError("PAYLOAD_REFERENCE_REQUIRED")
        completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=600, check=False)
        if completed.returncode:
            raise RuntimeError(f"FEEDER_EXIT_{completed.returncode}: {completed.stderr[-300:]}")
        progress=_result_json(completed.stdout)
        if progress.get("status")=="WAITING_FOR_RESEARCH_GAPS":
            store.transition(job_id,"WAITING",worker_id=worker_id)
            _footprint(job,store,started_wall,started_cpu,"WAITING")
            _release_reservation(governor, reservation, job_id)
            return {"status":"WAITING","job_type":job.job_type,"source_id":job.payload_ref}
        if job.job_type not in {"FEEDER_RESEARCH_CONTINUATION","RAY_NOVA_OPPORTUNITY_INTAKE"} and progress.get("count")==0:
            raise JobError("FEEDER_SOURCE_NOT_CLAIMABLE")
        result = {"status": "COMPLETED", "job_type": job.job_type, "stdout_tail": completed.stdout[-1000:],"workflow_event":progress.get("status")}
    elif route == "FINANCE":
        if job.job_type != "FINANCE_CAMPAIGN_REVIEW":
            raise JobError("UNSUPPORTED_FINANCE_JOB_TYPE")
        from nexus_agent_platform.finance.job_handlers import handle_campaign_review
        result = handle_campaign_review(job, store)
    elif route == "DOCUMENT_ANALYSIS":
        if job.job_type != "CREDIT_REPORT_ANALYSIS" or not job.source_document_id or job.payload_ref != job.source_document_id:
            raise JobError("CREDIT_DOCUMENT_IDENTITY_REQUIRED")
        completed = subprocess.run(
            [sys.executable, str(ROOT / "scripts/credit/parse_uploaded_credit_report.py"),
             "--document-id", job.source_document_id, "--nexus-job-id", job.job_id],
            cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=900, check=False)
        if completed.returncode:
            raise JobError(f"CREDIT_ANALYSIS_EXIT_{completed.returncode}")
        result = {"status":"COMPLETED","job_type":job.job_type,"source_document_id":job.source_document_id}
    else:
        if not job.payload_ref:
            store.transition(job_id,"BLOCKED",worker_id=worker_id)
            raise JobError("HANDOFF_REFERENCE_REQUIRED")
        if job.job_type=="PULSE_HANDOFF":
            runtime=ROOT / "scripts/research/pulse_runtime.py"
            command=[sys.executable,str(runtime),"handoff-once","--handoff-id",job.payload_ref]
        elif job.job_type=="HANDOFF_DELIVERY":
            runtime=ROOT / "scripts/nexus_agent_platform/feeder_runtime.py"
            command=[sys.executable,str(runtime),"handoff-delivery-once","--handoff-ref",job.payload_ref]
        else:
            runtime=ROOT / "scripts/nexus_agent_platform/feeder_runtime.py"
            command=[sys.executable,str(runtime),"handoff-once","--handoff-id",job.payload_ref]
        completed=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,timeout=120,check=False)
        if completed.returncode:
            raise RuntimeError(f"HANDOFF_EXIT_{completed.returncode}: {completed.stderr[-300:]}")
        result={"status":"COMPLETED","job_type":job.job_type,"handoff_result":_result_json(completed.stdout)}
    # The durable worker is the sole consumer of Research child results.
    # Persist each child result and hand continuation to the parent workflow;
    # a child receipt never completes the root objective by itself.
    parent_source = str((job.governance_context or {}).get("source") or "")
    is_parent_child = (job.department.upper() == "RESEARCH" and job.job_type == "RESEARCH_INTAKE"
        and (parent_source == "RESEARCH_PARENT_CONTINUATION" or
             (parent_source == "NOVA_MCP_RESEARCH_ASSIGNMENT" and
              str((assigned_work or {}).get("requested_intent") or "").upper() == "RESEARCH_MISSION"))
        and str(result.get("status") or "").upper() != "WAITING_FOR_CAPACITY")
    if is_parent_child:
        from nexus_agent_platform.research_parent_workflow import consume_child_result
        child_payload = result.get("child_result") if isinstance(result.get("child_result"), dict) else result
        parent_result = consume_child_result(store, job=job, result=child_payload,
                                             work_item=assigned_work or {})
        result["research_parent"] = {key: parent_result.get(key) for key in (
            "status", "research_parent_id", "root_objective_status", "next_action", "next_job_id")}
    if result.get("status") == "WAITING_FOR_CAPACITY":
        reason = str(result.get("reason") or "MAX_ACTIVE_DEEP_CASES_REACHED")
        _settle_capacity_wait(job, worker_id, store, reservation, governor, reason)
        _footprint(job,store,started_wall,started_cpu,"FAILED_RETRYABLE",reason)
        return result
    from nexus_agent_platform.supabase_egress_guard import job_egress_snapshot, JOB_MAX_RESPONSE_BYTES
    egress = job_egress_snapshot(job.job_id)
    attempt_budget_exceeded = egress.get("attempt_budget_exceeded", egress.get("budget_exceeded", False))
    attempt_response_bytes = egress.get("attempt_response_bytes", egress.get("response_bytes", 0))
    if attempt_budget_exceeded or attempt_response_bytes > min(JOB_MAX_RESPONSE_BYTES,int(budget["max_response_bytes"])):
        raise JobError("JOB_EGRESS_BUDGET_EXCEEDED")
    attempt_egress=_egress_delta(egress,prior_egress)
    governor.reconcile(reservation["reservation_id"],{"requests":attempt_egress["request_count"],"bytes":attempt_egress["response_bytes"],"cost":0})
    ACTIVE_RESERVATIONS.pop(job_id,None)
    result["egress"] = egress
    if time.time()-started_wall > budget["max_runtime_seconds"]: raise JobError("JOB_RUNTIME_BUDGET_EXCEEDED")
    if result.get("status")=="WAITING_RESOURCE_WINDOW":
        result["execution"] = execution_record
        wait={key:result.get(key) for key in ("resource","capability","policy_state","resume_condition","checkpoint_preserved","provider","service","policy_job_type","budget_period") if result.get(key) is not None}
        store.set_governance_context(job_id,{**execution_context,"resource_wait":wait})
        store.transition(job_id,"WAITING",worker_id=worker_id)
        _footprint(job,store,started_wall,started_cpu,"WAITING",result.get("reason"))
        return result
    if result.get("status") == "BLOCKED":
        diagnostic = {key: result.get(key) for key in (
            "reason", "error_summary", "execution", "result_summary", "stdout", "stderr")
            if result.get(key) is not None}
        store.transition(job_id,"BLOCKED",worker_id=worker_id,
            error_code=result.get("reason","WORKFLOW_BLOCKED"),
            error_summary=json.dumps(diagnostic or result.get("missing", []), default=str)[:1800])
        try:
            governor.record_incident("NEXUS_WORKFLOW", job_id, result.get("reason", "WORKFLOW_BLOCKED"),
                                     "BLOCKED_BEFORE_EXTERNAL_SIDE_EFFECT", project_id="NEXUS")
        except Exception:
            pass
        _footprint(job,store,started_wall,started_cpu,"BLOCKED",result.get("reason"))
        return result
    result["execution"] = execution_record
    # Keep a bounded, owner-readable result projection with the durable job.
    # The full worker output stays in its receipt/artifact; exact status reads
    # must not collapse a successful Systems check to STATE=COMPLETED.
    if ((job.job_type == "NEXUS_DEPARTMENT_QUERY" and job.department.upper() == "SYSTEMS")
            or job.job_type in {"NOVA_CREATIVE_ASSET", "NOVA_BOUNDED_CODING_TASK"}):
        projection = _bounded_result_summary(result)
        execution_context = dict(job.governance_context or {})
        execution_context["result_summary"] = projection
        store.set_governance_context(job_id, execution_context)
    # Persist immutable execution evidence before marking the durable job
    # complete. A footprint outage must leave the job retryable instead of
    # creating a terminal row with no worker record.
    from nexus_agent_platform.durable_jobs import _canonical_hash
    expected_result_hash=_canonical_hash(result)
    footprint=_footprint(job,store,started_wall,started_cpu,"COMPLETED",receipt_hash=expected_result_hash)
    if not footprint:
        raise JobError("COMPLETION_FOOTPRINT_REQUIRED")
    receipt=store.complete(job_id, worker_id, result)
    _lifecycle(job_id,"JOB_TERMINAL_TRANSITION",job=job,worker_id=worker_id,state="COMPLETED",receipt_present=True)
    if route == "MARKETING_CREATIVE":
        from nexus_agent_platform.marketing_creative_workflow import record_job_receipt
        record_job_receipt(job, receipt)
    elif route == "COMPANY_CERTIFICATION":
        from nexus_agent_platform.company_certification_workflow import record_receipt
        record_receipt(job, receipt, result)
    result["receipt_ref"]=receipt
    # A governed Research follow-up may carry a same-objective Alpha handoff.
    # Persist the Research evidence first, then create Alpha's job from that
    # exact artifact and receipt. Idempotency is keyed by the Research job.
    if (job.job_type == "RESEARCH_GAP_VERIFY" and job.department.upper() == "RESEARCH"
            and (job.governance_context or {}).get("source") == "NOVA_MCP_RESEARCH_ASSIGNMENT"
            and (assigned_work or {}).get("followup_department") == "ALPHA"):
        try:
            department_receipt_id=str(result.get("department_receipt_id") or "")
            artifact=Path(str(result.get("department_receipt_path") or ""))
            if not artifact.is_absolute():
                artifact=ROOT/artifact
            artifact=artifact.resolve()
            if not department_receipt_id or not artifact.is_file() or not _is_under_nexus_runtime_root(artifact):
                raise JobError("CROSS_DEPARTMENT_RESEARCH_EVIDENCE_NOT_PERSISTED")
            parent_request_id=job.correlation_id
            payload_ref=f"data/runtime/nova_cross_department_alpha/{job_id}.json"
            from nexus_agent_platform.runtime.paths import nexus_research_state_path
            payload_path=nexus_research_state_path("runtime", "nova_cross_department_alpha", f"{job_id}.json")
            payload_ref=str(payload_path)
            payload_path.parent.mkdir(parents=True,exist_ok=True)
            payload={"schema_version":"nexus.alpha-research-followup.v1","department":"ALPHA",
                "source_research_job_id":job_id,"source_durable_receipt_id":receipt,
                "source_department_receipt_id":department_receipt_id,
                "source_artifact_ref":str(artifact.relative_to(ROOT.resolve())),
                "request":"Reevaluate the same opportunity using the improved Research evidence. State what the new evidence resolved, what remains uncertain, and whether your conclusion changed.",
                "question":"Reevaluate the same opportunity using the improved evidence.",
                "parent_request_id":parent_request_id,"created_by":"NOVA_CROSS_DEPARTMENT_ORCHESTRATOR",
                "research_creation_authorized":False}
            payload_path.write_text(json.dumps(payload,sort_keys=True,indent=2)+"\n",encoding="utf-8")
            context={**(job.governance_context or {}),"source":"NOVA_CROSS_DEPARTMENT_ALPHA_HANDOFF","parent_mission_id":parent_request_id,
                "source_research_job_id":job_id,"spend_allowed":False,"paid_provider_authorized":False,
                "external_actions_authorized":False,"external_actions_allowed":False,
                "independent_job":True,"resource_dependencies":[],
                "research_creation_authorized":False}
            alpha_job=store.enqueue("ALPHA","NEXUS_DEPARTMENT_QUERY",priority=100,
                payload_ref=payload_ref,parent_job_id=job.parent_job_id,correlation_id=parent_request_id,
                max_attempts=3,idempotency_key=f"nova-alpha-followup:{job_id}",governance_context=context)
            result["alpha_reevaluation_job_id"]=alpha_job.job_id
            result["alpha_reevaluation_state"]=alpha_job.state
        except Exception as exc:
            result["alpha_handoff_error"]={"type":type(exc).__name__,"message":str(exc)[:240]}
            raise
    # Systems completion is owner-visible through Nova only after the durable
    # job and receipt have committed. Keep the event idempotent via the
    # completed job/receipt identity; the proactive worker also retains failed
    # deliveries for its normal retry cycle.
    if job.job_type == "NEXUS_DEPARTMENT_QUERY" and job.department.upper() == "SYSTEMS":
        answer = str(result.get("answer") or "Systems completed without a formatted answer.")
        event = {
            "kind": "SYSTEMS_RESULT", "event_type": "SYSTEMS_RESULT",
            "title": "Nexus Systems health check completed",
            "department": "SYSTEMS", "status": "COMPLETED",
            "source": str(receipt), "systems_job_id": job_id,
            "department_receipt_id": result.get("department_receipt_id"),
            "summary": (f"SYSTEMS_JOB_ID={job_id}\nJOB_STATUS=COMPLETED\n"
                        f"EXECUTING_DEPARTMENT=SYSTEMS\n{answer}\nRECEIPT_ID={receipt}"),
            "why_it_matters": "Current Systems evidence and its durable receipt are available.",
            "next": "No action is required unless the Systems findings identify a concrete issue.",
        }
        try:
            from nova.proactive_communications import MATERIAL_EVENTS_PATH
            MATERIAL_EVENTS_PATH.parent.mkdir(parents=True, exist_ok=True)
            with MATERIAL_EVENTS_PATH.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(event, sort_keys=True) + "\n")
            campaign_context=job.governance_context or {}
            from nexus_agent_platform.runtime.paths import nexus_research_state_path
            payload_path=nexus_research_state_path("runtime", "nova_systems_result_notices", f"{job_id}.json")
            payload_ref=str(payload_path)
            payload_path.parent.mkdir(parents=True,exist_ok=True)
            payload_path.write_text(json.dumps({"event":event,"completed_systems_job_id":job_id,
                "completed_systems_receipt_id":receipt},sort_keys=True,indent=2)+"\n",encoding="utf-8")
            context={**campaign_context,"source":"NEXUS_SYSTEMS_COMPLETION_NOTICE",
                "completed_systems_job_id":job_id,"completed_systems_receipt_id":receipt,
                "spend_allowed":False,"paid_provider_authorized":False,
                "external_actions_authorized":False,"external_actions_allowed":True}
            notice=store.enqueue("NOVA","NOVA_SYSTEMS_RESULT_NOTICE",priority=100,
                payload_ref=payload_ref,parent_job_id=job.parent_job_id,
                correlation_id=job.correlation_id,max_attempts=3,
                idempotency_key=f"nova-systems-result-notice:{job_id}:{receipt}",
                governance_context=context)
            result["nova_notice_job_id"]=notice.job_id
            result["nova_delivery_state"]="QUEUED"
        except Exception as exc:
            result["nova_delivery"] = {"status": "FAILED_RETAINED_FOR_RETRY",
                                       "error_type": type(exc).__name__,
                                       "event_type": "SYSTEMS_RESULT"}
    elif job.job_type == "NEXUS_DEPARTMENT_QUERY" and job.department.upper() == "ALPHA":
        alpha=result.get("alpha_review") if isinstance(result.get("alpha_review"),dict) else {}
        evaluation=alpha.get("evaluation") if isinstance(alpha.get("evaluation"),dict) else {}
        department_receipt=str(result.get("department_receipt_id") or "")
        event={"kind":"ALPHA_RESULT","event_type":"ALPHA_RESULT",
            "title":"Nexus Alpha completed the Microsoft Project review",
            "department":"ALPHA","status":"COMPLETED","source":str(receipt),
            "alpha_job_id":job_id,"department_receipt_id":department_receipt,
            "source_research_job_id":result.get("source_research_job_id"),
            "summary":(f"ALPHA_JOB_ID={job_id}\nRECEIPT_ID={receipt}\n"
                f"DEPARTMENT_RECEIPT_ID={department_receipt}\nEXECUTING_DEPARTMENT=ALPHA\n"
                f"RESULT={str(result.get('answer') or 'Alpha completed; see persisted evaluation.')[:2550]}"),
            "why_it_matters":"The requested review was performed by Nexus Alpha against the linked Research artifact.",
            "next":"No further action is implied; the evidence limitations remain part of the evaluation."}
        try:
            from nova.proactive_communications import MATERIAL_EVENTS_PATH
            MATERIAL_EVENTS_PATH.parent.mkdir(parents=True,exist_ok=True)
            with MATERIAL_EVENTS_PATH.open("a",encoding="utf-8") as stream:
                stream.write(json.dumps(event,sort_keys=True)+"\n")
            from nexus_agent_platform.runtime.paths import nexus_research_state_path
            payload_path=nexus_research_state_path("runtime", "nova_alpha_result_notices", f"{job_id}.json")
            payload_ref=str(payload_path)
            payload_path.parent.mkdir(parents=True,exist_ok=True)
            payload_path.write_text(json.dumps({"event":event,"completed_alpha_job_id":job_id,
                "completed_alpha_receipt_id":receipt},sort_keys=True,indent=2)+"\n",encoding="utf-8")
            context={**(job.governance_context or {}),"source":"NEXUS_ALPHA_COMPLETION_NOTICE",
                "alpha_job_id":job_id,"completed_alpha_job_id":job_id,"completed_alpha_receipt_id":receipt,
                "spend_allowed":False,"paid_provider_authorized":False,
                "external_actions_authorized":False,"external_actions_allowed":True}
            notice=store.enqueue("NOVA","NOVA_ALPHA_RESULT_NOTICE",priority=100,
                payload_ref=payload_ref,parent_job_id=job.parent_job_id,
                correlation_id=job.correlation_id,max_attempts=3,
                idempotency_key=f"nova-alpha-result-notice:{job_id}:{receipt}",
                governance_context=context)
            result["nova_notice_job_id"]=notice.job_id
            result["nova_delivery_state"]="QUEUED"
        except Exception as exc:
            result["nova_delivery"]={"status":"FAILED_RETAINED_FOR_RETRY",
                "error_type":type(exc).__name__,"event_type":"ALPHA_RESULT"}
    return result

def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--job-id", required=True); parser.add_argument("--worker-id", required=True)
    args = parser.parse_args(); store = default_store()
    os.environ["NEXUS_WORKER_ID"] = args.worker_id
    _lifecycle(args.job_id,"WORKER_PROCESS_STARTED",worker_id=args.worker_id,pid=os.getpid())
    try:
        result=run(args.job_id, args.worker_id, store)
        print(json.dumps({"job_id":args.job_id,"status":result.get("status"),
                          "receipt_ref":result.get("receipt_ref"),"result":result},default=str))
        # Capacity exhaustion is an expected, durably settled outcome: the job
        # has moved to its existing retryable state and released its lease.
        code=0 if result.get("status") in {"COMPLETED", "WAITING_FOR_CAPACITY"} else 1
        _lifecycle(args.job_id,"WORKER_PROCESS_EXIT",worker_id=args.worker_id,exit_code=code)
        return code
    except Exception as exc:
        active=ACTIVE_RESERVATIONS.pop(args.job_id,None)
        try:
            from nexus_agent_platform.worker_lifecycle import sanitize
            safe_error_summary = sanitize(exc, limit=500)
        except Exception:
            safe_error_summary = type(exc).__name__
        try:
            with _worker_cleanup_scope(args.job_id,args.worker_id,active[1] if active else None):
                job = store.get(args.job_id)
                if job and job.state in {"CLAIMED", "RUNNING"}:
                    store.transition(args.job_id, "FAILED_RETRYABLE", worker_id=args.worker_id,
                                     error_code=type(exc).__name__, error_summary=safe_error_summary)
                if active:
                    try:
                        from nexus_agent_platform.supabase_egress_guard import job_egress_snapshot
                        usage=job_egress_snapshot(args.job_id)
                        attempt_egress=_egress_delta(usage,active[2])
                        active[0].reconcile(active[1],{"requests":attempt_egress["request_count"],"bytes":attempt_egress["response_bytes"],"cost":0})
                    except Exception: pass
        except Exception as cleanup_exc:
            _lifecycle(args.job_id,"WORKER_CLEANUP_FAILED",worker_id=args.worker_id,
                       exception_type=type(cleanup_exc).__name__,error_code="EXACT_JOB_CLEANUP_FAILED")
        try:
            from nexus_agent_platform.worker_lifecycle import sanitize
            error_text=sanitize(exc,limit=500)
            _lifecycle(args.job_id,"WORKER_EXCEPTION",worker_id=args.worker_id,
                       exception_type=type(exc).__name__,summary=error_text)
            print(json.dumps({"job_id": args.job_id, "error_type": type(exc).__name__,
                              "error": error_text}), file=sys.stderr)
        except Exception:
            print(json.dumps({"job_id": args.job_id, "error_type": type(exc).__name__}), file=sys.stderr)
        _lifecycle(args.job_id,"WORKER_PROCESS_EXIT",worker_id=args.worker_id,exit_code=1)
        return 1

if __name__ == "__main__": raise SystemExit(main())
