"""Canonical Research modes and durable department mission metadata."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from nexus_agent_platform.governed import persistence
from nexus_agent_platform.research_work_queue import default_queue

ROOT = Path(__file__).resolve().parents[2]
CHARTER_PATH = ROOT / "configs/research_department_charters.json"
MODES = {"REQUESTED_RESEARCH", "GOCLEAR_PROACTIVE", "NEXUS_DEPARTMENTAL_PROACTIVE"}
TRIGGERS = {"COMPANY_GOAL", "DEPARTMENT_MISSION", "PROJECT_BLOCKER", "CUSTOMER_NEED", "MARKET_SIGNAL", "EXTERNAL_CHANGE", "FOLLOW_UP", "RESEARCH_GAP", "REVENUE_OPPORTUNITY"}

def charters() -> list[dict[str, Any]]:
    return list(json.loads(CHARTER_PATH.read_text(encoding="utf-8")).get("charters", []))

def charter_for(department: str) -> dict[str, Any] | None:
    wanted = str(department).upper().replace("/", "_")
    return next((row for row in charters() if str(row.get("department", "")).upper() == wanted), None)

def classify_mode(*, requested_by: str = "", mode: str | None = None, department: str = "") -> str:
    if mode and str(mode).upper() in MODES:
        return str(mode).upper()
    if str(requested_by).lower() in {"ray", "department", "alpha", "clyde", "governance"}:
        return "REQUESTED_RESEARCH"
    return "NEXUS_DEPARTMENTAL_PROACTIVE" if department else "GOCLEAR_PROACTIVE"

def build_proactive_question(*, department: str, question: str, why_this_research: str, trigger: str,
                             business_or_nexus: str, parent_goal: str = "", project: str = "",
                             expected_value: str = "", source_plan: list[str] | None = None,
                             requested_by: str = "nexus_research", mode: str | None = None,
                             objective_id: str = "", priority: int = 30,
                             source_candidates: list[dict[str, Any]] | None = None,
                             handoff_target: str | None = None) -> dict[str, Any]:
    trigger = str(trigger).upper()
    if trigger not in TRIGGERS:
        raise ValueError(f"unsupported-research-trigger:{trigger}")
    department = str(department).upper()
    selected_mode = classify_mode(requested_by=requested_by, mode=mode, department=department)
    charter = charter_for(department) or {}
    question = str(question).strip()
    import hashlib
    digest = hashlib.sha256(f"{department}:{question}:{parent_goal}:{project}".encode()).hexdigest()[:12]
    work_id = f"proactive:{department.lower()}:{digest}"
    request_id = f"research_request:{work_id}"
    return {
        "schema_version": "nexus.research-proactive-question.v1", "request_id": request_id, "work_id": work_id,
        "research_mode": selected_mode, "WHY_THIS_RESEARCH": str(why_this_research).strip(), "TRIGGER": trigger,
        "DEPARTMENT": department, "BUSINESS_OR_NEXUS": str(business_or_nexus).upper(), "PARENT_GOAL": parent_goal,
        "PROJECT": project, "QUESTION": question, "EXPECTED_VALUE": expected_value,
        "SOURCE_PLAN": list(source_plan or charter.get("source_categories", [])),
        "department": charter.get("handoff_target") or department, "department_target": handoff_target or charter.get("handoff_target") or department,
        "objective_id": objective_id or project or request_id, "parent_goal_id": parent_goal, "question": question,
        "title": question, "requested_by": requested_by, "priority": priority, "work_class": "ASSIGNED", "lifecycle": "ONE_TIME",
        "alpha_eligible": True, "alpha_review_required": True, "selection_reason": f"{selected_mode.lower()}:{trigger.lower()}",
        "status": "RECEIVED", "next_action": "Acquire bounded evidence, then invoke the existing Alpha review bridge.",
        "created_at": persistence._now(), "external_action_allowed": False, "source_candidates": list(source_candidates or []),
    }

def persist_question(record: dict[str, Any], *, enqueue: bool = True) -> dict[str, Any]:
    persistence.append_record("research_questions", record)
    if enqueue:
        # The governed question is RECEIVED; the existing work queue only
        # accepts operational scheduling states, so project the same question
        # as QUEUED without creating another queue.
        default_queue().upsert({**record, "status": "QUEUED", "source_type": record.get("source_type", "RESEARCH_OBJECTIVE")})
    return record

def record_next_question(*, parent_question_id: str, department: str, question: str, uncertainty: str,
                         trigger: str = "RESEARCH_GAP", **kwargs: Any) -> dict[str, Any]:
    record = build_proactive_question(department=department, question=question, why_this_research=uncertainty,
        trigger=trigger, parent_goal=kwargs.pop("parent_goal", ""), project=kwargs.pop("project", ""),
        expected_value=kwargs.pop("expected_value", "Resolve a material evidence gap."),
        business_or_nexus=kwargs.pop("business_or_nexus", "NEXUS"), **kwargs)
    record["parent_question_id"] = parent_question_id
    record["next_question"] = True
    return persist_question(record)
