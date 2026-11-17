"""Production Research Room execution adapters for Workflow Fabric.

The Research Case Engine remains the durable authority.  This module binds
bounded manual-goal research and room participants to that existing case
model; it does not create another queue, workflow engine, or database.
"""
from __future__ import annotations

import hashlib
import json
import os
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _room_id(workflow_id: str) -> str:
    digest = hashlib.sha256(workflow_id.encode()).hexdigest()[:20]
    return "rcase_rr_" + digest


def _ensure_step_execution_job(parent_job_id: str, workflow_id: str, step_id: str) -> tuple[str, dict[str, Any]]:
    """Create/reuse a bounded provider-accounting job for one Workflow step."""
    from nexus_agent_platform.durable_jobs import default_store
    budget = {"max_requests": 20, "max_response_bytes": 500_000, "max_tokens": 8_000,
        "max_gpu_seconds": 0, "max_runtime_seconds": 240, "max_resource_creations": 0,
        "max_estimated_cost": 0.0, "max_retries": 1}
    row = default_store().enqueue("RESEARCH", "RESEARCH_CASE_CONTINUATION", priority=65,
        scheduled_at="2099-01-01T00:00:00+00:00", parent_job_id=parent_job_id,
        correlation_id=workflow_id, max_attempts=1,
        idempotency_key=f"workflow-fabric:{workflow_id}:{step_id}:research-execution-v1",
        budget_envelope=budget, governance_context={"source": "WORKFLOW_FABRIC_RESEARCH_STEP",
            "workflow_id": workflow_id, "workflow_step": step_id,
            "controller_owns_execution": True, "provider_budget_class": "ZERO_SPEND_BOUNDED"})
    return str(row.job_id), budget


@contextmanager
def _governed_research_context(*, workflow_id: str, durable_job_id: str, call_id: str,
                               budget: dict[str, Any]):
    """Bind existing provider governance to the parent Workflow Fabric job."""
    if not durable_job_id:
        raise ValueError("DURABLE_WORKFLOW_JOB_ID_REQUIRED")
    values = {"NEXUS_DURABLE_JOB_ID": durable_job_id, "NEXUS_CORRELATION_ID": workflow_id,
        "NEXUS_PROJECT_ID": workflow_id, "NEXUS_DEPARTMENT": "RESEARCH",
        "NEXUS_JOB_TYPE": "RESEARCH_CASE_CONTINUATION",
        "NEXUS_RESEARCH_ROOM_PRODUCTION_CASE": "true",
        "NEXUS_RESEARCH_ROOM_CALL_ID": call_id,
        "NEXUS_DURABLE_EXECUTION_ID": durable_job_id,
        "NEXUS_JOB_BUDGET": json.dumps(budget, separators=(",", ":"))}
    keys = tuple(values)
    previous = {key: os.environ.get(key) for key in keys}
    os.environ.update(values)
    try:
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _save_room(case_id: str, state: dict[str, Any], event: str) -> dict[str, Any]:
    from research import research_case_engine as engine
    case = engine.get_case(case_id)
    if not case:
        raise LookupError("RESEARCH_ROOM_CASE_NOT_FOUND")
    saved = engine._save(case, event, research_room_state=state)
    sync = saved.get("supabase_sync") or {}
    return {"case": saved, "persisted": bool(sync.get("verified") or sync.get("status") == "ENGINE_PERSISTED"),
            "persistence_receipt": sync}


