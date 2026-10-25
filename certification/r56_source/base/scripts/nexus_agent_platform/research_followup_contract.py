"""Canonical structured contract for department-to-Research follow-ups.

Records are stored in the existing governed ``research_requests`` collection;
question rows and evidence packets use the existing ``research_questions``
collection. This module adds a contract, not another queue or handoff system.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from typing import Any, Iterable

from nexus_agent_platform.governed import persistence

CONTRACT_SCHEMA = "nexus.research-followup-contract.v1"
ALLOWED_STATUSES = {"OPEN", "IN_RESEARCH", "PARTIAL", "ANSWERED", "RETURNED", "CLOSED", "CANCELLED"}
DEPARTMENT_QUESTION_STARTERS = {
    "OPPORTUNITIES": ["customer problem and affected customer", "current alternatives and competitors", "willingness to pay and demand evidence", "monetization and affiliate availability", "distribution options", "regulatory and operational constraints", "minimum viable test and success criteria"],
    "TRADING": ["original strategy rules and source provenance", "market or pair and timeframe", "session and regime assumptions", "indicator definitions and parameter intent", "entry, exit, stop, and take-profit logic"],
    "MARKETING": ["customer language and objections", "competitor messaging and offer comparisons", "SEO/search demand and platform trends", "audience behavior and channel evidence", "content performance benchmarks"],
    "CREATIVE": ["verified factual inputs needed by the brief", "platform format and visual-reference trends", "audience creative preferences"],
    "LABS": ["official documentation and system requirements", "model specifications and license", "benchmarks, compatibility, and limitations", "provider pricing and installation requirements"],
    "UPGRADE_CONTROL": ["security and compatibility evidence", "cost and reliability evidence", "rollback and licensing requirements", "production support and provider durability"],
    "SYSTEMS": ["official provider incident or outage evidence", "official migration guidance", "dependency compatibility and vendor support status"],
}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _stable_id(prefix: str, value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, default=str).encode()
    return f"{prefix}_{hashlib.sha256(raw).hexdigest()[:24]}"


def question(question: str, evidence_type_required: str, preferred_source_type: str,
             minimum_evidence_standard: str, *, blocking: bool = True,
             question_id: str | None = None) -> dict[str, Any]:
    text = str(question).strip()
    return {"question_id": question_id or _stable_id("rq", text.lower()), "question": text,
            "evidence_type_required": evidence_type_required,
            "preferred_source_type": preferred_source_type,
            "minimum_evidence_standard": minimum_evidence_standard,
            "blocking_or_nonblocking": "BLOCKING" if blocking else "NONBLOCKING", "status": "OPEN"}


def build_contract(*, requesting_department: str, reason: str,
                   research_questions: Iterable[dict[str, Any] | str],
                   overall_evidence_required: Iterable[str], decision_unlocked_by_answers: str,
                   return_to_department: str, return_to_goal_id: str,
                   parent_goal_id: str | None = None, parent_handoff_id: str | None = None,
                   requesting_worker: str = "department_worker", subject_type: str = "GOAL",
                   subject_id: str | None = None, priority: str = "P2", due_or_freshness_requirement: str | None = None,
                   research_request_id: str | None = None) -> dict[str, Any]:
    dept = str(requesting_department).upper().strip()
    goal_id = str(return_to_goal_id or parent_goal_id or "").strip()
    questions = []
    for item in research_questions:
        row = item if isinstance(item, dict) else question(str(item), "SOURCE_BACKED_FACT", "OFFICIAL_OR_PRIMARY", "At least one attributable source or explicit NOT_FOUND")
        if not all(row.get(key) for key in ("question_id", "question", "evidence_type_required", "preferred_source_type", "minimum_evidence_standard")):
            raise ValueError("incomplete-research-question")
        questions.append({**row, "status": row.get("status") or "OPEN"})
    if not dept or len(str(reason).strip()) < 8 or not questions or not goal_id or not str(decision_unlocked_by_answers).strip():
        raise ValueError("incomplete-research-followup-contract")
    stamp = now()
    request_id = research_request_id or _stable_id("research_request", (dept, goal_id, subject_type, subject_id, [q["question_id"] for q in questions]))
    research_query = "\n".join(f"{index + 1}. {item['question']}" for index, item in enumerate(questions))
    evidence_requirements = list(overall_evidence_required)
    return {"schema_version": CONTRACT_SCHEMA, "research_request_id": request_id, "request_id": request_id,
            "parent_goal_id": parent_goal_id or goal_id, "parent_handoff_id": parent_handoff_id,
            "requesting_department": dept, "requesting_worker": requesting_worker,
            "subject_type": subject_type, "subject_id": subject_id or goal_id,
            "reason_more_research_required": str(reason).strip(), "research_questions": questions,
            "overall_evidence_required": evidence_requirements,
            "decision_unlocked_by_answers": decision_unlocked_by_answers,
            "return_to_department": str(return_to_department).upper(), "return_to_goal_id": goal_id,
            "priority": priority, "due_or_freshness_requirement": due_or_freshness_requirement,
            "created_at": stamp, "updated_at": stamp, "status": "OPEN",
            # Existing Active Operator Research consumer aliases. These keep
            # the canonical contract executable without adding a dispatcher.
            "department": dept, "objective_id": goal_id, "question": research_query,
            "knowledge_gap": str(reason).strip(), "reason_needed": str(reason).strip(),
            "desired_evidence": evidence_requirements, "research_status": "RECEIVED",
            "alpha_status": "NOT_STARTED", "department_resume": "WAITING_FOR_INTELLIGENCE",
            "next_action": "RESEARCH_CONTRACT_EXECUTE_AND_RETURN_EVIDENCE_PACKET"}


def department_question_starters(department: str) -> list[str]:
    """Domain question starters; callers must turn these into evidence standards."""
    return list(DEPARTMENT_QUESTION_STARTERS.get(str(department).upper(), []))


def validate_contract(contract: dict[str, Any]) -> None:
    required = ("research_request_id", "parent_goal_id", "requesting_department", "requesting_worker", "subject_type", "subject_id", "reason_more_research_required", "research_questions", "overall_evidence_required", "decision_unlocked_by_answers", "return_to_department", "return_to_goal_id", "priority", "created_at", "updated_at", "status")
    if contract.get("schema_version") != CONTRACT_SCHEMA or any(contract.get(key) in (None, "") for key in required):
        raise ValueError("invalid-research-followup-contract")
    if contract["status"] not in ALLOWED_STATUSES:
        raise ValueError("invalid-research-followup-status")
    if not contract["research_questions"]:
        raise ValueError("research-questions-required")


def persist_contract(contract: dict[str, Any]) -> dict[str, Any]:
    validate_contract(contract)
    prior = persistence.get_record("research_requests", contract["research_request_id"], key="research_request_id")
    if prior and prior.get("schema_version") == CONTRACT_SCHEMA and prior.get("status") not in {"CLOSED", "CANCELLED", "RETURNED"}:
        # Idempotent creation: repeated department evaluation does not create
        # another equivalent follow-up request or duplicate question rows.
        try:
            from nexus_agent_platform import supabase_knowledge
            client = supabase_knowledge.supabase
            if not os.environ.get("NEXUS_GOVERNED_DATA_DIR") and client is not None and client.configured() and (prior.get("supabase_persistence") or {}).get("status") != "PERSISTED":
                finance_experts = {"FINANCE": "LEDGER_FINANCE", "LEDGER_FINANCE": "LEDGER_FINANCE", "OPPORTUNITIES": "ATLAS_OPPORTUNITY", "ATLAS_OPPORTUNITY": "ATLAS_OPPORTUNITY", "TRADING": "MERCURY_TRADING", "MARKETING": "MIRA_MARKETING", "CREATIVE": "MIRA_MARKETING", "LABS": "FORGE_SYSTEMS", "UPGRADE_CONTROL": "FORGE_SYSTEMS", "SYSTEMS": "FORGE_SYSTEMS"}
                row = {"request_id": contract["research_request_id"], "expert_id": finance_experts.get(contract["requesting_department"], "SCOUT_INTELLIGENCE"),
                    "assessment_id": None, "parent_finding_id": contract.get("subject_id"),
                    "research_question": contract["research_questions"][0]["question"],
                    "required_evidence": contract["overall_evidence_required"],
                    "preferred_source_types": sorted({q["preferred_source_type"] for q in contract["research_questions"]}),
                    "status": contract["status"], "created_at": contract["created_at"], "contract_payload": contract,
                    "parent_goal_id": contract["parent_goal_id"], "parent_handoff_id": contract.get("parent_handoff_id"),
                    "return_to_department": contract["return_to_department"], "return_to_goal_id": contract["return_to_goal_id"],
                    "requesting_worker": contract["requesting_worker"], "subject_type": contract["subject_type"],
                    "subject_id": contract["subject_id"], "decision_unlocked_by_answers": contract["decision_unlocked_by_answers"],
                    "priority": contract["priority"], "due_or_freshness_requirement": contract.get("due_or_freshness_requirement"),
                    "updated_at": now()}
                code, body = supabase_knowledge._write("department_research_requests", row)
                result = {"status": "PERSISTED" if code in {200, 201} else "WRITE_FAILED", "http_status": code,
                          "error": None if code in {200, 201} else str(body)[:240]}
                persistence.append_record("research_requests", {**prior, "supabase_persistence": result, "updated_at": now()})
                prior["supabase_persistence"] = result
        except Exception as exc:
            prior["supabase_persistence"] = {"status": "WRITE_FAILED", "error": type(exc).__name__}
        return prior
    persistence.append_record("research_requests", contract)
    for item in contract["research_questions"]:
        persistence.append_record("research_questions", {
            "schema_version": CONTRACT_SCHEMA, "question_id": item["question_id"],
            "research_request_id": contract["research_request_id"], "parent_goal_id": contract["parent_goal_id"],
            "department": "RESEARCH", "requesting_department": contract["requesting_department"],
            "question": item["question"], "evidence_type_required": item["evidence_type_required"],
            "preferred_source_type": item["preferred_source_type"],
            "minimum_evidence_standard": item["minimum_evidence_standard"],
            "blocking_or_nonblocking": item["blocking_or_nonblocking"], "status": item["status"],
            "priority": contract["priority"], "created_at": contract["created_at"]})
    # Reuse the canonical Supabase department request table when configured.
    # Local governed persistence remains the durable fallback already used by
    # this runtime; never claim remote persistence unless PostgREST confirms it.
    remote = {"status": "NOT_CONFIGURED"}
    try:
        from nexus_agent_platform import supabase_knowledge
        if not os.environ.get("NEXUS_GOVERNED_DATA_DIR") and supabase_knowledge.supabase is not None and supabase_knowledge.supabase.configured():
            row = {"request_id": contract["research_request_id"],
                "expert_id": {"FINANCE": "LEDGER_FINANCE", "LEDGER_FINANCE": "LEDGER_FINANCE",
                              "OPPORTUNITIES": "ATLAS_OPPORTUNITY", "ATLAS_OPPORTUNITY": "ATLAS_OPPORTUNITY",
                              "TRADING": "MERCURY_TRADING", "MARKETING": "MIRA_MARKETING",
                              "CREATIVE": "MIRA_MARKETING", "LABS": "FORGE_SYSTEMS",
                              "UPGRADE_CONTROL": "FORGE_SYSTEMS", "SYSTEMS": "FORGE_SYSTEMS"}.get(contract["requesting_department"], "SCOUT_INTELLIGENCE"),
                "assessment_id": None, "parent_finding_id": contract.get("subject_id"),
                "research_question": contract["research_questions"][0]["question"],
                "required_evidence": contract["overall_evidence_required"],
                "preferred_source_types": sorted({q["preferred_source_type"] for q in contract["research_questions"]}),
                "status": contract["status"], "created_at": contract["created_at"],
                "contract_payload": contract, "parent_goal_id": contract["parent_goal_id"],
                "parent_handoff_id": contract.get("parent_handoff_id"), "return_to_department": contract["return_to_department"],
                "return_to_goal_id": contract["return_to_goal_id"], "updated_at": contract["updated_at"]}
            code, body = supabase_knowledge._write("department_research_requests", row)
            remote = {"status": "PERSISTED" if code in {200, 201} else "WRITE_FAILED", "http_status": code,
                      "error": None if code in {200, 201} else str(body)[:240]}
    except Exception as exc:  # bounded optional mirror; local record remains intact
        remote = {"status": "WRITE_FAILED", "error": type(exc).__name__}
    if remote["status"] != "NOT_CONFIGURED":
        persistence.append_record("research_requests", {**contract, "supabase_persistence": remote, "updated_at": now()})
    contract["supabase_persistence"] = remote
    return contract


def build_evidence_packet(contract: dict[str, Any], results: Iterable[dict[str, Any]], *, overall_summary: str,
                          remaining_unknowns: Iterable[str], recommended_next_action: str) -> dict[str, Any]:
    by_id = {str(row.get("question_id")): row for row in results}
    question_results = []
    for requested in contract["research_questions"]:
        result = by_id.get(str(requested["question_id"]), {})
        status = str(result.get("status") or "NOT_FOUND").upper()
        if status not in {"ANSWERED", "PARTIAL", "NOT_FOUND", "CONTRADICTED"}:
            status = "PARTIAL"
        question_results.append({"question_id": requested["question_id"], "question": requested["question"],
            "answer": result.get("answer", ""), "status": status, "confidence": result.get("confidence", "UNKNOWN"),
            "sources": result.get("sources", []), "facts": result.get("facts", []),
            "assumptions": result.get("assumptions", []), "unknowns": result.get("unknowns", []),
            "contradictions": result.get("contradictions", [])})
    states = [item["status"] for item in question_results]
    status = "ANSWERED" if states and all(x == "ANSWERED" for x in states) else "PARTIAL"
    stamp = now()
    packet = {"schema_version": "nexus.research-evidence-packet.v1", "research_request_id": contract["research_request_id"],
        "parent_goal_id": contract["parent_goal_id"], "requesting_department": contract["requesting_department"],
        "question_results": question_results, "overall_summary": overall_summary,
        "remaining_unknowns": list(remaining_unknowns), "recommended_next_action": recommended_next_action,
        "return_to_goal_id": contract["return_to_goal_id"], "status": status, "created_at": stamp}
    updated_contract = {**contract, "research_questions": [{**q, "status": next((r["status"] for r in question_results if r["question_id"] == q["question_id"]), "NOT_FOUND")} for q in contract["research_questions"]]}
    requesting_status = "READY_TO_RESUME" if status in {"PARTIAL", "ANSWERED"} else "FOLLOW_UP_REQUIRED"
    persistence.append_record("research_requests", {**updated_contract, "status": status, "research_status": requesting_status,
        "department_resume": "WAITING_FOR_DEPARTMENT_REVIEW", "updated_at": stamp,
        "evidence_packet": packet, "next_action": recommended_next_action})
    persistence.append_record("research_questions", {"schema_version": packet["schema_version"],
        "research_request_id": contract["research_request_id"], "parent_goal_id": contract["parent_goal_id"],
        "department": "RESEARCH", "answer": packet, "status": status, "created_at": stamp})
    try:
        from nexus_agent_platform import supabase_knowledge
        client = supabase_knowledge.supabase
        if not os.environ.get("NEXUS_GOVERNED_DATA_DIR") and client is not None and client.configured():
            query_id = str(contract["research_request_id"]).replace(" ", "%20")
            code, body = client.rest("PATCH", f"department_research_requests?request_id=eq.{query_id}",
                body={"status": status, "contract_payload": {**updated_contract, "research_status": requesting_status, "evidence_packet": packet}, "updated_at": stamp},
                prefer="return=minimal")
            packet["supabase_return_persistence"] = "PASS" if code in {200, 204} else f"WRITE_FAILED_{code}"
        else:
            packet["supabase_return_persistence"] = "NOT_CONFIGURED"
    except Exception as exc:
        packet["supabase_return_persistence"] = f"WRITE_FAILED_{type(exc).__name__}"
    try:
        from nexus_agent_platform.goal_completion import record_goal_progress
        record_goal_progress(contract["return_to_goal_id"], work_item_id=contract["research_request_id"],
            result={"status": status, "decision": status, "next_action": recommended_next_action,
                    "artifact_path": f"governed.research_requests:{contract['research_request_id']}"},
            action="RESEARCH_FOLLOWUP_EVIDENCE_RETURNED", receipt_ref=f"research_request:{contract['research_request_id']}:evidence_packet")
        packet["originating_goal_woken"] = contract["return_to_goal_id"]
    except Exception as exc:
        packet["originating_goal_woken"] = "NOT_PROVEN"
        packet["goal_wake_error"] = type(exc).__name__
    return packet
