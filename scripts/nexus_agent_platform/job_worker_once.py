#!/usr/bin/env python3
"""One bounded job process; adapters reuse existing Research/feeder entry points."""
from __future__ import annotations
import argparse
import json
import subprocess
import sys
import os
import time
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

def _result_json(stdout):
    try: return json.loads(stdout)
    except (ValueError,TypeError): return {}

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

def run(job_id: str, worker_id: str, store) -> dict:
    job = store.get(job_id)
    if not job or job.state != "CLAIMED" or job.claimed_by != worker_id:
        raise JobError("CLAIM_NOT_OWNED")
    store.transition(job_id, "RUNNING", worker_id=worker_id)
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
    os.environ["NEXUS_JOB_PAYLOAD_REF"] = job.payload_ref or ""
    from nexus_agent_platform.supabase_egress_guard import job_egress_snapshot
    prior_egress=job_egress_snapshot(job.job_id)
    remaining_requests=max(0,int(budget["max_requests"])-int(prior_egress.get("request_count",0)))
    remaining_bytes=max(0,int(budget["max_response_bytes"])-int(prior_egress.get("response_bytes",0)))
    from nexus_agent_platform.resource_spend_governor import default_store as default_governor_store, GovernanceDenied
    governor=default_governor_store()
    try:
        if remaining_requests < 1 or remaining_bytes < 1:
            raise GovernanceDenied("HARD_STOP","JOB_BUDGET_EXHAUSTED")
        reservation=governor.reserve("SUPABASE","durable_worker",job.job_type,job.job_id,
            {"requests":remaining_requests,"bytes":remaining_bytes,"cost":0},
            purpose=f"durable-job-envelope:attempt-{job.attempt_count}")
    except GovernanceDenied as exc:
        # A transient quota/concurrency throttle is a defer condition, not a
        # terminal workflow blocker. Persist bounded backoff so the durable
        # dispatcher can retry after capacity returns.
        state = "FAILED_RETRYABLE" if exc.state == "THROTTLED" else "BLOCKED"
        store.transition(job_id,state,worker_id=worker_id,error_code=exc.code,error_summary=exc.state)
        _footprint(job,store,started_wall,started_cpu,state,exc.code)
        return {"status":state,"job_type":job.job_type,"reason":exc.code,"governor_state":exc.state}
    ACTIVE_RESERVATIONS[job_id]=(governor,reservation["reservation_id"])
    route = handler_route(job.job_type)
    if route == "INTERNAL_CANARY":
        from nexus_agent_platform.internal_canary import execute_internal_canary
        result = execute_internal_canary(job)
    elif route == "MARKETING_CREATIVE":
        from nexus_agent_platform.marketing_creative_workflow import handle_job
        result = handle_job(job, store)
    elif route == "COMPANY_CERTIFICATION":
        from nexus_agent_platform.company_certification_workflow import handle_job
        result = handle_job(job, store)
    elif route == "RESEARCH":
        # The existing dispatched Research runner remains the business-logic owner.
        # Payload references are resolved by that runner in a subsequent adapter call.
        if not job.payload_ref:
            result = {"status": "BLOCKED", "reason": "PAYLOAD_REFERENCE_REQUIRED", "job_type": job.job_type}
            store.transition(job_id, "BLOCKED", worker_id=worker_id)
            return result
        os.environ["NEXUS_WORK_ID"] = job.payload_ref
        completed = subprocess.run([sys.executable, str(ROOT / "scripts/research/run_dispatched_research_job.py"), "--execution-id", job.job_id],
                                   cwd=ROOT, capture_output=True, text=True, timeout=900, check=False)
        if completed.returncode:
            raise RuntimeError(f"RESEARCH_EXIT_{completed.returncode}: {completed.stderr[-300:]}")
        if job.job_type=="RESEARCH_GAP_VERIFY":
            from nexus_agent_platform.feeder_runtime import continue_research_gap
            progression=continue_research_gap(job.payload_ref)
        elif job.job_type=="MARKETING_RESEARCH_GAP_VERIFY":
            from nexus_agent_platform.marketing_creative_workflow import research_completed_event
            progression=research_completed_event(job,result_ref=f"research-result:{job.payload_ref}")
        else: progression={"status":"NO_AUTOMATIC_NEXT_STAGE"}
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
    from nexus_agent_platform.supabase_egress_guard import job_egress_snapshot, JOB_MAX_RESPONSE_BYTES
    egress = job_egress_snapshot(job.job_id)
    if egress.get("budget_exceeded") or egress.get("response_bytes", 0) > min(JOB_MAX_RESPONSE_BYTES,int(budget["max_response_bytes"])):
        raise JobError("JOB_EGRESS_BUDGET_EXCEEDED")
    governor.reconcile(reservation["reservation_id"],{"requests":int(egress.get("request_count",0)),"bytes":int(egress.get("response_bytes",0)),"cost":0})
    ACTIVE_RESERVATIONS.pop(job_id,None)
    result["egress"] = egress
    if time.time()-started_wall > budget["max_runtime_seconds"]: raise JobError("JOB_RUNTIME_BUDGET_EXCEEDED")
    if result.get("status") == "BLOCKED":
        store.transition(job_id,"BLOCKED",worker_id=worker_id,error_code=result.get("reason","WORKFLOW_BLOCKED"),error_summary=json.dumps(result.get("missing",[]))[:400])
        try:
            governor.record_incident("NEXUS_WORKFLOW", job_id, result.get("reason", "WORKFLOW_BLOCKED"),
                                     "BLOCKED_BEFORE_EXTERNAL_SIDE_EFFECT", project_id="NEXUS")
        except Exception:
            pass
        _footprint(job,store,started_wall,started_cpu,"BLOCKED",result.get("reason"))
        return result
    # Persist immutable execution evidence before marking the durable job
    # complete. A footprint outage must leave the job retryable instead of
    # creating a terminal row with no worker record.
    from nexus_agent_platform.durable_jobs import _canonical_hash
    expected_result_hash=_canonical_hash(result)
    footprint=_footprint(job,store,started_wall,started_cpu,"COMPLETED",receipt_hash=expected_result_hash)
    if not footprint:
        raise JobError("COMPLETION_FOOTPRINT_REQUIRED")
    receipt=store.complete(job_id, worker_id, result)
    if route == "MARKETING_CREATIVE":
        from nexus_agent_platform.marketing_creative_workflow import record_job_receipt
        record_job_receipt(job, receipt)
    elif route == "COMPANY_CERTIFICATION":
        from nexus_agent_platform.company_certification_workflow import record_receipt
        record_receipt(job, receipt, result)
    result["receipt_ref"]=receipt
    return result

def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--job-id", required=True); parser.add_argument("--worker-id", required=True)
    args = parser.parse_args(); store = default_store()
    try: run(args.job_id, args.worker_id, store); return 0
    except Exception as exc:
        job = store.get(args.job_id)
        active=ACTIVE_RESERVATIONS.pop(args.job_id,None)
        if active:
            try:
                from nexus_agent_platform.supabase_egress_guard import job_egress_snapshot
                usage=job_egress_snapshot(args.job_id)
                active[0].reconcile(active[1],{"requests":int(usage.get("request_count",0)),"bytes":int(usage.get("response_bytes",0)),"cost":0})
            except Exception: pass
        if job and job.state in {"CLAIMED", "RUNNING"}:
            try: store.transition(args.job_id, "FAILED_RETRYABLE", worker_id=args.worker_id, error_code="WORKER_FAILED", error_summary=str(exc))
            except Exception: pass
            _footprint(job,store,time.time(),time.process_time(),"FAILED_RETRYABLE",str(exc))
        print(json.dumps({"job_id": args.job_id, "error": str(exc)[:500]}), file=sys.stderr)
        return 1

if __name__ == "__main__": raise SystemExit(main())