def ensure_room(workflow_id: str, objective: str) -> tuple[str, dict[str, Any]]:
    """Open/join one durable research case keyed to the existing workflow."""
    from research import research_case_engine as engine

    objective = " ".join(str(objective or "").split())[:2400]
    result = engine.open_or_join_case(
        objective=objective, objective_family="BUSINESS_FUNDING_RESEARCH",
        business_or_nexus_goal=("Prepare evidence-backed GoClear business funding launch research for workflow "
            + workflow_id),
        owner_department="RESEARCH", primary_question=objective,
        project_id=workflow_id, objective_id=workflow_id,
        originating_goal_id=workflow_id, force_existing=True,
        depth_budget={"max_sources": 8, "max_questions": 8, "max_followups": 3},
    )
    case = result.get("case")
    if not isinstance(case, dict) or not case.get("case_id"):
        raise RuntimeError("RESEARCH_ROOM_CASE_OPEN_FAILED:" + str(result.get("reason") or "unknown"))
    case_id = str(case["case_id"])

    source_id = "manual-objective-" + hashlib.sha256(workflow_id.encode()).hexdigest()[:18]
    if not any(str(row.get("source_id") or "") == source_id for row in case.get("sources") or []):
        attached = engine.add_source(case_id, {
            "source_id": source_id, "source_type": "MANUAL_RESEARCH_OBJECTIVE",
            "title": "Ray supplied GoClear launch objective", "content": objective,
            "source_class": "OWNER_SUPPLIED_CONTEXT", "provenance": {"workflow_id": workflow_id},
            "content_hash": hashlib.sha256(objective.encode()).hexdigest(),
        })
        if not attached.get("ok"):
            raise RuntimeError("MANUAL_OBJECTIVE_PERSISTENCE_FAILED")
        case = attached["case"]

    state = dict(case.get("research_room_state") or {})
    state.update({
        "schema_version": "nexus.research-room.v1", "room_id": case_id,
        "workflow_id": workflow_id, "objective": objective,
        "autonomous_research_ingestion": False, "manual_research_intake": True,
        "status": state.get("status", "OPEN"), "updated_at": _now(),
    })
    participants = state.setdefault("participants", {})
    for name in ("RESEARCH_LEAD", "ALPHA", "SOURCE_ANALYST", "FACT_CHECKER", "SYNTHESIZER"):
        participants.setdefault(name, {"status": "READY"})
    saved = _save_room(case_id, state, "RESEARCH_ROOM_BOUND_TO_WORKFLOW")
    if not saved["persisted"]:
        raise RuntimeError("RESEARCH_ROOM_STATE_PERSISTENCE_UNVERIFIED")
    return case_id, saved["case"]


def manual_intake(*, workflow_id: str, objective: str, input_type: str,
                  content: str, reference: str | None = None) -> dict[str, Any]:
    """Attach one explicit owner-supplied source; never runs discovery itself."""
    allowed = {"TEXT", "TRANSCRIPT", "URL", "PDF_REFERENCE", "VIDEO_REFERENCE",
               "ARTICLE", "BUSINESS_IDEA", "CLAIM", "QUESTION", "SOCIAL_POST"}
    kind = str(input_type or "").upper()
    if kind not in allowed or not str(content or reference or "").strip():
        return {"status": "VALIDATION_FAILED", "error_code": "MANUAL_RESEARCH_INPUT_INVALID"}
    room_id, case = ensure_room(workflow_id, objective)
    text = " ".join(str(content or "").split())[:16000]
    ref = " ".join(str(reference or "").split())[:1200]
    identity = ref or hashlib.sha256(text.encode()).hexdigest()
    source_id = "manual-" + hashlib.sha256((kind + "|" + identity).encode()).hexdigest()[:20]
    from research import research_case_engine as engine
    attached = engine.add_source(room_id, {
        "source_id": source_id, "source_type": kind,
        "url": ref if ref.startswith(("http://", "https://")) else None,
        "reference": ref or None, "title": ref[:240] or kind,
        "content": text or None, "extracted_evidence": text or None,
        "source_class": "OWNER_SUPPLIED", "content_hash": hashlib.sha256((text + ref).encode()).hexdigest(),
        "provenance": {"requested_by": "RAY", "manual_intake": True},
    })
    if not attached.get("ok"):
        return {"status": "RETRY", "error_code": "MANUAL_RESEARCH_SOURCE_PERSISTENCE_FAILED", "room_id": room_id}
    state = dict(attached["case"].get("research_room_state") or {})
    inputs = list(state.get("manual_inputs") or [])
    if not any(row.get("source_id") == source_id for row in inputs if isinstance(row, dict)):
        inputs.append({"source_id": source_id, "input_type": kind, "reference": ref or None,
                       "content_hash": hashlib.sha256((text + ref).encode()).hexdigest(), "added_at": _now()})
    state.update(manual_inputs=inputs[-100:], updated_at=_now())
    saved = _save_room(room_id, state, "MANUAL_RESEARCH_SOURCE_ATTACHED")
    return {"status": "COMPLETE" if saved["persisted"] else "RETRY", "room_id": room_id,
            "source_id": source_id, "source_count": len(saved["case"].get("sources") or []),
            "persistence_receipt": saved["persistence_receipt"]}


