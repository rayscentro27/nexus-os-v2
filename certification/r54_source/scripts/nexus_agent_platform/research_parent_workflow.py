"""Universal, bounded parent workflow for owner-assigned Research missions.

This module is deliberately adapter-driven: it owns continuation decisions and
the parent-state contract, while existing Research, advisor, Needle, library,
and handoff components remain responsible for their respective operations.
It does not perform network, model, NotebookLM, or queue work at import time.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Callable, Mapping

WORKFLOW = (
    "SOURCE_UNDERSTANDING", "KNOWLEDGE_RECONCILIATION", "ADVISOR_REVIEW",
    "QUESTION_GENERATION", "FOLLOWUP_RESEARCH", "NEEDLE_REVIEW",
    "SYNTHESIS", "CATEGORY_LIBRARY_ROUTING", "HANDOFF",
)
TERMINAL_CONDITIONS = {
    "NEW_INCREMENTAL_CASH_REQUIRED", "TRUE_TECHNICAL_BLOCKER", "RAY_ACTION_REQUIRED",
}
CHILD_ACTIVE = {"READY", "RUNNING", "REPAIRING", "REROUTING"}
QUESTION_STATES = {"OPEN", "ANSWERED", "PARTIAL", "UNVERIFIED", "NOT_APPLICABLE"}


def new_parent(*, objective_id: str, original_objective: str,
               source_url: str | None = None, source_type: str | None = None,
               research_scope: str | None = None, current_context: Mapping[str, Any] | None = None,
               subject_domain: str | None = None) -> dict[str, Any]:
    """Create an in-memory parent record; persistence is supplied by its caller."""
    if not objective_id or not str(original_objective).strip():
        raise ValueError("RESEARCH_PARENT_ID_AND_OBJECTIVE_REQUIRED")
    return {
        "schema_version": "nexus.research-parent.v1", "objective_id": str(objective_id),
        "original_objective": str(original_objective).strip(), "source_url": source_url,
        "source_type": str(source_type or "UNKNOWN").upper(),
        "research_scope": research_scope, "current_context": dict(current_context or {}),
        "subject_domain": str(subject_domain or "UNKNOWN").upper(), "status": "IN_PROGRESS",
        "stage_status": {}, "source_understanding": None, "knowledge_reconciliation": None,
        "advisor_findings": None, "questions": [], "evidence": [], "test_results": [],
        "needle": None, "synthesis": None, "action_owner": None, "next_department": None,
        "handoff": None, "terminal_condition": None, "continuation_sequence": 0,
        "followup_attempts": 0, "needle_repair_attempts": 0, "workflow_history": [],
    }


def _questions(state: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = state.get("questions") or []
    return [dict(row) for row in rows if isinstance(row, Mapping)]


def _open_questions(state: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [row for row in _questions(state)
            if str(row.get("status") or "OPEN").upper() in {"OPEN", "PARTIAL", "UNVERIFIED"}
            and row.get("needs_followup", True)]


def _source_text(state: Mapping[str, Any]) -> str:
    source = state.get("source_understanding") or {}
    return str(source.get("summary") or source.get("subject") or "")[:2400]


def select_next_action(state: Mapping[str, Any]) -> str | None:
    """Select the next bounded action; negative findings never imply completion."""
    if state.get("status") == "COMPLETE":
        return None
    if state.get("terminal_condition") in TERMINAL_CONDITIONS:
        return None
    status = state.get("stage_status") or {}
    if not state.get("source_understanding"):
        return "SOURCE_UNDERSTANDING"
    if not state.get("knowledge_reconciliation"):
        return "KNOWLEDGE_RECONCILIATION"
    if not state.get("advisor_findings"):
        return "ADVISOR_REVIEW"
    if not status.get("QUESTION_GENERATION"):
        return "QUESTION_GENERATION"
    # A bounded follow-up pass answers what can be answered. Remaining
    # uncertainty is carried to synthesis instead of orphaning the parent.
    needle_state = state.get("needle") or {}
    # A RESEARCH_MORE finding gets one bounded follow-up before synthesis.
    # Once synthesis exists, the parent must advance to category routing and
    # handoff; letting Needle's earlier status win here schedules SYNTHESIS
    # forever and strands the actionable package.
    if str(needle_state.get("status") or "").upper() == "RESEARCH_MORE" and not state.get("synthesis"):
        if int(state.get("needle_repair_attempts", 0)) < 1 and _open_questions(state):
            return "FOLLOWUP_RESEARCH"
        return "SYNTHESIS"
    if _open_questions(state) and int(state.get("followup_attempts", 0)) < 2:
        return "FOLLOWUP_RESEARCH"
    if not state.get("needle"):
        return "NEEDLE_REVIEW"
    if not state.get("synthesis"):
        return "SYNTHESIS"
    if not state.get("category_library_routing"):
        return "CATEGORY_LIBRARY_ROUTING"
    handoff = state.get("handoff") or {}
    if handoff.get("handoff_id") and (state.get("next_department") or state.get("action_owner")):
        return None
    return "HANDOFF"


def _normalize_questions(rows: Any) -> list[dict[str, Any]]:
    out = []
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, Mapping) or not str(row.get("question") or "").strip():
            continue
        status = str(row.get("status") or "OPEN").upper()
        if status not in QUESTION_STATES:
            status = "OPEN"
        out.append({"question": str(row["question"]).strip(), "status": status,
            "answer": row.get("answer"), "evidence_refs": list(row.get("evidence_refs") or []),
            "confidence": row.get("confidence"),
            "needs_followup": bool(row.get("needs_followup", status in {"OPEN", "PARTIAL", "UNVERIFIED"})),
            "related_action": row.get("related_action")})
    return out


def apply_action_result(state: dict[str, Any], action: str, result: Mapping[str, Any]) -> dict[str, Any]:
    """Apply one stage result to parent state without interpreting findings as stop signals."""
    action = str(action).upper()
    value = dict(result)
    result_status = str(value.get("status") or "COMPLETED").upper()
    # Needle's RESEARCH_MORE is a completed review with a bounded list of
    # uncovered questions. Persist the review before selecting follow-up so
    # the parent cannot repeat Needle indefinitely or lose its findings.
    if action == "NEEDLE_REVIEW" and result_status == "RESEARCH_MORE":
        state["needle"] = value
        for question in value.get("missing_questions") or []:
            state["questions"] = _normalize_questions(_questions(state) + [{
                "question": question, "status": "OPEN", "needs_followup": True}])
        state.setdefault("stage_status", {})[action] = result_status
        state["status"] = "IN_PROGRESS"
        state["continuation_required"] = False
        state.setdefault("workflow_history", []).append({"action": action,
            "status": result_status, "result_ref": value.get("result_ref")})
        return state
    # An unavailable research method is a finding about that method. It must
    # not repeatedly schedule the same stage or stop the root objective. Keep
    # the limitation in parent state and let the next stage proceed with the
    # evidence already available.
    unavailable = {"CONTINUATION_REQUIRED", "WAITING", "WAITING_RESOURCE_WINDOW",
                   "ADVISOR_UNAVAILABLE", "SOURCE_INSUFFICIENT", "NO_EXECUTION",
                   "SCOPE_UNRESOLVED", "RESEARCH_MORE", "RETRYABLE", "BLOCKED",
                   "FAILED", "UNAVAILABLE", "POLICY_DENIED"}
    if result_status in unavailable and action in {
            "SOURCE_UNDERSTANDING", "KNOWLEDGE_RECONCILIATION", "ADVISOR_REVIEW",
            "QUESTION_GENERATION", "FOLLOWUP_RESEARCH"}:
        state.setdefault("stage_status", {})[action] = f"{action}_UNAVAILABLE_WITH_FINDING"
        finding = {"method": action, "status": result_status,
                   "reason": value.get("reason") or value.get("error") or value.get("blocker")}
        state.setdefault("method_failures", []).append(finding)
        if action == "SOURCE_UNDERSTANDING":
            source_url = state.get("source_url")
            state["source_understanding"] = {"status": "SOURCE_INCOMPLETE",
                "subject": source_url or state.get("original_objective"),
                "summary": "Source acquisition methods were unavailable; continue with available evidence and preserve this limitation.",
                "source_url": source_url, "method_failure": finding}
            state.setdefault("evidence", []).append({"ref": source_url, "status": "UNVERIFIED",
                "limitation": "SOURCE_ACQUISITION_METHODS_UNAVAILABLE"})
        elif action == "KNOWLEDGE_RECONCILIATION":
            state["knowledge_reconciliation"] = {"relationship": "NEW", "lookup": "UNAVAILABLE",
                "prior_summary": None, "material_changes": [], "method_failure": finding}
        elif action == "ADVISOR_REVIEW":
            state["advisor_findings"] = {"status": "ADVISOR_UNAVAILABLE",
                "subject_interpretation": _source_text(state) or state.get("original_objective"),
                "questions": [], "uncertainty": [finding], "recommended_next_actions": []}
        elif action == "QUESTION_GENERATION":
            defaults = [
                "What material claims about the subject are supported by available evidence?",
                "What costs, constraints, risks, and alternatives remain relevant to the objective?",
                "What bounded next action would validate the recommendation?",
            ]
            existing = {str(row.get("question", "")).casefold() for row in _questions(state)}
            state["questions"] = _questions(state) + _normalize_questions([
                {"question": question} for question in defaults if question.casefold() not in existing])
        elif action == "FOLLOWUP_RESEARCH":
            state["followup_attempts"] = int(state.get("followup_attempts", 0)) + 1
            for question in state.get("questions") or []:
                if str(question.get("status") or "OPEN").upper() in {"OPEN", "PARTIAL", "UNVERIFIED"}:
                    question.update(status="UNVERIFIED", needs_followup=False,
                        answer="Follow-up research method unavailable; retained as unresolved uncertainty.")
        state["status"] = "IN_PROGRESS"
        state["continuation_required"] = False
        state.setdefault("workflow_history", []).append({"action": action,
            "status": state["stage_status"][action], "result_ref": value.get("result_ref"),
            "finding": finding})
        return state
    if result_status in {"CONTINUATION_REQUIRED", "WAITING", "WAITING_RESOURCE_WINDOW",
                         "ADVISOR_UNAVAILABLE", "SOURCE_INSUFFICIENT", "NO_EXECUTION",
                         "SCOPE_UNRESOLVED", "RESEARCH_MORE", "RETRYABLE"}:
        state.setdefault("stage_status", {})[action] = result_status
        state["last_continuation_result"] = {"action": action, **value}
        state["status"] = "IN_PROGRESS"
        state["continuation_required"] = True
        state["next_action"] = action
        # Source quality and a failed acquisition attempt are findings, not
        # terminal authority. The parent keeps the objective active; bounded
        # adapters may select another method or carry the limitation to
        # synthesis. Only explicit owner/cash/technical terminal decisions
        # elsewhere in the workflow may stop the root objective.
        state.setdefault("workflow_history", []).append({"action": action,
            "status": result_status, "result_ref": value.get("result_ref")})
        return state
    if action == "SOURCE_UNDERSTANDING":
        state["source_understanding"] = value
        state["subject_domain"] = str(value.get("category") or value.get("subject_domain") or state.get("subject_domain") or "UNKNOWN").upper()
        state["evidence"] = list(state.get("evidence") or []) + list(value.get("evidence") or [])
    elif action == "KNOWLEDGE_RECONCILIATION":
        relationship = str(value.get("relationship") or "NEW").upper()
        if relationship not in {"NEW", "RELATED", "DUPLICATE", "UPDATED", "CONTRADICTS"}:
            raise ValueError("INVALID_KNOWLEDGE_RELATIONSHIP")
        state["knowledge_reconciliation"] = {**value, "relationship": relationship}
    elif action == "ADVISOR_REVIEW":
        state["advisor_findings"] = value
        if value.get("questions") and not state.get("questions"):
            state["questions"] = _normalize_questions(value.get("questions"))
    elif action == "QUESTION_GENERATION":
        existing = {str(q.get("question", "")).casefold() for q in _questions(state)}
        state["questions"] = _questions(state) + [q for q in _normalize_questions(value.get("questions"))
            if str(q.get("question", "")).casefold() not in existing]
    elif action == "FOLLOWUP_RESEARCH":
        state["followup_attempts"] = int(state.get("followup_attempts", 0)) + 1
        state["needle_repair_attempts"] = int(state.get("needle_repair_attempts", 0)) + int(bool(state.get("needle")))
        state["evidence"] = list(state.get("evidence") or []) + list(value.get("evidence") or [])
        by_question = {str(q.get("question", "")).casefold(): q for q in _questions(state)}
        for answer in value.get("answers") or []:
            if not isinstance(answer, Mapping):
                continue
            target = by_question.get(str(answer.get("question") or "").casefold())
            if target:
                target.update({"status": str(answer.get("status") or "UNVERIFIED").upper(),
                    "answer": answer.get("answer"), "evidence_refs": list(answer.get("evidence_refs") or []),
                    "confidence": answer.get("confidence"),
                    "needs_followup": bool(answer.get("needs_followup", False)),
                    "related_action": answer.get("related_action")})
        state["questions"] = list(by_question.values())
        if value.get("test_result") is not None:
            test_results = list(state.get("test_results") or [])
            if value["test_result"] not in test_results:
                test_results.append(value["test_result"])
            state["test_results"] = test_results
    elif action == "NEEDLE_REVIEW":
        needle_status = str(value.get("status") or "").upper()
        if needle_status not in {"READY", "READY_FOR_DEPARTMENT", "RESEARCH_MORE"}:
            raise ValueError("INVALID_NEEDLE_STATUS")
        state["needle"] = value
        for question in value.get("missing_questions") or []:
            state["questions"] = _normalize_questions(_questions(state) + [{"question": question,
                "status": "OPEN", "needs_followup": True}])
    elif action == "SYNTHESIS":
        if not value.get("recommended_actions") or not (value.get("action_owner") or value.get("next_department")):
            raise ValueError("RESEARCH_SYNTHESIS_ACTION_AND_OWNER_REQUIRED")
        state["synthesis"] = value
        state["action_owner"] = value.get("action_owner") or state.get("action_owner")
        state["next_department"] = value.get("next_department") or state.get("next_department")
    elif action == "CATEGORY_LIBRARY_ROUTING":
        state["category_library_routing"] = value
    elif action == "HANDOFF":
        if not value.get("handoff_id") or not (value.get("next_department") or value.get("action_owner")):
            raise ValueError("ACTIONABLE_RESEARCH_HANDOFF_REQUIRED")
        state["handoff"] = value
        state["action_owner"] = value.get("action_owner") or state.get("action_owner")
        state["next_department"] = value.get("next_department") or state.get("next_department")
        if value.get("terminal_condition"):
            condition = str(value["terminal_condition"]).upper()
            if condition not in TERMINAL_CONDITIONS:
                raise ValueError("INVALID_RESEARCH_TERMINAL_CONDITION")
            state["terminal_condition"] = condition
    else:
        raise ValueError("UNKNOWN_RESEARCH_PARENT_ACTION")
    state.setdefault("stage_status", {})[action] = str(value.get("status") or "COMPLETED").upper()
    state.setdefault("workflow_history", []).append({"action": action,
        "status": state["stage_status"][action], "result_ref": value.get("result_ref")})
    return state


def run_parent_workflow(state: dict[str, Any], *, execute: Callable[[str, Mapping[str, Any]], Mapping[str, Any]],
                        persist: Callable[[Mapping[str, Any]], Any] | None = None,
                        max_steps: int = 32) -> dict[str, Any]:
    """Advance via bounded adapters until handoff, terminal state, or explicit wait."""
    for _ in range(max_steps):
        action = select_next_action(state)
        if action is None:
            if state.get("terminal_condition") in TERMINAL_CONDITIONS:
                state["status"] = state["terminal_condition"]
            elif state.get("handoff", {}).get("handoff_id"):
                state["status"] = "COMPLETE"
            return dict(state)
        state["continuation_sequence"] = int(state.get("continuation_sequence", 0)) + 1
        state["continuation_required"] = False
        try:
            result = execute(action, state)
        except Exception as exc:
            result = {"status": "CONTINUATION_REQUIRED", "error_type": type(exc).__name__,
                "error": str(exc)[:300]}
        apply_action_result(state, action, result or {})
        if persist:
            persist(state)
        if state.get("continuation_required"):
            return dict(state)
        # A legitimate terminal decision is recorded and surfaced, never
        # converted into ordinary completion or lost child state.
        if state.get("terminal_condition"):
            state["status"] = state["terminal_condition"]
            if persist:
                persist(state)
            return dict(state)
    if state.get("terminal_condition") in TERMINAL_CONDITIONS:
        state["status"] = state["terminal_condition"]
        state["continuation_required"] = False
    else:
        state["status"] = "IN_PROGRESS"
        state["continuation_required"] = True
    state["next_action"] = select_next_action(state)
    if persist:
        persist(state)
    return dict(state)


def continuation_job_key(objective_id: str, action: str, sequence: int) -> str:
    """Stable key for idempotent bounded continuation job creation."""
    if not objective_id or action not in WORKFLOW or int(sequence) < 1:
        raise ValueError("INVALID_RESEARCH_CONTINUATION_KEY")
    token = hashlib.sha256(f"{objective_id}|{action}|{sequence}".encode()).hexdigest()[:24]
    return f"research-parent-continuation:{token}"


def create_continuation_job(store: Any, *, state: Mapping[str, Any], parent_job_id: str,
                            payload_ref: str, priority: int = 70) -> Any:
    """Create one idempotent bounded child using the existing durable job store."""
    action = select_next_action(state)
    if not action:
        return None
    sequence = int(state.get("continuation_sequence", 0)) + 1
    return store.enqueue("RESEARCH", "RESEARCH_INTAKE", priority=priority,
        payload_ref=payload_ref, parent_job_id=parent_job_id,
        correlation_id=str(state.get("root_objective_id") or state.get("objective_id")),
        idempotency_key=continuation_job_key(str(state.get("objective_id") or ""), action, sequence),
        governance_context={"source": "RESEARCH_PARENT_CONTINUATION", "objective_id": state.get("root_objective_id") or state.get("objective_id"),
            "root_objective_id": state.get("root_objective_id") or state.get("objective_id"),
            "research_parent_objective_id": state.get("root_objective_id") or state.get("objective_id"),
            "research_parent_id": state.get("research_parent_id") or state.get("objective_id"),
            "research_case_id": state.get("research_case_id"),
            "original_objective": state.get("original_objective"),
            "original_source_url": state.get("source_url"),
            "original_source_type": state.get("source_type"),
            "research_parent_action": action, "research_parent_state": dict(state),
            "root_objective_status": "IN_PROGRESS"})


def recover_orphaned_objective(store: Any, *, state: Mapping[str, Any], parent_job_id: str,
                               payload_ref: str, child_states: list[str]) -> Any:
    """Idempotently repair an active objective with no active child or stop condition."""
    if state.get("status") == "COMPLETE" or state.get("terminal_condition") in TERMINAL_CONDITIONS:
        return None
    if any(str(value).upper() in CHILD_ACTIVE for value in child_states):
        return None
    child = create_continuation_job(store, state=state, parent_job_id=parent_job_id,
                                    payload_ref=payload_ref)
    if child is None or str(getattr(child, "state", "READY")).upper() in CHILD_ACTIVE:
        return child
    # An idempotency key for this sequence may already belong to a blocked or
    # failed child. Reusing it only returns the terminal row and leaves the
    # root orphaned. Advance one bounded sequence and create the next durable
    # attempt; subsequent watchdog passes see that active child and do nothing.
    advanced = dict(state)
    advanced["continuation_sequence"] = int(advanced.get("continuation_sequence", 0)) + 1
    recovered = create_continuation_job(store, state=advanced, parent_job_id=parent_job_id,
                                        payload_ref=payload_ref)
    if recovered is not None and str(getattr(recovered, "state", "READY")).upper() in CHILD_ACTIVE:
        return recovered
    return child


def consume_child_result(store: Any, *, job: Any, result: Mapping[str, Any],
                         work_item: Mapping[str, Any],
                         execute: Callable[[str, Mapping[str, Any]], Mapping[str, Any]] | None = None
                         ) -> dict[str, Any]:
    """Persist one bounded child result and schedule the parent's next action.

    This is the durable worker boundary: a completed child never marks the
    Research objective complete. Only a persisted handoff (or one of the
    existing terminal conditions) can do that.
    """
    from dataclasses import asdict, is_dataclass

    context = dict(getattr(job, "governance_context", {}) or {})
    child_result = dict(result or {})
    if context.get("source") == "RESEARCH_PARENT_CONTINUATION":
        state = dict(context.get("research_parent_state") or {})
        # Older parent contexts used the internal Nova work ID as objective_id.
        # Recover the Ray/Nova root correlation from the durable child row.
        root_id = str(context.get("root_objective_id") or "")
        ancestor_id = str(getattr(job, "parent_job_id", None) or "")
        # Follow durable parent links to the original Nova assignment. Older
        # continuation rows have only the internal work ID as correlation.
        for _ in range(64):
            if root_id or not ancestor_id:
                break
            ancestor = store.get(ancestor_id)
            if not ancestor:
                break
            ancestor_context = dict(getattr(ancestor, "governance_context", {}) or {})
            if ancestor_context.get("source") == "NOVA_MCP_RESEARCH_ASSIGNMENT":
                root_id = str(ancestor_context.get("root_objective_id") or ancestor.correlation_id or "")
                break
            ancestor_id = str(getattr(ancestor, "parent_job_id", None) or "")
        root_id = root_id or str(job.correlation_id or state.get("root_objective_id") or state.get("objective_id") or "")
        if root_id:
            state["root_objective_id"] = root_id
            state["objective_id"] = root_id
        action = str(context.get("research_parent_action") or "").upper()
        if not state or action not in WORKFLOW:
            raise ValueError("RESEARCH_PARENT_CONTINUATION_CONTEXT_REQUIRED")
        # Record only compact child output in the persistent state. Large
        # documents stay in their existing artifact store and are referenced.
        if execute is None:
            from nexus_agent_platform.research_parent_adapters import execute_action
            execute = lambda name, current: execute_action(name, current, work_item)
        stage_result = dict(execute(action, state) or {})
        apply_action_result(state, action, stage_result)
        state["continuation_sequence"] = int(state.get("continuation_sequence", 0)) + 1
        child_result = {"action": action, **_compact_result(stage_result)}
    else:
        # The Nova root objective is the durable correlation ID. Keep the
        # generated work ID separately as the internal Research parent ID.
        internal_parent_id = str(context.get("objective_id") or work_item.get("objective_id") or job.correlation_id)
        objective_id = str(context.get("root_objective_id") or work_item.get("parent_request_id")
                            or job.correlation_id or internal_parent_id)
        objective = str(context.get("original_objective") or work_item.get("original_objective")
                        or work_item.get("objective") or work_item.get("title") or "").strip()
        state = new_parent(objective_id=objective_id, original_objective=objective,
            source_url=context.get("original_source_url") or work_item.get("original_source_url") or work_item.get("source_url"),
            source_type=context.get("original_source_type") or work_item.get("original_source_type") or work_item.get("source_type"),
            research_scope=context.get("research_scope") or work_item.get("research_scope"),
            current_context=context.get("current_research_context") or work_item.get("current_research_context") or {},
            subject_domain=work_item.get("objective_type") or work_item.get("subject_domain"))
        state["research_parent_id"] = internal_parent_id
        state["root_objective_id"] = objective_id
        state["research_work_id"] = str(work_item.get("work_id") or job.payload_ref or "")
        state["research_case_id"] = child_result.get("case_id") or child_result.get("result", {}).get("case_id")
        state["stage_status"]["RESEARCH_INTAKE"] = "COMPLETED"
        state["last_child_result"] = _compact_result(child_result)

    if state.get("terminal_condition") in TERMINAL_CONDITIONS:
        state["status"] = state["terminal_condition"]
        state["continuation_required"] = False
    else:
        state["status"] = "IN_PROGRESS"
        state["continuation_required"] = True
    next_action = select_next_action(state)
    state["next_action"] = next_action
    if next_action is None:
        if state.get("handoff", {}).get("handoff_id") and (state.get("next_department") or state.get("action_owner")):
            state["status"] = "COMPLETE"
            state["continuation_required"] = False
            state["next_action"] = None
        elif state.get("terminal_condition") in TERMINAL_CONDITIONS:
            state["status"] = state["terminal_condition"]
            state["continuation_required"] = False
        elif state.get("terminal_condition") not in TERMINAL_CONDITIONS:
            raise ValueError("RESEARCH_PARENT_CANNOT_STOP_WITHOUT_HANDOFF")

    # Save parent state on the completed child for watchdog recovery and audit.
    context.update({"objective_id": state.get("objective_id"),
        "root_objective_id": state.get("root_objective_id") or state.get("objective_id"),
        "research_parent_state": state,
        "research_parent_objective_id": state["objective_id"],
        "research_parent_id": state.get("research_parent_id") or state["objective_id"],
        "research_case_id": state.get("research_case_id"),
        "last_research_child_result": _compact_result(child_result),
        "root_objective_status": state["status"]})
    store.set_governance_context(job.job_id, context)

    next_job = None
    if state.get("continuation_required") and next_action:
        next_job = create_continuation_job(store, state=state, parent_job_id=job.job_id,
            payload_ref=str(job.payload_ref or work_item.get("work_id") or ""))
        if next_job is None:
            raise RuntimeError("RESEARCH_CONTINUATION_JOB_NOT_CREATED")
        context["research_next_job_id"] = getattr(next_job, "job_id", None)
        store.set_governance_context(job.job_id, context)
        # Keep the existing Research work item as the projection of this active
        # root. A completed child with a queued projection and active child is
        # inconsistent and caused status/orphan checks to miss live work.
        if work_item.get("work_id"):
            from nexus_agent_platform.research_work_queue import default_queue
            updated = default_queue().settle(str(work_item["work_id"]), "IN_PROGRESS", result={
                "root_objective_id": state.get("root_objective_id"),
                "research_parent_id": state.get("research_parent_id"),
                "current_stage": next_action, "continuation_job_id": getattr(next_job, "job_id", None)})
            if updated is None:
                raise RuntimeError("RESEARCH_PARENT_WORK_ITEM_STATE_PERSIST_FAILED")
    if state["status"] == "COMPLETE":
        from nexus_agent_platform.research_work_queue import default_queue
        if work_item.get("work_id"):
            default_queue().settle(str(work_item["work_id"]), "COMPLETE", result={
                "final_status": "RESEARCH_HANDOFF_COMPLETE",
                "research_parent_id": state.get("research_parent_id"),
                "handoff": state.get("handoff")})
    elif state.get("terminal_condition") in TERMINAL_CONDITIONS:
        from nexus_agent_platform.research_work_queue import default_queue
        if work_item.get("work_id"):
            updated = default_queue().settle(str(work_item["work_id"]), "BLOCKED_EXTERNAL", result={
                "root_objective_id": state.get("root_objective_id"),
                "terminal_condition": state.get("terminal_condition"),
                "blocker": state.get("terminal_blocker")})
            if updated is None:
                raise RuntimeError("RESEARCH_PARENT_TERMINAL_STATE_PERSIST_FAILED")
    if state.get("continuation_required") and not next_job:
        raise RuntimeError("RESEARCH_PARENT_CONTINUATION_STATE_INCONSISTENT")
    return {"status": "CONTINUATION_SCHEDULED" if next_job else state["status"],
            "research_parent_id": state.get("research_parent_id"),
            "root_objective_status": state.get("status"), "next_action": next_action,
            "next_job_id": getattr(next_job, "job_id", None), "parent_state": state,
            "child_result": _compact_result(child_result)}


def _compact_result(value: Any, *, max_chars: int = 6000) -> dict[str, Any]:
    """Keep result references and concise findings; never copy source bodies."""
    import json
    from dataclasses import asdict, is_dataclass
    if is_dataclass(value):
        value = asdict(value)
    if not isinstance(value, Mapping):
        value = {"value": str(value)}
    omitted = {"raw_text", "normalized_text_or_markdown", "transcript", "transcript_text",
               "html", "source_body", "raw_source", "raw_response"}
    compact = {str(key): item for key, item in value.items() if str(key) not in omitted}
    encoded = json.dumps(compact, ensure_ascii=False, default=str)
    if len(encoded) <= max_chars:
        return compact
    return {key: compact[key] for key in ("status", "result_ref", "artifact_ref", "receipt_id",
            "case_id", "subject", "summary", "reason", "error", "handoff_id",
            "next_department", "action_owner") if key in compact} | {"result_truncated": True}


def recover_orphaned_parents(store: Any, *, limit: int = 500) -> dict[str, int]:
    """Dispatcher watchdog for incomplete parents with no active child."""
    if not hasattr(store, "list_research_parent_jobs"):
        return {"scanned": 0, "recovered": 0}
    jobs = store.list_research_parent_jobs(limit=limit)
    groups: dict[str, list[Any]] = {}
    for job in jobs:
        context = job.governance_context or {}
        state = context.get("research_parent_state")
        if not isinstance(state, dict):
            continue
        objective_id = str(state.get("objective_id") or context.get("research_parent_objective_id") or "")
        if objective_id:
            groups.setdefault(objective_id, []).append(job)
    recovered = 0
    for objective_id, rows in groups.items():
        rows.sort(key=lambda job: (int((job.governance_context or {}).get("research_parent_state", {}).get("continuation_sequence", 0)),
                                   str(job.created_at or "")))
        latest = rows[-1]
        context = latest.governance_context or {}
        state = dict(context.get("research_parent_state") or {})
        if state.get("status") == "COMPLETE" or state.get("terminal_condition") in TERMINAL_CONDITIONS:
            continue
        active_states = [str(job.state).upper() for job in rows
                         if str(job.state).upper() in CHILD_ACTIVE]
        if active_states:
            continue
        latest_action = str(context.get("research_parent_action") or "").upper()
        failed_same_action = [job for job in rows
            if str(job.state).upper() in {"BLOCKED", "FAILED_RETRYABLE", "FAILED_FINAL"}
            and str((job.governance_context or {}).get("research_parent_action") or "").upper() == latest_action]
        if latest_action in WORKFLOW and len(failed_same_action) >= 2:
            # Two failed executions end attempts for this method, not the
            # owner's Research objective. Preserve the failure as uncertainty
            # and advance the parent to the next useful stage.
            failure = {"status": "METHOD_FAILED", "action": latest_action,
                "failed_jobs": [{"job_id": job.job_id, "error_code": job.last_error_code,
                    "error_summary": job.last_error_summary} for job in failed_same_action[-2:]]}
            state.setdefault("stage_status", {})[latest_action] = "FAILED_WITH_FINDING"
            if latest_action == "SOURCE_UNDERSTANDING":
                state["source_understanding"] = {"status": "SOURCE_INCOMPLETE",
                    "subject": state.get("source_url") or state.get("original_objective"),
                    "summary": "Available source acquisition methods failed; continue with the objective and preserve this limitation.",
                    "source_url": state.get("source_url"), "method_failures": failure["failed_jobs"]}
                state.setdefault("evidence", []).append({"ref": state.get("source_url"),
                    "status": "UNVERIFIED", "limitation": "SOURCE_ACQUISITION_METHODS_FAILED"})
            elif latest_action == "KNOWLEDGE_RECONCILIATION":
                state["knowledge_reconciliation"] = {"relationship": "NEW", "lookup": "UNAVAILABLE",
                    "prior_summary": None, "material_changes": [], "method_failures": failure["failed_jobs"]}
            elif latest_action == "ADVISOR_REVIEW":
                state["advisor_findings"] = {"status": "ADVISOR_UNAVAILABLE",
                    "subject_interpretation": _source_text(state) or state.get("original_objective"),
                    "questions": [], "uncertainty": failure["failed_jobs"]}
            elif latest_action == "QUESTION_GENERATION":
                state["stage_status"][latest_action] = "FAILED_WITH_FINDING"
            elif latest_action == "FOLLOWUP_RESEARCH":
                state["followup_attempts"] = 2
                for question in state.get("questions") or []:
                    if str(question.get("status") or "OPEN").upper() in {"OPEN", "PARTIAL"}:
                        question.update(status="UNVERIFIED", needs_followup=False,
                            answer="Follow-up methods were unavailable; retained as unresolved uncertainty.")
            elif latest_action == "NEEDLE_REVIEW":
                state["needle"] = {"status": "RESEARCH_MORE", "missing_questions": [],
                    "reason": "NEEDLE_UNAVAILABLE_AFTER_BOUNDED_ATTEMPTS", "method_failures": failure["failed_jobs"]}
                state["needle_repair_attempts"] = 1
            elif latest_action == "SYNTHESIS":
                destination = _destination(state)
                state["synthesis"] = {"status": "PARTIAL_SYNTHESIS",
                    "original_objective": state.get("original_objective"),
                    "source_references": _evidence_refs(state),
                    "key_findings": state.get("evidence") or [],
                    "unresolved_uncertainty": [row.get("question") for row in state.get("questions") or []],
                    "research_conclusion": "A partial Research package is being handed off with method failures and unresolved uncertainty.",
                    "recommended_actions": ["Receiving owner reviews the available evidence and selects the next bounded action."],
                    "action_owner": "NOVA", "next_department": destination}
                state["action_owner"] = "NOVA"
                state["next_department"] = destination
            elif latest_action == "CATEGORY_LIBRARY_ROUTING":
                state["category_library_routing"] = {"status": "UNAVAILABLE", "category": state.get("subject_domain", "UNKNOWN")}
            state["status"] = "IN_PROGRESS"
            state["continuation_required"] = True
            state["last_continuation_result"] = failure
            context["research_parent_state"] = state
            context["root_objective_status"] = state["status"]
            store.set_governance_context(latest.job_id, context)
        payload_ref = str(latest.payload_ref or "")
        if not payload_ref:
            continue
        child = recover_orphaned_objective(store, state=state, parent_job_id=latest.job_id,
            payload_ref=payload_ref, child_states=[])
        if child is not None and str(getattr(child, "state", "READY")).upper() in CHILD_ACTIVE:
            recovered += 1
    return {"scanned": len(groups), "recovered": recovered}
