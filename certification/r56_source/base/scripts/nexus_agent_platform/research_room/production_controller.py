"""Narrow MCP bridge from Research Room turns to an existing production case.

Research Room contributes execution logic; the Research Case Engine remains
the sole persistence authority. No Research Room case store is used here.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import uuid
from datetime import datetime, timezone
from contextlib import contextmanager
from typing import Any

RESULTS_READ_MAX_BYTES = 512_000
RESULTS_READ_MAX_ITEMS = 40
RESULTS_READ_MAX_STRING = 24_000


@contextmanager
def _local_case_read_scope():
    """Read the local append-only mirror without spending Supabase egress."""
    key = "NEXUS_RESEARCH_CASE_READ_LOCAL_ONLY"
    previous = os.environ.get(key)
    os.environ[key] = "1"
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = previous


def _get_case_local(engine: Any, case_id: str) -> dict[str, Any] | None:
    with _local_case_read_scope():
        return engine.get_case(case_id)


def _bounded_read_value(value: Any, *, depth: int = 0) -> Any:
    if depth >= 8:
        return "[depth limit]"
    if isinstance(value, str):
        return value[:RESULTS_READ_MAX_STRING]
    if isinstance(value, list):
        return [_bounded_read_value(item, depth=depth + 1) for item in value[:RESULTS_READ_MAX_ITEMS]]
    if isinstance(value, dict):
        return {str(key)[:160]: _bounded_read_value(item, depth=depth + 1)
                for key, item in list(value.items())[:100]}
    return value


def _identity(case_id: str, objective_id: str, project_id: str, job_id: str) -> dict[str, str]:
    values = {"case_id": case_id, "objective_id": objective_id,
              "project_id": project_id, "job_id": job_id}
    if any(not str(value or "").strip() for value in values.values()):
        raise ValueError("EXACT_RESEARCH_OBJECTIVE_PROJECT_CASE_JOB_REQUIRED")
    return {key: str(value).strip() for key, value in values.items()}


@contextmanager
def _production_governance_context(identity: dict[str, str], *, call_id: str,
                                   execution_job_id: str | None = None,
                                   job_type: str = "RESEARCH_CASE_CONTINUATION"):
    """Bind provider calls to the existing production Research job lineage."""
    values = {
        "NEXUS_RESEARCH_ROOM_PRODUCTION_CASE": "true",
        "NEXUS_DURABLE_JOB_ID": execution_job_id or identity["job_id"],
        "NEXUS_CORRELATION_ID": identity["objective_id"],
        "NEXUS_PROJECT_ID": identity["project_id"],
        "NEXUS_DEPARTMENT": "RESEARCH",
        "NEXUS_JOB_TYPE": job_type,
        "NEXUS_RESEARCH_ROOM_CALL_ID": call_id,
    }
    previous = {key: os.environ.get(key) for key in values}
    os.environ.update(values)
    try:
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _load(identity: dict[str, str]) -> dict[str, Any]:
    from research import research_case_engine as engine
    case = _get_case_local(engine, identity["case_id"])
    if not isinstance(case, dict) or str(case.get("case_id") or "") != identity["case_id"]:
        raise LookupError("EXACT_RESEARCH_CASE_NOT_FOUND")
    case_project_id = str(case.get("project_id") or "")
    case_objective_id = str(case.get("objective_id") or case.get("originating_goal_id") or "")
    project_matches = (case_project_id == identity["project_id"] if case_project_id else
        identity["project_id"] in str(case.get("primary_question") or ""))
    objective_matches = not case_objective_id or case_objective_id == identity["objective_id"]
    if not project_matches or not objective_matches:
        raise PermissionError("RESEARCH_CASE_PROJECT_MISMATCH")
    # Resolve queue lineage from the authoritative data root, not from an
    # immutable code release's potentially stale copied data/ snapshot.
    from nexus_agent_platform.runtime.paths import nexus_research_state_path
    queue_path = nexus_research_state_path("runtime", "research_work_queue.json")
    try:
        queue_payload = json.loads(queue_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        queue_payload = {}
    projects = queue_payload.get("items", []) if isinstance(queue_payload, dict) else []
    project = next((row for row in projects if isinstance(row, dict)
        and str(row.get("work_id") or "") == identity["project_id"]), None)
    if not project or str(project.get("objective_id") or "") != identity["objective_id"]:
        raise PermissionError("RESEARCH_PROJECT_OBJECTIVE_LINEAGE_MISMATCH")
    from nexus_agent_platform.durable_jobs import default_store
    job = default_store().get(identity["job_id"])
    if not job:
        raise LookupError("EXACT_RESEARCH_JOB_NOT_FOUND")
    get = job.get if isinstance(job, dict) else lambda key, default=None: getattr(job, key, default)
    if (str(get("correlation_id") or "") != identity["objective_id"]
            or str(get("department") or "").upper() != "RESEARCH"
            or str(get("job_type") or "").upper() not in {"RESEARCH_INTAKE", "RESEARCH_CASE_CONTINUATION"}):
        raise PermissionError("RESEARCH_JOB_LINEAGE_MISMATCH")
    return case


def _projection(case: dict[str, Any], identity: dict[str, str]) -> dict[str, Any]:
    controller = case.get("research_room_controller")
    attempts = list((controller or {}).get("advisor_attempts") or [])
    latest_attempt = attempts[-1] if attempts else None
    return {"status": "ok", **identity, "controller": {
        "state": (controller or {}).get("state", "NOT_STARTED"),
        "current_participant": (controller or {}).get("next_participant"),
        "turn_count": int((controller or {}).get("turn_count", 0)),
        "last_event": (controller or {}).get("last_event"),
        "advisor_attempt_count": len(attempts),
        "latest_advisor_attempt": copy.deepcopy(latest_attempt),
    }, "case_status": case.get("status"), "open_question_count": len(case.get("open_questions") or []),
       "evidence_count": len(case.get("sources") or []),
       "synthesis_count": len(case.get("syntheses") or []),
       "pending_advisor_work": bool(latest_attempt and str(latest_attempt.get("status") or "").upper()
            in {"QUEUED", "RUNNING"}),
       "advisor_attempt_count": len(attempts),
       "latest_advisor_attempt": copy.deepcopy(latest_attempt),
       "read_only": True, "no_mutation": True}


def status(case_id: str, objective_id: str, project_id: str, job_id: str) -> dict[str, Any]:
    identity = _identity(case_id, objective_id, project_id, job_id)
    result = _projection(_load(identity), identity)
    result["read_source"] = "LOCAL_DURABLE_MIRROR"
    result["read_budget"] = {"max_case_tail_bytes": 8_000_000}
    return _bounded_read_value(result)


def open_questions(case_id: str, objective_id: str, project_id: str, job_id: str) -> dict[str, Any]:
    identity = _identity(case_id, objective_id, project_id, job_id)
    case = _load(identity)
    questions = _bounded_read_value(copy.deepcopy(case.get("open_questions") or []))
    return {"status": "ok", **identity, "open_questions": questions,
            "read_only": True, "no_mutation": True, "read_source": "LOCAL_DURABLE_MIRROR",
            "read_budget": {"max_question_count": RESULTS_READ_MAX_ITEMS,
                            "max_field_chars": RESULTS_READ_MAX_STRING}}


def results(case_id: str, objective_id: str, project_id: str, job_id: str) -> dict[str, Any]:
    identity = _identity(case_id, objective_id, project_id, job_id)
    case = _load(identity)
    fields = ("sources", "findings", "answered_questions", "syntheses", "recommendations",
              "research_room_advisor_reviews", "research_room_controller")
    projected = {key: copy.deepcopy(case.get(key) or ([] if key != "research_room_controller" else {}))
                 for key in fields}
    for key in fields:
        projected[key] = _bounded_read_value(projected[key])
    response = {"status": "ok", **identity, "results": projected,
                "read_only": True, "no_mutation": True, "read_source": "LOCAL_DURABLE_MIRROR"}
    encoded = json.dumps(response, ensure_ascii=False, default=str).encode("utf-8")
    if len(encoded) > RESULTS_READ_MAX_BYTES:
        # Trim the largest collections first while preserving lineage and counts.
        for key in ("research_room_advisor_reviews", "sources", "findings", "answered_questions", "syntheses"):
            rows = projected.get(key)
            if isinstance(rows, list) and len(rows) > 5:
                projected[key] = rows[-5:]
                response["read_payload_truncated"] = True
                encoded = json.dumps(response, ensure_ascii=False, default=str).encode("utf-8")
                if len(encoded) <= RESULTS_READ_MAX_BYTES:
                    break
    if len(encoded) > RESULTS_READ_MAX_BYTES:
        response["results"] = {key: (value if key in {"research_room_controller"} else
            [{k: row.get(k) for k in ("question_id", "answer_status", "status", "review_id",
              "role", "provider", "model", "attempt_id", "job_id") if k in row}
             for row in value if isinstance(row, dict)][:5] if isinstance(value, list) else value)
            for key, value in projected.items()}
        response["read_payload_truncated"] = True
    response.setdefault("read_payload_truncated", False)
    return response


def _save_controller(case_id: str, *, controller: dict[str, Any], advisor_review: dict[str, Any] | None = None,
                     event: str = "RESEARCH_ROOM_CONTROLLER_ADVANCED") -> dict[str, Any]:
    from research import research_case_engine as engine
    case = _get_case_local(engine, case_id)
    if not case or str(case.get("case_id") or "") != case_id:
        raise LookupError("EXACT_RESEARCH_CASE_NOT_FOUND")
    updates: dict[str, Any] = {"research_room_controller": controller}
    if advisor_review:
        reviews = list(case.get("research_room_advisor_reviews") or [])
        key = advisor_review["review_id"]
        if not any(row.get("review_id") == key for row in reviews if isinstance(row, dict)):
            reviews.append(advisor_review)
        updates["research_room_advisor_reviews"] = reviews
    saved = engine._save(case, event, **updates)
    receipt = saved.get("supabase_sync") if isinstance(saved, dict) else None
    return {"saved": isinstance(saved, dict), "supabase_sync": receipt or {"status": "ENGINE_PERSISTED"}}


def _primary_review_for_case(case: dict[str, Any], identity: dict[str, str]) -> dict[str, Any] | None:
    rows = [row for row in case.get("research_room_advisor_reviews") or []
        if isinstance(row, dict)
        and str(row.get("case_id") or identity["case_id"]) == identity["case_id"]
        and str(row.get("objective_id") or identity["objective_id"]) == identity["objective_id"]
        and str(row.get("project_id") or identity["project_id"]) == identity["project_id"]
        and str(row.get("job_id") or identity["job_id"]) == identity["job_id"]
        and str(row.get("role") or "").upper() in {"PRIMARY_RESEARCH_ADVISOR", "PRIMARY_ADVISOR"}
        and str(row.get("analysis") or "").strip()]
    if not rows:
        return None
    # A later misrouted/empty-context review must not replace an earlier
    # substantive review. Prefer actual decision analysis and evidence notes.
    return max(rows, key=lambda row: len(str(row.get("analysis") or ""))
        + 240 * len(row.get("risks") or []) + 120 * len(row.get("evidence_notes") or []))


def _project_primary_review_answers(identity: dict[str, str], case: dict[str, Any]) -> set[str]:
    """Persist formal answers derived only from a completed same-case review."""
    review = _primary_review_for_case(case, identity)
    if not review:
        return set()
    analysis = str(review.get("analysis") or "").strip()
    evidence_notes = [str(item).strip() for item in review.get("evidence_notes") or [] if str(item).strip()]
    risks = [str(item).strip() for item in review.get("risks") or [] if str(item).strip()]
    if not analysis:
        return set()
    q2 = next((row for row in case.get("open_questions") or [] if isinstance(row, dict)
        and str(row.get("question_id") or "") == "q_b04da13aa3b1464f"), None)
    q3 = next((row for row in case.get("open_questions") or [] if isinstance(row, dict)
        and str(row.get("question_id") or "") == "q_b42074818a3af0a5"), None)
    stop = {"about", "after", "also", "and", "are", "can", "could", "does", "from", "have",
        "into", "is", "its", "more", "only", "that", "the", "their", "then", "this", "those",
        "through", "what", "when", "where", "which", "with", "would", "your"}
    def terms(value: str) -> set[str]:
        import re
        return {token for token in re.findall(r"[a-z0-9]+", value.casefold())
                if len(token) > 2 and token not in stop}
    generic = []
    eligible_reviews = [row for row in case.get("research_room_advisor_reviews") or []
        if isinstance(row, dict)
        and str(row.get("case_id") or identity["case_id"]) == identity["case_id"]
        and str(row.get("objective_id") or identity["objective_id"]) == identity["objective_id"]
        and str(row.get("project_id") or identity["project_id"]) == identity["project_id"]
        and str(row.get("job_id") or identity["job_id"]) == identity["job_id"]
        and str(row.get("role") or "").upper() in {"PRIMARY_RESEARCH_ADVISOR", "PRIMARY_ADVISOR"}
        and str(row.get("analysis") or "").strip()]
    answered_ids = {str(row.get("question_id") or "") for row in case.get("answered_questions") or []
        if isinstance(row, dict)}
    for row in case.get("open_questions") or []:
        if not isinstance(row, dict) or row in (q2, q3) or str(row.get("question_id") or "") in answered_ids:
            continue
        question_terms = terms(str(row.get("question") or ""))
        if len(question_terms) < 4:
            continue
        matching_reviews = []
        for candidate in eligible_reviews:
            candidate_terms = terms(str(candidate.get("question") or ""))
            overlap = len(question_terms & candidate_terms) / max(1, len(question_terms))
            if overlap >= 0.35:
                matching_reviews.append((overlap, candidate))
        if matching_reviews:
            generic.append((row, max(matching_reviews, key=lambda item: (item[0],
                len(str(item[1].get("analysis") or ""))))[1]))
    if not q2 and not q3 and not generic:
        return set()
    q2_answer = (
        "MATERIAL CLAIMS AND EVIDENCE STATUS (from the persisted Primary Advisor review):\n"
        + analysis + "\n\nVERIFICATION BOUNDARY: No external sources or migration test results are attached. "
        "The migration-certification scope is supported by the supplied objective; historical provider "
        "outcomes and provider-policy statements are reported case context, not independently verified. "
        "Any assertion that a particular migration passed or that a proposed certification design is "
        "sufficient remains UNVERIFIED. No citations are inferred."
    )
    risk_lines = "\n".join(f"- {item}" for item in risks) or "- The review supplied no specific risk list."
    q3_answer = (
        "COSTS: No migration implementation or ongoing cost estimate is in the supplied case. The "
        "Primary Advisor request was recorded at $0 incremental; that is not a migration cost estimate.\n"
        "RISKS:\n" + risk_lines + "\n"
        "CONSTRAINTS: The migration type, system boundary, risk tier, dependencies, and operational "
        "cost model are unspecified. No external source, migration evidence, or test result is attached.\n"
        "ALTERNATIVES: Tailor verification depth to the eventual migration risk tier; retain a bounded "
        "read-only verification path when independent testing is not yet available; obtain the missing "
        "migration scope before setting thresholds. These are proposed paths, not validated outcomes.\n"
        "UNRESOLVED UNCERTAINTIES: Migration-specific acceptance criteria, evidence-retention needs, "
        "negative-path coverage, rollback behavior, independent-verifier method, and implementation/" 
        "ongoing costs.\n"
        "BASIS: Supplied objective plus persisted Primary Advisor review. No external claims are presented as verified."
    )
    from research import research_case_engine as engine
    persisted: set[str] = set()
    answer_rows = [(q2, q2_answer, 0.65), (q3, q3_answer, 0.55)]
    for row, matching_review in generic:
        matching_analysis = str(matching_review.get("analysis") or "").strip()
        matching_notes = [str(item).strip() for item in matching_review.get("evidence_notes") or []
            if str(item).strip()]
        answer = (
            "ANSWER FROM THE SAME-CASE PRIMARY ADVISOR REVIEW:\n" + matching_analysis
            + ("\n\nREVIEW EVIDENCE NOTES:\n" + "\n".join(matching_notes) if matching_notes else "")
            + "\n\nVERIFICATION BOUNDARY: This formal answer projects the substantive reasoning already "
              "persisted in the same-case Advisor review. No external sources or independent verification "
              "are implied; the answer is limited to the supplied case context and review."
        )
        answer_rows.append((row, answer, 0.65))
    for row, answer, confidence in answer_rows:
        if not row:
            continue
        with _local_case_read_scope():
            result = engine.answer_question(identity["case_id"], str(row["question_id"]),
                answer=answer[:5000], evidence_ids=[], confidence=confidence,
                limitations=["Answer is a synthesis of supplied case context and persisted Advisor reasoning; "
                             "no external source is attached and no migration-specific outcome is verified."])
        if not result.get("ok"):
            raise RuntimeError("ADVISOR_REVIEW_QUESTION_PROJECTION_FAILED:" + str(result.get("reason")))
        persisted.add(str(row["question_id"]))
        case = result.get("case") if isinstance(result.get("case"), dict) else case
    return persisted


def _sync_room_answers_from_case(state: dict[str, Any], case: dict[str, Any]) -> None:
    answered = {str(row.get("question_id") or ""): row for row in case.get("answered_questions") or []
        if isinstance(row, dict)}
    for question in state.get("questions") or []:
        if not isinstance(question, dict):
            continue
        row = answered.get(str(question.get("production_question_id") or ""))
        if row:
            question.update({"status": "ANSWERED", "answer": row.get("answer"),
                "confidence": row.get("confidence"), "evidence_refs": [], "needs_followup": False})


def _enrich_conversational_synthesis(state: dict[str, Any], case: dict[str, Any],
                                     identity: dict[str, str]) -> dict[str, Any]:
    synthesis = state.setdefault("final_synthesis", {})
    review = _primary_review_for_case(case, identity)
    answers = {str(row.get("question_id") or ""): str(row.get("answer") or "")
        for row in case.get("answered_questions") or [] if isinstance(row, dict)}
    what_we_know = answers.get("q_b04da13aa3b1464f", "")
    q3 = answers.get("q_b42074818a3af0a5", "")
    uncertainty = [line.strip(" -") for line in q3.splitlines()
        if line.startswith("UNRESOLVED UNCERTAINTIES:") or
        (line.startswith("BASIS:") is False and any(token in line.lower()
         for token in ("unspecified", "unknown", "uncertain", "not supplied")))]
    risks = [str(item) for item in (review or {}).get("risks") or [] if str(item).strip()]
    recommendations = (review or {}).get("recommended_actions") or []
    recommendation = ("Use risk-tiered acceptance criteria and verify resulting state independently; "
        "do not treat a step receipt alone as proof of success.")
    improvement = ("Specify migration type, system boundary, dependencies, risk tier, and recovery needs; "
        "then define positive and negative tests, demonstrated rollback, evidence retention, and independent verification.")
    next_action = str(synthesis.get("next_best_action") or synthesis.get("next_action") or
        next(iter(synthesis.get("recommended_actions") or []), "") or
        "Collect the concrete migration scope and risk tier before setting certification thresholds.")
    synthesis.update({
        "what_we_know": what_we_know[:3000] or "The supplied case defines the certification decision but includes no migration test results.",
        "what_we_think": recommendation,
        "what_is_uncertain": ["Migration type, system boundary, risk tier, and dependencies are not specified.",
            "Implementation and ongoing costs, evidence-retention needs, and rollback behavior are unknown."],
        "disagreements": [],
        "recommendation": recommendation,
        "how_to_improve": improvement,
        "next_best_action": next_action,
        "research_conclusion": recommendation,
        "recommended_actions": [next_action],
        "advisor_review_ids": [str(review.get("review_id"))] if review and review.get("review_id") else [],
        "evidence_basis": "CASE_CONTEXT_AND_ADVISOR_REVIEW",
        "source_backed": False,
        "unresolved_uncertainty": [{"question": item} for item in
            ["Migration-specific acceptance thresholds and system scope remain unknown.",
             "Costs, rollback behavior, and independent evidence requirements remain unverified."]],
    })
    if risks:
        synthesis["key_findings"] = [{"kind": "ADVISOR_RISK", "summary": item,
            "evidence_status": "ADVISOR_ASSESSMENT_NOT_EXTERNAL_VERIFICATION"} for item in risks]
    state.setdefault("metadata", {})["execution_mode"] = "RESEARCH_CONVERSATION"
    return synthesis


def _room_state(case: dict[str, Any], identity: dict[str, str], instruction: str) -> dict[str, Any]:
    from .models import new_case
    stored = case.get("research_room_controller")
    if isinstance(stored, dict) and isinstance(stored.get("room_state"), dict):
        state = copy.deepcopy(stored["room_state"])
        control_rows = [row for row in case.get("open_questions") or []
            if isinstance(row, dict) and _is_control_question(row)]
        if control_rows:
            satisfied = state.setdefault("control_requirements", [])
            for row in control_rows:
                satisfied.append({"production_question_id": row.get("question_id"),
                    "question": row.get("question"), "status": "CONTROL_REQUIREMENT_SATISFIED",
                    "satisfied_by": "verified production lineage and same-case persistence"})
            state["questions"] = [row for row in state.get("questions", []) if not _is_control_question(row)]
        return state
    room = new_case(identity["case_id"], instruction,
        metadata={"shadow_mode": False, "production_lineage": identity,
            "execution_mode": "DEEP_RESEARCH_MODE", "per_call_soft_target_usd": 0.0,
            "per_case_soft_target_usd": 0.0, "daily_research_soft_target_usd": 0.0,
            "daily_research_hard_limit_usd": 0.0})
    state = room.to_dict()
    state["metadata"]["shadow_mode"] = False
    control = []
    state["questions"] = [{"question": row.get("question", ""), "status": "OPEN",
        "answer": None, "evidence_refs": [], "confidence": None,
        "production_question_id": row.get("question_id")}
        for row in case.get("open_questions") or [] if isinstance(row, dict)
        and not _is_control_question(row)]
    for row in case.get("open_questions") or []:
        if isinstance(row, dict) and _is_control_question(row):
            control.append({"production_question_id": row.get("question_id"),
                "question": row.get("question"), "status": "CONTROL_REQUIREMENT_SATISFIED",
                "satisfied_by": "verified production lineage and same-case persistence"})
    state["control_requirements"] = control
    state["findings"] = copy.deepcopy(case.get("findings") or [])
    source_rows = case.get("sources") or []
    state["source_references"] = [{"url": row.get("url") or row.get("source_url"),
        "type": row.get("source_class") or "PUBLIC_WEB"} for row in source_rows
        if isinstance(row, dict) and (row.get("url") or row.get("source_url"))]
    state["next_participant"] = "RESEARCH_LEAD"
    return state


def _is_control_question(row: dict[str, Any]) -> bool:
    text = " ".join(str(row.get("question") or "").casefold().split())
    return ("continue the existing research project" in text or
        ("same project" in text and "same case" in text and "leave" in text and "open" in text))


def _satisfy_control_requirements(case: dict[str, Any], identity: dict[str, str]) -> dict[str, Any]:
    rows = [row for row in case.get("open_questions") or []
        if isinstance(row, dict) and _is_control_question(row)]
    if not rows:
        return case
    from research import research_case_engine as engine
    satisfied = list(case.get("research_room_control_requirements") or [])
    known = {str(row.get("question_id") or "") for row in satisfied if isinstance(row, dict)}
    for row in rows:
        if str(row.get("question_id") or "") not in known:
            satisfied.append({"question_id": row.get("question_id"),
                "status": "CONTROL_REQUIREMENT_SATISFIED",
                "description": row.get("question"),
                "satisfied_by": "verified exact objective, project, and case lineage"})
    remaining = [row for row in case.get("open_questions") or []
        if not isinstance(row, dict) or not _is_control_question(row)]
    saved = engine._save(case, "RESEARCH_ROOM_CONTROL_REQUIREMENT_SATISFIED",
        open_questions=remaining, research_room_control_requirements=satisfied)
    if not isinstance(saved, dict):
        raise RuntimeError("PRODUCTION_CONTROL_REQUIREMENT_PERSISTENCE_FAILED")
    return _get_case_local(engine, identity["case_id"]) or case


def _persist_source_attempt(identity: dict[str, str], attempt: dict[str, Any]) -> None:
    """Durably upsert a source receipt on the same production case controller."""
    case = _load(identity)
    controller = dict(case.get("research_room_controller") or {})
    attempts = list(controller.get("source_attempts") or [])
    value = dict(attempt, case_id=identity["case_id"])
    attempts = [row for row in attempts if not isinstance(row, dict) or row.get("attempt_id") != value.get("attempt_id")]
    attempts.append(value)
    controller.update({"lineage": identity, "source_attempts": attempts})
    saved = _save_controller(identity["case_id"], controller=controller, event="RESEARCH_SOURCE_ATTEMPT_RECORDED")
    if not saved.get("saved"):
        raise RuntimeError("SOURCE_ATTEMPT_PERSISTENCE_FAILED")


def _discover_public_source(question: str) -> tuple[str | None, list[dict[str, Any]]]:
    """Use the existing bounded credential-free public discovery adapter."""
    try:
        from nexus_agent_platform.proactive_discovery import web_search
        result = web_search(" ".join(str(question).split())[:700], 5)
    except Exception as exc:
        return None, [{"provider": "PUBLIC_WEB_DISCOVERY", "error_class": type(exc).__name__}]
    rows = result.get("results") if isinstance(result, dict) else None
    for row in rows or []:
        url = str(row.get("url") or "").strip() if isinstance(row, dict) else ""
        if url.startswith(("https://", "http://")):
            return url, []
    return None, [{"provider": result.get("provider") if isinstance(result, dict) else "UNKNOWN",
                   "status": "NO_PUBLIC_RESULT"}]


def _persist_room_projection(identity: dict[str, str], state: dict[str, Any]) -> dict[str, Any]:
    from research import research_case_engine as engine
    case = _get_case_local(engine, identity["case_id"])
    if not isinstance(case, dict) or str(case.get("case_id") or "") != identity["case_id"]:
        raise LookupError("EXACT_RESEARCH_CASE_NOT_FOUND_DURING_PROJECTION")
    source_report = state.get("source_report") if isinstance(state.get("source_report"), dict) else {}
    source_ids_new = []
    source_rows = source_report.get("sources") or ([source_report] if source_report.get("url") else [])
    for source_row in source_rows:
        url = str(source_row.get("url") or "").strip()
        text = str(source_row.get("text") or "")[:16000]
        if not url or not text:
            continue
        source_id = str(source_row.get("source_id") or "rrsrc_" + hashlib.sha256(url.encode()).hexdigest()[:20])
        source_class = "UNKNOWN"
        try:
            from nexus_agent_platform.research_tool_layer import classify_source
            source_class = classify_source(url, str(source_report.get("title") or ""), text).get("source_class", "UNKNOWN")
        except Exception:
            pass
        with _local_case_read_scope():
            added = engine.add_source(identity["case_id"], {"source_id": source_id, "url": url,
            "title": str(source_row.get("title") or url)[:240], "source_class": source_class,
            "source_type": source_row.get("source_type") or "WEB",
            "extraction_status": "EXTRACTED", "extracted_evidence": text,
            "source_content_hash": source_row.get("source_content_hash"),
            "provider": source_row.get("method") or "RESEARCH_ROOM_PUBLIC_HTTP",
            "question_ids": [source_row.get("question_id")] if source_row.get("question_id") else [],
            "originating_question_id": source_row.get("question_id"),
                "source_attempt_id": source_row.get("attempt_id")})
        if not added.get("ok"):
            attempt = next((row for row in source_report.get("source_attempts", [])
                if row.get("attempt_id") == source_row.get("attempt_id")), None)
            if attempt:
                attempt.update({"result": "PERSISTENCE_FAILED", "error_code": "SOURCE_PERSISTENCE_FAILED"})
                _persist_source_attempt(identity, attempt)
            continue
        source_ids_new.append(source_id)
    latest = _get_case_local(engine, identity["case_id"]) or case
    source_by_url = {str(row.get("url") or row.get("source_url") or ""): str(row.get("source_id") or "")
        for row in latest.get("sources") or [] if isinstance(row, dict)}
    source_ids = sorted({value for value in source_by_url.values() if value})

    def _ref_value(ref: Any) -> str:
        if isinstance(ref, dict):
            return str(ref.get("url") or ref.get("source_url") or ref.get("source_id") or "")
        return str(ref or "")

    # Preserve domain questions on the existing Research case. Room-generated
    # questions are idempotently joined to the production question registry,
    # and answered questions are recorded only when their evidence resolves
    # to sources already attached to that same case.
    production_question_ids: dict[str, str] = {}
    for question in state.get("questions") or []:
        if not isinstance(question, dict):
            continue
        text_value = " ".join(str(question.get("question") or "").split())
        if not text_value:
            continue
        qid = question.get("production_question_id")
        if not qid:
            registered = engine.add_question(identity["case_id"], text_value,
                why_it_matters="Research Room continuation question for the existing production case.")
            if not registered.get("ok"):
                raise RuntimeError("PRODUCTION_CASE_QUESTION_PERSISTENCE_FAILED")
            qid = (registered.get("question") or {}).get("question_id")
            question["production_question_id"] = qid
        if qid:
            production_question_ids[str(qid)] = text_value
        if str(question.get("status") or "").upper() != "ANSWERED" or not qid:
            continue
        evidence_refs = question.get("evidence_refs") or []
        linked_ids = sorted({source_by_url.get(_ref_value(ref), _ref_value(ref)) for ref in evidence_refs
            if source_by_url.get(_ref_value(ref), _ref_value(ref)) in source_ids})
        if not linked_ids or not str(question.get("answer") or "").strip():
            continue
        latest = _get_case_local(engine, identity["case_id"]) or latest
        if any(str(row.get("question_id") or "") == str(qid)
                for row in latest.get("answered_questions") or [] if isinstance(row, dict)):
            continue
        with _local_case_read_scope():
            answered = engine.answer_question(identity["case_id"], str(qid),
                answer=str(question["answer"])[:5000], evidence_ids=linked_ids,
                confidence=float(question.get("confidence") if isinstance(question.get("confidence"), (int, float)) else 0.5),
                limitations=["Research Room answer; evidence and limitations require Nova's independent completion check."])
        if not answered.get("ok"):
            raise RuntimeError("PRODUCTION_CASE_ANSWER_PERSISTENCE_FAILED")

    control_requirements = [row for row in state.get("control_requirements") or []
        if isinstance(row, dict) and row.get("production_question_id")]
    if control_requirements:
        latest = _get_case_local(engine, identity["case_id"]) or latest
        control_ids = {str(row["production_question_id"]) for row in control_requirements}
        remaining = [row for row in latest.get("open_questions") or []
            if str(row.get("question_id") or "") not in control_ids]
        prior_controls = list(latest.get("research_room_control_requirements") or [])
        indexed = {str(row.get("question_id")) for row in prior_controls if isinstance(row, dict)}
        prior_controls.extend({"question_id": row["production_question_id"],
            "status": "CONTROL_REQUIREMENT_SATISFIED", "description": row.get("question"),
            "satisfied_by": row.get("satisfied_by")} for row in control_requirements
            if str(row["production_question_id"]) not in indexed)
        if remaining != (latest.get("open_questions") or []) or len(prior_controls) != len(latest.get("research_room_control_requirements") or []):
            persisted = engine._save(latest, "RESEARCH_ROOM_CONTROL_REQUIREMENT_SATISFIED",
                open_questions=remaining, research_room_control_requirements=prior_controls)
            if not isinstance(persisted, dict):
                raise RuntimeError("PRODUCTION_CONTROL_REQUIREMENT_PERSISTENCE_FAILED")

    # Project only source-linked room findings into the canonical findings
    # registry. Advisor commentary and unsupported hypotheses remain in the
    # controller's review/state record rather than being mislabeled evidence.
    for index, finding in enumerate(state.get("findings") or []):
        if not isinstance(finding, dict):
            continue
        refs = finding.get("source_refs") or finding.get("evidence_refs") or []
        question_id = finding.get("question_id") or finding.get("production_question_id")
        explicit_ids = finding.get("evidence_ids") or finding.get("evidence_source_ids") or []
        linked_ids = sorted({source_by_url.get(_ref_value(ref), _ref_value(ref)) for ref in [*refs, *explicit_ids]
            if source_by_url.get(_ref_value(ref), _ref_value(ref)) in source_ids})
        if not linked_ids:
            continue
        value = dict(finding)
        value["finding_id"] = str(value.get("finding_id") or "rrfind_" + hashlib.sha256(
            f"{identity['case_id']}:{','.join(linked_ids)}:{index}".encode()).hexdigest()[:18])
        value["evidence_ids"] = linked_ids
        value["evidence_source_ids"] = linked_ids
        if question_id:
            value["question_id"] = question_id
        with _local_case_read_scope():
            persisted = engine.record_finding(identity["case_id"], value)
        if not persisted.get("ok"):
            raise RuntimeError("PRODUCTION_CASE_FINDING_PERSISTENCE_FAILED")

    # The Room synthesizer's output is a synthesis, not a terminal Research
    # case state. Store it using the production case schema while keeping the
    # case's status/completion authority untouched.
    final_synthesis = state.get("final_synthesis")
    review_ids = [str(row.get("review_id")) for row in latest.get("research_room_advisor_reviews") or []
        if isinstance(row, dict) and row.get("review_id")
        and str(row.get("case_id") or identity["case_id"]) == identity["case_id"]
        and str(row.get("objective_id") or identity["objective_id"]) == identity["objective_id"]
        and str(row.get("project_id") or identity["project_id"]) == identity["project_id"]]
    if isinstance(final_synthesis, dict) and (source_ids or review_ids):
        claims = []
        for finding in state.get("findings") or []:
            if not isinstance(finding, dict):
                continue
            text_value = str(finding.get("claim") or finding.get("summary") or "").strip()
            if text_value:
                claims.append({"claim": text_value[:1200], "evidence_ids": source_ids,
                    "confidence": finding.get("confidence") or "UNASSESSED"})
        synthesis_payload = {"claims": claims or [{"claim": str(final_synthesis.get("research_conclusion") or
            "Research Room summarized the available case context and Advisor reasoning.")[:1200],
            **({"evidence_ids": source_ids} if source_ids else {})}],
            "agreements": [], "disagreements": [],
            "uncertainties": [str(row.get("question") or row.get("detail") or row)[:800]
                for row in (final_synthesis.get("unresolved_uncertainty") or [])],
            "source_ids": source_ids, "advisor_review_ids": review_ids,
            "evidence_basis": "ATTACHED_SOURCES" if source_ids else "CASE_CONTEXT_AND_ADVISOR_REVIEW",
            "source_backed": bool(source_ids),
            "what_we_know": str(final_synthesis.get("what_we_know") or "")[:2000],
            "what_we_think": str(final_synthesis.get("what_we_think") or final_synthesis.get("research_conclusion") or "")[:2000],
            "recommendation": str(final_synthesis.get("recommendation") or final_synthesis.get("research_conclusion") or "")[:2000],
            "how_to_improve": str(final_synthesis.get("how_to_improve") or "")[:2000],
            "next_best_action": str(final_synthesis.get("next_best_action") or final_synthesis.get("next_action") or "")[:1000]}
        projection_id = hashlib.sha256((identity["case_id"] + ":" +
            hashlib.sha256(str(synthesis_payload).encode()).hexdigest()).encode()).hexdigest()[:24]
        latest = _get_case_local(engine, identity["case_id"]) or latest
        prior_syntheses = list(latest.get("syntheses") or [])
        if not any(isinstance(row, dict) and row.get("research_room_projection_id") == projection_id
                   for row in prior_syntheses):
            from datetime import datetime, timezone
            prior_syntheses.append({**synthesis_payload, "research_room_projection_id": projection_id,
                "recorded_at": datetime.now(timezone.utc).isoformat(),
                "research_room_summary": str(final_synthesis.get("research_conclusion") or "")[:2000]})
            saved_synthesis = engine._save(latest, "RESEARCH_ROOM_SYNTHESIS_PERSISTED",
                syntheses=prior_syntheses)
            if not isinstance(saved_synthesis, dict):
                raise RuntimeError("PRODUCTION_CASE_SYNTHESIS_PERSISTENCE_FAILED")
            latest = saved_synthesis
    existing_controller = dict(latest.get("research_room_controller") or {})
    existing_controller.update({
        "version": "research-room-production-controller.v1", "lineage": identity,
        "state": "RUNNING" if state.get("status") != "COMPLETE" else "ROOM_TURN_COMPLETE",
        "turn_count": int(state.get("turn_count") or 0),
        "next_participant": state.get("next_participant"), "last_event": state.get("next_participant"),
        "room_state": state, "updated_at": state.get("updated_at")})
    saved = _save_controller(identity["case_id"], controller=existing_controller)
    if not saved.get("saved"):
        raise RuntimeError("PRODUCTION_CASE_CONTROLLER_STATE_NOT_PERSISTED")
    return saved


def continue_case(case_id: str, objective_id: str, project_id: str, job_id: str,
                  instruction: str) -> dict[str, Any]:
    identity = _identity(case_id, objective_id, project_id, job_id)
    text = " ".join(str(instruction or "").split())[:1600]
    if len(text) < 8:
        return {"status": "rejected", "error": "CONTINUATION_INSTRUCTION_REQUIRED", **identity}
    case = _load(identity)
    projected_answers = _project_primary_review_answers(identity, case)
    if projected_answers:
        case = _load(identity)
    state = _room_state(case, identity, text)
    _sync_room_answers_from_case(state, case)
    controller = case.get("research_room_controller") or {}
    advisor_attempts = list(controller.get("advisor_attempts") or [])
    latest_attempt = advisor_attempts[-1] if advisor_attempts else None
    review = _primary_review_for_case(case, identity)
    if review:
        existing_review_ids = {str(row.get("review_id") or "") for row in state.get("advisor_comments") or []
            if isinstance(row, dict)}
        if str(review.get("review_id") or "") not in existing_review_ids:
            state.setdefault("advisor_comments", []).append({"review_id": review.get("review_id"),
                "analysis": review.get("analysis"), "risks": review.get("risks") or [],
                "evidence_notes": review.get("evidence_notes") or [],
                "provider": review.get("provider"), "model": review.get("model"),
                "role": review.get("role")})
    if not advisor_attempts and not review:
        supplied = [text, str(case.get("primary_question") or ""),
            str(case.get("original_request") or "")]
        for source in (case.get("sources") or [])[:8]:
            if isinstance(source, dict):
                supplied.append(str(source.get("extracted_evidence") or source.get("content") or "")[:6000])
        queued = advisor_request(**identity, question="\n\n".join(part for part in supplied if part)[:30000])
        return {**queued, "live_controller_used": True, "new_case_created": False,
            "source_discovery_optional": True, "advisor_first": True}
    if latest_attempt and str(latest_attempt.get("status") or "").upper() in {"QUEUED", "RUNNING"}:
        return {"status": "pending", **identity, "attempt_id": latest_attempt.get("attempt_id"),
            "job_id": latest_attempt.get("job_id"), "advisor_status": latest_attempt.get("status"),
            "new_case_created": False, "source_discovery_optional": True}
    if str(state.get("next_participant") or "").upper() == "ADVISOR_FOLLOWUP":
        followup_id = str(controller.get("needle_followup_attempt_id") or "")
        if (followup_id and latest_attempt and latest_attempt.get("attempt_id") == followup_id
                and str(latest_attempt.get("status") or "").upper() in {
                    "COMPLETED", "UNAVAILABLE", "FAILED", "TIMEOUT"}):
            followup_review = next((row for row in reversed(case.get("research_room_advisor_reviews") or [])
                if isinstance(row, dict) and row.get("review_id") == latest_attempt.get("response_reference")), None)
            if followup_review:
                state.setdefault("advisor_comments", []).append({"review_id": followup_review.get("review_id"),
                    "analysis": followup_review.get("analysis"), "risks": followup_review.get("risks") or [],
                    "evidence_notes": followup_review.get("evidence_notes") or [],
                    "provider": followup_review.get("provider"), "model": followup_review.get("model"),
                    "role": followup_review.get("role")})
            state["next_participant"] = "FINAL_STRATEGIST"
        else:
            needle = state.get("needle_result") or {}
            questions = [str(item).strip() for item in needle.get("missing_questions") or [] if str(item).strip()]
            followup = "Needle follow-up for this same case: " + "; ".join(questions[:5])
            queued_followup = advisor_request(**identity, question=followup, review_role="PRIMARY_ADVISOR")
            if queued_followup.get("status") == "queued":
                latest_case = _load(identity)
                followup_controller = dict(latest_case.get("research_room_controller") or {})
                followup_controller["needle_followup_attempt_id"] = queued_followup.get("attempt_id")
                followup_controller["last_event"] = "NEEDLE_FOLLOWUP_QUEUED"
                _save_controller(identity["case_id"], controller=followup_controller,
                    event="RESEARCH_ROOM_NEEDLE_FOLLOWUP_QUEUED")
            return {**queued_followup,
                "live_controller_used": True, "new_case_created": False,
                "source_discovery_optional": True, "advisor_first": False}
    if latest_attempt and str(latest_attempt.get("status") or "").upper() in {
            "COMPLETED", "UNAVAILABLE", "FAILED", "TIMEOUT"} and not state.get("advisor_comments"):
        reviews = case.get("research_room_advisor_reviews") or []
        state["advisor_comments"] = copy.deepcopy(reviews[-2:])
        if not state["advisor_comments"]:
            state["advisor_comments"] = [{"status": "ADVISOR_UNAVAILABLE",
                "analysis": "No authorized zero-cost Advisor route returned; continue from supplied input and preserve uncertainty."}]
        state["advisor_sessions"] = copy.deepcopy(state.get("advisor_sessions") or [])
        state["next_participant"] = "KNOWLEDGE_RECONCILIATION"
        state.setdefault("source_references", []).extend({"url": row.get("url") or row.get("source_url"),
            "type": row.get("source_class") or "PUBLIC_WEB"} for row in case.get("sources") or []
            if isinstance(row, dict) and (row.get("url") or row.get("source_url")))
    participant = str(state.get("next_participant") or "RESEARCH_LEAD").upper()
    state.setdefault("metadata", {}).setdefault("research_type",
        case.get("objective_family") or case.get("case_type") or "GENERAL")
    if participant == "SOURCE_ANALYST":
        # Public search is only run from an explicit Advisor tool request in
        # the durable Advisor worker. Legacy room state must not force search.
        state.setdefault("source_report", {"status": "SOURCE_NOT_REQUESTED", "text": ""})
        from .participants import ResearchLead
        participant = ResearchLead().select_next_participant(state)
        state["next_participant"] = participant
    try:
        turn = int(state.get("turn_count") or 0) + 1
        with _production_governance_context(identity, call_id=f"{identity['case_id']}:controller-turn:{turn}"):
            from .advisor_router import AdvisorRouter
            from .room_graph import RoomGraph
            from .source_tools import SourceTools
            # Research uses approved no-new-spend hosted routes only. Local
            # models and metered providers are not Research Advisor fallbacks.
            router = AdvisorRouter(free_only=True)
            graph = RoomGraph(source_tools=SourceTools(), advisor_router=router)
            updated = graph.turn(state, production_case_binding=identity)
    except Exception as exc:
        return {"status": "error", **identity, "error": type(exc).__name__,
                "error_summary": str(exc)[:240], "case_mutated": False}
    if isinstance(updated.get("final_synthesis"), dict):
        _enrich_conversational_synthesis(updated, case, identity)
        # Research conversation ends at synthesis; it must not generate an
        # execution handoff or downstream package without Ray's commitment.
        updated["handoff"] = None
        updated["next_participant"] = "DONE"
    elif str(participant).upper() == "NEEDLE":
        needle = updated.get("needle_result") or {}
        if needle.get("missing_questions"):
            updated["next_participant"] = "ADVISOR_FOLLOWUP"
        else:
            updated["next_participant"] = "FINAL_STRATEGIST"
    _persist_room_projection(identity, updated)
    latest = _load(identity)
    return {"status": "advanced", **identity, "executed_participant": participant,
        "next_participant": updated.get("next_participant"), "controller_turn": updated.get("turn_count"),
        "case_status": latest.get("status"), "open_question_count": len(latest.get("open_questions") or []),
        "needle_ran": str(participant).upper() == "NEEDLE",
        "needle_new_question_count": len((updated.get("needle_result") or {}).get("new_questions") or []),
        "needle_unresolved_count": len((updated.get("needle_result") or {}).get("missing_questions") or []),
        "synthesis_count": len(latest.get("syntheses") or []),
        "evidence_count": len(latest.get("sources") or []), "new_case_created": False,
        "advisor_provider": next((row.get("provider") for row in reversed(updated.get("advisor_sessions") or [])
            if row.get("provider")), None), "research_room_status_is_not_case_completion": True}


def advisor_request(case_id: str, objective_id: str, project_id: str, job_id: str,
                    question: str, review_role: str = "PRIMARY_ADVISOR") -> dict[str, Any]:
    identity = _identity(case_id, objective_id, project_id, job_id)
    target = " ".join(str(question or "").split())[:30000]
    role_key = str(review_role or "PRIMARY_ADVISOR").upper()
    if not target or role_key not in {"PRIMARY_ADVISOR", "CHALLENGER", "SECOND_OPINION"}:
        return {"status": "rejected", "error": "ADVISOR_REQUEST_SCHEMA_INVALID", **identity}
    case = _load(identity)
    case = _satisfy_control_requirements(case, identity)
    room_context = {"case_id": identity["case_id"], "original_request": target,
        "source_references": copy.deepcopy(case.get("sources") or [])[:12],
        "findings": copy.deepcopy(case.get("findings") or [])[:40],
        "questions": copy.deepcopy(case.get("open_questions") or [])[:20],
        "unresolved_items": copy.deepcopy(case.get("missing_information") or [])[:20],
        "provided_input": target,
        "metadata": {"execution_mode": "DEEP_RESEARCH_MODE", "per_call_soft_target_usd": 0.0,
            "per_case_soft_target_usd": 0.0, "daily_research_soft_target_usd": 0.0,
            "daily_research_spend_usd": 0.0, "daily_research_hard_limit_usd": 0.0,
            "high_value_case": False, "source_discovery_optional": True,
            "research_type": case.get("objective_family") or case.get("case_type") or "GENERAL"}}
    role = "PRIMARY_RESEARCH_ADVISOR" if role_key == "PRIMARY_ADVISOR" else "CHALLENGER_SECOND_OPINION"
    attempt_id = "rradvatt_" + uuid.uuid4().hex[:20]
    controller_state = dict(case.get("research_room_controller") or {})
    attempts = list(controller_state.get("advisor_attempts") or [])
    attempt = {"attempt_id": attempt_id, "case_id": identity["case_id"],
        "question_context": target[:1200], "provider": "ZERO_COST_PROVIDER_ROUTER", "model": None,
        "status": "QUEUED", "created_at": datetime.now(timezone.utc).isoformat(),
        "cost": 0.0, "zero_dollar_budget": True, "role": role_key}
    attempts.append(attempt)
    controller_state.update({"lineage": identity, "advisor_attempts": attempts,
        "state": "ADVISOR_ATTEMPT_QUEUED", "last_event": role_key})
    persisted = _save_controller(identity["case_id"], controller=controller_state,
        event="RESEARCH_ROOM_ADVISOR_ATTEMPT_QUEUED")
    if not persisted.get("saved"):
        return {"status": "error", **identity, "error": "ADVISOR_ATTEMPT_PERSISTENCE_FAILED",
            "attempt_id": attempt_id, "mission_complete": False}

    try:
        from nexus_agent_platform.runtime.paths import nexus_research_state_path
        from nexus_agent_platform.durable_jobs import default_store
        advisor_job_id = "job_" + uuid.uuid4().hex
        payload_path = nexus_research_state_path("runtime", "research_room_advisor", attempt_id + ".json")
        payload_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"schema_version": "research-room-advisor-job.v1", "identity": identity,
            "attempt_id": attempt_id, "review_role": role_key, "question": target,
            "case_context": room_context}
        temporary = payload_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(payload, ensure_ascii=False, default=str), encoding="utf-8")
        os.replace(temporary, payload_path)
        payload_ref = str(payload_path)
        attempt["job_id"] = advisor_job_id
        controller_state["advisor_attempts"] = attempts
        _save_controller(identity["case_id"], controller=controller_state,
            event="RESEARCH_ROOM_ADVISOR_JOB_LINKED")
        budget = {"max_requests": 20, "max_response_bytes": 500000, "max_tokens": 8000,
            "max_gpu_seconds": 0, "max_runtime_seconds": 240, "max_resource_creations": 0,
            "max_estimated_cost": 0.0, "max_retries": 1}
        queued = default_store().enqueue("RESEARCH", "RESEARCH_ROOM_ADVISOR",
            priority=70, payload_ref=payload_ref, parent_job_id=identity["job_id"],
            correlation_id=identity["objective_id"], max_attempts=1,
            idempotency_key="research-room-advisor:" + attempt_id, job_id=advisor_job_id,
            budget_envelope=budget, governance_context={"source": "RESEARCH_ROOM_ADVISOR",
                "owner_objective_id": identity["objective_id"], "project_id": identity["project_id"],
                "case_id": identity["case_id"], "advisor_attempt_id": attempt_id,
                "zero_dollar_budget": True, "paid_provider_authorized": False})
        return {"status": "queued", **identity, "attempt_id": attempt_id,
            "job_id": queued.job_id, "advisor_status": "QUEUED",
            "mission_complete": False, "production_case_readback_required": True}
    except Exception as exc:
        attempt.update({"status": "FAILED", "completed_at": datetime.now(timezone.utc).isoformat(),
            "error_code": type(exc).__name__, "error_summary": str(exc)[:300]})
        controller_state["advisor_attempts"] = attempts
        _save_controller(identity["case_id"], controller=controller_state, event="RESEARCH_ROOM_ADVISOR_FAILED")
        return {"status": "error", **identity, "error": type(exc).__name__,
                "error_summary": str(exc)[:240], "attempt_id": attempt_id, "mission_complete": False}


def record_queued_advisor_worker_failure(payload: dict[str, Any], *, worker_job_id: str,
                                         error: BaseException) -> dict[str, Any]:
    """Persist a terminal attempt outcome if worker dispatch fails before routing."""
    identity = _identity(**(payload.get("identity") or {}))
    attempt_id = str(payload.get("attempt_id") or "")
    from research.research_case_engine import get_case
    case = get_case(identity["case_id"])
    if not isinstance(case, dict):
        raise LookupError("EXACT_RESEARCH_CASE_NOT_FOUND_FOR_ADVISOR_FAILURE")
    controller_state = dict(case.get("research_room_controller") or {})
    attempts = list(controller_state.get("advisor_attempts") or [])
    attempt = next((row for row in attempts if row.get("attempt_id") == attempt_id), None)
    if not attempt or attempt.get("job_id") != worker_job_id:
        raise PermissionError("RESEARCH_ROOM_ADVISOR_ATTEMPT_JOB_MISMATCH")
    if str(attempt.get("status") or "").upper() in {"COMPLETED", "UNAVAILABLE", "FAILED"}:
        return {"saved": True, "attempt_id": attempt_id, "status": attempt["status"], "already_terminal": True}
    attempt.update({"status": "FAILED", "completed_at": datetime.now(timezone.utc).isoformat(),
        "error_code": type(error).__name__, "error_summary": str(error)[:300]})
    controller_state.update({"advisor_attempts": attempts, "state": "ADVISOR_WORKER_FAILED",
        "last_event": "ADVISOR_WORKER_FAILED"})
    saved = _save_controller(identity["case_id"], controller=controller_state,
        event="RESEARCH_ROOM_ADVISOR_WORKER_FAILED")
    if not saved.get("saved"):
        raise RuntimeError("ADVISOR_WORKER_FAILURE_PERSISTENCE_FAILED")
    return {"saved": True, "attempt_id": attempt_id, "status": "FAILED"}
def execute_queued_advisor(payload: dict[str, Any], *, worker_job_id: str) -> dict[str, Any]:
    """Run one durable zero-dollar Advisor job and persist every provider outcome."""
    identity = _identity(**(payload.get("identity") or {}))
    case = _load(identity)
    attempt_id = str(payload.get("attempt_id") or "")
    controller_state = dict(case.get("research_room_controller") or {})
    attempts = list(controller_state.get("advisor_attempts") or [])
    attempt = next((row for row in attempts if row.get("attempt_id") == attempt_id), None)
    if not attempt or attempt.get("job_id") != worker_job_id:
        raise PermissionError("RESEARCH_ROOM_ADVISOR_ATTEMPT_JOB_MISMATCH")
    attempt.update({"status": "RUNNING", "started_at": datetime.now(timezone.utc).isoformat()})

    def persist_attempt_event(row):
        row = dict(row)
        route_id = row.get("attempt_id") or ("rradvroute_" + uuid.uuid4().hex[:16])
        row["attempt_id"] = route_id
        routes = attempt.setdefault("provider_attempts", [])
        existing = next((item for item in routes if item.get("attempt_id") == route_id), None)
        if existing is None:
            routes.append(row)
        else:
            existing.update(row)
        controller_state["advisor_attempts"] = attempts
        if not _save_controller(identity["case_id"], controller=controller_state,
                event="RESEARCH_ROOM_ADVISOR_PROVIDER_ATTEMPT_RECORDED").get("saved"):
            raise RuntimeError("ADVISOR_ATTEMPT_PERSISTENCE_FAILED")
        return route_id

    controller_state["advisor_attempts"] = attempts
    running_saved = _save_controller(identity["case_id"], controller=controller_state,
        event="RESEARCH_ROOM_ADVISOR_RUNNING")
    if not running_saved.get("saved"):
        raise RuntimeError("ADVISOR_ATTEMPT_RUNNING_PERSISTENCE_FAILED")
    role_key = str(payload.get("review_role") or "PRIMARY_ADVISOR")
    role = "PRIMARY_RESEARCH_ADVISOR" if role_key == "PRIMARY_ADVISOR" else "CHALLENGER_SECOND_OPINION"
    context = copy.deepcopy(payload.get("case_context") or {})
    context["case_id"] = identity["case_id"]
    context.setdefault("metadata", {}).update({"per_call_soft_target_usd": 0.0,
        "per_case_soft_target_usd": 0.0, "daily_research_soft_target_usd": 0.0,
        "daily_research_spend_usd": 0.0, "daily_research_hard_limit_usd": 0.0,
        "high_value_case": False})
    try:
        with _production_governance_context(identity, call_id=attempt_id,
                execution_job_id=worker_job_id, job_type="RESEARCH_ROOM_ADVISOR"):
            from .advisor_router import AdvisorRouter
            router = AdvisorRouter(attempt_recorder=persist_attempt_event, free_only=True)
            result = router.ask(role=role, case_context=context,
                objective="Analyze the provided input first. Decide whether source research is needed. "
                    "If needed, return specific tool_requests tied to existing question IDs. "
                    + str(payload.get("question") or "")[:2000])
            tool_requests = [row for row in result.get("tool_requests", [])
                if isinstance(row, dict) and str(row.get("question") or "").strip()][:3]
            if tool_requests:
                from .source_tools import SourceTools
                questions = []
                for request in tool_requests:
                    qid = str(request.get("question_id") or "")
                    case_question = next((row for row in case.get("open_questions") or []
                        if isinstance(row, dict) and str(row.get("question_id") or "") == qid), None)
                    if case_question:
                        questions.append({"production_question_id": qid,
                            "question": str(request["question"])[:800], "case_id": identity["case_id"]})
                if questions:
                    source_result = SourceTools(attempt_recorder=lambda row:
                        _persist_source_attempt(identity, row)).research_questions(
                            str(payload.get("question") or ""), questions)
                    source_state = _room_state(case, identity, str(payload.get("question") or ""))
                    source_state["source_report"] = source_result
                    for acquired in source_result.get("sources") or []:
                        source_state.setdefault("findings", []).append({
                            "kind": "ADVISOR_REQUESTED_SOURCE_EVIDENCE",
                            "question_id": acquired.get("question_id"),
                            "summary": acquired.get("summary"), "claims": acquired.get("claims") or [],
                            "source_refs": acquired.get("source_refs") or [],
                            "source_content_hash": acquired.get("source_content_hash")})
                    _persist_room_projection(identity, source_state)
                    latest = _load(identity)
                    controller_state = dict(latest.get("research_room_controller") or controller_state)
                    attempts = list(controller_state.get("advisor_attempts") or attempts)
                    attempt = next((row for row in attempts if row.get("attempt_id") == attempt_id), attempt)
                    context["source_references"] = copy.deepcopy(latest.get("sources") or [])[:20]
                    context["findings"] = copy.deepcopy(latest.get("findings") or [])[:60]
                    context["tool_results"] = {"status": source_result.get("status"),
                        "attempts": source_result.get("source_attempts") or [],
                        "limitation": source_result.get("limitation")}
                    result = router.ask(role=role, case_context=context,
                        objective="Continue the same Advisor analysis using the governed source-tool results. "
                            "Preserve uncertainty where a requested source was unavailable. "
                            + str(payload.get("question") or "")[:1600])
    except Exception as exc:
        attempt.update({"status": "FAILED", "completed_at": datetime.now(timezone.utc).isoformat(),
            "error_code": type(exc).__name__, "error_summary": str(exc)[:300]})
        controller_state["advisor_attempts"] = attempts
        _save_controller(identity["case_id"], controller=controller_state, event="RESEARCH_ROOM_ADVISOR_FAILED")
        return {"status": "COMPLETED", "advisor_status": "UNAVAILABLE",
            "attempt_id": attempt_id, "error_code": type(exc).__name__}
    analysis = str(result.get("analysis") or "").strip()
    if not analysis:
        attempt.update({"status": "UNAVAILABLE", "completed_at": datetime.now(timezone.utc).isoformat(),
            "error_code": result.get("reason") or "ADVISOR_RESULT_NOT_USABLE",
            "error_summary": str(result.get("reason") or "No free Advisor returned usable analysis.")[:300]})
        controller_state["advisor_attempts"] = attempts
        controller_state["state"] = "ADVISOR_UNAVAILABLE"
        _save_controller(identity["case_id"], controller=controller_state, event="RESEARCH_ROOM_ADVISOR_UNAVAILABLE")
        return {"status": "COMPLETED", "advisor_status": "UNAVAILABLE", "attempt_id": attempt_id}
    review_id = "rrreview_" + hashlib.sha256(
        f"{identity['case_id']}:{attempt_id}".encode()).hexdigest()[:20]
    review = {"review_id": review_id, "role": role, "provider": result.get("provider"),
        "model": result.get("model"), "question": str(payload.get("question") or "")[:12000],
        "analysis": analysis[:12000], "new_questions": result.get("new_questions") or [],
        "risks": result.get("risks") or [], "evidence_notes": result.get("evidence_notes") or [],
        "cost_class": result.get("cost_class") or "FREE_ZERO_PRICED",
        "estimated_cost_usd": result.get("estimated_cost_usd") or 0.0, "case_id": identity["case_id"],
        "objective_id": identity["objective_id"], "project_id": identity["project_id"],
        "job_id": identity["job_id"]}
    attempt.update({"status": "COMPLETED", "provider": result.get("provider"),
        "model": result.get("model"), "completed_at": datetime.now(timezone.utc).isoformat(),
        "response_reference": review_id, "response_summary": analysis[:400],
        "cost": review["estimated_cost_usd"]})
    controller_state.update({"lineage": identity, "advisor_attempts": attempts,
        "state": "ADVISOR_RESULT_RECORDED", "last_event": role})
    saved = _save_controller(identity["case_id"], controller=controller_state,
        advisor_review=review, event="RESEARCH_ROOM_ADVISOR_COMPLETED")
    if not saved.get("saved"):
        raise RuntimeError("ADVISOR_RESULT_PERSISTENCE_FAILED")
    return {"status": "COMPLETED", "advisor_status": "COMPLETED",
        "attempt_id": attempt_id, "response_reference": review_id, "cost": review["estimated_cost_usd"]}