def steer(*, workflow_id: str, objective: str, instruction: str,
          room_id: str | None = None) -> dict[str, Any]:
    """Append one bounded owner instruction to the existing room without restarting it."""
    text = " ".join(str(instruction or "").split())[:1200]
    if not text:
        return {"status": "VALIDATION_FAILED", "error_code": "STEERING_INSTRUCTION_REQUIRED"}
    room_id, case = ensure_room(workflow_id, objective)
    state = dict(case.get("research_room_state") or {})
    rows = list(state.get("steering_instructions") or [])
    instruction_id = "steer_" + hashlib.sha256((workflow_id + "|" + text.casefold()).encode()).hexdigest()[:18]
    prior = next((row for row in rows if isinstance(row, dict) and row.get("instruction_id") == instruction_id), None)
    if not prior:
        rows.append({"instruction_id": instruction_id, "instruction": text,
            "requested_by": "RAY", "status": "PENDING", "added_at": _now()})
    state.update({"steering_instructions": rows[-50:], "work_graph_updated_at": _now(),
        "next_action": "APPLY_OWNER_STEERING_TO_ACTIVE_RESEARCH", "updated_at": _now()})
    saved = _save_room(room_id, state, "RESEARCH_ROOM_OWNER_STEERING_ADDED")
    graph_updated = False
    if saved["persisted"]:
        from nexus_agent_platform.workflow_fabric import default_state_store
        store = default_state_store()
        workflow = next((row for row in store.list(limit=100) if row.get("workflow_id") == workflow_id), None)
        if workflow and workflow.get("durable_job_id"):
            graph = list(workflow.get("dynamic_tasks") or [])
            if not any(row.get("task_id") == instruction_id for row in graph if isinstance(row, dict)):
                graph.append({"task_id": instruction_id, "instruction": text, "status": "PENDING",
                    "applies_to_step": workflow.get("current_step"), "requested_by": "RAY",
                    "added_at": _now(), "continuation_policy": "PRESERVE_CURRENT_WORKFLOW"})
            workflow["dynamic_tasks"] = graph[-50:]
            workflow["steering_instructions"] = rows[-50:]
            workflow["revision"] = int(workflow.get("revision", 0)) + 1
            workflow["updated_at"] = _now()
            store.save(workflow["durable_job_id"], workflow)
            graph_updated = True
    return {"status": "COMPLETE" if saved["persisted"] and graph_updated else "RETRY", "room_id": room_id,
        "instruction_id": instruction_id, "deduplicated": bool(prior),
        "workflow_id": workflow_id, "research_room_state_persisted": saved["persisted"],
        "workflow_graph_updated": graph_updated,
        "persistence_receipt": saved["persistence_receipt"]}


def _advisor_call(role: str, objective: str, context: dict[str, Any], *,
                  workflow_id: str, durable_job_id: str,
                  budget: dict[str, Any]) -> dict[str, Any]:
    """Use the existing Research Room provider router with its no-new-spend path."""
    from .advisor_router import AdvisorRouter
    with _governed_research_context(workflow_id=workflow_id, durable_job_id=durable_job_id,
            call_id=f"{workflow_id}:{role.lower()}", budget=budget):
        return AdvisorRouter(free_only=True).ask(role=role, case_context=context, objective=objective)


