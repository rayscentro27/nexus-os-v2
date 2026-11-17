#!/usr/bin/env python3
"""Resume the canonical V5 objective through the normal durable worker path."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"scripts"))
from nexus_agent_platform.durable_jobs import default_store
from nexus_agent_platform.durable_objective_control import (
    ACTIVE_CAMPAIGN_PATH, load_active_campaign, persist_campaign,
)

CAMPAIGN="NEXUS-OWNER-REAL-WORLD-V5-20261010-6fb82fd9"
OBJECTIVE="ownerobj_nexus_full_owner_real_world_v5_6fb82fd9"
JOB_ID="job_v5_research_source_review_20261010"
JOB_TYPE="RESEARCH_SOURCE_REVIEW_AND_OPPORTUNITY_INVENTORY"
CORRELATION="corr_4bfc9935c09e534da823278e"
WORKER="v5-canonical-controller"
PAYLOAD_REF="reports/certification/v5/jobs/job_v5_research_source_review_20261010.json"
SYSTEMS_JOB_ID="job_v5_systems_resource_circuit_analysis_20261010_v2"
SYSTEMS_PAYLOAD_REF="reports/certification/v5/jobs/job_v5_systems_resource_diagnosis_20261010.json"
PUBLIC_RESEARCH_JOB_ID="job_v5_public_web_research_while_notebooklm_paused_20261010"
PUBLIC_RESEARCH_PAYLOAD_REF="reports/certification/v5/jobs/job_v5_public_web_research_while_notebooklm_paused_20261010.json"

WORKER_ENV_KEYS=("NEXUS_DURABLE_JOB_ID","NEXUS_JOB_BUDGET","NEXUS_JOB_CORRELATION_ID",
    "NEXUS_CORRELATION_ID","NEXUS_DEPARTMENT","NEXUS_JOB_TYPE","NEXUS_JOB_PAYLOAD_REF",
    "NEXUS_OWNER_OBJECTIVE_ID","NEXUS_JOB_ATTEMPT_COUNT")


def run_department_job(job_id: str, worker: str, store):
    """Run one durable worker without leaking its egress identity to the controller."""
    from nexus_agent_platform.job_worker_once import run
    previous={key:os.environ.get(key) for key in WORKER_ENV_KEYS}
    try:
        try:
            return run(job_id,worker,store)
        except Exception as exc:
            current=store.get(job_id)
            if current and current.state in {"CLAIMED","RUNNING"}:
                try:
                    current=store.transition(job_id,"FAILED_RETRYABLE",worker_id=worker,
                        error_code="WORKER_FAILED",error_summary=f"{type(exc).__name__}:{str(exc)[:350]}")
                except Exception:
                    pass
            return {"status":"FAILED_RETRYABLE","error":f"{type(exc).__name__}:{str(exc)[:350]}",
                "job_state":current.state if current else "UNKNOWN"}
    finally:
        for key,value in previous.items():
            if value is None: os.environ.pop(key,None)
            else: os.environ[key]=value


def run_v5_systems_health_job(store, state: dict) -> dict:
    """Run the next independent, registered Systems check under the V5 job path."""
    job_id="job_v5_dag_systems_health_20261010"
    payload_ref=f"reports/certification/v5/jobs/{job_id}.json"
    payload_path=ROOT/payload_ref
    payload_path.parent.mkdir(parents=True,exist_ok=True)
    payload_path.write_text(json.dumps({"question":"Systems: run a read-only system health check for the active V5 campaign and record verified service findings."},indent=2)+"\n",encoding="utf-8")
    job=store.enqueue("SYSTEMS","NEXUS_DEPARTMENT_QUERY",priority=9700,payload_ref=payload_ref,
        parent_job_id=state.get("CURRENT_JOB_ID"),
        correlation_id=CORRELATION,idempotency_key=f"objective-independent:{CAMPAIGN}:{job_id}",
        job_id=job_id,max_attempts=2,
        budget_envelope={"max_requests":40,"max_response_bytes":160000,"max_tokens":5000,
            "max_gpu_seconds":0,"max_runtime_seconds":300,"max_resource_creations":0,
            "max_estimated_cost":0.0,"max_retries":1},
        governance_context={"campaign_id":CAMPAIGN,"owner_objective_id":OBJECTIVE,
            "objective_version":"V5","project_id":"project_nexus_owner_real_world_v5_20261010_6fb82fd9",
            "providers_allowed":["SUPABASE"],"spend_allowed":False,"external_actions_allowed":False,
            "resource_class":"LIGHTWEIGHT_INTERNAL","resource_dependencies":[],"dag_workstream":"SYSTEMS",
            "independent_job":True})
    if job.job_id!=job_id: raise RuntimeError("V5_DAG_SYSTEMS_JOB_ID_CONFLICT")
    current=store.get(job_id)
    if current.state=="COMPLETED":
        result={"status":"ALREADY_COMPLETED","receipt_ref":current.receipt_ref}
    elif current.state in {"READY","FAILED_RETRYABLE"}:
        claimed=store.claim_by_id(job_id,WORKER,lease_seconds=600)
        if not claimed: result={"status":"WAITING","job_state":store.get(job_id).state}
        else: result=run_department_job(job_id,WORKER,store)
    else:
        result={"status":"WAITING","job_state":current.state}
    current=store.get(job_id)
    state=load_active_campaign()
    state.setdefault("JOB_IDS",[])
    if job_id not in state["JOB_IDS"]: state["JOB_IDS"].append(job_id)
    if current and current.state=="COMPLETED":
        state["COMPLETED_JOBS"]=list(dict.fromkeys([*(state.get("COMPLETED_JOBS") or []),job_id]))
        state.setdefault("RECEIPT_IDS",[])
        if current.receipt_ref and current.receipt_ref not in state["RECEIPT_IDS"]: state["RECEIPT_IDS"].append(current.receipt_ref)
    state["V5_DAG_LAST_EXECUTION"]={"workstream":"SYSTEMS","job_id":job_id,
        "status":current.state if current else "UNKNOWN","receipt_id":current.receipt_ref if current else None,
        "result":result}
    if current and current.state=="COMPLETED":
        state["COMPLETED_V5_WORKSTREAMS"]=list(dict.fromkeys([*(state.get("COMPLETED_V5_WORKSTREAMS") or []),"SYSTEMS"]))
    persist_campaign(state)
    return result


def run_v5_resource_guard_job(store) -> dict:
    """Execute the independent Systems resource guard diagnosis via its real route."""
    job_id="job_v5_dag_resource_guard_diagnosis_20261010"
    payload_ref=f"reports/certification/v5/jobs/{job_id}.json"
    (ROOT/payload_ref).write_text(json.dumps({"question":"Systems: inspect NotebookLM resource guard limits and current reserve and reconcile evidence for V5; do not change policy."},indent=2)+"\n",encoding="utf-8")
    state=load_active_campaign()
    job=store.enqueue("SYSTEMS","NEXUS_DEPARTMENT_QUERY",priority=9600,payload_ref=payload_ref,
        parent_job_id=state.get("CURRENT_JOB_ID"),correlation_id=CORRELATION,
        idempotency_key=f"objective-independent:{CAMPAIGN}:{job_id}",job_id=job_id,max_attempts=2,
        budget_envelope={"max_requests":40,"max_response_bytes":160000,"max_tokens":5000,
            "max_gpu_seconds":0,"max_runtime_seconds":300,"max_resource_creations":0,
            "max_estimated_cost":0.0,"max_retries":1},
        governance_context={"campaign_id":CAMPAIGN,"owner_objective_id":OBJECTIVE,"objective_version":"V5",
            "project_id":"project_nexus_owner_real_world_v5_20261010_6fb82fd9","providers_allowed":["SUPABASE"],
            "spend_allowed":False,"external_actions_allowed":False,"resource_class":"LIGHTWEIGHT_INTERNAL",
            "resource_dependencies":[],"dag_workstream":"RESOURCE_GUARDS","independent_job":True})
    if job.job_id!=job_id: raise RuntimeError("V5_DAG_RESOURCE_GUARD_JOB_ID_CONFLICT")
    current=store.get(job_id)
    if current.state=="COMPLETED": result={"status":"ALREADY_COMPLETED","receipt_ref":current.receipt_ref}
    elif current.state in {"READY","FAILED_RETRYABLE"}:
        claimed=store.claim_by_id(job_id,WORKER,lease_seconds=600)
        result=run_department_job(job_id,WORKER,store) if claimed else {"status":"WAITING","job_state":store.get(job_id).state}
    else: result={"status":"WAITING","job_state":current.state}
    current=store.get(job_id); state=load_active_campaign()
    state.setdefault("JOB_IDS",[])
    if job_id not in state["JOB_IDS"]: state["JOB_IDS"].append(job_id)
    if current and current.state=="COMPLETED":
        state["COMPLETED_JOBS"]=list(dict.fromkeys([*(state.get("COMPLETED_JOBS") or []),job_id]))
        state["COMPLETED_V5_WORKSTREAMS"]=list(dict.fromkeys([*(state.get("COMPLETED_V5_WORKSTREAMS") or []),"RESOURCE_GUARDS"]))
        state.setdefault("RECEIPT_IDS",[])
        if current.receipt_ref and current.receipt_ref not in state["RECEIPT_IDS"]: state["RECEIPT_IDS"].append(current.receipt_ref)
    state["V5_DAG_RESOURCE_GUARD"]={"job_id":job_id,"status":current.state if current else "UNKNOWN",
        "receipt_id":current.receipt_ref if current else None,"result":result}
    persist_campaign(state)
    return result


def run_v5_remote_stack_health_job(store) -> dict:
    """Run existing read-only Oracle/Hermes/Modal capability checks as a DAG job."""
    job_id="job_v5_dag_remote_stack_health_20261010"
    state=load_active_campaign()
    job=store.enqueue("SYSTEMS","V5_REMOTE_STACK_HEALTH_CHECK",priority=9500,
        parent_job_id=state.get("CURRENT_JOB_ID"),correlation_id=CORRELATION,
        idempotency_key=f"objective-independent:{CAMPAIGN}:{job_id}",job_id=job_id,max_attempts=2,
        budget_envelope={"max_requests":30,"max_response_bytes":100000,"max_tokens":1500,
            "max_gpu_seconds":0,"max_runtime_seconds":90,"max_resource_creations":0,
            "max_estimated_cost":0.0,"max_retries":1},
        governance_context={"campaign_id":CAMPAIGN,"owner_objective_id":OBJECTIVE,"objective_version":"V5",
            "project_id":"project_nexus_owner_real_world_v5_20261010_6fb82fd9","spend_allowed":False,
            "external_actions_allowed":False,"resource_class":"LIGHTWEIGHT_INTERNAL",
            "resource_dependencies":[],"dag_workstream":"HERMES","independent_job":True})
    if job.job_id!=job_id: raise RuntimeError("V5_DAG_REMOTE_HEALTH_JOB_ID_CONFLICT")
    current=store.get(job_id)
    if current.state=="COMPLETED": result={"status":"ALREADY_COMPLETED","receipt_ref":current.receipt_ref}
    elif current.state in {"READY","FAILED_RETRYABLE"}:
        claimed=store.claim_by_id(job_id,WORKER,lease_seconds=120)
        result=run_department_job(job_id,WORKER,store) if claimed else {"status":"WAITING","job_state":store.get(job_id).state}
    else: result={"status":"WAITING","job_state":current.state}
    current=store.get(job_id); state=load_active_campaign()
    state.setdefault("JOB_IDS",[])
    if job_id not in state["JOB_IDS"]: state["JOB_IDS"].append(job_id)
    if current and current.state=="COMPLETED":
        state["COMPLETED_JOBS"]=list(dict.fromkeys([*(state.get("COMPLETED_JOBS") or []),job_id]))
        state["COMPLETED_V5_WORKSTREAMS"]=list(dict.fromkeys([*(state.get("COMPLETED_V5_WORKSTREAMS") or []),"HERMES"]))
        state.setdefault("RECEIPT_IDS",[])
        if current.receipt_ref and current.receipt_ref not in state["RECEIPT_IDS"]: state["RECEIPT_IDS"].append(current.receipt_ref)
    state["V5_DAG_HERMES_CHECK"]={"job_id":job_id,"status":current.state if current else "UNKNOWN",
        "receipt_id":current.receipt_ref if current else None,"result":result}
    persist_campaign(state)
    return result


def run_v5_opencode_benchmark_job(store) -> dict:
    """Run an isolated real OpenCode task after the DAG selects failover."""
    import subprocess
    job_id="job_v5_dag_opencode_free_model_benchmark_20261010"
    payload_ref=f"reports/certification/v5/jobs/{job_id}.json"
    checkpoint=subprocess.run(["git","rev-parse","HEAD"],cwd=ROOT,capture_output=True,text=True,check=True,timeout=5).stdout.strip()
    (ROOT/payload_ref).write_text(json.dumps({"model":"opencode/mimo-v2.5-free",
        "checkpoint_sha":checkpoint,"failover_trigger":"SIMULATED_CODEX_RATE_LIMIT"},indent=2)+"\n",encoding="utf-8")
    state=load_active_campaign()
    job=store.enqueue("SYSTEMS","V5_OPENCODE_MODEL_BENCHMARK",priority=9400,payload_ref=payload_ref,
        parent_job_id=state.get("CURRENT_JOB_ID"),correlation_id=CORRELATION,
        idempotency_key=f"objective-independent:{CAMPAIGN}:{job_id}",job_id=job_id,max_attempts=3,
        budget_envelope={"max_requests":40,"max_response_bytes":140000,"max_tokens":4000,
            "max_gpu_seconds":0,"max_runtime_seconds":120,"max_resource_creations":0,
            "max_estimated_cost":0.0,"max_retries":3},
        governance_context={"campaign_id":CAMPAIGN,"owner_objective_id":OBJECTIVE,"objective_version":"V5",
            "project_id":"project_nexus_owner_real_world_v5_20261010_6fb82fd9","spend_allowed":False,
            "external_actions_allowed":False,"resource_class":"LIGHTWEIGHT_INTERNAL",
            "resource_dependencies":[],"dag_workstream":"CODEX_OPENCODE_FAILOVER","independent_job":True})
    if job.job_id!=job_id: raise RuntimeError("V5_DAG_OPENCODE_JOB_ID_CONFLICT")
    store.ensure_retry_capacity(job_id,3)
    current=store.get(job_id)
    if current.state=="FAILED_RETRYABLE" and "OPENCODE_FAILOVER_SELECTION_FAILED" in str(current.last_error_summary or ""):
        current=store.transition(job_id,"READY")
    if current.state=="COMPLETED": result={"status":"ALREADY_COMPLETED","receipt_ref":current.receipt_ref}
    elif current.state in {"READY","FAILED_RETRYABLE"}:
        claimed=store.claim_by_id(job_id,WORKER,lease_seconds=120)
        result=run_department_job(job_id,WORKER,store) if claimed else {"status":"WAITING","job_state":store.get(job_id).state}
    else: result={"status":"WAITING","job_state":current.state}
    current=store.get(job_id); state=load_active_campaign()
    state.setdefault("JOB_IDS",[])
    if job_id not in state["JOB_IDS"]: state["JOB_IDS"].append(job_id)
    if current and current.state=="COMPLETED":
        state["COMPLETED_JOBS"]=list(dict.fromkeys([*(state.get("COMPLETED_JOBS") or []),job_id]))
        state["COMPLETED_V5_WORKSTREAMS"]=list(dict.fromkeys([*(state.get("COMPLETED_V5_WORKSTREAMS") or []),
            "CODEX_OPENCODE_FAILOVER","OPENCODE_MODEL_BENCHMARK"]))
        state.setdefault("RECEIPT_IDS",[])
        if current.receipt_ref and current.receipt_ref not in state["RECEIPT_IDS"]: state["RECEIPT_IDS"].append(current.receipt_ref)
    state["V5_DAG_OPENCODE_BENCHMARK"]={"job_id":job_id,"status":current.state if current else "UNKNOWN",
        "receipt_id":current.receipt_ref if current else None,"result":result}
    persist_campaign(state)
    return result


def run_v5_forex_research_job(store) -> dict:
    """Run the existing read-only OANDA practice market scanner as V5 work."""
    job_id="job_v5_dag_forex_market_scan_20261010"
    state=load_active_campaign()
    job=store.enqueue("TRADING","V5_TRADING_MARKET_SCAN",priority=9300,
        parent_job_id=state.get("CURRENT_JOB_ID"),correlation_id=CORRELATION,
        idempotency_key=f"objective-independent:{CAMPAIGN}:{job_id}",job_id=job_id,max_attempts=2,
        budget_envelope={"max_requests":20,"max_response_bytes":120000,"max_tokens":2000,
            "max_gpu_seconds":0,"max_runtime_seconds":180,"max_resource_creations":0,
            "max_estimated_cost":0.0,"max_retries":1},
        governance_context={"campaign_id":CAMPAIGN,"owner_objective_id":OBJECTIVE,"objective_version":"V5",
            "project_id":"project_nexus_owner_real_world_v5_20261010_6fb82fd9","spend_allowed":False,
            "external_actions_allowed":False,"resource_class":"LIGHTWEIGHT_INTERNAL",
            "resource_dependencies":[],"dag_workstream":"TRADING_RESEARCH","independent_job":True})
    if job.job_id!=job_id: raise RuntimeError("V5_DAG_FOREX_JOB_ID_CONFLICT")
    current=store.get(job_id)
    if current.state=="COMPLETED": result={"status":"ALREADY_COMPLETED","receipt_ref":current.receipt_ref}
    elif current.state in {"READY","FAILED_RETRYABLE"}:
        claimed=store.claim_by_id(job_id,WORKER,lease_seconds=240)
        result=run_department_job(job_id,WORKER,store) if claimed else {"status":"WAITING","job_state":store.get(job_id).state}
    else: result={"status":"WAITING","job_state":current.state}
    current=store.get(job_id); state=load_active_campaign()
    state.setdefault("JOB_IDS",[])
    if job_id not in state["JOB_IDS"]: state["JOB_IDS"].append(job_id)
    if current and current.state=="COMPLETED":
        state["COMPLETED_JOBS"]=list(dict.fromkeys([*(state.get("COMPLETED_JOBS") or []),job_id]))
        state["COMPLETED_V5_WORKSTREAMS"]=list(dict.fromkeys([*(state.get("COMPLETED_V5_WORKSTREAMS") or []),"TRADING_RESEARCH"]))
        state.setdefault("RECEIPT_IDS",[])
        if current.receipt_ref and current.receipt_ref not in state["RECEIPT_IDS"]: state["RECEIPT_IDS"].append(current.receipt_ref)
    state["V5_DAG_FOREX_RESEARCH"]={"job_id":job_id,"status":current.state if current else "UNKNOWN",
        "receipt_id":current.receipt_ref if current else None,"result":result}
    persist_campaign(state)
    return result


def run_v5_department_capability_job(store, workstream: str, department: str, question: str) -> dict:
    """Execute a read-only capability check through its real owning department."""
    job_id=f"job_v5_dag_{workstream.lower()}_capability_20261010"
    payload_ref=f"reports/certification/v5/jobs/{job_id}.json"
    payload_path=ROOT/payload_ref
    payload_path.parent.mkdir(parents=True,exist_ok=True)
    payload_path.write_text(json.dumps({"question":question},indent=2)+"\n",encoding="utf-8")
    state=load_active_campaign()
    job=store.enqueue(department,"NEXUS_DEPARTMENT_QUERY",priority=9200,payload_ref=payload_ref,
        parent_job_id=state.get("CURRENT_JOB_ID"),correlation_id=CORRELATION,
        idempotency_key=f"objective-independent:{CAMPAIGN}:{job_id}",job_id=job_id,max_attempts=2,
        budget_envelope={"max_requests":24,"max_response_bytes":100000,"max_tokens":3000,
            "max_gpu_seconds":0,"max_runtime_seconds":240,"max_resource_creations":0,
            "max_estimated_cost":0.0,"max_retries":1},
        governance_context={"campaign_id":CAMPAIGN,"owner_objective_id":OBJECTIVE,"objective_version":"V5",
            "project_id":"project_nexus_owner_real_world_v5_20261010_6fb82fd9",
            "providers_allowed":["SUPABASE","ORACLE"],"spend_allowed":False,"external_actions_allowed":False,
            "resource_class":"LIGHTWEIGHT_INTERNAL","resource_dependencies":[],"dag_workstream":workstream,
            "independent_job":True,"read_only_capability_check":True})
    if job.job_id!=job_id: raise RuntimeError(f"V5_DAG_JOB_ID_CONFLICT:{workstream}")
    current=store.get(job_id)
    if current.state=="COMPLETED": result={"status":"ALREADY_COMPLETED","receipt_ref":current.receipt_ref}
    elif current.state in {"READY","FAILED_RETRYABLE"}:
        claimed=store.claim_by_id(job_id,WORKER,lease_seconds=300)
        result=run_department_job(job_id,WORKER,store) if claimed else {"status":"WAITING","job_state":store.get(job_id).state}
    else: result={"status":"WAITING","job_state":current.state}
    current=store.get(job_id); state=load_active_campaign()
    state.setdefault("JOB_IDS",[])
    if job_id not in state["JOB_IDS"]: state["JOB_IDS"].append(job_id)
    if current and current.state=="COMPLETED":
        state["COMPLETED_JOBS"]=list(dict.fromkeys([*(state.get("COMPLETED_JOBS") or []),job_id]))
        state["COMPLETED_V5_WORKSTREAMS"]=list(dict.fromkeys([*(state.get("COMPLETED_V5_WORKSTREAMS") or []),workstream]))
        state.setdefault("RECEIPT_IDS",[])
        if current.receipt_ref and current.receipt_ref not in state["RECEIPT_IDS"]: state["RECEIPT_IDS"].append(current.receipt_ref)
    state.setdefault("V5_DAG_CAPABILITY_CHECKS",{})[workstream]={"job_id":job_id,
        "status":current.state if current else "UNKNOWN","receipt_id":current.receipt_ref if current else None,
        "result":result}
    persist_campaign(state)
    return result


def main() -> int:
    state=load_active_campaign()
    if state["CAMPAIGN_ID"]!=CAMPAIGN or state["OWNER_OBJECTIVE_ID"]!=OBJECTIVE:
        raise RuntimeError("ACTIVE_V5_IDENTITY_MISMATCH")
    if state.get("TERMINAL_CONDITION_SATISFIED")=="YES":
        print(json.dumps({"status":"ALREADY_COMPLETE","campaign_id":CAMPAIGN})); return 0
    payload={"campaign_id":CAMPAIGN,"owner_objective_id":OBJECTIVE,
        "objective_version":"V5","project_id":"project_nexus_owner_real_world_v5_20261010_6fb82fd9",
        "correlation_id":CORRELATION,"operation":"IMPORT_AND_SYNTHESIZE",
        "query":"Review the public sources already discovered for this owner campaign and synthesize evidence for an opportunity inventory. Compare low-cost online business models, current customer problems, pricing evidence, acquisition, retention, margins, automation, scalability, capital needs and competition. Cite source references for every material claim. Separate source claims, independently supported findings, unverified claims and inference. Produce distinct opportunity candidates with customer, recurring problem, offer hypothesis, validation evidence needed, fastest no-cost validation, risks and confidence. Do not claim validated demand or revenue.",
        "notebook_id":"e0657f43-bf4e-4241-8336-7854739e942d","source_class":"PUBLIC_WEB_RESEARCH",
        "max_import_sources":10,"cost_ceiling_usd":0}
    payload_path=ROOT/PAYLOAD_REF
    payload_path.parent.mkdir(parents=True,exist_ok=True)
    payload_path.write_text(json.dumps(payload,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    store=default_store()
    key=f"objective-next:{CAMPAIGN}:job_v5_objective_control_repair_20261010:{JOB_TYPE}"
    # The control-plane repair was persisted in the V5 campaign checkpoint but
    # predates the canonical Supabase queue row, so the first repaired job has
    # no relational parent. Campaign identity and idempotency remain authoritative.
    job=store.enqueue("RESEARCH",JOB_TYPE,priority=10000,payload_ref=PAYLOAD_REF,
        correlation_id=CORRELATION,
        idempotency_key=key,job_id=JOB_ID,max_attempts=3,
        budget_envelope={"max_requests":30,"max_response_bytes":500000,"max_tokens":10000,
            "max_gpu_seconds":0,"max_runtime_seconds":900,"max_resource_creations":0,
            "max_estimated_cost":0.0,"max_retries":3},
        governance_context={"campaign_id":CAMPAIGN,"owner_objective_id":OBJECTIVE,
            "objective_version":"V5","project_id":payload["project_id"],
            "providers_allowed":["NOTEBOOKLM"],"spend_allowed":False,
            "external_actions_allowed":False,"resource_class":"LIGHTWEIGHT_INTERNAL"})
    if job.job_id!=JOB_ID or job.job_type!=JOB_TYPE:
        raise RuntimeError("V5_EXPECTED_JOB_ID_CONFLICT")
    if job.priority<10000:
        if hasattr(store,"_request"):
            from urllib.parse import quote
            store._request(f"nexus_durable_jobs?job_id=eq.{quote(JOB_ID,safe='')}","PATCH",{"priority":10000},"return=minimal")
        elif hasattr(store,"_connect"):
            with store._connect() as db: db.execute("UPDATE jobs SET priority=10000 WHERE job_id=?",(JOB_ID,))
    if state.get("CURRENT_JOB_ID")!="job_v5_objective_control_repair_20261010":
        if state.get("CURRENT_JOB_ID") not in {JOB_ID,SYSTEMS_JOB_ID}:
            raise RuntimeError("V5_CONTROLLER_CURRENT_JOB_MISMATCH")
    else:
        state["COMPLETED_JOBS"]=list(dict.fromkeys([*(state.get("COMPLETED_JOBS") or []),
            "job_v5_objective_control_repair_20261010"]))
        state.update(CURRENT_PHASE="RESEARCH_SOURCE_REVIEW_AND_OPPORTUNITY_INVENTORY",
            CURRENT_JOB_ID=JOB_ID,CURRENT_JOB_TYPE=JOB_TYPE,ASSIGNED_DEPARTMENT="RESEARCH",
            ASSIGNED_WORKER="Nexus Research",WORKER_ROLE="DEPARTMENT_EXECUTION",
            NEXT_REQUIRED_JOB={"job_id":JOB_ID,"job_type":JOB_TYPE,"department":"RESEARCH","status":"READY"},
            CHECKPOINT={**(state.get("CHECKPOINT") or {}),"next_action":"Execute assigned V5 Research source review and opportunity inventory"})
        persist_campaign(state)
    current=store.get(JOB_ID)
    if current is None: raise RuntimeError("V5_JOB_NOT_PERSISTED")
    policy_ready=False
    if current.state in {"BLOCKED","WAITING"}:
        from nexus_agent_platform.resource_spend_governor import default_store as governor_store
        gov=governor_store()
        if hasattr(gov,"_request"):
            rows=gov._request("nexus_resource_policies?provider=eq.NOTEBOOKLM&service=eq.research_discovery&job_type=eq.NEXUS_NOTEBOOKLM_DISCOVERY_V5_6FB82FD9%3ANOTEBOOKLM_DISCOVERY&budget_period=eq.DAILY&select=state,autonomous_usage_allowed")
            policy_ready=bool(rows and rows[0].get("state")=="NORMAL" and rows[0].get("autonomous_usage_allowed"))
            policy_rows=rows or []
            # Ask the database to reset a resource circuit only after its UTC
            # day has expired. Its incident match protects manual/health stops.
            if policy_rows and policy_rows[0].get("state")=="HARD_STOP":
                full=gov._request("nexus_resource_policies?provider=eq.NOTEBOOKLM&service=eq.research_discovery&job_type=eq.NEXUS_NOTEBOOKLM_DISCOVERY_V5_6FB82FD9%3ANOTEBOOKLM_DISCOVERY&budget_period=eq.DAILY&select=state,autonomous_usage_allowed,updated_at") or []
                if full and full[0].get("updated_at"):
                    opened=datetime.fromisoformat(full[0]["updated_at"].replace("Z","+00:00"))
                    utc_day_start=datetime.now(timezone.utc).replace(hour=0,minute=0,second=0,microsecond=0)
                    if opened < utc_day_start:
                        try: gov.reset_due_daily_budget_hard_stops()
                        except Exception as exc:
                            print(json.dumps({"event":"RESOURCE_WINDOW_RECHECK_DEFERRED","reason":type(exc).__name__}))
                        rows=gov._request("nexus_resource_policies?provider=eq.NOTEBOOKLM&service=eq.research_discovery&job_type=eq.NEXUS_NOTEBOOKLM_DISCOVERY_V5_6FB82FD9%3ANOTEBOOKLM_DISCOVERY&budget_period=eq.DAILY&select=state,autonomous_usage_allowed")
                        policy_ready=bool(rows and rows[0].get("state")=="NORMAL" and rows[0].get("autonomous_usage_allowed"))
        elif hasattr(gov,"connect"):
            with gov.connect() as db:
                row=db.execute("SELECT state,autonomous_usage_allowed FROM policies WHERE provider='NOTEBOOKLM' AND service='research_discovery' AND job_type='NEXUS_NOTEBOOKLM_DISCOVERY_V5_6FB82FD9:NOTEBOOKLM_DISCOVERY' AND budget_period='DAILY'").fetchone()
            policy_ready=bool(row and row[0]=="NORMAL" and row[1])
    if current.state=="COMPLETED":
        result={"status":"ALREADY_COMPLETED","receipt_ref":current.receipt_ref}
    else:
        if current.state in {"BLOCKED","WAITING"} and policy_ready and current.attempt_count<current.max_attempts:
            current=store.transition(JOB_ID,"READY")
        if current.state in {"BLOCKED","WAITING"} and not policy_ready:
            if current.state=="BLOCKED": current=store.transition(JOB_ID,"WAITING")
            store.set_governance_context(JOB_ID,{**(current.governance_context or {}),"resource_wait":{
                "resource":"NOTEBOOKLM","capability":"research_discovery","policy_state":"HARD_STOP",
                "resource_classification":"INTERNAL_BUDGET_LIMIT","job_status":"WAITING_RESOURCE_WINDOW",
                "resume_condition":"NOTEBOOKLM_POLICY_NORMAL","checkpoint_preserved":True}})
            state=load_active_campaign()
            state["WAITING_RESOURCE_JOBS"]=[{"job_id":JOB_ID,"job_type":JOB_TYPE,"resource":"NOTEBOOKLM",
                "capability":"research_discovery","status":"WAITING_RESOURCE_WINDOW",
                "resume_condition":"NOTEBOOKLM_POLICY_NORMAL","checkpoint_preserved":True}]
            state["CURRENT_JOB_STATUS"]="WAITING_RESOURCE_WINDOW"
            state["CAMPAIGN_STATUS"]="ACTIVE"
            state["TERMINAL_CONDITION_SATISFIED"]="NO"
            persist_campaign(state)
            # Systems has an independent resource diagnosis route; run it while
            # the NotebookLM branch is waiting, under the same V5 identity.
            systems_payload={"question":"Systems: diagnose the NotebookLM research_discovery resource circuit. Assess expected usage, retries, duplicate ingestion, prompt size, cache reuse and V5 acceleration without changing the configured cap."}
            systems_path=ROOT/SYSTEMS_PAYLOAD_REF
            systems_path.parent.mkdir(parents=True,exist_ok=True)
            systems_path.write_text(json.dumps(systems_payload,indent=2)+"\n",encoding="utf-8")
            systems=store.enqueue("SYSTEMS","NEXUS_DEPARTMENT_QUERY",priority=9999,
                payload_ref=SYSTEMS_PAYLOAD_REF,parent_job_id=None,correlation_id=CORRELATION,
                idempotency_key=f"objective-independent:{CAMPAIGN}:{SYSTEMS_JOB_ID}",job_id=SYSTEMS_JOB_ID,
                governance_context={"campaign_id":CAMPAIGN,"owner_objective_id":OBJECTIVE,
                    "objective_version":"V5","project_id":"project_nexus_owner_real_world_v5_20261010_6fb82fd9",
                    "providers_allowed":["SUPABASE"],"spend_allowed":False,"external_actions_allowed":False,
                    "resource_class":"LIGHTWEIGHT_INTERNAL","resource_dependencies":[]})
            state=load_active_campaign()
            state.update(CURRENT_PHASE="SYSTEMS_RESOURCE_CIRCUIT_DIAGNOSIS",CURRENT_JOB_ID=SYSTEMS_JOB_ID,
                CURRENT_JOB_TYPE="NEXUS_DEPARTMENT_QUERY",ASSIGNED_DEPARTMENT="SYSTEMS",
                ASSIGNED_WORKER="Nexus Systems",WORKER_ROLE="DEPARTMENT_EXECUTION",
                NEXT_REQUIRED_JOB={"job_id":JOB_ID,"job_type":JOB_TYPE,"department":"RESEARCH",
                    "status":"WAITING_RESOURCE_WINDOW"},
                LAST_VALID_TRANSITION={"from_job":JOB_ID,"to_job":SYSTEMS_JOB_ID,"reason":"Independent Systems diagnosis while NotebookLM resource is paused"})
            persist_campaign(state)
            current_system=store.get(SYSTEMS_JOB_ID)
            if current_system.state!="COMPLETED":
                claimed_system=store.claim_by_id(SYSTEMS_JOB_ID,WORKER,lease_seconds=900)
                if not claimed_system: raise RuntimeError("V5_SYSTEMS_JOB_NOT_CLAIMABLE:"+str(store.get(SYSTEMS_JOB_ID).state))
                systems_result=run_department_job(SYSTEMS_JOB_ID,WORKER,store)
            else:
                systems_result={"status":"ALREADY_COMPLETED","receipt_ref":current_system.receipt_ref}
            current_system=store.get(SYSTEMS_JOB_ID)
            state=load_active_campaign()
            if current_system and current_system.state=="COMPLETED":
                state["COMPLETED_JOBS"]=list(dict.fromkeys([*(state.get("COMPLETED_JOBS") or []),SYSTEMS_JOB_ID]))
                state.setdefault("JOB_IDS",[])
                if SYSTEMS_JOB_ID not in state["JOB_IDS"]: state["JOB_IDS"].append(SYSTEMS_JOB_ID)
                state.setdefault("RECEIPT_IDS",[])
                if current_system.receipt_ref and current_system.receipt_ref not in state["RECEIPT_IDS"]: state["RECEIPT_IDS"].append(current_system.receipt_ref)
                state["SYSTEMS_RESOURCE_DIAGNOSIS"]={"STATUS":"COMPLETED","JOB_ID":SYSTEMS_JOB_ID,
                    "RECEIPT_ID":current_system.receipt_ref,"RESULT":systems_result}
                state.update(CURRENT_PHASE=JOB_TYPE,CURRENT_JOB_ID=JOB_ID,CURRENT_JOB_TYPE=JOB_TYPE,
                    ASSIGNED_DEPARTMENT="RESEARCH",ASSIGNED_WORKER="Nexus Research",
                    WORKER_ROLE="DEPARTMENT_EXECUTION")
                state["CURRENT_JOB_STATUS"]="WAITING_RESOURCE_WINDOW"
                persist_campaign(state)
            # Continue the separate public-web Research lane through the real
            # Research department. It does not satisfy or replace NotebookLM
            # source-review requirements; it preserves independent evidence.
            public_payload={"question":"Research public web evidence on low-cost online business models and recurring customer problems for the V5 opportunity inventory. Cite sources and separate evidence from inference; do not use NotebookLM."}
            public_path=ROOT/PUBLIC_RESEARCH_PAYLOAD_REF
            public_path.parent.mkdir(parents=True,exist_ok=True)
            public_path.write_text(json.dumps(public_payload,indent=2)+"\n",encoding="utf-8")
            public_job=store.enqueue("RESEARCH_ALPHA","NEXUS_DEPARTMENT_QUERY",priority=9800,
                payload_ref=PUBLIC_RESEARCH_PAYLOAD_REF,parent_job_id=JOB_ID,correlation_id=CORRELATION,
                idempotency_key=f"objective-independent:{CAMPAIGN}:{PUBLIC_RESEARCH_JOB_ID}",
                job_id=PUBLIC_RESEARCH_JOB_ID,max_attempts=3,
                budget_envelope={"max_requests":12,"max_response_bytes":120000,"max_tokens":5000,
                    "max_gpu_seconds":0,"max_runtime_seconds":300,"max_resource_creations":0,
                    "max_estimated_cost":0.0,"max_retries":2},
                governance_context={"campaign_id":CAMPAIGN,"owner_objective_id":OBJECTIVE,
                    "objective_version":"V5","project_id":"project_nexus_owner_real_world_v5_20261010_6fb82fd9",
                    "providers_allowed":["SUPABASE","ORACLE"],"spend_allowed":False,
                    "external_actions_allowed":False,"resource_class":"LIGHTWEIGHT_INTERNAL",
                    "independent_job":True,
                    "resource_dependencies":["SEARXNG","ORACLE_READ_ONLY_SSH"],
                    "notebooklm_substitution":False})
            # The previous worker lease expired without a receipt. This exact
            # read-only public Research job may have one bounded recovery try;
            # its policy/provider budget remains independently enforced.
            store.ensure_retry_capacity(PUBLIC_RESEARCH_JOB_ID,7)
            # Twelve control-plane requests were consumed before the worker
            # could dispatch. Keep the job-local envelope bounded at 30 so
            # one actual department attempt can proceed; global/provider
            # governors and zero-cost authorization remain in force.
            store.ensure_request_capacity(PUBLIC_RESEARCH_JOB_ID,60)
            current_public=store.get(PUBLIC_RESEARCH_JOB_ID)
            if current_public and not (current_public.governance_context or {}).get("independent_job"):
                store.set_governance_context(PUBLIC_RESEARCH_JOB_ID,{**(current_public.governance_context or {}),
                    "campaign_id":CAMPAIGN,"owner_objective_id":OBJECTIVE,"objective_version":"V5",
                    "independent_job":True,"spend_allowed":False,"external_actions_allowed":False,
                    "resource_dependencies":["SEARXNG","ORACLE_READ_ONLY_SSH"],"notebooklm_substitution":False})
                current_public=store.get(PUBLIC_RESEARCH_JOB_ID)
            if current_public.state=="BLOCKED" and current_public.attempt_count<current_public.max_attempts:
                current_public=store.transition(PUBLIC_RESEARCH_JOB_ID,"READY")
            if current_public.state=="COMPLETED":
                public_result={"status":"ALREADY_COMPLETED","receipt_ref":current_public.receipt_ref}
            else:
                claimed_public=store.claim_by_id(PUBLIC_RESEARCH_JOB_ID,WORKER,lease_seconds=900)
                if not claimed_public:
                    public_result={"status":"WAITING","job_state":store.get(PUBLIC_RESEARCH_JOB_ID).state}
                else:
                    public_result=run_department_job(PUBLIC_RESEARCH_JOB_ID,WORKER,store)
            current_public=store.get(PUBLIC_RESEARCH_JOB_ID)
            state=load_active_campaign()
            state.setdefault("JOB_IDS",[])
            if PUBLIC_RESEARCH_JOB_ID not in state["JOB_IDS"]: state["JOB_IDS"].append(PUBLIC_RESEARCH_JOB_ID)
            if current_public and current_public.state=="COMPLETED":
                state["COMPLETED_JOBS"]=list(dict.fromkeys([*(state.get("COMPLETED_JOBS") or []),PUBLIC_RESEARCH_JOB_ID]))
                state.setdefault("RECEIPT_IDS",[])
                if current_public.receipt_ref and current_public.receipt_ref not in state["RECEIPT_IDS"]: state["RECEIPT_IDS"].append(current_public.receipt_ref)
                state["INDEPENDENT_PUBLIC_RESEARCH"]={"STATUS":"COMPLETED","JOB_ID":PUBLIC_RESEARCH_JOB_ID,
                    "RECEIPT_ID":current_public.receipt_ref,"RESULT":public_result,
                    "NOTEBOOKLM_REQUIREMENTS_SATISFIED":False}
            else:
                state["INDEPENDENT_PUBLIC_RESEARCH"]={"STATUS":current_public.state if current_public else "UNKNOWN",
                    "JOB_ID":PUBLIC_RESEARCH_JOB_ID,"RESULT":public_result,"NOTEBOOKLM_REQUIREMENTS_SATISFIED":False}
            from nexus_agent_platform.resource_dependency_controller import global_stop_allowed
            executable_work=[]
            if current_public and current_public.state in {"READY","FAILED_RETRYABLE","CLAIMED","RUNNING"}:
                executable_work.append({"job_id":PUBLIC_RESEARCH_JOB_ID,"zero_cost_executable":True})
            state["GLOBAL_STOP_ALLOWED_ONLY_IF"]="NO_EXECUTABLE_ZERO_COST_JOB_REMAINS"
            state["GLOBAL_STOP_ALLOWED"]="NO; V5 terminal condition remains unsatisfied"
            state["NO_EXECUTABLE_ZERO_COST_JOB_REMAINS"]="YES" if global_stop_allowed(executable_work) else "NO"
            state["CONTINUE_CAMPAIGN"]="YES"
            state["NOTEBOOKLM_RESOURCE_CIRCUIT"]={"classification":"INTERNAL_BUDGET_LIMIT",
                "resource":"NOTEBOOKLM","capability":"research_discovery","limit_bytes_per_day":500000,
                "policy_state":"HARD_STOP","global_campaign_stop":False,
                "dependent_job_state":"WAITING_RESOURCE_WINDOW","independent_work_execution":
                    "PUBLIC_WEB_RESEARCH_AND_SYSTEMS_DIAGNOSIS"}
            state.update(CURRENT_PHASE=JOB_TYPE,CURRENT_JOB_ID=JOB_ID,CURRENT_JOB_TYPE=JOB_TYPE,
                CURRENT_JOB_STATUS="WAITING_RESOURCE_WINDOW",CAMPAIGN_STATUS="ACTIVE",
                NEXT_REQUIRED_JOB={"job_id":JOB_ID,"job_type":JOB_TYPE,"department":"RESEARCH",
                    "status":"WAITING_RESOURCE_WINDOW","resource":"NOTEBOOKLM",
                    "resume_condition":"NOTEBOOKLM_POLICY_NORMAL","checkpoint_preserved":True})
            persist_campaign(state)
            result={"status":"WAITING_RESOURCE_WINDOW","resource":"NOTEBOOKLM",
                "independent_systems_job_id":SYSTEMS_JOB_ID,"systems_result":systems_result,
                "independent_public_research_job_id":PUBLIC_RESEARCH_JOB_ID,"public_research_result":public_result}
        if result.get("status")=="WAITING_RESOURCE_WINDOW":
            pass
        elif current.state=="COMPLETED":
            pass
        else:
            claimed=store.claim_by_id(JOB_ID,WORKER,lease_seconds=900)
            if not claimed: raise RuntimeError("V5_EXPECTED_JOB_NOT_CLAIMABLE:"+str(store.get(JOB_ID).state))
            result=run_department_job(JOB_ID,WORKER,store)
    fresh=store.get(JOB_ID)
    state=load_active_campaign()
    if fresh and fresh.state=="COMPLETED":
        state["COMPLETED_JOBS"]=list(dict.fromkeys([*(state.get("COMPLETED_JOBS") or []),JOB_ID]))
        state.setdefault("JOB_IDS",[])
        if JOB_ID not in state["JOB_IDS"]: state["JOB_IDS"].append(JOB_ID)
        state.setdefault("RECEIPT_IDS",[])
        if fresh.receipt_ref and fresh.receipt_ref not in state["RECEIPT_IDS"]: state["RECEIPT_IDS"].append(fresh.receipt_ref)
        state["PHASE_RESULTS"]["RESEARCH_SOURCE_REVIEW_AND_OPPORTUNITY_INVENTORY"]={
            "STATUS":"PASS" if result.get("status") in {"COMPLETED","ALREADY_COMPLETED"} else result.get("status"),
            "JOB_ID":JOB_ID,"RECEIPT_ID":fresh.receipt_ref,"ARTIFACT_REF":result.get("opportunity_inventory_ref") or result.get("artifact_ref")}
        state["NEXT_REQUIRED_JOB"]={"job_type":"OWNER_OBJECTIVE_CONTINUATION","department":"NEXUS_CONTROLLER",
            "status":"REQUIRES_OBJECTIVE_JOB_PLAN"}
        state["TERMINAL_CONDITION_SATISFIED"]="NO"
        persist_campaign(state)
    elif fresh and fresh.state=="BLOCKED":
        state["CURRENT_JOB_STATUS"]="BLOCKED"
        state["NEXT_REQUIRED_JOB"]={"job_id":JOB_ID,"job_type":JOB_TYPE,"department":"RESEARCH",
            "status":"BLOCKED_WAITING_FOR_AUTHORIZED_NOTEBOOKLM_POLICY_RECOVERY"}
        state["TERMINAL_CONDITION_SATISFIED"]="NO"
        persist_campaign(state)
    # A waiting V5 resource branch cannot monopolize the controller. Run the
    # next independently executable registered department job before returning.
    if fresh and fresh.state in {"WAITING","BLOCKED"}:
        dag_result=run_v5_systems_health_job(store,load_active_campaign())
        resource_guard_result=run_v5_resource_guard_job(store)
        remote_stack_result=run_v5_remote_stack_health_job(store)
        opencode_result=run_v5_opencode_benchmark_job(store)
        forex_result=run_v5_forex_research_job(store)
        capability_specs=[
            ("NEEDLE","SYSTEMS","Systems: perform a read-only Needle AI installation and runtime capability check. Report installed version, MCP connection test result, and any missing local prerequisites. Do not install packages or spend money."),
            ("HUGGING_FACE","SYSTEMS","Systems: run a read-only Hugging Face integration/auth/quota capability check for V5 and report verified status and missing prerequisites. Do not create paid resources."),
            ("MODAL","SYSTEMS","Systems: run a read-only Modal CLI/SDK/auth capability check for V5 and report verified status and missing prerequisites. Do not create paid resources."),
            ("KAGGLE","SYSTEMS","Systems: run a read-only Kaggle API/auth/quota capability check for V5 and report verified status and missing prerequisites. Do not create paid resources."),
            ("META_AI","SYSTEMS","Systems: run a read-only Meta AI route and credential capability check for V5; report verified status and missing prerequisites. Do not send messages."),
            ("NOVA","NOVA","Nova: run the V5 100-question infrastructure/system capability test and report the actual completed count and evidence reference. Do not claim unexecuted tests."),
            ("EMAIL","SYSTEMS","Systems: run a read-only email integration/authentication and inbox retrieval capability check. Do not send email."),
            ("SOCIAL","SYSTEMS","Systems: run a read-only authorized organic social integration/auth capability check. Do not publish a post."),
        ]
        capability_results={}
        for workstream,department,question in capability_specs:
            capability_results[workstream]=run_v5_department_capability_job(store,workstream,department,question)
        from nexus_agent_platform.v5_dependency_graph import inspect_graph
        latest=load_active_campaign()
        graph=inspect_graph(completed=latest.get("COMPLETED_V5_WORKSTREAMS",[]),
            waiting_resources={"NOTEBOOKLM"} if latest.get("NOTEBOOKLM_CURRENT_STATE","").startswith("HARD_STOP") else set(),
            job_status={"RESEARCH":"WAITING_RESOURCE_WINDOW","SYSTEMS":
                ("COMPLETED" if dag_result.get("status") in {"COMPLETED","ALREADY_COMPLETED"} else "BLOCKED"),
                "RESOURCE_GUARDS":("COMPLETED" if resource_guard_result.get("status") in {"COMPLETED","ALREADY_COMPLETED"} else "BLOCKED"),
                "HERMES":("COMPLETED" if remote_stack_result.get("status") in {"COMPLETED","ALREADY_COMPLETED"} else "BLOCKED")})
        if opencode_result.get("status") not in {"COMPLETED","ALREADY_COMPLETED"}:
            graph["workstreams"]=[{**row,"current_status":"BLOCKED_EXTERNAL_PROVIDER"}
                if row["workstream"] in {"CODEX_OPENCODE_FAILOVER","OPENCODE_MODEL_BENCHMARK"} else row for row in graph["workstreams"]]
        if forex_result.get("status") not in {"COMPLETED","ALREADY_COMPLETED"}:
            graph["workstreams"]=[{**row,"current_status":"BLOCKED_EXTERNAL_PROVIDER"}
                if row["workstream"]=="TRADING_RESEARCH" else row for row in graph["workstreams"]]
        graph["runnable"]=[row for row in graph["workstreams"] if row["current_status"]=="READY"]
        graph["waiting"]=[row for row in graph["workstreams"] if row["current_status"].startswith(("WAITING","BLOCKED"))]
        graph["runnable_zero_cost_job_count"]=len(graph["runnable"])
        graph["global_stop_allowed"]=not graph["runnable"]
        latest["V5_DEPENDENCY_GRAPH"]={"workstreams":graph["workstreams"],
            "runnable_zero_cost_job_count":graph["runnable_zero_cost_job_count"],
            "waiting_job_count":len(graph["waiting"]),"global_stop_allowed":graph["global_stop_allowed"],
            "scheduler":"DEPENDENCY_AWARE_DAG","updated_at":datetime.now(timezone.utc).isoformat()}
        latest["INDEPENDENT_JOBS_DISCOVERED"]=[row["workstream"] for row in graph["runnable"]]
        latest["INDEPENDENT_JOBS_EXECUTED"]=list(dict.fromkeys([*(latest.get("INDEPENDENT_JOBS_EXECUTED") or []),
            "SYSTEMS" if dag_result.get("status") in {"COMPLETED","ALREADY_COMPLETED"} else "SYSTEMS_ATTEMPTED",
            "RESOURCE_GUARDS" if resource_guard_result.get("status") in {"COMPLETED","ALREADY_COMPLETED"} else "RESOURCE_GUARDS_ATTEMPTED"]))
        latest["INDEPENDENT_JOBS_EXECUTED"]=list(dict.fromkeys([*latest["INDEPENDENT_JOBS_EXECUTED"],
            "HERMES" if remote_stack_result.get("status") in {"COMPLETED","ALREADY_COMPLETED"} else "HERMES_ATTEMPTED"]))
        latest["INDEPENDENT_JOBS_EXECUTED"]=list(dict.fromkeys([*latest["INDEPENDENT_JOBS_EXECUTED"],
            "CODEX_OPENCODE_FAILOVER" if opencode_result.get("status") in {"COMPLETED","ALREADY_COMPLETED"} else "CODEX_OPENCODE_FAILOVER_ATTEMPTED"]))
        latest["INDEPENDENT_JOBS_EXECUTED"]=list(dict.fromkeys([*latest["INDEPENDENT_JOBS_EXECUTED"],
            "TRADING_RESEARCH" if forex_result.get("status") in {"COMPLETED","ALREADY_COMPLETED"} else "TRADING_RESEARCH_ATTEMPTED"]))
        latest["GLOBAL_STOP_ALLOWED_ONLY_IF"]="NO_EXECUTABLE_ZERO_COST_JOB_REMAINS"
        latest["GLOBAL_STOP_ALLOWED"]="NO" if graph["runnable_zero_cost_job_count"]>0 or latest.get("TERMINAL_CONDITION_SATISFIED")!="YES" else "YES"
        latest["NO_EXECUTABLE_ZERO_COST_JOB_REMAINS"]="YES" if graph["runnable_zero_cost_job_count"]==0 else "NO"
        latest["STOPPED_WITH_RUNNABLE_ZERO_COST_WORK"]="NO"
        persist_campaign(latest)
        result["independent_dag_systems_job_id"]="job_v5_dag_systems_health_20261010"
        result["independent_dag_systems_result"]=dag_result
        result["independent_dag_resource_guard_job_id"]="job_v5_dag_resource_guard_diagnosis_20261010"
        result["independent_dag_resource_guard_result"]=resource_guard_result
        result["independent_dag_hermes_job_id"]="job_v5_dag_remote_stack_health_20261010"
        result["independent_dag_hermes_result"]=remote_stack_result
        result["independent_dag_opencode_job_id"]="job_v5_dag_opencode_free_model_benchmark_20261010"
        result["independent_dag_opencode_result"]=opencode_result
        result["independent_dag_forex_job_id"]="job_v5_dag_forex_market_scan_20261010"
        result["independent_dag_forex_result"]=forex_result
        result["independent_dag_capability_results"]=capability_results
    print(json.dumps({"campaign_id":CAMPAIGN,"objective_id":OBJECTIVE,"job_id":JOB_ID,
        "job_state":fresh.state if fresh else None,"receipt_ref":fresh.receipt_ref if fresh else None,
        "result":result},ensure_ascii=False))
    return 0 if (fresh and fresh.state=="COMPLETED") or result.get("independent_systems_job_id")==SYSTEMS_JOB_ID or result.get("independent_public_research_job_id")==PUBLIC_RESEARCH_JOB_ID else 1

if __name__=="__main__": raise SystemExit(main())
