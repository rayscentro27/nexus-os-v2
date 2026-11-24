"""Bounded durable Needle verification and same-notebook Research repair jobs."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
from nexus_agent_platform.runtime.paths import nexus_research_state_path

PAYLOAD_ROOT = nexus_research_state_path("runtime", "needle_jobs")


def _write_payload(payload: dict[str, Any]) -> str:
    encoded=json.dumps(payload,ensure_ascii=False,sort_keys=True,separators=(",",":"))
    digest=hashlib.sha256(encoded.encode()).hexdigest()
    target=PAYLOAD_ROOT/f"{digest}.json"
    target.parent.mkdir(parents=True,exist_ok=True)
    if not target.exists():
        target.write_text(json.dumps(payload,ensure_ascii=False,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    return str(target)


def enqueue_job(*, case_id: str, job_type: str, completion_receipt_id: str,
                repair_attempt: int = 0, needle_request: dict[str, Any] | None = None,
                parent_job: Any | None = None, correlation_id: str | None = None) -> dict[str, Any]:
    """Enqueue an idempotent child in the existing durable job system."""
    from nexus_agent_platform.durable_jobs import create_next_job, default_store
    store=default_store()
    if parent_job is None:
        current_id=os.environ.get("NEXUS_DURABLE_JOB_ID")
        parent_job=store.get(current_id) if current_id else None
    parent_context=getattr(parent_job,"governance_context",{}) or {}
    notebooklm_policy_job_type=(os.environ.get("NEXUS_NOTEBOOKLM_GOVERNOR_JOB_TYPE")
        or parent_context.get("notebooklm_policy_job_type"))
    payload={"schema_version":"nexus.needle-research-job.v1","case_id":case_id,
        "completion_receipt_id":completion_receipt_id,"repair_attempt":int(repair_attempt),
        "needle_request":needle_request or {},"no_new_owner_objective":True,
        "notebooklm_policy_job_type":notebooklm_policy_job_type}
    payload_ref=_write_payload(payload)
    event_id=f"{case_id}:{completion_receipt_id}:{job_type}:repair-{int(repair_attempt)}"
    context={**parent_context,"source":"NOTEBOOK_COMPLETION_CONTRACT_NEEDLE",
        "research_case_id":case_id,"contract_completion_receipt_id":completion_receipt_id,
        "repair_attempt":int(repair_attempt),"spend_allowed":False,"paid_provider_authorized":False,
        "external_actions_allowed":False,"no_new_owner_objective":True,
        "execution_class":"LIGHT_REASONING" if job_type=="NEEDLE_RESEARCH_READINESS_VERIFY" else "SPECIALIZED_EXECUTOR",
        "notebooklm_policy_job_type":notebooklm_policy_job_type,
        "step_reason":"semantic research package readiness verification" if job_type=="NEEDLE_RESEARCH_READINESS_VERIFY" else "targeted research gap repair"}
    if job_type=="NEEDLE_RESEARCH_READINESS_VERIFY":
        # NotebookLM has completed before semantic verification starts. The
        # only metered capability this child needs is the canonical model route.
        context["resource_dependencies"]=["OPENAI_CODEX"]
    elif job_type=="NEEDLE_RESEARCH_TARGETED_REPAIR":
        context["resource_dependencies"]=["NOTEBOOKLM"]
    corr=(correlation_id or getattr(parent_job,"correlation_id",None) or os.environ.get("NEXUS_CORRELATION_ID")
          or f"needle:{case_id}:{completion_receipt_id}")
    if parent_job is not None:
        job=create_next_job(store,parent_job,department="RESEARCH",job_type=job_type,payload_ref=payload_ref,event_id=event_id)
        if context != (job.governance_context or {}):
            store.set_governance_context(job.job_id,{**(job.governance_context or {}),**context})
            job=store.get(job.job_id) or job
    else:
        job=store.enqueue("RESEARCH",job_type,priority=85,payload_ref=payload_ref,
            correlation_id=corr,max_attempts=2,
            idempotency_key=f"needle:{case_id}:{completion_receipt_id}:{job_type}:repair-{int(repair_attempt)}",
            governance_context=context)
    return {"job_id":job.job_id,"job_type":job.job_type,"state":job.state,"payload_ref":job.payload_ref,
        "parent_job_id":job.parent_job_id,"correlation_id":job.correlation_id}


def _load_payload(job: Any) -> dict[str, Any]:
    if not job.payload_ref:
        raise ValueError("NEEDLE_JOB_PAYLOAD_REQUIRED")
    path=(ROOT/job.payload_ref).resolve()
    if not path.is_relative_to(ROOT.resolve()) or not path.is_file():
        raise ValueError("NEEDLE_JOB_PAYLOAD_INVALID")
    value=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value,dict) or value.get("schema_version")!="nexus.needle-research-job.v1":
        raise ValueError("NEEDLE_JOB_PAYLOAD_SCHEMA_INVALID")
    return value


def _save_case(case_id: str, *, state: dict[str, Any], result: dict[str, Any],
               status: str, next_action: str) -> None:
    from research import research_case_engine as cases
    case=cases.get_case(case_id)
    if not case:
        return
    contract_summary={"contract_id":state.get("contract_id"),"research_purpose":state.get("research_purpose"),
        "research_domain":state.get("research_domain"),"notebook_id":state.get("notebook_id"),
        "verification_status":state.get("verification_status"),
        "question_count_required":len([q for q in state.get("required_questions",[]) if q.get("required")]),
        "question_count_asked":sum(bool(q.get("asked")) for q in state.get("required_questions",[]) if q.get("required")),
        "needle_verification":state.get("needle_verification"),"needle_repair_count":state.get("needle_repair_count",0),
        "handoff_status":state.get("handoff_status")}
    cases._save(case,"NEEDLE_RESEARCH_READINESS_CHECKPOINT",notebook_completion_contract=contract_summary,
        needle_verification=state.get("needle_verification"),status=status,continue_research=status!="DEPARTMENT_DEVELOPMENT",
        next_research_action=next_action,needle_job_result={key:result.get(key) for key in (
            "status","reason_code","next_job_id","next_department","notebook_id","receipt_id") if result.get(key) is not None})


def _reconcile_local_group_statuses(case_id: str, state: dict[str, Any], case: dict[str, Any]) -> int:
    """Deterministically recover status fields from the already-persisted local turns."""
    from research import notebook_completion_contracts as contract
    updates={}
    refs={}
    for row in case.get("notebook_answers") or []:
        kind=str(row.get("question_type") or "")
        if not (kind.startswith("CONTRACT_GROUP:") or kind.startswith("CONTRACT_GAP:")):
            continue
        artifact_ref=str(row.get("local_artifact_ref") or "")
        if not artifact_ref: continue
        path=(ROOT/artifact_ref).resolve()
        if not path.is_relative_to(ROOT.resolve()) or not path.is_file(): continue
        try:
            artifact=json.loads(path.read_text(encoding="utf-8"))
            statuses=contract._extract_statuses(str(artifact.get("answer") or ""))
        except (OSError,ValueError,TypeError):
            continue
        updates.update(statuses)
        if statuses:
            for qid in statuses:
                refs[qid]=sorted(set(refs.get(qid,[]))|set(str(x) for x in row.get("source_ids",[]) if x))
    changed=0
    allowed={row.get("question_id") for row in state.get("required_questions",[])}
    for row in state.get("required_questions",[]):
        value=updates.get(row.get("question_id"))
        if row.get("question_id") in allowed and value in {"VERIFIED","PARTIALLY_VERIFIED","UNVERIFIED","CONTRADICTED"}:
            if row.get("evidence_status")!=value:
                row["evidence_status"]=row["answer_status"]=value; changed+=1
            row["source_refs"]=sorted(set(row.get("source_refs") or [])|set(refs.get(row.get("question_id"),[])))
    prior={row.get("question_id"):row for row in state.get("evidence_gaps",[])}
    state["evidence_gaps"]=contract._derive_gaps(state.get("required_questions",[]),prior)
    if changed:
        state["status_reconciled_from_local_notebook_turns"]=changed
        state["updated_at"]=contract._now()
    return changed


def handle_job(job: Any, store: Any) -> dict[str, Any]:
    """Run either semantic verification or one targeted Research repair."""
    from research import notebook_completion_contracts as contract
    from research import research_case_engine as cases
    from research.notebooklm_research_adapter import AdapterConfig, NotebookLMResearchAdapter
    payload=_load_payload(job)
    case_id=str(payload["case_id"])
    state=contract.load_state(case_id=case_id)
    if not state:
        return {"status":"BLOCKED","reason":"NOTEBOOK_CONTRACT_STATE_NOT_FOUND"}
    receipt_id=str(payload.get("completion_receipt_id") or state.get("completion_receipt_id") or "")
    if not receipt_id:
        return {"status":"BLOCKED","reason":"NOTEBOOK_COMPLETION_RECEIPT_REQUIRED"}
    case=cases.get_case(case_id) or {}
    if case:
        _reconcile_local_group_statuses(case_id,state,case)
        contract.persist_state(state,case_id=case_id)
    if job.job_type=="NEEDLE_RESEARCH_TARGETED_REPAIR":
        if int(payload.get("repair_attempt",0)) != 1 or int(state.get("needle_repair_count",0)) >= 1:
            return {"status":"BLOCKED","reason":"NEEDLE_REPAIR_BOUND_EXHAUSTED"}
        state["needle_verification"]={**(state.get("needle_verification") or {}),"status":"RESEARCH_MORE"}
        state["local_state_ref"]=contract.persist_state(state,case_id=case_id)
        request=payload.get("needle_request") or {}
        prior_scope=os.environ.get("NEXUS_NOTEBOOKLM_GOVERNOR_JOB_TYPE")
        policy_scope=str(payload.get("notebooklm_policy_job_type")
            or (getattr(job,"governance_context",{}) or {}).get("notebooklm_policy_job_type") or "")
        if not policy_scope.startswith("NEXUS_FULL_RESEARCH_CANARY_"):
            return {"status":"BLOCKED","reason":"NEEDLE_REPAIR_CANARY_POLICY_SCOPE_MISSING"}
        os.environ["NEXUS_NOTEBOOKLM_GOVERNOR_JOB_TYPE"]=policy_scope
        try:
            adapter=NotebookLMResearchAdapter(AdapterConfig(profile="default"))
            from research.notebook_playbook_runner import _run_one_needle_repair
            repair=_run_one_needle_repair(case_id,state=state,adapter=adapter,needle=request)
        finally:
            if prior_scope is None: os.environ.pop("NEXUS_NOTEBOOKLM_GOVERNOR_JOB_TYPE",None)
            else: os.environ["NEXUS_NOTEBOOKLM_GOVERNOR_JOB_TYPE"]=prior_scope
        if not repair.get("ok"):
            state["verification_status"]="NEEDLE_REPAIR_PENDING"
            contract.persist_state(state,case_id=case_id)
            _save_case(case_id,state=state,result={"status":"WAITING_RESOURCE_WINDOW","reason_code":repair.get("reason")},
                status="MORE_RESEARCH_REQUIRED",next_action="RETRY_SAME_NOTEBOOK_NEEDLE_REPAIR")
            return {"status":"WAITING_RESOURCE_WINDOW","resource":"RESEARCH_PROVIDER",
                "capability":"targeted_notebook_research","resume_condition":"RESEARCH_PROVIDER_AVAILABLE",
                "checkpoint_preserved":True,"reason":repair.get("reason"),"notebook_id":state.get("notebook_id")}
        state["needle_repair_count"]=1
        state["needle_verification"]={**(state.get("needle_verification") or {}),"repair_performed":True,
            "repair_question_id":repair.get("question_id"),"repair_receipt_id":repair.get("expansion_receipt_id")}
        verification=contract.verify_completion(state,web_supplementation_appropriate=bool(state.get("evidence_gaps")))
        if not verification.get("complete"):
            state["verification_status"]="MECHANICAL_INCOMPLETE_AFTER_NEEDLE_REPAIR"
            contract.persist_state(state,case_id=case_id)
            _save_case(case_id,state=state,result={"status":"BLOCKED","reason_code":"MECHANICAL_INCOMPLETE_AFTER_REPAIR"},
                status="MORE_RESEARCH_REQUIRED",next_action="CONTINUE_NOTEBOOK_COMPLETION_CONTRACT")
            return {"status":"BLOCKED","reason":"MECHANICAL_INCOMPLETE_AFTER_REPAIR"}
        next_job=enqueue_job(case_id=case_id,job_type="NEEDLE_RESEARCH_READINESS_VERIFY",
            completion_receipt_id=receipt_id,repair_attempt=1,parent_job=job)
        state["verification_status"]="NEEDLE_RECHECK_QUEUED"
        state["local_state_ref"]=contract.persist_state(state,case_id=case_id)
        result={"status":"COMPLETED","research_case_id":case_id,"notebook_id":state.get("notebook_id"),
            "repair_question_id":repair.get("question_id"),"repair_receipt_id":repair.get("expansion_receipt_id"),
            "next_job_id":next_job["job_id"],"next_job_type":next_job["job_type"],"same_notebook_reused":True}
        _save_case(case_id,state=state,result=result,status="MORE_RESEARCH_REQUIRED",next_action="WAIT_FOR_NEEDLE_RECHECK")
        return result

    if job.job_type!="NEEDLE_RESEARCH_READINESS_VERIFY":
        return {"status":"BLOCKED","reason":"UNSUPPORTED_NEEDLE_JOB_TYPE"}
    mechanical=contract.verify_completion(state,web_supplementation_appropriate=bool(state.get("evidence_gaps")))
    if not mechanical.get("complete"):
        state["verification_status"]="MECHANICAL_INCOMPLETE"
        result={"status":"BLOCKED","reason":"MECHANICAL_NOTEBOOK_CONTRACT_GATE_FAILED",
            "mechanical_verification":mechanical}
        contract.persist_state(state,case_id=case_id)
        _save_case(case_id,state=state,result={"status":"BLOCKED","reason_code":result["reason"]},
            status="MORE_RESEARCH_REQUIRED",next_action="CONTINUE_NOTEBOOK_COMPLETION_CONTRACT")
        return result
    from research.needle_research_readiness import verify_readiness
    needle=verify_readiness(state,deterministic_result=mechanical,
        repair_attempt=int(payload.get("repair_attempt",0)))
    needle_compact={key:needle.get(key) for key in (
        "receipt_id","status","reason_code","summary","affected_question_ids","specific_gap",
        "requested_research_action","evidence_needed","unresolved_items_safe","next_department",
        "notebook_id","execution_class","provider","model","cost_class","latency_ms","artifact_ref","recorded_at","error_type","error") if needle.get(key) is not None}
    state["needle_verification"]=needle_compact
    if needle.get("status")=="BLOCKED":
        state["verification_status"]="NEEDLE_VERIFICATION_BLOCKED"
        contract.persist_state(state,case_id=case_id)
        _save_case(case_id,state=state,result=needle_compact,status="MORE_RESEARCH_REQUIRED",
            next_action="RETRY_NEEDLE_CANONICAL_MODEL_ROUTE")
        return {"status":"WAITING_RESOURCE_WINDOW","resource":"MODEL_ROUTER","capability":"research_readiness",
            "resume_condition":"CANONICAL_MODEL_ROUTE_AVAILABLE","checkpoint_preserved":True,"reason":needle.get("error")}
    if needle.get("status")=="RESEARCH_MORE":
        repair_count=int(payload.get("repair_attempt",0))
        state["verification_status"]="NEEDLE_RESEARCH_MORE"
        # A semantic readiness gap returns to Research under Alpha's director
        # role. Needle remains the verifier; Alpha only chooses what Research
        # should investigate next. Advice is compact and never evidence.
        alpha_direction = None
        if state.get("research_domain")=="BUSINESS_OPPORTUNITY" and repair_count<1:
            try:
                from nexus_agent_platform.business_opportunity_research_v2 import (
                    execute_outside_advisor, execute_research_director)
                compact_context={"opportunity_id":case.get("opportunity_id"),
                    "current_recommended_version":(state.get("structured_extraction") or {}).get("recommended_version"),
                    "verified_findings":(state.get("structured_extraction") or {}).get("key_verified_findings",[]),
                    "partial_findings":(state.get("structured_extraction") or {}).get("partially_verified_findings",[]),
                    "unverified_findings":(state.get("structured_extraction") or {}).get("unverified_findings",[]),
                    "unit_economics":(state.get("structured_extraction") or {}).get("unit_economics"),
                    "open_questions":[needle.get("specific_gap"),needle.get("requested_research_action")],
                    "major_risks":(state.get("structured_extraction") or {}).get("major_risks",[])}
                advisor=execute_outside_advisor(objective=str(state.get("objective") or ""),context=compact_context)
                compact_context["outside_advisor_feedback"]={"hypotheses_only":True,"advice":advisor.get("advice")}
                alpha_direction=execute_research_director(objective=str(state.get("objective") or ""),
                    context=compact_context,findings=[{"question_id":qid,"specific_gap":needle.get("specific_gap"),
                        "requested_research_action":needle.get("requested_research_action"),
                        "evidence_needed":needle.get("evidence_needed")} for qid in needle.get("affected_question_ids",[])[:4]],
                    event="NEEDLE_RESEARCH_MORE")
                alpha_direction={"status":alpha_direction.get("status"),"candidate_questions":alpha_direction.get("candidate_questions",[])[:4],
                    "alternatives":alpha_direction.get("alternatives",[])[:4],"next_research_action":alpha_direction.get("next_research_action"),
                    "outside_advisor_hypotheses_only":advisor.get("advice"),"hypotheses_only":True,
                    "evidence_created":False,"model_execution":alpha_direction.get("model_execution")}
                state["outside_advisor_feedback"]={"event":"NEEDLE_RESEARCH_MORE","hypotheses_only":True,
                    "evidence_created":False,"advice":advisor.get("advice"),"model_execution":advisor.get("model_execution")}
                state["alpha_research_direction"] = alpha_direction
            except Exception as exc:
                state["alpha_research_direction"]={"status":"UNAVAILABLE","error_class":type(exc).__name__,
                    "evidence_created":False,"needle_action_preserved":True}
        contract.persist_state(state,case_id=case_id)
        if repair_count<1:
            next_job=enqueue_job(case_id=case_id,job_type="NEEDLE_RESEARCH_TARGETED_REPAIR",
                completion_receipt_id=receipt_id,repair_attempt=1,
                needle_request={**needle_compact,"alpha_research_direction":alpha_direction},parent_job=job)
            result={"status":"COMPLETED","research_case_id":case_id,"needle_status":"RESEARCH_MORE",
                "reason_code":needle.get("reason_code"),"next_job_id":next_job["job_id"],
                "next_job_type":next_job["job_type"],"notebook_id":state.get("notebook_id")}
            _save_case(case_id,state=state,result=result,status="MORE_RESEARCH_REQUIRED",next_action="WAIT_FOR_TARGETED_RESEARCH_REPAIR")
            return result
        result={"status":"COMPLETED","research_case_id":case_id,"needle_status":"RESEARCH_MORE",
            "reason_code":needle.get("reason_code"),"repair_bound_exhausted":True,
            "notebook_id":state.get("notebook_id"),"no_downstream_handoff":True}
        _save_case(case_id,state=state,result=result,status="MORE_RESEARCH_REQUIRED",next_action="RESEARCH_MORE_BOUNDED_REPAIR_EXHAUSTED")
        return result
    if needle.get("status")!="READY_FOR_DEPARTMENT":
        return {"status":"BLOCKED","reason":"NEEDLE_INVALID_STATUS"}

    state["verification_status"]="READY_FOR_DEPARTMENT"
    state["handoff_package"]=contract.compact_handoff(state,receipt_id=receipt_id,
        library_entry_ids=state.get("library_entry_ids") or [])
    library_result=None; handoff=None
    if contract.CONTRACTS[state["contract_id"]]["is_library"]:
        library_result=contract.persist_library_entry(state,state.get("structured_extraction") or {})
        state["library_entry_ids"]=library_result.get("library_entry_ids",[])
        finalized=contract.finalize_contract(state,receipt_id=receipt_id,
            library_entry_persisted=library_result.get("status")=="PERSISTED",
            web_supplementation_appropriate=bool(state.get("evidence_gaps")))
        if not finalized.get("ok"):
            return {"status":"BLOCKED","reason":"NEEDLE_LIBRARY_DISTILLATION_FAILED","library_status":library_result.get("status")}
    else:
        from operations import nexus_handoff
        if not nexus_handoff.configured():
            return {"status":"WAITING_RESOURCE_WINDOW","resource":"SUPABASE",
                "capability":"department_handoff","resume_condition":"HANDOFF_STORE_AVAILABLE",
                "checkpoint_preserved":True,"reason":"GOVERNED_HANDOFF_STORE_UNAVAILABLE"}
        packet=state["handoff_package"]
        handoff=nexus_handoff.create_handoff(source_department="RESEARCH",
            target_department=needle["next_department"],handoff_type="NOTEBOOK_COMPLETION_CONTRACT",
            topic=str(state.get("objective") or case_id)[:180],
            payload={"research_case_id":case_id,"notebook_contract":packet,
                "continuation":{"owner_department":needle["next_department"],"next_action":"CONSUME_RESEARCH_PACKAGE_AND_CONTINUE_PARENT_OBJECTIVE",
                    "success_criteria":["consume compact evidence package","preserve unresolved facts","continue existing parent objective"]}},
            source_ids=[str(row.get("source_id")) for row in state.get("source_inventory",[]) if row.get("source_id")],
            artifact_refs=[str(state.get("notebook_id"))],
            logical_key=f"notebook-contract:{case_id}:{receipt_id}:{needle['next_department']}")
        if not handoff.get("handoff_id"):
            return {"status":"WAITING_RESOURCE_WINDOW","resource":"SUPABASE",
                "capability":"department_handoff","resume_condition":"HANDOFF_STORE_AVAILABLE",
                "checkpoint_preserved":True,"reason":handoff.get("status") or "HANDOFF_NOT_PERSISTED"}
        state["handoff_status"]="PERSISTED"
        finalized=contract.finalize_contract(state,receipt_id=receipt_id,handoff_persisted=True,
            web_supplementation_appropriate=bool(state.get("evidence_gaps")))
        if not finalized.get("ok"):
            return {"status":"BLOCKED","reason":"NOTEBOOK_CONTRACT_FINALIZATION_FAILED"}
    state["needle_verification"]={**needle_compact,"status":"READY_FOR_DEPARTMENT"}
    state["local_state_ref"]=contract.persist_state(state,case_id=case_id)
    next_department=needle["next_department"]
    result={"status":"COMPLETED","research_case_id":case_id,"research_job_id":state.get("research_job_id"),
        "completion_receipt_id":receipt_id,"needle_receipt_id":needle.get("receipt_id"),
        "needle_status":"READY_FOR_DEPARTMENT","next_department":next_department,
        "handoff_id":(handoff or {}).get("handoff_id"),"library_entry_ids":(library_result or {}).get("library_entry_ids",[]),
        "notebook_id":state.get("notebook_id"),"no_full_notebook_mirror_to_supabase":True}
    _save_case(case_id,state=state,result=result,status="DEPARTMENT_DEVELOPMENT",
        next_action=f"WAIT_FOR_{next_department}_TO_CONTINUE_PARENT_OBJECTIVE")
    return result