def deep_research(*, workflow_id: str, durable_job_id: str, objective: str) -> dict[str, Any]:
    """Run targeted public follow-up, Alpha analysis, and durable evidence capture."""
    from research import research_case_engine as engine
    from .source_tools import SourceTools

    execution_job_id, budget = _ensure_step_execution_job(durable_job_id, workflow_id, "DEEP_RESEARCH")
    room_id, case = ensure_room(workflow_id, objective)
    state = dict(case.get("research_room_state") or {})
    state["status"] = "RESEARCHING"
    state["plan"] = {
        "goal": "Gather bounded public evidence relevant to the owner-supplied GoClear launch objective.",
        "subtasks": ["funding need and readiness evidence", "provider positioning and offer patterns",
                     "risks, documentation gaps, and unresolved claims"],
        "external_actions": 0, "autonomous_ingestion": False, "created_at": state.get("created_at") or _now(),
    }
    question_specs = [
        ("funding-readiness", "Small business funding eligibility, readiness, and documentation gaps: what do official or credible public sources say?"),
        ("provider-positioning", "Small business funding provider positioning, service offers, and customer next steps based on public sources."),
        ("funding-risks", "Small business financing costs, qualification uncertainty, and borrower risks: public evidence and warnings."),
    ]
    questions = []
    for suffix, question in question_specs:
        qid = "rrq_" + hashlib.sha256(f"{workflow_id}:{suffix}".encode()).hexdigest()[:18]
        if not any(str(row.get("question_id") or "") == qid for row in case.get("open_questions") or []):
            added = engine.add_question(room_id, question, why_it_matters="Supports the owner-supplied GoClear business funding launch objective.",
                best_source_classes=["official/public primary sources", "public provider terms", "government guidance"])
            case = added.get("case") or case
        row = next((x for x in case.get("open_questions") or [] if question == x.get("question")), None)
        if row:
            questions.append({"production_question_id": row.get("question_id"), "question": question, "case_id": room_id})
    if not questions:
        return {"status": "VALIDATION_FAILED", "error_code": "RESEARCH_QUESTIONS_NOT_PERSISTED", "room_id": room_id}

    # Reuse bounded evidence already attached to this owner-directed room
    # (including an explicit manual source or targeted follow-up). Only invoke
    # discovery when the room has no usable evidence; this prevents retries
    # from discarding evidence just because a provider parser is degraded.
    reusable = [row for row in (case.get("sources") or []) if isinstance(row, dict)
        and (str(row.get("source_class") or "").upper() in {"OWNER_SUPPLIED", "TARGETED_PUBLIC_FOLLOWUP"}
             or bool((row.get("provenance") or {}).get("bounded_public_followup")))
        and str(row.get("extracted_evidence") or row.get("summary") or row.get("content") or "").strip()]
    if reusable:
        source_rows = [{"source_id": str(row.get("source_id") or ""), "url": row.get("url") or row.get("reference"),
            "title": row.get("title"), "source_type": row.get("source_type") or "OWNER_SUPPLIED",
            "summary": row.get("summary") or row.get("extracted_evidence") or row.get("content"),
            "claims": [str(row.get("extracted_evidence") or row.get("summary") or row.get("content"))[:1200]],
            "source_content_hash": row.get("content_hash") or row.get("source_content_hash"),
            "method": (row.get("provenance") or {}).get("method", "PERSISTED_ROOM_SOURCE"),
            "question_id": row.get("question_id")} for row in reusable[:3]]
        acquisition = {"sources": source_rows, "source_attempts": [], "method_failures": [],
            "limitation": None, "reused_persisted_room_evidence": True}
    else:
        # Existing Nexus/Hermes search and public page extraction routes. A
        # missing route is recorded as a limitation; broad ingestion stays off.
        with _governed_research_context(workflow_id=workflow_id, durable_job_id=execution_job_id,
                call_id=f"{workflow_id}:alpha-source-followup", budget=budget):
            acquisition = SourceTools(timeout=12).research_questions(objective, questions[:3])
    source_rows = acquisition.get("sources") or []
    persisted_sources = []
    evidence = []
    for index, row in enumerate(source_rows[:3]):
        url = str(row.get("url") or "")
        source_id = str(row.get("source_id") or "rrsrc_" + hashlib.sha256(url.encode()).hexdigest()[:20])
        compact_claims = [str(c)[:500] for c in (row.get("claims") or [])[:5]]
        attached = engine.add_source(room_id, {
            "source_id": source_id, "url": url, "title": str(row.get("title") or url)[:240],
            "source_type": str(row.get("source_type") or "PUBLIC_WEB"),
            "source_class": "PUBLIC_WEB_UNVERIFIED", "summary": str(row.get("summary") or "")[:1800],
            "extracted_evidence": "\n".join(compact_claims)[:3000],
            "content_hash": row.get("source_content_hash"), "source_content_hash": row.get("source_content_hash"),
            "retrieved_at": _now(), "provenance": {"method": row.get("method"), "workflow_id": workflow_id,
                "question_id": row.get("question_id"), "bounded_public_followup": True},
        })
        if not attached.get("ok"):
            continue
        persisted_sources.append({"source_id": source_id, "url": url, "title": row.get("title"),
            "source_type": row.get("source_type"), "source_class": "PUBLIC_WEB_UNVERIFIED",
            "summary": str(row.get("summary") or "")[:1000], "claims": compact_claims,
            "content_hash": row.get("source_content_hash"), "question_id": row.get("question_id")})
        evidence.append({"schema_version": "nexus.evidence.v1", "evidence_id": source_id,
            "status": "SUCCESS", "source": {"source_type": row.get("source_type") or "PUBLIC_WEB",
                "original_reference": url, "final_url": url, "retrieved_at": _now(),
                "provenance": {"method": row.get("method"), "question_id": row.get("question_id")}},
            "integrity": {"material_hash": row.get("source_content_hash")},
            "content": {"title": row.get("title"), "normalized_text_or_markdown": "\n".join(compact_claims)[:2500]}})
    if not persisted_sources:
        state.update({"status": "WAITING_DEPENDENCY", "source_attempts": acquisition.get("source_attempts") or [],
            "source_limitations": acquisition.get("method_failures") or [acquisition.get("limitation")],
            "updated_at": _now()})
        _save_room(room_id, state, "RESEARCH_ROOM_SOURCE_FOLLOWUP_LIMITED")
        return {"status": "WAITING_DEPENDENCY", "error_code": "NO_MATERIAL_PUBLIC_EVIDENCE_ACQUIRED",
            "room_id": room_id, "source_attempt_count": len(acquisition.get("source_attempts") or []),
            "partial_output": {"source_limitations": state["source_limitations"]}}

    source_context = {"case_id": room_id, "original_request": objective,
        "provided_input": objective, "source_references": persisted_sources,
        "source_report": {"status": "SOURCE_ACQUIRED", "sources": persisted_sources,
            "summary": "\n".join(row.get("summary") or "" for row in persisted_sources)[:2400]},
        "findings": [{"kind": "SOURCE_OBSERVATION", "source_id": row["source_id"],
            "claim": claim, "status": "UNVERIFIED", "confidence": "LOW", "fact_or_interpretation": "SOURCE_OBSERVATION"}
            for row in persisted_sources for claim in row["claims"][:3]],
        "questions": [{"question": row.get("question"), "status": "OPEN"} for row in questions[:3]],
        "unresolved_items": acquisition.get("method_failures") or [],
        "metadata": {"research_type": "BUSINESS_FUNDING_RESEARCH", "research_complexity": "HIGH",
            "daily_research_spend_usd": 0.0, "high_value_case": False,
            "autonomous_research_ingestion": False}}
    prior_finding = next((row for row in reversed(case.get("findings") or []) if isinstance(row, dict)
        and row.get("kind") == "ALPHA_ANALYSIS" and row.get("source_ids")), None)
    if prior_finding:
        analysis = {"analysis": prior_finding.get("claim") or prior_finding.get("summary") or "",
            "confidence": prior_finding.get("confidence"), "provider": prior_finding.get("provider"),
            "model": prior_finding.get("model"), "reused_persisted_alpha_result": True}
    else:
        analysis = _advisor_call("PRIMARY_RESEARCH_ADVISOR", objective,
            {**source_context, "analysis_requirements": ["central claims", "fact vs interpretation", "source quality",
                "unsupported claims", "contradictions", "missing information", "business implications", "uncertainty",
                "targeted next research actions"]}, workflow_id=workflow_id, durable_job_id=execution_job_id,
                budget=budget)
    analysis_text = str(analysis.get("analysis") or "").strip()
    if not analysis_text:
        state.update({"status": "PARTIAL", "source_ids": [x["source_id"] for x in persisted_sources],
            "source_attempts": acquisition.get("source_attempts") or [], "updated_at": _now()})
        _save_room(room_id, state, "RESEARCH_ROOM_ALPHA_PARTIAL")
        return {"status": "PARTIAL", "error_code": str(analysis.get("reason") or "ALPHA_ADVISOR_UNAVAILABLE"),
            "room_id": room_id, "source_count": len(persisted_sources),
            "partial_output": {"source_ids": state["source_ids"], "source_attempts": state["source_attempts"]}}

    # Analysis output is explicitly interpretive and linked to its source set;
    # it does not turn a search observation into a verified fact.
    finding = {"finding_id": "alpha_" + hashlib.sha256((workflow_id + analysis_text).encode()).hexdigest()[:20],
        "kind": "ALPHA_ANALYSIS", "claim": analysis_text[:8000], "summary": analysis_text[:3000],
        "source_ids": [x["source_id"] for x in persisted_sources],
        "evidence_ids": [x["source_id"] for x in persisted_sources],
        "status": "ANALYSIS_RECORDED", "confidence": str(analysis.get("confidence") or "UNSPECIFIED"),
        "fact_or_interpretation": "INTERPRETATION", "provider": analysis.get("provider"),
        "model": analysis.get("model"), "recorded_at": _now()}
    saved_finding = engine.record_finding(room_id, finding)
    if not saved_finding.get("ok"):
        return {"status": "RETRY", "error_code": "ALPHA_FINDING_PERSISTENCE_FAILED", "room_id": room_id,
            "partial_output": {"source_ids": [x["source_id"] for x in persisted_sources]}}

    from nexus_agent_platform.alpha_research import build_research_job, run_alpha_research
    alpha_job = build_research_job(objective=objective, research_type="FUNDING_PROGRAM_RESEARCH",
        requested_by="workflow_fabric", limits={"max_sources": 3, "max_model_calls": 1,
        "max_evidence_jobs": 3, "max_runtime_seconds": 240, "max_output_chars": 8000})
    alpha_pack = run_alpha_research(alpha_job, evidence, runtime_root=None)
    state.update({"status": "FACT_CHECK_PENDING", "plan": state.get("plan"),
        "source_ids": [x["source_id"] for x in persisted_sources],
        "evidence_count": len(evidence), "alpha_finding_id": finding["finding_id"],
        "alpha_provider": analysis.get("provider"), "alpha_model": analysis.get("model"),
        "alpha_analysis": analysis_text[:8000], "source_attempts": acquisition.get("source_attempts") or [],
        "source_limitations": acquisition.get("method_failures") or [], "updated_at": _now()})
    saved = _save_room(room_id, state, "RESEARCH_ROOM_ALPHA_ANALYSIS_RECORDED")
    if not saved["persisted"]:
        return {"status": "RETRY", "error_code": "RESEARCH_ROOM_PERSISTENCE_UNVERIFIED", "room_id": room_id}
    return {"status": "COMPLETE", "room_id": room_id, "research_room_state_persisted": True,
        "research_execution_job_id": execution_job_id,
        "source_count": len(persisted_sources), "evidence_count": len(evidence),
        "source_ids": [x["source_id"] for x in persisted_sources],
        "alpha_finding_id": finding["finding_id"], "alpha_used": True,
        "alpha_model_profile": "RESEARCH_DEEP", "alpha_provider": analysis.get("provider"),
        "alpha_model": analysis.get("model"), "alpha_analysis": analysis_text[:8000],
        "alpha_pack_receipt_id": alpha_pack["receipt"]["receipt_id"],
        "artifact_ids": [alpha_pack["receipt"]["research_pack_ref"]],
        "generation_receipt_id": alpha_pack["receipt"]["receipt_id"],
        "source_limitations": state["source_limitations"],
        "persistence_receipt": saved["persistence_receipt"]}


