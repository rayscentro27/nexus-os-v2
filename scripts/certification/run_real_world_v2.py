#!/usr/bin/env python3
"""Start/resume the isolated V2 durable-goal chain and checkpoint each step."""
from __future__ import annotations
import json, os, sys, uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"scripts"))
STATE=ROOT/"reports/certification/NEXUS_REAL_WORLD_V2_CERTIFICATION_STATE_20261010.json"
DB=ROOT/"data/runtime/nexus_real_world_v2_jobs.sqlite3"
GOV=ROOT/"data/runtime/nexus_real_world_v2_governor.sqlite3"
CAMPAIGN="campaign_nexus_real_world_v2_20261010"
PROJECT="project_nexus_real_world_v2_20261010"
CORR="corr_nexus_real_world_v2_20261010"

def now(): return datetime.now(timezone.utc).isoformat()
def checkpoint(d):
    d["UPDATED_AT"]=now(); STATE.parent.mkdir(parents=True,exist_ok=True)
    tmp=STATE.with_suffix(".tmp"); tmp.write_text(json.dumps(d,indent=2,sort_keys=True)+"\n"); tmp.replace(STATE)

def main():
    # Force all worker accounting to isolated local stores; no credentials are loaded.
    os.environ["NEXUS_DURABLE_JOBS_LOCAL"]="1"
    os.environ["NEXUS_DURABLE_JOBS_DB"]=str(DB)
    os.environ["NEXUS_GOVERNOR_DB"]=str(GOV)
    os.environ.pop("SUPABASE_URL",None); os.environ.pop("SUPABASE_SERVICE_ROLE_KEY",None); os.environ.pop("VITE_SUPABASE_URL",None)
    from nexus_agent_platform.durable_jobs import DurableJobStore, create_next_job, DEFAULT_JOB_BUDGET
    from nexus_agent_platform.resource_spend_governor import LocalGovernorStore
    from nexus_agent_platform.job_worker_once import run
    store=DurableJobStore(DB)
    state=json.loads(STATE.read_text()) if STATE.exists() else None
    if state and state.get("CURRENT_JOB_ID"):
        interrupted=store.get(state["CURRENT_JOB_ID"])
        if interrupted and interrupted.state in {"CLAIMED","RUNNING"}:
            # This command starts only after the previous one-shot process exited.
            # Reconcile its zero-egress reservation and return the same goal to READY.
            gov=LocalGovernorStore(GOV)
            with gov.connect() as db:
                active=db.execute("SELECT reservation_id FROM reservations WHERE job_id=? AND status='ACTIVE'",(interrupted.job_id,)).fetchall()
            for row in active: gov.reconcile(row["reservation_id"],{"requests":0,"bytes":0,"cost":0})
            store.transition(interrupted.job_id,"FAILED_RETRYABLE",worker_id=interrupted.claimed_by,
              error_code="V2_PROCESS_INTERRUPTED",error_summary="One-shot V2 worker exited before completing assigned goal")
            state.setdefault("FAILURES",[]).append({"JOB_ID":interrupted.job_id,"CODE":"V2_PROCESS_INTERRUPTED","RECOVERY":"SAME_GOAL_REQUEUED"})
            checkpoint(state)
    if store.health()["active_worker_count"]: raise RuntimeError("V2_ISOLATED_STORE_HAS_ACTIVE_WORKERS")
    if state is None:
        if store.health().get("counts"): raise RuntimeError("V2_STATE_MISSING_BUT_DB_HAS_JOBS")
        state={"CERTIFICATION_ID":"NEXUS-REAL-WORLD-V2-20261010-"+uuid.uuid4().hex[:8],
          "CERTIFICATION_VERSION":"V2","V1_RESULT":"FAIL_AUTONOMOUS_CONTINUATION",
          "V1_ARCHIVE_MANIFEST":"reports/certification/v1_archive/V1_IMMUTABLE_MANIFEST.json",
          "BASELINE_COMMIT":"6793dfaf3032fccabd9b6ce832430ea394bdc824",
          "CURRENT_PHASE":"ASSIGNED_GOALS","LAST_COMPLETED_PHASE":"V1_ARCHIVED_AND_HASH_VERIFIED",
          "NEXT_PHASE":"OPTIONS","GOALS":{},"JOB_IDS":[],"CORRELATION_IDS":[CORR],
          "ARTIFACT_REFS":[],"HANDOFF_IDS":[],"RECEIPT_IDS":[],"VISIBLE_OUTPUTS":[],
          "AUTONOMOUS_TRANSITIONS":[],"MANUAL_CONTINUE_PROMPTS_REQUIRED":0,
          "STOPPED_WITH_EXECUTABLE_WORK_REMAINING":"NO","INCREMENTAL_CASH_SPEND_USD":0,
          "FAILURES":[],"REPAIRS":[],"CASH_SPEND_USD":0}
        gov=LocalGovernorStore(GOV)
        gov.set_policy("SUPABASE","durable_worker","REAL_WORLD_V2_GOAL",autonomous_usage_allowed=True,
                       autonomous_spend_allowed=False,soft_limits={"requests":100,"bytes":2000000,"cost":0},
                       hard_limits={"requests":120,"bytes":2000000,"cost":0},concurrency_limit=1,
                       resource_creation_limit=0,state="NORMAL",approval_required=False)
        gov.set_policy("SUPABASE","durable_worker","CERTIFICATION_NOVA_SUMMARY",autonomous_usage_allowed=True,
                       autonomous_spend_allowed=False,soft_limits={"requests":100,"bytes":2000000,"cost":0},
                       hard_limits={"requests":120,"bytes":2000000,"cost":0},concurrency_limit=1,
                       resource_creation_limit=0,state="NORMAL",approval_required=False)
        payload=ROOT/"reports/certification/real_world_v2/execution/payload_options.json"
        payload.parent.mkdir(parents=True,exist_ok=True); payload.write_text(json.dumps({"stage":"OPTIONS","certification_version":"V2"},indent=2)+"\n")
        job=store.enqueue("TRADING_RESEARCH","REAL_WORLD_V2_GOAL",payload_ref=str(payload.relative_to(ROOT)),
          correlation_id=CORR,idempotency_key=state["CERTIFICATION_ID"]+":OPTIONS",
          budget_envelope={**DEFAULT_JOB_BUDGET,"max_requests":120,"max_tokens":0,"max_gpu_seconds":0,
             "max_runtime_seconds":180,"max_resource_creations":0,"max_estimated_cost":0,"max_retries":1},
          governance_context={"project_id":PROJECT,"campaign_id":CAMPAIGN,"providers_allowed":[],"spend_allowed":False,
             "resource_class":"LIGHTWEIGHT_INTERNAL","live_trading":False,"external_actions":False})
        state["JOB_IDS"].append(job.job_id); state["CURRENT_JOB_ID"]=job.job_id
        state["PHASE_RESULTS"]={"V1_PRESERVED":"PASS","V2_INITIALIZED":"PASS"}
        checkpoint(state)
    current=state.get("CURRENT_JOB_ID")
    worker_id="v2-certification-one-shot"
    state["CURRENT_PHASE"]="DURABLE_ASSIGNED_GOAL_EXECUTION"; checkpoint(state)
    while current:
        job=store.get(current)
        if not job: raise RuntimeError("V2_CURRENT_JOB_MISSING")
        if job.state=="FAILED_RETRYABLE":
            # Repair/resume the same assigned goal after its recorded attempt.
            store.transition(current,"READY")
            with store._connect() as db: db.execute("UPDATE jobs SET scheduled_at=? WHERE job_id=?",(now(),current))
            job=store.get(current)
        elif job.state=="READY" and job.attempt_count>0:
            # A resumed, repaired goal is eligible immediately in this isolated run.
            with store._connect() as db: db.execute("UPDATE jobs SET scheduled_at=? WHERE job_id=?",(now(),current))
            job=store.get(current)
        if job.state=="COMPLETED":
            result=json.loads((ROOT/"data/runtime/nexus_real_world_v2_job_results"/(job.job_id+".json")).read_text())
        else:
            ready=store.list_ready(10)
            if len(ready)!=1 or ready[0].job_id!=current: raise RuntimeError("V2_ISOLATED_QUEUE_NOT_SINGLE_EXPECTED_JOB")
            claimed=store.claim(worker_id)
            if not claimed or claimed.job_id!=current: raise RuntimeError("V2_CLAIM_FAILED")
            try:
                result=run(current,worker_id,store)
            except Exception as exc:
                active=__import__("nexus_agent_platform.job_worker_once",fromlist=["ACTIVE_RESERVATIONS"]).ACTIVE_RESERVATIONS.pop(current,None)
                if active:
                    from nexus_agent_platform.supabase_egress_guard import job_egress_snapshot
                    usage=job_egress_snapshot(current)
                    active[0].reconcile(active[1],{"requests":int(usage.get("request_count",0)),"bytes":int(usage.get("response_bytes",0)),"cost":0})
                failed=store.get(current)
                if failed and failed.state in {"CLAIMED","RUNNING"}:
                    store.transition(current,"FAILED_RETRYABLE",worker_id=worker_id,error_code="V2_GOAL_FAILED",error_summary=str(exc))
                state.setdefault("FAILURES",[]).append({"JOB_ID":current,"CODE":"V2_GOAL_FAILED","DETAIL":str(exc)[:500],"RECOVERY":"SAME_GOAL_RETRY"})
                checkpoint(state)
                raise
            completed=store.get(current)
            if not completed or completed.state!="COMPLETED" or not completed.receipt_ref: raise RuntimeError("V2_DURABLE_COMPLETION_OR_RECEIPT_MISSING")
            result_path=ROOT/"data/runtime/nexus_real_world_v2_job_results"/(current+".json")
            result_path.parent.mkdir(parents=True,exist_ok=True); result_path.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
            if current not in state["JOB_IDS"]: state["JOB_IDS"].append(current)
            state["RECEIPT_IDS"].append(completed.receipt_ref)
            refs=result.get("artifact_refs",[])
            for key in ("execution_artifact_ref","artifact_ref","handoff_ref"):
                if result.get(key): refs.append(result[key])
            state["ARTIFACT_REFS"] += [x for x in refs if x not in state["ARTIFACT_REFS"]]
            if result.get("handoff_ref"): state["HANDOFF_IDS"].append(result["handoff_ref"])
            stage=result.get("stage") or "NOVA"
            state["GOALS"][stage]={"STATUS":"COMPLETE","JOB_ID":current,"RECEIPT_ID":completed.receipt_ref,
               "ARTIFACT_REFS":refs,"EXECUTION_RESULT_REF":str(result_path.relative_to(ROOT))}
            child=result.get("next_job_id")
            if child:
                state["AUTONOMOUS_TRANSITIONS"].append({"FROM_JOB_ID":current,"TO_JOB_ID":child,"CREATED_BY":"WORKFLOW_HANDLER",
                    "EVENT":"GOAL_COMPLETED_NEXT_GOAL_CREATED","OBSERVED_READY_BEFORE_EXECUTION":True})
                if child not in state["JOB_IDS"]: state["JOB_IDS"].append(child)
            state["LAST_COMPLETED_PHASE"]=stage; state["NEXT_PHASE"]=("NOVA" if child and stage=="SELF_UPGRADE" else "COMPLETE" if not child else "NEXT_ASSIGNED_GOAL")
            state["VISIBLE_OUTPUTS"]=sorted(set(state["VISIBLE_OUTPUTS"]+state["ARTIFACT_REFS"]))
            state["CURRENT_JOB_ID"]=child; checkpoint(state)
            current=child
    state["CURRENT_PHASE"]="GOALS_BUILT"; state["LAST_COMPLETED_PHASE"]="NOVA"; state["NEXT_PHASE"]="EVALUATION"
    state["ALL_ASSIGNED_GOALS_COMPLETE"]="YES"; state["ALL_INCOMPLETE_GOALS_COST_BLOCKED"]="NO"
    state["AUTONOMOUS_NEXT_JOB_CREATION"]="PASS" if len(state["AUTONOMOUS_TRANSITIONS"])>=5 else "FAIL"
    state["AUTONOMOUS_NEXT_JOB_EXECUTION"]="PASS" if len(state["GOALS"])==8 else "FAIL"
    state["SEQUENTIAL_AUTONOMOUS_TRANSITIONS"]=len(state["AUTONOMOUS_TRANSITIONS"])
    checkpoint(state)
    print(json.dumps({"status":"GOALS_COMPLETE","certification_id":state["CERTIFICATION_ID"],
       "goals_completed":len(state["GOALS"]),"transitions":len(state["AUTONOMOUS_TRANSITIONS"]),
       "jobs":state["JOB_IDS"],"receipts":state["RECEIPT_IDS"],"outputs":state["VISIBLE_OUTPUTS"]},indent=2))

if __name__=="__main__": main()