def fact_check(*, workflow_id: str, durable_job_id: str, room_id: str | None) -> dict[str, Any]:
    from research import research_case_engine as engine
    if not room_id:
        room_id = _room_id(workflow_id)
    case = engine.get_case(room_id)
    if not case:
        return {"status": "WAITING_DEPENDENCY", "error_code": "RESEARCH_ROOM_CASE_NOT_FOUND"}
    execution_job_id, budget = _ensure_step_execution_job(durable_job_id, workflow_id, "FACT_CHECK")
    state = dict(case.get("research_room_state") or {})
    findings = [row for row in case.get("findings") or [] if isinstance(row, dict)
        and row.get("kind") in {"ALPHA_ANALYSIS", "FACT_CHECK"}]
    sources = list(case.get("sources") or [])
    source_summaries = [{"source_id": row.get("source_id"), "url": row.get("url"),
        "title": row.get("title"), "evidence": str(row.get("extracted_evidence") or row.get("summary") or "")[:1800]}
        for row in sources[:8] if isinstance(row, dict)]
    context = {"case_id": room_id, "provided_input": state.get("objective"),
        "source_references": source_summaries, "findings": findings,
        "metadata": {"research_type": "BUSINESS_FUNDING_RESEARCH", "daily_research_spend_usd": 0.0}}
    result = _advisor_call("FACT_CHECKER", "Assess each material claim against only the supplied source evidence. "
        "Distinguish supported, partially supported, unsupported, contradicted, and unverified. "
        "Identify misleading framing, unverifiable business/financial claims, and missing evidence. "
        "Return source IDs for every assessment; do not infer missing numbers.", context,
        workflow_id=workflow_id, durable_job_id=execution_job_id, budget=budget)
    analysis = str(result.get("analysis") or "").strip()
    if not analysis:
        return {"status": "PARTIAL", "error_code": str(result.get("reason") or "FACT_CHECK_ADVISOR_UNAVAILABLE"),
            "room_id": room_id, "source_count": len(source_summaries),
            "fact_check_result": {"status": "UNVERIFIED", "reason": "No authorized fact-check analysis returned."}}
    record = {"kind": "FACT_CHECK", "finding_id": "fc_" + hashlib.sha256((workflow_id + analysis).encode()).hexdigest()[:20],
        "summary": analysis[:6000], "status": "REVIEWED_WITH_LIMITATIONS", "confidence": result.get("confidence") or "UNSPECIFIED",
        "source_ids": [str(row.get("source_id")) for row in source_summaries if row.get("source_id")],
        "provider": result.get("provider"), "model": result.get("model"),
        "fact_or_interpretation": "EVIDENCE_ASSESSMENT", "recorded_at": _now(),
        "execution_job_id": execution_job_id}
    stored = engine.record_finding(room_id, record)
    state.update({"status": "SYNTHESIS_PENDING", "fact_check": record, "updated_at": _now()})
    saved = _save_room(room_id, state, "RESEARCH_ROOM_FACT_CHECK_RECORDED")
    ok = bool(stored.get("ok") and saved["persisted"])
    return {"status": "COMPLETE" if ok else "RETRY", "room_id": room_id,
        "fact_check_result": {"status": record["status"], "summary": record["summary"],
            "source_ids": record["source_ids"], "provider": record["provider"], "model": record["model"]},
        "research_room_state_persisted": ok, "generation_receipt_id": "fact-check-" + record["finding_id"]}


def synthesize(*, workflow_id: str, durable_job_id: str, room_id: str | None) -> dict[str, Any]:
    from research import research_case_engine as engine
    if not room_id:
        room_id = _room_id(workflow_id)
    case = engine.get_case(room_id)
    if not case:
        return {"status": "WAITING_DEPENDENCY", "error_code": "RESEARCH_ROOM_CASE_NOT_FOUND"}
    execution_job_id, budget = _ensure_step_execution_job(durable_job_id, workflow_id, "RESEARCH_SYNTHESIS")
    state = dict(case.get("research_room_state") or {})
    findings = [row for row in case.get("findings") or [] if isinstance(row, dict)]
    source_ids = [str(row.get("source_id")) for row in case.get("sources") or []
        if isinstance(row, dict) and row.get("source_id")]
    context = {"case_id": room_id, "provided_input": state.get("objective"),
        "source_references": [{"source_id": row.get("source_id"), "url": row.get("url"),
            "title": row.get("title"), "evidence": str(row.get("extracted_evidence") or row.get("summary") or "")[:1300]}
            for row in (case.get("sources") or [])[:8] if isinstance(row, dict)],
        "findings": findings[-12:], "metadata": {"research_type": "BUSINESS_FUNDING_RESEARCH"}}
    result = _advisor_call("RESEARCH_SYNTHESIZER", "Synthesize this evidence for Nexus. Address: what sources say; "
        "evidence that supports it; what is not proven; Nexus business, marketing, product and operations implications; "
        "risks; open research gaps; recommended actions; likely department handoffs; and a concise Nova executive view. "
        "Separate facts from interpretation and cite source IDs. Do not invent metrics or promise funding approval.", context,
        workflow_id=workflow_id, durable_job_id=execution_job_id, budget=budget)
    analysis = str(result.get("analysis") or "").strip()
    if not analysis:
        return {"status": "PARTIAL", "error_code": str(result.get("reason") or "SYNTHESIS_ADVISOR_UNAVAILABLE"),
            "room_id": room_id, "partial_output": {"source_ids": source_ids}}
    synthesis = {"synthesis_id": "synth_" + hashlib.sha256((workflow_id + analysis).encode()).hexdigest()[:20],
        "title": "GoClear Business Funding Research Synthesis", "summary": analysis[:8000],
        "claims": [{"claim": str(row.get("summary") or row.get("claim") or "")[:800],
            "status": row.get("status", "UNVERIFIED"), "source_ids": row.get("source_ids") or []}
            for row in findings[-10:] if str(row.get("summary") or row.get("claim") or "").strip()],
        "source_ids": source_ids, "uncertainties": list(state.get("source_limitations") or [])[:10],
        "provider": result.get("provider"), "model": result.get("model"), "recorded_at": _now(),
        "fact_or_interpretation": "SYNTHESIS", "execution_job_id": execution_job_id}
    handoff = {"handoff_id": "research-handoff-" + hashlib.sha256((workflow_id + synthesis["synthesis_id"] + "CLYDE").encode()).hexdigest()[:18],
        "target_domain_agent": "CLYDE", "objective": "Use evidence-backed funding preparation findings in the GoClear business plan.",
        "summary": analysis[:2200], "evidence": source_ids[:12], "artifacts": [synthesis["synthesis_id"]],
        "constraints": ["No lender approval promises", "No autonomous underwriting", "Public SBA guidance is general and not borrower-specific"],
        "open_questions": list(state.get("source_limitations") or [])[:8],
        "recommended_next_action": "BUILD_GOCLEAR_FUNDING_READINESS_PLAN", "approval_required": False}
    from research import research_case_engine as engine
    stored = engine.record_synthesis(room_id, claims=synthesis["claims"], agreements=[], disagreements=[],
        uncertainties=synthesis["uncertainties"], source_ids=source_ids)
    if not stored.get("ok"):
        return {"status": "RETRY", "error_code": stored.get("reason") or "SYNTHESIS_PERSISTENCE_FAILED", "room_id": room_id}
    state.update({"status": "SYNTHESIS_READY", "synthesis": synthesis, "department_handoff": handoff, "updated_at": _now()})
    saved = _save_room(room_id, state, "RESEARCH_ROOM_SYNTHESIS_RECORDED")
    return {"status": "COMPLETE" if saved["persisted"] else "RETRY", "room_id": room_id,
        "research_room_state_persisted": saved["persisted"], "synthesis": synthesis,
        "generation_receipt_id": synthesis["synthesis_id"], "handoff": handoff,
        "persistence_receipt": saved["persistence_receipt"]}
